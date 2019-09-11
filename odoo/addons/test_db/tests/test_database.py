# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import logging
from lxml import etree
from odoo.tests import common, tagged

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'migration')
class TestDatabase(common.SingleTransactionCase):
    def check_filter(self, name, model_id, domain, group_by, group_by_fields, sort, context):
        if group_by:
            try:
                self.env[model_id].with_context(context).read_group(domain, group_by_fields, group_by, orderby=sort)
            except ValueError as e:
                raise self.failureException("Test filter '%s' failed: %s" % (name, e)) from None
            except KeyError as e:
                raise self.failureException("Test filter '%s' failed: field or aggregate %s does not exist"% (name, e)) from None
        elif domain:
            try:
                self.env[model_id].with_context(context).search(domain, order=sort)
            except ValueError as e:
                raise self.failureException("Test filter '%s' failed: %s" % (name, e)) from None
        else:
            _logger.info("No domain or group by in filter %s with model %s and context %s", name, model_id, context)

    def test_filters(self):
        all_filters = self.env['ir.filters'].search([])
        for _filter in all_filters:
            name = _filter.name
            with self.subTest(name=name):
                model_id = _filter.model_id
                context = ast.literal_eval(_filter.context)
                domain = _filter._get_eval_domain()
                sort = ast.literal_eval(_filter.sort)
                group_by = context.get('group_by')
                group_by_fields = [field.split(':')[0] for field in group_by] if group_by else []
                self.check_filter(name, model_id, domain, group_by, group_by_fields, sort, context)

    @tagged('post_install', '-at_install', '-standard', 'migration')
    def test_views_filters(self):
        all_views = self.env['ir.ui.view'].with_context(lang=None).search([])
        for view in all_views:
            name = view.name
            with self.subTest(name=name):
                view._check_xml()
