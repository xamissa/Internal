# -*- coding: utf-8 -*-
{
    'name': 'Captcha - Contact Form',

    'summary': 'Simple Captcha for Contact Us Form',

    'description': """
Simple Captcha for "Contact Us" Form
====================================


This module adds simple captcha to the website **Contact Us** form
in order to protect you from most of the automated bot spam.


Note
----

This module requires the `Captcha`_  Python module.

Install the dependency
~~~~~~~~~~~~~~~~~~~~~
either with
^^^^^^^^^^^

``pip install captcha``

or with
^^^^^^^

``pip3 install captcha``


.. _Captcha: https://github.com/lepture/captcha
    """,

    'author': 'PluginMere',
    'website': 'https://github.com/pluginmere/community_odoo',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Website',
    'license': 'LGPL-3',
    'version': '14.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['website_crm'],
    'external_dependencies': {'python': ['captcha']},

    # always loaded
    'data': [
        'views/website_crm_captcha.xml',
        'views/snippets/s_website_form.xml',
    ],
    'installable': True,
    'auto_install': False,
}
