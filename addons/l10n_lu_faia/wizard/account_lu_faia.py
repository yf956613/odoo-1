# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
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

    def _prepare_header(self):
        company = self.env.company

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

    def _prepare_address_structure(self, addresses):
        address_list = []
        bad_addresses = []
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
                bad_addresses.append(address.display_name)
        if bad_addresses:
            raise UserError(_('Please define City/Zip for `%s`.' % (', '.join(bad_addresses))))

        return address_list

    def _prepare_contact_information_structure(self, contacts):
        contact_list = []
        for contact in contacts:
            if not (contact.phone or contact.mobile):
                raise UserError(_('Please define Phone number for `%s`, a contact of `%s`.' % (contact.name, contact.parent_id.name)))
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

        company_structure = self._prepare_company_structure(self.env.company)

        for partner in partners:
            contacts = partner.child_ids.filtered(lambda p: p.type == 'contact')
            addresses = partner.child_ids.filtered(lambda p: p.type != 'contact')
            # in case partner hasn't got contacts/addresses, address details set in partner is used as address
            partner_address = self._prepare_address_structure(addresses or partner)

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

    def _get_amount_currency(self, amount, line):
        amount_data = {
            'amount': '%.2f' % abs(amount),
        }
        if line and line.currency_id and line.company_id.currency_id != line.currency_id:
            exchange_rate = line.currency_id._get_rates(line.company_id.currency_id, line.date)[line.currency_id.id]
            amount_data.update({
                'currency_code': line.currency_id.name,
                'exchange_rate': '%.8f' % exchange_rate
            })
            if self._context.get('invoice_tax_line'):
                amount_data['amount_currency'] = '%.2f' % (abs(line.price_total) - abs(line.price_subtotal))
            else:
                amount_data['amount_currency'] = '%.2f' % abs(line.amount_currency)

        return amount_data

    def _prepare_tax_structure(self, taxes, amount=False, line=False):
        tax_list = []

        for tax in taxes:
            tax_list.append({
                'name': tax.name,
                'type': 'TVA-%s' % (tax.id), # TODO: verify if it is correct(we can't have duplicate type here)
                'code': tax.id,
                'amount_type': tax.amount_type, # TODO: What happens when it is group of taxes or tax included in price
                'amount_percentage': '%.2f' % tax.amount,
                'country': tax.company_id.country_id.code,
                'state_code': tax.company_id.state_id.code,
                'amount_data': self._get_amount_currency(amount, line)
            })

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
            data = self._get_amount_currency(line.debit or line.credit, line)
            if line.debit:
                amount_data['debit_amount_data'] = data
            else:
                amount_data['credit_amount_data'] = data

            if not lines.get(line.move_id.id):
                lines[line.move_id.id] = []

            tax_information = self._prepare_tax_structure(line.tax_line_id) or {}
            if tax_information:
                tax_information[0]['amount_data'] = data

            lines[line.move_id.id].append({
                'record_id': line.id,
                'account_id': line.account_id.id,
                'date': line.date,
                'move_id': line.move_id.id,
                'customer_id': line.partner_id.id if line.move_id.journal_id.type == 'sale' else '',
                'supplier_id': line.partner_id.id if line.move_id.journal_id.type == 'purchase' else '',
                'description': line.name,
                'amount_data': amount_data,
                'tax_information': tax_information
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

    def _prepare_credit_note_detail(self, invoice_id):
        datas = []
        for credit_note in invoice_id.reversed_entry_id:
            datas.append({
                'reference': credit_note.ref,
                'reason': credit_note.invoice_payment_ref,
            })

        return datas

    def _prepare_invoice_line(self, invoice_line_ids):
        datas = []

        for line in invoice_line_ids:
            # invoice line amount excluding tax in company currency
            amount_data = self._get_amount_currency(line.debit or line.credit, line)
            # tax amount in company currency
            tax_information = []
            if line.tax_ids:
                tax_amount_company_currency = line.currency_id._convert(line.price_total - line.price_subtotal, line.company_id.currency_id, line.company_id, line.date)
                tax_information = self.with_context(invoice_tax_line=True)._prepare_tax_structure(
                    line.tax_ids, tax_amount_company_currency, line)

            # unit price in company currency
            if line.currency_id:
                unit_price_company_currency = line.currency_id._convert(line.price_unit, line.company_id.currency_id, line.company_id, line.date)
            else:
                unit_price_company_currency = line.price_unit

            datas.append({
                'line_number': line.id,
                'account_id': line.account_id.id,
                'order_ref': line.name,
                'order_date': line.move_id.invoice_date,
                'product_code': line.product_id.default_code,
                'product_desc': line.product_id.name,
                'quantity': line.quantity,
                'uom_id': line.product_uom_id.name,
                'convert_fact': line.product_uom_id.factor_inv,
                'unit_price': '%.2f' % unit_price_company_currency,
                'to_point_date': line.move_id.invoice_date,
                'credit_note': self._prepare_credit_note_detail(line.move_id),
                'description': line.name,
                'amount_data': amount_data,
                'indicator': 'C' if line.move_id.type in ['in_refund', 'out_invoice'] else 'D',
                'tax_information': tax_information
            })

        return datas

    def _prepare_invoice_tax_detail(self, invoice_tax_lines, date_invoice):
        datas = []
        for invoice_tax_line in invoice_tax_lines:
            [tax_data] = self._prepare_tax_structure(invoice_tax_line.tax_line_id)
            amount_data = self._get_amount_currency(invoice_tax_line.debit or invoice_tax_line.credit, invoice_tax_line)
            tax_data['amount_data'] = amount_data
            x = self._prepare_tax_structure(invoice_tax_line.tax_line_id, invoice_tax_line.debit or invoice_tax_line.credit, invoice_tax_line)
            datas.append(tax_data)

        return datas

    def _prepare_invoice_structure(self, invoices):
        sales_invoices = {}

        total_debit = sum(invoices.filtered(lambda inv: inv.type == 'out_invoice').mapped('amount_total_signed')) - \
                        sum(invoices.filtered(lambda inv: inv.type == 'out_refund').mapped('amount_total_signed'))
        total_credit = sum(invoices.filtered(lambda inv: inv.type == 'in_invoice').mapped('amount_total_signed')) - \
                        sum(invoices.filtered(lambda inv: inv.type == 'in_refund').mapped('amount_total_signed'))

        sales_invoices['total_debit'] = '%.2f' % abs(total_debit)
        sales_invoices['total_credit'] = '%.2f' % abs(total_credit)
        sales_invoices['invoices'] = []

        for invoice in invoices:
            customer_info = supplier_info = {}
            [address] = self._prepare_address_structure(invoice.partner_id)

            if invoice.type in ['out_refund', 'out_invoice']:
                customer_info = address
            elif invoice.type in ['in_refund', 'in_invoice']:
                supplier_info = address

            if invoice.currency_id != invoice.company_id.currency_id:
                net_total = invoice.currency_id._convert(invoice.amount_untaxed, invoice.company_id.currency_id, invoice.company_id, invoice.date)
                gross_total = invoice.currency_id._convert(invoice.amount_total, invoice.company_id.currency_id, invoice.company_id, invoice.date)
            else:
                net_total = invoice.amount_untaxed
                gross_total = invoice.amount_total

            sales_invoices['invoices'].append({
                'invoice_no': invoice.name,
                'customer_info': customer_info,
                'supplier_info': supplier_info,
                'partner_id': invoice.partner_id.id,
                'partner_shipping_id': (invoice.partner_shipping_id.id if 'partner_shipping_id' in invoice else '') or invoice.partner_id.id,
                'period': invoice.invoice_date.year,
                'period_year': invoice.invoice_date.year,
                'invoice_date': invoice.invoice_date,
                'invoice_type': invoice.type[:9],
                'payment_term_id': invoice.invoice_payment_term_id.name,
                'source': invoice.invoice_origin,
                'gl_posting_date': invoice.invoice_date,
                'transaction_id': invoice.id,
                'lines': self._prepare_invoice_line(invoice.invoice_line_ids),
                'tax_information': self._prepare_invoice_tax_detail(invoice.line_ids.filtered('tax_line_id'), invoice.invoice_date),
                'net_total': '%.2f' % abs(net_total),
                'gross_total': '%.2f' % abs(gross_total)
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

        if self.env.company.country_id.code != 'LU':
            raise UserError(_("FAIA reports are meant to be generated for Luxembourg companies only! Please make sure your company's country is set to `Luxembourg`."))

        header_structure = self._prepare_header()

        move_lines = self.env['account.move.line'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', self.env.company.id)
        ])
        general_ledger_data = self._prepare_general_ledger_structure(move_lines)

        partners = move_lines.mapped('partner_id')
        supplier_list, customer_list = self._prepare_supplier_customer_structure(partners)

        accounts = move_lines.mapped('account_id')
        account_list = self._prepare_account_structure(accounts)

        products = move_lines.mapped('product_id')
        product_list = self._prepare_product_structure(products)

        # Tax table need to show all the taxes that are used in move lines/invoice lines/product's default taxes
        taxes = move_lines.mapped('tax_ids') | products.mapped('taxes_id') | products.mapped('supplier_taxes_id')
        tax_list = self._prepare_tax_structure(taxes)

        uoms = move_lines.mapped('product_uom_id') | move_lines.mapped('product_id.uom_id') | move_lines.mapped('product_id.uom_po_id')
        uom_list = self._prepare_uom_structure(uoms)

        invoices = move_lines.filtered(lambda mv: not mv.exclude_from_invoice_tab).mapped('move_id')
        invoice_list = self._prepare_invoice_structure(invoices)

        values = {
            'header_structure': header_structure,
            'company_data': header_structure['company_structure'], # same will be used to fill <owners> tag
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
        _check_with_xsd(data, open(path, "r"))
        self.write({
            'faia_data': base64.encodestring(data),
            'filename': 'FAIA Report_%s.xml' % (self.date_to)
        })
        action = {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=account.lu.faia&id=" + str(self.id) + "&filename_field=filename&field=faia_data&download=true&filename=" + self.filename,
            'target': 'self'
        }

        return action


