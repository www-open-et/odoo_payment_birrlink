# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Developed by Fkadeal Matiwos
# GitHub: https://github.com/fkadeal
# Company: BirrLink Financial Technology
#

import logging
import pprint

import requests
from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .. import const


_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('birrlink', "BirrLink")], 
        string='Provider'
    )
    birrlink_public_key = fields.Char(
        string="BirrLink Public Key",
        help="The key solely used to identify the account with BirrLink.",
        required_if_provider='birrlink',
    )
    birrlink_secret_key = fields.Char(
        string="BirrLink Secret Key",
        required_if_provider='birrlink',
        groups='base.group_system',
    )
    birrlink_webhook_secret = fields.Char(
        string="BirrLink Webhook Secret",
        required_if_provider='birrlink',
        groups='base.group_system',
    )
    birrlink_return_url = fields.Char(
        string="BirrLink Return URL",
        default="/payment/birrlink/return",
        help="URL to which BirrLink redirects after payment completion",
        required_if_provider='birrlink',
    )
    birrlink_auth_return_url = fields.Char(
        string="BirrLink Auth Return URL", 
        default="/payment/birrlink/auth_return",
        help="URL to which BirrLink redirects after authorization",
        required_if_provider='birrlink',
    )
    birrlink_webhook_url = fields.Char(
        string="BirrLink Webhook URL",
        default="/payment/birrlink/webhook",
        help="URL for BirrLink webhook notifications",
        required_if_provider='birrlink',
    )

    def _get_feature_support(self):
        res = super(PaymentAcquirer, self)._get_feature_support()
        if self.provider == 'birrlink':
            res['tokenize'] = ['birrlink']
        return res

    def _get_compatible_acquirers(self, currency_id=None, is_validation=False):
        """ Filter acquirers to only keep Birrlink ones for supported currencies. """
        acquirers = super(PaymentAcquirer, self)._get_compatible_acquirers(
            currency_id=currency_id, is_validation=is_validation
        )
        
        currency = self.env['res.currency'].browse(currency_id).exists()
        if (currency and currency.name not in const.SUPPORTED_CURRENCIES) or is_validation:
            acquirers = acquirers.filtered(lambda acquirer: acquirer.provider != 'birrlink')

        return acquirers

    def _birrlink_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to Birrlink API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        url = url_join('https://api.birrlink.et', endpoint)
        headers = {
                "Content-Type": "application/json",
                "api-key": self.birrlink_secret_key
            }
        
        # Log the request details
        _logger.info("Sending BirrLink API request to: %s", url)
        _logger.info("Request method: %s", method)
        _logger.info("Request headers: %s", str({k: '***' if k == 'api-key' else v for k, v in headers.items()}))
        if payload:
            _logger.info("Request payload: %s", pprint.pformat(payload))
        
        try:
            if method == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            # Log the response details
            _logger.info("Received BirrLink API response [HTTP %s]: %s", response.status_code, response.text[:500] if response.text else "No response body")
            
            try: 
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.error(
                    "Invalid API request at %s with data:\n%s\nResponse: %s", url, pprint.pformat(payload), response.text
                )
                try:
                    error_message = response.json().get('message', 'Unknown error')
                except ValueError:
                    # If response is not JSON, use the raw text
                    error_message = response.text or 'Unknown error'
                raise ValidationError(_("BirrLink: The communication with the API failed. BirrLink gave us the following information: '%s'") % error_message)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "BirrLink: " + _("Could not establish the connection to the API.")
            )
        return response.json()

    def birrlink_get_form_action_url(self):
        """ Generates the form action URL for BirrLink redirect.
        """
        _logger.info("Generating BirrLink form action URL")
        return '%s/payment/birrlink/redirect' % (self.env['ir.config_parameter'].sudo().get_param('web.base.url'))

    def birrlink_form_generate_values(self, values):
        """ Generate the values used to render the form button template.
        """
        _logger.info("Generating BirrLink form values with input data: %s", pprint.pformat(values))
        
        # Call the transaction's method to get the proper formatted values
        tx_obj = self.env['payment.transaction']
        birrlink_tx_values = tx_obj.birrlink_form_generate_values(values)
        
        # Add the form action URL to the values
        birrlink_tx_values['tx_url'] = self.birrlink_get_form_action_url()
        
        _logger.info("Final BirrLink form values with tx_url: %s", pprint.pformat(birrlink_tx_values))
        return birrlink_tx_values