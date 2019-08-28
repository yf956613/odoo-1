# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_in_gstin_partner_id = fields.Many2one(related="journal_id.l10n_in_gstin_partner_id")
