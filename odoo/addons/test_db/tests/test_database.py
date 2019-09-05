# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import logging
from lxml import etree
from odoo.tests import common, tagged
from odoo.tools.view_validation import get_attrs_field_names, Metamorph

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'migration')
class ToolTest(common.TransactionCase):
    def test_get_attrs_field_names(self):
        def test_arch(model, arch):
            node = etree.fromstring(arch)
            attrs_fields = get_attrs_field_names(self.env, node, self.env[model], False)
            for elem in attrs_fields:
                print(elem)
        test_arch('res.partner', """<filter name="test_filter" domain="[('fielsd1.test', '=', is_1 or accept(is_2) and True), ('fielsd2', '=', company_id.property)]"/>""")
        #test_arch('res.partner', """<filter name="test_filter" domain="[['fielsd1', '=', True], ['fielsd2', '=', company_id]]"/>""")
        #test_arch('res.partner', """<filter name="test_filter" domain="[('fielsd1', '=', is_1 or is_2)]"/>""")
        #test_arch('res.partner', """<filter name="test_filter" domain="[('fielsd1', '=', True), ('fielsd2', '=', company_id)]" context="{'group_by':'state'}"/>""")
        #test_arch('account.account', """<field name="asset_model" domain="[('state', '=', 'model')]" attrs="{'invisible': ['|', ('create_asset', '=', 'no'), ('can_create_asset', '=', False)], 'required': ['&amp;', ('create_asset', '=', 'validate'), ('can_create_asset', '=', True)]}" nolabel="1" context="{'default_state': 'model', 'form_view_ref': form_view_ref, 'default_asset_type': asset_type}"/>""")
        #test_arch('res.config.settings', """<field name="sale_tax_id" domain="[('type_tax_usea', 'in', ('sale', 'all')), ('company_ida', '=', company_id)]"/>""")
   

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
