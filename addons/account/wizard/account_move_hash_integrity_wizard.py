# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMoveHashWizard(models.TransientModel):
    _name = 'account.move.hash.wizard'
    _description = 'Account Move Hash Integrity Result Wizard'
    
    hash_integrity_result = fields.Html(readonly=True)
    report_values = fields.Char(readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('report_values'):
            vals['hash_integrity_result'] = _('''<p>
                    <h2 style="font-weight: bold;">Successful test !</h2>
                    <br/>
                    <br/>
                    The journal entries are guaranteed to be in their original and inalterable state<br/>
                    From: %(start_move_name)s %(start_move_ref)s <br/>
                    To: %(end_move_name)s %(end_move_ref)s <br/>
                    </p>'''
                ) % vals.get('report_values')

        return super(AccountMoveHashWizard, self).create(vals)
