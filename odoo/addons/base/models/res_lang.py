# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import locale
import logging
import os
import re
import shutil
import tarfile
import tempfile
from collections import defaultdict
from datetime import timedelta
from operator import itemgetter
from io import BytesIO, StringIO
from werkzeug.urls import url_join

import requests

from odoo import api, fields, models, http, tools, release, _
from odoo.modules.module import ad_paths
from odoo.modules import get_module_path, get_module_resource
from odoo.tools.misc import file_open
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

DEFAULT_DATE_FORMAT = '%m/%d/%Y'
DEFAULT_TIME_FORMAT = '%H:%M:%S'
MAX_FILE_SIZE = 15 * 1024 * 1024  # in megabytes
REFRESH_THRESHOLD = timedelta(hours=12)


class Lang(models.Model):
    _name = "res.lang"
    _description = "Languages"
    _order = "active desc,name"

    _disallowed_datetime_patterns = list(tools.DATETIME_FORMATS_MAP)
    _disallowed_datetime_patterns.remove('%y') # this one is in fact allowed, just not good practice

    name = fields.Char(required=True)
    code = fields.Char(string='Locale Code', required=True, help='This field is used to set/get locales for user')
    iso_code = fields.Char(string='ISO code', help='This ISO code is the name of po files to use for translations')
    translatable = fields.Boolean()
    active = fields.Boolean()
    direction = fields.Selection([('ltr', 'Left-to-Right'), ('rtl', 'Right-to-Left')], required=True, default='ltr')
    date_format = fields.Char(string='Date Format', required=True, default=DEFAULT_DATE_FORMAT)
    time_format = fields.Char(string='Time Format', required=True, default=DEFAULT_TIME_FORMAT)
    week_start = fields.Selection([('1', 'Monday'),
                                   ('2', 'Tuesday'),
                                   ('3', 'Wednesday'),
                                   ('4', 'Thursday'),
                                   ('5', 'Friday'),
                                   ('6', 'Saturday'),
                                   ('7', 'Sunday')], string='First Day of Week', required=True, default='7')
    grouping = fields.Char(string='Separator Format', required=True, default='[]',
        help="The Separator Format should be like [,n] where 0 < n :starting from Unit digit. "
             "-1 will end the separation. e.g. [3,2,-1] will represent 106500 to be 1,06,500; "
             "[1,2,-1] will represent it to be 106,50,0;[3] will represent it as 106,500. "
             "Provided ',' as the thousand separator in each case.")
    decimal_point = fields.Char(string='Decimal Separator', required=True, default='.', trim=False)
    thousands_sep = fields.Char(string='Thousands Separator', default=',', trim=False)
    last_fetch_date = fields.Datetime(string='Last Translations Fetch')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The name of the language must be unique !'),
        ('code_uniq', 'unique(code)', 'The code of the language must be unique !'),
    ]

    @api.constrains('active')
    def _check_active(self):
        # do not check during installation
        if self.env.registry.ready and not self.search_count([]):
            raise ValidationError(_('At least one language must be active.'))

    @api.constrains('time_format', 'date_format')
    def _check_format(self):
        for lang in self:
            for pattern in lang._disallowed_datetime_patterns:
                if (lang.time_format and pattern in lang.time_format) or \
                        (lang.date_format and pattern in lang.date_format):
                    raise ValidationError(_('Invalid date/time format directive specified. '
                                            'Please refer to the list of allowed directives, '
                                            'displayed when you edit a language.'))

    @api.constrains('grouping')
    def _check_grouping(self):
        warning = _('The Separator Format should be like [,n] where 0 < n :starting from Unit digit. '
                    '-1 will end the separation. e.g. [3,2,-1] will represent 106500 to be 1,06,500;'
                    '[1,2,-1] will represent it to be 106,50,0;[3] will represent it as 106,500. '
                    'Provided as the thousand separator in each case.')
        for lang in self:
            try:
                if not all(isinstance(x, int) for x in json.loads(lang.grouping)):
                    raise ValidationError(warning)
            except Exception:
                raise ValidationError(warning)

    @api.model_cr
    def _register_hook(self):
        # check that there is at least one active language
        if not self.search_count([]):
            _logger.error("No language is active.")

    def _activate_lang(self):
        """ activate languages. """
        self.filtered(lambda l: not l.active).write({'active': True})
        return self

    # TODO v13, remove me
    @api.model
    def load_lang(self, lang, lang_name=None):
        _logger.warning("Call to deprecated method load_lang, use _create_lang or _activate_lang instead")
        language = self._lang_get(lang)
        if language:
            language._activate_lang()
        else:
            self._create_lang(lang, lang_name=lang_name)


    @api.model
    def _create_lang(self, lang, lang_name=None):
        """ Create the given language if necessary, and make it active. """
        # create the language with locale information
        fail = True
        iso_lang = tools.get_iso_codes(lang)
        for ln in tools.get_locales(lang):
            try:
                locale.setlocale(locale.LC_ALL, str(ln))
                fail = False
                break
            except locale.Error:
                continue
        if fail:
            lc = locale.getdefaultlocale()[0]
            msg = 'Unable to get information for locale %s. Information from the default locale (%s) have been used.'
            _logger.warning(msg, lang, lc)

        if not lang_name:
            lang_name = lang

        def fix_xa0(s):
            """Fix badly-encoded non-breaking space Unicode character from locale.localeconv(),
               coercing to utf-8, as some platform seem to output localeconv() in their system
               encoding, e.g. Windows-1252"""
            if s == '\xa0':
                return '\xc2\xa0'
            return s

        def fix_datetime_format(format):
            """Python's strftime supports only the format directives
               that are available on the platform's libc, so in order to
               be 100% cross-platform we map to the directives required by
               the C standard (1989 version), always available on platforms
               with a C standard implementation."""
            # For some locales, nl_langinfo returns a D_FMT/T_FMT that contains
            # unsupported '%-' patterns, e.g. for cs_CZ
            format = format.replace('%-', '%')
            for pattern, replacement in tools.DATETIME_FORMATS_MAP.items():
                format = format.replace(pattern, replacement)
            return str(format)

        conv = locale.localeconv()
        lang_info = {
            'code': lang,
            'iso_code': iso_lang,
            'name': lang_name,
            'active': True,
            'translatable': True,
            'date_format' : fix_datetime_format(locale.nl_langinfo(locale.D_FMT)),
            'time_format' : fix_datetime_format(locale.nl_langinfo(locale.T_FMT)),
            'decimal_point' : fix_xa0(str(conv['decimal_point'])),
            'thousands_sep' : fix_xa0(str(conv['thousands_sep'])),
            'grouping' : str(conv.get('grouping', [])),
        }
        try:
            return self.create(lang_info).id
        finally:
            tools.resetlocale()

    @api.model
    def _get_i18n_url(self, base, lang):
        """ Generate the URL to fetch the translation resource
            e.g. https://nightly.odoo.com/i18n/13.0/fr.tar.xz
        """
        version = release.version
        return url_join(base, "i18n/{}/{}.tar.xz".format(version, lang))

    @api.model
    def _read_po_from_i18n_folder(self, addons, lang):
        path = get_module_resource(addons, 'i18n', lang + '.po')
        if path:
            with file_open(path, 'rb') as f:
                yield f

        extra_path = get_module_resource(addons, 'i18n_extra', lang + '.po')
        if extra_path:
            with file_open(extra_path, 'rb') as f:
                yield f

        if not path and not extra_path:
            _logger.info('module %s: no translation for language %s', addons, lang)

    @api.model
    def _read_po_from_attachment(self, addons, lang):
        module = self.env['ir.module.module'].search([('name', '=', addons)])
        if not module:
            return None

        attachment_name = "{}/i18n/{}.po".format(addons, lang)
        po_file = self.env['ir.attachment'].search([
            ('res_model', '=', 'ir.module.module'),
            ('res_id', '=', module.id),
            ('name', '=', attachment_name)
        ], limit=1)

        if po_file:
            yield StringIO(po_file.datas)

    @api.model
    def _extract_po_to_i18n_folder(self, addons, tmp, extracted_file):
        """ Extraction method if the po are stored on filesystem, inside /i18n/ folders """
        path = get_module_path(addons)
        if not os.access(path, os.W_OK):
            _logger.warning("Path %s is not writeable", path)
            return False

        src_file = os.path.join(tmp, extracted_file)
        dst_file = os.path.join(path, extracted_file)
        shutil.move(src_file, dst_file)

    @api.model
    def _extract_po_to_attachment(self, addons, tmp, extracted_file):
        """ Extraction method if the po are stored in db, inside ir.attachments """
        module = self.env['ir.module.module'].search([('name', '=', addons)], limit=1)
        if not module:
            _logger.info("Skip translations extraction for unexpected module %s", addons)
            return

        src_file = os.path.join(tmp, extracted_file)
        with open(src_file, 'r') as po_file:
            po_content = base64.b64encode(po_file.read().encode()).decode()

        # sudo to be able to search and write, even if no rights on ir.module.module
        Attachment = self.env['ir.attachment'].sudo()

        attached_po = Attachment.search([
            ('res_model', '=', 'ir.module.module'),
            ('res_id', '=', module.id)
            ('name', '=', extracted_file)
        ], limit=1)
        if attached_po:
            attached_po.write({'datas': po_content})
        else:
            attached_po = Attachment.create({
                'datas': po_content,
                'res_model': 'ir.module.module',
                'res_id': module.id,
                'name': extracted_file,
            })
        return attached_po

    @api.model
    def _extract_i18n_file_content(self, fileobj, lang, module_list, extraction_method):
        """ Extract the translations from the given archive

        The expected archive is a .tar.xz file using the structure:
            <module>/i18n/<lang>.po

        Regional variants are accepted (e.g. fr.tar.xz can contain both fr and
        fr_BE files)

        :param fileobj: a file object containing the compressed translation files
        :param lang: the simplified language code to load (e.g. 'fr')
        :param module_list: the list of modules to update from this archive
        :param extraction_method: the method to call with the extracted .po file
        """
        with tarfile.open(mode='r:xz', fileobj=fileobj) as tar_content:
            with tempfile.TemporaryDirectory() as tmp:
                for filename in tar_content.getnames():
                    if not filename.endswith('.po'):
                        _logger.info("Skip unexpected file %s", filename)
                        continue

                    # TODO different separators for windows in tar?
                    addons = filename.split('/')[0]
                    if addons not in module_list:
                        _logger.debug("Skip translations for unexpected module %s", addons)
                        continue

                    po_lang = filename.split('/')[-1][:-3]
                    if po_lang.split('_')[0] != lang:
                        _logger.debug("Skip translations for unexpected language %s", po_lang)
                        continue

                    _logger.debug("Extracting translation file %s to %s", filename, tmp)
                    tar_content.extract(filename, path=tmp)
                    extraction_method(addons, tmp, filename)

        return True

    @api.model
    def _get_po_extract_method(self):
        """ Get the method that will be used to process retrieved po file """
        save_to_fs = tools.config.get('translations_fs_store', False)
        if save_to_fs:
            return self._extract_po_to_i18n_folder
        else:
            return self._extract_po_to_attachment

    @api.model
    def _get_po_read_method(self):
        """ Get the method that will be used to find po file for a lang and module """
        save_to_fs = tools.config.get('translations_fs_store', False)
        if True:
            return self._read_po_from_i18n_folder
        else:
            return self._read_po_from_attachment

    def _download_translation_files(self):
        """ Download the translation files of all modules from the i18n servers """
        mods = self.env['ir.module.module'].search_read([('state', '!=', 'uninstallable'),],
                                                        fields=['name', 'i18n_location'])
        urls = defaultdict(list)
        # [{'id': 1, 'name': 'base', 'i18n_location': 'https://...'},...] -> {'https://...': ['base',...],...}
        for module_info in mods:
            urls[module_info['i18n_location']].append(module_info['name'])

        # will the files be extracted on filesystem or saved in ir.attachments
        extraction_method = self._get_po_extract_method()

        # ['fr_BE', 'fr', 'nl_BE'] -> {'fr', 'nl'}
        langs = {lang.split('_')[0] for lang in self.mapped('code')}

        for lang in langs:
            for url in urls:
                full_url = self._get_i18n_url(url, lang)
                try:
                    stream = requests.get(full_url, stream=True)
                    if stream.status_code != 200:
                        _logger.error("Could not fetch translations from %s, error code %s", full_url, stream.status_code)
                        continue

                    if int(stream.headers['content-length']) > MAX_FILE_SIZE:
                        raise UserError("Content too long (got %.2fMB, max %.2fMB)" % (
                            int(stream.headers['content-length']) / (1024*1024),
                            MAX_FILE_SIZE / (1024*1024)
                        ))
                    bio = BytesIO()
                    bio.write(stream.content)
                    bio.seek(0)
                    self._extract_i18n_file_content(bio, lang, urls[url], extraction_method)
                except requests.exceptions.RequestException as err:
                    _logger.error("Could not fetch translations from %s, error: %s", full_url, err)

    def _lang_to_download(self):
        """ Filter which languages should be downloaded """
       
        res = self.browse()

        if not tools.config.get('download_translations', True):
            return res

        # languages that are being installed yet should be downloaded
        inactive_languages = self.filtered(lambda l: not l.active)
        res |= inactive_languages

        now = fields.Datetime.now()
        for lang in self - inactive_languages:
            if not lang.last_fetch_date or \
                    (now - lang.last_fetch_date) > REFRESH_THRESHOLD:
                # has never been fetched or old enough
                res |= lang

        return res

    def _install_language(self, overwrite=False, remote=True):
        """
        Install/update a lang
        1. download language pack (if needed)
        2. load translations
        """

        to_download = self.browse()
        if remote:
            to_download = self._lang_to_download()
        self._activate_lang()

        if to_download:
            to_download._download_translation_files()

        # appropriate module filtering is done in _update_translations
        mods = self.env['ir.module.module'].search([])
        return mods._update_translations(filter_lang=self, overwrite=overwrite)


    @api.model
    def _set_default_lang(self):
        """

        This method is called from odoo/addons/base/base_data.xml to load
        some language and set it as the default for every partners. The
        language is set via tools.config by the RPC 'create' method on the
        'db' object. This is a fragile solution and something else should be
        found.

        """
        # config['load_language'] is a comma-separated list or None
        lang_code = (tools.config.get('load_language') or 'en_US').split(',')[0]
        lang = self._lang_get(lang_code)
        if lang:
            lang._activate_lang()
        else:
            self._create_lang(lang=lang_code)
        IrDefault = self.env['ir.default']
        default_value = IrDefault.get('res.partner', 'lang')
        if default_value is None:
            IrDefault.set('res.partner', 'lang', lang_code)
            # set language of main company, created directly by db bootstrap SQL
            partner = self.env.company_id.partner_id
            if not partner.lang:
                partner.write({'lang': lang_code})
        return True

    @tools.ormcache('code')
    def _lang_get_id(self, code):
        self.env.cr.execute("""
            SELECT id
            FROM res_lang
            WHERE code=%s
            """, (code,))
        lang_id = self.env.cr.fetchone()
        return lang_id and lang_id[0] or None

    @api.model
    def _lang_get(self, code):
        return self.browse(self._lang_get_id(code))

    @tools.ormcache('self.code', 'monetary')
    def _data_get(self, monetary=False):
        conv = locale.localeconv()
        thousands_sep = self.thousands_sep or conv[monetary and 'mon_thousands_sep' or 'thousands_sep']
        decimal_point = self.decimal_point
        grouping = self.grouping
        return grouping, thousands_sep, decimal_point

    @api.model
    @tools.ormcache()
    def get_available(self):
        """ Return the available languages as a list of (code, name) sorted by name. """
        langs = self.with_context(active_test=False).search([])
        return sorted([(lang.code, lang.name) for lang in langs], key=itemgetter(1))

    @api.model
    @tools.ormcache()
    def get_installed(self):
        """ Return the installed languages as a list of (code, name) sorted by name. """
        langs = self.with_context(active_test=True).search([])
        return sorted([(lang.code, lang.name) for lang in langs], key=itemgetter(1))

    @api.model_create_multi
    def create(self, vals_list):
        self.clear_caches()
        return super(Lang, self).create(vals_list)

    @api.multi
    def write(self, vals):
        lang_codes = self.mapped('code')
        if 'code' in vals and any(code != vals['code'] for code in lang_codes):
            raise UserError(_("Language code cannot be modified."))
        if vals.get('active') == False:
            if self.env['res.users'].search([('lang', 'in', lang_codes)]):
                raise UserError(_("Cannot deactivate a language that is currently used by users."))
            # delete linked ir.default specifying default partner's language
            self.env['ir.default'].discard_values('res.partner', 'lang', lang_codes)

        res = super(Lang, self).write(vals)
        self.clear_caches()
        return res

    @api.multi
    def unlink(self):
        for language in self:
            if language.code == 'en_US':
                raise UserError(_("Base Language 'en_US' can not be deleted."))
            ctx_lang = self._context.get('lang')
            if ctx_lang and (language.code == ctx_lang):
                raise UserError(_("You cannot delete the language which is the user's preferred language."))
            if language.active:
                raise UserError(_("You cannot delete the language which is Active!\nPlease de-activate the language first."))
            self.env['ir.translation'].search([('lang', '=', language.code)]).unlink()
        self.clear_caches()
        return super(Lang, self).unlink()

    @api.multi
    def format(self, percent, value, grouping=False, monetary=False):
        """ Format() will return the language-specific output for float values"""
        self.ensure_one()
        if percent[0] != '%':
            raise ValueError(_("format() must be given exactly one %char format specifier"))

        formatted = percent % value

        # floats and decimal ints need special action!
        if grouping:
            lang_grouping, thousands_sep, decimal_point = self._data_get(monetary)
            eval_lang_grouping = safe_eval(lang_grouping)

            if percent[-1] in 'eEfFgG':
                parts = formatted.split('.')
                parts[0] = intersperse(parts[0], eval_lang_grouping, thousands_sep)[0]

                formatted = decimal_point.join(parts)

            elif percent[-1] in 'diu':
                formatted = intersperse(formatted, eval_lang_grouping, thousands_sep)[0]

        return formatted


def split(l, counts):
    """

    >>> split("hello world", [])
    ['hello world']
    >>> split("hello world", [1])
    ['h', 'ello world']
    >>> split("hello world", [2])
    ['he', 'llo world']
    >>> split("hello world", [2,3])
    ['he', 'llo', ' world']
    >>> split("hello world", [2,3,0])
    ['he', 'llo', ' wo', 'rld']
    >>> split("hello world", [2,-1,3])
    ['he', 'llo world']

    """
    res = []
    saved_count = len(l) # count to use when encoutering a zero
    for count in counts:
        if not l:
            break
        if count == -1:
            break
        if count == 0:
            while l:
                res.append(l[:saved_count])
                l = l[saved_count:]
            break
        res.append(l[:count])
        l = l[count:]
        saved_count = count
    if l:
        res.append(l)
    return res

intersperse_pat = re.compile('([^0-9]*)([^ ]*)(.*)')

def intersperse(string, counts, separator=''):
    """

    See the asserts below for examples.

    """
    left, rest, right = intersperse_pat.match(string).groups()
    def reverse(s): return s[::-1]
    splits = split(reverse(rest), counts)
    res = separator.join(reverse(s) for s in reverse(splits))
    return left + res + right, len(splits) > 0 and len(splits) -1 or 0
