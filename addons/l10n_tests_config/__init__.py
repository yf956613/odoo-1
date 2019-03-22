# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re
from odoo import api, SUPERUSER_ID, tools

_logger = logging.getLogger(__name__)

def _configure_l10n(cr, registry):
    """ Configure company to test the l10n_ specified in the cli args """
    env = api.Environment(cr, SUPERUSER_ID, {})
    l10n_mod_re = re.compile('l10n_..$')
    
    # get l10n_ modules to install from command line
    l10n_modules_cli = [m for m, to_install in tools.config['init'].items() if to_install and l10n_mod_re.match(m)]
    
    # set company country code as the same as the first l10n_ module found
    if l10n_modules_cli:
        country_code = l10n_modules_cli[0][-2:].upper()
        country = env['res.country'].search([('code', '=', country_code)], limit=1)
        env.user.company_id.country_id = country.id

