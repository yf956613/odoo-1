# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpSeleniumCase):

    def test_01_point_of_sale_tour(self):
        self.selenium_run(
            "/web",
            "odoo.__DEBUG__.services['web_tour.tour'].run('point_of_sale_tour')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.point_of_sale_tour.ready",
            login="admin")
