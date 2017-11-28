# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpSeleniumCase):
    def test_01_portal_load_tour(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('portal_load_homepage')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.portal_load_homepage.ready",
            login="portal"
        )
