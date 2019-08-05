odoo.define('website.translateMenu', function (require) {
'use strict';

var utils = require('web.utils');
<<<<<<< HEAD
var TranslatorMenu = require('website.editor.menu.translate');
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
var weContext = require('web_editor.context');
var TranslatorMenu = require('website.editor.menu.translate');
=======
var weContext = require('web_editor.context');
var translate = require('web_editor.translate');
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
var websiteNavbarData = require('website.navbar');

var TranslatePageMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    assetLibs: ['web_editor.compiled_assets_wysiwyg', 'website.compiled_assets_wysiwyg'],

    actions: _.extend({}, websiteNavbarData.WebsiteNavbar.prototype.actions || {}, {
        edit_master: '_goToMasterPage',
        translate: '_startTranslateMode',
    }),

    /**
     * @override
     */
    start: function () {
        var context;
        this.trigger_up('context_get', {
            extra: true,
            callback: function (ctx) {
                context = ctx;
            },
        });
        this._mustEditTranslations = context.edit_translations;
        if (this._mustEditTranslations) {
            var url = window.location.href.replace(/([?&])&*edit_translations[^&#]*&?/, '\$1');
            window.history.replaceState({}, null, url);

            this._startTranslateMode();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Redirects the user to the same page but in the original language and in
     * edit mode.
     *
     * @private
     * @returns {Promise}
     */
    _goToMasterPage: function () {
        var lang = '/' + utils.get_cookie('frontend_lang');

        var current = document.createElement('a');
        current.href = window.location.toString();
        current.search += (current.search ? '&' : '?') + 'enable_editor=1';
        if (current.pathname.indexOf(lang) === 0) {
            current.pathname = current.pathname.replace(lang, '');
        }

        var link = document.createElement('a');
        link.href = '/website/lang/default';
        link.search += (link.search ? '&' : '?') + 'r=' + encodeURIComponent(current.pathname + current.search + current.hash);

        window.location = link.href;
        return new Promise(function () {});
    },
    /**
     * Redirects the user to the same page in translation mode (or start the
     * translator is translation mode is already enabled).
     *
     * @private
     * @returns {Promise}
     */
    _startTranslateMode: function () {
        if (!this._mustEditTranslations) {
            window.location.search += '&edit_translations';
            return new Promise(function () {});
        }
<<<<<<< HEAD

        var translator = new TranslatorMenu(this);
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        var translator = new TranslatorMenu(this);
=======
        var translator = new (translate.Class)(this, $('#wrapwrap'));
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        return translator.prependTo(document.body);
    },
});

websiteNavbarData.websiteNavbarRegistry.add(TranslatePageMenu, '.o_menu_systray:has([data-action="translate"])');
});
