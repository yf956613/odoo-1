from odoo import models, fields, api
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
        if not len(res):
            self.env['website.rewrite']._refresh()
            return super(WebsiteRoute, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
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

    name = fields.Char('Name', required=True)
    website_id = fields.Many2one('website', string="Website", ondelete='cascade')
    active = fields.Boolean(default=True)
    url_from = fields.Char('URL from')
    route_id = fields.Many2one('website.route')
    url_to = fields.Char("URL to")
    redirect_type = fields.Selection([
        ('not_found', '404 Not Found'),
        ('redirect_301', '301 Moved permanently'),
        ('redirect_302', '302 Moved temporarily'),
        ('rewrite', '308 Redirect / Rewrite'),
    ], string='Action', default="redirect_302",
        help='''Type of redirect/Rewrite:\n
        301 Moved permanently: The browser will keep in cache the new url.
        302 Moved temporarily: The browser will not keep in cache the new url and ask again the next time the new url.
        404 Not Found: If you want remove a specific page/controller (e.g. Ecommerce is installed, but you don't want /shop on a specific website)
        308 Redirect / Rewrite: If you want rename a controller with a new url. (Eg: /shop -> /garden - Both url will be accessible but /shop will automatically be redirected to /garden)
    ''')

    name = fields.Char(compute='_compute_name')
    sequence = fields.Integer()

    @api.onchange('route_id')
    def _onchange_route_id(self):
        self.url_from = self.route_id.path
        self.url_to = self.route_id.path

    def name_get(self):
        result = []
        for rewrite in self:
            name = rewrite.redirect_type + ' - ' + rewrite.name
            result.append((rewrite.id, name))
        return result

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
        if self.env['website.route'].check_access_rights('write'):
            self.env['website.route']._refresh()
        else:
            raise AccessDenied()
