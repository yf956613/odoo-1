odoo.define('stock.SingletonListView', function (require) {
'use strict';

var ListView = require('web.ListView');
var SingletonListController = require('stock.SingletonListController');
var SingletonListModel = require('stock.SingletonListModel');
var SingletonListRenderer = require('stock.SingletonListRenderer');
var viewRegistry = require('web.view_registry');

var SingletonListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        // Controller: SingletonListController,
        // Model: SingletonListModel,
        // Renderer: SingletonListRenderer,
    }),
});

viewRegistry.add('singleton_list', SingletonListView);

});
