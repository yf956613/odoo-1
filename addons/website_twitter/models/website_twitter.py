# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests
from odoo import fields, models

REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth2/token'
URLOPEN_TIMEOUT = 10

_logger = logging.getLogger(__name__)


class WebsiteTwitter(models.Model):
    _inherit = 'website'

    twitter_api_key = fields.Char(string='Twitter API key', help='Twitter API Key', groups="website.group_website_designer")
    twitter_api_secret = fields.Char(string='Twitter API secret', help='Twitter API Secret', groups="website.group_website_designer")
    twitter_api_access_token = fields.Char(string='Twitter API Access Token', help='Twitter API Access Token', groups="website.group_website_designer")

    def _get_access_token(self, website):
        """Obtain a bearer token."""
        self.ensure_one()
        if not self.twitter_api_access_token:
            r = requests.post(
                REQUEST_TOKEN_URL,
                data={'grant_type': 'client_credentials'},
                auth=(website.twitter_api_key, website.twitter_api_secret),
                timeout=URLOPEN_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            self.twitter_api_access_token = data['access_token']
        return self.twitter_api_access_token
