# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug
from werkzeug import urls
from json import dumps
from urllib.parse import unquote

from odoo import http
from odoo.http import request
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.controllers.portal import PaymentProcessing

_logger = logging.getLogger(__name__)


class OgoneController(http.Controller):
    _accept_url = '/payment/ogone/test/accept'
    _decline_url = '/payment/ogone/test/decline'
    _exception_url = '/payment/ogone/test/exception'
    _cancel_url = '/payment/ogone/test/cancel'

    @http.route([
        '/payment/ogone/accept', '/payment/ogone/test/accept',
        '/payment/ogone/decline', '/payment/ogone/test/decline',
        '/payment/ogone/exception', '/payment/ogone/test/exception',
        '/payment/ogone/cancel', '/payment/ogone/test/cancel',
    ], type='http', auth='public')
    def ogone_form_feedback(self, **post):
        """ Ogone contacts using GET, at least for accept """
        _logger.info('Ogone: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.env['payment.transaction'].sudo().form_feedback(post, 'ogone')
        return werkzeug.utils.redirect("/payment/process")

    @http.route(['/payment/ogone/s2s/create_json'], type='json', auth='public', csrf=False)
    def ogone_s2s_create_json(self, **kwargs):
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        new_id = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
        return new_id.id

    @http.route(['/payment/ogone/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def ogone_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        # CREATE THE TOKEN. WE ALREADY HAVE IT
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        token = False
        error = None

        try:
            token = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
        except Exception as e:
            error = str(e)

        if not token:
            res = {
                'result': False,
                'error': error,
            }
            return res

        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
            'verified': False,
        }

        if verify_validity != False:
            baseurl = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            params = {
                'accept_url': baseurl + '/payment/ogone/validate/accept',
                'decline_url': baseurl + '/payment/ogone/validate/decline',
                'exception_url': baseurl + '/payment/ogone/validate/exception',
                'return_url': kwargs.get('return_url', baseurl)
                }
            tx = token.validate(**params)
            res['verified'] = token.verified

            if tx and tx.html_3ds:
                res['3d_secure'] = tx.html_3ds

        return res

    @http.route(['/payment/ogone/s2s/create'], type='http', auth='public', methods=["POST"], csrf=False)
    def ogone_s2s_create(self, **post):
        error = ''
        acq = request.env['payment.acquirer'].browse(int(post.get('acquirer_id')))
        try:
            token = acq.s2s_process(post)
        except Exception as e:
            # synthax error: 'CHECK ERROR: |Not a valid date\n\n50001111: None'
            token = False
            error = str(e).splitlines()[0].split('|')[-1] or ''

        if token and post.get('verify_validity'):
            baseurl = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            params = {
                'accept_url': baseurl + '/payment/ogone/validate/accept',
                'decline_url': baseurl + '/payment/ogone/validate/decline',
                'exception_url': baseurl + '/payment/ogone/validate/exception',
                'return_url': post.get('return_url', baseurl)
                }
            tx = token.validate(**params)
            if tx and tx.html_3ds:
                return tx.html_3ds
            # add the payment transaction into the session to let the page /payment/process to handle it
            PaymentProcessing.add_payment_transaction(tx)
        return werkzeug.utils.redirect("/payment/process")

    @http.route([
        '/payment/ogone/validate/accept',
        '/payment/ogone/validate/decline',
        '/payment/ogone/validate/exception',
    ], type='http', auth='public')
    def ogone_validation_form_feedback(self, **post):
        """ Feedback from 3d secure for a bank card validation """
        request.env['payment.transaction'].sudo().form_feedback(post, 'ogone')
        return werkzeug.utils.redirect("/payment/process")

    @http.route(['/payment/ogone/s2s/feedback'], auth='public', csrf=False)
    def feedback(self, **kwargs):
        try:
            tx = request.env['payment.transaction'].sudo()._ogone_form_get_tx_from_data(kwargs)
            tx._ogone_s2s_validate_tree(kwargs)
        except ValidationError:
            return 'ko'
        return 'ok'

    @http.route(['/payment/ogone/feedback',], type='http', auth='public')
    def ogone_alias_gateway_feedback(self, **post):

        """ Ogone contacts using GET, at least for accept """
        _logger.info('Ogone: feeback Alias gateway with post data %s', pprint.pformat(post))  # debug)
        # If you have configured an SHA-OUT passphrase for these feedback requests,
        # you need to take the ALIAS parameter into account for your signature.
        pprint.pformat(post)
        print("===== STEP ALIAS =====")
        # post parameters are available to the server. We need an rpc call to give them to javascript that will send the direct link form
        # We have created the token. We can now make the payment and create the transaction.
        # Here we can try to perform the request to perform the direct link transaction
        url = "https://ogone.test.v-psp.com/ncol/test/orderdirect.asp"
        payload = {}
        ret = ""
        for key, value in post.items():
            ret += key + ":" + value + "</br>"
        return ret
        for key in ['FLAG3D', 'WIN3DS', 'browserColorDepth', 'browserJavaEnabled', 'browserLanguage',
                    'browserScreenHeight', 'browserScreenWidth', 'browserTimeZone', 'browserAcceptHeader',
                    'browserUserAgent', 'Alias', ]:
            # TODO : not robust because sensible to case
            try:
                payload[key] = post[key]
            except KeyError as e:
                _logger.error(str(e))
                pass
        acquirer = request.env['payment.acquirer'].search([('provider', '=', 'ogone')])
        # DATA VALIDATION
        data_clean = {}
        for key, value in post.items():
            data_clean[key.upper()] = value
        # TODO do something if the sha is bad. NOTE: IT IS RECHECKED in add_payment_transaction
        shasign = acquirer._ogone_generate_shasign('out', data_clean)
        print(data_clean['SHASIGN'])
        print(shasign.upper())
        if data_clean['SHASIGN'] != shasign.upper():
            ret = "<h1>ERROR BAD SHA</h1>" + ret
            return ret

        # PREPARE TRANSACTION
        # TEST
        url_feedback = "http://arj-odoo.agayon.be/payment/ogone/feedback/"
        payload['USERID'] = acquirer.ogone_userid
        payload['PSWD'] = acquirer.ogone_password
        payload['PSPID'] = acquirer.ogone_pspid
        payload['ACCEPTURL'] = url_feedback
        payload['DECLINEURL'] = url_feedback
        payload['EXCEPTIONURL'] = url_feedback
        payload['browserAcceptHeader'] = request.httprequest.headers.environ['HTTP_ACCEPT']
        payload['PARAMPLUS'] = urls.url_encode({'return_url': data_clean['RETURN_URL'], 'partner_id': post.get('partner_id')})
        # payload['HTTP_ACCEPT'] =  '*/*'
        # payload['COMPLUS'] = None
        payload['LANGUAGE'] = 'en_US'

        # *HTTP_ACCEPT and HTTP_USER_AGENT
        # don't have to be sent with browserAcceptHeader and browserUserAgent, otherwise we will fill it with the browser parameters.
        payload = {k.upper(): v for k, v in payload.items()}
        # ONLY TESTS
        # payload['SHASIGN'] = acquirer._ogone_generate_shasign('in', payload)
        print(payload)
        if post.get('partner_id'):
            cvc_masked = 'XXX'
            card_number_masked = post['CardNo']

            # Could be done in _ogone_form_get_tx_from_data ?
            token_parameters = {
                'cc_number': card_number_masked,
                'cc_cvc': cvc_masked,
                'cc_holder_name': data_clean.get('CN'),
                'cc_expiry': data_clean.get('ED'),
                'cc_brand': data_clean.get('BRAND'),
                'acquirer_id': acquirer.id,
                'partner_id': int(post.get('partner_id')),
                'alias_gateway': True,
                'alias': data_clean.get('ALIAS'),
                'acquirer_ref': data_clean.get('ALIAS'),
                'ogone_params': dumps(payload, ensure_ascii=True, indent=None)
            }
            try:
                token = request.env['payment.token'].create(token_parameters, )
                print(token)
            except Exception as e:
                _logger.error(e)
                _logger.error("no token created")
                pass
            return_url = unquote(data_clean['RETURN_URL'])
            print(return_url)
            """
            TODO: 
            - ajouter JS associé à cette page
            + récupérer le form et form action depuis le paramplus
            + soumettre ça par JS avec tous les attributs hidden
                    avec les paramatres propres au browser etc auquel on a accès via param+ ?
                    
            """
