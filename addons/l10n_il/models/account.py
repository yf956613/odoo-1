# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class WithhReason(models.Model):
    _name = 'l10n.il.withh.tax.reason'
    _description = 'Israel withholding tax reason'

    name = fields.Char(string='Withholding Tax Reason', help="The reason for which withholding tax is applied")
    code = fields.Char(string='Code', help="Israel withholding tax reason code")

    _sql_constraints = [('code_uniq', 'unique (code)', 'The code of the Withholding Tax Reason must be unique!')]


class ITABranch(models.Model):
    _name = 'l10n.il.ita.branch'
    _description = 'Israel Tax Authority branch'

    name = fields.Char(string='ITA Branch', help="ITA (Israel Tax Authority) branch name")
    code = fields.Char(string='Code', help="ITA (Israel Tax Authority) branch code")

    _sql_constraints = [('code_uniq', 'unique (code)', 'The code of the ITA Branch must be unique!')]

class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_il_valid_until_date = fields.Date(string='Valid Until Date', readonly=False)
    l10n_il_withh_tax_reason = fields.Many2one('l10n.il.withh.tax.reason', string='Withh Tax Reason', help="This field contains the withholding tax reason that will be used for Annual Witholding Tax Report'")
    l10n_il_ita_branch = fields.Many2one('l10n.il.ita.branch', string='ITA Branch', help="This field contains the ITA branch that expended the withholding tax rate and that will be used for Annual Witholding Tax Report")
