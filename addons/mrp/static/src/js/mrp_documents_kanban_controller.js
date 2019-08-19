odoo.define('mrp.MrpDocumentsKanbanController', function (require) {
"use strict";

/**
 * This file defines the Controller for the Documents Kanban view, which is an
 * override of the KanbanController.
 */

var DocumentViewer = require('mrp.MrpDocumentViewer');

var KanbanController = require('web.KanbanController');
var utils = require('web.utils');
var core = require('web.core');
var qweb = core.qweb;

var MrpDocumentsKanbanController = KanbanController.extend({
    events: _.extend({}, KanbanController.prototype.events, {
        'change input.o_input_file': '_onMrpAttachmentChange',
        'click .o_mrp_documents_kanban_upload': '_onUpload',
    }),
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        kanban_image_clicked: '_onKanbanPreview',
    }),
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.recordID
     * @param {Array<Object>} ev.data.recordList
     */
    _onKanbanPreview: function (ev) {
        ev.stopPropagation();
        var documents = ev.data.recordList;
        var documentID = ev.data.recordID;
        var documentViewer = new DocumentViewer(this, documents, documentID);
        documentViewer.appendTo(this.$('.o_documents_kanban_view'));
    },
});

return MrpDocumentsKanbanController;

});
