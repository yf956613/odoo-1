# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_in_gstin_partner_ids = fields.One2many('res.partner', 'l10n_in_gstin_company_id', string="Multi GSTIN")

    @api.model
    def create(self, vals):
        # company's partner will now act as it's gstin partner
        partner = self.env['res.partner']
        if vals.get('partner_id'):
            partner = partner.browse(vals['partner_id'])
        company = super(ResCompany, self).create(vals)
        (partner or company.partner_id).sudo().write({'l10n_in_gstin_company_id': company})
        return company