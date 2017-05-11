# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BaseModuleUpgrade(models.TransientModel):
    _name = "base.module.upgrade"
    _description = "Module Upgrade"

    @api.model
    def default_get(self, fields):
        res = super(BaseModuleUpgrade, self).default_get(fields)
        # modules = self.env['ir.module.module'].search([('id', 'in', self.env.context.get('active_ids'))])
        # if modules:
        #     deps = modules.downstream_dependencies(exclude_states=['uninstalled', 'uninstallable'])
        # print '<self.env',self.env.context.get('active_ids'), modules,deps
        res['module_id'] = self.env.context.get('active_id', False)
        return res

    module_id = fields.Many2one('ir.module.module', string='Module')
    icon_image = fields.Binary(related="module_id.icon_image")
    name = fields.Char(related="module_id.shortdesc")
    model_detail = fields.Char(compute="_compute_model_detail")
    impact_count = fields.Integer(compute="_compute_impacted_module")
    module_ids = fields.One2many('base.module.upgrade.line', 'upgrade_module_id', compute='_compute_module_ids', string='Impacted modules', readonly=True)

    @api.multi
    @api.depends('module_ids')
    def _compute_model_detail(self):
        for rec in self.filtered(lambda x: x.module_id):
            rec.model_detail = rec.module_ids.filtered(lambda x: x.module_id == rec.module_id).model_detail

    @api.multi
    @api.depends('module_ids')
    def _compute_impacted_module(self):
        for rec in self:
            rec.impact_count = len(rec.module_ids)

    @api.multi
    @api.depends('module_id')
    def _compute_module_ids(self):
        ModelData = self.env['ir.model.data']
        IrModel = self.env['ir.model']
        for wizard in self.filtered(lambda x: x.module_id):
            line = []
            dependencies = wizard.module_id.downstream_dependencies() + wizard.module_id
            for dep in dependencies:
                all_model_ids = ModelData.search([('module', '=', dep.name), ('model', '=', 'ir.model')]).mapped('res_id')
                text = []
                # TODO Later on move to mail by override for is_mail_thread
                for model in IrModel.browse(all_model_ids).filtered(lambda x: not x.transient and x.is_mail_thread):
                    other_declarations = ModelData.search([('module', '!=', dep.name), ('model', '=', 'ir.model'), ('res_id', '=', model.id)])
                    if not len(other_declarations):
                        model_obj = self.env.registry.get(model.model, False)
                        table_name = model_obj._table if model_obj else model.model.replace('.', '_')
                        self.env.cr.execute("SELECT reltuples AS row_qty FROM pg_class WHERE relname = '%s'" % table_name)
                        res = self.env.cr.fetchone()
                        if res and res[0]:
                            text.append((res[0], model.name))
                res = {
                    'module_id': dep.id,
                    'model_detail': ','.join("%s %s" % (int(x[0]), x[1]) for x in text) if text else False
                }
                line.append((0, 0, res))
            wizard.module_ids = line

    @api.multi
    def upgrade_module_cancel(self):
        Module = self.env['ir.module.module']
        to_install = Module.search([('state', 'in', ['to upgrade', 'to remove'])])
        to_install.write({'state': 'installed'})
        to_uninstall = Module.search([('state', '=', 'to install')])
        to_uninstall.write({'state': 'uninstalled'})
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def upgrade_module(self):
        Module = self.env['ir.module.module']

        # write state here instead of on unistallation wizard
        self.module_ids.write({'state': 'to remove'})
        # install/upgrade: double-check preconditions
        mods = Module.search([('state', 'in', ['to upgrade', 'to install'])])
        if mods:
            query = """ SELECT d.name
                        FROM ir_module_module m
                        JOIN ir_module_module_dependency d ON (m.id = d.module_id)
                        LEFT JOIN ir_module_module m2 ON (d.name = m2.name)
                        WHERE m.id in %s and (m2.state IS NULL or m2.state IN %s) """
            self._cr.execute(query, (tuple(mods.ids), ('uninstalled',)))
            unmet_packages = [row[0] for row in self._cr.fetchall()]
            if unmet_packages:
                raise UserError(_('The following modules are not installed or unknown: %s') % ('\n\n' + '\n'.join(unmet_packages)))

            mods.download()

        # terminate transaction before re-creating cursor below
        self._cr.commit()
        api.Environment.reset()
        odoo.modules.registry.Registry.new(self._cr.dbname, update_module=True)

        return {'type': 'ir.actions.act_window_close'}

class BaseModuleUpgradeLine(models.TransientModel):
    _name = "base.module.upgrade.line"
    _description = "Module Upgrade Line"

    upgrade_module_id = fields.Many2one('base.module.upgrade', required=True)
    module_id = fields.Many2one('ir.module.module', string="Module")
    shortdesc = fields.Char(related="module_id.shortdesc")
    name = fields.Char(related="module_id.name")
    # TODO mamaner to remove if installed
    state = fields.Selection(related="module_id.state")
    model_detail = fields.Char(string="Record Details")
