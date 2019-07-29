import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSBasicConfig(TestPoSCommon):
    """ Test PoS with basic configuration
    """

    def setUp(self):
        super(TestPoSBasicConfig, self).setUp()
        self.config = self.basic_config
        self.product1 = self.create_product('Product 1', self.categ_basic, 10.0, 5)
        self.product2 = self.create_product('Product 2', self.categ_basic, 20.0, 10)
        self.product3 = self.create_product('Product 3', self.categ_basic, 30.0, 15)
        self.adjust_inventory([self.product1, self.product2, self.product3], [100, 50, 50])

    def test_orders_no_invoiced(self):
        """ Test for orders without invoice

        1. 3 orders
        2. first 2 orders with cash payment
        3. last order with bank payment
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 10), (self.product2, 5)]))
        orders.append(self.create_ui_order_data([(self.product2, 7), (self.product3, 1)]))
        orders.append(self.create_ui_order_data(
            [(self.product1, 1), (self.product3, 5), (self.product2, 3)],
            payments=[(self.bank_pm, 220)]
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.session.order_count)
        orders_total = sum(order.amount_total for order in self.session.order_ids)
        self.assertAlmostEqual(orders_total, self.session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # close the session
        self.session.action_pos_session_validate()

        # check values after the session is closed
        account_move = self.session.move_id

        sales_line = account_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sales_line.balance, -orders_total, msg='Sales line balance should be equal to total orders amount.')

        receivable_line_bank = account_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 220.0, msg='Bank receivable should be equal to the total bank payments.')

        receivable_line_cash = account_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 370.0, msg='Cash receivable should be equal to the total cash payments.')

        self.assertTrue(receivable_line_cash.full_reconcile_id, msg='Cash receivable line should be fully-reconciled.')

    def test_orders_with_invoiced(self):
        """ Test for orders: one with invoice

        1. 3 orders
        2. order 1, paid by cash
        3. order 2, paid by bank
        4. order 3, paid by bank, invoiced
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product3, 1), (self.product1, 6), (self.product2, 3)],
            payments=[(self.cash_pm, 150)],
        ))
        orders.append(self.create_ui_order_data(
            [(self.product2, 20), (self.product1, 1)],
            payments=[(self.bank_pm, 410)],
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 10), (self.product3, 1)],
            payments=[(self.bank_pm, 130)],
            customer=self.customer,
            is_invoiced=True,
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.session.order_count)
        orders_total = sum(order.amount_total for order in self.session.order_ids)
        self.assertAlmostEqual(orders_total, self.session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # check account move in the invoiced order
        invoiced_order = self.session.order_ids.filtered(lambda order: order.account_move)
        self.assertEqual(1, len(invoiced_order), 'Only one order is invoiced in this test.')
        invoice = invoiced_order.account_move
        self.assertAlmostEqual(invoice.amount_total, 130, msg='Amount total should be 130. Product is untaxed.')
        invoice_receivable_line = invoice.line_ids.filtered(lambda line: line.account_id == self.receivable_account)

        # close the session
        self.session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.session.move_id

        sales_line = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sales_line.balance, -(orders_total - invoice.amount_total), msg='Sales line should be total order minus invoiced order.')

        pos_receivable_line_bank = session_move.line_ids.filtered(
            lambda line: self.bank_pm.name in line.name and line.account_id == self.bank_pm.receivable_account_id
        )
        self.assertAlmostEqual(pos_receivable_line_bank.balance, 540.0, msg='Bank receivable should be equal to the total bank payments.')

        pos_receivable_line_cash = session_move.line_ids.filtered(
            lambda line: self.cash_pm.name in line.name and line.account_id == self.bank_pm.receivable_account_id
        )
        self.assertAlmostEqual(pos_receivable_line_cash.balance, 150.0, msg='Cash receivable should be equal to the total cash payments.')

        receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        self.assertAlmostEqual(receivable_line.balance, -invoice.amount_total)

        # cash receivable and invoice receivable lines should be fully reconciled
        self.assertTrue(pos_receivable_line_cash.full_reconcile_id)
        self.assertTrue(receivable_line.full_reconcile_id)

        # matching number of the receivable lines should be the same
        self.assertEqual(receivable_line.full_reconcile_id, invoice_receivable_line.full_reconcile_id)

    def test_return_order(self):
        """ Test return order

        1. 2 orders
        2. return 2nd order
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 1), (self.product2, 5)],
            payments=[(self.bank_pm, 110)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 2), (self.product3, 1)],
            payments=[(self.cash_pm, 100)],
            uid='12345-123-1234'
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(2, self.session.order_count)
        orders_total = sum(order.amount_total for order in self.session.order_ids)
        self.assertAlmostEqual(orders_total, self.session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # return order
        order_to_return = self.session.order_ids.filtered(lambda order: '12345-123-1234' in order.pos_reference)
        order_to_return.refund()
        refund_order = self.session.order_ids.filtered(lambda order: order.state == 'draft')

        # check if amount to pay
        self.assertAlmostEqual(refund_order.amount_to_pay, -100)

        # pay the refund
        context_make_payment = {"active_ids": [refund_order.id], "active_id": refund_order.id}
        make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
            'payment_method_id': self.cash_pm.id,
            'amount': -100,
        })
        make_payment.check()
        self.assertEqual(refund_order.state, 'paid', 'Payment is registered, order should be paid.')
        self.assertAlmostEqual(refund_order.amount_paid, -100.0, msg='Amount paid for return order should be negative.')

        # close the session
        self.session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.session.move_id

        sale_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(len(sale_lines), 2, 'There should be lines for both sales and refund.')
        self.assertAlmostEqual(sum(sale_lines.mapped('balance')), -110.0)

        receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 110.0)

        # net cash in the session is zero, thus, there should be no receivable cash line.
        receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertFalse(receivable_line_cash, 'There should be no receivable cash line.')

    def test_picking(self):
        self.open_new_session()

        start_qty_available = {
            self.product1: self.product1.qty_available,
            self.product2: self.product2.qty_available,
            self.product3: self.product3.qty_available,
        }

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 1), (self.product2, 5)],
            payments=[(self.bank_pm, 110)],
            uid='00001-001-0001'
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 2), (self.product3, 1)],
            payments=[(self.cash_pm, 100)],
            uid='00005-005-0005'
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check product qty_available after syncing the order
        self.assertEqual(
            self.product1.qty_available + 4,
            start_qty_available[self.product1],
            '4 items of product1 should have been delivered.'
        )
        self.assertEqual(
            self.product2.qty_available + 7,
            start_qty_available[self.product2],
            '7 items of product2 should have been delivered.'
        )
        self.assertEqual(
            self.product3.qty_available + 1,
            start_qty_available[self.product3],
            '1 items of product3 should have been delivered.'
        )

        # picking and stock moves should be in done state
        for order in self.session.order_ids:
            self.assertEqual(
                order.picking_id.state,
                'done',
                'Picking should be in done state.'
            )
            move_lines = order.picking_id.move_lines
            self.assertEqual(
                move_lines.mapped('state'),
                ['done'] * len(move_lines),
                'Move Lines should be in done state.'
            )
