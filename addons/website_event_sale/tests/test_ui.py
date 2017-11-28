import odoo.tests
import logging


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpSeleniumCase):

    logger = logging.getLogger(__name__)

    def test_admin(self):
        # Seen that:
        # - this test relies on demo data that are entirely in USD (pricelists)
        # - that main demo company is gelocated in US
        # - that this test awaits for hardcoded USDs amount
        # we have to force company currency as USDs only for this test
        self.env.ref('base.main_company').write({'currency_id': self.env.ref('base.USD').id})
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('event_buy_tickets')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.event_buy_tickets.ready",
            login="admin",
            max_tries=25)

    def test_demo(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('event_buy_tickets')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.event_buy_tickets.ready",
            login="demo",
            max_tries=25)

    # TO DO - add public test with new address when convert to web.tour format.
