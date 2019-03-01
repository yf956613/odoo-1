# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import Warning, UserError


class SlidePartnerRelation(models.Model):
    _inherit = 'slide.slide.partner'

    user_input_ids = fields.One2many('survey.user_input', 'slide_partner_id', 'Certification attempts')
    survey_quizz_passed = fields.Boolean('Certification Quizz Passed', compute='_compute_survey_quizz_passed', store=True)

    @api.depends('partner_id', 'user_input_ids.quizz_passed')
    def _compute_survey_quizz_passed(self):
        passed_user_inputs = self.env['survey.user_input'].sudo().search([
            ('slide_partner_id', 'in', self.ids),
            ('quizz_passed', '=', True)
        ])
        passed_slide_partners = passed_user_inputs.mapped('slide_partner_id')
        for record in self:
            record.survey_quizz_passed = record in passed_slide_partners


class Slide(models.Model):
    _inherit = 'slide.slide'

    slide_type = fields.Selection(selection_add=[('certification', 'Certification')])
    survey_id = fields.Many2one('survey.survey', 'Certification')

    _sql_constraints = [
        ('check_survey_id', "CHECK(slide_type != 'certification' OR survey_id IS NOT NULL)", "A slide of type 'certification' requires a certification."),
        ('check_certification_preview', "CHECK(slide_type != 'certification' OR is_preview = False)", "A slide of type certification cannot be previewed."),
    ]

    def _action_set_viewed(self, target_partner):
        """ If the slide viewed is a certification, we initialize the first survey.user_input
        for the current partner. """
        new_slide_partners = super(Slide, self)._action_set_viewed(target_partner)
        certification_slides = self.search([
            ('id', 'in', new_slide_partners.mapped('slide_id').ids),
            ('slide_type', '=', 'certification'),
            ('survey_id', '!=', False)
        ])

        for new_slide_partner in new_slide_partners:
            if new_slide_partner.slide_id in certification_slides and not new_slide_partner.user_input_ids:
                new_slide_partner.slide_id.survey_id._create_answer(
                    partner=target_partner,
                    check_attempts=False,
                    **{
                        'slide_id': new_slide_partner.slide_id.id,
                        'slide_partner_id': new_slide_partner.id
                    }
                )

    def action_get_slide_survey_url(self, slide):
        if not all(s.channel_id.is_member for s in self):
            raise UserError(_('You cannot have access to the certification if you are not among its members.'))

        return self._action_get_slide_survey_url(self.env.user.partner_id, slide)

    def _action_get_slide_survey_url(self, target_partner, slide):
        certification_url = None
        if not self.env.user._is_public() and slide.slide_type == 'certification' and slide.survey_id:
            if slide.channel_id.is_member:
                user_membership_id_sudo = slide.user_membership_id.sudo()
                quizz_passed = user_membership_id_sudo.survey_quizz_passed
                if not quizz_passed:
                    last_user_input = next(user_input for user_input in user_membership_id_sudo.user_input_ids.sorted(
                        lambda user_input: user_input.create_date, reverse=True
                    ))
                    certification_url = last_user_input._get_survey_url()
            else:
                user_input = slide.survey_id._create_answer(
                    partner=target_partner,
                    check_attempts=False,
                    test_entry=True, **{
                        'slide_id': slide.id
                    }
                )
                certification_url = user_input._get_survey_url()

        return certification_url