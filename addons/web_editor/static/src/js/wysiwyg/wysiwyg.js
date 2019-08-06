odoo.define('web_editor.wysiwyg', function (require) {
'use strict';

var Widget = require('web.Widget');
var SummernoteManager = require('web_editor.rte.summernote');
var transcoder = require('web_editor.transcoder');

// core.bus
// media_dialog_demand

var Wysiwyg = Widget.extend({
    xmlDependencies: [
    ],
    defaultOptions: {
        recordInfo: {
            context: {},
        },
    },

    /**
     * @params {Object} params
     * @params {Object} params.recordInfo
     * @params {Object} params.recordInfo.context
     * @params {String} [params.recordInfo.context]
     * @params {integer} [params.recordInfo.res_id]
     * @params {String} [params.recordInfo.data_res_model]
     * @params {integer} [params.recordInfo.data_res_id]
     *   @see _onGetRecordInfo
     *   @see _getAttachmentsDomain in /wysiwyg/widgets/media.js
     * @params {Object} params.attachments
     *   @see _onGetRecordInfo
     *   @see _getAttachmentsDomain in /wysiwyg/widgets/media.js (for attachmentIDs)
     * @params {function} params.generateOptions
     *   called with the summernote configuration object used before sending to summernote
     *   @see _editorOptions
     **/
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.params = params;
    },
    /**
     * Load assets and color picker template then call summernote API
     * and replace $el by the summernote editable node.
     *
     * @override
     **/
    willStart: function () {
        new SummernoteManager(this);

        this.$target = this.$el;
        this.$target.wrap('<odoo-wysiwyg-container>');
        this.$el = this.$target.parent();
        var s = this.$target.summernote(this._editorOptions());
        this.$editor = this.$('.note-editable:first');
        this.$editor.data('wysiwyg', this);
        return this._super.apply(this, arguments);
    },

    /**
     *
     * @override
     */
    start: function () {
        this._value = this.$target.html() || this.$target.val();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a step (undo) in editor.
     */
    addHistoryStep: function () {
        console.log('addHistoryStep');
    },
    /**
     * Return the editable area.
     *
     * @returns {jQuery}
     */
    getEditable: function () {
        console.log('getEditable');
    },
    /**
     * Perform undo or redo in the editor.
     *
     * @param {integer} step
     */
    history: function (step) {
        console.log('history');
    },
    /**
     * Return true if the content has changed.
     *
     * @returns {Boolean}
     */
    isDirty: function () {
        return this._value !== (this.$target.html() || this.$target.val());
    },
    /**
     * Return true if the current node is unbreakable.
     * An unbreakable node can be removed or added but can't by split into
     * different nodes (for keypress and selection).
     * An unbreakable node can contain nodes that can be edited.
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    isUnbreakableNode: function (node) {
        console.log('isUnbreakableNode');
    },
    /**
     * Return true if the current node is editable (for keypress and selection).
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    isEditableNode: function (node) {
        console.log('isEditableNode');
    },
    /**
     * Set the focus on the element.
     */
    focus: function () {
        console.log('focus');
    },
    /**
     * Get the value of the editable element.
     *
     * @param {object} [options]
     * @param {Boolean} [options.keepPopover]
     * @param {jQueryElement} [options.$layout]
     * @returns {String}
     */
    getValue: function (options) {
        console.log('getValue ???', options);
        if (this.params['style-inline']) {
            transcoder.attachmentThumbnailToLinkImg(this.$editor);
            transcoder.fontToImg(this.$editor);
            transcoder.classToStyle(this.$editor);
        }
        return this.$editor.html();
    },
    /**
     * Save the content in the target
     *      - in init option beforeSave
     *      - receive editable jQuery DOM as attribute
     *      - called after deactivate codeview if needed
     * @returns {Promise}
     *      - resolve with true if the content was dirty
     */
    save: function () {
        var isDirty = this.isDirty();
        var html = this.getValue();
        if (this.$target.is('textarea')) {
            this.$target.val(html);
        } else {
            this.$target.html(html);
        }
        return Promise.resolve({isDirty:isDirty, html:html});
    },
    /**
     * @param {String} value
     * @param {Object} options
     * @param {Boolean} [options.notifyChange]
     * @returns {String}
     */
    setValue: function (value, options) {
        console.log('setValue ???', options);
        this.$editor.html(value);
        if (this.params['style-inline']) {
            transcoder.styleToClass(this.$editor);
            transcoder.imgToFont(this.$editor);
            transcoder.linkImgToAttachmentThumbnail(this.$editor);
        }
        this._value = (this.$target.html() || this.$target.val());
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _editorOptions: function () {
        return Object.assign({}, $.summernote.options, this.defaultOptions, this.params);
    },
});


Wysiwyg.getRange = function () {
    console.log('getRange');
};
Wysiwyg.setRange = function () {
    console.log('setRange');
};
Wysiwyg.setRangeFromNode = function () {
    console.log('setRangeFromNode');
};

return Wysiwyg;
});


odoo.define('web_editor.widget', function (require) {
'use strict';
    return {
        Dialog: require('wysiwyg.widgets.Dialog'),
        MediaDialog: require('wysiwyg.widgets.MediaDialog'),
    };
});
