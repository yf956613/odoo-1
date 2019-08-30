# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import calendar
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    siret = fields.Char(related='partner_id.siret', string='SIRET', size=14, readonly=False)
    ape = fields.Char(string='APE')

    @api.model
    def _get_unalterable_country(self):
        res = super(ResCompany, self)._get_unalterable_country()
        return res + ['FR', 'MF', 'MQ', 'NC', 'PF', 'RE', 'GF', 'GP', 'TF']

    def _is_vat_french(self):
        return self.vat and self.vat.startswith('FR') and len(self.vat) == 13

    def _is_accounting_unalterable(self):
        return super(ResCompany, self)._is_accounting_unalterable() or self._is_vat_french()

class ResPartner(models.Model):
    _inherit = 'res.partner'

    siret = fields.Char(string='SIRET', size=14)

class ChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        journals = super(ChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict)
        if company.country_id == self.env.ref('base.fr'):
            #For France, sale/purchase journals must have a dedicated sequence for refunds
            for journal in journals:
                if journal['type'] in ['sale', 'purchase']:
                    journal['refund_sequence'] = True
        return journals
