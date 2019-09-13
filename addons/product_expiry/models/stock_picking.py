# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class Picking(models.Model):
    _inherit = "stock.picking"

    has_expired_lot = fields.Boolean(compute='_compute_has_expired_lot')

    @api.depends('move_line_ids')
    def _compute_has_expired_lot(self):
        if any(line.lot_id.product_expiry_alert for line in self.move_line_ids):
            self.has_expired_lot = True
        else:
            self.has_expired_lot = False
