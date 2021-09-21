# -*- coding: utf-8 -*-
{
    'name': 'Helpdesk Ticket Custom',
    'version': '1.0',
    'category': 'Helpdesk',
    'summary': 'Helpdesk',
    'description': """
     Add create ticket and close ticket date and also all billable hours, quoted hours, time spent, remaining hours fileds of form.
    """,
    'author': 'Erpweb',
    'images': [],
    'depends': ['helpdesk','project','hr_timesheet_invoice','helpdesk_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'wizard/helpdesk_invoice_create_view.xml',
        'views/helpdesk_view.xml',
        'views/report_hours_quoted.xml',
    ],
    'demo': [],
    'test': [],
    'application': True,
    'qweb': [],
    'auto_install': False,
}

