# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMoveHashWizard(models.TransientModel):
    _inherit = 'account.move.hash.wizard'

    @api.model
    def create(self, vals):
        res = super(AccountMoveHashWizard, self).create(vals)
        
        if self.env.company._is_accounting_unalterable():
            res['hash_integrity_result'] += _('''
                    <br/>
                    <p>
                    For this report to be legally meaningful, please download your certification from <br/>
                    your customer account on Odoo.com (Only for Odoo Enterprise users). <br/>
                    </p>
                ''')
        return res
