# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class PartnerDashboard(http.Controller):

    def get_my_subscription(self):
        Subscription = request.env['sale.subscription']
        # partner_id = request.env.user.partner_id.id
        partner_id = request.env['res.partner'].browse(10).id
        return Subscription.search([('partner_id', '=', partner_id), ('code', 'like', 'PART-')], limit=1, order='create_date desc')

    def get_subscriptions(self):
        ENTERPRISE_USER_IDS = [request.env.ref('openerp_enterprise.product_user_month')]
        Subscription = request.env['sale.subscription']
        partner_id = request.env.user.partner_id.id
        subs = Subscription.search([('partner_id', '=', partner_id), ('name', 'not ilike', 'PART-')])

        user = 0
        rec_total = 0

        # sum(subs.mapped('recurring_invoice_line_ids').filtered(lambda line: line.product_id in ENTERPRISE_USER_IDS).mapped('quantity'))
        for sub in subs:
            for line in sub.recurring_invoice_line_ids:
                if line.product_id in ENTERPRISE_USER_IDS:
                    user += line.quantity
                    rec_total += sub.recurring_total
        return {
            'subscriptions': subs,
            'enterprise_user': user,
            'recurring_total': rec_total,
        }

    def get_purchase_orders(self):
        ENTERPRISE_USER_IDS = [request.env.ref('openerp_enterprise.product_user_month')]
        PurchaseOrder = request.env['purchase.order']
        partner_id = request.env.user.partner_id.id
        orders = PurchaseOrder.search([('partner_id', '=', partner_id), ('name', 'not ilike', 'PART-')])

        purchase_total = 0

        # sum(subs.mapped('recurring_invoice_line_ids').filtered(lambda line: line.product_id in ENTERPRISE_USER_IDS).mapped('quantity'))
        for order in orders:
            for line in order.order_line:
                if line.product_id in ENTERPRISE_USER_IDS:
                    purchase_total += line.price_subtotal
        return {
            'orders': orders,
            'purchase_total': purchase_total,
        }

    def get_country_stats(self):
        Leads = request.env['crm.lead']
        Partners = request.env['res.partner']
        partner = request.env['res.partner'].browse(10)
        partner_country = partner.country_id.id
        country_customers = Leads.search_count([('country_id', '=', partner_country)])
        country_leads = Leads.search_count([('country_id', '=', partner_country)])
        country_partners = Partners.search_count(['&', ('country_id', '=', partner_country), ('is_company', '=', True)])

        return {
            'country_leads': country_leads,
            'country_partners': country_partners,
            'country_customers': country_customers,
        }

    @http.route('/partnerDashboard', type='http', auth="user", website=True)
    def index(self, **kw):
        Partner = request.env['res.partner']
        Subscription = request.env['sale.subscription']

        saleman = Partner.browse(6)
        partner = Partner.browse(10)
        values = self.get_subscriptions()
        values.update(self.get_purchase_orders())
        values.update(self.get_country_stats())

        values.update({
            'partner': partner,
            'country': partner.country_id.name,
            'currency': partner.country_id.currency_id.symbol,
            'opportunities': partner.opportunity_count,
            'subscriptions': partner.subscription_count,
            'commissions': sum(Subscription.search([('partner_id', '=', 10)]).mapped('recurring_total')),
            'my_sub': self.get_my_subscription().display_name,
            'saleman': saleman,
        })
        return request.render('partner_dashboard.dashboard', values)

    @http.route('/partnerDashboard/createLead', type='http', auth="user", website=True)
    def createLead(self, **kw):
        return request.render('partner_dashboard.leadFormTemp')
