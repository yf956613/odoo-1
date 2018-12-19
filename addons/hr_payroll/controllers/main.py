# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from PyPDF2 import  PdfFileReader, PdfFileWriter

from odoo.http import request, route, Controller
from odoo.tools.safe_eval import safe_eval


class HrPayroll(Controller):

    @route(["/hr/payroll/print_report"], type='http', auth='user')
    def get_payroll_report(self, list_ids, **post):
        if not request.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            return request.not_found()

        ids = [int(s) for s in list_ids.split(',')]
        payslips = request.env['hr.payslip'].search([('id', 'in', ids)])

        if not payslips:
            return request.not_found()

        pdf_writer = PdfFileWriter()

        for payslip in payslips:
            if not payslip.struct_id or not payslip.struct_id.report_id:
                continue
            pdf_content, _ = payslip.struct_id.report_id.render_qweb_pdf(payslip.id)
            reader = PdfFileReader(io.BytesIO(pdf_content), strict=False, overwriteWarnings=False)
            if payslip.struct_id.report_id.print_report_name:
                report_name = safe_eval(payslip.struct_id.report_id.print_report_name, {'object': payslip})

            for page in range(reader.getNumPages()):
                pdf_writer.addPage(reader.getPage(page))

        _buffer = io.BytesIO()
        pdf_writer.write(_buffer)
        merged_pdf = _buffer.getvalue()
        _buffer.close()

        if len(payslips) > 1:
            report_name = "Payslip"

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(merged_pdf)),
            ('Content-Disposition', 'attachment; filename=' + report_name + '.pdf;')
        ]

        return request.make_response(merged_pdf, headers=pdfhttpheaders)
