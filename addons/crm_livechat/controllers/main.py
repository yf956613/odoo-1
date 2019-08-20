# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import fields, http, SUPERUSER_ID
from odoo.http import request
from odoo.tools import html2plaintext

from odoo.addons.bus.controllers.main import BusController
from odoo.addons.im_livechat.controllers.main import LivechatController


class CrmController(http.Controller):

    @http.route('/create/lead', type='json', auth="public")
    def create_lead(self, **kwargs):
        channel_uuid = kwargs.pop('channel_uuid')
        if channel_uuid:
            channel = request.env['mail.channel'].sudo().search([('uuid', '=', channel_uuid)])
            content = html2plaintext(''.join(
                '%s: %s\n' % (message.author_id.name or channel.anonymous_name, message.body)
                for message in channel.channel_message_ids.sorted('id'))
            )
            kwargs['description'] = content
        kwargs['user_id'] = False
        partner = request.env['res.partner'].sudo().create({'name': kwargs['name'], 'email': kwargs['email_from']})
        kwargs['partner_id'] = partner.id
        lead = request.env['crm.lead'].with_user(SUPERUSER_ID).create(kwargs)
        template = request.env.ref('crm_livechat.visitor_lead_creation_email_template', raise_if_not_found=False)
        if template:
            template.with_user(SUPERUSER_ID).send_mail(lead.id, force_send=True)
        return lead.id

    @http.route('/lead/update_description', type='json', auth="public")
    def update_lead_description(self, **kwargs):
        if kwargs.get('lead_id') and kwargs.get('content'):
            content = "Visitor: " + kwargs['content']
            lead = request.env['crm.lead'].sudo().browse(kwargs.get('lead_id'))
            if lead.description:
                content = lead.description + "\n" + content
            lead.write({'description': content})


class CrmLivechatController(BusController):

    # --------------------------
    # Extends BUS Controller Poll
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            partner_id = request.env.user.partner_id.id

            if partner_id:
                channels = list(channels)
                for mail_channel in request.env['mail.channel'].search([('livechat_operator_id', 'in', [partner_id]), ('uuid', 'in', channels)]):
                    if mail_channel.message_unread_counter and (fields.datetime.now() - mail_channel.message_ids[0].create_date).total_seconds() > 120 and not mail_channel.is_lead:
                        mail_channel.is_lead = True
                        data = {
                            'type': 'operator_unavailable'
                        }
                        request.env['bus.bus'].sendone(mail_channel.uuid, data)
        return super(CrmLivechatController, self)._poll(dbname, channels, last, options)


class LivechatController(LivechatController):

    @http.route('/im_livechat/init', type='json', auth="public", cors="*")
    def livechat_init(self, channel_id):
        res = super(LivechatController, self).livechat_init(channel_id)
        if not res.get('rule'):
            res['rule'] = self.get_livechat_rule(channel_id) or {}
        if not res.get('available_for_me'):
            res['available_for_me'] = True and res.get('rule', {}).get('action') != 'hide_button'
        return res

    @http.route('/im_livechat/load_templates', type='json', auth='none', cors="*")
    def load_templates(self, **kwargs):
        res = super(LivechatController, self).load_templates(**kwargs)
        res.append(tools.file_open('crm_livechat/static/src/xml/im_livechat.xml', 'rb').read())
        return res
