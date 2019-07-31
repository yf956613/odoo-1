# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def write(self, vals):
        res = super(PricelistItem, self).write(vals)
        product = self.product_id or self.product_tmpl_id.product_variant_ids
        order = self.env['sale.order'].search([('sale_order_option_ids.product_id', 'in', product.ids), ('state', 'in', ('draft', 'sent')), ('pricelist_id', '=', self.pricelist_id.id)])
        order.write({'is_change_pricelist': True})
        return res
