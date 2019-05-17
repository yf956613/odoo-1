# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super(IrHttp, self).session_info()
        res['uoms'] = self.get_uoms() if request.session.uid else {}
        return res

    def get_uoms(self):
        uom = request.env['uom.uom']
        uoms = uom.search([]).read(['name', 'decimal_places'])
        return {u['id']: {'name': u['name'], 'decimal_places': u['decimal_places']} for u in uoms}
