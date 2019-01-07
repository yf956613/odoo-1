# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from odoo import api, fields, models, release
from odoo.tools.xml_utils import _check_with_xsd
from dateutil.relativedelta import relativedelta
from odoo.modules.module import get_module_resource


class AccountLuFaia(models.TransientModel):
    _name = 'account.lu.faia'
    _description = 'Ficher Echange Informatise'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    faia_data = fields.Binary('FAIA File', readonly=True)
    filename = fields.Char(string='Filename', size=256, readonly=True)

    def _compute_opening_debit_credit(self):
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        if where_clause:
            where_clause = 'AND ' + where_clause
        self._cr.execute("""SELECT account_move_line.account_id, SUM(account_move_line.balance)
                    FROM account_move_line
                    JOIN account_account a ON a.id = account_move_line.account_id
                    """ + where_clause + """
                    GROUP BY account_move_line.account_id
                    """, where_params)
        debit_credit = {}
        for aid, val in self._cr.fetchall():
            if val < 0:
                debit_credit['opening_credit'] = abs(val)
                debit_credit['opening_debit'] = 0.0
            else:
                debit_credit['opening_debit'] = val
                debit_credit['opening_credit'] = 0.0
        return debit_credit

    def _prepare_faia_entries(self, date_from, date_to):

        def _prepare_debit_credit_balance(customer):
            return {
                'debit': customer.debit - customer.credit if customer.debit - customer.credit >= 0 else 0,
                'credit': abs(customer.debit - customer.credit) if customer.debit - customer.credit < 0 else 0,
            }

        def _prepare_customer_contact_detail(customers):
            datas = []
            for customer in customers:
                datas.append({
                    'title': customer.title or '',
                    'name': customer.name,
                    'phone': customer.phone,
                    'email': customer.email,
                    'website': customer.website
                })
            return datas

        def _prepare_customer_address_detail(customers):
            datas = []
            for customer in customers:
                datas.append({
                    'cust_street': customer.street,
                    'cust_add_address': customer.street2,
                    'city': customer.city,
                    'postal_code': customer.zip,
                    'region': customer.state_id.code,
                    'country': customer.country_id.code
                })
            return datas

        def _prepare_customer_detail(customer):
            child_partners = customer.child_ids
            return {
                'cust_street': customer.street,
                'cust_add_address': customer.street2,
                'city': customer.city,
                'postal_code': customer.zip,
                'region': customer.state_id.code,
                'country': customer.country_id.code,
                'other_address': _prepare_customer_address_detail(child_partners.filtered(lambda x: x.type != 'contact')),
                'contact_address': _prepare_customer_contact_detail(child_partners.filtered(lambda x: x.type == 'contact'))
            }

        def _prepare_bank_details(customer):
            datas = []
            for bank in customer.bank_ids:
                datas.append({
                    'name': bank.bank_name,
                    'number': bank.acc_number,
                    'code': bank.bank_bic
                })
            return datas

        def _prepare_tax_information(line):
            datas = []
            for tax in line.tax_ids:
                datas.append({
                    'name': tax.name,
                    'tax_type': tax.description[:9],
                    'tax_code': tax.id,
                    'tax_percentage': tax.amount if tax.amount_type == 'percent' else 0.0,
                    'amount': '%.2f' % tax.amount if tax.amount_type == 'fix' else 0.0,
                    'currency_code': tax.company_id.currency_id.name if tax.company_id.currency_id else '',
                    'currency_amount': '%.2f' % tax.company_id.currency_id.rate if tax.company_id.currency_id else ''
                })
            return datas

        def _prepare_move_lines(move):
            datas = []
            for line in move.line_ids:
                datas.append({
                    'record_id': line.id,
                    'account_id': line.account_id.id,
                    'valuedate': line.date,
                    'sourcedocument_id': line.move_id.id,
                    'customer_id': line.partner_id.id if move.journal_id.type == 'sale' else '',
                    'supplier_id': line.partner_id.id if move.journal_id.type == 'purchase' else '',
                    'description': line.name,
                    'debit_amount': {},
                    'credit_amount': {},
                    'tax_information': _prepare_tax_information(line)
                })
                amount_vals = {
                    'amount': '%.2f' % line.debit if line.debit else '%.2f' % line.credit,
                    'currency_code': line.company_currency_id and line.company_currency_id.name,
                    'currency_amount': '%.2f' % line.amount_currency
                }
                if line.credit:
                    datas[-1]['credit_amount'] = amount_vals
                else:
                    datas[-1]['debit_amount'] = amount_vals
            return datas

        def _prepare_transaction_entries(move_lines, journal_id):
            datas = []
            for move in move_lines.mapped('move_id').filtered(lambda x:x.journal_id == journal_id):
                datas.append({
                    'transaction_id': move.id,
                    'period': move.date.year,
                    'period_year': move.date.year,
                    'transaction_date': move.date,
                    'source_id': move.journal_id.id,
                    'transaction_type': move.journal_id.type,
                    'description': move.name,
                    'system_entry_date': move.create_date.date(),
                    'glposting_date': move.date,
                    'customer_id': move.partner_id.id if move.journal_id.type == 'sale' else '',
                    'supplier_id': move.partner_id.id if move.journal_id.type == 'purchase' else '',
                    'lines': _prepare_move_lines(move)
                })
            return datas

        def _prepare_credit_note_detail(invoice_id):
            datas = []
            for credit_note in invoice_id.refund_invoice_ids:
                datas.append({
                    'reference': credit_note.number,
                    'reason': credit_note.name,
                })
            return datas

        def _prepare_invoice_line(invoice_line_ids):
            datas = []
            for line in invoice_line_ids:
                datas.append({
                    'line_number': line.id,
                    'account_id': line.account_id.id,
                    'order_ref': line.origin,
                    'ship_delivery_date': line.invoice_id.date_due,
                    'ship_to_address': _prepare_customer_address_detail(line.partner_id)[0],
                    'ship_from_address': _prepare_customer_address_detail(line.company_id)[0],
                    'product_code': line.product_id.default_code,
                    'product_desc': line.product_id.name,
                    'delivery_date': line.invoice_id.date_due,
                    'quantity': line.quantity,
                    'uom_id': line.uom_id.name,
                    'convert_fact': line.uom_id.factor_inv,
                    'unit_price': line.price_unit,
                    'to_point_date': line.invoice_id.date,
                    'credit_note': _prepare_credit_note_detail(line.invoice_id),
                    'description': line.name,
                    'amount': line.price_subtotal_signed,
                    'currency_code': line.currency_id.name if line.currency_id != line.company_id.currency_id else '',
                    'currency_amount': line.currency_id.amount if line.currency_id != line.company_id.currency_id else '',
                    'exchange_rate': (line.currency_id._get_rates(line.company_id, line.invoice_id.date_invoice))[0] if line.currency_id != line.company_id.currency_id else '',
                    'indicator': 'C' if line.invoice_id.type in ['in_refund', 'out_invoice'] else 'D',
                })
            return datas

        def _prepare_invoice_tax_detail(invoice_id):
            datas = []
            for tax in invoice_id.tax_line_ids.filtered(lambda x:x.tax_id.type_tax_use != 'none'):
                datas.append({
                    'tax_type': tax.tax_id.description[:9],
                    'tax_code': tax.tax_id.id,
                    'tax_percentage': tax.tax_id.amount,
                    'tax_description': tax.tax_id.name,
                    'tax_amount': tax.amount,
                    'currency_code': tax.company_id.currency_id and tax.company_id.currency_id.name,
                    'currency_amount': '%.2f'%tax.company_id.currency_id.rate if tax.company_id.currency_id else 0.0,
                    'exchange_rate': (invoice_id.currency_id._get_rates(tax.company_id, invoice_id.date_invoice))[0] if invoice_id.currency_id != tax.company_id.currency_id else 0.0,
                })
            return datas

        accounts = []
        customers = []
        suppliers = []
        taxes = []
        uom_entries = []
        products = []
        general_ledger = {}
        sales_invoices = {}
        fiscalyear_starting_date = self.env.user.company_id.compute_fiscalyear_dates(date_from)['date_from'] - relativedelta(days=1)
        move_lines = self.env['account.move.line'].search([('date', '>=', date_from), ('date', '<=', date_to)])

        owner_address = {'address': _prepare_customer_detail(self.env.user.company_id.partner_id)}

        for account_id in move_lines.mapped('account_id'):
            accounts.append({
                'id': account_id.id,
                'name': account_id.name,
                'code': account_id.code,
                'group_code': account_id.group_id.id or "",
                'group_categ': account_id.group_id and account_id.group_id.name or "",
                'acccount_type': account_id.user_type_id.name[:18],
                'account_balance_date_from': self.with_context(date_from=fiscalyear_starting_date, date_to=date_from, account_ids=account_id)._compute_opening_debit_credit(),
                'account_balance_date_to': self.with_context(date_from=date_from, date_to=date_to, account_ids=account_id)._compute_opening_debit_credit()
            })

        for partner in move_lines.mapped('partner_id'):
            partner_details = {
                'id': partner.id,
                'name': partner.name,
                'address': _prepare_customer_detail(partner),
                'tax_registration': partner.vat,
                'bank_accounts': _prepare_bank_details(partner),
                'partner_balance_date_from':  _prepare_debit_credit_balance(partner.with_context(date_to=date_from)),
                'partner_balance_date_to':  _prepare_debit_credit_balance(partner.with_context(date_to=date_to))
            }
            if partner.filtered('customer'):
                customers.append(partner_details)
            elif partner.filtered('supplier'):
                suppliers.append(partner_details)

        for tax_id in move_lines.mapped('tax_ids'):
            taxes.append({
                'tax_type': tax_id.description[:9],
                'tax_code': tax_id.id,
                'description': tax_id.name,
                'country': tax_id.company_id.country_id.code,
                'region': tax_id.company_id.state_id.code
            })
            if tax_id.amount_type == 'percent':
                taxes[-1]['percent_amount'] = '%.2f' % tax_id.amount
            if tax_id.amount_type == 'fix':
                taxes[-1]['fix_amount'] = '%.2f' % tax_id.amount
                taxes[-1]['currency_code'] = tax_id.company_id.currency_id.name
                taxes[-1]['currency_amount'] = '%.2f' % tax_id.company_id.currency_id.rate,

        for uom_id in move_lines.mapped('product_uom_id') | move_lines.mapped('product_id.uom_id'):
            uom_entries.append({
                'measure': uom_id.name,
                'description': uom_id.uom_type
            })

        for product_id in move_lines.mapped('product_id'):
            products.append({
                'product_code': product_id.default_code,
                'group': product_id.categ_id.name,
                'description': product_id.name,
                'product_number_code': product_id.barcode,
                'valuation': product_id.valuation[:9] if 'valuation' in product_id else "",
                'uom_base': product_id.uom_id.name,
                'uom_standard': product_id.uom_id.name,
                'convert_fact': product_id.uom_id.factor_inv,
                'taxes': []
            })
            for tax_id in product_id.taxes_id:
                products[-1]['taxes'].append({
                    'type': tax_id.description[:9],
                    'code': tax_id.code
                })

        journal_ids = move_lines.mapped('journal_id')
        general_ledger['total_debit'] = sum(move_lines.mapped('debit'))
        general_ledger['total_credit'] = sum(move_lines.mapped('credit'))
        general_ledger['journals'] = []
        for journal_id in journal_ids:
            general_ledger['journals'].append({
                'journal_id': journal_id.id,
                'description': journal_id.name,
                'type': journal_id.type,
                'transactions': _prepare_transaction_entries(move_lines, journal_id)
            })

        invocie_ids = move_lines.mapped('invoice_id')
        sales_invoices['total_debit'] = sum(invocie_ids.filtered(lambda x:x.type == 'out_invoice').mapped('amount_total')) - sum(invocie_ids.filtered(lambda x:x.type == 'out_refund').mapped('amount_total'))
        sales_invoices['total_credit'] = sum(invocie_ids.filtered(lambda x:x.type == 'in_invoice').mapped('amount_total')) - sum(invocie_ids.filtered(lambda x:x.type == 'in_refund').mapped('amount_total'))
        sales_invoices['invoices'] = []
        for invoice_id in invocie_ids:
            sales_invoices['invoices'].append({
                'invoice_no': invoice_id.number,
                'customer_info': _prepare_customer_address_detail(invoice_id.partner_id)[0] if invoice_id.type in ['out_refund', 'out_invoice'] else {},
                'supplier_info': _prepare_customer_address_detail(invoice_id.partner_id)[0] if invoice_id.type in ['in_refund', 'in_invoice'] else {},
                'partner_id': invoice_id.partner_id.id,
                'partner_shipping_id': invoice_id.partner_shipping_id.id if 'partner_shipping_id' in invoice_id else '',
                'account_id': invoice_id.account_id.id,
                'period': invoice_id.date_invoice.year,
                'period_year': invoice_id.date_invoice.year,
                'invoice_date': invoice_id.date_invoice,
                'invoice_type': invoice_id.type[:9],
                'ship_to_delivery_date': invoice_id.date_due if 'partner_shipping_id' in invoice_id else '',
                'ship_to_address': _prepare_customer_address_detail(invoice_id.partner_shipping_id)[0] if 'partner_shipping_id' in invoice_id else {},
                'ship_from_delivery_date': invoice_id.date_due,
                'ship_from_address': _prepare_customer_address_detail(invoice_id.company_id.partner_id)[0] if invoice_id.company_id.partner_id else {},
                'payment_term_id': invoice_id.payment_term_id.name,
                'source_id': invoice_id.origin,
                'gl_posting_date': invoice_id.move_id.date,
                'transaction_id': invoice_id.move_id.id,
                'receipt_number': invoice_id.payment_ids and invoice_id.payment_ids[0].name,
                'lines': _prepare_invoice_line(invoice_id.invoice_line_ids),
                'tax_information': _prepare_invoice_tax_detail(invoice_id),
                'net_total': invoice_id.amount_total,
                'gross_total': invoice_id.amount_total
            })

        return owner_address, customers, suppliers, taxes, uom_entries, products, general_ledger, accounts, fiscalyear_starting_date, sales_invoices

    @api.multi
    def generate_faia_report(self):
        self.ensure_one()
        owner_address, customers, suppliers, taxes, uom_entries, products, general_ledger, accounts, fiscalyear_starting_date, sales_invoices = self._prepare_faia_entries(self.date_from, self.date_to)

        values = {
            'AuditFileDateCreated': fields.Date.today(),
            'SoftwareVersion': release.version,
            'date_from': self.date_from - relativedelta(days=1),
            'date_to': self.date_to,
            'fiscalyear_starting_date': fiscalyear_starting_date,
            'owner_address': owner_address,
            'accounts': accounts,
            'customers': customers,
            'suppliers': suppliers,
            'taxes': taxes,
            'uom_entries': uom_entries,
            'products': products,
            'general_ledger': general_ledger,
            'sales_invoices': sales_invoices
        }
        data = self.env['ir.qweb'].render('l10n_lu_faia.faia_xml_data', values)
        path = get_module_resource('l10n_lu_faia', 'schemas', 'FAIA_v_2_01_reduced_version_A.xsd')
        _check_with_xsd(data, open(path, "r"))
        self.write({
            'faia_data': base64.encodestring(data),
            'filename': 'FAIA Report_%s.xml' % (self.date_to)
        })
        # This action is return FAIA xml file.
        action = {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=account.lu.faia&id=" + str(self.id) + "&filename_field=filename&field=faia_data&download=true&filename=" + self.filename,
            'target': 'self'
        }
        return action
