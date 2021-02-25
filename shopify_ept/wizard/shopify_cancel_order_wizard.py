import json
from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError
from .. import shopify

class shopify_cancel_order_wizard(models.TransientModel):
    _name="shopify.cancel.order.wizard"
    _description = 'Shopify Cancel Order Wizard'
    
    @api.multi
    def get_amount(self):
        active_id=self._context.get('active_id')
        sale_order=self.env['sale.order'].browse(active_id)
        total=sale_order.amount_total
        return total
    message=fields.Selection([('customer','Customer changed/cancelled order'),
                              ('inventory','Fraudulent order'),
                              ('fraud','Items unavailable'),
                              ('other','Other'),
                              ],string="Message",default="inventory")
    amount=fields.Float("Amount",digits=(12,2))
    restock=fields.Boolean("Restock In Shopify ?",default=True)
    notify_by_email=fields.Boolean("Notify By Email ?",default=True)
    suggested_amount=fields.Float("Suggest Amount",digits=(12,2))   
    journal_id=fields.Many2one('account.journal', 'Journal', help='You can select here the journal to use for the credit note that will be created. If you leave that field empty, it will use the same journal as the current invoice.')
    inv_line_des=fields.Char("Invoice Line Description",default="Refund Line")
    auto_create_refund=fields.Boolean("Auto Create Refund",default=True)
    company_id=fields.Many2one("res.company")
    date_ept=fields.Date("Invoice Date")
    
    @api.model    
    def default_get(self,fields):
        context = self._context
        active_id=self._context.get('active_id')
        sale_order=self.env['sale.order'].browse(active_id)
        res = super(shopify_cancel_order_wizard, self).default_get(fields)
        res.update({'suggested_amount':self.get_amount(),'company_id':sale_order.company_id.id})
        return res
    
    """Cancel Order In Shopify using this api we can not cancel partial order"""
    @api.multi
    def cancel_in_shopify(self):    
        active_id=self._context.get('active_id')
        # picking_ids = self._context.get('picking_id')
        sale_order = self.env['sale.order'].browse(active_id)
        # picking_ids = self.env['stock.picking'].browse(picking_ids)
        instance=sale_order.shopify_instance_id
        
        instance.connect_in_shopify()
        try:
            order_id = shopify.Order()
        except Exception as e:
            raise Warning(e)
        order_id.id=sale_order.shopify_order_id
        order_id.reason=self.message
        order_id.restock=self.restock and 'true' or  'false'
        order_id.email=self.notify_by_email and 'true' or 'false'
        try:
            order_id.cancel()
        except Exception as error:
            if hasattr(error, "response"):
                if hasattr(error.response, "body") and error.response.code == 422:
                    msg = "Error while cancelling the order in shopify :\n%s" % (
                        json.loads(error.response.body.decode()).get("error"))
                else:
                    msg = "Error while cancelling the order in shopify : %s\n%s" % (
                    error.response.code, json.loads(error.response.body.decode()))
            else:
                msg = "Error while cancelling the order in shopify :\n%s" % str(error)
            raise UserError(msg)

        if self.auto_create_refund:
            self.create_refund(sale_order)
        # picking.write({'canceled_in_shopify':True})
        sale_order.write({'canceled_in_shopify':True})
        return True
    
    @api.multi
    def create_refund(self,order):
        source_invoices = order.invoice_ids.filtered(lambda m:m.type == 'out_invoice' and
                                                       m.state not in ['draft', 'cancel'])
        if not source_invoices:
            order._cr.commit()
            warning_message = "Order {} cancel in Shopify But unable to create a credit note in Odoo \n " \
                              "Since order may be uncreated or unpaid invoice.".format(order.name)
            raise Warning(warning_message)

        for source_invoice in source_invoices:
            refund_invoice_description = self.inv_line_des if self.inv_line_des else 'Refund Invoice of {}'.format(source_invoice.name)
            journal_id = self.journal_id and self.journal_id.id
            values = source_invoice._prepare_refund(source_invoice, date_invoice=source_invoice.date_invoice,
                                                       date=self.date_ept,
                                                       description=refund_invoice_description,
                                                       journal_id=journal_id)
            values.update({'source_invoice_id': source_invoice.id})
            source_invoice.create(values)
        # account_invoice_line_obj=self.env['account.invoice.line']
        # for line in order.order_line:
        #     for invoice_line in line.invoice_lines:
        #         source_invoices += invoice_line.invoice_id
        #         break
        # invoice_vals = {
        #     'name': order.name or '',
        #     'origin': order.name,
        #     'type': 'out_refund',
        #     'reference': order.client_order_ref or order.name,
        #     'account_id': order.partner_id.property_account_receivable_id.id,
        #     'partner_id': order.partner_invoice_id.id,
        #     'journal_id': journal_id,
        #     'currency_id': order.pricelist_id.currency_id.id,
        #     'comment': order.note,
        #     'instance_id':order.shopify_instance_id.id,
        #     'payment_term_id': order.payment_term_id and order.payment_term_id.id or False,
        #     'fiscal_position_id': order.fiscal_position_id and order.fiscal_position_id.id or False,
        #     'company_id': self.company_id.id,
        #     'user_id': self._uid or False,
        #     'date_invoice':self.date_ept or False,
        #     'team_id' : order.team_id and order.team_id.id,
        #     'source_invoice_id': source_invoice_id and source_invoice_id.id or False,
        #     'picking_id':picking.id
        # }
        # invoice=self.env['account.invoice'].create(invoice_vals)
        # tax_ids=[]
        # product=False
        # qty=0.0
        # for line in picking_ids.mapped('move_lines'):
        #     if not product:
        #         product=line.product_id
        #     tax_ids+=line.sale_line_id.tax_id.ids
        #     qty+=line.product_qty
        # tax_ids=list(set(tax_ids))
        # account=self.env['account.invoice.line'].get_invoice_line_account('out_refund', line.product_id,order.fiscal_position_id,order.company_id)
        # price_unit = round(self.amount/ qty,self.env['decimal.precision'].precision_get('Product Price'))
        #
        # new_record = account_invoice_line_obj.new({
        #                                           'product_id':product.id,
        #                                           'name':self.inv_line_des,
        #                                           'invoice_id':invoice.id,
        #                                           'account_id':account.id,
        #                                           'price_unit':price_unit,
        #                                           'quantity':qty,
        #                                           'uom_id':product.uom_id.id,
        #                                            })
        #
        # new_record._onchange_product_id()
        #
        #
        # vals=account_invoice_line_obj._convert_to_write({name: new_record[name] for name in new_record._cache})
        #
        # vals.update({'invoice_line_tax_id':[(6,0,tax_ids)],'invoice_id':invoice.id,'price_unit':price_unit,'quantity':qty,'name':self.inv_line_des,'account_id':account.id})
        # account_invoice_line_obj.create(vals)

        return True
