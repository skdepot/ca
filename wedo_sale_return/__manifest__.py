# -*- coding: utf-8 -*-
# Copyright 2020 WeDo Technology
# Website: http://wedotech-s.com
# Email: apps@wedotech-s.com
# Phone:00249900034328 - 00249122005009
{
    'name': "Sale Return Managment",
    'version': '14.0.1.0',
    'sequence': 1,
    'author': "Wedo Technology",
    'website': "http://wedotech-s.com",
    'support': 'odoo.support@wedotech-s.com',
    'license': 'OPL-1',
    'category': "Sale",
    'summary': """
Manage Sale picking return and invoice refund    
""",
    'description': """
Manage Sale picking return and invoice refund    

    """,
    'depends': ['sale_stock','stock','account'],
    'images': ['images/main.png','images/sale.png', 'images/s_return.png', 'images/tree.png'],

    'data': [
        'security/security_view.xml',
        'security/ir.model.access.csv',
        'data/return_sequense.xml',
        'views/sale_return_view.xml',
        'views/stock_picking_inherited.xml',
        'views/templates.xml',
        'reports/sale_return_report.xml',
    ],
    'test': [

    ],
    'price': 49,
    'currency': 'USD',
    'auto_install': False,
    'installable': True,
}
