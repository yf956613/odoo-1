# -*- coding: utf-8 -*-
import odoo.addons.web.controllers.main
from odoo import http, _
from odoo.http import request


class Home(odoo.addons.web.controllers.main.Home):
    @http.route(
        '/web/login/totp',
        type='http', auth='public', methods=['GET', 'POST'], sitemap=False,
        website=True, # website breaks the login layout...
    )
    def web_totp(self, redirect=None, **kwargs):
        if request.session.uid:
            return http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))

        error = None
        if request.httprequest.method == 'POST':
            user = request.env['res.users'].browse(request.session.pre_uid)
            if user._check_totp(int(kwargs['totp_token'])):
                request.session.finalize()
                return http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))
            error = _("Authentication code failed.")

        return request.render('auth_totp.auth_totp_form', {
            'error': error,
            'redirect': redirect,
        })
