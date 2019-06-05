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
from odoo.exceptions import AccessDenied
from odoo.http import request


class Users(models.Model):
    _inherit = 'res.users'

    totp_secret = fields.Char()
    totp_last_valid = fields.Integer(default=0)
    totp_enabled = fields.Boolean(compute='_compute_totp_enabled')

    def _mfa_url(self):
        r = super()._mfa_url()
        if r is not None:
            return r
        if self.totp_enabled:
            return '/web/login/totp'

    @api.depends('totp_secret')
    def _compute_totp_enabled(self):
        for r, v in zip(self, self.sudo().read(['totp_secret'])):
            r.totp_enabled = bool(v['totp_secret'])

    @api.depends('totp_secret')
    def _compute_keys_only(self):
        super()._compute_keys_only()
        for u in self:
            self.api_keys_only |= u.totp_enabled

    def _totp_check(self, code):
        sudo = self.sudo()
        key = base64.b32decode(sudo.totp_secret.upper())
        match = TOTP(key).match(code, previous=sudo.totp_last_valid)
        if match is None:
            raise AccessDenied()

        sudo.totp_last_valid = match

    def totp_try_setting(self, secret, code):
        match = TOTP(base64.b32decode(secret.upper())).match(code, previous=0)
        if match is None:
            return False

        sudo = self.sudo()
        sudo.write({
            'totp_secret': secret,
            'totp_last_valid': match,
        })
        return True

    def totp_generate(self):
        if self.totp_enabled:
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

    def match(self, code, *, previous, t=None, window=TIMESTEP):
        """
        :param code: authenticator code to check against this key
        :param int previous: counter value returned by a prevously successful
                             match, windows older than that counter will not
                             be attempted (avoids replay attacks / shoulder
                             surfing), pass in `0` for a first attempt
        :param int t: current timestamp (seconds)
        :param int window: fuzz window to account for slow fingers, network
                           latency, desynchronised clocks, ..., every code
                           valid between t-window an t+window is considered
                           valid
        """
        if t is None:
            t = time.time()

        low = max(int((t - window) / TIMESTEP), previous+1)
        high = int((t + window) / TIMESTEP) + 1

        return next((
            counter for counter in range(low, high)
            if hotp(self._key, counter) == code
        ), None)

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
