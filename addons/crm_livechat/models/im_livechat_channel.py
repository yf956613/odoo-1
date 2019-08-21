# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ImLivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def _get_mail_channel(self, anonymous_name, previous_operator_id=None, user_id=None, country_id=None):
        self.ensure_one()
        res = super(ImLivechatChannel, self)._get_mail_channel(anonymous_name, previous_operator_id=previous_operator_id, user_id=user_id, country_id=country_id)
        if not res:
            mail_channel = self._create_mail_channel(None, user_id, anonymous_name, country_id)
            return mail_channel.sudo().channel_info()[0]
        return res

    def get_livechat_info(self, username='Visitor'):
        res = super(ImLivechatChannel, self).get_livechat_info(username='Visitor')
        if not res.get('available'):
            res['available'] = True
            res['options'] = self._get_channel_infos()
            res['options']['default_username'] = username
        return res
