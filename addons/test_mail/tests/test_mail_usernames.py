# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import re
import email
import logging

import odoo.tools as tools
from odoo.tests import common
import odoo.addons.base.models.ir_mail_server as ir_mail_server
from odoo.addons.test_mail.tests import common as mail_common

example_email_sub_ref = """Subject: Re: About contact Fountain
To: Mitchéll, Admin <test@odoodoo.com>
References: %REF%
From: =?UTF-8?B?8J+QpywgcGVuIHBlbg==?= <pen@odoodoo.com>
Message-ID: <a4471088-1cca-d553-e92f-14546bac0ed8@odoodoo.com>
Date: Fri, 6 Sep 2019 10:49:26 +0200
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101
 Thunderbird/60.8.0
MIME-Version: 1.0
In-Reply-To: %REF%
Content-Type: multipart/alternative;
 boundary="------------CFCB0A82F1145C22384CD846"
Content-Language: en-US

This is a multi-part message in MIME format.
--------------CFCB0A82F1145C22384CD846
Content-Type: text/plain; charset=utf-8; format=flowed
Content-Transfer-Encoding: 8bit

text

--------------CFCB0A82F1145C22384CD846
Content-Type: text/html; charset=utf-8
Content-Transfer-Encoding: 8bit

<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  </head>
  <body bgcolor="#333333" text="#CCCCCC">
    <p>
        text
    </p>
  </body>
</html>

--------------CFCB0A82F1145C22384CD846--
"""


class TestMailUsernames(common.SavepointCase, mail_common.MockEmails):

    @tools.mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_message_values_unicode(self):
        """Normal flow demonstrating the name handling; the user replied on a thread.
        """
        thread_record = self.env['res.partner'].create({'name': "Fountain"})
        reference = '<openerp-%s-res.partner@werk>' % thread_record.id
        mail = self.env['mail.message'].create({
            'model': 'res.partner',
            'res_id': thread_record.id,
            'author_id': self.env.ref('base.user_demo').partner_id.id,
            'reply_to': 'test@odoodoo.com',
            'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
        })
        mail.message_id = reference
        thread_record.message_ids = [(4, mail.id)]

        example_email = re.sub("%REF%", reference, example_email_sub_ref)

        logger = logging.getLogger('odoo.addons.base.models.ir_mail_server')
        log_capture_string = io.StringIO()
        ch = logging.StreamHandler(log_capture_string)
        logger.addHandler(ch)

        self.env['mail.thread'].message_process(False, example_email)

        log_contents = log_capture_string.getvalue()
        log_capture_string.close()

        # without fix:
        # self.assertIn("Failed to encode the address", log_contents)
        self.assertEqual(log_contents, '')

    @tools.mute_logger('odoo.addons.mail.models.mail_mail')
    def test_decode_recode_username(self):
        """If the name of a contact contains a comma,
        it might cause trouble since it's used as email separator.
        We check that in both cases, decoding is idempotent,
        and we get back get the right name/address couples
        """
        froms = [
            "From: pen pen <pen@odoodoo.com>",
            "From: pen, pen <pen@odoodoo.com>",
            "From: =?UTF-8?B?8J+QpyBwZW4gcGVuIPCfkKc=?= <pen@odoodoo.com>",  # basic unicode
            "From: =?UTF-8?B?8J+QpywgcGVuIHBlbg==?= <pen@odoodoo.com>",  # with comma
            "From: =?UTF-8?B?8J+QpyIsIGxlbg==?= <pen@odoodoo.com >",  # with double quote
            "From: =?UTF-8?B?8J+QpycsIGxlbg==?= <pen@odoodoo.com >",  # with single quote
            "From: =?UTF-8?B?8J+Qp1wnLCBsZVxu?= <pen@odoodoo.com >",  # with backslash
        ]
        for header_from in froms:
            decoded_from = tools.decode_smtp_header(header_from, escape_names=True)
            addresses_from = email.utils.getaddresses([decoded_from])
            re_encoded = ir_mail_server.encode_rfc2822_address_header(decoded_from)
            redecoded_from = tools.decode_smtp_header(re_encoded, escape_names=True)
            addresses_from_redecoded = email.utils.getaddresses([redecoded_from])

            self.assertEqual(len(addresses_from), len(addresses_from_redecoded))
            self.assertEqual(addresses_from[0][1], addresses_from_redecoded[0][1])
            self.assertEqual(addresses_from[0][0], addresses_from_redecoded[0][0])
