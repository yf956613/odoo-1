# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class MailActivityFeedback(models.TransientModel):
    _name = 'mail.activity.feedback'
    _description = "Log Activity Feedback"

    activity_id = fields.Many2one('mail.activity', 'Activity')
    feedback = fields.Html('Feedback')

    @api.multi
    def action_done(self):
        self.ensure_one()
        self.activity_id.feedback = self.feedback
        return self.activity_id.action_done()

    @api.multi
    def action_done_schedule_next(self):
        self.ensure_one()
        ctx = self._context.copy()
        ctx.update({'default_res_id': self.activity_id.res_id, 'default_res_model': self.activity_id.res_model})
        self.action_done()
        return {
            'name': _('Schedule Activity'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.activity',
            'target': 'new',
            'context': ctx,
            'res_id': False
        }
