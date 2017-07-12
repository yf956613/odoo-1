# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from odoo import api, SUPERUSER_ID


def _set_product_image_ids(cr, registry):
    #write the default product_image_ids on product.template
    env = api.Environment(cr, SUPERUSER_ID, {})
    for template in env['product.template'].search([]):
        env['product.image'].create({'image': template.image, 'product_tmpl_id': template.id, 'name': template.name, 'is_main_image': True})
