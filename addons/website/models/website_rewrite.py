from odoo import models, fields, api, _
from odoo.exceptions import AccessDenied

import logging
_logger = logging.getLogger(__name__)


class WebsiteRoute(models.Model):
    _rec_name = 'path'
    _name = 'website.route'
    _description = "All Website Route"

    path = fields.Char('Route')

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        res = super(WebsiteRoute, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        if not len(res) and not self.env.context.get('refreshing'):
            self.env['website.rewrite'].refresh_routes()  # force group check
            return self.with_context(refreshing=1)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        return res

    def _refresh(self):
        _logger.warning("Refreshing website.route")
        ir_http = self.env['ir.http']
        tocreate = []
        paths = {rec.path: rec for rec in self.search([])}
        for u, e, r in ir_http._generate_routing_rules(self.pool._init_modules, converters=ir_http._get_converters()):
            if 'GET' in (r.get('methods') or ['GET']):
                if paths.get(u):
                    paths.pop(u)
                else:
                    tocreate.append({'path': u})

        if tocreate:
            _logger.info("Add %d website.route" % len(tocreate))
            self.create(tocreate)

        if paths:
            find = self.search([('path', 'in', list(paths.keys()))])
            _logger.info("Delete %d website.route" % len(find))
            find.unlink()


class WebsiteRewrite(models.Model):
    _name = 'website.rewrite'
    _description = "Website rewrite"

    label = fields.Char('Label', help='Reminder / Reason')
    website_id = fields.Many2one('website', string="Website", ondelete='cascade')
    active = fields.Boolean(default=True)
    url_from = fields.Char('URL from')
    route_id = fields.Many2one('website.route')
    url_to = fields.Char("URL to")
    redirect_type = fields.Selection([
        ('not_found', '404 - Not Found'),
        ('redirect_301', 'Moved permanently'),
        ('redirect_302', 'Moved temporarily'),
        ('rewrite', 'Rewrite'),
    ], string='Action todo', default="redirect_302")

    name = fields.Char(compute='_compute_name')
    sequence = fields.Integer()

    @api.onchange('route_id')
    def _onchange_route_id(self):
        self.url_from = self.route_id.path
        self.url_to = self.route_id.path

    def _compute_name(self):
        self.name = self.label or _("%s for %s") % (self.redirect_type, self.url_from)

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
        # call clear_caches on this worker to reload routing table
        self.env['ir.http'].clear_caches()

    def refresh_routes(self):
        if self.env.user.has_group('website.group_website_designer'):
            self.env['website.route']._refresh()
        else:
            raise AccessDenied()
