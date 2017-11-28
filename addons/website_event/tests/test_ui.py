import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpSeleniumCase):
    def test_admin(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('event')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.event.ready",
            login='admin')
