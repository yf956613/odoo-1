# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_is_zero


class PosMakePayment(models.TransientModel):
    _name = 'pos.make.payment'
    _description = 'Point of Sale Make Payment Wizard'

    def _default_amount(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            return self.env['pos.order'].browse(active_id).amount_to_pay
        return False

    def _default_payment_method(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            order_id = self.env['pos.order'].browse(active_id)
            payment_method_ids = order_id.session_id.payment_method_ids
            cash_payment_method = order_id.session_id.cash_payment_method_id
            return (cash_payment_method or payment_method_ids[0]) if payment_method_ids else False
        return False

    def _default_payment_method_options(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            order_id = self.env['pos.order'].browse(active_id)
            return order_id.session_id.payment_method_ids
        return self.env['pos.payment.method'].search([])

    amount = fields.Float(digits=0, required=True, default=_default_amount)
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', required=True, default=_default_payment_method)
    payment_name = fields.Char(string='Payment Reference')
    payment_date = fields.Datetime(string='Payment Date', required=True, default=lambda *a: fields.Datetime.now())
    payment_method_option_ids = fields.Many2many('pos.payment.method', string='Payment Method Options', default=_default_payment_method_options)

    def check(self):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        self.ensure_one()

        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))
        currency = order.currency_id

        init_data = self.read()[0]
        if not float_is_zero(init_data['amount'], precision_rounding=currency.rounding or 0.01):
            order.add_payment({
                'pos_order_id': order.id,
                'amount': currency.round(init_data['amount']) if currency else init_data['amount'],
                'name': init_data['payment_name'],
                'payment_method_id': init_data['payment_method_id'][0],
            })

        if order.is_fully_paid:
            order.action_pos_order_paid()
            return {'type': 'ir.actions.act_window_close'}

        return self.launch_payment()

    def launch_payment(self):
        return {
            'name': _('Payment'),
            'view_mode': 'form',
            'res_model': 'pos.make.payment',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
            'context': self.env.context,
        }
