# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Use for filter import and export type.
    l10n_in_import_export = fields.Boolean("Import/Export", help="Tick this if this journal is use for Import/Export Under Indian GST.")
    l10n_in_unit_id = fields.Many2one('res.partner', string="Operating Unit", ondelete="restrict", help="Unit related to this journal. If need the same journal for company all unit then keep this empty.")

    _sql_constraints = [
        ('code_company_uniq', 'unique (code, name, company_id, l10n_in_unit_id)', 'The code and name of the journal must be unique per company unit!'),
    ]

    @api.onchange('company_id')
    def _onchange_company_id(self):
        default_unit = self.l10n_in_unit_id or self.env.user._get_default_unit()
        if default_unit not in self.company_id.l10n_in_unit_ids:
            self.l10n_in_unit_id = self.company_id.partner_id


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('move_id.line_ids', 'move_id.line_ids.tax_line_id', 'move_id.line_ids.debit', 'move_id.line_ids.credit')
    def _compute_tax_base_amount(self):
        aml = self.filtered(lambda l: l.company_id.country_id.code == 'IN' and l.tax_line_id  and l.product_id)
        for move_line in aml:
            base_lines = move_line.move_id.line_ids.filtered(lambda line: move_line.tax_line_id in line.tax_ids and move_line.product_id == line.product_id)
            move_line.tax_base_amount = abs(sum(base_lines.mapped('balance')))
        remaining_aml = self - aml
        if remaining_aml:
            return super(AccountMoveLine, remaining_aml)._compute_tax_base_amount()


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_in_reverse_charge = fields.Boolean("Reverse charge", help="Tick this if this tax is reverse charge. Only for Indian accounting")

    def get_grouping_key(self, invoice_tax_val):
        """ Returns a string that will be used to group account.invoice.tax sharing the same properties"""
        key = super(AccountTax, self).get_grouping_key(invoice_tax_val)
        if self.company_id.country_id.code == 'IN':
            key += "-%s-%s"% (invoice_tax_val.get('l10n_in_product_id', False),
                invoice_tax_val.get('l10n_in_uom_id', False))
        return key
