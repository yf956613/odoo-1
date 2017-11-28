from odoo.tests import HttpSeleniumCase, tagged


@odoo.tests.tagged('post_install','-at_install')
class TestUi(HttpSeleniumCase):

    def test_01_admin_bank_statement_reconciliation(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web.Tour'].run('bank_statement_reconciliation', 'test')",
            ready="odoo.__DEBUG__.services['web.Tour'].tours.bank_statement_reconciliation",
            login="admin")
