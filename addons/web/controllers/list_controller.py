# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http
from odoo.http import request
from odoo.tools.misc import xlwt


HEADER_BOLD = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25;")

class TableListExporter(http.Controller):

    @http.route('/web/list/check_xlwt', type='json', auth='none')
    def check_xlwt(self):
        return xlwt is not None

    def _write_group_header(self, worksheet, x, y, group, columns, group_depth=0):
        aggregates = group.get('aggregateValues', {})
        title = group.get('value')

        if group.get('hideHeader'):
            return x, y

        title = '%s %s (%s)' % ('>' * group_depth, title, group.get('count', 0))
        worksheet.write(x, y, title, HEADER_BOLD)
        for column in columns[1:]: # No aggregates allowed in the first column
            y += 1
            worksheet.write(x, y, aggregates.get(column['field'], ''), HEADER_BOLD)
        return x + 1, 0

    def _write_record(self, worksheet, x, y, record, columns):
        for column in columns:
            worksheet.write(x, y, record.get(column['field']))
            y += 1
        return x + 1, 0

    def _write_groups(self, worksheet, x, y, groups, columns, group_depth=0):
        """
        Write groups to the xls worksheet. Recursive if groups are nested (chained groupby)
        :param worksheet:
        :param x: start position where to write the group (vertical axis, pointing downward)
        :param y: start position where to write the group (horizontal axis, pointing to the right)
        :param groups:  list of groups. Each group is a dict containing either records' data
                        or sub-groups. A group has the following structure:
                            'data': list of records or list of sub-groups
                            'isGrouped': True if data contains sub-groups
                            'value': title of the group
                            'count': number of records in the group
                            'aggregateValues': dict container aggregated values of fields {field: aggregatedValue, ...}
                            'hideHeader': self explanatory, used when the records are not grouped at all.
        :param columns: list of displayed columns. Each column is a dict with the following keys:
                            'field': field name
                            'aggregateValue': aggregate for all records
                            'string':
        """
        for group in groups:
            if group['isGrouped']:
                # Recursively write sub-groups
                x, y = self._write_group_header(worksheet, x, y, group, columns, group_depth)
                x, y = self._write_groups(worksheet, x, y, group['data'], columns, group_depth + 1)
            else:
                x, y = self._write_group_header(worksheet, x, y, group, columns, group_depth)
                for record in group['data']:
                    x, y = self._write_record(worksheet, x, y, record, columns)
        return x, y

    @http.route('/web/list/export_xls', type='http', auth="user")
    def export_xls(self, data, token):
        data = json.loads(data)
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('My awesome title')
        bold = xlwt.easyxf("font: bold on;")

        columns = data['columns']
        groups = data['groups']

        # Write main header
        for y, field in enumerate(columns):
            worksheet.write(0, y, field['string'], bold)

        # Write data
        x, y = 1, 0
        x, y = self._write_groups(worksheet, x, y, groups, columns)

        # Write column aggregates
        for y, field in enumerate(columns):
            worksheet.write(x, y, field.get('aggregateValue', ''), bold)

        response = request.make_response(None,
            headers=[('Content-Type', 'application/vnd.ms-excel'),
                    ('Content-Disposition', 'attachment; filename=table.xls')],
            cookies={'fileToken': token})
        workbook.save(response.stream)

        return response
