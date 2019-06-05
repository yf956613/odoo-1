odoo.define('auth_totp.SetupDialog', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');

var _t = core._t;

return Dialog.extend({
    template: 'auth_totp.TOTPDialog',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/auth_totp/static/src/xml/templates.xml']
    ),

    init: function (parent, options) {
        this._super(parent, _.extend({
            title: _t('Enable Enhanced Login Security'),
            buttons: [{
                text: _t("Enable"),
                click: this.proxy('_tryEnabling'),
                classes: 'btn-primary',
            }, {
                text: _t("Cancel"), close: true,
            }]
        }, options));
    },

    willStart: function () {
        var self = this;
        return Promise.all([
            this._super.apply(this, arguments),
            this._rpc({
                model: 'res.users',
                method: 'totp_generate',
                args: [this.getSession().user_id],
            }).then(function (candidate) {
                self._secret = candidate.secret;
                self._code = candidate.qrcode;
            })
        ]);
    },
    start: function () {
        var $input = this.$('input[name=code]');
        return this._super().then(function () { $input.focus(); });
    },
    _tryEnabling: function () {
        var self = this;
        var $input = this.$('input[name=code]');
        var code = Number($input.val())|0;

        console.log('tryEnabling', code);
        this._rpc({
            model: 'res.users',
            method: 'totp_try_setting',
            args: [this.getSession().user_id, this._secret, code],
        }).then(function (valid) {
            if (valid) {
                self.close();
            } else {
                $input.val('').focus()
                    .parent().addClass('o_field_invalid');
            }
        })
    }
});
});
