# -*- coding: utf-8 -*-

import base64

from odoo import http
from odoo.http import request


class ShareRoute(http.Controller):
    def binary_content(self, id, env=None, field='datas', share_id=None, share_token=None,
                       download=False, unique=False, filename_field='name'):
        env = env or request.env
        record = env['mrp.document'].browse(int(id))
        filehash = None

        if not record:
            return (404, [], None)

        mimetype = False
        status, content, filename, mimetype, filehash = env['ir.http']._binary_record_content(
            record, field=field, filename=None, filename_field=filename_field,
            default_mimetype='application/octet-stream')
        status, headers, content = env['ir.http']._binary_set_headers(
            status, content, filename, mimetype, unique, filehash=filehash, download=download)

        return status, headers, content

    @http.route(['/mrp/content/<int:id>'], type='http', auth='user')
    def _get_file_response(self, id, field='datas', share_id=None, share_token=None):
        """
        returns the http response to download one file.

        """

        status, headers, content = self.binary_content(
            id, field=field, share_id=share_id, share_token=share_token, download=True)

        if status != 200:
            return request.env['ir.http']._response_by_status(status, headers, content)
        else:
            content_base64 = base64.b64decode(content)
            headers.append(('Content-Length', len(content_base64)))
            response = request.make_response(content_base64, headers)

        return response
