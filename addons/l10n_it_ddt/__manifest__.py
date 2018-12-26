# -*- coding: utf-8 -*-
{
    'name': "l10n_it_ddt",
    'website': 'https://www.odoo.com',
    'category': 'Localization',
    'version': '0.1',

    'depends': ['l10n_it', 'sale_stock', 'delivery'],

    'data': [
        'report/l10n_it_ddt_report.xml',
        'views/stock_picking_views.xml',
    ]
}
