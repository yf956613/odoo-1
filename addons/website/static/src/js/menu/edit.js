odoo.define('website.editMenu', function (require) {
'use strict';

var core = require('web.core');
<<<<<<< HEAD
var EditorMenu = require('website.editor.menu');
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
var weContext = require('web_editor.context');
var EditorMenu = require('website.editor.menu');
=======
var weContext = require('web_editor.context');
var editor = require('web_editor.editor');
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
var websiteNavbarData = require('website.navbar');

var _t = core._t;

/**
 * Adds the behavior when clicking on the 'edit' button (+ editor interaction)
 */
var EditPageMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    assetLibs: ['web_editor.compiled_assets_wysiwyg', 'website.compiled_assets_wysiwyg'],

    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions, {
        edit: '_startEditMode',
        on_save: '_onSave',
    }),
    custom_events: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.custom_events || {}, {
        content_will_be_destroyed: '_onContentWillBeDestroyed',
        content_was_recreated: '_onContentWasRecreated',
        snippet_will_be_cloned: '_onSnippetWillBeCloned',
        snippet_cloned: '_onSnippetCloned',
        snippet_dropped: '_onSnippetDropped',
    }),

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        var context;
        this.trigger_up('context_get', {
            extra: true,
            callback: function (ctx) {
                context = ctx;
            },
        });
        this._editorAutoStart = (context.editable && window.location.search.indexOf('enable_editor') >= 0);
        var url = window.location.href.replace(/([?&])&*enable_editor[^&#]*&?/, '\$1');
        window.history.replaceState({}, null, url);
    },
    /**
     * Auto-starts the editor if necessary or add the welcome message otherwise.
     *
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

<<<<<<< HEAD
        // If we auto start the editor, do not show a welcome message
        if (this._editorAutoStart) {
            return Promise.all([def, this._startEditMode()]);
        }

        // Check that the page is empty
        var $wrap = this._targetForEdition().filter('#wrapwrap.homepage').find('#wrap');
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        // Check that the page is empty
        var $wrap = this._targetForEdition().find('#wrap');
        this.$wrap = $wrap;
=======
        // If we auto start the editor, do not show a welcome message
        if (this._editorAutoStart) {
            this._startEditMode();
            return def;
        }
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field

        // Check that the page is empty
        var $wrap = $('#wrapwrap.homepage #wrap'); // TODO find this element another way
        if (!$wrap.length || $wrap.html().trim() !== '') {
            return def;
        }

        // If readonly empty page, show the welcome message
        this.$welcomeMessage = $(core.qweb.render('website.homepage_editor_welcome_message'));
        this.$welcomeMessage.css('min-height', $wrap.parent('main').height() - ($wrap.outerHeight(true) - $wrap.height()));
        $wrap.empty().append(this.$welcomeMessage);

        setTimeout(function () {
            if ($('.o_tooltip.o_animated').length) {
                $('.o_tooltip_container').addClass('show');
            }
        }, 1000); // ugly hack to wait that tooltip is loaded

        return def;
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Creates an editor instance and appends it to the DOM. Also remove the
     * welcome message if necessary.
     *
     * @private
     * @returns {Promise}
     */
    _startEditMode: function () {
        var self = this;
<<<<<<< HEAD
        if (this.editModeEnable) {
            return;
        }
        this.trigger_up('widgets_stop_request', {
            $target: this._targetForEdition(),
        });
        var $welcomeMessageParent = null;
        if (this.$welcomeMessage) {
            $welcomeMessageParent = this.$welcomeMessage.parent();
            this.$welcomeMessage.detach(); // detach from the readonly rendering before the clone by summernote
        }
        this.editModeEnable = true;
        return new EditorMenu(this).prependTo(document.body).then(function () {
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        this.trigger_up('animation_stop_demand', {
            $target: this._targetForEdition(),
        });
        if (this.$welcomeMessage) {
            this.$welcomeMessage.detach(); // detach from the readonly rendering before the clone by summernote
        }
        return new EditorMenu(this).prependTo(document.body).then(function () {
=======
        return (new (editor.Class)(this)).prependTo(document.body).then(function () {
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
            if (self.$welcomeMessage) {
<<<<<<< HEAD
                $welcomeMessageParent.append(self.$welcomeMessage); // reappend if the user cancel the edition
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
                self.$wrap.append(self.$welcomeMessage); // reappend if the user cancel the edition
=======
                self.$welcomeMessage.remove();
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
            }
<<<<<<< HEAD

            var $target = self._targetForEdition();
            self.$editorMessageElements = $target
                .find('.oe_structure.oe_empty, [data-oe-type="html"]')
                .not('[data-editor-message]')
                .attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
            new Promise(function (resolve, reject) {
                self.trigger_up('widgets_start_request', {
                    editableMode: true,
                    onSuccess: resolve,
                    onFailure: reject,
                });
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
            var $wrapwrap = self._targetForEdition();
            var $htmlEditable = $wrapwrap.find('.oe_structure.oe_empty, [data-oe-type="html"]').not('[data-editor-message]');
            $htmlEditable.attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
            var def = $.Deferred();
            self.trigger_up('animation_start_demand', {
                editableMode: true,
                onSuccess: def.resolve.bind(def),
                onFailure: def.reject.bind(def),
=======
            var $wrapwrap = $('#wrapwrap'); // TODO find this element another way
            var $htmlEditable = $wrapwrap.find('.oe_structure.oe_empty, [data-oe-type="html"]').not('[data-editor-message]');
            $htmlEditable.attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
            var def = $.Deferred();
            self.trigger_up('animation_start_demand', {
                editableMode: true,
                onSuccess: def.resolve.bind(def),
                onFailure: def.reject.bind(def),
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
            });
        });
    },
    /**
     * On save, the editor will ask to parent widgets if something needs to be
     * done first. The website navbar will receive that demand and asks to its
     * action-capable components to do something. For example, the content menu
     * handles page-related options saving. However, some users with limited
     * access rights do not have the content menu... but the website navbar
     * expects that the save action is performed. So, this empty action is
     * defined here so that all users have an 'on_save' related action.
     *
     * @private
     * @todo improve the system to somehow declare required/optional actions
     */
    _onSave: function () {},

    //--------------------------------------------------------------------------
<<<<<<< HEAD
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the target for edition.
     *
     * @private
     * @returns {JQuery}
     */
    _targetForEdition: function () {
        return $('#wrapwrap'); // TODO should know about this element another way
    },

    //--------------------------------------------------------------------------
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the target for edition.
     *
     * @private
     * @returns {JQuery}
     */
    _targetForEdition: function () {
        // in edit mode, we have .note-editable className
        return $('#wrapwrap:not(.note-editable), #wrapwrap.note-editable');
    },

    //--------------------------------------------------------------------------
=======
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when content will be destroyed in the page. Notifies the
     * WebsiteRoot that is should stop the public widgets.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onContentWillBeDestroyed: function (ev) {
        this.trigger_up('widgets_stop_request', {
            $target: ev.data.$target,
        });
    },
    /**
<<<<<<< HEAD
     * Called when content was recreated in the page. Notifies the
     * WebsiteRoot that is should start the public widgets.
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
     * Called when content was recreated in the page. Notifies the
     * WebsiteRoot that is should start the animations.
=======
     * Called when content will be recreated in the page. Notifies the
     * WebsiteRoot that is should start the animations.
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onContentWasRecreated: function (ev) {
        this.trigger_up('widgets_start_request', {
            editableMode: true,
            $target: ev.data.$target,
        });
    },
    /**
<<<<<<< HEAD
     * Called when edition will stop. Notifies the
     * WebsiteRoot that is should stop the public widgets.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditionWillStop: function (ev) {
        this.$editorMessageElements.removeAttr('data-editor-message');
        this.trigger_up('widgets_stop_request', {
            $target: this._targetForEdition(),
        });
    },
    /**
     * Called when edition was stopped. Notifies the
     * WebsiteRoot that is should start the public widgets.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditionWasStopped: function (ev) {
        this.trigger_up('widgets_start_request', {
            $target: this._targetForEdition(),
        });
        this.editModeEnable = false;
    },
    /**
     * Called when a snippet is about to be cloned in the page. Notifies the
     * WebsiteRoot that is should destroy the animations for this snippet.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetWillBeCloned: function (ev) {
        this.trigger_up('animation_stop_demand', {
            $target: ev.data.$target,
        });
    },
    /**
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
     * Called when edition will stop. Notifies the
     * WebsiteRoot that is should stop the animations.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditionWillStop: function (ev) {
        var $target = this._targetForEdition();
        $target.find('[data-editor-message]').removeAttr('data-editor-message');
        this.trigger_up('animation_stop_demand', {
            $target: $target,
        });
    },
    /**
     * Called when edition was stopped. Notifies the
     * WebsiteRoot that is should start the animations.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditionWasStopped: function (ev) {
        var $target = this._targetForEdition();
        this.trigger_up('animation_start_demand', {
            $target: $target,
        });
    },
    /**
=======
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
     * Called when a snippet is cloned in the page. Notifies the WebsiteRoot
     * that is should start the public widgets for this snippet and the snippet it
     * was cloned from.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetCloned: function (ev) {
        this.trigger_up('widgets_start_request', {
            editableMode: true,
            $target: ev.data.$target,
        });
        // TODO: remove in saas-12.5, undefined $origin will restart #wrapwrap
        if (ev.data.$origin) {
            this.trigger_up('widgets_start_request', {
                editableMode: true,
                $target: ev.data.$origin,
            });
        }
    },
    /**
     * Called when a snippet is dropped in the page. Notifies the WebsiteRoot
     * that is should start the public widgets for this snippet.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetDropped: function (ev) {
        this.trigger_up('widgets_start_request', {
            editableMode: true,
            $target: ev.data.$target,
        });
    },
});

websiteNavbarData.websiteNavbarRegistry.add(EditPageMenu, '#edit-page-menu');
});
