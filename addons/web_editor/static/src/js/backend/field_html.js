odoo.define('web_editor.backend', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var basic_fields = require('web.basic_fields');
var config = require('web.config');
var core = require('web.core');
<<<<<<< HEAD
var Wysiwyg = require('web_editor.wysiwyg.root');
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
var Wysiwyg = require('web_editor.wysiwyg');
=======
var session = require('web.session');
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
var field_registry = require('web.field_registry');
<<<<<<< HEAD
// must wait for web/ to add the default html widget, otherwise it would override the web_editor one
require('web._field_registry');
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
=======
var SummernoteManager = require('web_editor.rte.summernote');
var transcoder = require('web_editor.transcoder');
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field

var _lt = core._lt;
var TranslatableFieldMixin = basic_fields.TranslatableFieldMixin;
var QWeb = core.qweb;
<<<<<<< HEAD
var assetsLoaded;
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
=======
var _t = core._t;

>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field

/**
 * FieldTextHtmlSimple Widget
 * Intended to display HTML content. This widget uses the summernote editor
 * improved by odoo.
 *
 */
<<<<<<< HEAD
var FieldHtml = basic_fields.DebouncedField.extend(TranslatableFieldMixin, {
    description: _lt("Html"),
    className: 'oe_form_field oe_form_field_html',
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
var FieldHtml = basic_fields.DebouncedField.extend(TranslatableFieldMixin, {
    className: 'oe_form_field oe_form_field_html',
=======
var FieldTextHtmlSimple = basic_fields.DebouncedField.extend(TranslatableFieldMixin, {
    className: 'oe_form_field oe_form_field_html_text',
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    supportedFieldTypes: ['html'],

    /**
     * @override
     */
<<<<<<< HEAD
    willStart: function () {
        var self = this;
        this.isRendered = false;
        this._onUpdateIframeId = 'onLoad_' + _.uniqueId('FieldHtml');
        var defAsset;
        if (this.nodeOptions.cssReadonly) {
            defAsset = ajax.loadAsset(this.nodeOptions.cssReadonly);
        }

        if (!assetsLoaded) { // avoid flickering when begin to edit
            assetsLoaded = new Promise(function (resolve) {
                var wysiwyg = new Wysiwyg(self, {});
                wysiwyg.attachTo($('<textarea>')).then(function () {
                    wysiwyg.destroy();
                    resolve();
                });
            });
        }

        return Promise.all([this._super(), assetsLoaded, defAsset]);
    },
    /**
     * @override
     */
    destroy: function () {
        delete window.top[this._onUpdateIframeId];
        if (this.$iframe) {
            this.$iframe.remove();
        }
        this._super();
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    willStart: function () {
        this._onUpdateIframeId = 'onLoad_' + _.uniqueId('FieldHtml');
        var defAsset = this.nodeOptions.cssReadonly && ajax.loadAsset(this.nodeOptions.cssReadonly);
        return $.when(this._super().then(Wysiwyg.prepare.bind(Wysiwyg, this)), defAsset);
    },
    /**
     * @override
     */
    destroy: function () {
        delete window.top[this._onUpdateIframeId];
        if (this.$iframe) {
            this.$iframe.remove();
        }
        this._super();
=======
    start: function () {
        new SummernoteManager(this);
        return this._super.apply(this, arguments);
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Summernote doesn't notify for changes done in code mode. We override
     * commitChanges to manually switch back to normal mode before committing
     * changes, so that the widget is aware of the changes done in code mode.
     *
     * @override
     */
    commitChanges: function () {
<<<<<<< HEAD
        var self = this;
        if (this.mode == "readonly" || !this.isRendered) {
            return this._super();
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        var self = this;
        if (!this.wysiwyg) {
            return this._super();
=======
        // switch to WYSIWYG mode if currently in code mode to get all changes
        if (config.debug && this.mode === 'edit') {
            var layoutInfo = this.$textarea.data('layoutInfo');
            $.summernote.pluginEvents.codeview(undefined, undefined, layoutInfo, false);
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        }
<<<<<<< HEAD
        var _super = this._super.bind(this);
        return this.wysiwyg.save().then(function (result) {
            self._isDirty = result.isDirty;
            _super();
        });
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        var _super = this._super.bind(this);
        return this.wysiwyg.save().then(function (isDirty, html) {
            self._isDirty = isDirty;
            _super();
        });
=======
        if (this._getValue() !== this.value) {
            this._isDirty = true;
        }
        this._super.apply(this, arguments);
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    },
    /**
     * @override
     */
    isSet: function () {
        return this.value && this.value !== "<p><br/></p>" && this.value.match(/\S/);
    },
    /**
     * @override
     */
    getFocusableElement: function () {
        return this.$content || this._super.apply(this, arguments);
    },
    /**
     * Do not re-render this field if it was the origin of the onchange call.
     *
     * @override
     */
    reset: function (record, event) {
        this._reset(record, event);
        if (!event || event.target !== this) {
            if (this.mode === 'edit') {
                this.$content.html(this._textToHtml(this.value));
            } else {
                this._renderReadonly();
            }
        }
        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the domain for attachments used in media dialog.
     * We look for attachments related to the current document. If there is a value for the model
     * field, it is used to search attachments, and the attachments from the current document are
     * filtered to display only user-created documents.
     * In the case of a wizard such as mail, we have the documents uploaded and those of the model
     *
     * @private
     * @returns {Array} "ir.attachment" odoo domain.
     */
    _getAttachmentsDomain: function () {
        var domain = ['|', ['id', 'in', _.pluck(this.attachments, 'id')]];
        var attachedDocumentDomain = [
            '&',
            ['res_model', '=', this.model],
            ['res_id', '=', this.res_id|0]
        ];
        // if the document is not yet created, do not see the documents of other users
        if (!this.res_id) {
            attachedDocumentDomain.unshift('&');
            attachedDocumentDomain.push(['create_uid', '=', session.uid]);
        }
        if (this.recordData.res_model || this.recordData.model) {
            var relatedDomain = ['&',
                ['res_model', '=', this.recordData.res_model || this.recordData.model],
                ['res_id', '=', this.recordData.res_id|0]];
            if (!this.recordData.res_id) {
                relatedDomain.unshift('&');
                relatedDomain.push(['create_uid', '=', session.uid]);
            }
            domain = domain.concat(['|'], attachedDocumentDomain, relatedDomain);
        } else {
            domain = domain.concat(attachedDocumentDomain);
        }
        return domain;
    },
    /**
     * @private
     * @returns {Object} the summernote configuration
     */
    _getSummernoteConfig: function () {
        var summernoteConfig = {
            model: this.model,
            id: this.res_id,
            focus: false,
            height: 180,
            toolbar: [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['insert', this.nodeOptions['no-attachment'] ? ['link'] : ['link', 'picture']],
                ['history', ['undo', 'redo']]
            ],
            prettifyHtml: false,
            styleWithSpan: false,
            inlinemedia: ['p'],
            lang: "odoo",
            onChange: this._doDebouncedAction.bind(this),
            disableDragAndDrop: !!this.nodeOptions['no-attachment'],
        };

<<<<<<< HEAD
        // by default this is synchronous because the assets are already loaded in willStart
        // but it can be async in the case of options such as iframe, snippets...
        return this.wysiwyg.attachTo(this.$target).then(function () {
            self.$content = self.wysiwyg.$editor;
            self._onLoadWysiwyg();
            self.isRendered = true;
        });
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        // by default this is synchronous because the assets are already loaded in willStart
        // but it can be async in the case of options such as iframe, snippets...
        return this.wysiwyg.attachTo(this.$target).then(function () {
            self.$content = self.wysiwyg.$el;
            self._onLoadWysiwyg();
        });
=======
        var fieldNameAttachment =_.chain(this.recordData)
            .pairs()
            .find(function (value) {
                return _.isObject(value[1]) && value[1].model === "ir.attachment";
            })
            .first()
            .value();

        if (fieldNameAttachment) {
            this.fieldNameAttachment = fieldNameAttachment;
            this.attachments = [];
            summernoteConfig.onUpload = this._onUpload.bind(this);
        }
        summernoteConfig.getMediaDomain = this._getAttachmentsDomain.bind(this);


        if (config.debug) {
            summernoteConfig.toolbar.splice(7, 0, ['view', ['codeview']]);
        }
        return summernoteConfig;
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    },
    /**
     * @override
     * @private
     */
    _getValue: function () {
        if (this.nodeOptions['style-inline']) {
            transcoder.attachmentThumbnailToLinkImg(this.$content);
            transcoder.fontToImg(this.$content);
            transcoder.classToStyle(this.$content);
        }
        return this.$content.html();
    },
    /**
     * trigger_up 'field_changed' add record into the "ir.attachment" field found in the view.
     * This method is called when an image is uploaded by the media dialog.
     *
     * For e.g. when sending email, this allows people to add attachments with the content
     * editor interface and that they appear in the attachment list.
     * The new documents being attached to the email, they will not be erased by the CRON
     * when closing the wizard.
     *
     * @private
     */
    _onUpload: function (attachments) {
        var self = this;
        attachments = _.filter(attachments, function (attachment) {
            return !_.findWhere(self.attachments, {id: attachment.id});
        });
        if (!attachments.length) {
            return;
        }
        this.attachments = this.attachments.concat(attachments);
        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: _.object([this.fieldNameAttachment], [{
                operation: 'ADD_M2M',
                ids: attachments
            }])
        });
    },
    /**
     * @override
     * @private
     */
    _renderEdit: function () {
        this.$textarea = $('<textarea>');
        this.$textarea.appendTo(this.$el);
        this.$textarea.summernote(this._getSummernoteConfig());
        this.$content = this.$('.note-editable:first');
        this.$content.html(this._textToHtml(this.value));
        // trigger a mouseup to refresh the editor toolbar
        var mouseupEvent = $.Event('mouseup', {'setStyleInfoFromEditable': true});
        this.$content.trigger(mouseupEvent);
        if (this.nodeOptions['style-inline']) {
            transcoder.styleToClass(this.$content);
            transcoder.imgToFont(this.$content);
            transcoder.linkImgToAttachmentThumbnail(this.$content);
        }
        // reset the history (otherwise clicking on undo before editing the
        // value will empty the editor)
        var history = this.$content.data('NoteHistory');
        if (history) {
            history.reset();
        }
        this.$('.note-toolbar').append(this._renderTranslateButton());
    },
    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        var self = this;
        this.$el.empty();
<<<<<<< HEAD
        var resolver;
        var def = new Promise(function (resolve) {
            resolver = resolve;
        });
        if (this.nodeOptions.cssReadonly) {
            this.$iframe = $('<iframe class="o_readonly"/>');
            this.$iframe.appendTo(this.$el);

            var avoidDoubleLoad = 0; // this bug only appears on some computers with some chrome version.

            // inject content in iframe

            this.$iframe.data('loadDef', def); // for unit test
            window.top[this._onUpdateIframeId] = function (_avoidDoubleLoad) {
                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg iframe double load detected');
                    return;
                }
                self.$content = $('#iframe_target', self.$iframe[0].contentWindow.document.body);
                resolver();
            };

            this.$iframe.on('load', function onLoad() {
                var _avoidDoubleLoad = ++avoidDoubleLoad;
                ajax.loadAsset(self.nodeOptions.cssReadonly).then(function (asset) {
                    if (_avoidDoubleLoad !== avoidDoubleLoad) {
                        console.warn('Wysiwyg immediate iframe double load detected');
                        return;
                    }
                    var cwindow = self.$iframe[0].contentWindow;
                    cwindow.document
                        .open("text/html", "replace")
                        .write(
                            '<head>' +
                                '<meta charset="utf-8"/>' +
                                '<meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"/>\n' +
                                '<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no"/>\n' +
                                _.map(asset.cssLibs, function (cssLib) {
                                    return '<link type="text/css" rel="stylesheet" href="' + cssLib + '"/>';
                                }).join('\n') + '\n' +
                                _.map(asset.cssContents, function (cssContent) {
                                    return '<style type="text/css">' + cssContent + '</style>';
                                }).join('\n') + '\n' +
                            '</head>\n' +
                            '<body class="o_in_iframe o_readonly">\n' +
                                '<div id="iframe_target">' + value + '</div>\n' +
                                '<script type="text/javascript">' +
                                    'if (window.top.' + self._onUpdateIframeId + ') {' +
                                        'window.top.' + self._onUpdateIframeId + '(' + _avoidDoubleLoad + ')' +
                                    '}' +
                                '</script>\n' +
                            '</body>');

                    var height = cwindow.document.body.scrollHeight;
                    self.$iframe.css('height', Math.max(30, Math.min(height, 500)) + 'px');
                });
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field

        var def = $.Deferred();
        if (this.nodeOptions.cssReadonly) {
            this.$iframe = $('<iframe class="o_readonly"/>');
            this.$iframe.appendTo(this.$el);

            var avoidDoubleLoad = 0; // this bug only appears on some computers with some chrome version.

            // inject content in iframe

            this.$iframe.data('load-def', def); // for unit test
            window.top[this._onUpdateIframeId] = function (_avoidDoubleLoad) {
                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg iframe double load detected');
                    return;
                }
                self.$content = $('#iframe_target', self.$iframe[0].contentWindow.document.body);
                def.resolve();
            };

            this.$iframe.one('load', function onLoad() {
                var _avoidDoubleLoad = ++avoidDoubleLoad;
                ajax.loadAsset(self.nodeOptions.cssReadonly).then(function (asset) {
                    if (_avoidDoubleLoad !== avoidDoubleLoad) {
                        console.warn('Wysiwyg immediate iframe double load detected');
                        return;
                    }
                    var cwindow = self.$iframe[0].contentWindow;
                    cwindow.document
                        .open("text/html", "replace")
                        .write(
                            '<head>' +
                                '<meta charset="utf-8"/>' +
                                '<meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"/>\n' +
                                '<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no"/>\n' +
                                _.map(asset.cssLibs, function (cssLib) {
                                    return '<link type="text/css" rel="stylesheet" href="' + cssLib + '"/>';
                                }).join('\n') + '\n' +
                                _.map(asset.cssContents, function (cssContent) {
                                    return '<style type="text/css">' + cssContent + '</style>';
                                }).join('\n') + '\n' +
                            '</head>\n' +
                            '<body class="o_in_iframe o_readonly">\n' +
                                '<div id="iframe_target">' + value + '</div>\n' +
                                '<script type="text/javascript">' +
                                    'if (window.top.' + self._onUpdateIframeId + ') {' +
                                        'window.top.' + self._onUpdateIframeId + '(' + _avoidDoubleLoad + ')' +
                                    '}' +
                                '</script>\n' +
                            '</body>');

                    var height = cwindow.document.body.scrollHeight;
                    self.$iframe.css('height', Math.max(30, Math.min(height, 500)) + 'px');
                });
=======
        if (this.nodeOptions['style-inline']) {
            var $iframe = $('<iframe class="o_readonly"/>');
            $iframe.on('load', function () {
                self.$content = $($iframe.contents()[0]).find("body");
                self.$content.html(self._textToHtml(self.value));
                self._resize();
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
            });
            $iframe.appendTo(this.$el);
        } else {
            this.$content = $('<div class="o_readonly"/>');
            this.$content.html(this._textToHtml(this.value));
            this.$content.appendTo(this.$el);
<<<<<<< HEAD
            resolver();
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
            def.resolve();
=======
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        }
    },
    /**
     * Sets the height of the iframe.
     *
     * @private
     */
    _resize: function () {
        var height = this.$content[0] ? this.$content[0].scrollHeight : 0;
        this.$('iframe').css('height', Math.max(30, Math.min(height, 500)) + 'px');
    },
    /**
     * @private
     * @param {string} text
     * @returns {string} the text converted to html
     */
    _textToHtml: function (text) {
        var value = text || "";
        try {
            $(text)[0].innerHTML; // crashes if text isn't html
        } catch (e) {
            if (value.match(/^\s*$/)) {
                value = '<p><br/></p>';
            } else {
                value = "<p>" + value.split(/<br\/?>/).join("<br/></p><p>") + "</p>";
                value = value
                            .replace(/<p><\/p>/g, '')
                            .replace('<p><p>', '<p>')
                            .replace('<p><p ', '<p ')
                            .replace('</p></p>', '</p>');
            }
        }
        return value;
    },
    /**
     * @override
     * @private
     * @returns {jQueryElement}
     */
    _renderTranslateButton: function () {
        if (_t.database.multi_lang && this.field.translate && this.res_id) {
            return $(QWeb.render('web_editor.FieldTextHtml.button.translate', {widget: this}))
                .on('click', this._onTranslate.bind(this));
        }
        return $();
    },

});

var FieldTextHtml = AbstractField.extend({
    template: 'web_editor.FieldTextHtml',
    supportedFieldTypes: ['html'],

    start: function () {
        var self = this;

        this.editorLoadedDeferred = $.Deferred();
        this.contentLoadedDeferred = $.Deferred();
        this.callback = _.uniqueId('FieldTextHtml_');
        window.odoo[this.callback+"_editor"] = function (EditorBar) {
            setTimeout(function () {
                self.on_editor_loaded(EditorBar);
            },0);
        };
        window.odoo[this.callback+"_content"] = function () {
            self.on_content_loaded();
        };
        window.odoo[this.callback+"_updown"] = null;
        window.odoo[this.callback+"_downup"] = function () {
            self.resize();
        };

        // init jqery objects
        this.$iframe = this.$el.find('iframe');
        this.document = null;
        this.$body = $();
        this.$content = $();

        this.$iframe.css('min-height', 'calc(100vh - 360px)');

        // init resize
        this.resize = function resize() {
            if (self.mode === 'edit') {
                if ($("body").hasClass("o_field_widgetTextHtml_fullscreen")) {
                    self.$iframe.css('height', (document.body.clientHeight - self.$iframe.offset().top) + 'px');
                } else {
                    self.$iframe.css("height", (self.$body.find("#oe_snippets").length ? 500 : 300) + "px");
                }
            }
        };
        $(window).on('resize', this.resize);

        this.old_initialize_content();
        var def = this._super.apply(this, arguments);
        return def;
    },
    getDatarecord: function () {
        return this.recordData;
    },
    get_url: function (_attr) {
        var src = this.nodeOptions.editor_url || "/mass_mailing/field/email_template";
        var k;
        var datarecord = this.getDatarecord();
        var attr = {
            'model': this.model,
            'field': this.name,
            'res_id': datarecord.id || '',
            'callback': this.callback
        };
        _attr = _attr || {};

        if (this.nodeOptions['style-inline']) {
            attr.inline_mode = 1;
        }
        if (this.nodeOptions.snippets) {
            attr.snippets = this.nodeOptions.snippets;
        }
        if (this.nodeOptions.template) {
            attr.template = this.nodeOptions.template;
        }
        if (this.mode === "edit") {
            attr.enable_editor = 1;
        }
        if (session.debug) {
            attr.debug = session.debug;
        }

        for (k in _attr) {
            attr[k] = _attr[k];
        }

        if (src.indexOf('?') === -1) {
            src += "?";
        }

        for (k in attr) {
            if (attr[k] !== null) {
                src += "&"+k+"="+(_.isBoolean(attr[k]) ? +attr[k] : attr[k]);
            }
        }

        // delete datarecord[this.name];
        src += "&datarecord="+ encodeURIComponent(JSON.stringify(datarecord));
        return src;
    },
    old_initialize_content: function () {
        this.$el.closest('.modal-body').css('max-height', 'none');
        this.$iframe = this.$el.find('iframe');
        this.document = null;
        this.$body = $();
        this.$content = $();
        this.editor = false;
        window.odoo[this.callback+"_updown"] = null;
        this.$iframe.attr("src", this.get_url());
    },
    on_content_loaded: function () {
        var self = this;
        this.document = this.$iframe.contents()[0];
        this.$body = $("body", this.document);
        this.$content = this.$body.find("#editable_area");
        this.render();
        this.add_button();
        this.contentLoadedDeferred.resolve();
        setTimeout(self.resize, 0);
    },
    on_editor_loaded: function (EditorBar) {
        var self = this;
        this.editor = EditorBar;
        if (this.value && window.odoo[self.callback+"_updown"] && !(this.$content.html()||"").length) {
            this.render();
        }
        this.editorLoadedDeferred.resolve();
        setTimeout(function () {
            setTimeout(self.resize,0);
        }, 0);
    },
    add_button: function () {
        var self = this;
        var $to = this.$body.find("#web_editor-top-edit, #wrapwrap").first();

        $(QWeb.render('web_editor.FieldTextHtml.fullscreen'))
            .appendTo($to)
            .on('click', '.o_fullscreen', function () {
                $("body").toggleClass("o_field_widgetTextHtml_fullscreen");
                var full = $("body").hasClass("o_field_widgetTextHtml_fullscreen");
                self.$iframe.parents().toggleClass('o_form_fullscreen_ancestor', full);
                $(window).trigger("resize"); // induce a resize() call and let other backend elements know (the navbar extra items management relies on this)
            });

        this.$body.on('click', '[data-action="cancel"]', function (event) {
            event.preventDefault();
            self.old_initialize_content();
        });
<<<<<<< HEAD
        var $toolbar = this.$content.find('.note-toolbar');
        $toolbar.css('position', 'relative');
        $toolbar.append($button);
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        var $toolbar = this.$content.closest('.note-editor').find('.note-toolbar');
        $toolbar.css('position', 'relative');
        $toolbar.append($button);
=======
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
    },
    render: function () {
        var value = (this.value || "").replace(/^<p[^>]*>(\s*|<br\/?>)<\/p>$/, '');
        if (!this.$content) {
            return;
        }
        if (this.mode === "edit") {
            if (window.odoo[this.callback+"_updown"]) {
                // FIXME
                // window.odoo[this.callback+"_updown"](value, this.view.get_fields_values(), this.name);
                this.resize();
            }
        } else {
            this.$content.html(value);
            if (this.$iframe[0].contentWindow) {
                this.$iframe.css("height", (this.$body.height()+20) + "px");
            }
        }
    },
    has_no_value: function () {
        return this.value === false || !this.$content.html() || !this.$content.html().match(/\S/);
    },
    destroy: function () {
        $(window).off('resize', this.resize);
        delete window.odoo[this.callback+"_editor"];
        delete window.odoo[this.callback+"_content"];
        delete window.odoo[this.callback+"_updown"];
        delete window.odoo[this.callback+"_downup"];
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Set the value when the widget is fully loaded (content + editor).
     *
     * @override
     */
    commitChanges: function () {
        var self = this;
        var result = this._super.bind(this, arguments);
        if (this.mode === 'readonly') {
            return;
        }
        return $.when(this.contentLoadedDeferred, this.editorLoadedDeferred, result).then(function () {
            // switch to WYSIWYG mode if currently in code mode to get all changes
            if (config.debug && self.editor.rte) {
                var layoutInfo = self.editor.rte.editable().data('layoutInfo');
                $.summernote.pluginEvents.codeview(undefined, undefined, layoutInfo, false);
            }
            var $ancestors = self.$iframe.filter(':not(:visible)').parentsUntil(':visible').addBack();
            var ancestorsStyle = [];
            // temporarily force displaying iframe (needed for firefox)
            _.each($ancestors, function (el) {
                var $el = $(el);
                ancestorsStyle.unshift($el.attr('style') || null);
                $el.css({display: 'initial', visibility: 'hidden', height: 1});
            });
            self.editor.snippetsMenu && self.editor.snippetsMenu.cleanForSave();
            _.each($ancestors, function (el) {
                var $el = $(el);
                $el.attr('style', ancestorsStyle.pop());
            });
            self._setValue(self.$content.html());
        });
    },
});

field_registry
    .add('html', FieldTextHtmlSimple)
    .add('html_frame', FieldTextHtml);

return {
    FieldTextHtmlSimple: FieldTextHtmlSimple,
    FieldTextHtml: FieldTextHtml,
};
});
