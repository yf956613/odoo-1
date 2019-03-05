# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import itertools

from odoo import models, _

from odoo.addons.iap.models.iap import InsufficientCreditError

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _get_default_sms_recipients(self):
        """ This method will likely need to be overriden by inherited models.
               :returns partners: recordset of res.partner
        """
        partners = self.env['res.partner']
        if hasattr(self, 'partner_id'):
            partners |= self.mapped('partner_id')
        if hasattr(self, 'partner_ids'):
            partners |= self.mapped('partner_ids')
        return partners

    def message_post_send_sms(self, sms_message, numbers=None, partners=None, note_msg=None):
        """ Send an SMS text message and post an internal note in the chatter if successfull
            :param sms_message: plaintext message to send by sms
            :param numbers: the numbers to send to, if none are given it will take those
                                from partners or _get_default_sms_recipients
            :param partners: the recipients partners, if none are given it will take those
                                from _get_default_sms_recipients, this argument
                                is ignored if numbers is defined
            :param note_msg: message to log in the chatter, if none is given a default one
                             containing the sms_message is logged
        """

        if not numbers:
            if not partners:
                partners = self._get_default_sms_recipients()

                # Collect numbers, we will consider the message to be sent if at least one number can be found
                numbers = list(set([i.mobile or i.phone for i in partners if i.mobile or i.phone]))

        mail_message = note_msg or sms_message

        for thread, partner, number in itertools.zip_longest(self, partners, numbers, fillvalue=False):
            message_id = thread.message_post(body=mail_message, message_type='sms')
            sms = self.env['sms.sms'].create({
                'user_id': self.env.user.id,
                'partner_id': partner.id if partner else False,
                'number': number,
                'body': sms_message,
                'message_id': message_id.id
            })
            sms.send_sms()

        return False
