odoo.define('crm_livechat.im_livechat', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var LiveChat = require('im_livechat.im_livechat');

var _t = core._t;
var QWeb = core.qweb;

LiveChat.LivechatButton.include({
    /**
    * create lead for visitor when operator is not available
    *
    * @private
    * @param {Object} livechatData
    */
    _createLead: function (livechatData) {
        var self = this;
        var $dialog = new Dialog(self, {
            title: _t('Lead Generation'),
            size: 'medium',
            $content: QWeb.render('crm_livechat.create_lead'),
            buttons: [
            {text: _t('OK'), classes: 'btn-primary',close: true, click: function () {
                var name = this.$el.find('input[name="name"]').val();
                var email = this.$el.find('input[name="email"]').val();

                if (!name || !email) {
                    return;
                }
                return this._rpc({
                    route: '/create/lead',
                    params: {'email_from': email, 'channel_uuid': this._livechat ? this._livechat._uuid : false, 'name': name},
                }).then(function (res_id) {
                    self.lead_id = res_id;
                    if (!self._livechat) {
                        self.options.default_message = _t("Hello, your lead has been created. comment your questions here, we will contact you soon!");
                        livechatData['operator_pid'] = [res_id, 'Visitor Lead'];
                        self._createChatWindow(livechatData);
                    }
                });
            }},
            {text: _t('Cancel'), close: true}]
        }).open();
    },
    /**
     * @private
     * @override
     */
    _handleNotification: function  (notification) {
        if (this._livechat && (notification[0] === this._livechat.getUUID())) {
            if (notification[1].type == 'operator_unavailable') {
                if (!this.is_lead) {
                    this._createLead();
                }
            } else {
                this._super.apply(this, arguments);
            }
        }
    },
    /**
     * @override
     * @private
     */
    _notifyNoOperator: function (livechatData) {
        this._createLead(livechatData);
    },
    /**
     * @override
     * @private
     */
    _onPostMessageChatWindow: function (ev) {
        ev.stopPropagation();
        if (this.lead_id) {
            this._rpc({
                route: '/lead/update_description',
                params: {lead_id: this.lead_id, content: ev.data.messageData.content, channel_uuid: this._livechat._uuid},
            });
        }
        return this._super.apply(this, arguments);
    },

});
});
