import odoo.tests
# Part of Odoo. See LICENSE file for full copyright and licensing details.

@odoo.tests.common.tagged('post_install','-at_install')
class TestUi(odoo.tests.HttpSeleniumCase):

    def test_01_admin_survey_tour(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('test_survey')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.test_survey.ready",
            login="admin")

    def test_02_demo_survey_tour(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('test_survey')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.test_survey.ready",
            login="demo")

    def test_03_public_survey_tour(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('test_survey')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.test_survey.ready")
