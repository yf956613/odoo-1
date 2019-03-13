
import time

env = env(user=env.ref('base.user_root'))

# remove all ir.rules
# env['ir.rule'].sudo().search([]).unlink()

line_ids = [
    (0, 0, {'account_id': 17, 'name': 'X0', 'price_unit': 750, 'product_id': 10, 'quantity': 1, 'uom_id': 1}),
    (0, 0, {'account_id': 17, 'name': 'X1', 'price_unit': 12.5, 'product_id': 22, 'quantity': 1, 'uom_id': 1}),
    (0, 0, {'account_id': 17, 'name': 'X2', 'price_unit': 885, 'product_id': 27, 'quantity': 1, 'uom_id': 1}),
    (0, 0, {'account_id': 17, 'name': 'X3', 'price_unit': 85, 'product_id': 23, 'quantity': 1, 'uom_id': 1}),
    (0, 0, {'account_id': 17, 'name': 'X4', 'price_unit': 2950, 'product_id': 28, 'quantity': 1, 'uom_id': 1}),
    (0, 0, {'account_id': 17, 'name': 'X5', 'price_unit': 40000, 'product_id': 31, 'quantity': 1, 'uom_id': 1}),
    (0, 0, {'account_id': 17, 'name': 'X6', 'price_unit': 70, 'product_id': 5, 'quantity': 1, 'uom_id': 1}),
    (0, 0, {'account_id': 17, 'name': 'X7', 'price_unit': 2100, 'product_id': 26, 'quantity': 1, 'uom_id': 1}),
    (0, 0, {'account_id': 17, 'name': 'X8', 'price_unit': 1950, 'product_id': 25, 'quantity': 1, 'uom_id': 1}),
    (0, 0, {'account_id': 17, 'name': 'X9', 'price_unit': 280, 'product_id': 7, 'quantity': 1, 'uom_id': 1}),
]

invoice = env['account.invoice'].create({
    'account_id': 7,
    'journal_id': 1,
    'partner_id': 14,
    'payment_term_id': 6,
    'invoice_line_ids': line_ids,
})
invoice.recompute()
invoice.action_invoice_open()
invoice.recompute()

for N in [10, 100, 1000]:
    invoice = env['account.invoice'].create({
        'account_id': 7,
        'journal_id': 1,
        'partner_id': 14,
        'payment_term_id': 6,
        'invoice_line_ids': line_ids * (N // 10),
    })
    invoice.recompute()
    invoice.invalidate_cache()
    t0 = time.time()
    q0 = env.cr.sql_log_count
    invoice.action_invoice_open()
    invoice.recompute()
    t1 = time.time()
    q1 = env.cr.sql_log_count
    print("validate invoice of %d lines: %d queries, %.3fs" % (N, q1 - q0, t1 - t0))
