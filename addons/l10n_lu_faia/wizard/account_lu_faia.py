# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from dateutil.relativedelta import relativedelta
from lxml import etree
import xml.dom.minidom

from odoo import api, fields, models, release, _
from odoo.exceptions import UserError
from odoo.tools.xml_utils import _check_with_xsd
from odoo.modules.module import get_module_resource


class AccountLuFaia(models.TransientModel):
    _name = 'account.lu.faia'
    _description = 'Ficher Echange Informatise'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    faia_data = fields.Binary('FAIA File', readonly=True)
    filename = fields.Char(string='Filename', size=256, readonly=True)

    def _prepare_address_structure(self, addresses):
        address_list = []
        wrong_addresses = []
        for address in addresses:
            address_list.append({
                'street': address.street,
                'street2': address.street2,
                'city': address.city,
                'zip': address.zip,
                'state_code': address.state_id.code,
                'country': address.country_id.code
            })
            if not (address.city or address.zip):
                wrong_addresses.append(address.display_name)
        if wrong_addresses:
            raise UserError(_('Please define City/Zip for `%s`.' % (', '.join(wrong_addresses))))
        return address_list

    def _prepare_contact_information_structure(self, contacts):
        contact_list = []
        for contact in contacts:
            contact_list.append({
                'title': contact.title.name,
                'name': contact.name,
                'mobile': contact.phone or contact.mobile,
                'email': contact.email,
                'website': contact.website
            })
        return contact_list

    def _prepare_bank_account_structure(self, banks):
        bank_account_list = []
        for bank in banks:
            bank_account_list.append({
                'bank_name': bank.bank_name,
                'acc_number': bank.acc_number,
                'bank_bic': bank.bank_bic
            })
        return bank_account_list

    def _prepare_company_structure(self, company):
        if not company.company_registry:
            raise UserError(_('Define `Company Registry` for %s company.' % (company.name,)))
        company_contacts = company.partner_id.child_ids.filtered(lambda partner: partner.type == 'contact')
        if not company_contacts:
            raise UserError(_('Define atleast one `Contact` for %s company.' % (company.name,)))
        addresses = company.partner_id.child_ids.filtered(lambda partner: partner.type != 'contact')
        company_addresses = self._prepare_address_structure(addresses or company.partner_id)

        return {
            'id': company.id,
            'company_registry': company.company_registry,
            'name': company.name,
            'addresses': company_addresses,
            'contacts': self._prepare_contact_information_structure(company_contacts),
            'vat': company.vat,
            'bank_accounts': self._prepare_bank_account_structure(company.bank_ids),
        }

    def _prepare_supplier_customer_structure(self, partners):

        def _prepare_opening_closing_balance(partner):
            return {
                'debit': '%.2f' % (partner.debit - partner.credit if partner.debit - partner.credit >= 0 else 0),
                'credit': '%.2f' % (abs(partner.debit - partner.credit) if partner.debit - partner.credit < 0 else 0),
            }

        supplier_list = []
        customer_list = []

        company_structure = self._prepare_company_structure(self.env.user.company_id)

        for partner in partners:
            contacts = partner.child_ids.filtered(lambda p: p.type == 'contact')
            addresses = partner.child_ids.filtered(lambda p: p.type != 'contact')
                # partner has no contacts/addresses, address details set in partner is used as address
            partner_address = self._prepare_address_structure(addresses or partner)
            print("\n\npartner_address::::", partner.name, partner_address)
            print("contacts:::::::::::", contacts)
            partner_data = {
                'name': partner.name,
                'addresses': partner_address,
                'contacts': self._prepare_contact_information_structure(contacts),
                'vat': partner.vat,
                'bank_accounts': self._prepare_bank_account_structure(partner.bank_ids),
                # TODO: TO check if date_to gives correct results !
                'opening_balance': _prepare_opening_closing_balance(partner.with_context(date_to=self.date_from)),
                'closing_balance': _prepare_opening_closing_balance(partner.with_context(date_to=self.date_to)),
            }
            if partner.supplier:
                partner_data['supplier_id'] = partner.id
                supplier_list.append(partner_data)
            if partner.customer:
                partner_data['customer_id'] = partner.id
                customer_list.append(partner_data)

        return (supplier_list, customer_list)

    def _prepare_account_structure(self, accounts):

        def _compute_opening_debit_credit():
            tables, where_clause, where_params = self.env['account.move.line']._query_get()
            if where_clause:
                where_clause = 'AND ' + where_clause
            self._cr.execute("""SELECT account_move_line.account_id as account_id, SUM(account_move_line.balance)
                        FROM account_move_line
                        JOIN account_account a ON a.id = account_move_line.account_id
                        """ + where_clause + """
                        GROUP BY account_move_line.account_id
                        """, where_params)
            debit_credit = {}

            for account_id, balance in self._cr.fetchall():
                if not debit_credit.get(account_id):
                    debit_credit[account_id] = {}
                #debit_credit[account_id] = account_id
                if balance < 0:
                    debit_credit[account_id]['credit'] = '%.2f' % abs(balance)
                    debit_credit[account_id]['debit'] = 0.0
                else:
                    debit_credit[account_id]['debit'] = '%.2f' % balance
                    debit_credit[account_id]['credit'] = 0.0

            return debit_credit

        account_list = []
        account_balance = _compute_opening_debit_credit()

        for account in accounts:
            balance_data = account_balance.get(account.id)
            account_list.append({
                'id': account.id,
                'name': account.name,
                'code': account.code,
                'group_code': account.group_id.id or "",
                'group_categ': account.group_id and account.group_id.name or "",
                'acccount_type': account.user_type_id.name[:18],
                'opening_balance': balance_data,
                'closing_balance': balance_data
            })

        return account_list

    def _prepare_product_structure(self, products):
        product_list = []

        for product in products:
            product_data = {
                'product_code': product.default_code,
                'group': product.categ_id.name,
                'description': product.name,
                'product_number_code': product.barcode,
                'cost_method': product.cost_method if 'cost_method' in product else "",
                'uom_base': product.uom_id.name,
                'uom_standard': product.uom_id.name,
                'convert_fact': product.uom_id.factor_inv,
                'taxes': []
            }
            for tax in product.taxes_id:
                product_data['taxes'] = self._prepare_tax_structure(product.taxes_id)
            product_list.append(product_data)

        return product_list

    def _get_amount_currency(self, amount, amount_currency, company, document_currency, transaction_date):
        company_currency = company.currency_id
        amount_data = {
            'amount': '%.2f' % amount,
        }
        if company_currency and document_currency and company_currency != document_currency:
            exchange_rate = document_currency._get_rates(company_currency, transaction_date)[document_currency.id]
            amount_data.update({
                'currency_code': document_currency.name,
                'amount_currency': '%.2f' % amount_currency,
                'exchange_rate': '%.8f' % exchange_rate
            })
        return amount_data

    def _prepare_tax_structure(self, taxes, amount=0, amount_currency=False, company=False, currency=False, date=False):
        """
        pass amount_currency, company, currency and date along with amount when amount needs to be converted into another currency
        """
        tax_list = []

        for tax in taxes:
            print("TAXXX IN TAX STR", tax, tax.name, tax.amount)
            tax_data = {
                'name': tax.name,
                'type': 'TVA-%s' % (tax.id), # TODO: verify if it is correct(we can't have duplicate type here)
                'code': tax.id,
                'amount_type': tax.amount_type, # TODO: What happens when it is group of taxes or tax included in price
                'amount_percentage': '%.2f' % tax.amount,
                'country': tax.company_id.country_id.code,
                'state_code': tax.company_id.state_id.code,
            }
            if amount:
                tax_data['amount_data'] = self._get_amount_currency(
                    amount, amount_currency, company, currency, date
                )
            tax_list.append(tax_data)

        return tax_list

    def _prepare_uom_structure(self, uoms):
        uom_list = []

        for uom in uoms:
            uom_list.append({
                'measure': uom.name,
                'description': uom.uom_type
            })

        return uom_list

    def _prepare_move_lines(self, move_lines):
        lines = {}
        for line in move_lines:
            amount_data = {'debit_amount_data': {}, 'credit_amount_data': {}}
            data = {
                'amount': '%.2f' % (line.debit or line.credit) or 0.0,
            }
            if line.currency_id:
                data.update({
                    'currency_code': line.currency_id.name,
                    'amount_currency': '%.2f' % line.amount_currency
                })
            if line.debit:
                amount_data['debit_amount_data'] = data
            else:
                amount_data['credit_amount_data'] = data

            if not lines.get(line.move_id.id):
                lines[line.move_id.id] = []

            lines[line.move_id.id].append({
                'record_id': line.id,
                'account_id': line.account_id.id,
                'date': line.date,
                'move_id': line.move_id.id,
                'customer_id': line.partner_id.id if line.move_id.journal_id.type == 'sale' else '',
                'supplier_id': line.partner_id.id if line.move_id.journal_id.type == 'purchase' else '',
                'description': line.name,
                'amount_data': amount_data,
                'tax_information': self._prepare_tax_structure(line.tax_line_id, line.debit or line.credit,
                                                                   line.amount_currency, line.company_id,
                                                                   line.currency_id, line.date_maturity)
            })
        return lines

    def _prepare_transaction_entries(self, move_lines):
        move_data = {}
        move_lines_data = self._prepare_move_lines(move_lines)
        for move in move_lines.mapped('move_id'):
            data = {
                'transaction_id': move.id,
                'period': move.date.year,
                'period_year': move.date.year,
                'transaction_date': move.date,
                'source': move.ref,
                'transaction_type': move.journal_id.type,
                'description': move.name,
                'system_entry_date': move.create_date.date(),
                'glposting_date': move.date,
                'customer_id': move.partner_id.id if move.journal_id.type == 'sale' else '',
                'supplier_id': move.partner_id.id if move.journal_id.type == 'purchase' else '',
                'lines': move_lines_data.get(move.id) or []
            }
            if not move_data.get(move.journal_id.id):
                move_data[move.journal_id.id] = [data]
            else:
                move_data[move.journal_id.id].append(data)
        return move_data

    def _prepare_general_ledger_structure(self, move_lines):
        general_ledger_data = {}
        general_ledger_data['total_debit'] = '%.2f' % sum(move_lines.mapped('debit'))
        general_ledger_data['total_credit'] = '%.2f' % sum(move_lines.mapped('credit'))
        general_ledger_data['journals'] = []

        move_data = self._prepare_transaction_entries(move_lines) # moves by journal

        for journal in move_lines.mapped('journal_id'):
            general_ledger_data['journals'].append({
                'journal_id': journal.id,
                'description': journal.name,
                'type': journal.type,
                'moves': move_data.get(journal.id) or []
           })

        return general_ledger_data

    def _prepare_header(self):
        company = self.env.user.company_id
        return {
            'country': company.country_id.code,
            'region': company.state_id.code,
            'date_created': fields.Date.today(),
            'software_version': release.version,
            'company_structure': self._prepare_company_structure(company),
            'company_currency': company.currency_id.name,
            'date_from': self.date_from,
            'date_to': self.date_to
        }

    def _prepare_credit_note_detail(self, invoice_id):
        datas = []
        for credit_note in invoice_id.refund_invoice_ids:
            datas.append({
                'reference': credit_note.number,
                'reason': credit_note.name,
            })
        return datas

    def _prepare_invoice_line(self, invoice_line_ids):
        datas = []
        for line in invoice_line_ids:
            amount_data = self._get_amount_currency(line.price_subtotal_signed, line.price_subtotal, line.company_id, line.currency_id, line.invoice_id.date_invoice)
            datas.append({
                'line_number': line.id,
                'account_id': line.account_id.id,
                'order_ref': line.origin,
                'order_date': line.invoice_id.date_invoice,
                'product_code': line.product_id.default_code,
                'product_desc': line.product_id.name,
                'quantity': line.quantity,
                'uom_id': line.uom_id.name,
                'convert_fact': line.uom_id.factor_inv,
                'unit_price': '%.2f' % line.price_unit,
                'to_point_date': line.invoice_id.date,
                'credit_note': self._prepare_credit_note_detail(line.invoice_id),
                'description': line.name,
                'amount_data': amount_data,
                'indicator': 'C' if line.invoice_id.type in ['in_refund', 'out_invoice'] else 'D',
                # 'tax_information': 
            })
        return datas

    def _convert_amount(self, amount, from_currency, to_currency, company, date):
        tax_amount_unsigned = amount
        if from_currency and company and from_currency != to_currency:
            tax_amount_unsigned = from_currency._convert(amount, to_currency, company, date)
        return tax_amount_unsigned

    def _prepare_invoice_tax_detail(self, tax_line_ids, date_invoice):
        datas = []
        for tax_line in tax_line_ids.filtered(lambda x: x.tax_id.type_tax_use != 'none'):
            # currently we do not store tax amount in company currency, hence converting amount from invoice currency into company currency
            tax_amount_unsigned = self._convert_amount(tax_line.amount, tax_line.currency_id, tax_line.company_id.currency_id, tax_line.company_id, date_invoice or fields.Date.today())
            [tax_data] = self._prepare_tax_structure(tax_line.tax_id, tax_amount_unsigned, tax_line.amount,
                tax_line.company_id, tax_line.currency_id, date_invoice)
            datas.append(dict(tax_data))
        return datas

    def _prepare_invoice_structure(self, invoices):
        sales_invoices = {}
        total_debit = sum(invoices.filtered(lambda inv: inv.type == 'out_invoice').mapped('amount_total')) - \
                        sum(invoices.filtered(lambda inv: inv.type == 'out_refund').mapped('amount_total'))
        total_credit = sum(invoices.filtered(lambda inv: inv.type == 'in_invoice').mapped('amount_total')) - \
                        sum(invoices.filtered(lambda inv: inv.type == 'in_refund').mapped('amount_total'))
        sales_invoices['total_debit'] = '%.2f' % total_debit
        sales_invoices['total_credit'] = '%.2f' % total_credit
        sales_invoices['invoices'] = []
        for invoice in invoices:
            customer_info = supplier_info = {}
            [address] = self._prepare_address_structure(invoice.partner_id)
            if invoice.type in ['out_refund', 'out_invoice']:
                customer_info = address
            elif invoice.type in ['in_refund', 'in_invoice']:
                supplier_info = address
            sales_invoices['invoices'].append({
                'invoice_no': invoice.number,
                'customer_info': customer_info,
                'supplier_info': supplier_info,
                'partner_id': invoice.partner_id.id,
                'partner_shipping_id': (invoice.partner_shipping_id.id if 'partner_shipping_id' in invoice else '') or invoice.partner_id.id,
                'account_id': invoice.account_id.id,
                'period': invoice.date_invoice.year,
                'period_year': invoice.date_invoice.year,
                'invoice_date': invoice.date_invoice,
                'invoice_type': invoice.type[:9],
                'payment_term_id': invoice.payment_term_id.name,
                'source': invoice.origin,
                'gl_posting_date': invoice.move_id.date,
                'transaction_id': invoice.move_id.id,
                'lines': self._prepare_invoice_line(invoice.invoice_line_ids),
                'tax_information': self._prepare_invoice_tax_detail(invoice.tax_line_ids, invoice.date_invoice),
                'net_total': '%.2f' % invoice.amount_total_signed,
                'gross_total': '%.2f' % invoice.amount_total_signed
            })
        return sales_invoices

    def generate_faia_report(self):

        def prettyPrint(x):
            # Helper function to properly indent the XML content
            s = ''
            for line in x.toprettyxml().split('\n'):
                if not line.strip() == '':
                    line+='\n'
                    s+=line
            return s

        move_lines = self.env['account.move.line'].search([
            ('date', '>=', self.date_from), ('date', '<=', self.date_to)
        ])
        general_ledger_data = self._prepare_general_ledger_structure(move_lines)

        partners = move_lines.mapped('partner_id')
        supplier_list, customer_list = self._prepare_supplier_customer_structure(partners)

        accounts = move_lines.mapped('account_id')
        account_list = self._prepare_account_structure(accounts)

        products = move_lines.mapped('product_id')
        product_list = self._prepare_product_structure(products)

        # Tax table need to have all the taxes that are used in move lines/invoice lines/product's default taxes
        taxes = move_lines.mapped('tax_ids') | products.mapped('taxes_id')
        tax_list = self._prepare_tax_structure(taxes)

        uoms = move_lines.mapped('product_uom_id') | move_lines.mapped('product_id.uom_id')
        uom_list = self._prepare_uom_structure(uoms)

        invoices = move_lines.mapped('invoice_id')
        invoice_list = self._prepare_invoice_structure(invoices)

        values = {
            'header_structure': self._prepare_header(),
            'company_data': self._prepare_company_structure(self.env.user.company_id), # same will be used for <owners> tag
            'customers': customer_list,
            'suppliers': supplier_list,
            'accounts': account_list,
            'products': product_list,
            'taxes': tax_list,
            'uom_entries': uom_list,
            'general_ledger': general_ledger_data,
            'sales_invoices': invoice_list
        }

        data = self.env['ir.qweb'].render('l10n_lu_faia.FAIATemplate', values)
        dom = xml.dom.minidom.parseString(data.decode('utf-8'))
        s1 = prettyPrint(dom)
        data = s1.encode('utf-8')
        path = get_module_resource('l10n_lu_faia', 'schemas', 'FAIA_v_2_01_reduced_version_A.xsd')
        # print(">>>>\n", s1)
        # _check_with_xsd(data, open(path, "r"))
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
        _check_with_xsd(data, open(path, "r"))
        return action


