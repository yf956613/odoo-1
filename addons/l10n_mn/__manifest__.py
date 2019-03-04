# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Mongolia - Accounting",
    "version" : "1.0",
    'category': 'Localization',
    "description": """
This is the module to manage the accounting chart for Mongolia.
========================================================================

    * the Mongolia Official Chart of Accounts,
    * the Tax Code Chart for Mongolia
    * the main taxes used in Mongolia
""",
    "depends": ['account'],
    'data': [
        'data/l10n_mn_chart_data.xml',
        'data/account.account.tag.csv',
        'data/account.account.template.csv',
        'data/account.tax.group.csv',
        'data/account.tax.template.csv',
        'data/account.chart.template.csv',
        'data/account_chart_template_data.xml'
    ],
}
