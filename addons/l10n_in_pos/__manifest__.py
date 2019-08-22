# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Point of Sale',
    'version': '1.0',
    'description': """GST Point of Sale""",
    'category': 'Localization',
    'depends': [
        'l10n_in',
        'point_of_sale'
    ],
    'data': [
    ],
    'demo': [
        'data/product_demo.xml',
        'views/point_of_sale.xml',
    ],
    'qweb': [
        'static/src/xml/pos_receipt.xml',
    ],
    'auto_install': True,
}
