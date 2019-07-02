# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Luxemburg : FAIA',
    'category': 'Localization',
    'version': '1.0',
    'description': 'Fichier Audit Informatisé AED',
    'depends': ['l10n_lu', 'account'],
    'data': [
        'wizard/account_lu_faia_view.xml',
        'wizard/lu_faia1.xml',
        'views/FAIA_xml_format.xml',
        'views/FAIA.xml',
    ],
}
