# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpSeleniumCase):
    def test_01_admin_shop_tour(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('shop')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.shop.ready",
            login="admin",
            max_tries=25)

    def test_02_admin_checkout(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('shop_buy_product')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.shop_buy_product.ready",
            login="admin",
            max_tries=25)

    def test_03_demo_checkout(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('shop_buy_product')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.shop_buy_product.ready",
            login="demo",
            max_tries=25)

    # TO DO - add public test with new address when convert to web.tour format.
