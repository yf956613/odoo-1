odoo.define('mrp.document_kanban_tests', function (require) {
"use strict";

var MrpDocumentsKanbanView = require('mrp.MrpDocumentsKanbanView');
var mailTestUtils = require('mail.testUtils');
var testUtils = require('web.test_utils');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

function mockXHR(uploadXHR, customSend) {
    // the original window.XMLHttpRequest must be saved and restored after it the mock version has been used.
    window.XMLHttpRequest = class {
        constructor () {
            uploadXHR.push(this);
            this.upload = new window.EventTarget();
        }
        open() {}
        send(data) {customSend && customSend(data);}
    };
}

QUnit.module('Views');

QUnit.module('MrpDocumentsKanbanView', {
    beforeEach: function () {
        this.data = {
            'mrp.document': {
                fields: {
                    name: {string: "Name", type: 'char', default: ' '},
                    active: {string: "Active", type: 'boolean', default: true},
                    ir_attachment_id: {string: "Attachment", type: 'many2one', relation: 'ir.attachment'},
                    priority: {string: 'priority', type: 'selection',
                        selection: [['0', 'Normal'], ['1', 'Low'], ['2', 'High'], ['3', 'Very High']]},
                },
                records: [
                    {id: 1, name:'test1', ir_attachment_id: '1', priority: 2},
                    {id: 4, name:'test2', ir_attachment_id: '2', priority: 1},
                    {id: 3, name:'test3', ir_attachment_id: '3', priority: 3},
                    {id: 4, name:'test4', ir_attachment_id: '4', priority: 2},
                    {id: 5, name:'test5', ir_attachment_id: '5', priority: 1},
                    {id: 6, name:'test6', ir_attachment_id: '6', priority: 3},
                    {id: 7, name:'test7', ir_attachment_id: '7', priority: 2},
                ],
            },
        'ir.attachment': {
                fields: {
                    res_id: {string: "Resource id", type: 'integer'},
                    res_model: {string: "Model (technical)", type: 'char'},
                },
                records: [{id: 1, res_id:1, res_model: 'mrp.document'},],
            },
        };
    },
}, function () {
    QUnit.test('Mrp basic rendering', async function (assert) {
        assert.expect(9);

        var kanban = await createView({
            View: MrpDocumentsKanbanView,
            model: 'mrp.document',
            debug: true,
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });
        assert.ok(kanban, "kanban is created");

        assert.ok(kanban.$buttons.find('.o_mrp_documents_kanban_upload'),
            "the upload button should be disabled on global view");

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 7,
            "should have 7 records in the renderer");

        // check view layout
        assert.containsN(kanban, '.o_content > div', 1,
            "should have 3 columns");
        assert.containsOnce(kanban, '.o_content > .o_kanban_view',
            "should have a 'classical kanban view' column");
        assert.hasClass(kanban.$('.o_kanban_view'), 'o_mrp_documents_kanban_view',
            "should have classname 'o_mrp_documents_kanban_view'");
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 7,
            "should have 7 records in the renderer");

        // check control panel buttons
        assert.containsN(kanban, '.o_cp_buttons .btn-primary', 1,
            "should have three primary buttons");
        assert.strictEqual(kanban.$('.o_cp_buttons .btn-primary:first').text().trim(), 'Upload',
            "should have a primary 'Upload' button");

        kanban.destroy();
    });
});

});
