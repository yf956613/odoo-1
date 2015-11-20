# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    module_account_taxcloud = fields.Boolean("Compute sales tax automatically using TaxCloud.",
        help='Compute sales tax automatically using TaxCloud based on customer address in United States.\n'
                                          '-that installs the module account_taxcloud.')
