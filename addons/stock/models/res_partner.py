# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'company.consistency.mixin']

    property_stock_customer = fields.Many2one(
        'stock.location', string="Customer Location", company_dependent=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', allowed_company_ids[0])]",
        help="The stock location used as destination when sending goods to this contact.")
    property_stock_supplier = fields.Many2one(
        'stock.location', string="Vendor Location", company_dependent=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', allowed_company_ids[0])]",
        help="The stock location used as source when receiving goods from this contact.")
    picking_warn = fields.Selection(WARNING_MESSAGE, 'Stock Picking', help=WARNING_HELP, default='no-message')
    picking_warn_msg = fields.Text('Message for Stock Picking')

    @api.model
    def create(self, vals):
        partner = super(Partner, self).create(vals)
        partner._company_consistency_check()
        return partner

    def write(self, vals):
        res = super(Partner, self).write(vals)
        if any(field in vals for field in self._company_consistency_fields()):
            self._company_consistency_check()
        return res

    def _company_consistency_m2o_property_optional_cid_fields(self):
        res = super(Partner, self)._company_consistency_m2o_property_optional_cid_fields()
        return res + ['property_stock_customer', 'property_stock_supplier']
