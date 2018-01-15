#-*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.tools.xml_utils import create_xml_node, create_xml_node_chain
from lxml import etree


class AccountFrFec(models.TransientModel):
    _name = 'account.lu_faia'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    @api.multi
    def generate_fec(self):
        self.ensure_one()
        self.generate_xml(self.company_id, self.date_from)
        header = [
            u'TaxAccountingBasis',    # 0
            ]

    def generate_xml(self, company_id, date_from):
        """ Generates a SDD XML file containing the payments corresponding to this recordset,
        associating them to the given company, with the specified
        collection date.
        """
        document = etree.Element("Document", nsmap={None: 'urn:schemas-OECD:schema-extensions:documentation', 'xsi': "http://www.w3.org/2001/XMLSchema"})
        CstmrDrctDbtInitn = etree.SubElement(document, 'Header')
        self._sdd_xml_gen_header(company_id, CstmrDrctDbtInitn)

    def _sdd_xml_gen_header(self, company_id, CstmrDrctDbtInitn):
        """ Generates the header of the SDD XML file.
        """
        TaxAccountingBasis = create_xml_node(CstmrDrctDbtInitn, 'TaxAccountingBasis')
        TaxEntity = create_xml_node(CstmrDrctDbtInitn, 'TaxEntity')
