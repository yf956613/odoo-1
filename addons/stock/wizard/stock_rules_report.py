# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockRulesReport(models.TransientModel):
    _name = 'stock.rules.report'
    _description = 'Stock Rules report'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses', required=True,
        help="Show the routes that apply on selected warehouses.")
    product_has_variants = fields.Boolean('Has variants', default=False, required=True)

    @api.model
    def default_get(self, fields):
        res = super(StockRulesReport, self).default_get(fields)
        product_tmpl_id = False
        if self.context.get('active_model', '') == 'product.product':
            product_id = self.context.get('active_id')
            product = self.env['product.product'].browse(product_id)
            res['product_id'] = product_id
            res['product_tmpl_id'] = product.product_tmpl_id.id
            if len(product_tmpl_id.product_variant_ids) > 1:
                res['product_has_variants'] = True
        elif self.context.get('active_model', '') == 'product.template':
            ptmpl_id = self.context.get('active_id')
            ptmpl = self.env['product.template'].browse(ptmpl_id)
            res['product_id'] = ptmpl.product_variant_id.id
            res['product_tmpl_id'] = ptmpl_id
            if len(product_tmpl_id.product_variant_ids) > 1:
                res['product_has_variants'] = True
        else:
            return res

        # VFE NOTE move to independent default function ?
        if 'warehouse_ids' in fields:
            warehouse_id = self.env['stock.warehouse'].search([], limit=1).id
            res['warehouse_ids'] = [(6, 0, [warehouse_id])]
        return res

    def _prepare_report_data(self):
        data = {
            'product_id': self.product_id.id,
            'warehouse_ids': self.warehouse_ids.ids,
        }
        return data

    def print_report(self):
        self.ensure_one()
        data = self._prepare_report_data()
        return self.env.ref('stock.action_report_stock_rule').report_action(None, data=data)
