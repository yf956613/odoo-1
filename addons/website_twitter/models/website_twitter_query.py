# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
import requests

from odoo import api, fields, models

REQUEST_FAVORITE_LIST_URL = 'https://api.twitter.com/1.1/favorites/list.json'
URLOPEN_TIMEOUT = 10

_logger = logging.getLogger(__name__)


class WebsiteTwitterQuery(models.Model):
    _name = 'website.twitter.query'

    name = fields.Char('Name', required=True)
    query = fields.Text('Query', required=True)
    last_fetch = fields.Datetime('Last fetch', help='Last time tweets were fetched from the Twitter API.')
    website_id = fields.Many2one('website', string='Website')

    @api.model
    def _request(self, website, url, params=None):
        """Send an authenticated request to the Twitter API."""
        access_token = self._get_access_token(website)
        try:
            request = requests.get(url, params=params, headers={'Authorization': 'Bearer %s' % access_token}, timeout=URLOPEN_TIMEOUT)
            request.raise_for_status()
            return request.json()
        except requests.HTTPError as e:
            _logger.debug("Twitter API request failed with code: %r, msg: %r, content: %r",
                          e.response.status_code, e.response.reason, e.response.content)
            raise

    @api.multi
    def fetch_favorite_tweets(self):
        self.ensure_one()
        WebsiteTweets = self.env['website.twitter.tweet']
        tweet_ids = []
        for website in self:
            if not all((website.twitter_api_key, website.twitter_api_secret)):
                _logger.debug("Skip fetching favorite tweets for unconfigured website %s", website)
                continue
            params = {'query': self.query}
            last_tweet = WebsiteTweets.search([
                ('website_id', '=', website.id),
                ('query_id', '=', self.id)
            ], limit=1, order='tweet_id desc')
            if last_tweet:
                params['since_id'] = int(last_tweet.tweet_id)
            _logger.debug("Fetching favorite tweets using params %r", params)
            response = self._request(website, REQUEST_FAVORITE_LIST_URL, params=params)
            for tweet_dict in response:
                tweet_id = tweet_dict['id']  # unsigned 64-bit snowflake ID
                tweet_ids = WebsiteTweets.search([('tweet_id', '=', tweet_id)]).ids
                if not tweet_ids:
                    new_tweet = WebsiteTweets.create({
                        'website_id': website.id,
                        'tweet': json.dumps(tweet_dict),
                        'tweet_id': tweet_id,  # stored in NUMERIC PG field
                        'query_id': self.id,
                    })
                    _logger.debug("Found new favorite: %r, %r", tweet_id, tweet_dict)
                    tweet_ids.append(new_tweet.id)
        return tweet_ids
