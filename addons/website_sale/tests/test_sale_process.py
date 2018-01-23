# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_01_admin_shop_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('shop')", "odoo.__DEBUG__.services['web_tour.tour'].tours.shop.ready", login="admin")

    def test_02_admin_checkout(self):
#         fp = self.env.ref('account_taxcloud.account_fiscal_position_taxcloud_us', False)
#         if fp:
#             print('\n\n\n\n\n\n BEFORE admin checkout', fp.auto_apply)
#             fp.write({'auto_apply': False})
#             print('\n\n\n\n\n\n', fp.auto_apply)
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('shop_buy_product')", "odoo.__DEBUG__.services['web_tour.tour'].tours.shop_buy_product.ready", login="admin")

    def test_03_demo_checkout(self):
#         fp = self.env.ref('account_taxcloud.account_fiscal_position_taxcloud_us', False)
#         if fp:
#             print('\n\n\n\n\n\n BEFORE demo checkout', fp.auto_apply)
#             fp.write({'auto_apply': False})
#             print('\n\n\n\n\n\n', fp.auto_apply)
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('shop_buy_product')", "odoo.__DEBUG__.services['web_tour.tour'].tours.shop_buy_product.ready", login="demo")

    # TO DO - add public test with new address when convert to web.tour format.
