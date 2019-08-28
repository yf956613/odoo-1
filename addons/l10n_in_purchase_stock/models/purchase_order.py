# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        self.journal_id = self.env['account.journal'].search([('company_id','=', self.company_id.id),
            ('type', '=', 'purchase'),
            ('l10n_in_gstin_partner_id','=', self.picking_type_id.warehouse_id.partner_id.id)],limit=1)
        return super()._onchange_picking_type_id()
