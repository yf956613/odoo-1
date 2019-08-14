# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import  api, models
from odoo.exceptions import UserError


class CompanyConsistencyMixin(models.AbstractModel):
    _name = "company.consistency.mixin"
    _description = 'Company Consistency Mixin'

    @api.model
    def _company_consistency_m2o_required_cid_fields(self):
        return []

    @api.model
    def _company_consistency_m2o_optional_cid_fields(self):
        return []

    @api.model
    def _company_consistency_m2o_property_required_cid_fields(self):
        return []

    @api.model
    def _company_consistency_m2o_property_optional_cid_fields(self):
        return []

    @api.model
    def _company_consistency_m2m_required_cid_fields(self):
        return []

    @api.model
    def _company_consistency_m2m_optional_cid_fields(self):
        return []

    @api.model
    def _company_consistency_fields(self):
        fields = self._company_consistency_m2o_required_cid_fields() + \
            self._company_consistency_m2o_optional_cid_fields() + \
            self._company_consistency_m2o_property_required_cid_fields() + \
            self._company_consistency_m2o_property_optional_cid_fields() + \
            self._company_consistency_m2m_required_cid_fields() + \
            self._company_consistency_m2m_optional_cid_fields()
        return fields

    def _company_consistency_check(self):
        for rec in self:
            company_to_compare_to = rec.company_id if rec._name != 'res.company' else rec
            # Check consistency with many2one on which company_id is required.
            for field in self._company_consistency_m2o_required_cid_fields():
                if rec[field] and not (rec[field]['company_id'] == company_to_compare_to):
                    raise UserError("Company inconsistent with %s." % field)

            # Check consistency with many2one on which company_id is not required.
            for field in self._company_consistency_m2o_optional_cid_fields():
                if rec[field] and not (rec[field]['company_id'] == company_to_compare_to or not rec[field]['company_id'].id):
                    raise UserError("Company inconsistent with %s." % field)

            # Check consistency with many2many on which company_id is required.
            for field in self._company_consistency_m2m_required_cid_fields():
                for item in rec[field]:
                    if item and not (item['company_id'] == company_to_compare_to):
                        raise UserError("Company inconsistent with %s." % field)

            # Check consistency with many2many on which company_id is not required.
            for field in self._company_consistency_m2m_optional_cid_fields():
                for item in rec[field]:
                    if item and not (item['company_id'] == company_to_compare_to or not item['company_id'].id):
                        raise UserError("Company inconsistent with %s." % field)

            # Check consistency with property many2one. As these are property fields, we compare
            # with the company into which the property will be set.
            if self.env.context.get('force_company'):
                property_company_to_compare_to = self.env['res.company'].browse(self.env.context['force_company'])
            else:
                property_company_to_compare_to = self.env.company

            # Check consistency with property many2one on which company_id is required.
            for field in self._company_consistency_m2o_property_required_cid_fields():
                if rec[field] and not (rec[field]['company_id'] == property_company_to_compare_to):
                    raise UserError("Company inconsistent with %s." % field)

            # Check consistency with property many2one on which company_id is not required.
            for field in self._company_consistency_m2o_property_optional_cid_fields():
                if rec[field] and not (rec[field]['company_id'] == property_company_to_compare_to or not rec[field]['company_id'].id):
                    raise UserError("Company inconsistent with %s." % field)

