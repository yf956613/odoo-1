# -*- coding: utf-8 -*-
from odoo import http, tools, _
from odoo.http import request
from odoo.exceptions import ValidationError
from random import randint
import base64
from ..models import consts


class PartnerDashboard(http.Controller):

    def _get_geocountry(self):
        country = False
        country_code = request.session.geoip and request.session.geoip.get('country_code') or False
        if country_code:
            country = request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1)
        return country or request.env.ref('base.be')

    def _get_random_partner(self):
        Employee = request.env['hr.employee'].sudo()
        contact = consts.POINT_OF_CONTACT_IDS[randint(0, len(consts.POINT_OF_CONTACT_IDS) - 1)]
        return Employee.browse(contact).user_id.partner_id.id

    def _values(self, access_token):
        Subscription = request.env['sale.subscription'].sudo()
        Partner = request.env['res.partner'].sudo()
        Lead = request.env['crm.lead'].sudo()
        lead = Lead.decode(request) and Lead.browse(Lead.decode(request)).exists()

        # TODO: Use location to assign a saleman from the correct sale ZONE departement

        subscription = False
        saleman = False
        partner = False
        contact = False

        if access_token:
            subscription = Subscription.search([('uuid', '=', access_token), ('template_id.code', '=', "PART")], limit=1, order='create_date desc')
        elif not request.website.is_public_user():
            subscription = Subscription.search([('partner_id', '=', request.env.user.partner_id.commercial_partner_id.id), ('template_id.code', '=', "PART")], limit=1, order='create_date desc')

        if subscription:
            partner = subscription.partner_id
            saleman = subscription.user_id and subscription.user_id.partner_id.id
        else:
            if request.website.is_public_user():
                if lead:
                    partner = lead.partner_id  # - TODO
                    lead_pic = lead.env['ir.attachment'].search([('datas_fname', '=', 'profile_pic'), ('res_id', '=', lead.id)])['datas']
                    saleman = lead.user_id.id or (lead.partner_id and lead.partner_id.user_id.id)

                    contact = Partner.new({
                        'name': lead.contact_name,
                        'street': lead.street,
                        'state_id': lead.state_id,
                        'city': lead.city,
                        'zip': lead.zip,
                        'country_id': lead.country_id,
                        'email': lead.email_from,
                        'phone': lead.phone,
                    })
            else:
                partner = request.env.user.partner_id.commercial_partner_id
                saleman = partner.user_id.partner_id.id

        if not saleman:
            saleman = request.session.get('saleman_id', self._get_random_partner())
            request.session['saleman_id'] = saleman

        country = (partner and partner.country_id) or (lead and lead.country_id) or self._get_geocountry()

        values = {}
        values.update(country._get_country_cached_stat())
        values.update(country._get_events())

        values.update({
            'saleman': Partner.browse(saleman),
            'access_token': access_token,
            'partner': partner,
            'contact': contact or partner,
            'country_id': country,
            # 'source': partner or lead,
            # 'source_email': (partner and partner.email) or (lead and lead.email_from),
            # 'source_name': (partner and partner.name) or (lead and lead.contact_name),
            'source_image': (partner and partner.image_medium) or (lead and lead_pic),

        })

        if request.website.is_public_user() and not access_token:
            if lead:
                values.update({
                    'street': lead.street,
                })
        else:  # partner set
            values.update(partner._get_subscriptions())
            values.update(partner._get_purchase_orders())
            values.update(partner._get_grade())
            values.update(partner._get_opportunities())
            values.update({
                'currency': partner.country_id.currency_id.symbol,  # TODO FIX ME
                'my_sub': subscription,
            })
        print(values['country_id'].currency_id)
        return values

    @http.route(['/dashboard', '/dashboard/<access_token>'], type='http', auth="public", website=True)
    def dashboard_token(self, access_token=None, **kw):
        values = self._values(access_token)
        return request.render('partner_dashboard.dashboard', values)

    @http.route(['/dashboard/profile'], type='http', auth='public', website=True)
    def dasboard_profile(self, redirect=None, **data):
        Lead = request.env['crm.lead'].sudo()
        lead = Lead.decode(request) and Lead.browse(Lead.decode(request)).exists()

        MANDATORY_FIELDS = ["name", "phone", "email", "street", "city", "country_id"]
        OPTIONAL_FIELDS = ["zipcode", "state_id", "vat", "company_name", "website_description"]

        error = {}
        error_message = []

        if request.website.is_public_user():
            partner = False
            img = lead and request.env['ir.attachment'].search([
                ('datas_fname', '=', 'profile_pic'), ('res_id', '=', lead.id)
            ])['datas']
        else:
            partner = request.env.user.partner_id.commercial_partner_id
            img = partner.image_medium

        if request.httprequest.method == 'POST':

            # Validation required
            for field_name in MANDATORY_FIELDS:
                if not data.get(field_name):
                    error[field_name] = 'missing'

            # email validation
            if data.get('email') and not tools.single_email_re.match(data.get('email')):
                error["email"] = 'error'
                error_message.append(_('Invalid Email! Please enter a valid email address.'))

            # vat validation
            Partner = request.env["res.partner"]
            if data.get("vat") and hasattr(Partner, "check_vat"):
                if data.get("country_id"):
                    data["vat"] = request.env["res.partner"].fix_eu_vat_number(int(data.get("country_id")), data.get("vat"))
                partner_dummy = Partner.new({
                    'vat': data['vat'],
                    'country_id': (int(data['country_id']) if data.get('country_id') else False),
                })
                try:
                    partner_dummy.check_vat()
                except ValidationError:
                    error["vat"] = 'error'

            # error message for empty required fields
            if [err for err in error.values() if err == 'missing']:
                error_message.append(_('Some required fields are empty.'))

            if not error:
                resp = request.redirect('/dashboard')
                values = {key: data[key] for key in MANDATORY_FIELDS}
                values.update({key: data[key] for key in OPTIONAL_FIELDS if key in data})
                values.update({'zip': values.pop('zipcode', '')})

                if 'country_id' in values:
                    values['country_id'] = int(values['country_id'])

                if not partner:
                    lead_data = {
                        'partner_name': values['company_name'],
                        'street': values['street'],
                        'city': values['city'],
                        'zip': values['zip'],
                        'country_id': values['country_id'],
                        'email_from': values['email'],
                        'phone': values['phone'],
                        'contact_name': values['name'],
                    }
                    if lead:
                        lead_data['user_id'] = lead.user_id
                        lead.write(lead_data)
                    else:
                        lead_data.update({
                            'name': "NEW PARTNERSHIP for %s" % values['name'],
                            'user_id': False,
                        })
                        lead = Lead.create(lead_data)

                        sign = Lead.encode(lead.id)
                        resp.set_cookie('lead_id', sign)

                    if data['image']:
                        file = request.httprequest.files['image']
                        img = base64.encodestring(file.stream.read())

                        attach_id = request.env['ir.attachment'].search([('res_id', '=', lead.id), ('datas_fname', 'ilike', 'profile_pic')])
                        if attach_id:
                            attach_id.datas = img
                        else:
                            request.env['ir.attachment'].create({
                                'name': 'Profile Picture',
                                'datas': img,
                                'datas_fname': 'profile_pic',
                                'res_model': 'crm.lead',
                                'res_id': lead.id,
                            })
                else:
                    if partner._vat_readonly(partner):
                        'vat' in values and values.pop('vat')
                        'name' in values and values.pop('name')
                        'company_name' in values and values.pop('company_name')
                    partner = partner.write(values)
                return resp

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])

        data.update({
            'partner': partner or request.env["res.partner"],
            'source_email': lead and lead.email_from or partner and partner.email,
            'source_name': lead and lead.contact_name or partner and partner.name,
            'source_image': img,
            'source': partner or lead or request.env["res.partner"],
            'countries': countries,
            'states': states,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'error': error,
            'error_message': error_message,
        })

        return request.render("partner_dashboard.partner_form", data)

    @http.route('/dashboard/pricing', type='http', auth="public", website=True)
    def pricing(self, **kw):
        Product = request.env['product.template'].sudo()
        if request.env.user.partner_id:
            country = request.env.user.partner_id.country_id
        else:
            country = self._get_geocountry()

        learning_price = Product.browse(consts.PRODUCT_LEARNING_PRICE)
        official_price = Product.browse(consts.PRODUCT_OFFICIAL_PRICE)

        return request.render('partner_dashboard.plans_prices', {
            'learning_price': learning_price,
            'official_price': official_price,
            'currency': country.currency_id,
        })
