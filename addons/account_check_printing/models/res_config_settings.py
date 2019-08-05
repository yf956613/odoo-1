# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    country_code = fields.Char(string="Company Country code", related='company_id.country_id.code', readonly=True)
    account_check_printing_report_actions = fields.Selection(related="company_id.account_check_printing_report_actions", string='Check Layout', readonly=False,
        help="Set the layout for you want to print the checks.")
    account_check_printing_date_label = fields.Boolean(related='company_id.account_check_printing_date_label', string="Print Date Label", readonly=False,
        help="This option allows you to print the date label on the check as per CPA. Disable this if your pre-printed check includes the date label.")
    account_check_printing_multi_stub = fields.Boolean(related='company_id.account_check_printing_multi_stub', string='Multi-Pages Check Stub', readonly=False,
        help="This option allows you to print check details (stub) on multiple pages if they don't fit on a single page.")
    account_check_printing_margin_top = fields.Float(related='company_id.account_check_printing_margin_top', string='Check Top Margin', readonly=False,
        help="Adjust the margins of generated checks to make it fit your printer's settings.")
    account_check_printing_margin_left = fields.Float(related='company_id.account_check_printing_margin_left', string='Check Left Margin', readonly=False,
        help="Adjust the margins of generated checks to make it fit your printer's settings.")
    account_check_printing_margin_right = fields.Float(related='company_id.account_check_printing_margin_right', string='Check Right Margin', readonly=False,
        help="Adjust the margins of generated checks to make it fit your printer's settings.")
