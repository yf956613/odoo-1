# -*- coding: utf-8 -*-

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import Form, SavepointCase

import logging

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestAccountInvoice(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountInvoice, cls).setUpClass()

        chart_template = cls.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False)
        if not chart_template:
            _logger.warning('TestAccountInvoice skipped because l10n_generic_coa is not installed')
            cls.skipTest("l10n_generic_coa not installed")

        # Create companies.
        cls.company_parent = cls.env['res.company'].create({
            'name': 'company_parent',
            'currency_id': cls.env.ref('base.USD').id,
        })

        # EUR = 2 USD
        cls.eur_to_usd = cls.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 2.0,
            'currency_id': cls.env.ref('base.EUR').id,
            'company_id': cls.company_parent.id,
        })

        # Create user.
        user = cls.env['res.users'].create({
            'name': 'Because I am invoiceman!',
            'login': 'invoiceman',
            'groups_id': [(6, 0, (cls.env.user.groups_id + cls.env.ref('account.group_account_user')).ids)],
            'company_id': cls.company_parent.id,
            'company_ids': [(6, 0, cls.company_parent.ids)],
        })
        user.partner_id.email = 'invoiceman@test.com'

        # Shadow the current environment/cursor with one having the report user.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        # Get the new chart of accounts using the new environment.
        chart_template = cls.env.ref('l10n_generic_coa.configurable_chart_template')

        cls.partner_a = cls.env['res.partner'].create({'name': 'partner_a', 'company_id': False})
        cls.partner_b = cls.env['res.partner'].create({'name': 'partner_b', 'company_id': False})

        chart_template.try_loading_for_current_company()

        cls.sale_journal_parent = cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.company_parent.id)], limit=1)
        cls.purchase_journal_parent = cls.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', cls.company_parent.id)], limit=1)
        cls.receivable_parent = cls.env['account.account'].search([
            ('user_type_id', '=', cls.env.ref('account.data_account_type_receivable').id),
            ('company_id', '=', cls.company_parent.id)
        ], limit=1)
        cls.bank_journal_parent = cls.env['account.journal'].search(
            [('type', '=', 'bank'), ('company_id', '=', cls.company_parent.id)], limit=1)

    def _create_invoice(self, invoice_type):
        # 'type' must be present in the context to get the right default journal.
        self_ctx = self.env['account.invoice'].with_context(type=invoice_type)
        journal_id = self_ctx.default_get(['journal_id'])['journal_id']
        # 'journal_id' must be present in the context to get the right default invoice_line account.
        self_ctx = self_ctx.with_context(journal_id=journal_id)

        view = 'account.invoice_form' if 'out' in invoice_type else 'account.invoice_supplier_form'
        return Form(self_ctx, view=view)

    # -------------------------------------------------------------------------
    # TESTS METHODS
    # -------------------------------------------------------------------------

    def test_sequence_number_next(self):
        ''' Create an invoice for the first time.
        The user is able to specify the 'next_number' field value of the journal's sequence.
        '''
        self.sale_journal_parent.write({
            'refund_sequence': True,
            'refund_sequence_id': self.sale_journal_parent.sequence_id.copy().id,
        })

        # ==== Test out_invoice ====

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        invoice_form.sequence_number_next = '0042'
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.0
        invoice = invoice_form.save()
        invoice.action_invoice_open()

        self.assertEquals(invoice.journal_id, self.sale_journal_parent)
        self.assertEquals(invoice.number, 'INV/%s/0042' % fields.Date.today().year)

        # ==== Test out_refund ====

        invoice_form = self._create_invoice('out_refund')
        invoice_form.partner_id = self.partner_a
        invoice_form.sequence_number_next = '0042'
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.0
        invoice = invoice_form.save()
        invoice.action_invoice_open()

        self.assertEquals(invoice.journal_id, self.sale_journal_parent)
        self.assertEquals(invoice.number, 'INV/%s/0042' % fields.Date.today().year)

    def test_journal_id(self):
        ''' Test default values/onchange based on the 'journal_id' field. '''
        # Duplicate journals to have ones having a foreign currency.
        sale_journal_curr = self.sale_journal_parent.copy()
        purchase_journal_curr = self.purchase_journal_parent.copy()
        (sale_journal_curr + purchase_journal_curr).write({'currency_id': self.env.ref('base.MXN').id})

        # ==== Test out_invoice ====

        sale_journal_curr.sequence += 1
        self.sale_journal_parent.sequence += 2

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a

        self.assertEquals(invoice_form.journal_id, sale_journal_curr)
        self.assertEquals(invoice_form.currency_id, sale_journal_curr.currency_id)
        self.assertEquals(invoice_form.company_id, self.company_parent)

        invoice_form.journal_id = self.sale_journal_parent

        self.assertEquals(invoice_form.journal_id, self.sale_journal_parent)
        self.assertEquals(invoice_form.currency_id, self.company_parent.currency_id)
        self.assertEquals(invoice_form.company_id, self.company_parent)

        sale_journal_curr.sequence -= 1
        self.sale_journal_parent.sequence -= 2

        # ==== Test in_invoice ====

        purchase_journal_curr.sequence += 1
        self.purchase_journal_parent.sequence += 2

        invoice_form = self._create_invoice('in_invoice')
        invoice_form.partner_id = self.partner_a

        self.assertEquals(invoice_form.journal_id.name, purchase_journal_curr.name)
        self.assertEquals(invoice_form.currency_id, purchase_journal_curr.currency_id)
        self.assertEquals(invoice_form.company_id, self.company_parent)

        invoice_form.journal_id = self.purchase_journal_parent

        self.assertEquals(invoice_form.journal_id, self.purchase_journal_parent)
        self.assertEquals(invoice_form.currency_id, self.company_parent.currency_id)
        self.assertEquals(invoice_form.company_id, self.company_parent)

        purchase_journal_curr.sequence -= 1
        self.purchase_journal_parent.sequence -= 2

    def test_vendor_display_info(self):
        ''' Test the computation of the 'vendor_display_name'/'source_email' fields. '''

        # ==== Test vendor_display_name with vendor ====

        invoice_form = self._create_invoice('in_invoice')
        invoice_form.partner_id = self.partner_a
        invoice = invoice_form.save()

        self.assertTrue(invoice.partner_id.name in invoice.vendor_display_name)

        # ==== Test vendor_display_name created by user ====

        invoice_form = self._create_invoice('in_invoice')
        invoice = invoice_form.save()

        self.assertTrue(self.env.user.name in invoice.vendor_display_name)

        # ==== Test vendor_display_name from email ====

        invoice.source_email = self.env.user.partner_id.email

        self.assertTrue(self.env.user.partner_id.email in invoice.vendor_display_name)

    def test_reference(self):
        ''' Test the 'reference' field. '''

        # ==== Test free reference ====

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        invoice_form.reference = 'xxxxxxxxxxxxxxxxxx'
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.0
        invoice = invoice_form.save()
        invoice.action_invoice_open()

        self.assertEquals(invoice.reference, 'xxxxxxxxxxxxxxxxxx')

        # ==== Test reference based on number ====

        self.company_parent.invoice_reference_type = 'invoice_number'

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.0
        invoice = invoice_form.save()
        invoice.action_invoice_open()

        self.assertEquals(invoice.reference, 'INV/%s/0002/02' % fields.Date.today().year)

        # ==== Test reference based on partner ====

        self.company_parent.invoice_reference_type = 'partner'

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.0
        invoice = invoice_form.save()
        invoice.action_invoice_open()

        self.assertEquals(invoice.reference, 'CUST/%s' % str(self.partner_a.id % 97).rjust(2, '0'))

    def test_vendor_bill_id(self):
        ''' When setting the 'vendor_bill_id' field on an invoice, the invoice lines and the payment terms
        are loaded from this one.
        '''
        account_payment_term_45days = self.env.ref('account.account_payment_term_45days')
        account_payment_term_2months = self.env.ref('account.account_payment_term_2months')

        invoice_form = self._create_invoice('in_invoice')
        invoice_form.partner_id = self.partner_a
        invoice_form.payment_term_id = account_payment_term_2months
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 200
        vendor_bill = invoice_form.save()
        vendor_bill_line = vendor_bill.invoice_line_ids

        invoice_form = self._create_invoice('in_invoice')
        invoice_form.partner_id = self.partner_a
        invoice_form.payment_term_id = account_payment_term_45days
        invoice_form.vendor_bill_id = vendor_bill
        invoice = invoice_form.save()

        self.assertEquals(len(invoice.invoice_line_ids), 1)
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': vendor_bill_line.name,
            'price_unit': vendor_bill_line.price_unit,
            'quantity': vendor_bill_line.quantity,
            'account_id': vendor_bill_line.account_id.id,
        }])
        self.assertEquals(invoice.payment_term_id, vendor_bill.payment_term_id)

    def test_payment_term_id(self):
        ''' Ensure the 'due_date' is computed based on the 'payment_term_id'. '''
        account_payment_term_45days = self.env.ref('account.account_payment_term_45days')
        account_payment_term_2months = self.env.ref('account.account_payment_term_2months')

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        invoice_form.date_invoice = fields.Date.from_string('2017-01-01')
        invoice_form.payment_term_id = account_payment_term_45days

        self.assertEquals(invoice_form.date_due, fields.Date.from_string('2017-02-15'))

        invoice_form.payment_term_id = account_payment_term_2months

        self.assertEquals(invoice_form.date_due, fields.Date.from_string('2017-03-02'))

    def test_partner_bank_id(self):
        ''' Ensure the 'partner_bank_id' field is set as a default value. '''
        self.env['res.partner.bank'].create({
            'acc_number': 'aaaabbbbcccc',
            'bank_name': 'Bank',
            'partner_id': self.company_parent.partner_id.id,
        })
        self.env['res.partner.bank'].create({
            'acc_number': 'ddddeeeeffff',
            'bank_name': 'Bank',
            'partner_id': self.partner_a.id,
        })

        # ==== Test out_invoice ====

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        invoice = invoice_form.save()

        self.assertEquals(invoice.partner_bank_id, self.company_parent.partner_id.bank_ids)

        # ==== Test out_refund ====

        invoice_form = self._create_invoice('out_refund')
        invoice_form.partner_id = self.partner_a
        invoice = invoice_form.save()

        self.assertEquals(invoice.partner_bank_id, self.partner_a.bank_ids)

        # ==== Test in_invoice ====

        invoice_form = self._create_invoice('in_invoice')
        invoice_form.partner_id = self.partner_a
        invoice = invoice_form.save()

        self.assertEquals(invoice.partner_bank_id, self.partner_a.bank_ids)

        # ==== Test in_refund ====

        invoice_form = self._create_invoice('in_refund')
        invoice_form.partner_id = self.partner_a
        invoice = invoice_form.save()

        self.assertEquals(invoice.partner_bank_id, self.company_parent.partner_id.bank_ids)

    def test_partner_id(self):
        ''' Test default values/onchange based on the 'partner_id' field. '''
        self.partner_a.property_account_position_id = self.env['account.fiscal.position'].create({'name': 'aaaa'})
        self.partner_b.property_account_position_id = self.env['account.fiscal.position'].create({'name': 'bbbb'})

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a

        self.assertEquals(invoice_form.account_id, self.partner_a.property_account_receivable_id)
        self.assertEquals(invoice_form.fiscal_position_id, self.partner_a.property_account_position_id)

        invoice_form.partner_id = self.partner_b

        self.assertEquals(invoice_form.account_id, self.partner_b.property_account_receivable_id)
        self.assertEquals(invoice_form.fiscal_position_id, self.partner_b.property_account_position_id)

    def test_amounts(self):
        ''' Test computation of all amounts in account.invoice, account.invoice.line and
        account.invoice.tax.
        '''
        # ==== Test out_invoice ====

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.quantity = 2
            invoice_line_form.price_unit = 100.0
            invoice_line_form.discount = 10.0
        invoice = invoice_form.save()

        self.assertEquals(invoice.invoice_line_ids.price_subtotal, 180.0)
        self.assertEquals(invoice.invoice_line_ids.price_subtotal_signed, 180.0)
        self.assertEquals(invoice.invoice_line_ids.price_total, 207.0)
        self.assertEquals(invoice.tax_line_ids.base, 180.0)
        self.assertEquals(invoice.tax_line_ids.amount_total, 27.0)
        self.assertEquals(invoice.amount_untaxed, 180.0)
        self.assertEquals(invoice.amount_tax, 27.0)
        self.assertEquals(invoice.amount_total, 207.0)
        self.assertEquals(invoice.amount_total_signed, 207.0)
        self.assertEquals(invoice.amount_total_company_signed, 207.0)
        self.assertEquals(invoice.amount_untaxed_signed, 180.0)

        invoice.action_invoice_open()

        self.assertTrue(invoice.move_id)
        self.assertEquals(len(invoice.move_id.line_ids), 3)
        self.assertRecordValues(invoice.move_id.line_ids, [
            {
                'name': '',
                'account_id': invoice.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 207.0,
                'credit': 0.00,
            },
            {
                'name': 'Tax 15.00%',
                'account_id': invoice.tax_line_ids.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 0.00,
                'credit': 27.00,
            },
            {
                'name': 'test',
                'account_id': invoice.invoice_line_ids.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 0.00,
                'credit': 180.00,
            },
        ])

        # ==== Test out_refund ====

        invoice_form = self._create_invoice('out_refund')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.quantity = 2
            invoice_line_form.price_unit = 100.0
            invoice_line_form.discount = 10
        invoice = invoice_form.save()

        self.assertEquals(invoice.invoice_line_ids.price_subtotal, 180.0)
        self.assertEquals(invoice.invoice_line_ids.price_subtotal_signed, -180.0)
        self.assertEquals(invoice.invoice_line_ids.price_total, 207.0)
        self.assertEquals(invoice.tax_line_ids.base, 180.0)
        self.assertEquals(invoice.tax_line_ids.amount_total, 27.0)
        self.assertEquals(invoice.amount_untaxed, 180.0)
        self.assertEquals(invoice.amount_tax, 27.0)
        self.assertEquals(invoice.amount_total, 207.0)
        self.assertEquals(invoice.amount_total_signed, -207.0)
        self.assertEquals(invoice.amount_total_company_signed, -207.0)
        self.assertEquals(invoice.amount_untaxed_signed, -180.0)

        invoice.action_invoice_open()

        self.assertTrue(invoice.move_id)
        self.assertEquals(len(invoice.move_id.line_ids), 3)
        self.assertRecordValues(invoice.move_id.line_ids, [
            {
                'name': '',
                'account_id': invoice.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 0.00,
                'credit': 207.00,
            },
            {
                'name': 'Tax 15.00%',
                'account_id': invoice.tax_line_ids.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 27.00,
                'credit': 0.00,
            },
            {
                'name': 'test',
                'account_id': invoice.invoice_line_ids.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 180.00,
                'credit': 0.00,
            },
        ])

        # ==== Test in_invoice ====

        invoice_form = self._create_invoice('in_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.quantity = 2
            invoice_line_form.price_unit = 100.0
            invoice_line_form.discount = 10
        invoice = invoice_form.save()

        self.assertEquals(invoice.invoice_line_ids.price_subtotal, 180.0)
        self.assertEquals(invoice.invoice_line_ids.price_subtotal_signed, 180.0)
        self.assertEquals(invoice.invoice_line_ids.price_total, 207.0)
        self.assertEquals(invoice.tax_line_ids.base, 180.0)
        self.assertEquals(invoice.tax_line_ids.amount_total, 27.0)
        self.assertEquals(invoice.amount_untaxed, 180.0)
        self.assertEquals(invoice.amount_tax, 27.0)
        self.assertEquals(invoice.amount_total, 207.0)
        self.assertEquals(invoice.amount_total_signed, 207.0)
        self.assertEquals(invoice.amount_total_company_signed, 207.0)
        self.assertEquals(invoice.amount_untaxed_signed, 180.0)

        invoice.action_invoice_open()

        self.assertTrue(invoice.move_id)
        self.assertEquals(len(invoice.move_id.line_ids), 3)
        self.assertRecordValues(invoice.move_id.line_ids, [
            {
                'name': '',
                'account_id': invoice.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 0.00,
                'credit': 207.00,
            },
            {
                'name': 'Tax 15.00%',
                'account_id': invoice.tax_line_ids.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 27.00,
                'credit': 0.00,
            },
            {
                'name': 'test',
                'account_id': invoice.invoice_line_ids.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 180.00,
                'credit': 0.00,
            },
        ])

        # ==== Test in_refund ====

        invoice_form = self._create_invoice('in_refund')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.quantity = 2
            invoice_line_form.price_unit = 100.0
            invoice_line_form.discount = 10
        invoice = invoice_form.save()

        self.assertEquals(invoice.invoice_line_ids.price_subtotal, 180.0)
        self.assertEquals(invoice.invoice_line_ids.price_subtotal_signed, -180.0)
        self.assertEquals(invoice.invoice_line_ids.price_total, 207.0)
        self.assertEquals(invoice.tax_line_ids.base, 180.0)
        self.assertEquals(invoice.tax_line_ids.amount_total, 27.0)
        self.assertEquals(invoice.amount_untaxed, 180.0)
        self.assertEquals(invoice.amount_tax, 27.0)
        self.assertEquals(invoice.amount_total, 207.0)
        self.assertEquals(invoice.amount_total_signed, -207.0)
        self.assertEquals(invoice.amount_total_company_signed, -207.0)
        self.assertEquals(invoice.amount_untaxed_signed, -180.0)

        invoice.action_invoice_open()

        self.assertTrue(invoice.move_id)
        self.assertEquals(len(invoice.move_id.line_ids), 3)
        self.assertRecordValues(invoice.move_id.line_ids, [
            {
                'name': '',
                'account_id': invoice.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 207.00,
                'credit': 0.00,
            },
            {
                'name': 'Tax 15.00%',
                'account_id': invoice.tax_line_ids.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 0.00,
                'credit': 27.00,
            },
            {
                'name': 'test',
                'account_id': invoice.invoice_line_ids.account_id.id,
                'amount_currency': 0.00,
                'currency_id': False,
                'debit': 0.00,
                'credit': 180.00,
            },
        ])

    def test_amounts_currency(self):
        ''' Test computation of all amounts with a foreign currency in account.invoice,
        account.invoice.line and account.invoice.tax.
        '''
        # ==== Test out_invoice ====

        eur = self.env.ref('base.EUR')

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        invoice_form.currency_id = eur
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.quantity = 2
            invoice_line_form.price_unit = 100.0
            invoice_line_form.discount = 10.0
        invoice = invoice_form.save()

        self.assertEquals(invoice.invoice_line_ids.price_subtotal, 180.0)
        self.assertEquals(invoice.invoice_line_ids.price_subtotal_signed, 90.0)
        self.assertEquals(invoice.invoice_line_ids.price_total, 207.0)
        self.assertEquals(invoice.tax_line_ids.base, 180.0)
        self.assertEquals(invoice.tax_line_ids.amount_total, 27.0)
        self.assertEquals(invoice.amount_untaxed, 180.0)
        self.assertEquals(invoice.amount_tax, 27.0)
        self.assertEquals(invoice.amount_total, 207.0)
        self.assertEquals(invoice.amount_total_signed, 207.0)
        self.assertEquals(invoice.amount_total_company_signed, 103.50)
        self.assertEquals(invoice.amount_untaxed_signed, 90.0)

        invoice.action_invoice_open()

        self.assertTrue(invoice.move_id)
        self.assertEquals(len(invoice.move_id.line_ids), 3)
        self.assertRecordValues(invoice.move_id.line_ids, [
            {
                'name': '',
                'account_id': invoice.account_id.id,
                'amount_currency': 207.00,
                'currency_id': eur.id,
                'debit': 103.50,
                'credit': 0.00,
            },
            {
                'name': 'Tax 15.00%',
                'account_id': invoice.tax_line_ids.account_id.id,
                'amount_currency': -27.00,
                'currency_id': eur.id,
                'debit': 0.00,
                'credit': 13.50,
            },
            {
                'name': 'test',
                'account_id': invoice.invoice_line_ids.account_id.id,
                'amount_currency': -180.00,
                'currency_id': eur.id,
                'debit': 0.00,
                'credit': 90.00,
            },
        ])

        # ==== Test out_refund ====

        invoice_form = self._create_invoice('out_refund')
        invoice_form.partner_id = self.partner_a
        invoice_form.currency_id = eur
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.quantity = 2
            invoice_line_form.price_unit = 100.0
            invoice_line_form.discount = 10
        invoice = invoice_form.save()

        self.assertEquals(invoice.invoice_line_ids.price_subtotal, 180.0)
        self.assertEquals(invoice.invoice_line_ids.price_subtotal_signed, -90.0)
        self.assertEquals(invoice.invoice_line_ids.price_total, 207.0)
        self.assertEquals(invoice.tax_line_ids.base, 180.0)
        self.assertEquals(invoice.tax_line_ids.amount_total, 27.0)
        self.assertEquals(invoice.amount_untaxed, 180.0)
        self.assertEquals(invoice.amount_tax, 27.0)
        self.assertEquals(invoice.amount_total, 207.0)
        self.assertEquals(invoice.amount_total_signed, -207.0)
        self.assertEquals(invoice.amount_total_company_signed, -103.50)
        self.assertEquals(invoice.amount_untaxed_signed, -90.0)

        invoice.action_invoice_open()

        self.assertTrue(invoice.move_id)
        self.assertEquals(len(invoice.move_id.line_ids), 3)
        self.assertRecordValues(invoice.move_id.line_ids, [
            {
                'name': '',
                'account_id': invoice.account_id.id,
                'amount_currency': -207.00,
                'currency_id': eur.id,
                'debit': 0.00,
                'credit': 103.50,
            },
            {
                'name': 'Tax 15.00%',
                'account_id': invoice.tax_line_ids.account_id.id,
                'amount_currency': 27.00,
                'currency_id': eur.id,
                'debit': 13.50,
                'credit': 0.00,
            },
            {
                'name': 'test',
                'account_id': invoice.invoice_line_ids.account_id.id,
                'amount_currency': 180.00,
                'currency_id': eur.id,
                'debit': 90.00,
                'credit': 0.00,
            },
        ])

        # ==== Test in_invoice ====

        invoice_form = self._create_invoice('in_invoice')
        invoice_form.partner_id = self.partner_a
        invoice_form.currency_id = eur
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.quantity = 2
            invoice_line_form.price_unit = 100.0
            invoice_line_form.discount = 10
        invoice = invoice_form.save()

        self.assertEquals(invoice.invoice_line_ids.price_subtotal, 180.0)
        self.assertEquals(invoice.invoice_line_ids.price_subtotal_signed, 90.0)
        self.assertEquals(invoice.invoice_line_ids.price_total, 207.0)
        self.assertEquals(invoice.tax_line_ids.base, 180.0)
        self.assertEquals(invoice.tax_line_ids.amount_total, 27.0)
        self.assertEquals(invoice.amount_untaxed, 180.0)
        self.assertEquals(invoice.amount_tax, 27.0)
        self.assertEquals(invoice.amount_total, 207.0)
        self.assertEquals(invoice.amount_total_signed, 207.0)
        self.assertEquals(invoice.amount_total_company_signed, 103.50)
        self.assertEquals(invoice.amount_untaxed_signed, 90.0)

        invoice.action_invoice_open()

        self.assertTrue(invoice.move_id)
        self.assertEquals(len(invoice.move_id.line_ids), 3)
        self.assertRecordValues(invoice.move_id.line_ids, [
            {
                'name': '',
                'account_id': invoice.account_id.id,
                'amount_currency': -207.00,
                'currency_id': eur.id,
                'debit': 0.00,
                'credit': 103.50,
            },
            {
                'name': 'Tax 15.00%',
                'account_id': invoice.tax_line_ids.account_id.id,
                'amount_currency': 27.00,
                'currency_id': eur.id,
                'debit': 13.50,
                'credit': 0.00,
            },
            {
                'name': 'test',
                'account_id': invoice.invoice_line_ids.account_id.id,
                'amount_currency': 180.00,
                'currency_id': eur.id,
                'debit': 90.00,
                'credit': 0.00,
            },
        ])

        # ==== Test in_refund ====

        invoice_form = self._create_invoice('in_refund')
        invoice_form.partner_id = self.partner_a
        invoice_form.currency_id = eur
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.quantity = 2
            invoice_line_form.price_unit = 100.0
            invoice_line_form.discount = 10
        invoice = invoice_form.save()

        self.assertEquals(invoice.invoice_line_ids.price_subtotal, 180.0)
        self.assertEquals(invoice.invoice_line_ids.price_subtotal_signed, -90.0)
        self.assertEquals(invoice.invoice_line_ids.price_total, 207.0)
        self.assertEquals(invoice.tax_line_ids.base, 180.0)
        self.assertEquals(invoice.tax_line_ids.amount_total, 27.0)
        self.assertEquals(invoice.amount_untaxed, 180.0)
        self.assertEquals(invoice.amount_tax, 27.0)
        self.assertEquals(invoice.amount_total, 207.0)
        self.assertEquals(invoice.amount_total_signed, -207.0)
        self.assertEquals(invoice.amount_total_company_signed, -103.50)
        self.assertEquals(invoice.amount_untaxed_signed, -90.0)

        invoice.action_invoice_open()

        self.assertTrue(invoice.move_id)
        self.assertEquals(len(invoice.move_id.line_ids), 3)
        self.assertRecordValues(invoice.move_id.line_ids, [
            {
                'name': '',
                'account_id': invoice.account_id.id,
                'amount_currency': 207.00,
                'currency_id': eur.id,
                'debit': 103.50,
                'credit': 0.00,
            },
            {
                'name': 'Tax 15.00%',
                'account_id': invoice.tax_line_ids.account_id.id,
                'amount_currency': -27.00,
                'currency_id': eur.id,
                'debit': 0.00,
                'credit': 13.50,
            },
            {
                'name': 'test',
                'account_id': invoice.invoice_line_ids.account_id.id,
                'amount_currency': -180.00,
                'currency_id': eur.id,
                'debit': 0.00,
                'credit': 90.00,
            },
        ])

    def test_cash_rounding(self):
        ''' Test the cash rounding feature. '''

        # ==== Test add_invoice_line ====

        cash_rounding_up = self.env['account.cash.rounding'].create({
            'name': 'rounding',
            'rounding': 0.5,
            'account_id': self.receivable_parent.id,
            'strategy': 'add_invoice_line',
            'rounding_method': 'UP',
        })
        cash_rounding_down = self.env['account.cash.rounding'].create({
            'name': 'rounding',
            'rounding': 1.0,
            'account_id': self.receivable_parent.id,
            'strategy': 'add_invoice_line',
            'rounding_method': 'DOWN',
        })
        cash_rounding_halfup = self.env['account.cash.rounding'].create({
            'name': 'rounding',
            'rounding': 1.0,
            'account_id': self.receivable_parent.id,
            'strategy': 'add_invoice_line',
            'rounding_method': 'HALF-UP',
        })

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.2
            invoice_line_form.invoice_line_tax_ids.clear()
        invoice_form.cash_rounding_id = cash_rounding_up
        invoice = invoice_form.save()

        self.assertEquals(len(invoice.invoice_line_ids), 2)
        self.assertEquals(invoice.invoice_line_ids[0].price_total, 100.2)
        self.assertEquals(invoice.invoice_line_ids[1].price_total, 0.3)

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.9
            invoice_line_form.invoice_line_tax_ids.clear()
        invoice_form.cash_rounding_id = cash_rounding_down
        invoice = invoice_form.save()

        self.assertEquals(len(invoice.invoice_line_ids), 2)
        self.assertEquals(invoice.invoice_line_ids[0].price_total, 100.9)
        self.assertEquals(invoice.invoice_line_ids[1].price_total, -0.9)

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.5
            invoice_line_form.invoice_line_tax_ids.clear()
        invoice_form.cash_rounding_id = cash_rounding_halfup
        invoice = invoice_form.save()

        self.assertEquals(len(invoice.invoice_line_ids), 2)
        self.assertEquals(invoice.invoice_line_ids[0].price_total, 100.5)
        self.assertEquals(invoice.invoice_line_ids[1].price_total, 0.5)

        # ==== Test biggest_tax ====

        cash_rounding_up = self.env['account.cash.rounding'].create({
            'name': 'rounding',
            'rounding': 0.5,
            'account_id': self.receivable_parent.id,
            'strategy': 'biggest_tax',
            'rounding_method': 'UP',
        })
        cash_rounding_down = self.env['account.cash.rounding'].create({
            'name': 'rounding',
            'rounding': 1.0,
            'account_id': self.receivable_parent.id,
            'strategy': 'biggest_tax',
            'rounding_method': 'DOWN',
        })
        cash_rounding_halfup = self.env['account.cash.rounding'].create({
            'name': 'rounding',
            'rounding': 1.0,
            'account_id': self.receivable_parent.id,
            'strategy': 'biggest_tax',
            'rounding_method': 'HALF-UP',
        })

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.20
        invoice_form.cash_rounding_id = cash_rounding_up
        invoice = invoice_form.save()

        self.assertEquals(len(invoice.invoice_line_ids), 1)
        self.assertEquals(invoice.invoice_line_ids.price_total, 115.23)
        self.assertEquals(len(invoice.tax_line_ids), 1)
        self.assertEquals(invoice.tax_line_ids.amount, 15.03)
        self.assertEquals(invoice.tax_line_ids.amount_rounding, 0.27)
        self.assertEquals(invoice.tax_line_ids.amount_total, 15.30)

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.90
        invoice_form.cash_rounding_id = cash_rounding_down
        invoice = invoice_form.save()

        self.assertEquals(len(invoice.invoice_line_ids), 1)
        self.assertEquals(invoice.invoice_line_ids.price_total, 116.04)
        self.assertEquals(len(invoice.tax_line_ids), 1)
        self.assertEquals(invoice.tax_line_ids.amount, 15.14)
        self.assertEquals(invoice.tax_line_ids.amount_rounding, -0.04)
        self.assertEquals(invoice.tax_line_ids.amount_total, 15.10)

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.50
        invoice_form.cash_rounding_id = cash_rounding_halfup
        invoice = invoice_form.save()

        self.assertEquals(len(invoice.invoice_line_ids), 1)
        self.assertEquals(invoice.invoice_line_ids.price_total, 115.58)
        self.assertEquals(len(invoice.tax_line_ids), 1)
        self.assertEquals(invoice.tax_line_ids.amount, 15.08)
        self.assertEquals(invoice.tax_line_ids.amount_rounding, 0.42)
        self.assertEquals(invoice.tax_line_ids.amount_total, 15.50)

    def test_state(self):
        (self.sale_journal_parent + self.purchase_journal_parent).write({'update_posted': True})

        # test out_invoice

        invoice_form = self._create_invoice('out_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.0
        invoice = invoice_form.save()

        self.assertEquals(invoice.state, 'draft')
        self.assertFalse(invoice.number)

        # draft -> open
        invoice.action_invoice_open()

        self.assertEquals(invoice.state, 'open')
        self.assertEquals(invoice.number, 'INV/%s/0001' % fields.Date.today().year)

        # open -> paid
        self.bank_journal_parent.post_at_bank_rec = False
        with Form(self.env['account.payment']) as payment_form:
            payment_form.journal_id = self.bank_journal_parent
            payment_form.payment_type = 'inbound'
            payment_form.partner_type = 'customer'
            payment_form.partner_id = self.partner_a
            payment_form.amount = 115.0
        payment = payment_form.save()
        payment.post()
        payment_line = payment.move_line_ids.filtered(lambda line: line.account_id == invoice.account_id)

        self.assertTrue(invoice.outstanding_credits_debits_widget)
        self.assertTrue(payment_line.move_id.name in invoice.outstanding_credits_debits_widget)

        invoice.assign_outstanding_credit(payment_line.id)

        self.assertEquals(invoice.state, 'paid')

        # paid -> cancel
        invoice.action_invoice_cancel()

        self.assertEquals(invoice.state, 'cancel')
        self.assertFalse(invoice.number)

        # cancel -> draft
        invoice.action_invoice_draft()

        self.assertEquals(invoice.state, 'draft')
        self.assertFalse(invoice.number)

        # draft -> open
        invoice.action_invoice_open()

        self.assertEquals(invoice.state, 'open')
        self.assertEquals(invoice.number, 'INV/%s/0001' % fields.Date.today().year)

        # open -> in_payment
        self.bank_journal_parent.post_at_bank_rec = True
        with Form(self.env['account.payment']) as payment_form:
            payment_form.journal_id = self.bank_journal_parent
            payment_form.payment_type = 'inbound'
            payment_form.partner_type = 'customer'
            payment_form.partner_id = self.partner_a
            payment_form.amount = 115.0
        payment = payment_form.save()
        payment.post()
        payment_line = payment.move_line_ids.filtered(lambda line: line.account_id == invoice.account_id)

        self.assertTrue(invoice.outstanding_credits_debits_widget)
        self.assertTrue(payment_line.move_id.name in invoice.outstanding_credits_debits_widget)

        invoice.assign_outstanding_credit(payment_line.id)

        self.assertEquals(invoice.state, 'in_payment')

        # test in_invoice

        invoice_form = self._create_invoice('in_invoice')
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = 100.0
        invoice = invoice_form.save()

        self.assertEquals(invoice.state, 'draft')
        self.assertFalse(invoice.number)

        # draft -> open
        invoice.action_invoice_open()

        self.assertEquals(invoice.state, 'open')
        self.assertEquals(invoice.number, 'BILL/%s/0001' % fields.Date.today().year)

        # open -> paid
        self.bank_journal_parent.post_at_bank_rec = False
        with Form(self.env['account.payment']) as payment_form:
            payment_form.journal_id = self.bank_journal_parent
            payment_form.payment_type = 'outbound'
            payment_form.partner_type = 'supplier'
            payment_form.partner_id = self.partner_a
            payment_form.amount = 115.0
        payment = payment_form.save()
        payment.post()
        payment_line = payment.move_line_ids.filtered(lambda line: line.account_id == invoice.account_id)

        self.assertTrue(invoice.outstanding_credits_debits_widget)
        self.assertTrue(payment_line.move_id.name in invoice.outstanding_credits_debits_widget)

        invoice.assign_outstanding_credit(payment_line.id)

        self.assertEquals(invoice.state, 'paid')

        # paid -> cancel
        invoice.action_invoice_cancel()

        self.assertEquals(invoice.state, 'cancel')
        self.assertFalse(invoice.number)

        # cancel -> draft
        invoice.action_invoice_draft()

        self.assertEquals(invoice.state, 'draft')
        self.assertFalse(invoice.number)

        # draft -> open
        invoice.action_invoice_open()

        self.assertEquals(invoice.state, 'open')
        self.assertEquals(invoice.number, 'BILL/%s/0001' % fields.Date.today().year)

        # open -> in_payment
        self.bank_journal_parent.post_at_bank_rec = True
        with Form(self.env['account.payment']) as payment_form:
            payment_form.journal_id = self.bank_journal_parent
            payment_form.payment_type = 'outbound'
            payment_form.partner_type = 'supplier'
            payment_form.partner_id = self.partner_a
            payment_form.amount = 115.0
        payment = payment_form.save()
        payment.post()
        payment_line = payment.move_line_ids.filtered(lambda line: line.account_id == invoice.account_id)

        self.assertTrue(invoice.outstanding_credits_debits_widget)
        self.assertTrue(payment_line.move_id.name in invoice.outstanding_credits_debits_widget)

        invoice.assign_outstanding_credit(payment_line.id)

        self.assertEquals(invoice.state, 'in_payment')
