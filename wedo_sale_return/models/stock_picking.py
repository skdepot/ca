# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tests import Form


class StockPicking(models.Model):
    _inherit = 'stock.move'

    sale_return_line_id = fields.Many2one('sale.return.line')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_sale_return = fields.Boolean(string="Sale Return")
    sale_return_id = fields.Many2one('sale.return')

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.sale_return_id and self.move_ids_without_package and self.state == 'done':
            invoice = self.sudo().sale_return_id.invoice_ids.filtered(lambda r: r.picking_id.id == self.id)
            if not invoice:
                self.sudo().create_sale_customer_bill()
        return res

    def create_sale_customer_bill(self):
        for picking_id in self:
            current_user = self.env.uid
            if picking_id.picking_type_id.code == 'incoming':
                sale_journal_id = picking_id.sale_return_id.return_journal_id.id
                invoice_line_list = []
                lines = picking_id.move_ids_without_package.sudo().filtered(lambda r: r.quantity_done > 0)
                for move in lines:
                    if move.quantity_done > 0:
                        vals = (0, 0, {
                            'name': move.sale_return_line_id.product_id.name,
                            'product_id': move.sale_return_line_id.product_id.id,
                            'price_unit': move.sale_return_line_id.price_unit,
                            'tax_ids': [(6, 0, move.sale_return_line_id.tax_id.ids)],
                            'quantity': move.quantity_done,
                            'sale_return_line_id': move.sale_return_line_id.id,
                        })
                        invoice_line_list.append(vals)
                if invoice_line_list:
                    invoice = picking_id.env['account.move'].sudo().create({
                        'move_type': 'out_refund',
                        'invoice_origin': picking_id.name,
                        'invoice_user_id': current_user,
                        'partner_id': picking_id.partner_id.id,
                        'currency_id': picking_id.env.company.currency_id.id,
                        'journal_id': int(sale_journal_id),
                        'ref': "sale Return %s" % picking_id.name,
                        # 'picking_id': picking_id.id,
                        'sale_return_id': picking_id.sale_return_id.id,
                        'invoice_line_ids': invoice_line_list
                    })

                    return invoice
