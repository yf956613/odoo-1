odoo.define('crm_livechat.im_livechat', function (require) {
"use strict";

var LiveChat = require('im_livechat.im_livechat');

LiveChat.LivechatButton.include({
    /**
    * create lead for visitor when operator is not available
    *
    * @private
    * @param {Object} livechatData
    */
    _createLead: function (livechatData) {
        var self = this;
        var getEmail = prompt("There is no operator available at the moment. Please leave your email adress if you want us to reach you as soon as someone is available");
        if (getEmail) {
            return this._rpc({
                route: '/create/lead',
                params: {'name': 'visitor lead', 'email_from': getEmail, 'channel_uuid': this._livechat ? this._livechat._uuid : false},
            }).then(function (res_id) {
                livechatData['operator_pid'] = [res_id, 'Visitor Lead'];
                self.lead_id = res_id;
                self.options.default_message = "Hello, your lead has been created. comment your questions here, we will contact you soon!"
                if (!self._livechat) {
                    self._createChatWindow(livechatData);
                }
            });
        }
    },
    /**
     * @private
     * @override
     */
    _handleNotification: function  (notification) {
        if (this._livechat && (notification[0] === this._livechat.getUUID())) {
            if (notification[1].type == 'operator_unavailable') {
                this._createLead(this._livechat);
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
        this._super.apply(this, arguments);
        if (this.lead_id) {
            this._rpc({
                route: '/lead/update_description',
                params: {lead_id: this.lead_id, content: ev.data.messageData.content, channel_uuid: this._livechat._uuid},
            })
        }
    },

});
});
