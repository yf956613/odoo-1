# -*- coding: utf-8 -*-

from odoo import models
from datetime import date, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from . import consts


class Partner(models.Model):
    _inherit = 'res.partner'

    def _get_subscriptions(self):
        Subscription = self.env['sale.subscription'].sudo()

        last_year = (date.today() - timedelta(days=365)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        subs = Subscription.search([
            ('partner_id', '=', self.id),
            ('name', 'not ilike', 'PART-'),
            ('recurring_next_date', '>', last_year)
        ])

        last_12month_enterprise_user = 0
        current_enterprise_user = 0

        for sub in subs:
            for line in sub.recurring_invoice_line_ids:
                if line.product_id.id in consts.ENTERPRISE_USER_IDS:
                    last_12month_enterprise_user += line.quantity
                    if sub.state == 'open':
                        current_enterprise_user += line.quantity
        return {
            'subscriptions': subs,
            'current_enterprise_user': current_enterprise_user,
            'last_12month_enterprise_user': last_12month_enterprise_user,
        }

    def _get_purchase_orders(self):
        # assert not request.website.is_public_user()
        PurchaseOrder = self.env['purchase.order']

        last_year = (date.today() - timedelta(days=365)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        orders = PurchaseOrder.sudo().search([
            ('partner_id', '=', self.id),
            ('date_order', '>', last_year),
            ('state', '!=', 'cancel')
        ])

        last_12months_purchase_total = 0
        commission_to_receive = 0

        for order in orders:
            for line in order.order_line:
                if line.product_id.id in consts.ENTERPRISE_COMMISSION_USER_IDS:
                    last_12months_purchase_total += line.price_subtotal
                    if order.invoice_status == 'to invoice':
                        commission_to_receive += line.price_subtotal

        return {
            'orders': orders,
            'commission_to_receive': commission_to_receive,
            'last_12months_purchase_total': last_12months_purchase_total,
        }

    def _get_grade(self):
        NEXT_GRADE_USERS_VALUE = {'Learning': 0, 'Bronze': 50, 'Silver': 100, 'Gold': 0, 'Platinum': -10}
        NEXT_GRADE_CERTIFIED_VALUE = {'Learning': 1, 'Bronze': 2, 'Silver': 4, 'Gold': 0, 'Platinum': -10}
        NEXT_GRADE_COMMISSION_VALUE = {'Learning': 5, 'Bronze': 10, 'Silver': 20, 'Gold': 0, 'Platinum': -10}
        partner_grade = self.grade_id.name

        next_level_users = 0
        next_level_certified = 0
        next_level_com = 0

        certified_experts = []
        nbr_certified = 0

        for child in self.child_ids:
            certifs = []
            for certif in child.website_tag_ids.filtered(lambda x: len(consts.ODOO_CERT_IDS & x)):
                certifs.append(certif)
            if certifs:
                certified_experts.append({
                    'partner': child,
                    'certifs': certifs
                })

        company_certifs = self.commercial_partner_id.website_tag_ids.filtered(lambda x: len(consts.ODOO_CERT_IDS & x))

        nbr_certified = len(certified_experts)

        if partner_grade:
            next_level_users = NEXT_GRADE_USERS_VALUE[partner_grade]
            next_level_certified = NEXT_GRADE_CERTIFIED_VALUE[partner_grade]
            next_level_com = NEXT_GRADE_COMMISSION_VALUE[partner_grade]

        return {
            'partner_grade': partner_grade,
            'company_certif': company_certifs,
            'next_level_users': next_level_users,
            'next_level_certified': next_level_certified,
            'next_level_com': next_level_com,
            'nbr_certif': nbr_certified,
            'certified_experts': certified_experts,
        }

    def _get_opportunities(self):
        Lead = self.env['crm.lead'].sudo()
        won_opportunities = Lead.search_count([('partner_id', "=", self.id), ('stage_id', '=', 4)])
        not_won_opportunities = Lead.search_count([('partner_id', "=", self.id), ('stage_id', '!=', 4)])

        return{
            'won_opportunities': won_opportunities,
            'not_won_opportunities': not_won_opportunities,
        }
