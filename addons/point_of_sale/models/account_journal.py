# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    pos_payment_method_ids = fields.One2many('pos.payment.method', 'cash_journal_id', string='Point of Sale Payment Methods')

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        session_id = self.env.context.get('pos_session_id', False)
        if session_id:
            session = self.env['pos.session'].browse(session_id)
            if session:
                args += [('id', 'in', session.payment_method_ids.filtered(lambda pm: pm.is_cash_count).mapped('cash_journal_id').ids)]
        return super(AccountJournal, self)._search(args=args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
