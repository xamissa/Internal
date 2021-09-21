# -*- coding: utf-8 -*-
##############################################################################

#
##############################################################################

{
    'name': 'Invoice on Timesheets',
    'depends': ['base', 'account', 'hr_timesheet', 'product', 'project'],
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
Generate your Invoices from Expenses, Timesheet Entries.


reports.""",
    'author': 'ERPWEB',
    'license': 'AGPL-3',
    'website': 'https://erpweb.co.zac',
    'data': [
        'wizard/hr_timesheet_invoice_create_view.xml',
'views/hr_timesheet_invoice_view.xml',
    ],
    'demo': [
        # 'demo/hr_timesheet_invoice_data.xml',
        #'demo/hr_timesheet_invoice_demo.xml',
    ],
    'images': [
        'static/description/invoice-on-timesheets-banner.jpg',
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
}
