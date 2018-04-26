# -*- coding: utf-8 -*-

from odoo import models
from odoo.http import request
import json
import base64


class partner_dashboard(models.Model):
    _name = 'partner_dashboard.partner_dashboard'

    def _define_companies_size(self):
        Leads = request.env['crm.lead']
        Attachment = request.env['ir.attachment'].sudo()

        mimetype = 'application/json;charset=utf-8'

        def create_attachment(url):
            return Attachment.create({
                'mimetype': mimetype,
                'type': 'url',
                'name': url,
                'url': url,
            })

        dom = [('url', '=', '/company_size.json'), ('type', '=', 'url')]

        Attachment.search(dom, limit=1).unlink()

        if not Attachment.search(dom, limit=1):
            create_attachment('/company_size.json')

        size_tag_ids = {'< 5': 20, '5-20': 12, '20-50': 22, '50-250': 23, '> 250': 24, }
        size_tag_value = []

        index = -1
        for country in request.env['res.country'].search([]):
            size_tag_value.append({'country_id': country.id, 'values': []})
            index += 1
            for key in size_tag_ids:
                size_tag_value[index]['values'].append({"label": key, 'value': Leads.sudo().search_count([('tag_ids', '=', size_tag_ids[key]), ('country_id', '=', country.id)])})

        to_render = json.dumps(size_tag_value)

        attachment = Attachment.search(dom, limit=1)
        attachment.write({"datas": base64.b64encode(to_render.encode("utf-8"))})
