odoo.define('mrp.MrpDocumentViewer', function (require) {
"use strict";

var DocumentViewer = require('mail.DocumentViewer');

/**
 * This file defines the DocumentViewer for the Documents Kanban view.
 */
var MrpDocumentsDocumentViewer = DocumentViewer.extend({
    init: function (parent, attachments, activeAttachmentID) {
        this._super.apply(this, arguments);
        this.modelName = 'mrp.document';
    },
});

return MrpDocumentsDocumentViewer;

});
