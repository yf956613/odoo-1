# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr

from . import models, wizard
from odoo import api, SUPERUSER_ID

def _l10n_fr_post_init_hook(cr, registry):
    _preserve_tag_on_taxes(cr, registry)
    _setup_inalterability(cr, registry)

def _preserve_tag_on_taxes(cr, registry):
    from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes
    preserve_existing_tags_on_taxes(cr, registry, 'l10n_fr')

def _setup_inalterability(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # enable ping for this module
    env['publisher_warranty.contract'].update_notification(cron_mode=True)

    fr_companies = env['res.company'].search([('partner_id.country_id.code', 'in', env['res.company']._get_unalterable_country())])
    fr_companies.filtered(lambda x: not x.secure_sequence_id)._create_secure_sequence(['secure_sequence_id'])

    if fr_companies:
        # set the restrict_mode_hash_table field to True
        journals = env['account.journal'].search([('company_id', 'in', fr_companies.ids)])
        journals.write({'restrict_mode_hash_table': True})
