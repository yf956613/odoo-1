from odoo import models, fields, api


class WebsiteRewrite(models.Model):
    _name = 'website.rewrite'
    _description = "Website rewrite"

    label = fields.Char('Label', help='Reminder / Reason')
    website_id = fields.Many2one('website', help='Let empty to apply for all yours websites', string="Website", ondelete='cascade')
    active = fields.Boolean(default=True)
    url_from = fields.Char('URL from')
    url_to = fields.Char('URL to')
    redirect_type = fields.Selection([
        ('rewrite', 'Rewrite'),
        ('not_found', '404'),
        ('redirect_301', 'Moved permanently'),
        ('redirect_302', 'Moved temporarily')
    ], string='Action todo', default="rewrite")

    name = fields.Char(compute='_compute_name')
    sequence = fields.Integer()

    def _compute_name(self):
        self.name = self.label or "%s for %s" % (self.redirect_type, self.url_from)

    @api.model
    def create(self, vals):
        res = super(WebsiteRewrite, self).create(vals)
        self._invalidate_routing()
        return res

    def write(self, vals):
        res = super(WebsiteRewrite, self).write(vals)
        self._invalidate_routing()
        return res

    def unlink(self):
        res = super(WebsiteRewrite, self).unlink()
        self._invalidate_routing()
        return res

    def _invalidate_routing(self):
        # call clear_caches on all model for all other workers to reset routing's table
        self.pool.cache_invalidated = True
        self.pool.signal_changes()

        # call clear_caches on this worker to reload routing table
        self.env['ir.http'].clear_caches()
