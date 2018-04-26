# -*- coding: utf-8 -*-
from odoo import http, tools, _
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime, timedelta
from random import randint
import json
import base64

from openerp.addons.saas_worker.util import ip2coordinates


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
        ODOO_EXP_ID = 12
        ODOO_TOUR_ID = 11
        Events = request.env['event.event'].sudo()
        today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        oxp = Events.search([('event_type_id', '=', ODOO_EXP_ID), ('date_begin', '>', today)], limit=1)
        tour = Events.search([('event_type_id', '=', ODOO_TOUR_ID), ('date_begin', '>', today)])

        local_tour = tour.filtered(lambda x: x.country_id == country_id)
        foreign_tour = tour.filtered(lambda x: x.country_id != country_id)
        return {'events': (oxp + local_tour + foreign_tour)[:3]}

    def _get_companies_size(self, country_id):
        Attachment = request.env['ir.attachment'].sudo()

        company_size = None

        dom = [('url', '=', '/company_size.json'), ('type', '=', 'url')]
        attachment = Attachment.search(dom, limit=1)
        if attachment:
            data_dict = json.loads(base64.b64decode(attachment.datas))

            index = 0
            while True:
                if data_dict[index]['country_id'] == country_id:
                    company_size = data_dict[index]['values']
                    break
                if index < len(data_dict) - 1:
                    index += 1
                else:
                    break

            company_size = json.dumps(company_size)
        else:
            company_size = 'Find no data for your country'

        return {
            'company_size': company_size
        }

    def _get_purchase_orders(self, partner_id):
        # assert not request.website.is_public_user()

        # TODO: see with avw / fp the process
        ENTERPRISE_USER_IDS = [350, 209, 208, ]
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

    def _get_country_stats(self, country_id):
        Leads = request.env['crm.lead'].sudo()
        Partners = request.env['res.partner']

        # TODO: preprocess?
        country_customers = Leads.search_count([('country_id', '=', country_id), ('partner_id', '!=', None)])
        country_leads = Leads.search_count([('country_id', '=', country_id)])
        country_partners = Partners.search_count([('country_id', '=', country_id), ('is_company', '=', True)])

        return {
            'country_leads': country_leads,
            'country_partners': country_partners,
            'country_customers': country_customers,
        }

    def _get_grade(self, partner):
        ODOO_CERT_IDS = request.env['res.partner.category'].sudo().search([('name', '=ilike', 'Certification%')])
        ODOO_COMPANY_CERT_IDS = request.env['res.partner.category'].sudo().search([('name', '=ilike', 'CTP Certif%')])
        NEXT_GRADE_USERS_VALUE = {'Bronze': 50, 'Silver': 100, 'Gold': 0, 'Platinum': -10}
        NEXT_GRADE_CERTIFIED_VALUE = {'Bronze': 2, 'Silver': 4, 'Gold': 0, 'Platinum': -10}
        NEXT_GRADE_COMMISSION_VALUE = {'Bronze': 10, 'Silver': 20, 'Gold': 0, 'Platinum': -10}
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

    def _get_location(self, ip_address=None):
        country_id = None
        location = {}
        if not ip_address:
            ip_address = request.httprequest.headers.get('X-Odoo-GeoIP') or request.httprequest.environ['REMOTE_ADDR']
        if ip_address:
            coordinates = ip2coordinates(ip_address)
            country_code = coordinates['country_code']
            country = request.env['res.country'].sudo().search([('code', '=', country_code.upper())], limit=1)
            country_id = country
            if coordinates.get('city'):
                location['city'] = coordinates['city']
            if coordinates.get('longitude'):
                location['partner_longitude'] = float(coordinates['longitude'])
            if coordinates.get('latitude'):
                location['partner_latitude'] = float(coordinates['latitude'])
            if coordinates.get('region'):
                state = country.state_ids.filtered(lambda x: x.code == coordinates.get('region'))
                location['state_id'] = state and state[0].id
        return {
            'country_id': country_id,
            'location': location,
        }

    def values(self, access_token):
        Partner = request.env['res.partner'].sudo()
        Subscription = request.env['sale.subscription'].sudo()

        Lead = request.env['crm.lead']

        point_of_contact = [42, 43, 6, 3]

        values = {}
        is_access_token = False

        if access_token:
            is_access_token = True
            sub = Subscription.search([('uuid', '=', access_token), ('template_id.code', '=', "PART")])
            if sub:
                partner = sub.partner_id
        else:
            partner = request.env.user.partner_id

        saleman = Partner.browse(point_of_contact[randint(0, len(point_of_contact) - 1)])
        my_sub = Subscription.search([('partner_id', '=', partner.id), ('template_id.code', '=', "PART")], limit=1, order='create_date desc')

        if my_sub:
            if my_sub.user_id:
                saleman = Partner.browse(my_sub.user_id.partner_id.id)

        if request.website.is_public_user() and Lead.decode(request) and not access_token:
            lead = Lead.sudo().browse(Lead.decode(request))
            lead_pic = lead.env['ir.attachment'].search([('datas_fname', '=', 'profile_pic'), ('res_id', '=', lead.id)])['datas']
            values = {
                'saleman': saleman,
            }
            if not lead.country_id:
                values.update(self._get_location())
                values.update(self._get_country_stats(values['country_id'].id))
                values.update(self._get_events(values['country_id']))
                values.update(self._get_companies_size(values['country_id'].id))

            else:
                values.update(self._get_country_stats(lead.country_id.id))
                values.update(self._get_events(lead.country_id))
                values.update(self._get_companies_size(lead.country_id.id))
                values.update({'country_id': lead.country_id})

            values.update({
                'partner': False,
                'basic_infos': True,
                'street'
                'access_token': is_access_token,
                'partner_name': lead.contact_name,
                'partner_image': lead_pic,
                'source': lead,
                'email': lead.email_from,
            })

        elif request.website.is_public_user() and not access_token:
            values = {
                'saleman': saleman,
            }
            values.update(self._get_location())
            values.update(self._get_country_stats(values['country_id'].id))
            values.update(self._get_events(values['country_id']))
            values.update(self._get_companies_size(values['country_id'].id))
            values.update({
                'partner': False,
                'basic_infos': False,
                'access_token': is_access_token,
            })

        else:
            values = self._get_subscriptions(partner.id)
            values.update(self._get_purchase_orders(partner.id))
            values.update(self._get_grade(partner))
            values.update(self._get_opportunities(partner.id))

            if not partner.country_id:
                values.update(self._get_location())
                values.update(self._get_country_stats(values['country_id'].id))
                values.update(self._get_events(values['country_id']))
                values.update(self._get_companies_size(values['country_id'].id))

            else:
                values.update(self._get_country_stats(partner.country_id.id))
                values.update(self._get_events(partner.country_id))
                values.update(self._get_companies_size(partner.country_id.id))
                values.update({'country_id': partner.country_id})

            values.update({
                'partner': partner,
                'partner_name': partner.name,
                'partner_image': partner.image_medium,
                'currency': partner.country_id.currency_id.symbol,
                'my_sub': my_sub,
                'saleman': saleman,
                'access_token': is_access_token,
                'source': partner,
                'email': partner.email,
            })

        return values

    @http.route(['/dashboard', '/dashboard/<access_token>'], type='http', auth="public", website=True)
    def dashboard_token(self, access_token=None, **kw):
        return request.render('partner_dashboard.dashboard', self.values(access_token))

    @http.route(['/dashboard/profile'], type='http', auth='public', website=True)
    def dasboardLead(self, redirect=None, **data):
        MANDATORY_FIELDS = ["name", "phone", "email", "street", "city", "country_id"]
        OPTIONAL_FIELDS = ["zipcode", "state_id", "vat", "company_name", "website_description"]

        error = {}
        error_message = []

        if request.website.is_public_user():
            partner = False
        else:
            partner = request.env.user.partner_id.commercial_partner_id

            # if partner._vat_readonly(partner):
                # data.pop('vat')
                # data.pop('name')
                # data.pop('company_name')

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
                        'name': "NEW PARTNERSHIP !! %s" % values['name'],
                        'partner_name': values['company_name'],
                        'street': values['street'],
                        'city': values['city'],
                        'zip': values['zip'],
                        'country_id': values['country_id'],
                        'email_from': values['email'],
                        'phone': values['phone'],
                        'contact_name': values['name'],
                        'description': values['website_description'],
                    })

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
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @http.route('/dashboard/pricing', type='http', auth="public", website=True)
    def pricing(self, **kw):
        Products = request.env['product.product']

        learning_price = Products.sudo().browse(10)
        official_price = Products.sudo().browse(36)
        # first_year_discount = Products.sudo().browse(5216)

        if request.website.is_public_user():
            currency = self._get_location()['country_id'].currency_id
        else:
            partner = request.env.user.partner_id
            currency = partner.country_id.currency_id

        values = {
            'learning_price': learning_price,
            'official_price': official_price,
            # 'first_year_discount': first_year_discount,
            'currency': currency,
        }

        return request.render('partner_dashboard.plans_prices', values)
