odoo.define('website_slides.quiz', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var session = require('web.session');

    var CourseJoinWidget = require('website_slides.course.join.widget').courseJoinWidget;
    var QuestionFormWidget = require('website_slides.quiz.question.form');

    var QWeb = core.qweb;
    var _t = core._t;

    /**
     * This widget is responsible of displaying quiz questions and propositions. Submitting the quiz will fetch the
     * correction and decorate the answers according to the result. Error message or modal can be displayed.
     *
     * This widget can be attached to DOM rendered server-side by `website_slides.slide_type_quiz` or
     * used client side (Fullscreen).
     *
     * Triggered events are :
     * - slide_go_next: need to go to the next slide, when quiz is done. Event data contains the current slide id.
     * - quiz_completed: when the quiz is passed and completed by the user. Event data contains current slide data.
     */
    var Quiz= publicWidget.Widget.extend({
        template: 'slide.slide.quiz',
        xmlDependencies: ['/website_slides/static/src/xml/slide_quiz.xml'],
        events: {
            "click .o_wslides_quiz_answer": '_onAnswerClick',
            "click .o_wslides_js_lesson_quiz_submit": '_onSubmitQuiz',
            "click .o_wslides_quiz_btn": '_onClickNext',
            "click .o_wslides_quiz_continue": '_onClickNext',
            "click .o_wslides_js_lesson_quiz_reset": '_onClickReset',
            'click .o_wslides_js_quiz_add': '_onQuizCreation',
            'click .o_wslides_js_quiz_edit_question': '_onEditQuestionClick',
            'click .o_wslides_js_quiz_delete_question': '_onDeleteQuestionClick',
        },

        custom_events: {
            displayCreatedQuestion: '_displayCreatedQuestion',
            displayUpdatedQuestion: '_displayUpdatedQuestion',
            resetDisplay: '_resetDisplay',
            deleteQuestion: '_deleteQuestion',
        },

        /**
        * @override
        * @param {Object} parent
        * @param {Object} slide_data holding all the classic slide informations
        * @param {Object} quiz_data : optional quiz data to display. If not given, will be fetched. (questions and answers).
        */
        init: function (parent, slide_data, channel_data, quiz_data) {
            this.slide = _.defaults(slide_data, {
                id: 0,
                name: '',
                hasNext: false,
                completed: false,
                readonly: false,
            });
            this.quiz = quiz_data || false;
            if (this.quiz)
                this.quiz.questionsCount = quiz_data.questions.length || 0;
            this.readonly = slide_data.readonly || false;
            this.publicUser = session.is_website_user;
            this.redirectURL = encodeURIComponent(document.URL);
            this.channel = channel_data;
            return this._super.apply(this, arguments);
        },

        /**
         * @override
         */
        willStart: function () {
            var defs = [this._super.apply(this, arguments)];
            if (!this.quiz) {
                defs.push(this._fetchQuiz());
            }
            return Promise.all(defs);
        },

        /**
         * @override
         */
        start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function ()  {
                self._renderAnswers();
                self._renderAnswersHighlighting();
                self._renderValidationInfo();
                self._bindSortable();
                self._checkLocationHref();
                new CourseJoinWidget(self, self.channel.channelId).appendTo(self.$('.o_wslides_course_join_widget'));
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _alertHide: function () {
            this.$('.o_wslides_js_lesson_quiz_error').addClass('d-none');
        },

        _alertShow: function (alert_code) {
            var message = _t('There was an error validating this quiz.');
            if (! alert_code || alert_code === 'slide_quiz_incomplete') {
                message = _t('All questions must be answered !');
            }
            else if (alert_code === 'slide_quiz_done') {
                message = _t('This quiz is already done. Retaking it is not possible.');
            } else if (alert_code === 'public_user') {
                message = _t("You must be logged to submit the quiz.");
            }
            this.$('.o_wslides_js_lesson_quiz_error span').html(message);
            this.$('.o_wslides_js_lesson_quiz_error').removeClass('d-none');
        },

        /**
         * Allows to reorder the questions
         * @private
         */
        _bindSortable: function() {
            this.$el.sortable({
                handle: '.o_wslides_js_quiz_sequence_handler',
                items: '.o_wslides_js_lesson_quiz_question',
                stop: this._reorderQuestions.bind(this),
                placeholder: 'o_wslides_js_quiz_sequence_highlight position-relative my-3'
            });
        },

        _getQuestions: function () {
            var questionIds = [];
            this.$('.o_wslides_js_lesson_quiz_question').each(function (index, question) {
                $(question).find('span.o_wslides_quiz_question_sequence').text(index + 1);
                questionIds.push($(question).data('question-id'));
            });
            return questionIds;
        },

        _reorderQuestions: function () {
            var self = this;
            self._rpc({
                route: '/web/dataset/resequence',
                params: {
                    model: "slide.question",
                    offset: 1,
                    ids: self._getQuestions()
                }
            });
        },

        /*
         * @private
         * Fetch the quiz for a particular slide
         */
        _fetchQuiz: function () {
            var self = this;
            return self._rpc({
                route:'/slides/slide/quiz/get',
                params: {
                    'slide_id': self.slide.id,
                }
            }).then(function (quiz_data) {
                self.quiz = {
                    questions: quiz_data.slide_questions,
                    questionsCount: quiz_data.slide_questions.length,
                    quizAttemptsCount: quiz_data.quiz_attempts_count,
                    quizKarmaGain: quiz_data.quiz_karma_gain,
                    quizKarmaWon: quiz_data.quiz_karma_won
                };
            });
        },

        _renderQuestions: function () {
            this.$('.o_wslides_js_lesson_quiz_question').each(function () {
                var $question = $(this);
                $question.find('.o_wslides_js_quiz_sequence_handler').addClass('d-none');
                $question.find('.o_wslides_js_quiz_edit_del').addClass('d-none');
            });
        },

        /**
         * @private
         * Decorate the answers according to state
         */
        _renderAnswers: function () {
            var self = this;
            this.$('input[type=radio]').each(function () {
                $(this).prop('disabled', self.slide.readonly || self.slide.completed);
            });
        },

        /**
         * @private
         * Decorate the answer inputs according to the correction
         */
        _renderAnswersHighlighting: function () {
            var self = this;
            this.$('a.o_wslides_quiz_answer').each(function () {
                var $answer = $(this);
                var answerId = $answer.data('answerId');
                if (_.contains(self.quiz.goodAnswers, answerId)) {
                    $answer.removeClass('list-group-item-danger').addClass('list-group-item-success');
                    $answer.find('i.fa').addClass('d-none');
                    $answer.find('i.fa-check-circle').removeClass('d-none');
                }
                else if (_.contains(self.quiz.badAnswers, answerId)) {
                    $answer.removeClass('list-group-item-success').addClass('list-group-item-danger');
                    $answer.find('i.fa').addClass('d-none');
                    $answer.find('i.fa-times-circle').removeClass('d-none');
                    $answer.find('label input').prop('checked', false);
                }
                else {
                    if (!self.slide.completed) {
                        $answer.removeClass('list-group-item-danger list-group-item-success');
                        $answer.find('i.fa').addClass('d-none');
                        $answer.find('i.fa-circle').removeClass('d-none');
                    }
                }
            });
        },

        /**
         * @private
         * When the quiz is done and succeed, a congratulation modal appears.
         */
        _renderSuccessModal: function () {
            var $modal = this.$('#slides_quiz_modal');
            if (!$modal.length) {
                this.$el.append(QWeb.render('slide.slide.quiz.finish', {'widget': this}));
                $modal = this.$('#slides_quiz_modal');
            }
            $modal.modal({
                'show': true,
            });
            $modal.on('hidden.bs.modal', function () {
                $modal.remove();
            });
        },

        /*
         * @private
         * Update validation box (karma, buttons) according to widget state
         */
        _renderValidationInfo: function () {
            var $validationElem = this.$('.o_wslides_js_lesson_quiz_validation');
            $validationElem.html(
                QWeb.render('slide.slide.quiz.validation', {'widget': this})
            );
        },
        /*
         * Submit the given answer, and display the result
         *
         * @param Array checkedAnswerIds: list of checked answers
         */
        _submitQuiz: function (checkedAnswerIds) {
            var self = this;
            return this._rpc({
                route: '/slides/slide/quiz/submit',
                params: {
                    slide_id: self.slide.id,
                    answer_ids: checkedAnswerIds,
                }
            }).then(function(data){
                if (data.error) {
                    self._alertShow(data.error);
                } else {
                    self.quiz = _.extend(self.quiz, data);
                    if (data.completed) {
                        self._renderSuccessModal(data);
                        self.slide.completed = true;
                        self.trigger_up('slide_completed', {slide: self.slide, completion: data.channel_completion});
                    }
                    self._renderQuestions();
                    self._renderAnswersHighlighting();
                    self._renderValidationInfo();
                }
            });
        },

       _getQuestionDetails: function ($elem) {
            var answers = [];
            $elem.find('.o_wslides_quiz_answer').each(function () {
                answers.push({
                    'id': $(this).data('answerId'),
                    'text_value': $(this).data('text'),
                    'is_correct': $(this).data('isCorrect')
                });
            });
            return {
                'id': $elem.data('questionId'),
                'sequence': parseInt($elem.find('.o_wslides_quiz_question_sequence').text()),
                'text': $elem.data('title'),
                'answers': answers,
            };
        },

        /**
         * If the slides has been called with the Add Quiz button on the slide list
         * it goes straight to the anchor and open a new QuestionFormWidget.
         * @private
         */
        _checkLocationHref: function() {
            if (window.location.href.includes('#quiz')) {
                this._onQuizCreation();
            }
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * When clicking on an answer, this one should be marked as "checked".
         *
         * @private
         * @param OdooEvent ev
         */
        _onAnswerClick: function (ev) {
            ev.preventDefault();
            if (! this.slide.readonly && ! this.slide.completed) {
                $(ev.currentTarget).find('input[type=radio]').prop('checked', true);
            }
            this._alertHide();
        },
        /**
         * Triggering a event to switch to next slide
         *
         * @private
         * @param OdooEvent ev
         */
        _onClickNext: function (ev) {
            if (this.slide.hasNext) {
                this.trigger_up('slide_go_next');
            }
        },
        /**
         * Triggering a event to reset the completion of the slide
         *
         * @private
         */
        _onClickReset: function () {
            this._rpc({
                route: '/slides/slide/quiz/reset',
                params: {
                    slide_id: this.slide.id
                }
            }).then(function() {
                window.location.reload();
            });
        },
        /**
         * Submit a quiz and get the correction. It will display messages
         * according to quiz result.
         *
         * @private
         * @param OdooEvent ev
         */
        _onSubmitQuiz: function (ev) {
            var inputs = this.$('input[type=radio]:checked');
            var values = [];
            for (var i = 0; i < inputs.length; i++){
                values.push(parseInt($(inputs[i]).val()));
            }

            if (values.length === this.quiz.questionsCount){
                this._alertHide();
                this._submitQuiz(values);
            } else {
                this._alertShow();
            }
        },

        _onQuizCreation: function () {
            var $elem = this.$('.o_wslides_js_quiz_add');
            new QuestionFormWidget(this, {
                slideId: this.slide.id,
                sequence: this.quiz.questionsCount + 1
            }).replace($elem);
        },

        _onEditQuestionClick: function (ev) {
            var $elem = $(ev.currentTarget).closest('.o_wslides_js_lesson_quiz_question');
            var question = this._getQuestionDetails($elem);
            new QuestionFormWidget(this, {
                oldElement: $elem,
                question: question,
                slideId: this.slide.id,
                sequence: question.sequence,
                update: true
            }).replace($elem);
        },

        _onDeleteQuestionClick: function (ev) {
            var question = $(ev.currentTarget).closest('.o_wslides_js_lesson_quiz_question');
            new ConfirmationDialog(this, null, question).open();
        },

        /**
         * Displays the created Question at the correct place (after the last question or
         * at the first place if there is no questions yet) It also displays the 'Add Question'
         * button or open a new QuestionFormWidget if the user wants to immediately add another one.
         *
         * @param response
         * @private
         */
        _displayCreatedQuestion: function (response) {
            var newQuestion = response.data.newQuestionData;
            var $lastQuestion = this.$('.o_wslides_js_lesson_quiz_question:last');
            var renderedQuestion = QWeb.render('slide.quiz.question.view', {question: newQuestion});
            if ($lastQuestion.length !== 0) {
                $lastQuestion.after(renderedQuestion);
            } else {
                this.$el.prepend(renderedQuestion);
            }
            this.quiz.questionsCount++;
            var $elem = this.$('.o_wsildes_quiz_question_input:last');
            if (response.data.createNext) {
                new QuestionFormWidget(this, {
                    slideId: this.slide.id,
                    sequence: this.quiz.questionsCount + 1
                }).replace($elem);
            } else {
                $elem.replaceWith(QWeb.render('slide.quiz.new.question.button'));
            }
        },

        _displayUpdatedQuestion: function (response) {
            response.data.element.replaceWith(QWeb.render('slide.quiz.question.view', { question: response.data.newQuestionData }));
        },

        /**
         * If the user cancels the creation or update of a Question it resets the display
         * of the updated Question or it displays back the buttons.
         *
         * @param reset
         * @private
         */
        _resetDisplay: function (reset) {
            if (reset.data.update) {
                reset.data.$elem.html(reset.data.$oldElem);
            } else {
                var $elem = this.$('.o_wslides_js_lesson_quiz_new_question');
                if (this.quiz.questionsCount > 0) {
                    $elem.html(QWeb.render('slide.quiz.new.question.button'));
                } else {
                    $elem.html(QWeb.render('slide.quiz.new.quiz.button'));
                }
            }
        },

        /**
         * After deletion of a Question the display is refreshed with the removal of the Question
         * the reordering of all the remaining Questions and the change of the new Question sequence
         * if the QuestionFormWidget is initialized.
         *
         * @param event
         * @private
         */
        _deleteQuestion: function(event) {
            var question = event.data;
            question.remove();
            this.quiz.questionsCount--;
            this._reorderQuestions();
            var $newQuestion = this.$('.o_wslides_js_lesson_quiz_new_question .o_wslides_quiz_question_sequence');
            $newQuestion.text(parseInt($newQuestion.text()) - 1);
        },
    });

    /**
     * Dialog box shown when clicking the deletion button on a Question.
     * When confirming it sends a RPC request to delete the Question.
     */
    var ConfirmationDialog = Dialog.extend({
        template: 'slide.quiz.confirm.deletion',
        xmlDependencies: Dialog.prototype.xmlDependencies.concat(
            ['/website_slides/static/src/xml/slide_quiz_create.xml']
        ),

        init: function (parent, options, question) {
            options = _.defaults(options || {}, {
                title: _t('Delete Question'),
                buttons: [
                    { text: _t('Yes'), classes: 'btn-primary', click: this._confirm },
                    { text: _t('No'), close: true}
                ],
                size: 'medium'
            });
            this.question = question;
            this._super(parent, options);
        },

        _confirm: function () {
            var self = this;
            this._rpc({
                model: 'slide.question',
                method: 'unlink',
                args: [this.question.data('questionId')],
            }).then(function () {
                self.trigger_up('deleteQuestion', self.question);
                self.close();
            }, function (error) {
                console.log(error);
            });
        }

    });

    publicWidget.registry.websiteSlidesQuizNoFullscreen = publicWidget.Widget.extend({
        selector: '.o_wslides_lesson_main', // selector of complete page, as we need slide content and aside content table
        custom_events: {
            slide_go_next: '_onQuizNextSlide',
            slide_completed: '_onQuizCompleted',
        },

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         * @param {Object} parent
         */
        start: function () {
            var self = this;
            this.quizWidgets = [];
            var defs = [this._super.apply(this, arguments)];
            this.$('.o_wslides_js_lesson_quiz').each(function () {
                var slideData = $(this).data();
                var channelData = self._extractChannelData(slideData);
                slideData.quizData = {
                    questions: self._extractQuestionsAndAnswers(),
                    quizKarmaMax: slideData.quizKarmaMax,
                    quizKarmaWon: slideData.quizKarmaWon,
                    quizKarmaGain: slideData.quizKarmaGain,
                    quizAttemptsCount: slideData.quizAttemptsCount,
                };
                defs.push(new Quiz(self, slideData, channelData, slideData.quizData).attachTo($(this)));
            });
            return Promise.all(defs);
        },

        //----------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------
        _onQuizCompleted: function (ev) {
            var self = this;
            var slide = ev.data.slide;
            var completion = ev.data.completion;
            this.$('#o_wslides_lesson_aside_slide_check_' + slide.id).addClass('text-success fa-check').removeClass('text-600 fa-circle-o');
            // need to use global selector as progress bar is ouside this animation widget scope
            $('.o_wslides_lesson_header .progress-bar').css('width', completion + "%");
            $('.o_wslides_lesson_header .progress span').text(_.str.sprintf("%s %%", completion));
        },
        _onQuizNextSlide: function () {
            var url = this.$('.o_wslides_js_lesson_quiz').data('next-slide-url');
            window.location.replace(url);
        },

        //----------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        _extractChannelData: function (slideData){
            return {
                id: slideData.channelId,
                channelEnroll: slideData.channelEnroll,
                signupAllowed: slideData.signupAllowed
            };
        },

        /**
         * Extract data from exiting DOM rendered server-side, to have the list of questions with their
         * relative answers.
         * This method should return the same format as /slide/quiz/get controller.
         *
         * @return {Array<Object>} list of questions with answers
         */
        _extractQuestionsAndAnswers: function() {
            var questions = [];
            this.$('.o_wslides_js_lesson_quiz_question').each(function () {
                var $question = $(this);
                var answers = [];
                $question.find('.o_wslides_quiz_answer').each(function () {
                    var $answer = $(this);
                    answers.push({
                        id: $answer.data('answerId'),
                        text: $answer.data('text'),
                    });
                });
                questions.push({
                    id: $question.data('questionId'),
                    title: $question.data('title'),
                    answers: answers,
                });
            });
            return questions;
        },
    });

    return Quiz;
});
