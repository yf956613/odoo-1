# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderCancel(models.TransientModel):
    _name = 'sale.order.cancel'
    _description = "Sales Order Cancel"

    sale_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    note = fields.Html('Note', readonly=True)

    def action_cancel(self):
        self.ensure_one()
        return self.sale_id.with_context({'disable_cancel_warning': True}).action_cancel()
