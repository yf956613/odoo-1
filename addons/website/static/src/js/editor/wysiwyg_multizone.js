odoo.define('web_editor.wysiwyg.multizone', function (require) {
'use strict';
var Wysiwyg = require('web_editor.wysiwyg');


/**
 * HtmlEditor
 * Intended to edit HTML content. This widget uses the Wysiwyg editor
 * improved by odoo.
 *
 * class editable: o_editable
 * class non editable: o_not_editable
 *
 */
var WysiwygMultizone = Wysiwyg.extend({
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = options;
    },
    start: function () {
        this.options.toolbarHandler = $('#web_editor-top-edit');
        return this._super();
    },

    /**
     * @override
     * @returns {Promise}
     */
    save: function () {
        return this._super().then(function(res) {
            if (this.isDirty()) {
                return this.editor.save().then(function() {
                    return {isDirty: true};
                });
            } else {
                return {isDirty: false};
            }
        }.bind(this));
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getEditableArea: function() {
        return $(':o_editable');
    },

});

return WysiwygMultizone;
});
