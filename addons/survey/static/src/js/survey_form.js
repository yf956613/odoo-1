odoo.define('survey.form', function(require) {
'use strict';

var ajax = require('web.ajax');
var field_utils = require('web.field_utils');
var rpc = require('web.rpc');
var publicWidget = require('web.public.widget');
var time = require('web.time');

publicWidget.registry.SurveyFormWidget = publicWidget.Widget.extend({
    selector: '.o_survey_form',
    events: {
        'change .o_survey_form_simple_radio input[type="radio"]': '_onChangeRadio',
        'change .o_survey_form_select': '_onChangeSelect',
        'change .o_survey_form_checkbox_other': '_onChangeMultipleCheckbox',
        'click button[name="button_submit"]': '_onSubmit',
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    start: function () {
        var self = this;
        self.surveyToken = self.$target.data('surveyToken');
        self.answerToken = self.$target.data('answerToken');

        var $timer = $('.o_survey_timer');
        if ($timer.length) {
            self.surveyTimerWidget = new publicWidget.registry.SurveyTimerWidget(this);
            self.surveyTimerWidget.attachTo($timer);
            self.surveyTimerWidget.on('time_up', self, function (ev) {
                self.$el.find('button[name="button_submit"]').click();
            });
        }

        this.$('div.o_survey_form_date').each(function () {
            self._updateDateForDisplay($(this));
        });

        this.$('div.o_survey_form_multiple').each(function () {
            self._updateMultipleChoiceForDisplay($(this));
        });

        this.$('div.o_survey_form_simple_radio').each(function () {
            self._updateSimpleRadioForDisplay($(this));
        });

        this.$('div.o_survey_form_simple_select').each(function () {
            self._updateSimpleSelectForDisplay($(this));
        });

        return this._super.apply(this, arguments);
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    // EVENTS
    // -------------------------------------------------------------------------
    _onChangeRadio: function (event) {
        var $radioGroup = $(event.currentTarget).parents('.o_survey_form_simple_radio');
        return this._updateSimpleRadioForDisplay($radioGroup);
    },

    _onChangeSelect: function (event) {
        var $selectGroup = $(event.currentTarget).parents('.o_survey_form_simple_select');
        return this._updateSimpleSelectForDisplay($selectGroup);
    },

    _onChangeMultipleCheckbox: function (event) {
        var $checkGroup = $(event.currentTarget).parents('.o_survey_form_multiple');
        return this._updateMultipleChoiceForDisplay($checkGroup);
    },

    _onSubmit: function (event) {
        var self = this;
        event.preventDefault();
        var $target = $(event.currentTarget);
        var submitValue = $target.val();
        var $form = $target.parents('form.o_survey_form');
        var formData = new FormData($form[0]);
        var params = {
            button_submit: submitValue,
        };

        this.$('div.o_survey_form_date').each(function () {
            self._updateDateForSubmit($(this), formData);
        });
        this._prepareSubmitValues(formData, params);

        this._resetErrors();

        return self._rpc({
            route: '/survey/submit/' + self.surveyToken + '/' + self.answerToken,
            params: params,
        }).then(function (result) {
            return self._onSubmitDone(result, params);
        });
    },

    _onSubmitDone: function (result, params) {
        var self = this;
        if (result && !result.error) {
            window.location = result;
        }
        else if (result && result.fields && result.error === 'validation') {
            var fieldKeys = _.keys(result.fields);
            _.each(fieldKeys, function (key) {
                self.$("#" + key + '>.o_survey_question_error').append($('<p>', {text: result.fields[key]})).show();
                if (fieldKeys[fieldKeys.length - 1] === key) {
                    self._scrollToError(self.$('.o_survey_question_error:visible:first').closest('.js_question-wrapper'));
                }
            });
            return false;
        }
        else {
            var $target = self.$('.o_survey_error');
            $target.append('<p>Their was an error during the validation of the survey.</p>').show();
            self._scrollToError($target);
            return false;
        }
    },

    // INIT FIELDS
    // -------------------------------------------------------------------------
    /*
    * Convert the server side date format into client side date format before display
    * And initialize the datetimepicker with min - max date constraints
    */
    _updateDateForDisplay: function ($dateGroup) {
        this._formatDateValue($dateGroup);
        // if review mode, avoid to use the datetimepicker
        var review_fieldset = $dateGroup.closest('fieldset');
        if (review_fieldset.lenght === 1 && review_fieldset[0].disabled) {
            $dateGroup.find('.input-group-append').hide();
        } else {
            this._initDateTimePicker($dateGroup);
        }
    },

    /*
    * Convert the client side date format into server side date format before submit
    */
    _updateDateForSubmit: function (dateGroup, formData) {
        var input = $(dateGroup).find('input');
        var dateValue = input.val();
        var questionType = $(input).closest('.o_survey_form_date').data('questiontype');
        if (dateValue) {
            var momentDate = questionType === 'datetime' ? field_utils.parse.datetime(dateValue, null, {timezone: true}) : field_utils.parse.date(dateValue);
            var newDate = momentDate ? momentDate.toJSON() : '';
            formData.set(input.attr('name'), newDate);
            input.val(newDate);
        }
    },

    /*
    * Checks, for review mode or already answered page, if the 'other' choice is checked.
    * Clear the comment textarea and disable if if not checked (just in case) or focus on it and enable it.
    */
    _updateMultipleChoiceForDisplay: function ($checkGroup) {
        var $other = $checkGroup.find('.o_survey_form_checkbox_other');
        var $commentInput = $checkGroup.find('textarea[type="text"]');
        if (!$other.prop('checked') && !$commentInput.hasClass('o_survey_comment')) {
            $commentInput.enable(false);
            $commentInput.val('');
        } else {
            $commentInput.enable();
            $commentInput.focus();
        }
    },

    /*
    * Checks, for review mode or already answered page, if the 'other' choice is checked.
    * Clear the comment textarea if not checked (just in case) or focus on it.
    */
    _updateSimpleRadioForDisplay: function ($radioGroup) {
        var $other = $radioGroup.find('.o_survey_form_radio_other');
        var $commentInput = $radioGroup.find('textarea[type="text"]');
        if (!$other.prop('checked') && !$commentInput.hasClass('o_survey_comment')) {
            $commentInput.enable(false);
            $commentInput.val('');
        } else {
            $commentInput.enable();
        }
    },

    /*
    * Checks, for review mode or already answered page, if the 'other' choice is checked.
    * Clear and hide the comment textarea if not checked (just in case) or display it.
    */
    _updateSimpleSelectForDisplay: function ($selectGroup) {
        var $select = $selectGroup.find('select');
        var $other = $selectGroup.find('.o_survey_form_select_other');
        var $commentInput = $selectGroup.find('textarea[type="text"]');
        if ($select.val() === $other.val() || $commentInput.hasClass('o_survey_comment')) {
            $commentInput.show();
        } else {
            $commentInput.val('');
            $commentInput.hide();
        }
    },

    // TOOLS
    // -------------------------------------------------------------------------
    _prepareSubmitValues: function (formData, params) {
        var self = this;
        formData.forEach(function(value, key){
            if (value !== -1) {
                // Handles Comment
                if (key.indexOf('_comment') !== -1){
                    key = key.split('_comment')[0];
                    value = {'comment': value};
                }
                // Handles Matrix - Matrix answer_tag are composed like : 'questionId_rowId_colId'
                // and are the only ones with this structure.
                var splitKey = key.split('_');
                if (splitKey.length === 3 && splitKey[2] === value) {
                    params = self._prepareSubmitMatrix(params, splitKey, value);
                }
                // Handles the rest
                else {
                    params = self._prepareSubmitOther(params, key, value);
                }
            }
        });
    },

    /**
    *   Prepare answer before submitting form if question type is matrix.
    *   This method regroups answers by question and by row to make a object like :
    *   params = { 'matrixQuestionId' : { 'rowId1' : [colId1, colId2,...], 'rowId2' : [colId1, colId3, ...] } }
    */
    _prepareSubmitMatrix: function(params, splitKey, value) {
        var key = splitKey[0];
        var rowId = splitKey[1];
        var colId = splitKey[2];
        value = key in params ? params[key] : {};
        if (rowId in value) {
            value[rowId].push(colId);
        } else {
            value[rowId] = [colId];
        }
        params[key] = value;
        return params;
    },

    /**
    *   Prepare answer before submitting form (any kind of answer - except Matrix -).
    *   This method regroups answers by question.
    *   Lonely answer are directly assigned to questionId. Multiple answers are regrouped in an array:
    *   params = { 'questionId1' : lonelyAnswer, 'questionId2' : [multipleAnswer1, multipleAnswer2, ...] }
    */
    _prepareSubmitOther: function(params, key, value) {
        if (key in params) {
            if (params[key].constructor === Array) {
                params[key].push(value);
            } else {
                params[key] = [params[key], value];
            }
        } else {
            params[key] = value;
        }
        return params;
    },

    /**
    * Convert date value in client current timezone (if review mode)
    */
    _formatDateValue: function ($dateGroup) {
        var input = $dateGroup.find('input');
        var dateValue = input.val();
        if (dateValue !== '') {
            var momentDate = field_utils.parse.date(dateValue);
            if ($dateGroup.data('questiontype') === 'datetime') {
                dateValue = field_utils.format.datetime(momentDate, null, {timezone: true});
            } else {
                dateValue = field_utils.format.date(momentDate, null, {timezone: true});
            }
        }
        input.val(dateValue);
        return dateValue
    },

    /**
    * Initialize datetimepicker in correct format and with constraints
    */
    _initDateTimePicker: function ($dateGroup) {
        var disabledDates = []

        var minDateData = $dateGroup.data('mindate')
        var minDate = minDateData ? this._formatDateTime(minDateData) : moment({ y: 1900 });
        var maxDateData = $dateGroup.data('maxdate')
        var maxDate = maxDateData ? this._formatDateTime(maxDateData) : moment().add(200, "y");

        var datetimepickerFormat = time.getLangDateFormat()
        if ($dateGroup.data('questiontype') === 'datetime') {
            datetimepickerFormat = time.getLangDatetimeFormat()
        } else {
            // Include min and max date in selectable values
            maxDate = moment(maxDate).add(1, "d");
            minDate = moment(minDate).subtract(1, "d");
            disabledDates = [minDate, maxDate]
        }

        $dateGroup.datetimepicker({
            format : datetimepickerFormat,
            minDate: minDate,
            maxDate: maxDate,
            disabledDates: disabledDates,
            useCurrent: false,
            viewDate: moment(new Date()).hours(0).minutes(0).seconds(0).milliseconds(0),
            calendarWeeks: true,
            icons: {
                time: 'fa fa-clock-o',
                date: 'fa fa-calendar',
                next: 'fa fa-chevron-right',
                previous: 'fa fa-chevron-left',
                up: 'fa fa-chevron-up',
                down: 'fa fa-chevron-down',
            },
            locale : moment.locale(),
            allowInputToggle: true,
        });
    },

    _formatDateTime: function ($target){
        return field_utils.format.datetime(moment($target), null, {timezone: true});
    },

    _scrollToError: function ($target) {
        var scrollLocation = $target.offset().top;
        var navbarHeight = $('.o_main_navbar').height();
        if (navbarHeight != undefined) {
            scrollLocation -= navbarHeight
        }
        $('html, body').animate({
            scrollTop: scrollLocation
        }, 500);
    },

    /**
    * Clean all form errors in order to clean DOM before a new validation
    */
    _resetErrors: function () {
        this.$('.o_survey_question_error, .o_survey_error').html('').hide();
    },

});

return publicWidget.registry.SurveyFormWidget;

});
