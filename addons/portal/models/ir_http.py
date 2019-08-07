# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from lxml import etree
import traceback
import werkzeug

from odoo import api, exceptions, models, registry
from odoo.http import request
from odoo.osv import expression
from odoo.tools import config

from odoo.addons.base.models.qweb import QWebException

logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_domain(cls):
        domain = super(IrHttp, cls)._get_translation_frontend_modules_domain()
        return expression.OR([domain, [('name', '=', 'portal')]])

    @classmethod
    def _get_exception_code_values(cls, exception):
        """ Return a tuple with the error code following by the values matching the exception"""
        code = 500  # default code
        values = dict(
            exception=exception,
            traceback=traceback.format_exc(),
        )
        # only except_orm exceptions contain a message
        if isinstance(exception, exceptions.except_orm):
            values['error_message'] = exception.name
            code = 400
            if isinstance(exception, exceptions.AccessError):
                code = 403

        elif isinstance(exception, QWebException):
            values.update(qweb_exception=exception)

            # retro compatibility to remove in 12.2
            exception.qweb = dict(message=exception.message, expression=exception.html)

            if type(exception.error) == exceptions.AccessError:
                code = 403

        elif isinstance(exception, werkzeug.exceptions.HTTPException):
            code = exception.code

        values.update(
            status_message=werkzeug.http.HTTP_STATUS_CODES[code],
            status_code=code,
        )

        return (code, values)

    @classmethod
    def _get_values_500_error(cls, env, values, exception):
        View = env["ir.ui.view"]
        values['view'] = View
        if 'qweb_exception' in values:
            try:
                # exception.name might be int, string
                exception_template = int(exception.name)
            except:
                exception_template = exception.name
            view = View._view_obj(exception_template)
            if exception.html and exception.html in view.arch:
                values['view'] = view
            else:
                # There might be 2 cases where the exception code can't be found
                # in the view, either the error is in a child view or the code
                # contains branding (<div t-att-data="request.browse('ok')"/>).
                et = etree.fromstring(view.with_context(inherit_branding=False).read_combined(['arch'])['arch'])
                node = et.xpath(exception.path)
                line = node is not None and etree.tostring(node[0], encoding='unicode')
                if line:
                    values['view'] = View._views_get(exception_template).filtered(
                        lambda v: line in v.arch
                    )
                    values['view'] = values['view'] and values['view'][0]
        return values

    @classmethod
    def _get_error_html(cls, env, code, values):
        return env['ir.ui.view'].render_template('portal.%s' % code, values)

    @classmethod
    def _handle_exception(cls, exception):
        is_portal_request = bool(getattr(request, 'is_frontend', False))
        if not is_portal_request:
            # Don't touch non portal requests exception handling
            return super(IrHttp, cls)._handle_exception(exception)
        try:
            response = super(IrHttp, cls)._handle_exception(exception)

            if isinstance(response, Exception):
                exception = response
            else:
                # if parent excplicitely returns a plain response, then we don't touch it
                return response
        except Exception as e:
            if 'werkzeug' in config['dev_mode']:
                raise e
            exception = e

        code, values = cls._get_exception_code_values(exception)

        if code is None:
            # Hand-crafted HTTPException likely coming from abort(),
            # usually for a redirect response -> return it directly
            return exception

        if not request.uid:
            cls._auth_method_public()
        with registry(request.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, request.uid, request.env.context)
            if code == 500:
                logger.error("500 Internal Server Error:\n\n%s", values['traceback'])
                values = cls._get_values_500_error(env, values, exception)
            elif code == 403:
                logger.warn("403 Forbidden:\n\n%s", values['traceback'])
            elif code == 400:
                logger.warn("400 Bad Request:\n\n%s", values['traceback'])
            try:
                html = cls._get_error_html(env, code, values)
            except Exception:
                html = env['ir.ui.view'].render_template('portal.http_error', values)

        return werkzeug.wrappers.Response(html, status=code, content_type='text/html;charset=utf-8')
