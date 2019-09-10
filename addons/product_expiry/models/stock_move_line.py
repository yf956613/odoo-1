# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = "stock.move"
    expiration_date = fields.Boolean(
        string='Use Expiration Date', related='product_id.expiration_date')

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _default_life_date(self):
        product = self.env['product.product'].browse(self.env.context.get('default_product_id'))
        if not product.expiration_date:
            return
        return fields.Datetime.today() + datetime.timedelta(days=product.life_time)

    expiration_date = fields.Boolean(
        string='Use Expiration Date', related='product_id.expiration_date')
    life_date = fields.Datetime(string='Expiration Date',
        help='This is the date on which the goods with this Serial Number may'
        ' become dangerous and must not be consumed.',
        default=lambda self: self._default_life_date())

    def _create_and_assign_production_lot(self):
        super(StockMoveLine, self)._create_and_assign_production_lot()
        self.lot_id._update_date_values(self.life_date)
