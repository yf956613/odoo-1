# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

import logging
_logger = logging.getLogger(__name__)


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _inherit = "ir.module.module"

    def write(self, vals):
        res = super(IrModuleModule, self).write(vals)
        try:
            if 'state' in vals and vals['state'] == 'installed':
                self.env['website.route']._refresh()
        except Exception as e:
            # not critical, just a nice to have
            _logger.warning(repr(e))
            pass
        return res
