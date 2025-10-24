# -*- coding: utf-8 -*-
{
    'name': "Payment Acquirer: BirrLink",
    'version': '10.0.1.1',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 1,
    'summary': "Ethiopian Payment Acquirer",
    'description': """<div>
        <h1>BirrLink Payment Gateway Integration</h1>
        <p>Company: BirrLink Financial Technology</p>
        <p>This module integrates BirrLink payment gateway with Odoo, providing seamless payment processing capabilities for businesses operating in Ethiopia and the African region.</p>
        <h2>Developed by:</h2>
        <p>Fkadeal Matiwos</p>
        <p>GitHub: <a href="https://github.com/fkadeal">https://github.com/fkadeal</a></p>
        </div>""",
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
    'author': 'Fkadeal Matiwos',
    'website': 'https://github.com/fkadeal',
    'maintainer': 'BirrLink Financial Technology',
}
