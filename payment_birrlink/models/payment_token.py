# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Developed by Fkadeal Matiwos
# GitHub: https://github.com/fkadeal
# Company: BirrLink Financial Technology
#

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    birrlink_customer_email = fields.Char(
        string="Customer Email",
        help="The email of the customer at the time the token was created.", readonly=True
    )
