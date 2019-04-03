odoo.define('stock.SingletonListController', function (require) {
"use strict";

var ListController = require('web.ListController');

var SingletonListController = ListController.extend({
    saveRecord: function (recordID, options) {
        var self = this;
        var superProm = this._super(recordID, options);
        superProm.then(function (data) {
            var record = self.model.localData[recordID];
            var model = record.model;
            var res_id = record.res_id;
            var foundedRecords = _.filter(self.model.localData, function (rec) {
                return rec.res_id === res_id && rec.model === model;
            });
            if (foundedRecords.length > 1) {
                self.renderer.unselectRow().then(function () {
                        self.reload().then(function () {
                            // debugger
                        });
                    });
            }
        });
        return superProm;
    },
});

return SingletonListController;

});
