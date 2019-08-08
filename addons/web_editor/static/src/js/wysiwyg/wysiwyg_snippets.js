odoo.define('web_editor.wysiwyg.snippets', function (require) {
'use strict';
var editor = require('web_editor.editor');
var Wysiwyg = require('web_editor.wysiwyg');


Wysiwyg.include({
    init: function (parent, options) {
        this._super.apply(this, arguments);
        if (this.options.snippets) {
            this.options.toolbarHandler = document.body;
        }
        this.Editor = editor.Class;
    },
    start: async function () {
        if (this.options.snippets) {
            this.editor = new (this.Editor)(this, this.options);
            this.$editor = this.editor.rte.editable();
            await this.editor.prependTo(this.$editor[0].ownerDocument.body);
            this.options.toolbarHandler.append(this.editor.$el);
        } else {
            return this._super();
        }
    }
});

});
