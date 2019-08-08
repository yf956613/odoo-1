odoo.define('web_editor.wysiwyg.iframe', function (require) {
'use strict';

var Wysiwyg = require('web_editor.wysiwyg');
var ajax = require('web.ajax');
var core = require('web.core');

var qweb = core.qweb;
var promiseCommon;
var promiseWysiwyg;


/**
 * Add option (inIframe) to load Wysiwyg in an iframe.
 **/
Wysiwyg.include({
    /**
     * Add options to load Wysiwyg in an iframe.
     *
     * @override
     * @param {boolean} options.inIframe
     **/
    init: function (parent, options) {
        this._super.apply(this, arguments);
        if (this.options.inIframe) {
            if (!this.options.iframeCssAssets) {
                this.options.iframeCssAssets = 'web_editor.wysiwyg_iframe_css_assets';
            }
            this._onUpdateIframeId = 'onLoad_' + this.id;
        }
    },
    /**
     * Load assets to inject into iframe.
     *
     * @override
     **/
    willStart: function () {
        if (!this.options.inIframe) {
            return this._super();
        }
        var debug = odoo.debug;
        odoo.debug = false;

        var defAsset;
        if (this.options.iframeCssAssets) {
            defAsset = ajax.loadAsset(this.options.iframeCssAssets);
        } else {
            defAsset = Promise.resolve({
                cssLibs: [],
                cssContents: []
            });
        }

        promiseWysiwyg = promiseWysiwyg || ajax.loadAsset('web_editor.wysiwyg_iframe_editor_assets');
        odoo.debug = debug;

        this.defAsset = Promise.all([promiseWysiwyg, defAsset]);

        this.$target = this.$el;
        return this.defAsset
            .then(this._loadIframe.bind(this))
            .then(this._super.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Create iframe, inject css and create a link with the content,
     * then inject the target inside.
     *
     * @private
     * @returns {Promise}
     */
    _loadIframe: function () {
        var self = this;
        this.$iframe = $('<iframe class="wysiwyg_iframe">').css({
            'min-height': '400px',
            width: '100%'
        });
        var avoidDoubleLoad = 0; // this bug only appears on some configurations.

        // resolve deferred on load
        var def = new Promise(function (resolve) {
            window.top[self._onUpdateIframeId] = function (Editor, _avoidDoubleLoad) {
                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg iframe double load detected');
                    return;
                }
                delete window.top[self._onUpdateIframeId];
                var $iframeTarget = self.$iframe.contents().find('#iframe_target');
                $iframeTarget.find('.o_editable').html(self.$target.val());
                self.options.toolbarHandler = $('#web_editor-top-edit', self.$iframe[0].contentWindow.document);
                self.Editor = Editor;
                resolve();
            };
        });
        this.$iframe.data('loadDef', def);  // for unit test

        // inject content in iframe

        this.$iframe.on('load', function onLoad (ev) {
            var _avoidDoubleLoad = ++avoidDoubleLoad;
            self.defAsset.then(function (assets) {
                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg immediate iframe double load detected');
                    return;
                }

                console.log(assets);

                var iframeContent = qweb.render('wysiwyg.iframeContent', {
                    assets: assets,
                    updateIframeId: self._onUpdateIframeId,
                    avoidDoubleLoad: _avoidDoubleLoad
                });
                self.$iframe[0].contentWindow.document
                    .open("text/html", "replace")
                    .write(iframeContent);
            });
        });

        this.$iframe.insertAfter(this.$target);

        return def;
    },
});

//--------------------------------------------------------------------------
// Public helper
//--------------------------------------------------------------------------

/**
 * Get the current range from Summernote.
 *
 * @param {Node} [DOM]
 * @returns {Object}
*/
Wysiwyg.getRange = function (DOM) {
    var summernote = (DOM.defaultView || DOM.ownerDocument.defaultView)._summernoteSlave || window.top.$.summernote;
    var range = summernote.range.create();
    return range && {
        sc: range.sc,
        so: range.so,
        ec: range.ec,
        eo: range.eo,
    };
};
/**
 * @param {Node} sc - start container
 * @param {Number} so - start offset
 * @param {Node} ec - end container
 * @param {Number} eo - end offset
*/
Wysiwyg.setRange = function (sc, so, ec, eo) {
    var summernote = sc.ownerDocument.defaultView._summernoteSlave || window.top.$.summernote;
    $(sc).focus();
    if (ec) {
        summernote.range.create(sc, so, ec, eo).select();
    } else {
        summernote.range.create(sc, so).select();
    }
    // trigger for Unbreakable
    $(sc.tagName ? sc : sc.parentNode).trigger('wysiwyg.range');
};

});