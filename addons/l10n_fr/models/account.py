# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.addons.account.models.account_move import INTEGRITY_HASH_LINE_FIELDS


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        if set(vals).intersection(INTEGRITY_HASH_LINE_FIELDS):
            if any(l.company_id._is_accounting_unalterable() and l.move_id.state == 'posted' for l in self):
                raise UserError(_("According to the French law, you cannot modify a journal item in order for its posted data to be updated or deleted. Unauthorized field: %s.") % ', '.join(INTEGRITY_HASH_LINE_FIELDS))
        return super(AccountMoveLine, self).write(vals)
