# -*- coding: utf-8 -*-
{
    "name": "Internal Delivery",
    "version": "1.0",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com",
    "category": "Generic Modules/Base",
    "depends": ["delivery_bpost", "base_automation"],
    "description": """Custom delivery integration with bpost""",
    "data": [
        "wizard/merge_picking_label.xml",
        "data/data.xml",
    ],
    'license': 'OEEL-1',
}
