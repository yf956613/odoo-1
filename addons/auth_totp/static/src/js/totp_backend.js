odoo.define('auth_totp.backend', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('auth_totp.SetupDialog');
core.action_registry.add('totp_setup', function (parent) {
    // fixme: trigger reloading of parent somehow
    new Dialog(parent).open();
});
});
