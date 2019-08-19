odoo.define('mrp.MrpDocumentsKanbanRecord', function (require) {
"use strict";

/**
 * This file defines the KanbanRecord for the Documents Kanban view.
 */

var KanbanRecord = require('web.KanbanRecord');
var framework = require('web.framework');
var session = require('web.session');

var MrpDocumentsKanbanRecord = KanbanRecord.extend({
    events: _.extend({}, KanbanRecord.prototype.events, {
        'click .o_mrp_download': '_onDownload',
        'click .oe_kanban_previewer': '_onImageClicked',
    }),
    _onDownload: function () {
        window.location = '/mrp/content/' + this.id;
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onImageClicked: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.trigger_up('kanban_image_clicked', {
            recordList: [this.recordData],
            recordID: this.recordData.id
        });
    },
});

return MrpDocumentsKanbanRecord;

});
