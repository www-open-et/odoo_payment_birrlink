# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Developed by Fkadeal Matiwos
# GitHub: https://github.com/fkadeal
# Company: BirrLink Financial Technology
#

import hmac
import json
import logging
import pprint
import time

from werkzeug.exceptions import Forbidden
from werkzeug import urls
import werkzeug.utils

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


_logger = logging.getLogger(__name__)


class BirrlinkController(http.Controller):
    _default_return_url = '/payment/birrlink/return'
    _default_auth_return_url = '/payment/birrlink/auth_return'
    _default_webhook_url = '/payment/birrlink/webhook'

    @http.route('/payment/birrlink/return', type='http', auth='public', methods=['GET'])
    def birrlink_return_from_checkout(self, **data):
        """ Process the notification data sent by BirrLink after redirection from checkout.

        :param dict data: The notification data.
        """
        _logger.info("Handling redirection from BirrLink with data:\n%s", pprint.pformat(data))

        # Find the transaction and handle the notification data
        if data.get('status') != 'cancelled':
            tx = request.env['payment.transaction'].sudo()._birrlink_form_get_tx_from_data(data)
            tx.form_feedback(data, 'birrlink')
        else:  # The customer cancelled the payment by clicking on the close button.
            pass  # Don't try to process this case because the transaction id was not provided.

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @http.route('/payment/birrlink/auth_return', type='http', auth='public', methods=['GET'])
    def birrlink_return_from_authorization(self, response):
        """ Process the response sent by BirrLink after authorization.

        :param str response: The stringified JSON response.
        """
        data = json.loads(response)
        return self.birrlink_return_from_checkout(**data)

    @http.route('/payment/birrlink/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def birrlink_webhook(self):
        """Process the notification data sent by BirrLink to the webhook."""
        _logger.info("Received webhook request from BirrLink with headers: %s", dict(request.httprequest.headers))
        
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except ValueError:
            _logger.error("Received invalid JSON data from BirrLink webhook: %s", request.httprequest.data)
            return '', 400
        
        _logger.info("Notification received from BirrLink with data:\n%s", pprint.pformat(data))

        if not data:
            _logger.error("No JSON data received from BirrLink webhook")
            return '', 400

        # Handle both flat and nested structures
        notification_data = data.get('data', data)

        _logger.info("Processing BirrLink notification with status: %s", notification_data.get('status'))

        # Handle various payment statuses, not just COMPLETED
        payment_status = notification_data.get('status', '').upper()
        if payment_status in ['COMPLETED', 'SUCCESS', 'APPROVED', 'DONE']:
            try:
                tx_sudo = request.env['payment.transaction'].sudo()._birrlink_form_get_tx_from_data(
                    notification_data
                )

                # Uncomment signature verification when webhook secret is configured
                # signature = request.httprequest.headers.get('verif-hash')
                # if signature and tx_sudo.acquirer_id.birrlink_webhook_secret:
                #     self._verify_notification_signature(signature, tx_sudo)

                tx_sudo.form_feedback(notification_data, 'birrlink')
                _logger.info("Successfully processed BirrLink notification for transaction %s", tx_sudo.reference)

            except ValidationError:
                _logger.exception("Unable to handle the notification data; skipping acknowledgment")

        _logger.info("Webhook processing completed")
        return ''

    def _verify_notification_signature(self, received_signature, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict received_signature: The signature received with the notification data.
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        # Check for the received signature.
        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature.
        expected_signature = tx_sudo.acquirer_id.birrlink_webhook_secret
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()

    @http.route('/payment/birrlink/s2s/create', type='json', auth='public', csrf=False)
    def birrlink_s2s_create(self, **kwargs):
        """ Create a new token from a payment request. """
        _logger.info("BirrLink S2S create request received with data: %s", pprint.pformat(kwargs))
        
        values = kwargs
        values['reference'] = request.env['payment.transaction'].get_next_reference(values['reference'])
        values['amount'] = float(values['amount'])
        values['currency_id'] = request.env['res.currency'].search([('name', '=', values['currency'])], limit=1).id

        tx = request.env['payment.transaction'].sudo().create(values)
        result = tx.birrlink_s2s_do_transaction()
        
        _logger.info("BirrLink S2S create completed, transaction ID: %s", tx.id)
        return tx.id

    @http.route('/payment/birrlink/redirect', type='http', auth='public', methods=['POST'])
    def birrlink_redirect(self, **post):
        """ Redirect to the BirrLink payment page. """
        _logger.info("BirrLink redirect request received with data: %s", pprint.pformat(post))
        
        acquirer_id = int(post.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        
        # Get transaction reference - use the one from post or generate a new one
        reference = post.get('reference') or post.get('tx_ref')
        if not reference or reference == '/':
            # Generate a proper reference if it's missing or invalid
            reference = 'BIRR%s' % str(int(time.time()))

        # Get currency
        currency_name = post.get('currency') or 'ETB'  # Default to ETB if not provided
        currency = request.env['res.currency'].search([('name', '=', currency_name)], limit=1)
        if not currency:
            # Try to get the default company currency as fallback
            currency = request.env.user.company_id.currency_id if hasattr(request.env.user, 'company_id') else None
            if not currency:
                # Fallback to USD if no currency found
                currency = request.env['res.currency'].search([('name', '=', 'USD')], limit=1)
                if not currency:
                    # If USD not found, use the first currency
                    currency = request.env['res.currency'].search([], limit=1)

        # Get partner data - try to use current user's partner if available
        partner_id = None
        if hasattr(request.env, 'user') and request.env.user and request.env.user.partner_id:
            partner_id = request.env.user.partner_id.id
            
        if not partner_id:
            # Try to get partner from post data
            partner_email = post.get('partner_email', '')
            partner_name = post.get('partner_name', 'Unknown')
            partner_phone = post.get('partner_phone', post.get('phone_number', ''))
            
            # Create or find partner based on email
            if partner_email:
                partner = request.env['res.partner'].search([('email', '=', partner_email)], limit=1)
                if partner:
                    partner_id = partner.id
                else:
                    # Create new partner
                    partner = request.env['res.partner'].create({
                        'name': partner_name,
                        'email': partner_email,
                        'phone': partner_phone,
                    })
                    partner_id = partner.id
            else:
                # Create partner without email
                partner = request.env['res.partner'].create({
                    'name': partner_name,
                    'phone': partner_phone,
                })
                partner_id = partner.id

        # Get transaction reference
        tx_values = {
            'acquirer_id': acquirer_id,
            'reference': reference,
            'amount': float(post.get('amount')),
            'currency_id': currency.id,
            'partner_id': partner_id,
            'partner_name': post.get('partner_name', ''),
            'partner_email': post.get('partner_email', ''),
            'partner_phone': post.get('partner_phone', post.get('phone_number', '')),
        }
        
        tx = request.env['payment.transaction'].create(tx_values)
        _logger.info("Created transaction with reference: %s", tx.reference)
        
        # Prepare the payment request to BirrLink.
        payload = {
            'order_id': tx.reference,
            'amount': tx.amount,
            'currency': tx.currency_id.name,
            "idempotency_key": str(tx.id),
            'phone_number': tx.validate_and_format_ethiopian_phone(tx.partner_phone),
            'title': tx.acquirer_id.company_id.name,
            'return_url': urls.url_join(request.httprequest.url_root, tx.acquirer_id.birrlink_return_url or self._default_return_url),
            'callback_url': urls.url_join(request.httprequest.url_root, tx.acquirer_id.birrlink_webhook_url or self._default_webhook_url),
        }
        
        _logger.info("Making payment request to BirrLink with payload: %s", pprint.pformat(payload))
        
        payment_link_data = acquirer._birrlink_make_request('/api/v1/payments', payload=payload)
        _logger.info("Received payment link from BirrLink: %s", payment_link_data.get('redirect_url', 'N/A'))
        
        # Redirect to the payment link
        _logger.info("Redirecting to payment link: %s", payment_link_data['redirect_url'])
        return werkzeug.utils.redirect(payment_link_data['redirect_url'])
