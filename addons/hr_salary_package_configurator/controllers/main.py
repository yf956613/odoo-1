# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.website_portal.controllers.main import website_account

class SalaryPackage(website_account):

    @http.route(['/my/salary-package', '/my/salary-package/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_salary_package(self, page=1, date_begin=None, date_end=None, sortby=None):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        return request.render("hr_salary_package_configurator.portal_my_salary_package", values)