# -*- coding: utf-8 -*-
from odoo import http, tools, _
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date, timedelta
from random import randint
import json
import base64
from ..models import consts


class PartnerDashboard(http.Controller):

    def _get_events(self, country_id):
        Events = request.env['event.event'].sudo()
        today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        oxp = Events.search([('event_type_id', '=', consts.ODOO_EXP_ID), ('date_begin', '>', today)], limit=1)
        tour = Events.search([('event_type_id', '=', consts.ODOO_TOUR_ID), ('date_begin', '>', today)])

        local_tour = tour.filtered(lambda x: x.country_id == country_id)
        foreign_tour = tour.filtered(lambda x: x.country_id != country_id)
        return {'events': (oxp + local_tour + foreign_tour)[:3]}

    def _get_country_cached_stat(self, country_id):
        attachment = request.env.ref('partner_dashboard.dashboard_partner_stats').sudo()
        if not attachment.datas:
            request.env['crm.lead']._refresh_dashboard_data()
        data_dict = json.loads(base64.b64decode(attachment.datas))
        country_dict = next(filter(lambda x: x['country_id'] == country_id, data_dict))
        return {
            'company_size': json.dumps(country_dict['lead_by_company_size']),
            'country_leads': country_dict['country_leads'],
            'country_partners': country_dict['country_partners'],
            'country_customers': country_dict['country_customers'],
        }

    def _get_subscriptions(self, partner_id):
        Subscription = request.env['sale.subscription'].sudo()

        last_year = (date.today() - timedelta(days=365)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        subs = Subscription.search([
            ('partner_id', '=', partner_id),
            ('name', 'not ilike', 'PART-'),
            ('recurring_next_date', '>', last_year)
        ])

        last_12month_enterprise_user = 0
        current_enterprise_user = 0

        for sub in subs:
            for line in sub.recurring_invoice_line_ids:
                if line.product_id.id in consts.ENTERPRISE_USER_IDS:
                    last_12month_enterprise_user += line.quantity
                    if sub.state == 'open':
                        current_enterprise_user += line.quantity
        return {
            'subscriptions': subs,
            'current_enterprise_user': current_enterprise_user,
            'last_12month_enterprise_user': last_12month_enterprise_user,
        }

    def _get_purchase_orders(self, partner_id):
        # assert not request.website.is_public_user()
        PurchaseOrder = request.env['purchase.order']

        last_year = (date.today() - timedelta(days=365)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        orders = PurchaseOrder.sudo().search([
            ('partner_id', '=', partner_id),
            ('date_order', '>', last_year),
            ('state', '!=', 'cancel')
        ])

        last_12months_purchase_total = 0
        commission_to_receive = 0

        for order in orders:
            for line in order.order_line:
                if line.product_id.id in consts.ENTERPRISE_COMMISSION_USER_IDS:
                    last_12months_purchase_total += line.price_subtotal
                    if order.invoice_status == 'to invoice':
                        commission_to_receive += line.price_subtotal

        return {
            'orders': orders,
            'commission_to_receive': commission_to_receive,
            'last_12months_purchase_total': last_12months_purchase_total,
        }

    def _get_grade(self, partner):
        NEXT_GRADE_USERS_VALUE = {'Learning': 0, 'Bronze': 50, 'Silver': 100, 'Gold': 0, 'Platinum': -10}
        NEXT_GRADE_CERTIFIED_VALUE = {'Learning': 1, 'Bronze': 2, 'Silver': 4, 'Gold': 0, 'Platinum': -10}
        NEXT_GRADE_COMMISSION_VALUE = {'Learning': 5, 'Bronze': 10, 'Silver': 20, 'Gold': 0, 'Platinum': -10}
        partner_grade = partner.grade_id.name

        next_level_users = 0
        next_level_certified = 0
        next_level_com = 0

        certified_experts = []
        nbr_certified = 0
        partner_certif = ''

        for child in partner.child_ids:
            certifs = []
            for certif in child.website_tag_ids.filtered(lambda x: len(consts.ODOO_CERT_IDS & x)):
                certifs.append(certif)
            if certifs:
                certified_experts.append({
                    'partner': child,
                    'certifs': certifs
                })

        company_certifs = partner.commercial_partner_id.website_tag_ids.filtered(lambda x: len(consts.ODOO_CERT_IDS & x))

        nbr_certified = len(certified_experts)

        if partner_grade:
            next_level_users = NEXT_GRADE_USERS_VALUE[partner_grade]
            next_level_certified = NEXT_GRADE_CERTIFIED_VALUE[partner_grade]
            next_level_com = NEXT_GRADE_COMMISSION_VALUE[partner_grade]

        return {
            'partner_grade': partner_grade,
            'company_certif': company_certifs,
            'next_level_users': next_level_users,
            'next_level_certified': next_level_certified,
            'next_level_com': next_level_com,
            'nbr_certif': nbr_certified,
            'certified_experts': certified_experts,
        }

    def _get_opportunities(self, partner_id):
        Lead = request.env['crm.lead'].sudo()
        won_opportunities = Lead.search_count([('partner_id', "=", partner_id), ('stage_id', '=', 4)])
        not_won_opportunities = Lead.search_count([('partner_id', "=", partner_id), ('stage_id', '!=', 4)])

        return{
            'won_opportunities': won_opportunities,
            'not_won_opportunities': not_won_opportunities,
        }

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
        values.update(self._get_country_cached_stat(country.id))
        values.update(self._get_events(country))

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
            values.update(self._get_subscriptions(partner.id))
            values.update(self._get_purchase_orders(partner.id))
            values.update(self._get_grade(partner))
            values.update(self._get_opportunities(partner.id))
            values.update({
                'currency': partner.country_id.currency_id.symbol,  # TODO FIX ME
                'my_sub': subscription,
            })

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
                    import pprint;pprint.pprint(values)
                    print(partner)
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

        learning_price = Product.browse(consts.PRODUCT_LEARNING_PRICE)
        official_price = Product.browse(consts.PRODUCT_OFFICIAL_PRICE)

        return request.render('partner_dashboard.plans_prices', {
            'learning_price': learning_price,
            'official_price': official_price,
        })
