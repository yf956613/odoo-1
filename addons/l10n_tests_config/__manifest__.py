# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'l10n configure tests',
    'category': 'Hidden',
    'sequence': 10,
    'summary': 'Configure company for l10n tests',
    'description': """
This module configures Odoo to run tests with a specific l10n\_ module.
Basicaly, it creates a company located in the l10n\_ country and set this company
on the admin user.

This module ins intended for tests only.
""",
    'post_init_hook': '_configure_l10n',
}
