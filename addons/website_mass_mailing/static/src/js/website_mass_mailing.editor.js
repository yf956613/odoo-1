odoo.define('website_mass_mailing.editor', function (require) {
'use strict';

var core = require('web.core');
var rpc = require('web.rpc');
var weContext = require('web_editor.context');
var web_editor = require('web_editor.editor');
var options = require('web_editor.snippets.options');
var wUtils = require('website.utils');
var _t = core._t;

<<<<<<< HEAD

options.registry.mailing_list_subscribe = options.Class.extend({
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field

var mass_mailing_common = options.Class.extend({
=======
var mass_mailing_common = options.Class.extend({
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    popup_template_id: "editor_new_mailing_list_subscribe_button",
    popup_title: _t("Add a Newsletter Subscribe Button"),

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Allows to select mailing list.
     *
     * @see this.selectClass for parameters
     */
    select_mailing_list: function (previewMode, value) {
        var self = this;
        var def = wUtils.prompt({
            'id': this.popup_template_id,
            'window_title': this.popup_title,
            'select': _t("Newsletter"),
            'init': function (field, dialog) {
                return rpc.query({
<<<<<<< HEAD
                    model: 'mailing.list',
                    method: 'name_search',
                    args: ['', [['is_public', '=', true]]],
                    context: self.options.recordInfo.context,
                }).then(function (data) {
                    $(dialog).find('.btn-primary').prop('disabled', !data.length);
                    return data;
                });
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
                        model: 'mail.mass_mailing.list',
                        method: 'name_search',
                        args: ['', []],
                        context: self.options.recordInfo.context,
                    });
=======
                        model: 'mail.mass_mailing.list',
                        method: 'name_search',
                        args: ['', []],
                        context: weContext.get(), // TODO use this._rpc
                    });
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
            },
        });
        def.then(function (result) {
            self.$target.attr("data-list-id", result.val);
        });
        return def;
    },
    /**
     * @override
     */
    onBuilt: function () {
        var self = this;
        this._super();
        this.select_mailing_list('click').guardedCatch(function () {
            self.getParent()._onRemoveClick($.Event( "click" ));
        });
    },
});

options.registry.newsletter_popup = options.registry.mailing_list_subscribe.extend({
    popup_template_id: "editor_new_mailing_list_subscribe_popup",
    popup_title: _t("Add a Newsletter Subscribe Popup"),

    /**
     * @override
     */
    start: function () {
        var self = this;
<<<<<<< HEAD
        this.$target.on('click.newsletter_popup_option', '.o_edit_popup', function (ev) {
            // So that the snippet is not enabled again by the editor
            ev.stopPropagation();
            self.$target.data('quick-open', true);
            self._refreshPublicWidgets();
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        return this._super(previewMode, value).then(function (mailing_list_id) {
            ajax.jsonRpc('/web/dataset/call', 'call', {
                model: 'mail.mass_mailing.list',
                method: 'read',
                args: [[parseInt(mailing_list_id)], ['popup_content'], self.options.recordInfo.context],
            }).then(function (data) {
                self.$target.find(".o_popup_content_dev").empty();
                if (data && data[0].popup_content) {
                    $(data[0].popup_content).appendTo(self.$target.find(".o_popup_content_dev"));
                }
            });
=======
        return this._super(previewMode, value).then(function (mailing_list_id) {
            self._rpc({
                model: 'mail.mass_mailing.list',
                method: 'read',
                args: [[parseInt(mailing_list_id)], ['popup_content']],
            }).then(function (data) {
                self.$target.find(".o_popup_content_dev").empty();
                if (data && data[0].popup_content) {
                    $(data[0].popup_content).appendTo(self.$target.find(".o_popup_content_dev"));
                }
            });
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        });
        this.$target.on('shown.bs.modal.newsletter_popup_option hide.bs.modal.newsletter_popup_option', function () {
            self.$target.closest('.o_editable').trigger('content_changed');
            self.trigger_up('deactivate_snippet');
        });
        return this._super.apply(this, arguments);
    },
<<<<<<< HEAD
    /**
     * @override
     */
    cleanForSave: function () {
        var self = this;
        var content = this.$target.data('content');
        if (content) {
            this.trigger_up('get_clean_html', {
                $layout: $('<div/>').html(content),
                callback: function (html) {
                    self.$target.data('content', html);
                },
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
});

WysiwygMultizone.include({
    events: _.extend({}, WysiwygMultizone.prototype.events, {
        'click #edit_dialog': 'edit_dialog',
        'click .o_popup_modal_content [data-dismiss="modal"]': 'close_dialog',
    }),
    save: function () {
        var $target = $('#wrapwrap').find('#o_newsletter_popup');
        if ($target && $target.length) {
            this.close_dialog();
            $('.o_popup_bounce_small').show();
            if (!$target.find('.o_popup_content_dev').length) {
                $target.find('.o_popup_modal_body').prepend($('<div class="o_popup_content_dev" data-oe-placeholder="' + _t("Type Here ...") + '"></div>'));
            }
            var content = $('#wrapwrap .o_popup_content_dev').html();
            var newsletter_id = $target.parent().attr('data-list-id');
            ajax.jsonRpc('/web/dataset/call', 'call', {
                model: 'mail.mass_mailing.list',
                method: 'write',
                args: [
                    parseInt(newsletter_id),
                    {'popup_content':content},
                    this.options.recordInfo.context,
                ],
=======
});

web_editor.Class.include({
    start: function () {
        $('body').on('click','#edit_dialog',_.bind(this.edit_dialog, this.rte.editor));
        return this._super();
    },
    save: function () {
        var $target = $('#wrapwrap').find('#o_newsletter_popup');
        if ($target && $target.length) {
            $target.modal('hide');
            $target.css("display", "none");
            $('.o_popup_bounce_small').show();
            if (!$target.find('.o_popup_content_dev').length) {
                $target.find('.o_popup_modal_body').prepend($('<div class="o_popup_content_dev" data-oe-placeholder="' + _t("Type Here ...") + '"></div>'));
            }
            var content = $('#wrapwrap .o_popup_content_dev').html();
            var newsletter_id = $target.parent().attr('data-list-id');
            this._rpc({
                model: 'mail.mass_mailing.list',
                method: 'write',
                args: [
                    parseInt(newsletter_id),
                    {'popup_content':content},
                ],
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
            });
        }
        this._super.apply(this, arguments);
    },
<<<<<<< HEAD
    /**
     * @override
     */
    destroy: function () {
        this.$target.off('.newsletter_popup_option');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    select_mailing_list: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$target.data('quick-open', true);
            self.$target.removeData('content');
            self._refreshPublicWidgets();
        });
    },
});

WysiwygMultizone.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _saveElement: function (outerHTML, recordInfo, editable) {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        var $popups = $(editable).find('.o_newsletter_popup');
        _.each($popups, function (popup) {
            var $popup = $(popup);
            var content = $popup.data('content');
            if (content) {
                defs.push(self._rpc({
                    route: '/website_mass_mailing/set_content',
                    params: {
                        'newsletter_id': parseInt($popup.attr('data-list-id')),
                        'content': content,
                    },
                }));
            }
        });
        return Promise.all(defs);
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    destroy: function () {
        this.close_dialog();
        this._super();
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    close_dialog: function () {
        $('#wrapwrap').find('#o_newsletter_popup').modal('hide');
    },
    edit_dialog: function (ev) {
        $('#wrapwrap').find('#o_newsletter_popup').modal('show');
        $('.o_popup_bounce_small').hide();
        $('.modal-backdrop').css("z-index", "0");
=======
    edit_dialog: function () {
        $('#wrapwrap').find('#o_newsletter_popup').modal('show');
        $('.o_popup_bounce_small').hide();
        $('.modal-backdrop').css("z-index", "0");
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    },
});
});
