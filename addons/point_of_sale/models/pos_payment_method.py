from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    """ Used to classify pos.payment.

    Generic characteristics of a pos.payment is described in this model.
    E.g. A cash payment can be described by a pos.payment.method with
    fields: is_cash_count = True and a cash_journal_id set to an
    `account.journal` (type='cash') record.

    When a pos.payment.method is cash, cash_journal_id is required as
    it will be the journal where the account.bank.statement.line records
    will be created.
    """

    _name = "pos.payment.method"
    _description = "Point of Sale Payment Methods"
    _order = "id asc"

    name = fields.Char(string="Payment Method", required=True)
    receivable_account_id = fields.Many2one('account.account',
        string='Intermediary Account',
        required=True,
        domain=[('reconcile', '=', True), ('user_type_id.type', '=', 'receivable')],
        default=lambda self: self.env.company.default_pos_receivable_account_id,
        help='Account used as counterpart of the income account in the accounting entry representing the pos sales.')
    is_cash_count = fields.Boolean(string='Cash')
    cash_journal_id = fields.Many2one('account.journal',
        string='Cash Journal',
        domain=[('type', '=', 'cash')],
        help='The payment method is of type cash. A cash statement will be automatically generated.')
    split_transactions = fields.Boolean(
        string='Split Transactions',
        default=False,
        help='If ticked, each payment will generate a separated journal item. Ticking that option will slow the closing of the PoS.')
    session_ids = fields.Many2many('pos.session', string='Pos Sessions', help='Pos sessions that are using this payment method.')
    config_ids = fields.Many2many('pos.config', string='Point of Sale Configurations')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.onchange('is_cash_count')
    def _onchange_is_cash_count(self):
        if not self.is_cash_count:
            self.cash_journal_id = False

    def write(self, vals):
        active_sessions = self.mapped('session_ids').filtered(lambda session: session.state != 'closed')
        if active_sessions:
            raise UserError('Modifying payment methods used in an open session is not allowed.\n'
                            'Open sessions: %s' % (' '.join(active_sessions.mapped('name')),))
        return super(PosPaymentMethod, self).write(vals)

    @api.model
    def generate_bank_and_cash_payment_methods(self, company=None):
        """ Used to create bank and cash payment methods.

        The purpose of this function is to automatically generate
        bank and cash payment methods when PoS module is installed
        or when chart of accounts is installed in a company.

        Thus, this is called when loading PoS data and in the inherited
        function `_create_bank_journals` of account.chart.template model.
        """
        company = company or self.env.company
        if not company.chart_template_id:
            # Do not proceed if no chart of accounts is installed in the company.
            return

        pos_receivable_account = company.default_pos_receivable_account_id
        cash_journals = self.env['account.journal'].search([('company_id', '=', company.id), ('type', '=', 'cash')])

        cash_payment_method_ids = self.env['pos.payment.method'].create({
            'name': _('Cash'),
            'receivable_account_id': pos_receivable_account.id,
            'is_cash_count': True,
            'cash_journal_id': cash_journals[0].id,
            'company_id': company.id,
        }).ids if cash_journals else []

        bank_payment_method_ids = self.env['pos.payment.method'].create({
            'name': _('Bank'),
            'receivable_account_id': pos_receivable_account.id,
            'is_cash_count': False,
            'company_id': company.id,
        }).ids

        main_shop = self.env.ref('point_of_sale.pos_config_main', raise_if_not_found=False)
        # pos_config_main might belong to other company. If so, do not add the payment methods.
        if main_shop and main_shop.company_id == company:
            main_shop.with_context(force_company=company.id).write(
                {"payment_method_ids": [(6, 0, cash_payment_method_ids + bank_payment_method_ids)]}
            )
