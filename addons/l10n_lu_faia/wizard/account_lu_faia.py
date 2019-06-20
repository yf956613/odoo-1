# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import api, fields, models, release
from odoo.tools.xml_utils import _check_with_xsd
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
        self._cr.execute("""SELECT account_move_line.account_id as account_id, SUM(account_move_line.balance)
                    FROM account_move_line
                    JOIN account_account a ON a.id = account_move_line.account_id
                    """ + where_clause + """
                    GROUP BY account_move_line.account_id
                    """, where_params)
        debit_credit = {'account_id': False, 'opening_credit': 0.0, 'opening_debit': 0.0}
        for aid, val in self._cr.fetchall():
            debit_credit['account_id'] = aid
            if val < 0:
                debit_credit['opening_credit'] = abs(val)
                debit_credit['opening_debit'] = 0.0
            else:
                debit_credit['opening_debit'] = val
                debit_credit['opening_credit'] = 0.0
        return debit_credit

    def _prepare_faia_entries(self, date_from, date_to):

        def _prepare_debit_credit_balance(partner):
            return {
                'debit': partner.debit - partner.credit if partner.debit - partner.credit >= 0 else 0,
                'credit': abs(partner.debit - partner.credit) if partner.debit - partner.credit < 0 else 0,
            }

        def _prepare_partner_contact_detail(partners):
            datas = []
            for partner in partners:
                datas.append({
                    'title': partner.title.name or '',
                    'name': partner.name,
                    'mobile': partner.mobile,
                    'phone': partner.phone,
                    'email': partner.email,
                    'website': partner.website
                })
            return datas

        def _prepare_partner_address_detail(partners):
            datas = []
            for partner in partners:
                datas.append({
                    'street': partner.street,
                    'street2': partner.street2,
                    'city': partner.city,
                    'zip': partner.zip,
                    'state_code': partner.state_id.code,
                    'country': partner.country_id.code
                })
            return datas

        def _prepare_partner_detail(partner):
            child_partners = partner.child_ids
            partner_address = {
                'street': partner.street,
                'street2': partner.street2,
                'city': partner.city,
                'zip': partner.zip,
                'state_code': partner.state_id.code,
                'country': partner.country_id.code,
            }
            other_addresses = _prepare_partner_address_detail(child_partners.filtered(lambda x: x.type != 'contact'))
            contacts = _prepare_partner_contact_detail(child_partners.filtered(lambda x: x.type == 'contact'))
            print("OTHER, contac", other_addresses, contacts)
            if not other_addresses and not contacts:
                other_addresses = [partner_address]
            partner_address['other_address'] = other_addresses
            partner_address['contact_address'] = contacts
            print("PPPPP", partner_address)
            return partner_address

        def _prepare_bank_details(partner):
            datas = []
            for bank in partner.bank_ids:
                datas.append({
                    'bank_name': bank.bank_name,
                    'acc_number': bank.acc_number,
                    'bank_bic': bank.bank_bic
                })
            return datas

        def _prepare_tax_information(line):
            datas = []
            for tax in line.tax_ids:
                datas.append({
                    'name': tax.name,
                    'tax_type': tax.description[:9],
                    'tax_code': tax.id,
                    'tax_percentage': '%.2f' % (tax.amount if tax.amount_type == 'percent' else 0.0),
                    'amount': '%.2f' % tax.amount if tax.amount_type == 'fix' else 0.0,
                    'currency_code': tax.company_id.currency_id.name if tax.company_id.currency_id else '',
                    'currency_amount': '%.2f' % tax.company_id.currency_id.rate if tax.company_id.currency_id else 0
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
                    'amount': '%.2f' % line.debit or 0 if line.debit else '%.2f' % line.credit or 0,
                    'currency_code': line.company_currency_id and line.company_currency_id.name,
                    'currency_amount': '%.2f' % line.amount_currency or 0
                }
                if line.credit:
                    datas[-1]['credit_amount'] = amount_vals
                else:
                    datas[-1]['debit_amount'] = amount_vals
            return datas

        def _prepare_transaction_entries(move_lines, journal_id):
            datas = []
            for move in move_lines.mapped('move_id').filtered(lambda x:x.journal_id == journal_id):
                data = {
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
                }
                datas.append(data)
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
                rate = line.currency_id._get_rates(line.company_id, line.invoice_id.date_invoice)
                print("\n\n\nRRRR", rate, line.company_id.currency_id.id, line.currency_id.id)
                datas.append({
                    'line_number': line.id,
                    'account_id': line.account_id.id,
                    'order_ref': line.origin,
                    'ship_delivery_date': line.invoice_id.date_due,
                    'ship_to_address': line.partner_id and _prepare_partner_address_detail(line.partner_id)[0] or {},
                    'ship_from_address': line.company_id and _prepare_partner_address_detail(line.company_id)[0] or {},
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
                    'amount': '%.2f' % line.price_subtotal_signed or 0,
                    'currency_code': line.currency_id.name if line.currency_id != line.company_id.currency_id else '',
                    'currency_amount': '%.2f' % (line.currency_id.rate if line.currency_id != line.company_id.currency_id else 0.0),
                    'exchange_rate': rate[line.currency_id.id] if line.currency_id != line.company_id.currency_id else 0.0,
                    'indicator': 'C' if line.invoice_id.type in ['in_refund', 'out_invoice'] else 'D',
                })
            return datas

        def _prepare_invoice_tax_detail(invoice_id):
            datas = []
            for tax_line in invoice_id.tax_line_ids.filtered(lambda x:x.tax_id.type_tax_use != 'none'):
                rate = invoice_id.currency_id._get_rates(tax_line.company_id, invoice_id.date_invoice)
                print("RRRR INVOICE TAX>>>>", rate, tax_line.company_id.currency_id.id, invoice_id.currency_id.id)
                datas.append({
                    'name': tax_line.tax_id.name,
                    'tax_type': tax_line.tax_id.description[:9],
                    'tax_code': tax_line.tax_id.id,
                    'tax_percentage': '%.2f' % tax_line.tax_id.amount or 0,
                    'amount': '%.2f' % tax_line.amount or 0.0,
                    'currency_code': tax_line.company_id.currency_id and tax_line.company_id.currency_id.name,
                    'currency_amount': '%.2f' % tax_line.company_id.currency_id.rate if tax_line.company_id.currency_id else 0.0,
                    'exchange_rate': rate[invoice_id.currency_id.id] if invoice_id.currency_id != tax_line.company_id.currency_id else 0.0,
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

        owner_address = {'address': _prepare_partner_detail(self.env.user.company_id.partner_id)}

        company = self.env.user.company_id
        company_data = {
            'company_registry': company.company_registry,
            'name': company.name,
            'tax_registration': company.vat,
            'bank_accounts': _prepare_bank_details(company.partner_id),
            'address': owner_address['address']
        }

        for account in move_lines.mapped('account_id'):
            accounts.append({
                'id': account.id,
                'name': account.name,
                'code': account.code,
                'group_code': account.group_id.id or "",
                'group_categ': account.group_id and account.group_id.name or "",
                'acccount_type': account.user_type_id.name[:18],
                'account_balance_date_from': self.with_context(date_from=fiscalyear_starting_date, date_to=date_from, account_ids=account)._compute_opening_debit_credit(),
                'account_balance_date_to': self.with_context(date_from=date_from, date_to=date_to, account_ids=account)._compute_opening_debit_credit()
            })
        partners = move_lines.mapped('partner_id')
        for partner in partners:
            partner_details = {
                'id': partner.id,
                'name': partner.name,
                'address': _prepare_partner_detail(partner),
                'tax_registration': partner.vat,
                'bank_accounts': _prepare_bank_details(partner),
                'partner_balance_date_from':  _prepare_debit_credit_balance(partner.with_context(date_to=date_from)),
                'partner_balance_date_to':  _prepare_debit_credit_balance(partner.with_context(date_to=date_to)),
            }
            if partner.customer:
                customers.append(partner_details)
            if partner.supplier:
                suppliers.append(partner_details)

            print("\n\n\n PARTNERS:::::", partner_details)
        for tax in move_lines.mapped('tax_ids'):
            taxes.append({
                'tax_type': tax.description[:9],
                'tax_code': tax.id,
                'description': tax.name,
                'country': tax.company_id.country_id.code,
                'state_code': tax.company_id.state_id.code
            })
            if tax.amount_type == 'percent':
                taxes[-1]['percent_amount'] = '%.2f' % tax.amount or 0
            if tax.amount_type == 'fix':
                taxes[-1]['fix_amount'] = '%.2f' % tax.amount or 0
                taxes[-1]['currency_code'] = tax.company_id.currency_id.name
                taxes[-1]['currency_amount'] = '%.2f' % tax.company_id.currency_id.rate or 0,

        for uom in move_lines.mapped('product_uom_id') | move_lines.mapped('product_id.uom_id'):
            uom_entries.append({
                'measure': uom.name,
                'description': uom.uom_type
            })

        for product in move_lines.mapped('product_id'):
            products.append({
                'product_code': product.default_code,
                'group': product.categ_id.name,
                'description': product.name,
                'product_number_code': product.barcode,
                'valuation': product.valuation[:9] if 'valuation' in product else "",
                'uom_base': product.uom_id.name,
                'uom_standard': product.uom_id.name,
                'convert_fact': product.uom_id.factor_inv,
                'taxes': []
            })
            for tax_id in product.taxes_id:
                products[-1]['taxes'].append({
                    'type': tax_id.description[:9],
                    'code': tax_id.id
                })

        general_ledger['total_debit'] = '%.2f' % sum(move_lines.mapped('debit'))
        general_ledger['total_credit'] = '%.2f' % sum(move_lines.mapped('credit'))
        general_ledger['journals'] = []
        for journal in move_lines.mapped('journal_id'):
            general_ledger['journals'].append({
                'journal_id': journal.id,
                'description': journal.name,
                'type': journal.type,
                'transactions': _prepare_transaction_entries(move_lines, journal)
            })

        invoices = move_lines.mapped('invoice_id')
        sales_invoices['total_debit'] = '%.2f' % (sum(invoices.filtered(lambda x:x.type == 'out_invoice').mapped('amount_total')) - sum(invoices.filtered(lambda x:x.type == 'out_refund').mapped('amount_total')) or 0)
        sales_invoices['total_credit'] = '%.2f' % (sum(invoices.filtered(lambda x:x.type == 'in_invoice').mapped('amount_total')) - sum(invoices.filtered(lambda x:x.type == 'in_refund').mapped('amount_total')) or 0)
        sales_invoices['invoices'] = []
        for invoice in invoices:
            d = {
                'invoice_no': invoice.number,
                'customer_info': invoice.partner_id and _prepare_partner_address_detail(invoice.partner_id)[0] if invoice.type in ['out_refund', 'out_invoice'] else {} or {},
                'supplier_info': invoice.partner_id and _prepare_partner_address_detail(invoice.partner_id)[0] if invoice.type in ['in_refund', 'in_invoice'] else {} or {},
                'partner_id': invoice.partner_id.id,
                'partner_shipping_id': (invoice.partner_shipping_id.id if 'partner_shipping_id' in invoice else '') or invoice.partner_id.id,
                'account_id': invoice.account_id.id,
                'period': invoice.date_invoice.year,
                'period_year': invoice.date_invoice.year,
                'invoice_date': invoice.date_invoice,
                'invoice_type': invoice.type[:9],
                'ship_to_delivery_date': invoice.date_due if 'partner_shipping_id' in invoice else '',
                'ship_to_address': invoice.partner_shipping_id and _prepare_partner_address_detail(invoice.partner_shipping_id)[0] if 'partner_shipping_id' in invoice else {} or {},
                'ship_from_delivery_date': invoice.date_due,
                'ship_from_address': invoice.company_id.partner_id and _prepare_partner_address_detail(invoice.company_id.partner_id)[0] if invoice.company_id.partner_id else {} or {},
                'payment_term_id': invoice.payment_term_id.name,
                'source_id': invoice.origin,
                'gl_posting_date': invoice.move_id.date,
                'transaction_id': invoice.move_id.id,
                'receipt_number': invoice.payment_ids and invoice.payment_ids[0].name or '',
                'lines': _prepare_invoice_line(invoice.invoice_line_ids),
                'tax_information': _prepare_invoice_tax_detail(invoice),
                'net_total': '%.2f' % invoice.amount_total or 0,
                'gross_total': '%.2f' % invoice.amount_total or 0
            }
            print("\n\n\nDDDD", d['customer_info'], d['partner_id'])
            sales_invoices['invoices'].append(d)

        return company_data, owner_address, customers, suppliers, taxes, uom_entries, products, general_ledger, accounts, fiscalyear_starting_date, sales_invoices

    @api.multi
    def generate_faia_report(self):
        import xml.dom.minidom
        self.ensure_one()
        company_data, owner_address, customers, suppliers, taxes, uom_entries, products, general_ledger, accounts, fiscalyear_starting_date, sales_invoices = self._prepare_faia_entries(self.date_from, self.date_to)

        values = {
            'AuditFileDateCreated': fields.Date.today(),
            'company_data': company_data,
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
        data = self.env['ir.qweb'].render('l10n_lu_faia.FAIATemplate', values)
        data_str = data.decode('utf-8')
        def prettyPrint(x):
            s = ''
            for line in x.toprettyxml().split('\n'):
                if not line.strip() == '':
                    line+='\n'
                    s+=line
            return s
        dom = xml.dom.minidom.parseString(data_str)
        pretty_xml_as_string = dom.toprettyxml()
        
        s1 = prettyPrint(dom)
        print("SSSSS", s1)
        data = s1.encode('utf-8')

        root = etree.fromstring(s1)
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
