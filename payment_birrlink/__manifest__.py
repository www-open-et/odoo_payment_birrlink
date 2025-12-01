# -*- coding: utf-8 -*-
{
    'name': "Payment Acquirer: BirrLink",
    'version': '10.0.1.1',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 1,
    'summary': "Ethiopian Payment Acquirer",
    'description': 'BirrLink Payment Gateway Integration - Ethiopian Payment Acquirer',
    'images': ['static/description/cover.png'],
    'depends': ['payment', 'account'],
    'data': [
        'views/payment_birrlink_templates.xml',
        'views/payment_acquirer_views.xml',
        'views/inventory_payment_views.xml',
        'data/payment_acquirer_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'application': False,
    'license': 'LGPL-3',
    'author': 'BirrLink Financial Technology',
    'website': 'https://birrlink.et',
    'maintainer': 'BirrLink Financial Technology',
}
