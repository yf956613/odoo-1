# -*- coding: utf-8 -*-

from odoo import models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date
import base64
import json
from . import consts


class Country(models.Model):
    _inherit = 'res.country'

    def _get_events(self):
        Events = self.env['event.event'].sudo()
        today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        oxp = Events.search([('event_type_id', '=', consts.ODOO_EXP_ID), ('date_begin', '>', today)], limit=1)
        tour = Events.search([('event_type_id', '=', consts.ODOO_TOUR_ID), ('date_begin', '>', today)])

        local_tour = tour.filtered(lambda x: x.country_id == self.id)
        foreign_tour = tour.filtered(lambda x: x.country_id != self.id)
        return {'events': (oxp + local_tour + foreign_tour)[:3]}

    def _get_country_cached_stat(self):
        attachment = self.env.ref('partner_dashboard.dashboard_partner_stats').sudo()
        if not attachment.datas:
            self.env['crm.lead']._refresh_dashboard_data()
        data_dict = json.loads(base64.b64decode(attachment.datas))
        country_dict = next(filter(lambda x: x['country_id'] == self.id, data_dict))
        return {
            'company_size': json.dumps(country_dict['lead_by_company_size']),
            'country_leads': country_dict['country_leads'],
            'country_partners': country_dict['country_partners'],
            'country_customers': country_dict['country_customers'],
        }
