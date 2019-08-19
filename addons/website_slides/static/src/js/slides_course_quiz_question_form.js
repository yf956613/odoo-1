odoo.define('website_slides.quiz.question.form', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');

    var QWeb = core.qweb;
    var _t = core._t;

    /**
     * This Widget is responsible of displaying the question inputs when adding a new question or when updating an
     * existing one. When validating the question it makes an RPC call to the server and trigger an event for
     * displaying the question by the Quiz widget.
     */
    var QuestionFormWidget = publicWidget.Widget.extend({
        template: 'slide.quiz.question.input',
        xmlDependencies: ['/website_slides/static/src/xml/slide_quiz_create.xml'],
        events: {
            'click .o_wslides_js_quiz_validate_question': '_validateQuestion',
            'click .o_wslides_js_quiz_cancel_question': '_cancelValidation',
            'click .o_wslides_js_quiz_add_answer': '_addAnswerLine',
            'click .o_wslides_js_quiz_remove_answer': '_removeAnswerLine',
        },

        init: function (parent, options) {
            this.$oldElem = options.oldElement;
            this.question = options.question || {};
            this.update = options.update;
            this.sequence = options.sequence;
            this.slideId = options.slideId;
            this._super.apply(this, arguments);
        },

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.$('.o_wslides_quiz_question input').focus();
            });
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        _addAnswerLine: function (ev) {
            $(ev.currentTarget).closest('.o_wslides_js_quiz_answer').after(QWeb.render('slide.quiz.answer.line'));
        },

        _removeAnswerLine: function (ev) {
            if (this.$('.o_wslides_js_quiz_answer').length > 1) {
                $(ev.currentTarget).closest('.o_wslides_js_quiz_answer').remove();
            }
        },

        _validateQuestion: function (ev) {
            var createNext = $(ev.currentTarget).hasClass('o_wslides_js_quiz_create_next');
            this._createOrUpdateQuestion(createNext)
        },

        _cancelValidation: function () {
            this.trigger_up('resetDisplay', {
                $oldElem: this.$oldElem,
                $elem: this.$el,
                update: this.update
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _createOrUpdateQuestion: function (createNext) {
            var self = this;
            var form = this.$('form');
            if (this._isValidForm(form)) {
                var values = this._serializeForm(form);
                this._rpc({
                    route: '/slides/slide/quiz/question_add_or_update',
                    params: values
                }).then(function (response) {
                    console.log(response);
                    if (response.update) {
                        self.trigger_up('displayUpdatedQuestion', {
                            element: self.$el,
                            newQuestionData: response
                        });
                    } else {
                        self.trigger_up('displayCreatedQuestion', {
                            createNext: createNext,
                            newQuestionData: response
                        });
                    }
                }, function (error) {
                    self._alertShow(form, error.message.data.arguments[0]);
                });
            } else {
                this._alertShow(form, _t('Please fill up the question'));
                this.$('.o_wslides_quiz_question input').focus();
            }
        },

        _isValidForm: function(form) {
            return form.find('.o_wslides_quiz_question input[type=text]').val().trim() !== "";
        },

        _serializeForm: function (form) {
            var answers = [];
            var sequence = 1;
            form.find('.o_wslides_js_quiz_answer').each(function () {
                var value = $(this).find('input[type=text]').val();
                if (value.trim() !== "") {
                    var answer = {
                        'sequence': sequence++,
                        'text_value': value,
                        'is_correct': $(this).find('input[type=radio]').prop('checked') === true
                    };
                    answers.push(answer);
                }
            });
            return {
                'id': this.$el.data('id'),
                'sequence': this.sequence,
                'question': form.find('.o_wslides_quiz_question input[type=text]').val(),
                'slide_id': this.slideId,
                'answer_ids': answers
            };
        },

        _alertShow: function (form, message) {
            form.find('.o_wslides_js_quiz_create_error').removeClass('d-none');
            form.find('.o_wslides_js_quiz_create_error span:first').text(message);
        },

    });

    return QuestionFormWidget;

});