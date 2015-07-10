odoo.define('web.SwitchCompany', function(require) {
    "use strict";

var core = require('web.core');
var Model = require('web.Model');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var SwitchCompany = Widget.extend({
    template: 'SwitchCompany',
    start: function() {
        var self = this;
        new Model('res.users').call('user_systray_info').then(function(res) {
            if (res) {
                self.$el.removeClass('hidden').find('span.oe_topbar_name').text(res.current_company);
                var list_parent = self.$el.find('ul.dropdown-menu');
                _.each(res.other_allowed_companies, function(company) {
                    var list_element = $('<li><a href="#" data-id=' + company[0] + '>' + company[1] + '</a></li>');
                    list_element.on('click', function(ev) {
                        ev.preventDefault();
                        self.switch_user_company(ev);
                    })
                    list_parent.append(list_element);
                });
            }
        });
        return this._super.apply(this, arguments);
    },
    switch_user_company: function(ev) {
        var company_id = $(ev.target).data('id');
        new Model('res.users').call('write', [[session.uid], {'company_id': company_id}]).then(function() {
            location.reload();
        });
    },
});

return SwitchCompany;

});
