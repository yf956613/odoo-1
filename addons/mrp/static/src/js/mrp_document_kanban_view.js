odoo.define('mrp.MrpDocumentsKanbanView', function (require) {
"use strict";

var MrpDocumentsKanbanController = require('mrp.MrpDocumentsKanbanController');
var MrpDocumentsKanbanRenderer = require('mrp.MrpDocumentsKanbanRenderer');
var view_registry = require('web.view_registry');
var KanbanView = require('web.KanbanView');

var MrpDocumentsKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: MrpDocumentsKanbanController,
        Renderer: MrpDocumentsKanbanRenderer,
    }),
    init: function () {
        return this._super.apply(this, arguments);
    },
});

view_registry.add('mrp_documents_kanban', MrpDocumentsKanbanView);

return MrpDocumentsKanbanView;

});
