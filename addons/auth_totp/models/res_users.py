# -*- coding: utf-8 -*-
import base64
import hmac
import io
import os
import struct
import time

import qrcode
import werkzeug.urls

from odoo import api, fields, models
from odoo.http import request


class Users(models.Model):
    _inherit = 'res.users'

    secret_totp = fields.Char()
    has_totp = fields.Boolean(compute='_compute_has_totp')

    def _mfa_url(self):
        r = super()._mfa_url()
        if r is not None:
            return r
        if self.has_totp:
            return '/web/login/totp'

    @api.depends('secret_totp')
    def _compute_has_totp(self):
        for r, v in zip(self, self.sudo().read(['secret_totp'])):
            r.has_totp = bool(v['secret_totp'])

    @api.depends('secret_totp')
    def _compute_keys_only(self):
        super()._compute_keys_only()
        for u in self:
            self.api_keys_only |= u.has_totp

    # TODO: token invalidation, time boundary
    def _check_totp(self, code):
        secret = self.sudo().secret_totp
        key = base64.b32decode(secret.upper())
        return TOTP(key).match(code)

    def try_setting(self, secret, code):
        if TOTP(base64.b32decode(secret)).match(code):
            self.sudo().secret_totp = secret
            return True
        return False

    def totp_generate(self):
        if self.has_totp:
            return False

        secret = base64.b32encode(os.urandom(35)).decode()

        user = request.env.user
        label = '{0.company_id.display_name}:{0.login}'.format(user)
        url = werkzeug.urls.url_unparse((
            'otpauth', 'totp',
            werkzeug.urls.url_quote(label, safe=''),
            werkzeug.urls.url_encode({
                'secret': secret,
                'issuer': user.company_id.display_name,
                # apparently a lowercase hash name is anathema to google
                # authenticator (error) and passlib (no token)
                'algorithm': ALGORITHM.upper(),
                'digits': DIGITS,
                'period': TIMESTEP,
            }), ''
        ))

        data = io.BytesIO()
        qrcode.make(url.encode(), box_size=4).save(data, optimise=True, format='PNG')
        return {
            # NOTE: sign the secret?
            # NOTE: store secret in session instead of getting it back from the client?
            'secret': secret,
            'qrcode': base64.b64encode(data.getvalue()).decode(),
        }

# The algorithm (and key URI format) allows customising these parameters but
# google authenticator doesn't support it
# https://github.com/google/google-authenticator/wiki/Key-Uri-Format
ALGORITHM = 'sha1'
DIGITS = 6
TIMESTEP = 30

class TOTP:
    def __init__(self, key):
        self._key = key

    def match(self, code, t=None, window=TIMESTEP):
        if t is None:
            t = time.time()

        low = int((t - window) / TIMESTEP)
        high = int((t + window) / TIMESTEP) + 1

        return any(
            hotp(self._key, counter) == code
            for counter in range(low, high)
        )

def hotp(secret, counter):
    # C is the 64b counter encoded in big-endian
    C = struct.pack(">Q", counter)
    mac = hmac.new(secret, msg=C, digestmod=ALGORITHM).digest()
    # the data offset is the last nibble of the hash
    offset = mac[-1] & 0xF
    # code is the 4 bytes at the offset interpreted as a 31b big-endian uint
    # (31b to avoid sign concerns). This effectively limits digits to 9 and
    # hard-limits it to 10: each digit is normally worth 3.32 bits but the
    # 10th is only worth 1.1 (9 digits encode 29.9 bits).
    code = struct.unpack_from('>I', mac, offset)[0] & 0x7FFFFFFF
    r = code % (10 ** DIGITS)
    # NOTE: use text / bytes instead of int?
    return r
