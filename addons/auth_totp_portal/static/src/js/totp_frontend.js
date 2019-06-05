odoo.define('auth_totp_portal.button', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var Dialog = require('auth_totp.SetupDialog');
var session = require('web.session');

publicWidget.registry.totpButton = publicWidget.Widget.extend({
    selector: '.auth_totp_portal_button',
    events: {
        click: '_onClick',
    },

    _onClick: function () {
        new Dialog(this).open().on('closed', null, function () {
            window.location.reload();
        });
    }
})
});
