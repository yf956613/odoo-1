odoo.define('mrp.MrpDocumentsKanbanRenderer', function (require) {
"use strict";

/**
 * This file defines the Renderer for the Documents Kanban view, which is an
 * override of the KanbanRenderer.
 */

var MrpDocumentsKanbanRecord = require('mrp.MrpDocumentsKanbanRecord');

var KanbanRenderer = require('web.KanbanRenderer');

var MrpDocumentsKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: MrpDocumentsKanbanRecord,
    }),

    /**
     * @override
     */
    start: function () {
        this.$el.addClass('o_mrp_documents_kanban_view position-relative align-content-start flex-grow-1 flex-shrink-1');
        return this._super.apply(this, arguments);
    },
});

return MrpDocumentsKanbanRenderer;

});
