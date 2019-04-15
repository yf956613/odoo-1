# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import ValidationError


class SurveyCertificationReportTemplate(models.Model):
    _name = "survey.certification.report.template"
    _description = "Certification report template"
    _rec_name = "name"

    name = fields.Char(required=True)
    certification_report_template_xml_id = fields.Char("Certification template", required=True)
    color_theme = fields.Char("Color theme", help="Used as a class name in the certification template.")

    @api.constrains('certification_report_template_xml_id')
    def _check_if_template_exists(self):
        template = self.env.ref(self.certification_report_template_xml_id, raise_if_not_found=False)
        if not template:
            raise ValidationError(_('Template id: %s not found') % (self.certification_report_template_xml_id))
