# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import os
from tempfile import TemporaryFile

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BaseLanguageImport(models.TransientModel):
    _name = "base.language.import"
    _description = "Language Import"

    name = fields.Char('Language Name', required=True)
    code = fields.Char('ISO Code', size=6, required=True,
                       help="ISO Language and Country code, e.g. en_US")
    data = fields.Binary('File', required=True, attachment=False)
    filename = fields.Char('File Name', required=True)
    overwrite = fields.Boolean('Overwrite Existing Terms',
                               help="If you enable this option, existing translations (including custom ones) "
                                    "will be overwritten and replaced by those in this file")

    def import_lang(self):
        self.ensure_one()
        with TemporaryFile('wb+') as buf:
            try:
                buf.write(base64.decodestring(self.data))

                # now we determine the file format
                buf.seek(0)
                fileformat = os.path.splitext(self.filename)[-1][1:].lower()

                lang = self.env['res.lang']._lang_get(self.code)
                if not lang:
                    # lets create the language with locale information
                    self.env['res.lang']._create_lang(lang=self.code, lang_name=self.name)
                else:
                    lang._activate_lang()

                tools.trans_load_data(self._cr, buf, fileformat, self.code, context=dict(self._context, overwrite=self.overwrite))
            except Exception as e:
                _logger.exception('File unsuccessfully imported, due to format mismatch.')
                raise UserError(
                    _('File %r not imported due to format mismatch or a malformed file.'
                      ' (Valid formats are .csv, .po, .pot)\n\nTechnical Details:\n%s') %
                      (self.filename, tools.ustr(e))
                )
        return True
