# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero


class PosSession(models.Model):
    _name = 'pos.session'
    _order = 'id desc'
    _description = 'Point of Sale Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    POS_SESSION_STATE = [
        ('new_session', 'New Session'),
        ('opening_control', 'Opening Control'),  # method action_pos_session_open
        ('opened', 'In Progress'),               # method action_pos_session_closing_control
        ('closing_control', 'Closing Control'),  # method action_pos_session_close
        ('closed', 'Closed & Posted'),
    ]

    company_id = fields.Many2one('res.company', related='config_id.company_id', string="Company", readonly=True)

    config_id = fields.Many2one(
        'pos.config', string='Point of Sale',
        help="The physical point of sale you will use.",
        required=True,
        index=True)
    name = fields.Char(string='Session ID', required=True, readonly=True, default='/')
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        required=True,
        index=True,
        readonly=True,
        states={'opening_control': [('readonly', False)]},
        default=lambda self: self.env.uid)
    currency_id = fields.Many2one('res.currency', related='config_id.currency_id', string="Currency", readonly=False)
    start_at = fields.Datetime(string='Opening Date', readonly=True)
    stop_at = fields.Datetime(string='Closing Date', readonly=True, copy=False)

    state = fields.Selection(
        POS_SESSION_STATE, string='Status',
        required=True, readonly=True,
        index=True, copy=False, default='new_session')

    sequence_number = fields.Integer(string='Order Sequence Number', help='A sequence number that is incremented with each order', default=1)
    login_number = fields.Integer(string='Login Sequence Number', help='A sequence number that is incremented each time a user resumes the pos session', default=0)

    cash_control = fields.Boolean(compute='_compute_cash_all', string='Has Cash Control')
    cash_journal_id = fields.Many2one('account.journal', compute='_compute_cash_all', string='Cash Journal', store=True)
    cash_register_id = fields.Many2one('account.bank.statement', compute='_compute_cash_all', string='Cash Register', store=True)

    cash_register_balance_end_real = fields.Monetary(
        related='cash_register_id.balance_end_real',
        string="Ending Balance",
        help="Total of closing cash control lines.",
        readonly=True)
    cash_register_balance_start = fields.Monetary(
        related='cash_register_id.balance_start',
        string="Starting Balance",
        help="Total of opening cash control lines.",
        readonly=True)
    cash_register_total_entry_encoding = fields.Monetary(
        compute='_compute_cash_balance',
        string='Total Cash Transaction',
        readonly=True,
        help="Total of all paid sales orders")
    cash_register_balance_end = fields.Monetary(
        compute='_compute_cash_balance',
        digits=0,
        string="Theoretical Closing Balance",
        help="Sum of opening balance and transactions.",
        readonly=True)
    cash_register_difference = fields.Monetary(
        compute='_compute_cash_balance',
        string='Difference',
        help="Difference between the theoretical closing balance and the real closing balance.",
        readonly=True)

    order_ids = fields.One2many('pos.order', 'session_id',  string='Orders')
    order_count = fields.Integer(compute='_compute_order_count')
    statement_ids = fields.One2many('account.bank.statement', 'pos_session_id', string='Cash Statements', readonly=True)
    picking_count = fields.Integer(compute='_compute_picking_count')
    rescue = fields.Boolean(string='Recovery Session',
        help="Auto-generated session for orphan orders, ignored in constraints",
        readonly=True,
        copy=False)
    move_id = fields.Many2one('account.move', string='Journal Entry')
    payment_method_ids = fields.Many2many('pos.payment.method', related='config_id.payment_method_ids', string='Payment Methods')
    total_payments_amount = fields.Float(compute='_compute_total_payments_amount', string='Total Payments Amount')
    cash_payment_method_id = fields.Many2one('pos.payment.method', string='Cash payment method')
    is_in_company_currency = fields.Boolean('Is Using Company Currency', compute='_compute_is_in_company_currency')

    _sql_constraints = [('uniq_name', 'unique(name)', "The name of this POS Session must be unique !")]

    @api.depends('currency_id', 'company_id.currency_id')
    def _compute_is_in_company_currency(self):
        for session in self:
            session.is_in_company_currency = session.currency_id == session.company_id.currency_id

    @api.depends('payment_method_ids', 'order_ids', 'cash_register_balance_start', 'cash_register_id')
    def _compute_cash_balance(self):
        for session in self.filtered(lambda session: session.config_id.cash_control):
            total_cash_payment = sum(session.order_ids.mapped('payment_ids').filtered(lambda payment: payment.payment_method_id == session.cash_payment_method_id).mapped('amount'))
            session.cash_register_total_entry_encoding = session.cash_register_id.total_entry_encoding + (
                0.0 if session.state == 'closed' else total_cash_payment
            )
            session.cash_register_balance_end = session.cash_register_balance_start + session.cash_register_total_entry_encoding
            session.cash_register_difference = session.cash_register_balance_end_real - session.cash_register_balance_end

    def _compute_total_payments_amount(self):
        for session in self:
            session.total_payments_amount = sum(session.order_ids.mapped('payment_ids').mapped('amount'))

    def _compute_order_count(self):
        orders_data = self.env['pos.order'].read_group([('session_id', 'in', self.ids)], ['session_id'], ['session_id'])
        sessions_data = {order_data['session_id'][0]: order_data['session_id_count'] for order_data in orders_data}
        for session in self:
            session.order_count = sessions_data.get(session.id, 0)

    def _compute_picking_count(self):
        for pos in self:
            pickings = pos.order_ids.mapped('picking_id').filtered(lambda x: x.state != 'done')
            pos.picking_count = len(pickings.ids)

    def action_stock_picking(self):
        pickings = self.order_ids.mapped('picking_id').filtered(lambda x: x.state != 'done')
        action_picking = self.env.ref('stock.action_picking_tree_ready')
        action = action_picking.read()[0]
        action['context'] = {}
        action['domain'] = [('id', 'in', pickings.ids)]
        return action

    @api.depends('config_id', 'statement_ids')
    def _compute_cash_all(self):
        # Only one cash register is supported by point_of_sale.
        for session in self:
            session.cash_journal_id = session.cash_register_id = session.cash_control = False
            if session.config_id.cash_control:
                for statement in session.statement_ids:
                    if statement.journal_id == session.cash_payment_method_id.cash_journal_id:
                        session.cash_control = True
                        session.cash_journal_id = statement.journal_id.id
                        session.cash_register_id = statement.id
                        break  # stop iteration after finding the cash journal
                if not session.cash_control and session.state != 'closed':
                    raise UserError(_("Cash control can only be applied to cash journals."))

    @api.constrains('user_id', 'state')
    def _check_unicity(self):
        # open if there is no session in 'opening_control', 'opened', 'closing_control' for one user
        if self.search_count([
                ('state', 'not in', ('closed', 'closing_control')),
                ('user_id', '=', self.user_id.id),
                ('rescue', '=', False)
            ]) > 1:
            raise ValidationError(_("You cannot create two active sessions with the same responsible."))

    @api.constrains('config_id')
    def _check_pos_config(self):
        if self.search_count([
                ('state', '!=', 'closed'),
                ('config_id', '=', self.config_id.id),
                ('rescue', '=', False)
            ]) > 1:
            raise ValidationError(_("Another session is already opened for this point of sale."))

    @api.constrains('start_at')
    def _check_start_date(self):
        for record in self:
            company = record.config_id.journal_id.company_id
            start_date = record.start_at.date()
            if (company.period_lock_date and start_date <= company.period_lock_date) or (company.fiscalyear_lock_date and start_date <= company.fiscalyear_lock_date):
                raise ValidationError(_("You cannot create a session before the accounting lock date."))

    @api.model
    def create(self, values):
        config_id = values.get('config_id') or self.env.context.get('default_config_id')
        if not config_id:
            raise UserError(_("You should assign a Point of Sale to your session."))

        # journal_id is not required on the pos_config because it does not
        # exists at the installation. If nothing is configured at the
        # installation we do the minimal configuration. Impossible to do in
        # the .xml files as the CoA is not yet installed.
        pos_config = self.env['pos.config'].browse(config_id)
        ctx = dict(self.env.context, company_id=pos_config.company_id.id)
        if not pos_config.journal_id:
            default_journals = pos_config.with_context(ctx).default_get(['journal_id', 'invoice_journal_id'])
            if (not default_journals.get('journal_id') or
                    not default_journals.get('invoice_journal_id')):
                raise UserError(_("Unable to open the session. You have to assign a sales journal to your point of sale."))
            pos_config.with_context(ctx).sudo().write({
                'journal_id': default_journals['journal_id'],
                'invoice_journal_id': default_journals['invoice_journal_id']})

        if not pos_config.payment_method_ids:
            company = pos_config.company_id
            default_payment_method = self.env['pos.payment.method'].search([('company_id', '=', company.id)], limit=1)
            if not default_payment_method:
                default_payment_method = self.env['pos.payment.method'].create({
                    'name': _('Default Payment Method'),
                    'receivable_account_id': company.default_pos_receivable_account_id.id,
                    'is_cash_count': False,
                    'company_id': company.id,
                })
            pos_config.write({'payment_method_ids': [(6, 0, default_payment_method.ids)]})

        pos_name = self.env['ir.sequence'].with_context(ctx).next_by_code('pos.session')
        if values.get('name'):
            pos_name += ' ' + values['name']

        uid = SUPERUSER_ID if self.env.user.has_group('point_of_sale.group_pos_user') else self.env.user.id

        cash_payment_methods = pos_config.payment_method_ids.filtered(lambda pm: pm.is_cash_count)
        statement_ids = self.env['account.bank.statement']
        for cash_journal in cash_payment_methods.mapped('cash_journal_id'):
            ctx['journal_id'] = cash_journal.id if pos_config.cash_control and cash_journal.type == 'cash' else False
            st_values = {
                'journal_id': cash_journal.id,
                'user_id': self.env.user.id,
                'name': pos_name,
                'balance_start': self.env["account.bank.statement"]._get_opening_balance(cash_journal.id) if cash_journal.type == 'cash' else 0
            }
            statement_ids |= statement_ids.with_context(ctx).with_user(uid).create(st_values)

        values.update({
            'name': pos_name,
            'statement_ids': [(6, 0, statement_ids.ids)],
            'config_id': config_id,
            'payment_method_ids': [(6, 0, pos_config.payment_method_ids.ids)],
            # Set the first cash payment method as the cash payment method of this session.
            # Important in calculation of fields for cash control.
            'cash_payment_method_id': cash_payment_methods[0].id if cash_payment_methods else False,
        })

        res = super(PosSession, self.with_context(ctx).with_user(uid)).create(values)
        if not pos_config.cash_control:
            res.action_pos_session_open()

        return res

    def unlink(self):
        for session in self.filtered(lambda s: s.statement_ids):
            session.statement_ids.unlink()
        return super(PosSession, self).unlink()

    def login(self):
        self.ensure_one()
        self.write({
            'login_number': self.login_number + 1,
        })

    def action_pos_session_open(self):
        # second browse because we need to refetch the data from the DB for cash_register_id
        # we only open sessions that haven't already been opened
        for session in self.filtered(lambda session: session.state in ('new_session', 'opening_control')):
            values = {}
            if not session.start_at:
                values['start_at'] = fields.Datetime.now()
            values['state'] = 'opened'
            session.write(values)
            session.statement_ids.button_open()
        return True

    def action_pos_session_closing_control(self):
        self._check_pos_session_balance()
        for session in self:
            session.write({'state': 'closing_control', 'stop_at': fields.Datetime.now()})
            if not session.config_id.cash_control:
                session.action_pos_session_close()

    def _check_pos_session_balance(self):
        for session in self:
            for statement in session.statement_ids:
                if (statement != session.cash_register_id) and (statement.balance_end != statement.balance_end_real):
                    statement.write({'balance_end_real': statement.balance_end})

    def action_pos_session_validate(self):
        self._check_pos_session_balance()
        return self.action_pos_session_close()

    def _validate_session(self):
        self.ensure_one()
        self.check_if_no_draft_orders()
        self.create_account_move()
        if self.move_id.line_ids:
            self.move_id.post()
        else:
            # The cash register needs to be confirmed for cash diffs
            # made thru cash in/out when sesion is in cash_control.
            if self.config_id.cash_control:
                self.cash_register_id.button_confirm_bank()
            self.move_id.unlink()
        self.write({'state': 'closed'})
        return {
            'type': 'ir.actions.client',
            'name': 'Point of Sale Menu',
            'tag': 'reload',
            'params': {'menu_id': self.env.ref('point_of_sale.menu_point_root').id},
        }

    def action_pos_session_close(self):
        # Session without cash payment method will not have a cash register.
        # However, there could be other payment methods, thus, session still
        # needs to be validated.
        if not self.cash_register_id:
            return self._validate_session()

        if abs(self.cash_register_difference) > self.config_id.amount_authorized_diff:
            # Only pos manager can close statements with cash_register_difference greater than amount_authorized_diff.
            if not self.user_has_groups("point_of_sale.group_pos_manager"):
                raise UserError(_(
                    "Your ending balance is too different from the theoretical cash closing (%.2f), "
                    "the maximum allowed is: %.2f. You can contact your manager to force it."
                ) % (self.cash_register_difference, self.config_id.amount_authorized_diff))
            else:
                return self._warning_balance_closing()
        else:
            return self._validate_session()

    def create_account_move(self):
        """ Create account.move and account.move.line records for this session.

        Side-effects include:
            - setting self.move_id to the created account.move record
            - creating and validating account.bank.statement for cash payments
            - reconciling cash receivable lines, invoice receivable lines and stock output lines
        """
        journal = self.config_id.journal_id
        # Passing default_journal_id for the calculation of default currency of account move
        # See _get_default_currency in the account/account_move.py.
        account_move = self.env['account.move'].with_context(default_journal_id=journal.id).create({
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'ref': self.name,
            'name': journal.sequence_id.next_by_id()
        })
        self.write({'move_id': account_move.id})

        ## SECTION: Accumulate the amounts for each accounting lines group
        # Each dict maps `key` -> `amounts`, where `key` is the group key.
        # E.g. `combine_receivables` is derived from pos.payment records
        # in the self.order_ids with group key of the `payment_method_id`
        # field of the pos.payment record.
        split_receivables           = defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0})
        split_receivables_cash      = defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0})
        combine_receivables         = defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0})
        combine_receivables_cash    = defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0})
        invoice_receivables         = defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0})
        sales                       = defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0})
        taxes                       = defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0})
        stock_expense               = defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0})
        stock_output                = defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0})
        # Track the receivable lines of the invoiced orders' account moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        order_account_move_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        for order in self.order_ids:
            # Combine pos receivable lines
            # Separate cash payments for cash reconciliation later.
            for payment in order.payment_ids:
                amount, date = payment.amount, payment.payment_date
                if payment.payment_method_id.split_transactions:
                    if payment.payment_method_id.is_cash_count:
                        split_receivables_cash[payment] = self._update_amounts(amount, date, **split_receivables_cash[payment])
                    else:
                        split_receivables[payment] = self._update_amounts(amount, date, **split_receivables[payment])
                else:
                    key = payment.payment_method_id
                    if payment.payment_method_id.is_cash_count:
                        combine_receivables_cash[key] = self._update_amounts(amount, date, **combine_receivables_cash[key])
                    else:
                        combine_receivables[key] = self._update_amounts(amount, date, **combine_receivables[key])

            if order.is_invoiced:
                # Combine invoice receivable lines
                key = order.partner_id.property_account_receivable_id.id
                invoice_receivables[key] = self._update_amounts(order.amount_total, order.date_order, **invoice_receivables[key])
                # side loop to gather receivable lines by account for reconciliation
                for move_line in order.account_move.line_ids.filtered(lambda aml: aml.account_id.internal_type == 'receivable'):
                    order_account_move_receivable_lines[move_line.account_id.id] |= move_line
            else:
                for line in map(self._prepare_line, order.lines):
                    # Combine sales/refund lines
                    sale_key = (
                        # account
                        line['income_account_id'],
                        # sign
                        -1 if line['amount'] < 0 else 1,
                        # for taxes
                        tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in line['taxes']),
                    )
                    sales[sale_key] = self._update_amounts(line['amount'], line['date_order'], **sales[sale_key])
                    # Combine tax lines
                    for tax in line['taxes']:
                        tax_key = (tax['account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']))
                        taxes[tax_key] = self._update_tax_amounts(tax['amount'], tax['base'], tax['date_order'], **taxes[tax_key])
                # Combine stock lines
                stock_moves = self.env['stock.move'].search([
                    ('picking_id', '=', order.picking_id.id),
                    ('company_id.anglo_saxon_accounting', '=', True),
                    ('product_id.categ_id.property_valuation', '=', 'real_time')
                ])
                for move in stock_moves:
                    exp_key = move.product_id.property_account_expense_id or move.product_id.categ_id.property_account_expense_categ_id
                    out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                    amount = -sum(move.stock_valuation_layer_ids.mapped('value'))
                    stock_expense[exp_key] = self._update_amounts(amount, move.picking_id.date, **stock_expense[exp_key])
                    stock_output[out_key] = self._update_amounts(amount, move.picking_id.date, **stock_output[out_key])

        ## SECTION: Create non-reconcilable move lines
        # Create account.move.line records for
        #   - sales
        #   - taxes
        #   - stock expense
        #   - non-cash split receivables (not for automatic reconciliation)
        #   - non-cash combine receivables (not for automatic reconciliation)
        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

        tax_vals = [self._get_tax_vals(key, **amounts) for key, amounts in taxes.items()]
        # Check if all taxes lines have account_id assigned. If not, there are repartition lines of the tax that have no account_id.
        tax_names_no_account = [line['name'] for line in tax_vals if line['account_id'] == False]
        if len(tax_names_no_account) > 0:
            error_message = _(
                'Unable to close and validate the session.\n'
                'Please set corresponding tax account in each repartition line of the following taxes: \n%s'
            ) % ', '.join(tax_names_no_account)
            raise UserError(error_message)

        MoveLine.create(
            tax_vals
            + [self._get_sale_vals(key, **amounts) for key, amounts in sales.items()]
            + [self._get_stock_expense_vals(key, **amounts) for key, amounts in stock_expense.items()]
            + [self._get_split_receivable_vals(key, **amounts) for key, amounts in split_receivables.items()]
            + [self._get_combine_receivable_vals(key, **amounts) for key, amounts in combine_receivables.items()]
        )

        ## SECTION: Create cash statement lines and cash move lines
        # Create the split and combine cash statement lines and account move lines.
        # Keep the reference by statement for reconciliation.
        # `split_cash_statement_lines` maps `statement` -> split cash statement lines
        # `combine_cash_statement_lines` maps `statement` -> combine cash statement lines
        # `split_cash_receivable_lines` maps `statement` -> split cash receivable lines
        # `combine_cash_receivable_lines` maps `statement` -> combine cash receivable lines
        statements_by_journal_id = {statement.journal_id.id: statement for statement in self.statement_ids}
        # handle split cash payments
        split_cash_statement_line_vals  = defaultdict(list)
        split_cash_receivable_vals      = defaultdict(list)
        for payment, amounts in split_receivables_cash.items():
            statement = statements_by_journal_id[payment.payment_method_id.cash_journal_id.id]
            split_cash_statement_line_vals[statement].append(self._get_statement_line_vals(statement, payment.payment_method_id.receivable_account_id, **amounts))
            split_cash_receivable_vals[statement].append(self._get_split_receivable_vals(payment, **amounts))
        # handle combine cash payments
        combine_cash_statement_line_vals    = defaultdict(list)
        combine_cash_receivable_vals        = defaultdict(list)
        for payment_method, amounts in combine_receivables_cash.items():
            if not float_is_zero(amounts['amount'] , precision_rounding=self.currency_id.rounding):
                statement = statements_by_journal_id[payment_method.cash_journal_id.id]
                combine_cash_statement_line_vals[statement].append(self._get_statement_line_vals(statement, payment_method.receivable_account_id, **amounts))
                combine_cash_receivable_vals[statement].append(self._get_combine_receivable_vals(payment_method, **amounts))
        # create the statement lines and account move lines
        BankStatementLine = self.env['account.bank.statement.line']
        split_cash_statement_lines      = {}
        combine_cash_statement_lines    = {}
        split_cash_receivable_lines     = {}
        combine_cash_receivable_lines   = {}
        for statement in self.statement_ids:
            split_cash_statement_lines[statement] = BankStatementLine.create(split_cash_statement_line_vals[statement])
            combine_cash_statement_lines[statement] = BankStatementLine.create(combine_cash_statement_line_vals[statement])
            split_cash_receivable_lines[statement] = MoveLine.create(split_cash_receivable_vals[statement])
            combine_cash_receivable_lines[statement] = MoveLine.create(combine_cash_receivable_vals[statement])

        ## SECTION: Create invoice receivable lines for this session's move_id.
        # Keep reference of the invoice receivable lines because
        # they are reconciled with the lines in order_account_move_receivable_lines
        invoice_receivable_vals = defaultdict(list)
        invoice_receivable_lines = {}
        for receivable_account_id, amounts in invoice_receivables.items():
            invoice_receivable_vals[receivable_account_id].append(self._get_invoice_receivable_vals(receivable_account_id, **amounts))
        for receivable_account_id, vals in invoice_receivable_vals.items():
            invoice_receivable_lines[receivable_account_id] = MoveLine.create(vals)

        ## SECTION: Create stock output lines
        # Keep reference to the stock output lines because
        # they are reconciled with output lines in the stock.move's account.move.line
        stock_output_vals = defaultdict(list)
        stock_output_lines = {}
        for output_account, amounts in stock_output.items():
            stock_output_vals[output_account].append(self._get_stock_output_vals(output_account, **amounts))
        for output_account, vals in stock_output_vals.items():
            stock_output_lines[output_account] = MoveLine.create(vals)

        ## SECTION: Create rounding error
        MoveLine.create(self._get_rounding_error_vals())

        ## SECTION: Reconcile account move lines
        # reconcile cash receivable lines
        for statement in self.statement_ids:
            if not self.config_id.cash_control:
                statement.write({'balance_end_real': statement.balance_end})
            statement.button_confirm_bank()
            all_lines = (
                  split_cash_statement_lines[statement].mapped('journal_entry_ids').filtered(lambda aml: aml.account_id.internal_type == 'receivable')
                | combine_cash_statement_lines[statement].mapped('journal_entry_ids').filtered(lambda aml: aml.account_id.internal_type == 'receivable')
                | split_cash_receivable_lines[statement]
                | combine_cash_receivable_lines[statement]
            )
            accounts = all_lines.mapped('account_id')
            lines_by_account = [all_lines.filtered(lambda l: l.account_id == account) for account in accounts]
            for lines in lines_by_account:
                lines.reconcile()

        # reconcile invoice receivable lines
        for account_id in order_account_move_receivable_lines:
            ( order_account_move_receivable_lines[account_id]
            | invoice_receivable_lines[account_id]
            ).reconcile()

        # reconcile stock output lines
        stock_moves = self.env['stock.move'].search([('picking_id', 'in', self.order_ids.mapped('picking_id').ids)])
        stock_account_move_lines = self.env['account.move'].search([('stock_move_id', 'in', stock_moves.ids)]).mapped('line_ids')
        for account_id in stock_output_lines:
            ( stock_output_lines[account_id]
            | stock_account_move_lines.filtered(lambda aml: aml.account_id == account_id)
            ).reconcile()

    def _prepare_line(self, order_line):
        """ Derive from order_line the order date, income account, amount and taxes information.

        These information will be used in accumulating the amounts for sales and tax lines.
        """
        def get_income_account(order_line):
            product = order_line.product_id
            income_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
            if not income_account:
                raise UserError(_('Please define income account for this product: "%s" (id:%d).')
                                % (product.name, product.id))
            return order_line.order_id.fiscal_position_id.map_account(income_account)

        tax_ids = order_line.tax_ids_after_fiscal_position\
                    .filtered(lambda t: t.company_id.id == order_line.order_id.company_id.id)
        price = order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
        taxes = tax_ids.compute_all(price_unit=price, quantity=order_line.qty, currency=self.currency_id, is_refund=order_line.qty<0).get('taxes', [])
        date_order = order_line.order_id.date_order
        taxes = [{'date_order': date_order, **tax} for tax in taxes]
        return {
            'date_order': order_line.order_id.date_order,
            'income_account_id': get_income_account(order_line).id,
            'amount': order_line.price_subtotal,
            'taxes': taxes,
        }

    def _get_split_receivable_vals(self, payment, amount, amount_converted):
        partial_vals = {
            'account_id': payment.payment_method_id.receivable_account_id.id,
            'move_id': self.move_id.id,
            'partner_id': self.env["res.partner"]._find_accounting_partner(payment.partner_id).id,
            'name': '%s - %s' % (self.name, payment.payment_method_id.name),
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_combine_receivable_vals(self, payment_method, amount, amount_converted):
        partial_vals = {
            'account_id': payment_method.receivable_account_id.id,
            'move_id': self.move_id.id,
            'name': '%s - %s' % (self.name, payment_method.name)
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_invoice_receivable_vals(self, account_id, amount, amount_converted):
        partial_vals = {
            'account_id': account_id,
            'move_id': self.move_id.id,
            'name': 'From invoiced orders'
        }
        return self._credit_amounts(partial_vals, amount, amount_converted)

    def _get_sale_vals(self, key, amount, amount_converted):
        account_id, sign, tax_keys = key
        tax_ids = [tax[0] for tax in tax_keys]
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        name = '' if not applied_taxes else '%s group: %s' % ('Sales' if sign == 1 else 'Refund', ', '.join([tax.name for tax in applied_taxes]))
        base_tags = applied_taxes\
            .mapped('invoice_repartition_line_ids' if sign == 1 else 'refund_repartition_line_ids')\
            .filtered(lambda line: line.repartition_type == 'base')\
            .tag_ids
        partial_vals = {
            'name': name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'tax_ids': [(6, 0, tax_ids)],
            'tag_ids': [(6, 0, base_tags.ids)],
        }
        return self._credit_amounts(partial_vals, amount, amount_converted)

    def _get_tax_vals(self, key, amount, amount_converted, base_amount):
        account_id, repartition_line_id, tax_id, tag_ids = key
        tax = self.env['account.tax'].browse(tax_id)
        partial_args = {
            'name': tax.name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'tax_base_amount': base_amount,
            'tax_repartition_line_id': repartition_line_id,
            'tag_ids': [(6, 0, tag_ids)],
        }
        return self._credit_amounts(partial_args, amount, amount_converted)

    def _get_stock_expense_vals(self, exp_account, amount, amount_converted):
        partial_args = {'account_id': exp_account.id, 'move_id': self.move_id.id}
        return self._debit_amounts(partial_args, amount, amount_converted)

    def _get_stock_output_vals(self, out_account, amount, amount_converted):
        partial_args = {'account_id': out_account.id, 'move_id': self.move_id.id}
        return self._credit_amounts(partial_args, amount, amount_converted)

    def _get_statement_line_vals(self, statement, receivable_account, amount, amount_converted):
        return {
            'date': fields.Date.context_today(self),
            'amount': amount,
            'name': self.name,
            'statement_id': statement.id,
            'account_id': receivable_account.id,
        }

    def _update_amounts(self, new_amount, date, amount, amount_converted):
        return {
            'amount': amount + new_amount,
            'amount_converted': amount_converted if self.is_in_company_currency else (amount_converted + self._amount_converter(new_amount, date)),
        }

    def _update_tax_amounts(self, new_amount, new_base_amount, date, amount, amount_converted, base_amount):
        return {
            'amount': amount + new_amount,
            'amount_converted': amount_converted if self.is_in_company_currency else (amount_converted + self._amount_converter(new_amount, date)),
            'base_amount': base_amount + new_base_amount
        }

    def _get_rounding_error_vals(self):
        """ Generate the line for imbalanced lines in this session's move_id.

        NOTE Decision on how to tackle rounding error is not very easy.
        It could be the developer's fault. Or it could be an error that can't
        be avoided which should be accounted like how I tackled it in here.

        TODO Can the error be included in the sales lines?

        Scenarios where rounding errors can be reproduced:
          1. Taxes with multiple repartition lines.
          2. Multiple payments in one order at different currency from company.
        """
        diff = sum(self.move_id.line_ids.mapped('balance'))
        undistributed_account = self.env['account.account'].search([('code', '=', '999999')])
        if float_is_zero(diff, precision_rounding=self.currency_id.rounding):
            return []
        counter_amount = -self.currency_id.round(diff)
        # Use currency_id.rounding value as the threshold for rounding error.
        # Any counter_amount greater than it should raise an exception.
        max_rounding_error = self.currency_id.rounding
        if not float_is_zero(abs(counter_amount) - max_rounding_error, precision_rounding=self.currency_id.rounding):
            raise UserError(_('The magnitude of rounding error amount (%s) is more than %s.') % (counter_amount, max_rounding_error))
        return [{
            'account_id': undistributed_account.id,
            'move_id': self.move_id.id,
            'name': "Rounding error",
            'amount_currency': 0.0,
            'currency_id': self.currency_id.id,
            'debit': counter_amount if counter_amount > 0.0 else 0.0,
            'credit': -counter_amount if counter_amount < 0.0 else 0.0,
        }]

    def _credit_amounts(self, partial_move_line_vals, amount, amount_converted):
        """ `partial_move_line_vals` is completed by `credit`ing the given amounts.

        NOTE Amounts in PoS are in the currency of journal_id in the session.config_id.
        This means that amount fields in any pos record are actually equivalent to amount_currency
        in account module. Understanding this basic is important in correctly assigning values for
        'amount' and 'amount_currency' in the account.move.line record.

        :param partial_move_line_vals dict:
            initial values in creating account.move.line
        :param amount float:
            amount derived from pos.payment, pos.order, or pos.order.line records
        :param amount_converted float:
            converted value of `amount` from the given `session_currency` to company currency

        :return dict: complete values for creating 'amount.move.line' record
        """
        if self.is_in_company_currency:
            return {
                'debit': -amount if amount < 0.0 else 0.0,
                'credit': amount if amount > 0.0 else 0.0,
                **partial_move_line_vals
            }
        else:
            return {
                'debit': -amount_converted if amount_converted < 0.0 else 0.0,
                'credit': amount_converted if amount_converted > 0.0 else 0.0,
                'amount_currency': -amount if amount_converted > 0 else amount,
                'currency_id': self.currency_id.id,
                **partial_move_line_vals
            }

    def _debit_amounts(self, partial_move_line_vals, amount, amount_converted):
        """ `partial_move_line_vals` is completed by `debit`ing the given amounts.

        See _credit_amounts docs for more details.
        """
        if self.is_in_company_currency:
            return {
                'debit': amount if amount > 0.0 else 0.0,
                'credit': -amount if amount < 0.0 else 0.0,
                **partial_move_line_vals
            }
        else:
            return {
                'debit': amount_converted if amount_converted > 0.0 else 0.0,
                'credit': -amount_converted if amount_converted < 0.0 else 0.0,
                'amount_currency': amount if amount_converted > 0 else -amount,
                'currency_id': self.currency_id.id,
                **partial_move_line_vals
            }

    def _amount_converter(self, amount, date):
        # self should be single record as this method is only called in the subfunctions of self._validate_session
        return self.currency_id._convert(amount, self.company_id.currency_id, self.company_id, date)

    def _get_cash_move_lines(self):
        return self.env['account.move.line'].search([('statement_id', '!=', False), ('statement_id', '=', self.cash_register_id.id)])

    def _get_related_account_moves(self):
        def get_matched_move_lines(aml):
            if aml.credit > 0:
                return [r.debit_move_id.id for r in aml.matched_debit_ids]
            else:
                return [r.credit_move_id.id for r in aml.matched_credit_ids]

        session_move = self.move_id
        # get all the linked move lines to this account move.
        non_reconcilable_lines = session_move.line_ids.filtered(lambda aml: not aml.account_id.reconcile)
        reconcilable_lines = session_move.line_ids - non_reconcilable_lines
        fully_reconciled_lines = reconcilable_lines.filtered(lambda aml: aml.full_reconcile_id)
        partially_reconciled_lines = reconcilable_lines - fully_reconciled_lines

        cash_move_lines = self._get_cash_move_lines()

        ids = (non_reconcilable_lines.ids
                + fully_reconciled_lines.mapped('full_reconcile_id').mapped('reconciled_line_ids').ids
                + sum(partially_reconciled_lines.mapped(get_matched_move_lines), partially_reconciled_lines.ids)
                + cash_move_lines.ids)

        return self.env['account.move.line'].browse(ids).mapped('move_id')

    def show_journal_items(self):
        self.ensure_one()
        all_related_moves = self._get_related_account_moves()
        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree',
            'view_id':self.env.ref('account.view_move_line_tree_grouped').id,
            'domain': [('id', 'in', all_related_moves.mapped('line_ids').ids)],
            'context': {
                'journal_type':'general',
                'search_default_group_by_move': 1,
                'group_by':'move_id', 'search_default_posted':1,
                'name_groupby':1,
            },
        }

    def action_show_payments_list(self):
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment',
            'view_id': self.env.ref('point_of_sale.view_pos_payment_tree').id,
            'view_mode': 'tree',
            'domain': [('session_id', '=', self.id)],
            'context': {'search_default_group_by_payment_method': 1}
        }

    def open_frontend_cb(self):
        if not self.ids:
            return {}
        for session in self.filtered(lambda s: s.user_id.id != self.env.uid):
            raise UserError(_("You cannot use the session of another user. This session is owned by %s. "
                              "Please first close this one to use this point of sale.") % session.user_id.name)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url':   '/pos/web/',
        }

    def open_cashbox_pos(self):
        self.ensure_one()
        action = self.cash_register_id.open_cashbox_id()
        action['view_id'] = self.env.ref('point_of_sale.view_account_bnk_stmt_cashbox_footer').id
        action['context']['pos_session_id'] = self.id
        action['context']['default_pos_id'] = self.config_id.id
        return action

    def action_view_order(self):
        return {
            'name': _('Orders'),
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'domain': [('session_id', 'in', self.ids)],
        }

    @api.model
    def _alert_old_session(self):
        # If the session is open for more then one week,
        # log a next activity to close the session.
        sessions = self.search([('start_at', '<=', (fields.datetime.now() - timedelta(days=7))), ('state', '!=', 'closed')])
        for session in sessions:
            if self.env['mail.activity'].search_count([('res_id', '=', session.id), ('res_model', '=', 'pos.session')]) == 0:
                session.activity_schedule('point_of_sale.mail_activity_old_session',
                        user_id=session.user_id.id, note=_("Your PoS Session is open since ") + fields.Date.to_string(session.start_at)
                        + _(", we advise you to close it and to create a new one."))

    def _warning_balance_closing(self):
        self.ensure_one()

        context = dict(self._context)
        context['session_id'] = self.id

        return {
            'name': _('Balance control'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'closing.balance.confirm.wizard',
            'view_id': self.env.ref('point_of_sale.closing_balance_confirm').id,
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new'
        }

    def check_if_no_draft_orders(self):
        draft_orders = self.order_ids.filtered(lambda order: order.state == 'draft')
        if draft_orders:
            raise UserError(_(
                    'There are still orders in draft state in the session. '
                    'Pay or cancel the following orders to validate the session:\n%s'
                ) % ', '.join(draft_orders.mapped('name'))
            )
        return True

class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super(ProcurementGroup, self)._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        self.env['pos.session']._alert_old_session()
        if use_new_cursor:
            self.env.cr.commit()

class ClosingBalanceConfirm(models.TransientModel):
    _name = 'closing.balance.confirm.wizard'
    _description = 'This wizard is used to display a warning message if the manager wants to close a session with a too high difference between real and expected closing balance'

    def confirm_closing_balance(self):
        current_session =  self.env['pos.session'].browse(self._context['session_id'])
        return current_session._validate_session()
