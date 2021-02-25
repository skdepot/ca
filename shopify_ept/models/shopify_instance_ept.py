from odoo import models, fields, api, _
from odoo.exceptions import Warning
from .. import shopify

class shopify_instance_ept(models.Model):
    _name = "shopify.instance.ept"
    _description = 'Shopify Instance Ept'

    def _default_tip_product(self):
        """
        This method is used to set the tip product in an instance.
        @author: Haresh Mori on Date 9-Dec-2020.
        """
        tip_product = self.env.ref('shopify_ept.shopify_tip_product') or False
        return tip_product

    name = fields.Char(size=120, string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    lang_id = fields.Many2one('res.lang', string='Language')
    order_prefix = fields.Char(size=10, string='Order Prefix')
    order_auto_import = fields.Boolean(string='Auto Order Import?')
    order_auto_update = fields.Boolean(string="Auto Order Update ?")
    stock_auto_export = fields.Boolean(string="Stock Auto Export?")
    import_stock = fields.Boolean(string="import_stock?")
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')
    stock_field = fields.Many2one('ir.model.fields', string='Stock Field')
    country_id = fields.Many2one("res.country", "Country")
    api_key = fields.Char("API Key", required=True)
    password = fields.Char("Password", required=True)
    shared_secret = fields.Char("Secret Key", required=True)
    host = fields.Char("Host", required=True)
    shipment_charge_product_id = fields.Many2one("product.product", "Shipment Fee",
                                                 domain=[('type', '=', 'service')])
    section_id = fields.Many2one('crm.team', 'Sales Team')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term')
    discount_product_id = fields.Many2one("product.product", "Discount",
                                          domain=[('type', '=', 'service')])
    apply_tax_in_order = fields.Selection([("odoo_tax", "Odoo Default Tax Behaviour"),
                                           ("create_shopify_tax", "Create new tax if not found")],
                                          default='create_shopify_tax', copy=False, help=""" For Shopify Orders :- \n
                    1) Odoo Default Tax Behaviour - The Taxes will be set based on Odoo's
                                 default functional behaviour i.e. based on Odoo's Tax and Fiscal Position configurations. \n
                    2) Create New Tax If Not Found - System will search the tax data received 
                    from Shopify in Odoo, will create a new one if it fails in finding it.""")
    invoice_tax_account_id = fields.Many2one('account.account', string='Invoice Tax Account')
    credit_tax_account_id = fields.Many2one('account.account', string='Credit Tax Account')
    add_discount_tax = fields.Boolean("Calculate Discount Tax", default=False)
    last_inventory_update_time = fields.Datetime("Last Inventory Update Time")
    auto_closed_order = fields.Boolean("Auto Closed Order", default=False)
    state = fields.Selection([('not_confirmed', 'Not Confirmed'), ('confirmed', 'Confirmed')],
                             default='not_confirmed')
    workflow_config_ids = fields.One2many("sale.auto.workflow.configuration", "shopify_instance_id",
                                          "Workflows")
    multiple_tracking_number = fields.Boolean(string='One order can have multiple Tracking Number',
                                              default=False)
    notify_customer = fields.Boolean("Notify Customer about Update Order Status?",
                                     help="If checked,Notify the customer via email about Update Order Status")
    notify_by_email_while_cancel_picking = fields.Boolean("Notify Customer about Cancel Picking?",
                                                          help="If checked,Notify the customer via email about Order Cancel")
    notify_by_email_while_refund = fields.Boolean("Notify Customer about Refund?",
                                                  help="If checked,Notify the customer via email about Refund")
    restock_in_shopify = fields.Boolean("Restock In Shopify ?",
                                        help="If checked,Restock In Shopify while refund")
    auto_import_product = fields.Boolean(string="Auto Create Product if not found?")
    sync_images_with_product = fields.Boolean("Sync Images?",
                                              help="Check if you want to import images along with products",
                                              default=False)
    # auto_import_stock=fields.Boolean(string="Auto Import Stock?")
    import_price = fields.Boolean(string="Import Price?")
    inventory_adjustment_id = fields.Many2one('stock.inventory', "Last Inventory")
    is_image_url = fields.Boolean("Is Image URL?",
                                  help="Check this if you use Images from URL\nKeep as it is if you use Product images")
    is_set_price = fields.Boolean(string="Set Price ?", default=False)
    is_set_stock = fields.Boolean(string="Set Stock ?", default=False)
    is_publish = fields.Boolean(string="Publish In Website ?", default=False)
    is_set_image = fields.Boolean(string="Set Image ?", default=False)
    last_date_order_import = fields.Datetime(string="Last Date of Import Order",
                                             help="Which from date to import shopify order from shopify")
    import_shopify_order_status_ids = fields.Many2many('import.shopify.order.status',
                                                       'shopify_instance_order_status_rel',
                                                       'instance_id', 'status_id',
                                                       "Import Order Status",
                                                       help="Selected status orders will be imported from Shopify")
    update_category_in_odoo_product = fields.Boolean(string="Update Category In Odoo Product ?")
    is_use_default_sequence = fields.Boolean("Use Odoo Default Sequence?",
                                             help="If checked,Then use default sequence of odoo for sale order create")
    # Account field
    shopify_property_account_payable_id = fields.Many2one('account.account',
                                                          string="Account Payable",
                                                          help='This account will be used instead of the default one as the payable account for the current partner')
    shopify_property_account_receivable_id = fields.Many2one('account.account',
                                                             string="Account Receivable",
                                                             help='This account will be used instead of the default one as the receivable account for the current partner')
    shopify_last_date_update_stock = fields.Datetime(string="Last Date of Stock Update",
                                                     help="it is used to store last update inventory stock date")
    shopify_store_time_zone = fields.Char("Store Time Zone",
                                          help='This field used to import order process')
    color = fields.Integer(string='Color Index')
    #Below field is used for product count
    product_count = fields.Integer(compute='_count_all', string="Product")
    exported_product_count = fields.Integer(compute='_count_all', string="Exported Products")
    ready_to_expor_product_count = fields.Integer(compute='_count_all', string="Ready For Export")
    published_product_count = fields.Integer(compute='_count_all', string="Published Product")
    unpublished_product_count = fields.Integer(compute='_count_all', string="#UnPublished Product")
    #Below field is used for sale order count
    sale_order_count = fields.Integer(compute='_count_all', string="Sale Order Count")
    quotation_count = fields.Integer(compute='_count_all', string="Quotation")
    order_count = fields.Integer(compute='_count_all', string="Sales Orders")
    risk_order_count = fields.Integer(compute='_count_all', string="Risky Orders")
    #Below field is used for picking count
    picking_count = fields.Integer(compute='_count_all', string="Picking")
    confirmed_picking_count = fields.Integer(compute='_count_all', string="Confirm Picking")
    assigned_picking_count = fields.Integer(compute='_count_all', string="Assigned Pickings")
    done_picking_count = fields.Integer(compute='_count_all', string="Done Picking")
    #Below field is used for invoice count
    invoice_count = fields.Integer(compute='_count_all', string="Invoice")
    open_invoice_count = fields.Integer(compute='_count_all', string="Open Invoice")
    paid_invoice_count = fields.Integer(compute='_count_all', string="Paid Invoice")
    refund_invoice_count = fields.Integer(compute='_count_all', string="Refund Invoices")
    #Below field is used for collection count
    shopify_custom_collection_count = fields.Integer(compute='_count_all', string="Shopify Collections")
    shopify_smart_collection_count = fields.Integer(compute='_count_all', string="Shopify Smart Collections")

    global_channel_id = fields.Many2one('global.channel.ept', string="Global Channel")



    shopify_api_url = fields.Char(string="Payout API URL", default = 'admin/api/2019-04/shopify_payments/')
    transaction_line_ids = fields.One2many("shopify.payout.account.config.ept", "instance_id",
                                           string="Transaction Line")
    shopify_settlement_report_journal_id = fields.Many2one('account.journal',
                                                           string='Payout Report Journal')
    payout_last_import_date = fields.Date(string="Payout last Import Date")
    shopify_activity_type_id = fields.Many2one('mail.activity.type',
                                               string="Activity Type")
    shopify_date_deadline = fields.Integer('Deadline lead days',
                                           help="its add number of  days in schedule activity deadline date ")
    tip_product_id = fields.Many2one("product.product", "TIP",domain=[('type', '=', 'service')],
                                     default=_default_tip_product, help="This is used for set tip product in a sale order lines")

    def _count_all(self):
        for instance in self:
            #Below is used to count product records.
            product_query = self.prepare_query_to_count_record('shopify_product_template_ept',instance)
            instance.product_count = self.query_to_product_count(product_query)
            instance.exported_product_count = self.query_to_product_count(False, instance,'exported_in_shopify','true')
            instance.ready_to_expor_product_count = self.query_to_product_count(False, instance,'exported_in_shopify','false')
            instance.published_product_count = self.query_to_product_count(False, instance,'website_published','true')
            unpublished_product_query = product_query +" and website_published = 'false' and exported_in_shopify = 'true'"
            instance.unpublished_product_count = self.query_to_product_count(unpublished_product_query)

            #Below is used to count sale order records.
            sale_query = self.prepare_query_to_count_record('sale_order',instance)
            instance.sale_order_count = self.query_to_sale_order_count(sale_query)
            instance.quotation_count = self.query_to_sale_order_count(False,instance, 'state', ('draft', 'sent'))
            order_query = sale_query +" and state not in ('draft', 'sent', 'cancel')"
            instance.order_count = self.query_to_sale_order_count(order_query)
            risky_order_query = sale_query+" and state IN ('draft') and is_risky_order = true"
            instance.risk_order_count = self.query_to_sale_order_count(risky_order_query)

            #Below is used to count picking records.
            picking_query = self.prepare_query_to_count_record('stock_picking',instance)
            instance.picking_count = self.query_to_delivery_count(picking_query)
            instance.confirmed_picking_count = self.query_to_delivery_count(False, instance, 'state', 'confirmed')
            instance.assigned_picking_count = self.query_to_delivery_count(False, instance, 'state', 'assigned')
            instance.done_picking_count = self.query_to_delivery_count(False, instance, 'state', 'done')

            #Below is used to count invoice records.
            invoice_query = self.prepare_query_to_count_record('account_invoice',instance)
            instance.invoice_count = self.query_to_invoice_count(invoice_query)
            open_invoice_query = invoice_query+" and state='open' and type='out_invoice'"
            instance.open_invoice_count = self.query_to_invoice_count(open_invoice_query)
            paid_invoice_query = invoice_query+" and state='paid' and type='out_invoice'"
            instance.paid_invoice_count = self.query_to_invoice_count(paid_invoice_query)
            refund_invoice_query = invoice_query+" and type='out_refund'"
            instance.refund_invoice_count = self.query_to_invoice_count(refund_invoice_query)

            #Below is used to count collection records.
            instance.shopify_custom_collection_count = self.query_to_collection_count(False, instance, 'is_smart_collection', 'false')
            instance.shopify_smart_collection_count = self.query_to_collection_count(False, instance, 'is_smart_collection', 'true')

    def prepare_query_to_count_record(self, table_name, instance):
        """ This method is used to prepare a query.
            :param table_name: Name of table
            :param instance: Record of instance.
            @return: query
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 December 2020 .
            Task_id: 168799 - Shopify Dashboard changes v13 & v12
        """
        query = """select count(*) from %s where 
            shopify_instance_id=%s"""%(table_name, instance.id)
        return query


    def query_to_product_count(self, query, instance = '', query_field = '', value =''):
        """ This method is used to count the product record using the sql query.
            :param query: Sql query
            :param instance: Record of instance.
            :param query_field: field name
            :param value: value of field.
            @return: Count of record.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 December 2020 .
            Task_id: 168799 - Shopify Dashboard changes v13 & v12
        """
        if not query:
            query = """select count(*) from shopify_product_template_ept where shopify_instance_id=%s and 
            %s=%s""" % (instance.id,query_field,value)
        self._cr.execute(query)
        records = self._cr.dictfetchall()
        return records[0].get('count')

    def query_to_sale_order_count(self, query, instance = '', query_field = '', value = ''):
        """ This method is used to count the sale order record using the sql query.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 December 2020 .
            Task_id: 168799 - Shopify Dashboard changes v13 & v12
        """
        if not query:
            query = """select count(*) from sale_order where shopify_instance_id=%s and 
            %s IN %s""" % (instance.id,query_field,value)
        self._cr.execute(query)
        records = self._cr.dictfetchall()
        return records[0].get('count')

    def query_to_delivery_count(self, query, instance = '', query_field = '', value = ''):
        """ This method is used to count the delivery record using the sql query.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 December 2020 .
            Task_id: 168799 - Shopify Dashboard changes v13 & v12
        """
        if not query:
            query = """select count(*) from stock_picking where shopify_instance_id=%s and 
            %s='%s'""" % (instance.id,query_field,value)
        self._cr.execute(query)
        records = self._cr.dictfetchall()
        return records[0].get('count')

    def query_to_invoice_count(self, query):
        """ This method is used to count the delivery record using the sql query.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 December 2020 .
            Task_id: 168799 - Shopify Dashboard changes v13 & v12
        """
        self._cr.execute(query)
        records = self._cr.dictfetchall()
        return records[0].get('count')

    def query_to_collection_count(self, query, instance = '', query_field = '', value = ''):
        """ This method is used to count the delivery record using the sql query.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 December 2020 .
            Task_id: 168799 - Shopify Dashboard changes v13 & v12
        """
        if not query:
            query = """select count(*) from shopify_collection_ept where shopify_instance_id=%s and 
            %s='%s'""" % (instance.id, query_field, value)
        self._cr.execute(query)
        records = self._cr.dictfetchall()
        return records[0].get('count')


    @api.multi
    def test_shopify_connection(self):
        shop = self.host.split("//")
        if len(shop) == 2:
            shop_url = shop[0] + "//" + self.api_key + ":" + self.password + "@" + shop[
                1] + "/admin/api/2020-01"
        else:
            shop_url = "https://" + self.api_key + ":" + self.password + "@" + shop[0] + "/admin/api/2020-01"
        shopify.ShopifyResource.set_site(shop_url)
        try:
            shop_id = shopify.Shop.current()
            shop_detail = shop_id.to_dict()
            self.write({'shopify_store_time_zone': shop_detail.get('timezone')})
            self._cr.commit()
        except Exception as e:
            raise Warning(e)
        raise Warning('Service working properly')

    @api.multi
    def reset_to_confirm(self):
        self.write({'state':'not_confirmed'})
        return True

    @api.multi
    def confirm(self):
        self.connect_in_shopify()
        try:
            shop_id = shopify.Shop.current()
        except Exception as e:
            raise Warning(e)
        self.write({'state':'confirmed'})
        self.env['shopify.location.ept'].import_shopify_locations(self)
        return True

    @api.model
    def connect_in_shopify(self):
        instance = self
        shop = instance.host.split("//")
        if len(shop) == 2:
            shop_url = shop[0] + "//" + instance.api_key + ":" + instance.password + "@" + shop[
                1] + "/admin/api/2020-01"
        else:
            shop_url = "https://" + instance.api_key + ":" + instance.password + "@" + shop[
                0] + "/admin/api/2020-01"
        shopify.ShopifyResource.set_site(shop_url)
        return True
