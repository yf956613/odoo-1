# -*- coding: utf-8 -*-
from odoo import http, tools, _
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date, timedelta
from random import randint
import json
import base64
from ..models.consts import ENTERPRISE_USER_IDS, POINT_OF_CONTACT_IDS


class PartnerDashboard(http.Controller):

    def _get_subscriptions(self, partner_id):
        # assert not request.website.is_public_user()

        ENTERPRISE_USER_IDS = [request.env.ref('openerp_enterprise.product_user_month')]
        Subscription = request.env['sale.subscription']

        last_year = (date.today() - timedelta(days=365)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        subs = Subscription.sudo().search([('partner_id', '=', partner_id), ('name', 'not ilike', 'PART-'), ('recurring_next_date', '>', last_year)])

        last_12month_enterprise_user = 0
        current_enterprise_user = 0

        for sub in subs:
            for line in sub.recurring_invoice_line_ids:
                if line.product_id in ENTERPRISE_USER_IDS:
                    last_12month_enterprise_user += line.quantity
                    if sub.state == 'open':
                        current_enterprise_user += line.quantity
        return {
            'subscriptions': subs,
            'current_enterprise_user': current_enterprise_user,
            'last_12month_enterprise_user': last_12month_enterprise_user,
        }

    def _get_events(self, country_id):
        ODOO_EXP_ID = 12  # The id of the Odoo Experience category
        ODOO_TOUR_ID = 11  # The id of the Odoo Tour category
        Events = request.env['event.event'].sudo()
        today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        oxp = Events.search([('event_type_id', '=', ODOO_EXP_ID), ('date_begin', '>', today)], limit=1)
        tour = Events.search([('event_type_id', '=', ODOO_TOUR_ID), ('date_begin', '>', today)])

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

    def _get_purchase_orders(self, partner_id):
        # assert not request.website.is_public_user()
        PurchaseOrder = request.env['purchase.order']

        last_year = (date.today() - timedelta(days=365)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        orders = PurchaseOrder.sudo().search([('partner_id', '=', partner_id), ('date_order', '>', last_year), ('state', '!=', 'cancel')])

        last_12months_purchase_total = 0
        commission_to_receive = 0

        for order in orders:
            for line in order.order_line:
                if line.product_id.id in ENTERPRISE_USER_IDS:
                    last_12months_purchase_total += line.price_subtotal
                    if order.invoice_status == 'to invoice':
                        commission_to_receive += line.price_subtotal

        return {
            'orders': orders,
            'commission_to_receive': commission_to_receive,
            'last_12months_purchase_total': last_12months_purchase_total,
        }

    def _get_grade(self, partner):
        ODOO_CERT_IDS = request.env['res.partner.category'].sudo().search([('name', '=ilike', 'Certification%')])
        ODOO_COMPANY_CERT_IDS = request.env['res.partner.category'].sudo().search([('name', '=ilike', 'CTP Certif%')])
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
            for certif in child.category_id.filtered(lambda x: len(ODOO_CERT_IDS & x)):
                certifs.append(certif)
            if certifs:
                certified_experts.append({
                    'partner': child,
                    'certifs': certifs
                })

        if partner.category_id.filtered(lambda x: len(ODOO_COMPANY_CERT_IDS & x)):
            partner_certif = partner.category_id.filtered(lambda x: len(ODOO_COMPANY_CERT_IDS & x))

        nbr_certified = len(certified_experts)

        if partner_grade:
            next_level_users = NEXT_GRADE_USERS_VALUE[partner_grade]
            next_level_certified = NEXT_GRADE_CERTIFIED_VALUE[partner_grade]
            next_level_com = NEXT_GRADE_COMMISSION_VALUE[partner_grade]

        return {
            'partner_grade': partner_grade,
            'partner_certif': partner_certif,
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
        country_code = request.session.geoip and request.session.geoip.get('country_code') or False
        if country_code:
            country = request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1)
        return country

    def _get_random_partner(self):
        Employee = request.env['hr.employee'].sudo()
        return Employee.browse(POINT_OF_CONTACT_IDS[randint(0, len(POINT_OF_CONTACT_IDS) - 1)]).user_id.partner_id

    def _values(self, access_token):
        Subscription = request.env['sale.subscription'].sudo()
        Lead = request.env['crm.lead'].sudo()

        # TODO: Use location to assign a saleman from the correct sale ZONE departement

        subscription = False
        saleman = False
        partner = False
        lead = False

        if access_token:
            subscription = Subscription.search([('uuid', '=', access_token), ('template_id.code', '=', "PART")], limit=1, order='create_date desc')
        elif not request.website.is_public_user():
            subscription = Subscription.search([('partner_id', '=', request.env.user.partner_id.commercial_partner_id.id), ('template_id.code', '=', "PART")], limit=1, order='create_date desc')

        if subscription:
            partner = subscription.partner_id
            saleman = subscription.user_id and subscription.user_id.partner_id
        else:
            if request.website.is_public_user():
                lead_id = Lead.decode(request)
                if lead_id:
                    lead = Lead.browse(lead_id)
                    saleman = lead.user_id.partner_id
                    partner = lead.partner_id  # - TODO
            else:
                partner = request.env.user.partner_id
                saleman = partner.user_id.partner_id

        if not saleman:
            print("NO SALEMAN")
            # saleman = request.session.get('saleman_id', self._get_random_partner())
            # request.session['saleman_id'] = saleman
            saleman = self._get_random_partner()

        country = (partner and partner.country_id) or (lead and lead.country_id) or self._get_geocountry()

        values = {}
        values.update(self._get_country_cached_stat(country.id))
        values.update(self._get_events(country))
        values.update({
            'saleman': saleman,
            'access_token': access_token,
            'country_id': country,
            'partner': partner,
        })
        # if subscription:

        if request.website.is_public_user() and not access_token:
            if lead:
                lead_pic = lead.env['ir.attachment'].search([('datas_fname', '=', 'profile_pic'), ('res_id', '=', lead.id)])['datas']
                values.update({
                    'street': lead.street,
                    'source': lead,
                    'source_email': lead.email_from,
                    'source_name': lead.contact_name,
                    'source_image': lead_pic,
                })
        else:  # partner set
            values.update(self._get_subscriptions(partner.id))
            values.update(self._get_purchase_orders(partner.id))
            values.update(self._get_grade(partner))
            values.update(self._get_opportunities(partner.id))
            values.update({
                'source': partner,
                'source_email': partner.email,
                'source_name': partner.name,
                'source_image': partner.image_medium,
                'currency': partner.country_id.currency_id.symbol,  # TODO FIX ME
                'my_sub': subscription,
            })

        return values

    @http.route(['/dashboard', '/dashboard/<access_token>'], type='http', auth="public", website=True)
    def dashboard_token(self, access_token=None, **kw):
        values = self._values(access_token)
        return request.render('partner_dashboard.dashboard', values)

    @http.route(['/dashboard/profile'], type='http', auth='public', website=True)
    def dasboardLead(self, redirect=None, **data):
        # Employees = request.env['hr.employee'].sudo()
        MANDATORY_FIELDS = ["name", "phone", "email", "street", "city", "country_id"]
        OPTIONAL_FIELDS = ["zipcode", "state_id", "vat", "company_name", "website_description"]

        error = {}
        error_message = []

        # if request.session.get('saleman_id'):
        #     saleman_id = request.session.get('saleman_id')
        #     if saleman_id:
        #         user_id = Employees.browse(saleman_id).user_id
        #     else:
        #         user_id = 0

        if request.website.is_public_user():
            partner = False
        else:
            partner = request.env.user.partner_id.commercial_partner_id

        if request.httprequest.method == 'POST':

            # Validation
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

                if data['image']:
                    file = request.httprequest.files['image']
                    img = base64.encodestring(file.stream.read())
                    values['image'] = img
                if not partner:
                    # partner = request.env['res.partner'].sudo().create(values)
                    lead = request.env['crm.lead'].sudo().create({
                        'name': "NEW PARTNERSHIP for %s" % values['name'],
                        'partner_name': values['company_name'],
                        'street': values['street'],
                        'city': values['city'],
                        'zip': values['zip'],
                        'country_id': values['country_id'],
                        'email_from': values['email'],
                        'phone': values['phone'],
                        'contact_name': values['name'],
                        # 'user_id': user_id.id,
                    })
                    if 'image' in values.keys():
                        attachment = {
                            'name': 'Profile Picture',
                            'datas': (values['image']),
                            'datas_fname': 'profile_pic',
                            'res_model': 'crm.lead',
                            'res_id': lead.id,
                        }

                        lead.env['ir.attachment'].create(attachment)
                    sign = lead.encode(lead.id)
                    resp.set_cookie('lead_id', sign)
                else:
                    if partner._vat_readonly(partner):
                        values.pop('vat')
                        values.pop('name')
                        values.pop('company_name')
                    partner = partner.write(values)
                return resp

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])

        data.update({
            'partner': partner or request.env["res.partner"],
            'countries': countries,
            'states': states,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'error': error,
            'error_message': error_message,
        })

        response = request.render("partner_dashboard.partner_form", data)
        return response

    @http.route('/dashboard/pricing', type='http', auth="public", website=True)
    def pricing(self, **kw):
        Products = request.env['product.product']

        learning_price = Products.browse(10)
        official_price = Products.browse(36)

        values = {
            'learning_price': learning_price,
            'official_price': official_price,
        }

        return request.render('partner_dashboard.plans_prices', values)
