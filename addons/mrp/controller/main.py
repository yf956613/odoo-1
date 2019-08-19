# -*- coding: utf-8 -*-

import base64
import json
import logging

from odoo import http
from odoo.http import request
from odoo.tools.translate import _

logger = logging.getLogger(__name__)


class MrpDocumentRoute(http.Controller):
    def _neuter_mimetype(self, mimetype, user):
        wrong_type = 'ht' in mimetype or 'xml' in mimetype or 'svg' in mimetype
        if wrong_type and not user._is_system():
            return 'text/plain'
        return mimetype

    def binary_content(self, id, env=None, field='datas',
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
    def _get_file_response(self, id, field='datas'):
        """
        returns the http response to download one file.

        """

        status, headers, content = self.binary_content(
            id, download=True)

        if status != 200:
            return request.env['ir.http']._response_by_status(status, headers, content)
        else:
            content_base64 = base64.b64decode(content)
            headers.append(('Content-Length', len(content_base64)))
            response = request.make_response(content_base64, headers)

        return response

    @http.route('/mrp/upload_attachment', type='http', methods=['POST'], auth="user")
    def upload_document(self, ufile, **kwargs):
        files = request.httprequest.files.getlist('ufile')
        result = {'success': _("All files uploaded")}
        for ufile in files:
            try:
                mimetype = self._neuter_mimetype(ufile.content_type, http.request.env.user)
                request.env['mrp.document'].create({
                    'name': ufile.filename,
                    'res_model': kwargs.get('default_res_model'),
                    'res_id': kwargs.get('default_res_id'),
                    'mimetype': mimetype,
                    'datas': base64.encodestring(ufile.read()),
                })
            except Exception as e:
                logger.exception("Fail to upload document %s" % ufile.filename)
                result = {'error': str(e)}

        return json.dumps(result)
