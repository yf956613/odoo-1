# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import Environment
import odoo.tests

@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteHrRecruitmentForm(odoo.tests.HttpSeleniumCase):
    def test_tour(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('website_hr_recruitment_tour')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.website_hr_recruitment_tour.ready")

        # check result
        record = self.env['hr.applicant'].search([('description', '=', '### HR RECRUITMENT TEST DATA ###')])
        self.assertEqual(len(record), 1)
        self.assertEqual(record.partner_name, "John Smith")
        self.assertEqual(record.email_from, "john@smith.com")
        self.assertEqual(record.partner_phone, '118.218')
