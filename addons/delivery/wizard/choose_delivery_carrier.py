# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ChooseDeliveryCarrier(models.TransientModel):
    _name = 'choose.delivery.carrier'
    _description = 'Delivery Carrier Selection Wizard'

    def _default_available_carrier(self):
        carriers = self.env['delivery.carrier'].search([])
        partner_id = self.env.context.get('default_partner_id')
        return carriers.available_carriers(partner_id) if partner_id else carriers

    order_id = fields.Many2one('sale.order')
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id')
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string="Shipping Method",
        help="Choose the method to deliver your goods",
    )
    delivery_type = fields.Selection(related='carrier_id.delivery_type', store=False)
    delivery_price = fields.Float(string='Cost', readonly=True)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', readonly=True)
    available_carrier_ids = fields.Many2many("delivery.carrier", default=_default_available_carrier, string="Available Carriers")
    invoicing_message = fields.Text(compute='_compute_invoicing_message')

    @api.onchange('carrier_id')
    def _onchange_carrier_id(self):
        if self.delivery_type in ('fixed', 'base_on_rule'):
            self.order_id.carrier_id = self.carrier_id
            vals = self.get_delivery_price()
            self.delivery_price = vals['delivery_price']
        else:
            self.delivery_price = 0

    @api.depends('carrier_id')
    def _compute_invoicing_message(self):
        self.ensure_one()
        if self.carrier_id.invoice_policy == 'real':
            self.invoicing_message = 'The shipping price will be set once the delivery is done.'
        else:
            self.invoicing_message = ""

    def update_price(self):
        self.order_id.carrier_id = self.carrier_id
        vals = self.get_delivery_price()
        self.delivery_price = vals['delivery_price']
        return {
            'name': _('Add a shipping method'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.delivery.carrier',
            'res_id': self.id,
            'target': 'new',
        }

    @api.model_create_multi
    def create(self, vals):
        return super(ChooseDeliveryCarrier, self).create(vals)

    def get_delivery_price(self):
        self.order_id.get_delivery_price()
        if not self.order_id.delivery_rating_success and self.order_id.delivery_message:
            raise UserError(self.order_id.delivery_message)
        else:
            return {'delivery_price': self.order_id.delivery_price}

    def button_confirm(self):
        self.order_id.carrier_id = self.carrier_id
        self.order_id.delivery_price = self.delivery_price
        self.order_id.set_delivery_line()
