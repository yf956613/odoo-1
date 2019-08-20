# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ImLivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def _get_mail_channel(self, anonymous_name, previous_operator_id=None, user_id=None, country_id=None):
        self.ensure_one()
        res = super(ImLivechatChannel, self)._get_mail_channel(anonymous_name, previous_operator_id=previous_operator_id, user_id=user_id, country_id=country_id)

        if not res:
            channel_partner_to_add = []
            visitor_user = False
            if user_id:
                visitor_user = self.env['res.users'].browse(user_id)
                if visitor_user and visitor_user.active:  # valid session user (not public)
                    channel_partner_to_add.append((4, visitor_user.partner_id.id))

            mail_channel = self.env["mail.channel"].with_context(mail_create_nosubscribe=False).sudo().create({
                'channel_partner_ids': channel_partner_to_add,
                'livechat_operator_id': False,
                'livechat_channel_id': self.id,
                'anonymous_name': False if user_id else anonymous_name,
                'country_id': country_id,
                'channel_type': 'livechat',
                'name': visitor_user.name if visitor_user else anonymous_name,
                'public': 'private',
                'email_send': False,
            })
            return mail_channel.sudo().channel_info()[0]
        return res

    def get_livechat_info(self, username='Visitor'):
        self.ensure_one()
        res = {
            'available': True,
            'server_url': self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            'options': self._get_channel_infos()
        }
        res['options']['default_username'] = username
        return res
