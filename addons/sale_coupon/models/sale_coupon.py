# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import random
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class SaleCoupon(models.Model):
    _name = 'sale.coupon'
    _description = "Sales Coupon"
    _rec_name = 'code'

    @api.model
    def _generate_code(self):
        """Generate a 20 char long pseudo-random string of digits for barcode
        generation.

        A decimal serialisation is longer than a hexadecimal one *but* it
        generates a more compact barcode (Code128C rather than Code128A).

        Generate 8 bytes (64 bits) barcodes as 16 bytes barcodes are not 
        compatible with all scanners.
         """
        return str(random.getrandbits(64))

    code = fields.Char(default=_generate_code, required=True, readonly=True)
    expiration_date = fields.Date('Expiration Date', compute='_compute_expiration_date')
    state = fields.Selection([
        ('reserved', 'Pending'),
        ('new', 'Valid'),
        ('sent', 'Sent'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ('cancel', 'Cancelled')
    ], required=True, default='new')
    partner_id = fields.Many2one('res.partner', "For Customer")
    program_id = fields.Many2one('sale.coupon.program', "Program")
    order_id = fields.Many2one('sale.order', 'Order Reference', readonly=True,
        help="The sales order from which coupon is generated")
    sales_order_id = fields.Many2one('sale.order', 'Used in', readonly=True,
        help="The sales order on which the coupon is applied")
    discount_line_product_id = fields.Many2one('product.product', related='program_id.discount_line_product_id', readonly=False,
        help='Product used in the sales order to apply the discount.')

    _sql_constraints = [
        ('unique_coupon_code', 'unique(code)', 'The coupon code must be unique!'),
    ]

    def _compute_expiration_date(self):
        for coupon in self.filtered(lambda x: x.program_id.validity_duration > 0):
            coupon.expiration_date = (coupon.create_date + relativedelta(days=coupon.program_id.validity_duration)).date()

    def _check_coupon_code(self, order):
        message = {}
        applicable_programs = order._get_applicable_programs()
        if self.state == 'used':
            message = {'error': _('This coupon %s has been used.') % (self.code)}
        elif self.state == 'reserved':
            message = {'error': _('This coupon %s exists but the origin sales order is not validated yet.') % (self.code)}
        elif self.state == 'cancel':
            message = {'error': _('This coupon %s is cancelled.') % (self.code)}
        elif self.state == 'expired' or (self.expiration_date and self.expiration_date < order.date_order.date()):
            message = {'error': _('This coupon %s has been expired.') % (self.code)}
        # Minimum requirement should not be checked if the coupon got generated by a promotion program (the requirement should have only be checked to generate the coupon)
        elif self.program_id.program_type == 'coupon_program' and not self.program_id._filter_on_mimimum_amount(order):
            message = {'error': _('A minimum of %s %s should be purchased to get the reward') % (self.program_id.rule_minimum_amount, self.program_id.currency_id.name)}
        elif not self.program_id.active:
            message = {'error': _('The coupon program for %s is in draft or closed state') % (self.code)}
        elif self.partner_id and self.partner_id != order.partner_id:
            message = {'error': _('Invalid partner.')}
        elif self.program_id in order.applied_coupon_ids.mapped('program_id'):
            message = {'error': _('A Coupon is already applied for the same reward')}
        elif self.program_id._is_global_discount_program() and order._is_global_discount_already_applied():
            message = {'error': _('Global discounts are not cumulable.')}
        elif self.program_id.reward_type == 'product' and not order._is_reward_in_order_lines(self.program_id):
            message = {'error': _('The reward products should be in the sales order lines to apply the discount.')}
        elif not self.program_id._is_valid_partner(order.partner_id):
            message = {'error': _("The customer doesn't have access to this reward.")}
        # Product requirement should not be checked if the coupon got generated by a promotion program (the requirement should have only be checked to generate the coupon)
        elif self.program_id.program_type == 'coupon_program' and not self.program_id._filter_programs_on_products(order):
            message = {'error': _("You don't have the required product quantities on your sales order. All the products should be recorded on the sales order. (Example: You need to have 3 T-shirts on your sales order if the promotion is 'Buy 2, Get 1 Free').")}
        else:
            if self.program_id not in applicable_programs and self.program_id.promo_applicability == 'on_current_order':
                message = {'error': _('At least one of the required conditions is not met to get the reward!')}
        return message

    def action_coupon_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('sale_coupon.mail_template_sale_coupon', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='sale.coupon',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
            custom_layout='mail.mail_notification_light',
            mark_coupon_as_sent=True,
            force_email=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def action_coupon_cancel(self):
        self.state = 'cancel'

    def cron_expire_coupon(self):
        self._cr.execute("""
            SELECT C.id FROM SALE_COUPON as C
            INNER JOIN SALE_COUPON_PROGRAM as P ON C.program_id = P.id
            WHERE C.STATE in ('reserved', 'new', 'sent')
                AND P.validity_duration > 0
                AND C.create_date + interval '1 day' * P.validity_duration < now()""")

        expired_ids = [res[0] for res in self._cr.fetchall()]
        self.browse(expired_ids).write({'state': 'expired'})
