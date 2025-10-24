# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Developed by Fkadeal Matiwos
# GitHub: https://github.com/fkadeal
# Company: BirrLink Financial Technology
#

# The currencies supported by BirrLink, in ISO 4217 format.
# See https://BirrLink.et 
SUPPORTED_CURRENCIES = [
    'ETB',
    'GBP',
    'CAD',
    'XAF',
    'CLP',
    'COP',
    'EGP',
    'EUR',
    'GHS',
    'GNF',
    'KES',
    'MWK',
    'MAD',
    'NGN',
    'RWF',
    'SLL',
    'STD',
    'ZAR',
    'TZS',
    'UGX',
    'USD',
    'XOF',
    'ZMW',
]

# Mapping of transaction states to BirrLink payment statuses.
PAYMENT_STATUS_MAPPING = {
    'pending': ['pending'],
    'done': ['success', 'approved', 'completed'],
    'cancel': ['cancelled', 'canceled'],
    'error': ['failed', 'error'],
}

