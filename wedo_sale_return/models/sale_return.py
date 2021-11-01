# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError
from odoo.tests import Form


class SaleReturn(models.Model):
    _name = 'sale.return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "sale return management"
    _order = 'id desc'

    @api.model
    def _get_default_journal(self):
        journal = self.env['account.journal'].sudo().search([('type', '=', 'sale'),('company_id','=',self.env.company.id)], limit=1)
        if journal:
            return journal

    @api.model
    def _get_picking_type(self):
        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'incoming'), ('warehouse_id.company_id', '=', self.env.company.id)])
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return picking_type[:1]

    name = fields.Char(string="Name", copy=False, readonly=True, default=lambda x: _('New'))
    date_order = fields.Datetime('Order Date', required=True, default=fields.Datetime.now())
    sale_order_id = fields.Many2one('sale.order', string="Sale Order", track_visibility='always')
    location_id = fields.Many2one('stock.location', string="Return Location", track_visibility='always')
    picking_ids = fields.One2many('stock.picking', 'sale_return_id', string="Return Picking", track_visibility='always')
    partner_id = fields.Many2one("res.partner", string='Customer', track_visibility='always', required=True)
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='State', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    order_line_ids = fields.One2many('sale.return.line', 'order_id', string='Return Lines',
                                     states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    return_journal_id = fields.Many2one('account.journal', string='Return Journal', required=True,
                                        default=_get_default_journal)
    invoice_count = fields.Integer(string='Invoices', compute='_compute_invoice_count')
    picking_count = fields.Integer(string='Picking', compute='_compute_invoice_count')
    sale = fields.Boolean(string="From Sale Order")
    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id.id)
    invoice_ids = fields.One2many('account.move', 'sale_return_id', string="Invoice")
    location_id = fields.Many2one('stock.location', 'Receive To')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company.id)
    picking_type_id = fields.Many2one('stock.picking.type', 'Receive To',
                                      required=True, default=_get_picking_type, domain=[('code', '=', 'incoming')])
    default_location_dest_id_usage = fields.Selection(related='picking_type_id.default_location_dest_id.usage',
                                                      string='Destination Location Type',
                                                      readonly=True)
    reason_id = fields.Many2one('sale.return.reason',string="Reason",required=True, track_visibility='always')
    reference = fields.Char(string="Reference", track_visibility='always',copy=False)
    total = fields.Float(compute='_compute_total_amount', store=True)


    _sql_constraints = [
        ('reference_uniq', 'unique (reference)', "This Reference already exists !"),
    ]

    @api.depends('order_line_ids.price_subtotal')
    def _compute_total_amount(self):
        for rec in self:
            rec.total = sum(rec.order_line_ids.mapped('price_subtotal')) if rec.order_line_ids else 0.0


    def unlink(self):
        for rec in self:
            if rec.state not in ['draft', 'cancel']:
                raise ValidationError(_("You can not delete confirmed Requests"))
            else:
                return super(SaleReturn, rec).unlink()

    @api.model
    def create(self, vals):
        res = super(SaleReturn, self).create(vals)
        if not res.name or res.name == _('New'):
            res.name = self.env['ir.sequence'].sudo().next_by_code('sale.return.sequence') or _('New')
        return res

    def _compute_invoice_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)
            rec.invoice_count = len(rec.invoice_ids)

    def action_open_picking_invoice(self):
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.invoice_ids.ids), ],
            'context': {'create': False},
            'target': 'current'
        }

    def action_open_picking(self):
        return {
            'name': 'Picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('id', '=', self.picking_ids.ids)],
            'target': 'current'
        }

    @api.onchange('sale_order_id', 'sale')
    def get_line(self):
        for rec in self:
            if rec.sale:
                if rec.sale_order_id:
                    rec.order_line_ids = False
                    lines = []
                    for order in rec.sale_order_id.order_line:
                        lines.append((0, 0, {
                            'sale_order_id': order.id,
                            'product_id': order.product_id.id,
                            'product_qty': order.product_uom_qty,
                            'product_uom': order.product_uom.id,
                            'price_unit': order.price_unit, }))
                    rec.write({'order_line_ids': lines})
            else:
                rec.order_line_ids = False
                rec.sale_order_id = False

    @api.onchange('partner_id')
    def chang_partner(self):
        for rec in self:
            rec.order_line_ids = False
            rec.sale_order_id = False

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def action_process(self):
        if self.order_line_ids:
            returns = self.order_line_ids.filtered(lambda r: r.qty_return > 0)
            if returns:
                self.create_picking_returns(returns)
            else:
                raise ValidationError(_("No line to return picking"))
            self.state = 'done'
        else:
            raise ValidationError(_("No lines"))

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done' and rec.picking_ids.filtered(lambda r: r.state == 'done'):
                raise ValidationError(_("You can not cancel processed request"))
            else:
                rec.state = "cancel"
                picks = rec.picking_ids.filtered(lambda r: r.state not in ['done', 'cancel'])
                if picks:
                    for picking_id in picks:
                        picking_id.sudo().action_cancel()

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'done' and rec.picking_ids.filtered(lambda r: r.state == 'done'):
                raise ValidationError(_("You can not reset processed request"))
            else:
                rec.state = 'draft'

    def create_picking_returns(self, returns_line):
        customer_picking = self.env['stock.picking'].sudo().create({
            'location_id': self.picking_type_id.default_location_src_id.id if self.picking_type_id.default_location_src_id
            else self.partner_id.property_stock_customer.id,
            'location_dest_id': self.picking_type_id.default_location_dest_id.id,
            'partner_id': self.partner_id.id,
            'picking_type_id': self.picking_type_id.id,
            'is_sale_return': True,
            'sale_return_id': self.id,
            'origin': self.name,
        })

        for re in returns_line:
            customer_move = self.env['stock.move'].sudo().create({
                'name': 'Sale Return',
                'location_id': self.partner_id.property_stock_customer.id if self.partner_id.property_stock_customer
                else self.picking_type_id.default_location_src_id.id,
                'location_dest_id': self.picking_type_id.default_location_dest_id.id,
                'product_id': re.product_id.id,
                'product_uom': re.product_uom.id,
                'price_unit': re.price_unit,
                'product_uom_qty': re.qty_return,
                'picking_id': customer_picking.id,
                'sale_return_line_id': re.id,
            })
        customer_picking.sudo().action_assign()


class SaleReturnLine(models.Model):
    _name = 'sale.return.line'

    sequence = fields.Integer(string='Sequence', default=10)
    product_qty = fields.Float(string='Sale Quantity', digits='Product Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product', required=True, )
    order_id = fields.Many2one('sale.return', string='Return Order', index=True,
                               ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order.line', string='Sale Order line', )
    state = fields.Selection(related='order_id.state', store=True, )
    qty_return = fields.Float("Return Qty", digits='Product Unit of Measure', required=True)
    received_qty = fields.Float("Received Qty", compute="get_qty_amount", store=True, digits='Product Unit of Measure')
    invoiced_qty = fields.Float("Invoiced Qty", compute="get_qty_amount", store=True, digits='Product Unit of Measure')
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    date_order = fields.Datetime(related='order_id.date_order', string='Order Date')
    tax_id = fields.Many2many('account.tax', string='Taxes', )
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    currency_id = fields.Many2one("res.currency", related='order_id.currency_id', string="Currency", readonly=True,
                                  required=True)

    @api.depends('order_id.invoice_ids', 'order_id.picking_ids', 'order_id.picking_ids.state')
    def get_qty_amount(self):
        for rec in self:
            rec.invoiced_qty = sum(
                rec.order_id.invoice_ids.invoice_line_ids.filtered(lambda r: r.sale_return_line_id == rec).mapped(
                    'quantity'))
            rec.received_qty = sum(rec.order_id.picking_ids.move_ids_without_package.filtered(
                lambda r: r.sale_return_line_id == rec and r.picking_id.state == 'done').mapped('quantity_done'))

    @api.depends('qty_return', 'product_id', 'price_unit', 'currency_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit
            line.price_subtotal = line.qty_return * price

    @api.onchange('product_id')
    def get_unit_uom(self):
        self.product_uom = self.product_id.uom_id.id
        self.price_unit = self.product_id.lst_price


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_return_id = fields.Many2one('sale.return', string='Return')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    sale_return_line_id = fields.Many2one('sale.return.line', string='Sale Return')

class SaleReturnReason(models.Model):
    _name = 'sale.return.reason'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "sale return reason"
    _order = 'sequence'



    name = fields.Char(string="Reason",required=True, track_visibility='always')
    sequence = fields.Integer(string="Sequence",default=10)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "This Reason already exists !"),
    ]