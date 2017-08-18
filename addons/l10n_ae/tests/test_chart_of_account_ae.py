# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestChartOfaccountAE(common.TransactionCase):

    def test_company_chart_of_account(self):
        company = self.env.user.company_id
        self.assertIn('U.A.E Chart of Accounts', company.chart_template_id.name)
