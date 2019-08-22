# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import models, fields, api, tools, _
import base64

class MergePickingLabel(models.TransientModel):

    _name = "openerp.delivery.merge_picking_label"
    _description = "Merge Shipping Labels"

    all_labels = fields.Binary('Merged PDF', readonly=True)
    all_labels_fname = fields.Char()
    nb_labels = fields.Char()

    @api.model
    def default_get(self, fields):
        res = super(MergePickingLabel, self).default_get(fields)
        if 'all_labels' in fields and self.env.context.get('active_model') == 'stock.picking':
            pickings = self.env['stock.picking'].browse(self.env.context.get('active_ids', []))
            pdf_data = []
            nb_labels = 0
            for picking in pickings:
                pdf = self.env['ir.attachment'].search(
                    [('res_id', '=', picking.id), ('res_model', '=', 'stock.picking'),
                     ('name', '=ilike', 'Label-bpost-%')], limit=1)
                if pdf:
                    pdf_data.append(base64.decodestring(pdf.datas))
                    nb_labels += 1
            result = tools.pdf.merge_pdf(pdf_data)
            res['all_labels'] = base64.encodestring(result)
            res['all_labels_fname'] = 'merged.pdf'
            res['nb_labels'] = _("Number of labels merged: %s") % nb_labels
        return res

    @api.model
    def create(self, vals):
        res = super(MergePickingLabel, self).create(vals)
        if self.env.context.get('active_model') == 'stock.picking':
            pickings = self.env['stock.picking'].browse(self.env.context.get('active_ids', []))
            if pickings:
                pickings.write({'note': 'PRINTED by %s, on %s' %
                                   (self.env.user.name, fields.Datetime.now())})
        return res
