# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteCrm(odoo.tests.HttpSeleniumCase):

    def test_tour(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('website_crm_tour')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.website_crm_tour.ready")

        # check result
        record = self.env['crm.lead'].search([('description', '=', '### TOUR DATA ###')])
        self.assertEqual(len(record), 1)
        self.assertEqual(record.contact_name, 'John Smith')
        self.assertEqual(record.email_from, 'john@smith.com')
        self.assertEqual(record.partner_name, 'Odoo S.A.')
