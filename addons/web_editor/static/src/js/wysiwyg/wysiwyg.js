odoo.define('web_editor.wysiwyg', function (require) {
'use strict';

var Widget = require('web.Widget');
var SummernoteManager = require('web_editor.rte.summernote');
var id = 0;

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
     * @options {Object} options
     * @options {Object} options.recordInfo
     * @options {Object} options.recordInfo.context
     * @options {String} [options.recordInfo.context]
     * @options {integer} [options.recordInfo.res_id]
     * @options {String} [options.recordInfo.data_res_model]
     * @options {integer} [options.recordInfo.data_res_id]
     *   @see _onGetRecordInfo
     *   @see _getAttachmentsDomain in /wysiwyg/widgets/media.js
     * @options {Object} options.attachments
     *   @see _onGetRecordInfo
     *   @see _getAttachmentsDomain in /wysiwyg/widgets/media.js (for attachmentIDs)
     * @options {function} options.generateOptions
     *   called with the summernote configuration object used before sending to summernote
     *   @see _editorOptions
     **/
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.id = ++id;
        this.options = options;
        this.options.isEditableNode = function (node) {
            return $(node).is(':o_editable');
        };
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
        return this._super();
    },

    /**
     *
     * @override
     */
    start: function () {
        this.$target.wrap('<odoo-wysiwyg-container>');
        this.$el = this.$target.parent();
        this.$target.summernote(this._editorOptions());
        this.$editor = this.$('.note-editable:first');
        this.$editor.data('wysiwyg', this);

        this._value = this.$target.html() || this.$target.val();
        return this._super();
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
        return this.$editor;
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
        this._value = value;
        if (this.$editor.is('textarea')) {
            this.$target.val(value);
        } else {
            this.$target.html(value);
        }
        this.$editor.html(value);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _editorOptions: function () {
        return Object.assign({}, $.summernote.options, this.defaultOptions, this.options);
    },
});

//--------------------------------------------------------------------------
// Public helper
//--------------------------------------------------------------------------

/**
 * @param {Node} node (editable or node inside)
 * @returns {Object}
 * @returns {Node} sc - start container
 * @returns {Number} so - start offset
 * @returns {Node} ec - end container
 * @returns {Number} eo - end offset
 */
Wysiwyg.getRange = function (node) {
    var range = $.summernote.range.create();
    return range && {
        sc: range.sc,
        so: range.so,
        ec: range.ec,
        eo: range.eo,
    };
};
/**
 * @param {Node} startNode
 * @param {Number} startOffset
 * @param {Node} endNode
 * @param {Number} endOffset
 */
Wysiwyg.setRange = function (startNode, startOffset, endNode, endOffset) {
    $(startNode).focus();
    if (endNode) {
        $.summernote.range.create(startNode, startOffset, endNode, endOffset).select();
    } else {
        $.summernote.range.create(startNode, startOffset).select();
    }
    // trigger for Unbreakable
    $(startNode.tagName ? startNode : startNode.parentNode).trigger('wysiwyg.range');
};
/**
 * @param {Node} node - dom node
 * @param {Object} [options]
 * @param {Boolean} options.begin move the range to the beginning of the first node.
 * @param {Boolean} options.end move the range to the end of the last node.
 */
Wysiwyg.setRangeFromNode = function (node, options) {
    var last = node;
    while (last.lastChild) {
        last = last.lastChild;
    }
    var first = node;
    while (first.firstChild) {
        first = first.firstChild;
    }

    if (options && options.begin && !options.end) {
        Wysiwyg.setRange(first, 0);
    } else if (options && !options.begin && options.end) {
        Wysiwyg.setRange(last, last.textContent.length);
    } else {
        Wysiwyg.setRange(first, 0, last, last.tagName ? last.childNodes.length : last.textContent.length);
    }
};


return Wysiwyg;
});


odoo.define('web_editor.widget', function (require) {
'use strict';
    return {
        Dialog: require('wysiwyg.widgets.Dialog'),
        MediaDialog: require('wysiwyg.widgets.MediaDialog'),
        LinkDialog: require('wysiwyg.widgets.LinkDialog'),
    };
});
