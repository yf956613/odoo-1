# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_module_l10n_in = fields.Boolean(compute='_compute_show_module_l10n_in')
    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")
    group_l10n_in_multi_gstin = fields.Boolean(string="Multi GSTIN", implied_group='l10n_in.group_l10n_in_multi_gstin')

    def set_values(self):
        super().set_values()
        #set company it self as unit in exsiting records
        if self.group_l10n_in_multi_gstin:
            for company in self.env.user.company_ids:
                company.partner_id.sudo().write({'l10n_in_gstin_company_id': company})

    def action_open_company(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.company',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.company_id.id,
        }

    @api.depends('company_id')
    def _compute_show_module_l10n_in(self):
        self.show_module_l10n_in = self.company_id.country_id.code == 'IN'
