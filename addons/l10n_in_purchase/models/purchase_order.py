# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    journal_id = fields.Many2one('account.journal', string="Journal", states={'posted': [('readonly', True)]}, domain="[('type','=', 'purchase')]")
    l10n_in_gstin_partner_id = fields.Many2one(related="journal_id.l10n_in_gstin_partner_id")

    @api.onchange('company_id')
    def l10n_in_onchange_company_id(self):
        self.journal_id = False
