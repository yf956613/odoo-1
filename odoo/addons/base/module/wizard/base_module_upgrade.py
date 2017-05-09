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
        modules = self.env['ir.module.module'].search([('id', 'in', self.env.context.get('active_ids'))])
        if modules:
            deps = modules.downstream_dependencies(exclude_states=['uninstalled', 'uninstallable'])
        print '<self.env',self.env.context.get('active_ids'), modules,deps
        res['module_id'] = self.env.context.get('active_id', False)
        return res

    module_id = fields.Many2one('ir.module.module', string='Module')
    module_ids = fields.One2many('base.module.upgrade.line', 'upgrade_module_id', compute='_compute_module_ids', string='Impacted modules', readonly=True)

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
                print 'innnnnnnnnn',dep.name
                text = []
                # TODO Later on move to mail by override for is_mail_thread
                for model in IrModel.browse(all_model_ids).filtered(lambda x: not x.transient and x.is_mail_thread):
                    other_declarations = ModelData.search([('module', '!=', dep.name), ('model', '=', 'ir.model'), ('res_id', '=', model.id)])
                    if not len(other_declarations):
                        model_obj = self.env.registry.get(model.model, False)
                        table_name = model_obj._table if model_obj else model.model.replace('.', '_')
                        self.env.cr.execute("SELECT reltuples AS row_qty FROM pg_class WHERE relname = '%s'" % table_name)
                        res = self.env.cr.fetchone()
                        text.append((res[0], model.name))
                res = {
                    'module_id': dep.id,
                    'model_detail': ','.join("%s (%s)" % (x[1], int(x[0])) for x in text)
                }
                line.append((0, 0, res))
            wizard.module_ids = line

    # @api.model
    # @api.returns('ir.module.module')
    # def get_module_list(self):
    #     states = ['to upgrade', 'to remove', 'to install']
    #     return self.env['ir.module.module'].search([('state', 'in', states)])

    # @api.model
    # def _default_module_info(self):
    #     return "\n".join("%s: %s" % (mod.name, mod.state) for mod in self.get_module_list())

    # module_info = fields.Text('Apps to Update', readonly=True, default=_default_module_info)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(BaseModuleUpgrade, self).fields_view_get(view_id, view_type, toolbar=toolbar,submenu=False)
        if view_type != 'form':
            return res

        if not(self._context.get('active_model') and self._context.get('active_id')):
            return res

        # if not self.get_module_list():
        #     res['arch'] = '''<form string="Upgrade Completed" version="7.0">
        #                         <separator string="Upgrade Completed" colspan="4"/>
        #                         <footer>
        #                             <button name="config" string="Start Configuration" type="object" class="btn-primary"/>
        #                             <button special="cancel" string="Close" class="btn-default"/>
        #                         </footer>
        #                      </form>'''

        return res

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

    @api.multi
    def config(self):
        return self.env['res.config'].next()

class BaseModuleUpgradeLine(models.TransientModel):
    _name = "base.module.upgrade.line"
    _description = "Module Upgrade Line"

    upgrade_module_id = fields.Many2one('base.module.upgrade', required=True)
    module_id = fields.Many2one('ir.module.module', string="Module")
    model_detail = fields.Char(string="Record Details")

    # @api.multi
    # @api.depends('upgrade_module_id')
    # def _compute_model_detail(self):
    #     for wizard in self.filtered(lambda x: x.upgrade_module_id):
    #         wizard.model_detail = wizard.module_id.downstream_dependencies()
