odoo.define('stock.SingletonListModel', function (require) {
'use strict';

var BasicModel = require('web.BasicModel');

var SingletonListModel = BasicModel.extend({
    save: function (recordID, options) {
        var self = this;
        var superProm = this._super(recordID, options);
        superProm.then(function (data) {
            // console.log(self);
            // debugger
        });
        return superProm;
    },
});

return SingletonListModel;

});
