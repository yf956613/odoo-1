# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_common import TestCommonSaleNoChart
from odoo.tests.common import users, warmup
from odoo.tools import mute_logger


class TestSalePerformance(TestCommonSaleNoChart):

    def setUp(self):
        super(TestSalePerformance, self).setUp()

        self.setUpAdditionalAccounts()
        self.setUpClassicProducts()
        self.setUpAccountJournal()

        _quick_create_ctx = {
            'no_reset_password': True,
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
        }

        self.user_salesman = self.env['res.users'].with_context(_quick_create_ctx).create({
            'name': 'Marinette Salesman',
            'login': 'sales',
            'email': 'm.m@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('sales_team.group_sale_salesman').id])],
        })
        self.user_salesman2 = self.env['res.users'].with_context(_quick_create_ctx).create({
            'name': 'Ignasse Igor',
            'login': 'sales2',
            'email': 'i.i@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('sales_team.group_sale_salesman_all_leads').id])],
        })

    @users('admin', 'sales2')
    @warmup
    def test_sale_create(self):
        customer_id = self.partner_customer_usd.id
        pl_id = self.pricelist_usd.id
        line0_data = {
            'name': self.product_order.name,
            'product_id': self.product_order.id,
            'product_uom_qty': 2,
            'product_uom': self.product_order.uom_id.id,
            'price_unit': self.product_order.list_price
        }
        line1_data = {
            'name': self.product_deliver.name,
            'product_id': self.product_deliver.id,
            'product_uom_qty': 2,
            'product_uom': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price
        }
        with self.assertQueryCount(admin=777, sales2=888):  # com runbot: ?? - ?? // sale only: 128 - 218
            so = self.env['sale.order'].create({
                'user_id': self.env.uid,
                'partner_id': customer_id,
                'partner_invoice_id': customer_id,
                'partner_shipping_id': customer_id,
                'pricelist_id': pl_id,
                'order_line': [(0, 0, line0_data), (0, 0, line1_data)],
            })

        # change responsible
        # with self.assertQueryCount(admin=139, sales2=224):  # test_sale only: 3 - 3
        #     so.write({
        #         'user_id': self.user_salesman.id,
        #     })

        # confirm