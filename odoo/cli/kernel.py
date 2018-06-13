# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from ipykernel.ipkernel import IPythonKernel
from ipykernel.kernelapp import IPKernelApp

from . import Command


class OdooKernel(IPythonKernel):
    @property
    def banner(self):
        return self.shell.banner + 'Odoo %s Shell' % odoo.release.version

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        res = super(OdooKernel, self).do_execute(code,
                                                 silent,
                                                 store_history=store_history,
                                                 user_expressions=user_expressions,
                                                 allow_stdin=allow_stdin)
        res = self.shell.run_cell('env.cr.commit()', store_history=False, silent=True)
        return res


class Kernel(Command):
    def init(self, args):
        self.connection_file = args.pop(0)
        odoo.tools.config.parse_config(args)
        self.dbname = odoo.tools.config['db_name']
        odoo.cli.server.report_configuration()
        odoo.service.server.start(preload=[], stop=True)

    def console(self, local_vars):
        IPKernelApp.launch_instance(
            kernel_class=OdooKernel,
            argv=[],
            user_ns=local_vars,
            connection_file=self.connection_file)

    def kernel(self):
        local_vars = {
            'openerp': odoo,
            'odoo': odoo,
        }
        with odoo.api.Environment.manage():
            if self.dbname:
                registry = odoo.registry(self.dbname)
                with registry.cursor() as cr:
                    uid = odoo.SUPERUSER_ID
                    ctx = odoo.api.Environment(cr, uid, {})['res.users'].context_get()
                    env = odoo.api.Environment(cr, uid, ctx)
                    local_vars['env'] = env
                    local_vars['self'] = env.user
                    self.console(local_vars)
                    cr.rollback()
            else:
                self.console(local_vars)

    def run(self, args):
        self.init(args)
        self.kernel()
        return 0
