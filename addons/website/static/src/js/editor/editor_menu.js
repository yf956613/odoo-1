odoo.define('web_editor.editor', function (require) {
'use strict';

var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var core = require('web.core');
<<<<<<< HEAD
var Wysiwyg = require('web_editor.wysiwyg.root');
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
var weContext = require('web_editor.context');
var WysiwygMultizone = require('web_editor.wysiwyg.multizone');
=======
var rte = require('web_editor.rte');
var snippetsEditor = require('web_editor.snippet.editor');
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field

var _t = core._t;

<<<<<<< HEAD
var WysiwygMultizone = Wysiwyg.extend({
    assetLibs: Wysiwyg.prototype.assetLibs.concat(['website.compiled_assets_wysiwyg']),
    _getWysiwygContructor: function () {
        return odoo.__DEBUG__.services['web_editor.wysiwyg.multizone'];
    }
});

var EditorMenu = Widget.extend({
    template: 'website.editorbar',
    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
var EditorMenu = Widget.extend({
    template: 'website.editorbar',
    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
=======
var EditorMenuBar = Widget.extend({
    template: 'web_editor.editorbar',
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    events: {
        'click button[data-action=save]': '_onSaveClick',
        'click button[data-action=cancel]': '_onCancelClick',
    },
    custom_events: {
<<<<<<< HEAD
        request_save: '_onSnippetRequestSave',
        get_clean_html: '_onGetCleanHTML',
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        request_save: '_onSnippetRequestSave',
=======
        request_history_undo_record: '_onHistoryUndoRecordRequest',
        request_save: '_onSaveRequest',
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    },

    /**
     * Initializes RTE and snippets menu.
     *
     * @constructor
     */
    init: function (parent) {
        var self = this;
        var res = this._super.apply(this, arguments);
        this.rte = new rte.Class(this);
        this.rte.on('rte:start', this, function () {
            self.trigger('rte:start');
        });

        // Snippets edition
        var $editable = this.rte.editable();
        window.__EditorMenuBar_$editable = $editable; // TODO remove this hack asap
        this.snippetsMenu = new snippetsEditor.Class(this, $editable);

        return res;
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];

        core.bus.on('editor_save_request', this, this.save);
        core.bus.on('editor_discard_request', this, this.cancel);

        $('.dropdown-toggle').dropdown();

        $(document).on('keyup', function (event) {
            if ((event.keyCode === 8 || event.keyCode === 46)) {
                var $target = $(event.target).closest('.o_editable');
                if (!$target.is(':has(*:not(p):not(br))') && !$target.text().match(/\S/)) {
                    $target.empty();
                }
            }
        });
        $(document).on('click', '.note-editable', function (ev) {
            ev.preventDefault();
        });
        $(document).on('submit', '.note-editable form .btn', function (ev) {
            ev.preventDefault(); // Disable form submition in editable mode
        });
        $(document).on('hide.bs.dropdown', '.dropdown', function (ev) {
            // Prevent dropdown closing when a contenteditable children is focused
            if (ev.originalEvent
                    && $(ev.target).has(ev.originalEvent.target).length
                    && $(ev.originalEvent.target).is('[contenteditable]')) {
                ev.preventDefault();
            }
        });

        this.rte.start();

        var flag = false;
        window.onbeforeunload = function (event) {
            if (rte.history.getEditableHasUndo().length && !flag) {
                flag = true;
                _.defer(function () { flag=false; });
                return _t('This document is not saved!');
            }
        };

        // Snippets menu
        defs.push(this.snippetsMenu.insertAfter(this.$el));
        this.rte.editable().find('*').off('mousedown mouseup click');

        return $.when.apply($, defs).then(function () {
            self.trigger_up('edit_mode');
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        core.bus.off('editor_save_request', this, this._onSaveRequest);
        core.bus.off('editor_discard_request', this, this._onDiscardRequest);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Asks the user if he really wants to discard its changes (if there are
     * some of them), then simply reload the page if he wants to.
     *
     * @param {boolean} [reload=true]
     *        true if the page has to be reloaded when the user answers yes
     *        (do nothing otherwise but add this to allow class extension)
     * @returns {Deferred}
     */
    cancel: function (reload) {
        var self = this;
<<<<<<< HEAD
        var def = new Promise(function (resolve, reject) {
            if (!self.wysiwyg.isDirty()) {
                resolve();
            } else {
                var confirm = Dialog.confirm(self, _t("If you discard the current edition, all unsaved changes will be lost. You can cancel to return to the edition mode."), {
                    confirm_callback: resolve,
                });
                confirm.on('closed', self, reject);
            }
        });

||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        var def = $.Deferred();
        if (!this.wysiwyg.isDirty()) {
            def.resolve();
        } else {
            var confirm = Dialog.confirm(this, _t("If you discard the current edition, all unsaved changes will be lost. You can cancel to return to the edition mode."), {
                confirm_callback: def.resolve.bind(def),
            });
            confirm.on('closed', def, def.reject);
        }
=======
        var def = $.Deferred();
        if (!rte.history.getEditableHasUndo().length) {
            def.resolve();
        } else {
            var confirm = Dialog.confirm(this, _t("If you discard the current edition, all unsaved changes will be lost. You can cancel to return to the edition mode."), {
                confirm_callback: def.resolve.bind(def),
            });
            confirm.on('closed', def, def.reject);
        }
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        return def.then(function () {
            if (reload !== false) {
                window.onbeforeunload = null;
                return self._reload();
            }
        });
    },
    /**
     * Asks the snippets to clean themself, then saves the page, then reloads it
     * if asked to.
     *
     * @param {boolean} [reload=true]
     *        true if the page has to be reloaded after the save
     * @returns {Deferred}
     */
    save: function (reload) {
        var self = this;
<<<<<<< HEAD
        this.trigger_up('edition_will_stopped');
        return this.wysiwyg.save().then(function (result) {
            var $wrapwrap = $('#wrapwrap');
            self.editable($wrapwrap).removeClass('o_editable');
            if (result.isDirty && reload !== false) {
                // remove top padding because the connected bar is not visible
                $('body').removeClass('o_connected_user');
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        this.trigger_up('edition_will_stopped');
        return this.wysiwyg.save().then(function (dirty) {
            var $wrapwrap = $('#wrapwrap');
            self.editable($wrapwrap).removeClass('o_editable');
            if (dirty && reload !== false) {
                // remove top padding because the connected bar is not visible
                $('body').removeClass('o_connected_user');
=======
        var defs = [];
        this.trigger_up('ready_to_save', {defs: defs});
        return $.when.apply($, defs).then(function () {
            self.snippetsMenu.cleanForSave();
            return self._saveCroppedImages();
        }).then(function () {
            return self.rte.save();
        }).then(function () {
            if (reload !== false) {
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
                return self._reload();
            }
        });
    },
<<<<<<< HEAD
    /**
     * Returns the editable areas on the page.
     *
     * @param {DOM} $wrapwrap
     * @returns {jQuery}
     */
    editable: function ($wrapwrap) {
        return $wrapwrap.find('[data-oe-model]')
            .not('.o_not_editable')
            .filter(function () {
                var $parent = $(this).closest('.o_editable, .o_not_editable');
                return !$parent.length || $parent.hasClass('o_editable');
            })
            .not('link, script')
            .not('[data-oe-readonly]')
            .not('img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]')
            .not('.oe_snippet_editor')
            .not('hr, br, input, textarea')
            .add('.o_editable');
    },
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    /**
     * Returns the editable areas on the page.
     *
     * @param {DOM} $wrapwrap
     * @returns {jQuery}
     */
    editable: function ($wrapwrap) {
        return $wrapwrap.find('[data-oe-model]')
            .not('.o_not_editable')
            .filter(function () {
                return !$(this).closest('.o_not_editable').length;
            })
            .not('link, script')
            .not('[data-oe-readonly]')
            .not('img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]')
            .not('.oe_snippet_editor')
            .add('.o_editable');
    },
=======
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
<<<<<<< HEAD
     * @private
     */
    _wysiwygInstance: function () {
        var context;
        this.trigger_up('context_get', {
            callback: function (ctx) {
                context = ctx;
            },
        });
        return new WysiwygMultizone(this, {
            snippets: 'website.snippets',
            recordInfo: {
                context: context,
                data_res_model: 'website',
                data_res_id: context.website_id,
            }
        });
    },
    /**
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
     * @private
     */
    _wysiwygInstance: function () {
        return new WysiwygMultizone(this, {
            snippets: 'website.snippets',
            recordInfo: {
                context: weContext.get(),
                data_res_model: 'website',
                data_res_id: weContext.get().website_id,
            }
        });
    },
    /**
=======
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
     * Reloads the page in non-editable mode, with the right scrolling.
     *
     * @private
     * @returns {Deferred} (never resolved, the page is reloading anyway)
     */
    _reload: function () {
<<<<<<< HEAD
        $('body').addClass('o_wait_reload');
        this.wysiwyg.destroy();
        this.$el.hide();
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        $('body').addClass('o_wait_reload');
        this.wysiwyg.destroy();
=======
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        window.location.hash = 'scrollTop=' + window.document.body.scrollTop;
<<<<<<< HEAD
        window.location.reload(true);
        return new Promise(function () {});
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        if (window.location.search.indexOf(this.LOCATION_SEARCH) >= 0) {
            var regExp = new RegExp('[&?]' + this.LOCATION_SEARCH + '(=[^&]*)?', 'g');
            window.location.href = window.location.href.replace(regExp, '?');
        } else {
            window.location.reload(true);
        }
        return $.Deferred();
=======
        if (window.location.search.indexOf('enable_editor') >= 0) {
            window.location.href = window.location.href.replace(/&?enable_editor(=[^&]*)?/g, '');
        } else {
            window.location.reload(true);
        }
        return $.Deferred();
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    },
    /**
     * @private
     */
    _saveCroppedImages: function () {
        var self = this;
        var defs = _.map(this.rte.editable().find('.o_cropped_img_to_save'), function (croppedImg) {
            var $croppedImg = $(croppedImg);
            $croppedImg.removeClass('o_cropped_img_to_save');

            var resModel = $croppedImg.data('crop:resModel');
            var resID = $croppedImg.data('crop:resID');
            var cropID = $croppedImg.data('crop:id');
            var mimetype = $croppedImg.data('crop:mimetype');
            var originalSrc = $croppedImg.data('crop:originalSrc');

            var datas = $croppedImg.attr('src').split(',')[1];

            if (!cropID) {
                var name = originalSrc + '.crop';
                return self._rpc({
                    model: 'ir.attachment',
                    method: 'create',
                    args: [{
                        res_model: resModel,
                        res_id: resID,
                        name: name,
                        datas_fname: name,
                        datas: datas,
                        mimetype: mimetype,
                        url: originalSrc, // To save the original image that was cropped
                    }],
                }).then(function (attachmentID) {
                    return self._rpc({
                        model: 'ir.attachment',
                        method: 'generate_access_token',
                        args: [[attachmentID]],
                    }).then(function (access_token) {
                        $croppedImg.attr('src', '/web/image/' + attachmentID + '?access_token=' + access_token[0]);
                    });
                });
            } else {
                return self._rpc({
                    model: 'ir.attachment',
                    method: 'write',
                    args: [[cropID], {datas: datas}],
                });
            }
        });
        return $.when.apply($, defs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "Discard" button is clicked -> discards the changes.
     *
     * @private
     */
    _onCancelClick: function () {
        this.cancel();
    },
    /**
<<<<<<< HEAD
     * Get the cleaned value of the editable element.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onGetCleanHTML: function (ev) {
        ev.data.callback(this.wysiwyg.getValue({$layout: ev.data.$layout}));
    },
    /**
     * Snippet (menu_data) can request to save the document to leave the page
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
     * Snippet (menu_data) can request to save the document to leave the page
=======
     * Called when an element askes to record an history undo -> records it.
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onHistoryUndoRecordRequest: function (ev) {
        this.rte.historyRecordUndo(ev.data.$target, ev.data.event);
    },
    /**
     * Called when the "Save" button is clicked -> saves the changes.
     *
     * @private
     */
    _onSaveClick: function () {
        this.save();
    },
    /**
     * Called when a discard request is received -> discard the page content
     * changes.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onDiscardRequest: function (ev) {
        this.cancel(ev.data.reload).then(ev.data.onSuccess, ev.data.onFailure);
    },
    /**
     * Called when a save request is received -> saves the page content.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSaveRequest: function (ev) {
        ev.stopPropagation();
        this.save(ev.data.reload).then(ev.data.onSuccess, ev.data.onFailure);
    },
});

return {
    Class: EditorMenuBar,
};
});
