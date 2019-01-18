# -*- coding: utf-8 -*-

import json
import re
import uuid
from functools import partial

from lxml import etree

from odoo import api, exceptions, fields, models, _
from odoo.tools import email_re, email_split, email_escape_char, float_is_zero, float_compare, \
    pycompat, date_utils
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning

from odoo.addons import decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Credit Note
    'in_refund': 'in_invoice',          # Vendor Credit Note
}

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')


class AccountInvoice(models.Model):
    _name = "account.invoice"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _inherits = {'account.move': 'move_id'}
    _description = "Invoice"
    _order = "date_invoice desc, name desc, id desc"

    @api.model
    def _get_default_incoterm(self):
        return self.env.user.company_id.incoterm_id

    @api.model
    def _default_type(self):
        return self._context.get('type', 'out_invoice')

    # Not-relational fields.
    origin = fields.Char(string='Source Document',
        help="Reference of the document that produced this invoice.",
        readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection([
            ('out_invoice', 'Customer Invoice'),
            ('in_invoice', 'Vendor Bill'),
            ('out_refund', 'Customer Credit Note'),
            ('in_refund', 'Vendor Credit Note'),
        ], readonly=True, states={'draft': [('readonly', False)]}, index=True, change_default=True,
        default=_default_type,
        tracking=True)
    state = fields.Selection([
            ('draft','Draft'),
            ('open', 'Open'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        tracking=True, copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'In Payment' status is used when payments have been registered for the entirety of the invoice in a journal configured to post entries at bank reconciliation only, and some of them haven't been reconciled with a bank statement line yet.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    description = fields.Char(string='Reference/Description', index=True, readonly=True, copy=False,
        states={'draft': [('readonly', False)]},
        help='The name that will be used on account move lines')
    sent = fields.Boolean(readonly=True, default=False, copy=False,
        help="It indicates that the invoice has been sent.")
    date_invoice = fields.Date(string='Invoice Date',
        readonly=True, states={'draft': [('readonly', False)]}, index=True,
        help="Keep empty to use the current date", copy=False)
    date_due = fields.Date(string='Due Date',
        readonly=True, states={'draft': [('readonly', False)]}, index=True, copy=False,
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. The Payment terms may compute several due dates, for example 50% "
             "now and 50% in one month, but if you want to force a due date, make sure that the payment "
             "term is not set on the invoice. If you keep the Payment terms and the due date empty, it "
             "means direct payment.")
    amount_by_group = fields.Binary(string="Tax amount by group", compute='_amount_by_group', help="type: [(name, amount, base, formated amount, formated base)]")
    amount_tax = fields.Monetary(string='Tax', store=True, readonly=True,
        compute='_compute_amount')
    amount_tax_signed = fields.Monetary(string='Tax Signed', store=True, readonly=True,
        compute='_compute_amount')
    amount_tax_company_signed = fields.Monetary(string='Tax Signed in Company Currency',
        store=True, readonly=True,
        currency_field='company_currency_id',
        compute='_compute_amount')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True,
        compute='_compute_amount', tracking=True)
    amount_untaxed_signed = fields.Monetary(string='Untaxed Amount Signed', store=True, readonly=True,
        compute='_compute_amount')
    amount_untaxed_company_signed = fields.Monetary(string='Untaxed Amount Signed in Company Currency',
        store=True, readonly=True,
        currency_field='company_currency_id',
        compute='_compute_amount')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True,
        compute='_compute_amount')
    amount_total_signed = fields.Monetary(string='Total Signed', store=True, readonly=True,
        compute='_compute_amount')
    amount_total_company_signed = fields.Monetary(string='Total Signed in Company Currency',
        store=True, readonly=True,
        currency_field='company_currency_id',
        compute='_compute_amount')
    residual = fields.Monetary(string='Amount Due', store=True,
        compute='_compute_amount',
        help="Remaining amount due.")
    residual_signed = fields.Monetary(string='Amount Due in Invoice Currency', store=True,
        currency_field='currency_id',
        compute='_compute_amount',
        help="Remaining amount due in the currency of the invoice.")
    residual_company_signed = fields.Monetary(string='Amount Due in Company Currency', store=True,
        currency_field='company_currency_id',
        compute='_compute_amount',
        help="Remaining amount due in the currency of the company.")
    reconciled = fields.Boolean(string='Paid/Reconciled', store=True, readonly=True,
        compute='_compute_amount',
        help="It indicates that the invoice has been paid and the journal entry of the invoice has been reconciled with one or several journal entries of payment.")
    outstanding_credits_debits_widget = fields.Text(compute='_get_outstanding_info_JSON', groups="account.group_account_invoice")
    payments_widget = fields.Text(compute='_get_payment_info_JSON', groups="account.group_account_invoice")
    has_outstanding = fields.Boolean(compute='_get_outstanding_info_JSON', groups="account.group_account_invoice")
    sequence_number_next = fields.Char(string='Next Number', compute="_get_sequence_number_next", inverse="_set_sequence_next")
    sequence_number_next_prefix = fields.Char(string='Next Number Prefix', compute="_get_sequence_prefix")
    source_email = fields.Char(string='Source Email', tracking=True)
    vendor_display_name = fields.Char(compute='_get_vendor_display_info', store=True)  # store=True to enable sorting on that column
    invoice_icon = fields.Char(compute='_get_vendor_display_info', store=False)

    # Relational fields.
    user_id = fields.Many2one('res.users', string='Salesperson', track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user, copy=False)
    refund_invoice_id = fields.Many2one('account.invoice', string="Invoice for which this invoice is the credit note")
    vendor_bill_id = fields.Many2one('account.invoice', string='Vendor Bill',
        help="Auto-complete from a past bill.")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term',
        readonly=True, states={'draft': [('readonly', False)]},
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. If you keep the payment terms and the due date empty, it means direct payment. "
             "The payment terms may compute several due dates, for example 50% now, 50% in one month.")
    account_id = fields.Many2one('account.account', string='Account', required=True,
        domain=[('deprecated', '=', False)],
        help="The partner account used for this invoice.")
    invoice_line_ids = fields.One2many('account.move.line', string='Invoice Lines', readonly=True, copy=True,
        compute='_compute_line_ids',
        inverse='_inverse_line_ids',
        states={'draft': [('readonly', False)]})
    tax_line_ids = fields.One2many('account.move.line', string='Tax Lines', readonly=True, copy=True,
        compute='_compute_line_ids',
        inverse='_inverse_line_ids',
        states={'draft': [('readonly', False)]})
    pay_term_line_ids = fields.One2many('account.move.line', string='Payment Term Lines', readonly=True, copy=True,
        compute='_compute_line_ids',
        inverse='_inverse_line_ids')
    cash_rounding_line_id = fields.Many2one('account.move.line', string='Cash Rounding line', readonly=True, copy=True)
    refund_invoice_ids = fields.One2many('account.invoice', 'refund_invoice_id', string='Refund Invoices', readonly=True)
    move_id = fields.Many2one('account.move', string='Journal Entry',
        required=True, readonly=True, index=True, ondelete='cascade',
        help="Link to the automatically generated Journal Items.")
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True,
        states={'draft': [('readonly', False)]})
    partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account',
        help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Vendor Credit Note, otherwise a Partner bank account number.',
        readonly=True, states={'draft': [('readonly', False)]})  # Default value computed in default_get for out_invoices
    payment_ids = fields.Many2many('account.payment', 'account_invoice_payment_rel', 'invoice_id', 'payment_id',
        string="Payments", copy=False, readonly=True)
    payment_move_line_ids = fields.Many2many('account.move.line', string='Payment Move Lines',
        compute='_compute_payments', store=True)
    cash_rounding_id = fields.Many2one('account.cash.rounding', string='Cash Rounding Method',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Defines the smallest coinage of the currency that can be used to pay by cash.')
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterm',
        default=_get_default_incoterm,
        help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')

    # -------------------------------------------------------------------------
    # HELPERS / HOOKS
    # -------------------------------------------------------------------------

    @api.model
    def _get_default_partner_bank_id(self, values):
        ''' Retrieve the default partner_bank_id.
        /!\ This default is done manually because it depends of others fields.
        :param values:  Others computed default values in 'default_get'.
        :return:        A res.partner.bank record's id or None.
        '''
        # 'partner_bank_id' is set only for 'out_invoice'/'in_refund' invoices.
        if values.get('type') not in ('out_invoice', 'in_refund'):
            return None

        journal = self.env['account.journal'].browse(values['journal_id'])
        company = journal.company_id

        # No partner found.
        if not company.partner_id:
            return None

        res_partner_bank = self.env['res.partner.bank'].search([('partner_id', '=', company.partner_id.id)], limit=1)

        return res_partner_bank and res_partner_bank.id or None

    @api.multi
    def _get_default_product_name(self, move_line):
        self.ensure_one()

        if self.type in ('out_invoice', 'out_refund'):
            return '\n'.join([move_line.product_id.partner_ref, move_line.product_id.description_sale])
        else:
            return '\n'.join([move_line.product_id.partner_ref, move_line.product_id.description_purchase])

    @api.multi
    def _get_default_product_account(self, move_line):
        self.ensure_one()

        accounts = move_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=self.fiscal_position_id)
        if self.type in ('out_invoice', 'out_refund'):
            return accounts['income']
        else:
            return accounts['expense']

    @api.multi
    def _get_default_product_taxes(self, move_line):
        self.ensure_one()

        if self.invoice_id.type in ('out_invoice', 'out_refund'):
            tax_ids = move_line.product_id.taxes_id or move_line.account_id.tax_ids
        else:
            tax_ids = move_line.product_id.supplier_taxes_id or move_line.account_id.tax_ids

        if move_line.product_id:
            return tax_ids
        else:
            return self.fiscal_position_id.map_tax(tax_ids, partner=self.partner_id)

    @api.multi
    def _get_default_product_price_unit(self, move_line):
        self.ensure_one()

        if self.invoice_id.type in ('out_invoice', 'out_refund'):
            return self.product_id.lst_price
        else:
            return self.product_id.standard_price

    @api.multi
    def _get_computed_reference(self):
        self.ensure_one()
        if self.company_id.invoice_reference_type == 'invoice_number':
            seq_suffix = self.journal_id.sequence_id.suffix or ''
            regex_number = '.*?([0-9]+)%s$' % seq_suffix
            exact_match = re.match(regex_number, self.name)
            if exact_match:
                identification_number = int(exact_match.group(1))
            else:
                ran_num = str(uuid.uuid4().int)
                identification_number = int(ran_num[:5] + ran_num[-5:])
            prefix = self.name
        else:
            #self.company_id.invoice_reference_type == 'partner'
            identification_number = self.partner_id.id
            prefix = 'CUST'
        return '%s/%s' % (prefix, str(identification_number % 97).rjust(2, '0'))

    @api.multi
    def get_delivery_partner_id(self):
        self.ensure_one()
        return self.partner_id.address_get(['delivery'])['delivery']

    @api.multi
    def _get_intrastat_country_id(self):
        self.ensure_one()
        return self.partner_id.country_id.id

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_id.line_ids', 'account_id')
    def _compute_line_ids(self):
        for inv in self:
            inv.pay_term_line_ids = inv.line_ids.filtered(lambda line: line.account_id == inv.account_id)
            inv.tax_line_ids = inv.line_ids.filtered(lambda line: line.tax_line_id)
            inv.invoice_line_ids = inv.line_ids - inv.pay_term_line_ids - inv.tax_line_ids

    @api.multi
    def _inverse_line_ids(self):
        pass

    @api.depends(
        'move_id.currency_id', 'type',
        'move_id.line_ids.price_total',
        'move_id.line_ids.balance',
        'move_id.line_ids.amount_currency',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.amount_residual_currency')
    def _compute_amount(self):
        for inv in self:
            sign = 1 if inv.type in ('out_invoice', 'in_invoice') else -1

            # Compute amounts.
            balance_field = 'balance' if inv.currency_id == inv.company_currency_id else 'amount_currency'
            inv.amount_tax = sum(inv.mapped('tax_line_ids.price_total'))
            inv.amount_tax_signed = sign * inv.amount_tax
            inv.amount_tax_company_signed = sign * abs(sum(inv.mapped('tax_line_ids.%s' % balance_field)))
            inv.amount_untaxed = sum(inv.mapped('invoice_line_ids.price_total'))
            inv.amount_untaxed_signed = sign * inv.amount_untaxed
            inv.amount_untaxed_company_signed = sign * abs(sum(inv.mapped('invoice_line_ids.%s' % balance_field)))
            inv.amount_total = sum(inv.mapped('pay_term_line_ids.price_total'))
            inv.amount_total_signed = sign * inv.amount_total
            inv.amount_total_company_signed = sign * abs(sum(inv.mapped('pay_term_line_ids.%s' % balance_field)))

            # Compute residual amounts.
            residual_field = 'amount_residual' if inv.currency_id == inv.company_currency_id else 'amount_residual_currency'
            inv.residual = abs(sum(inv.mapped('pay_term_line_ids.%s' % residual_field)))
            inv.residual_signed = sign * abs(sum(inv.mapped('pay_term_line_ids.%s' % residual_field)))
            inv.residual_company_signed = sign * abs(sum(inv.mapped('pay_term_line_ids.amount_residual')))
            inv.reconciled = inv.currency_id.is_zero(inv.residual)

    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('account_id', '=', self.account_id.id), ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id), ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0)]
            if self.type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = self.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == self.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        currency = line.company_id.currency_id
                        amount_to_show = currency._convert(abs(line.amount_residual), self.currency_id, self.company_id, line.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True

    @api.model
    def _get_payments_vals(self):
        if not self.payment_move_line_ids:
            return []
        payment_vals = []
        currency_id = self.currency_id
        for payment in self.payment_move_line_ids:
            payment_currency_id = False
            if self.type in ('out_invoice', 'in_refund'):
                amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                amount_currency = sum(
                    [p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                if payment.matched_debit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in
                                               payment.matched_debit_ids]) and payment.matched_debit_ids[
                                              0].currency_id or False
            elif self.type in ('in_invoice', 'out_refund'):
                amount = sum(
                    [p.amount for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if
                                       p.credit_move_id in self.move_id.line_ids])
                if payment.matched_credit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in
                                               payment.matched_credit_ids]) and payment.matched_credit_ids[
                                              0].currency_id or False
            # get the payment value in invoice currency
            if payment_currency_id and payment_currency_id == self.currency_id:
                amount_to_show = amount_currency
            else:
                currency = payment.company_id.currency_id
                amount_to_show = currency._convert(amount, self.currency_id, payment.company_id, self.date or fields.Date.today())
            if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                continue
            payment_ref = payment.move_id.name
            if payment.move_id.ref:
                payment_ref += ' (' + payment.move_id.ref + ')'
            payment_vals.append({
                'name': payment.name,
                'journal_name': payment.journal_id.name,
                'amount': amount_to_show,
                'currency': currency_id.symbol,
                'digits': [69, currency_id.decimal_places],
                'position': currency_id.position,
                'date': payment.date,
                'payment_id': payment.id,
                'account_payment_id': payment.payment_id.id,
                'invoice_id': payment.invoice_id.id,
                'move_id': payment.move_id.id,
                'ref': payment_ref,
            })
        return payment_vals

    @api.one
    @api.depends('payment_move_line_ids.amount_residual')
    def _get_payment_info_JSON(self):
        self.payments_widget = json.dumps(False)
        if self.payment_move_line_ids:
            info = {'title': _('Less Payment'), 'outstanding': False, 'content': self._get_payments_vals()}
            self.payments_widget = json.dumps(info, default=date_utils.json_default)

    @api.one
    @api.depends('move_id.line_ids.amount_residual')
    def _compute_payments(self):
        payment_lines = set()
        for line in self.move_id.line_ids.filtered(lambda l: l.account_id.id == self.account_id.id):
            payment_lines.update(line.mapped('matched_credit_ids.credit_move_id.id'))
            payment_lines.update(line.mapped('matched_debit_ids.debit_move_id.id'))
        self.payment_move_line_ids = self.env['account.move.line'].browse(list(payment_lines)).sorted()

    @api.depends('move_id.partner_id', 'source_email')
    def _get_vendor_display_info(self):
        for invoice in self:
            vendor_display_name = invoice.partner_id.name
            invoice.invoice_icon = ''
            if not vendor_display_name:
                if invoice.source_email:
                    vendor_display_name = _('From: ') + invoice.source_email
                    invoice.invoice_icon = '@'
                else:
                    vendor_display_name = ('Created by: ') + invoice.create_uid.name
                    invoice.invoice_icon = '#'
            invoice.vendor_display_name = vendor_display_name

    def _get_seq_number_next_stuff(self):
        self.ensure_one()
        journal_sequence = self.journal_id.sequence_id
        if self.journal_id.refund_sequence:
            domain = [('type', '=', self.type)]
            journal_sequence = self.type in ['in_refund', 'out_refund'] and self.journal_id.refund_sequence_id or self.journal_id.sequence_id
        elif self.type in ['in_invoice', 'in_refund']:
            domain = [('type', 'in', ['in_invoice', 'in_refund'])]
        else:
            domain = [('type', 'in', ['out_invoice', 'out_refund'])]
        if self.id:
            domain += [('id', '<>', self.id)]
        domain += [('journal_id', '=', self.journal_id.id), ('state', 'not in', ['draft', 'cancel'])]
        return journal_sequence, domain

    @api.depends('state', 'move_id.journal_id', 'date_invoice')
    def _get_sequence_prefix(self):
        """ computes the prefix of the number that will be assigned to the first invoice/bill/refund of a journal, in order to
        let the user manually change it.
        """
        if not self.env.user._is_system():
            for invoice in self:
                invoice.sequence_number_next_prefix = False
                invoice.sequence_number_next = ''
            return
        for invoice in self:
            journal_sequence, domain = invoice._get_seq_number_next_stuff()
            if (invoice.state == 'draft') and not self.search(domain, limit=1):
                prefix, dummy = journal_sequence.with_context(ir_sequence_date=invoice.date_invoice,
                                                              ir_sequence_date_range=invoice.date_invoice)._get_prefix_suffix()
                invoice.sequence_number_next_prefix = prefix
            else:
                invoice.sequence_number_next_prefix = False

    @api.depends('state', 'move_id.journal_id')
    def _get_sequence_number_next(self):
        """ computes the number that will be assigned to the first invoice/bill/refund of a journal, in order to
        let the user manually change it.
        """
        for invoice in self:
            journal_sequence, domain = invoice._get_seq_number_next_stuff()
            if (invoice.state == 'draft') and not self.search(domain, limit=1):
                number_next = journal_sequence._get_current_sequence().number_next_actual
                invoice.sequence_number_next = '%%0%sd' % journal_sequence.padding % number_next
            else:
                invoice.sequence_number_next = ''

    @api.multi
    def _set_sequence_next(self):
        ''' Set the number_next on the sequence related to the invoice/bill/refund'''
        self.ensure_one()
        journal_sequence, domain = self._get_seq_number_next_stuff()
        if not self.env.user._is_admin() or not self.sequence_number_next or self.search_count(domain):
            return
        nxt = re.sub("[^0-9]", '', self.sequence_number_next)
        result = re.match("(0*)([0-9]+)", nxt)
        if result and journal_sequence:
            # use _get_current_sequence to manage the date range sequences
            sequence = journal_sequence._get_current_sequence()
            sequence.number_next = int(result.group(2))

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        account_id = False
        payment_term_id = False
        fiscal_position = False
        warning = {}
        domain = {}
        company_id = self.company_id.id
        p = self.partner_id if not company_id else self.partner_id.with_context(force_company=company_id)
        type = self.type
        if p:
            rec_account = p.property_account_receivable_id
            pay_account = p.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

            if type in ('out_invoice', 'out_refund'):
                account_id = rec_account.id
                payment_term_id = p.property_payment_term_id.id
            else:
                account_id = pay_account.id
                payment_term_id = p.property_supplier_payment_term_id.id

            delivery_partner_id = self.get_delivery_partner_id()
            fiscal_position = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id, delivery_id=delivery_partner_id)

            # If partner has no warning, check its company
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn and p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                    p = p.parent_id
                warning = {
                    'title': _("Warning for %s") % p.name,
                    'message': p.invoice_warn_msg
                    }
                if p.invoice_warn == 'block':
                    self.partner_id = False

        self.account_id = account_id
        self.payment_term_id = payment_term_id
        self.date_due = False
        self.fiscal_position_id = fiscal_position

        if type in ('in_invoice', 'out_refund'):
            bank_ids = p.commercial_partner_id.bank_ids
            bank_id = bank_ids[0].id if bank_ids else False
            self.partner_bank_id = bank_id
            domain = {'partner_bank_id': [('id', 'in', bank_ids.ids)]}

        res = {}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    @api.onchange('account_id')
    def _onchange_account_id(self):
        for move_line in self.pay_term_line_ids:
            move_line.account_id = self.account_id



    # @api.onchange('amount_total')
    # def _onchange_amount_total(self):
    #     for inv in self:
    #         if float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1:
    #             raise Warning(_('You cannot validate an invoice with a negative total amount. You should create a credit note instead.'))

    # # Load all Vendor Bill lines
    # @api.onchange('vendor_bill_id')
    # def _onchange_vendor_bill(self):
    #     if not self.vendor_bill_id:
    #         return {}
    #     self.currency_id = self.vendor_bill_id.currency_id
    #     new_lines = self.env['account.invoice.line']
    #     for line in self.vendor_bill_id.invoice_line_ids:
    #         new_lines += new_lines.new(line._prepare_invoice_line())
    #     self.invoice_line_ids += new_lines
    #     self.payment_term_id = self.vendor_bill_id.payment_term_id
    #     self.vendor_bill_id = False
    #     return {}

    # @api.onchange('partner_id', 'company_id')
    # def _onchange_partner_id(self):
    #

    # @api.onchange('payment_term_id', 'date_invoice')
    # def _onchange_payment_term_date_invoice(self):
    #     date_invoice = self.date_invoice
    #     if not date_invoice:
    #         date_invoice = fields.Date.context_today(self)
    #     if self.payment_term_id:
    #         pterm = self.payment_term_id
    #         pterm_list = pterm.with_context(currency_id=self.company_id.currency_id.id).compute(value=1, date_ref=date_invoice)
    #         self.date_due = max(line[0] for line in pterm_list)
    #     elif self.date_due and (date_invoice > self.date_due):
    #         self.date_due = date_invoice
    #
    # @api.onchange('cash_rounding_id', 'invoice_line_ids', 'tax_line_ids')
    # def _onchange_cash_rounding(self):
    #     # Drop previous cash rounding lines
    #     lines_to_remove = self.invoice_line_ids.filtered(lambda l: l.is_rounding_line)
    #     if lines_to_remove:
    #         self.invoice_line_ids -= lines_to_remove
    #
    #     # Clear previous rounded amounts
    #     for tax_line in self.tax_line_ids:
    #         if tax_line.amount_rounding != 0.0:
    #             tax_line.amount_rounding = 0.0
    #
    #     if self.cash_rounding_id and self.type in ('out_invoice', 'out_refund'):
    #         rounding_amount = self.cash_rounding_id.compute_difference(self.currency_id, self.amount_total)
    #         if not self.currency_id.is_zero(rounding_amount):
    #             if self.cash_rounding_id.strategy == 'biggest_tax':
    #                 # Search for the biggest tax line and add the rounding amount to it.
    #                 # If no tax found, an error will be raised by the _check_cash_rounding method.
    #                 if not self.tax_line_ids:
    #                     return
    #                 biggest_tax_line = None
    #                 for tax_line in self.tax_line_ids:
    #                     if not biggest_tax_line or tax_line.amount > biggest_tax_line.amount:
    #                         biggest_tax_line = tax_line
    #                 biggest_tax_line.amount_rounding += rounding_amount
    #             elif self.cash_rounding_id.strategy == 'add_invoice_line':
    #                 # Create a new invoice line to perform the rounding
    #                 rounding_line = self.env['account.invoice.line'].new({
    #                     'name': self.cash_rounding_id.name,
    #                     'invoice_id': self.id,
    #                     'account_id': self.cash_rounding_id.account_id.id,
    #                     'price_unit': rounding_amount,
    #                     'quantity': 1,
    #                     'is_rounding_line': True,
    #                     'sequence': 9999  # always last line
    #                 })
    #
    #                 # To be able to call this onchange manually from the tests,
    #                 # ensure the inverse field is updated on account.invoice.
    #                 if not rounding_line in self.invoice_line_ids:
    #                     self.invoice_line_ids += rounding_line

    # -------------------------------------------------------------------------
    # CONSTRAINS METHODS
    # -------------------------------------------------------------------------

    @api.constrains('partner_id', 'partner_bank_id')
    def validate_partner_bank_id(self):
        for record in self:
            if record.partner_bank_id:
                if record.type in ('in_invoice', 'out_refund') and record.partner_bank_id.partner_id != record.partner_id.commercial_partner_id:
                    raise ValidationError(_("Commercial partner and vendor account owners must be identical."))
                elif record.type in ('out_invoice', 'in_refund') and not record.company_id in record.partner_bank_id.partner_id.ref_company_ids:
                    raise ValidationError(_("The account selected for payment does not belong to the same company as this invoice."))

    @api.constrains('cash_rounding_id', 'tax_line_ids')
    def _check_cash_rounding(self):
        for inv in self:
            if inv.cash_rounding_id:
                rounding_amount = inv.cash_rounding_id.compute_difference(inv.currency_id, inv.amount_total)
                if rounding_amount != 0.0:
                    raise UserError(_('The cash rounding cannot be computed because the difference must '
                                      'be added on the biggest tax found and no tax are specified.\n'
                                      'Please set up a tax or change the cash rounding method.'))

    @api.multi
    def _check_duplicate_supplier_reference(self):
        for invoice in self:
            # refuse to validate a vendor bill/credit note if there already exists one with the same reference for the same partner,
            # because it's probably a double encoding of the same bill/credit note
            if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference), ('company_id', '=', invoice.company_id.id), ('commercial_partner_id', '=', invoice.commercial_partner_id.id), ('id', '!=', invoice.id)]):
                    raise UserError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note."))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        invoices = super(AccountInvoice, self.with_context(mail_create_nolog=True)).create(vals_list)
        for inv in invoices:
            inv.move_id.invoice_id = inv.id
        return invoices

    # @api.multi
    # def _write(self, vals):
    #     pre_not_reconciled = self.filtered(lambda invoice: not invoice.reconciled)
    #     pre_reconciled = self - pre_not_reconciled
    #     res = super(AccountInvoice, self)._write(vals)
    #     reconciled = self.filtered(lambda invoice: invoice.reconciled)
    #     not_reconciled = self - reconciled
    #     (reconciled & pre_reconciled).filtered(lambda invoice: invoice.state == 'open').action_invoice_paid()
    #     (not_reconciled & pre_not_reconciled).filtered(lambda invoice: invoice.state in ('in_payment', 'paid')).action_invoice_re_open()
    #     return res

    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an invoice which is not draft or cancelled. You should create a credit note instead.'))
            elif invoice.move_name:
                raise UserError(_('You cannot delete an invoice after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return super(AccountInvoice, self).unlink()

    @api.model
    def default_get(self, default_fields):
        # OVERRIDE
        values = super(AccountInvoice, self).default_get(default_fields)

        # Compute some default values.
        # This is done here because the invoice could not be stored yet inside the database and then,
        # the move_id is not set. However, some fields (e.g. journal_id) are related to the move_id
        # due to the inherits.
        if not values.get('partner_bank_id') and 'partner_bank_id' in default_fields:
            values['partner_bank_id'] = self._get_default_partner_bank_id(values)

        return values

    @api.multi
    def get_formview_id(self, access_uid=None):
        """ Update form view id of action to open the invoice """
        if self.type in ('in_invoice', 'in_refund'):
            return self.env.ref('account.invoice_supplier_form').id
        else:
            return self.env.ref('account.invoice_form').id

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        def get_view_id(xid, name):
            try:
                return self.env.ref('account.' + xid)
            except ValueError:
                view = self.env['ir.ui.view'].search([('name', '=', name)], limit=1)
                if not view:
                    return False
                return view.id

        context = self._context
        supplier_form_view_id = get_view_id('invoice_supplier_form', 'account.invoice.supplier.form').id
        if context.get('active_model') == 'res.partner' and context.get('active_ids'):
            partner = self.env['res.partner'].browse(context['active_ids'])[0]
            if not view_type:
                view_id = get_view_id('invoice_tree', 'account.invoice.tree')
                view_type = 'tree'
            elif view_type == 'form':
                if partner.supplier and not partner.customer:
                    view_id = supplier_form_view_id
                elif partner.customer and not partner.supplier:
                    view_id = get_view_id('invoice_form', 'account.invoice.form').id

        return super(AccountInvoice, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    @api.multi
    def _notify_get_groups(self, message, groups):
        """ Give access button to users and portal customer as portal is integrated
        in account. Customer and portal group have probably no right to see
        the document so they don't have the access button. """
        groups = super(AccountInvoice, self)._notify_get_groups(message, groups)

        if self.state not in ('draft', 'cancel'):
            for group_name, group_method, group_data in groups:
                if group_name in ('customer', 'portal'):
                    continue
                group_data['has_button_access'] = True

        return groups

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Credit Note'),
            'in_refund': _('Vendor Credit note'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s %s" % (inv.name or TYPES[inv.type], inv.name or '')))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        invoice_ids = []
        if name:
            invoice_ids = self._search([('number', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
        if not invoice_ids:
            invoice_ids = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        return self.browse(invoice_ids).name_get()

    # -------------------------------------------------------------------------
    # MISC
    # -------------------------------------------------------------------------

    def _compute_access_url(self):
        super(AccountInvoice, self)._compute_access_url()
        for invoice in self:
            invoice.access_url = '/my/invoices/%s' % (invoice.id)

    @api.multi
    def _get_report_base_filename(self):
        self.ensure_one()
        return  self.type == 'out_invoice' and self.state == 'draft' and _('Draft Invoice') or \
                self.type == 'out_invoice' and self.state in ('open','in_payment','paid') and _('Invoice - %s') % (self.name) or \
                self.type == 'out_refund' and self.state == 'draft' and _('Credit Note') or \
                self.type == 'out_refund' and _('Credit Note - %s') % (self.name) or \
                self.type == 'in_invoice' and self.state == 'draft' and _('Vendor Bill') or \
                self.type == 'in_invoice' and self.state in ('open','in_payment','paid') and _('Vendor Bill - %s') % (self.name) or \
                self.type == 'in_refund' and self.state == 'draft' and _('Vendor Credit Note') or \
                self.type == 'in_refund' and _('Vendor Credit Note - %s') % (self.name)

    @api.multi
    def invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.filtered(lambda inv: not inv.sent).write({'sent': True})
        if self.user_has_groups('account.group_account_invoice'):
            return self.env.ref('account.account_invoices').report_action(self)
        else:
            return self.env.ref('account.account_invoices_without_payment').report_action(self)

    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', False)
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            force_email=True
        )
        return {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_invoice_as_sent'):
            self.filtered(lambda inv: not inv.sent).write({'sent': True})
            self.env.user.company_id.set_onboarding_step_done('account_onboarding_sample_invoice_state')
        return super(AccountInvoice, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overrides mail_thread message_new(), called by the mailgateway through message_process,
            to complete values for vendor bills created by mails.
        """
        # Split `From` and `CC` email address from received email to look for related partners to subscribe on the invoice
        subscribed_emails = email_split((msg_dict.get('from') or '') + ',' + (msg_dict.get('cc') or ''))
        subscribed_partner_ids = [pid for pid in self._find_partner_from_emails(subscribed_emails) if pid]

        # Detection of the partner_id of the invoice:
        # 1) check if the email_from correspond to a supplier
        email_from = msg_dict.get('from') or ''
        email_from = email_escape_char(email_split(email_from)[0])
        partner_id = self._search_on_partner(email_from, extra_domain=[('supplier', '=', True)])

        # 2) otherwise, if the email sender is from odoo internal users then it is likely that the vendor sent the bill
        # by mail to the internal user who, inturn, forwarded that email to the alias to automatically generate the bill
        # on behalf of the vendor.
        if not partner_id:
            user_partner_id = self._search_on_user(email_from)
            if user_partner_id and user_partner_id in self.env.ref('base.group_user').users.mapped('partner_id').ids:
                # In this case, we will look for the vendor's email address in email's body and assume if will come first
                email_addresses = email_re.findall(msg_dict.get('body'))
                if email_addresses:
                    partner_ids = [pid for pid in self._find_partner_from_emails([email_addresses[0]], force_create=False) if pid]
                    partner_id = partner_ids and partner_ids[0]
            # otherwise, there's no fallback on the partner_id found for the regular author of the mail.message as we want
            # the partner_id to stay empty

        # If the partner_id can be found, subscribe it to the bill, otherwise it's left empty to be manually filled
        if partner_id:
            subscribed_partner_ids.append(partner_id)

        # Find the right purchase journal based on the "TO" email address
        destination_emails = email_split((msg_dict.get('to') or '') + ',' + (msg_dict.get('cc') or ''))
        alias_names = [mail_to.split('@')[0] for mail_to in destination_emails]
        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'), ('alias_name', 'in', alias_names)
        ], limit=1)

        # Create the message and the bill.
        values = dict(custom_values or {}, partner_id=partner_id, source_email=email_from)
        if journal:
            values['journal_id'] = journal.id
        # Passing `type` in context so that _default_journal(...) can correctly set journal for new vendor bill
        invoice = super(AccountInvoice, self.with_context(type=values.get('type'))).message_new(msg_dict, values)

        # Subscribe people on the newly created bill
        if subscribed_partner_ids:
            invoice.message_subscribe(subscribed_partner_ids)
        return invoice

    @api.model
    def complete_empty_list_help(self):
        # add help message about email alias in vendor bills empty lists
        Journal = self.env['account.journal']
        journals = Journal.browse(self._context.get('default_journal_id')) or Journal.search([('type', '=', 'purchase')])

        if journals:
            links = ''
            alias_count = 0
            for journal in journals.filtered(lambda j: j.alias_domain and j.alias_id.alias_name):
                email = format(journal.alias_id.alias_name) + "@" + format(journal.alias_domain)
                links += "<a id='o_mail_test' href='mailto:{}'>{}</a>".format(email, email) + ", "
                alias_count += 1
            if links and alias_count == 1:
                help_message = _('Or share the email %s to your vendors: bills will be created automatically upon mail reception.') % (links[:-2])
            elif links:
                help_message = _('Or share the emails %s to your vendors: bills will be created automatically upon mail reception.') % (links[:-2])
            else:
                help_message = _('''Or set an <a data-oe-id=%s data-oe-model="account.journal" href=#id=%s&model=account.journal>email alias</a> '''
                                              '''to allow draft vendor bills to be created upon reception of an email.''') % (journals[0].id, journals[0].id)
        else:
            help_message = _('<p>You can control the invoice from your vendor based on what you purchased or received.</p>')
        return help_message

    @api.multi
    def action_invoice_draft(self):
        if self.filtered(lambda inv: inv.state != 'cancel'):
            raise UserError(_("Invoice must be cancelled in order to reset it to draft."))
        # go from canceled state to draft state
        self.write({'state': 'draft', 'date': False})
        # Delete former printed invoice
        try:
            report_invoice = self.env['ir.actions.report']._get_report_from_name('account.report_invoice')
        except IndexError:
            report_invoice = False
        if report_invoice and report_invoice.attachment:
            for invoice in self:
                with invoice.env.do_in_draft():
                    invoice.name, invoice.state = invoice.move_name, 'open'
                    attachment = self.env.ref('account.account_invoices').retrieve_attachment(invoice)
                    invoice.name, invoice.state = False, 'draft'
                if attachment:
                    attachment.unlink()
        return True

    @api.multi
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: not inv.partner_id):
            raise UserError(_("The field Vendor is required, please complete it to validate the Vendor Bill."))
        if to_open_invoices.filtered(lambda inv: inv.state != 'draft'):
            raise UserError(_("Invoice must be in draft state in order to validate it."))
        if to_open_invoices.filtered(lambda inv: float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1):
            raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead."))
        if to_open_invoices.filtered(lambda inv: not inv.account_id):
            raise UserError(_('No account was found to create the invoice, be sure you have installed a chart of account.'))
        to_open_invoices.action_date_assign()
        to_open_invoices.invoice_validate()
        return to_open_invoices.action_move_create()

    @api.multi
    def action_invoice_paid(self):
        # lots of duplicate calls to action_invoice_paid, so we remove those already paid
        to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
        if to_pay_invoices.filtered(lambda inv: inv.state not in ('open', 'in_payment')):
            raise UserError(_('Invoice must be validated in order to set it to register payment.'))
        if to_pay_invoices.filtered(lambda inv: not inv.reconciled):
            raise UserError(_('You cannot pay an invoice which is partially paid. You need to reconcile payment entries first.'))

        for invoice in to_pay_invoices:
            if any([move.journal_id.post_at_bank_rec and move.state == 'draft' for move in invoice.payment_move_line_ids.mapped('move_id')]):
                invoice.write({'state': 'in_payment'})
            else:
                invoice.write({'state': 'paid'})

    @api.multi
    def action_invoice_re_open(self):
        if self.filtered(lambda inv: inv.state not in ('in_payment', 'paid')):
            raise UserError(_('Invoice must be paid in order to set it to register payment.'))
        return self.write({'state': 'open'})

    @api.multi
    def action_invoice_cancel(self):
        return self.filtered(lambda inv: inv.state != 'cancel').action_cancel()

    @api.multi
    def register_payment(self, payment_line, writeoff_acc_id=False, writeoff_journal_id=False):
        """ Reconcile payable/receivable lines from the invoice with payment_line """
        line_to_reconcile = self.env['account.move.line']
        for inv in self:
            line_to_reconcile += inv.move_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
        return (line_to_reconcile + payment_line).reconcile(writeoff_acc_id, writeoff_journal_id)

    @api.multi
    def assign_outstanding_credit(self, credit_aml_id):
        self.ensure_one()
        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if not credit_aml.currency_id and self.currency_id != self.company_id.currency_id:
            amount_currency = self.company_id.currency_id._convert(credit_aml.balance, self.currency_id, self.company_id, credit_aml.date or fields.Date.today())
            credit_aml.with_context(allow_amount_currency=True, check_move_validity=False).write({
                'amount_currency': amount_currency,
                'currency_id': self.currency_id.id})
        if credit_aml.payment_id:
            credit_aml.payment_id.write({'invoice_ids': [(4, self.id, None)]})
        return self.register_payment(credit_aml)

    @api.multi
    def action_date_assign(self):
        for inv in self:
            # Here the onchange will automatically write to the database
            inv._onchange_payment_term_date_invoice()
        return True

    def inv_line_characteristic_hashcode(self, invoice_line):
        """Overridable hashcode generation for invoice lines. Lines having the same hashcode
        will be grouped together if the journal has the 'group line' option. Of course a module
        can add fields to invoice lines that would need to be tested too before merging lines
        or not."""
        return "%s-%s-%s-%s-%s-%s-%s" % (
            invoice_line['account_id'],
            invoice_line.get('tax_ids', 'False'),
            invoice_line.get('tax_line_id', 'False'),
            invoice_line.get('product_id', 'False'),
            invoice_line.get('analytic_account_id', 'False'),
            invoice_line.get('date_maturity', 'False'),
            invoice_line.get('analytic_tag_ids', 'False'),
        )

    def group_lines(self, iml, line):
        """Merge account move lines (and hence analytic lines) if invoice line hashcodes are equals"""
        if self.journal_id.group_invoice_lines:
            line2 = {}
            for x, y, l in line:
                tmp = self.inv_line_characteristic_hashcode(l)
                if tmp in line2:
                    am = line2[tmp]['debit'] - line2[tmp]['credit'] + (l['debit'] - l['credit'])
                    line2[tmp]['debit'] = (am > 0) and am or 0.0
                    line2[tmp]['credit'] = (am < 0) and -am or 0.0
                    line2[tmp]['amount_currency'] += l['amount_currency']
                    line2[tmp]['analytic_line_ids'] += l['analytic_line_ids']
                    qty = l.get('quantity')
                    if qty:
                        line2[tmp]['quantity'] = line2[tmp].get('quantity', 0.0) + qty
                else:
                    line2[tmp] = l
            line = []
            for key, val in line2.items():
                line.append((0, 0, val))
        return line

    @api.multi
    def action_move_create(self):
        return True

    @api.multi
    def invoice_validate(self):
        for invoice in self.filtered(lambda invoice: invoice.partner_id not in invoice.message_partner_ids):
            invoice.message_subscribe([invoice.partner_id.id])

        for invoice in self:
            vals = {'state': 'open'}
            if not invoice.date_invoice:
                vals['date_invoice'] = fields.Date.context_today(self)
            if not invoice.date_due:
                vals['date_due'] = vals.get('date_invoice', invoice.date_invoice)

            if (invoice.move_name and invoice.move_name != '/'):
                new_name = invoice.move_name
            else:
                new_name = False
                journal = invoice.journal_id
                if journal.sequence_id:
                    # If invoice is actually refund and journal has a refund_sequence then use that one or use the regular one
                    sequence = journal.sequence_id
                    if invoice.type in ['out_refund', 'in_refund'] and journal.refund_sequence:
                        if not journal.refund_sequence_id:
                            raise UserError(_('Please define a sequence for the credit notes'))
                        sequence = journal.refund_sequence_id

                    new_name = sequence.with_context(ir_sequence_date=invoice.date or invoice.date_invoice).next_by_id()
                else:
                    raise UserError(_('Please define a sequence on the journal.'))
            #give the invoice its number directly as it's needed in _get_computed_reference()
            invoice.name = new_name

            # Auto-compute reference, if not already existing and if configured on company
            if not invoice.reference and invoice.type == 'out_invoice':
                vals['reference'] = invoice._get_computed_reference()

            invoice.write(vals)

        self._check_duplicate_supplier_reference()
        return True

    @api.model
    def line_get_convert(self, line, part):
        return self.env['product.product']._convert_prepared_anglosaxon_line(line, part)

    @api.multi
    def action_cancel(self):
        moves = self.env['account.move']
        for inv in self:
            if inv.move_id:
                moves += inv.move_id
            #unreconcile all journal items of the invoice, since the cancellation will unlink them anyway
            inv.move_id.line_ids.filtered(lambda x: x.account_id.reconcile).remove_move_reconcile()

        # First, set the invoices as cancelled and detach the move ids
        self.write({'state': 'cancel', 'move_id': False})
        if moves:
            # second, invalidate the move(s)
            moves.button_cancel()
            # delete the move this invoice was pointing to
            # Note that the corresponding move_lines and move_reconciles
            # will be automatically deleted too
            moves.unlink()
        return True

    ###################

    @api.model
    def _refund_cleanup_lines(self, lines):
        """ Convert records to dict of values suitable for one2many line creation

            :param recordset lines: records to convert
            :return: list of command tuple for one2many line creation [(0, 0, dict of valueis), ...]
        """
        result = []
        for line in lines:
            values = {}
            for name, field in line._fields.items():
                if name in MAGIC_COLUMNS:
                    continue
                elif field.type == 'many2one':
                    values[name] = line[name].id
                elif field.type not in ['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'invoice_line_tax_ids':
                    values[name] = [(6, 0, line[name].ids)]
                elif name == 'analytic_tag_ids':
                    values[name] = [(6, 0, line[name].ids)]
            result.append((0, 0, values))
        return result

    @api.model
    def _get_refund_common_fields(self):
        return ['partner_id', 'payment_term_id', 'account_id', 'currency_id', 'journal_id']

    @api.model
    def _get_refund_prepare_fields(self):
        return ['name', 'reference', 'comment', 'date_due']

    @api.model
    def _get_refund_modify_read_fields(self):
        read_fields = ['type', 'number', 'invoice_line_ids', 'tax_line_ids',
                       'date']
        return self._get_refund_common_fields() + self._get_refund_prepare_fields() + read_fields

    @api.model
    def _get_refund_copy_fields(self):
        copy_fields = ['company_id', 'user_id', 'fiscal_position_id']
        return self._get_refund_common_fields() + self._get_refund_prepare_fields() + copy_fields

    def _get_currency_rate_date(self):
        return self.date or self.date_invoice

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        """ Prepare the dict of values to create the new credit note from the invoice.
            This method may be overridden to implement custom
            credit note generation (making sure to call super() to establish
            a clean extension chain).

            :param record invoice: invoice as credit note
            :param string date_invoice: credit note creation date from the wizard
            :param integer date: force date from the wizard
            :param string description: description of the credit note from the wizard
            :param integer journal_id: account.journal from the wizard
            :return: dict of value to create() the credit note
        """
        values = {}
        for field in self._get_refund_copy_fields():
            if invoice._fields[field].type == 'many2one':
                values[field] = invoice[field].id
            else:
                values[field] = invoice[field] or False

        values['invoice_line_ids'] = self._refund_cleanup_lines(invoice.invoice_line_ids)

        tax_lines = invoice.tax_line_ids
        values['tax_line_ids'] = self._refund_cleanup_lines(tax_lines)

        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
        elif invoice['type'] == 'in_invoice':
            journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        else:
            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        values['journal_id'] = journal.id

        values['type'] = TYPE2REFUND[invoice['type']]
        values['date_invoice'] = date_invoice or fields.Date.context_today(invoice)
        values['state'] = 'draft'
        values['number'] = False
        values['origin'] = invoice.name
        values['payment_term_id'] = False
        values['refund_invoice_id'] = invoice.id

        if date:
            values['date'] = date
        if description:
            values['name'] = description
        return values

    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(invoice, date_invoice=date_invoice, date=date,
                                    description=description, journal_id=journal_id)
            refund_invoice = self.create(values)
            if invoice.type == 'out_invoice':
                message = _("This customer invoice credit note has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a><br>Reason: %s") % (invoice.id, invoice.name, description)
            else:
                message = _("This vendor bill credit note has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a><br>Reason: %s") % (invoice.id, invoice.name, description)

            refund_invoice.message_post(body=message)
            new_invoices += refund_invoice
        return new_invoices

    def _prepare_payment_vals(self, pay_journal, pay_amount=None, date=None, writeoff_acc=None, communication=None):
        payment_type = self.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
        if payment_type == 'inbound':
            payment_method = self.env.ref('account.account_payment_method_manual_in')
            journal_payment_methods = pay_journal.inbound_payment_method_ids
        else:
            payment_method = self.env.ref('account.account_payment_method_manual_out')
            journal_payment_methods = pay_journal.outbound_payment_method_ids

        if not communication:
            communication = self.type in ('in_invoice', 'in_refund') and self.reference or self.name
            if self.origin:
                communication = '%s (%s)' % (communication, self.origin)

        payment_vals = {
            'invoice_ids': [(6, 0, self.ids)],
            'amount': pay_amount or self.residual,
            'payment_date': date or fields.Date.context_today(self),
            'communication': communication,
            'partner_id': self.partner_id.id,
            'partner_type': self.type in ('out_invoice', 'out_refund') and 'customer' or 'supplier',
            'journal_id': pay_journal.id,
            'payment_type': payment_type,
            'payment_method_id': payment_method.id,
            'payment_difference_handling': writeoff_acc and 'reconcile' or 'open',
            'writeoff_account_id': writeoff_acc and writeoff_acc.id or False,
        }
        return payment_vals

    @api.multi
    def pay_and_reconcile(self, pay_journal, pay_amount=None, date=None, writeoff_acc=None):
        """ Create and post an account.payment for the invoice self, which creates a journal entry that reconciles the invoice.

            :param pay_journal: journal in which the payment entry will be created
            :param pay_amount: amount of the payment to register, defaults to the residual of the invoice
            :param date: payment date, defaults to fields.Date.context_today(self)
            :param writeoff_acc: account in which to create a writeoff if pay_amount < self.residual, so that the invoice is fully paid
        """
        if isinstance(pay_journal, int):
            pay_journal = self.env['account.journal'].browse([pay_journal])
        assert len(self) == 1, "Can only pay one invoice at a time."

        payment_vals = self._prepare_payment_vals(pay_journal, pay_amount=pay_amount, date=date, writeoff_acc=writeoff_acc)
        payment = self.env['account.payment'].create(payment_vals)
        payment.post()

        return True

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'paid' and self.type in ('out_invoice', 'out_refund'):
            return self.env.ref('account.mt_invoice_paid')
        elif 'state' in init_values and self.state == 'open' and self.type in ('out_invoice', 'out_refund'):
            return self.env.ref('account.mt_invoice_validated')
        elif 'state' in init_values and self.state == 'draft' and self.type in ('out_invoice', 'out_refund'):
            return self.env.ref('account.mt_invoice_created')
        return super(AccountInvoice, self)._track_subtype(init_values)

    def _amount_by_group(self):
        for invoice in self:
            currency = invoice.currency_id or invoice.company_id.currency_id
            fmt = partial(formatLang, invoice.with_context(lang=invoice.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in invoice.tax_line_ids:
                res.setdefault(line.tax_line_id.tax_group_id, {'base': 0.0, 'amount': 0.0})
                res[line.tax_line_id.tax_group_id]['amount'] += line.amount_total
                res[line.tax_line_id.tax_group_id]['base'] += line.base
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            invoice.amount_by_group = [(
                r[0].name, r[1]['amount'], r[1]['base'],
                fmt(r[1]['amount']), fmt(r[1]['base']),
                len(res),
            ) for r in res]

    @api.multi
    def preview_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

