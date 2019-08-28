# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        res = super(SaleOrder, self)._onchange_warehouse_id()
        self.journal_id = self.env['account.journal'].search([('company_id','=', self.company_id.id),
        	('type', '=', 'sale'),
            ('l10n_in_gstin_partner_id','=', self.warehouse_id.partner_id.id)],limit=1)
        return res
