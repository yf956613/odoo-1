# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def send_mail(self, **kwargs):
        if self._context.get('mark_coupon_as_sent') and self.partner_ids:
            self.env[self.model].browse(self.res_id).state = 'sent'
        return super().send_mail(**kwargs)
