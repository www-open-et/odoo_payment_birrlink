# -*- coding: utf-8 -*-
{
    'name': "Payment Acquirer: BirrLink",
    'version': '10.0.1.1',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 1,
    'summary': "Ethiopian Payment Acquirer",
    'description': """
BirrLink Payment Gateway Integration
====================================

Developed by: Fkadeal Matiwos
GitHub: https://github.com/fkadeal
Company: BirrLink Financial Technology

This module integrates BirrLink payment gateway with Odoo.
    """,   
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
    'author': 'Fkadeal Matiwos',
    'website': 'https://github.com/fkadeal',
    'maintainer': 'BirrLink Financial Technology',
}
