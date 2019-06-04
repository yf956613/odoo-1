# -*- coding: utf-8 -*-
from odoo import api, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _create_bank_journals(self, company, acc_template_ref):
        """ Automatically generate bank and cash payment methods.

        This is a helper function in loading a chart of accounts.
        After calling the super of this function, bank and cash
        journals are available. `generate_bank_and_cash_payment_methods`
        can now be called because it is dependent on the existing
        cash journals.
        """
        journals = super(AccountChartTemplate, self)._create_bank_journals(company, acc_template_ref)
        self.env['pos.payment.method'].generate_bank_and_cash_payment_methods(company)
        return journals
