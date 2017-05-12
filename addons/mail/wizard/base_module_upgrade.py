# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class BaseModuleUpgrade(models.TransientModel):
    _inherit = "base.module.upgrade"

    @api.model
    def _check_model(self, model_ids):
        res = super(BaseModuleUpgrade, self)._check_model(model_ids)
        return res.filtered(lambda x: x.is_mail_thread)
