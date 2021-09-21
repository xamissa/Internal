# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016-Today Geminate Consultancy Services (<http://geminatecs.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name' : 'Mail SMTP and IMAP + Alias Domain By Company',
    'version' : '12.0.0.1',
    'author': 'Geminate Consultancy Services',
    'company': 'Geminate Consultancy Services',
    'category': 'sales',
    'website': 'https://www.geminatecs.com/',
    'summary' : 'Mail SMTP and IMAP + Alias Domain By Company',
    'description' : """Geminate comes with a feature to support multiple domain and multi company emailing system.""",
    'depends' : ['base','sale_management','fetchmail','crm','project','mail','account','hr_recruitment'],
    'data' : [
        'security/ir.model.access.csv',
        'views/mail_server_view.xml',
        'views/alias_mail_view.xml',
    ],
    'qweb': [],
    "license": "Other proprietary",
    'installable': True,
    'images': ['static/description/email-alias.jpg'],
    'auto_install': False,
    'application': False,
    "price": 49.99,
    "currency": "EUR"
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
