# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Developed by Fkadeal Matiwos
# GitHub: https://github.com/fkadeal
# Company: BirrLink Financial Technology
#

import logging
import pprint
import re
from werkzeug import urls
import uuid
from odoo import _, models
from odoo.exceptions import UserError, ValidationError

from .. import const
from ..controllers.main import BirrlinkController


_logger = logging.getLogger(__name__)


# Define helper functions since payment_utils don't exist in Odoo 10
def split_partner_name(partner_name):
    """Split partner name into first and last name."""
    if not partner_name:
        return '', ''
    name_parts = partner_name.split(' ', 1)
    if len(name_parts) == 1:
        return name_parts[0], ''
    return name_parts[0], name_parts[1]


def get_customer_ip_address():
    """Get customer IP address from request."""
    from odoo.http import request
    forwarded_for = request.httprequest.headers.environ.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0]
    return request.httprequest.remote_addr


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _birrlink_form_get_tx_from_data(self, data):
        """ Given a data dict coming from BirrLink, verify it and find the related
        transaction. This method is used by the form_feedback method in the controller.

        :param dict data: The data from BirrLink
        :return: Recordset of the transaction if found
        :raise: ValidationError if the data is inconsistent
        """
        reference = data.get('tx_ref') or data.get('order_id')
        if not reference:
            raise ValidationError("BirrLink: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference), ('acquirer_id.provider', '=', 'birrlink')])
        if not tx:
            raise ValidationError(
                "BirrLink: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _birrlink_form_get_invalid_parameters(self, data):
        """ Compare the data and the transaction, to check if the data comes from
        BirrLink. This method is used by the form_feedback method in the controller.

        :param dict data: The data from BirrLink
        :return: List of invalid parameters, if any
        """
        invalid_parameters = []

        # Check what you need to validate based on your requirements
        # For example, check amount, currency, etc.
        return invalid_parameters

    def _birrlink_form_validate(self, data):
        """ Verify that the given values are correct and update the transaction state.
        This method is used by the form_feedback method in the controller.

        :param dict data: The data from BirrLink
        :return: True if the transaction is validated, False otherwise
        """
        _logger.info("BirrLink validation request received with data: %s", pprint.pformat(data))
        
        if self.state == 'done':
            _logger.info('BirrLink: Already validated tx %s', self.reference)
            # Even if already validated, we should still try to update invoice status
            # in case it wasn't properly linked before
            self._update_invoice_status_from_transaction()
            return True
        
        # Verify the transaction with BirrLink API
        tx_ref = data.get('order_id') or data.get('tx_ref') or self.reference
        _logger.info("Initiating status verification for transaction: %s", tx_ref)
        
        verification_response_content = self.acquirer_id._birrlink_make_request(
            '/api/v1/payments/status',
            payload={"order_id": tx_ref},
            method='GET'
        )

        _logger.info("BirrLink verification response for %s: %s", tx_ref, verification_response_content)

        verified_data = verification_response_content.get('data', verification_response_content)
        if not verified_data.get('status'):
            raise ValidationError(_("Invalid verification response: missing 'status' field."))

        # Update acquirer reference
        acquirer_reference = (
            verified_data.get('id')
            or verified_data.get('payment_id')
            or verified_data.get('order_id')
            or self.acquirer_reference
        )
        
        # Update the transaction reference in the system
        self.write({
            'acquirer_reference': acquirer_reference
        })

        # Normalize payment status
        payment_status = (
            verified_data.get('status_detail')
            or verified_data.get('status')
            or ''
        ).lower()

        _logger.info("Payment status for %s: %s", tx_ref, payment_status)

        # Map payment states
        if payment_status in const.PAYMENT_STATUS_MAPPING['pending']:
            self.write({
                'state': 'pending',
                'state_message': 'Payment is pending'
            })
            _logger.info("Transaction %s marked as pending", self.reference)

        elif payment_status in const.PAYMENT_STATUS_MAPPING['done'] or payment_status == 'completed':
            self.write({
                'state': 'done',
                'state_message': 'Payment completed successfully'
            })
            _logger.info("BirrLink transaction marked as done: %s", self.reference)

            # Update invoice status for completed transactions
            self._update_invoice_status_from_transaction()

        elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
            self.write({
                'state': 'cancel',
                'state_message': 'Payment was cancelled'
            })
            _logger.info("Transaction %s marked as cancelled", self.reference)

        elif payment_status in const.PAYMENT_STATUS_MAPPING['error']:
            self.write({
                'state': 'error',
                'state_message': _("An error occurred during the processing of your payment (status %s). Please try again.",
                                  payment_status)
            })
            _logger.error("Transaction %s marked as error with status: %s", self.reference, payment_status)

        else:
            _logger.warning(
                "BirrLink: Unknown payment status (%s) for transaction reference %s. Response: %s",
                payment_status, self.reference, verified_data
            )
            self.write({
                'state': 'error',
                'state_message': _("Unknown payment status: %s") % payment_status
            })
        
        _logger.info("BirrLink validation completed for transaction: %s", self.reference)
        return True

    def birrlink_get_form_action_url(self):
        """ Generates the form action URL for BirrLink redirect.
        """
        return '%s/payment/birrlink/redirect' % (self.env['ir.config_parameter'].sudo().get_param('web.base.url'))

    def birrlink_form_generate_values(self, values):
        """ Generate the values used to render the form button template.
        """
        _logger.info("Generating BirrLink form values with input: %s", pprint.pformat(values))
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        phone_number = self.validate_and_format_ethiopian_phone(values.get('partner_phone', ''))
        if not phone_number:
            phone_number = '251911111111'  # Default fallback number

        birrlink_tx_values = dict(values)
        birrlink_tx_values.update({
            'tx_ref': values.get('reference'),
            'amount': float(values.get('amount')),
            'currency': values.get('currency'),
            'idempotency_key': str(uuid.uuid4()),
            'phone_number': phone_number,
            'title': self.acquirer_id.company_id.name,
            'return_url': urls.url_join(base_url, self.acquirer_id.birrlink_return_url or BirrlinkController._default_return_url),
            'callback_url': urls.url_join(base_url, self.acquirer_id.birrlink_webhook_url or BirrlinkController._default_webhook_url),
        })
        
        _logger.info("Generated BirrLink form values: %s", pprint.pformat(birrlink_tx_values))
        return birrlink_tx_values

    def birrlink_s2s_do_transaction(self, **kwargs):
        """ Create a payment transaction for a specific payment token.
        Note: self.ensure_one()
        """
        self.ensure_one()
        if not self.payment_token_id:
            raise UserError("BirrLink: " + _("The transaction is not linked to a token."))

        _logger.info("Starting BirrLink S2S transaction for reference: %s", self.reference)
        
        first_name, last_name = split_partner_name(self.partner_name)
        base_url = self.acquirer_id.get_base_url()
        data = {
            'token': self.payment_token_id.acquirer_ref,
            'email': self.payment_token_id.birrlink_customer_email,
            'amount': self.amount,
            'currency': "ETB",  # TODO: self.currency_id.name,
            'country': self.acquirer_id.company_id.country_id.code,
            'tx_ref': self.reference,
            'first_name': first_name,
            'last_name': last_name,
            'ip': get_customer_ip_address(),
            'redirect_url': urls.url_join(base_url, self.acquirer_id.birrlink_auth_return_url or BirrlinkController._default_auth_return_url),
        }

        # Make the payment request to BirrLink.
        _logger.info("Making S2S payment request to BirrLink with data: %s", pprint.pformat(data))
        response_content = self.acquirer_id._birrlink_make_request(
            'api/v1/payments', payload=data
        )

        # Handle the payment request response.
        _logger.info(
            "S2S payment request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )
        # For Odoo 10, we call the form validate method which will update transaction state
        self._birrlink_form_validate(response_content.get('data', response_content))
        _logger.info("S2S transaction completed for reference: %s", self.reference)
        return self

    def _birrlink_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        """
        self.ensure_one()

        token = self.env['payment.token'].create({
            'acquirer_id': self.acquirer_id.id,
            'acquirer_ref': notification_data.get('card', {}).get('token'),
            'name': notification_data.get('card', {}).get('last_4digits', ''),
            'partner_id': self.partner_id.id,
            'birrlink_customer_email': notification_data.get('customer', {}).get('email'),
        })
        self.write({
            'payment_token_id': token,
        })
        _logger.info(
            "created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {
                'token_id': token.id,
                'partner_id': self.partner_id.id,
                'ref': self.reference,
            },
        )

    def validate_and_format_ethiopian_phone(self, phone_number):
        # Remove all spaces or dashes
        if not phone_number:
            return None
        phone_number = phone_number.strip().replace(" ", "").replace("-", "")
        
        # Case 1: Starts with '+'
        if phone_number.startswith("+"):
            phone_number = phone_number[1:]

        # Case 2: Starts with '07' or '09'
        if phone_number.startswith("07") or phone_number.startswith("09"):
            phone_number = "251" + phone_number[1:]

        # Case 3: Already in correct format '251...'
        elif phone_number.startswith("251"):
            pass
        else:
            return None  # Invalid prefix

        # Validate: must be exactly 12 digits and all numeric
        if re.match(r"^251\d{9}$", phone_number):
            return phone_number
        else:
            return None  # Invalid format or length

    def _update_invoice_status_from_transaction(self):
        """Update invoice status based on this transaction."""
        # First try direct match with reference
        invoices = self.env['account.invoice'].search([
            ('number', '=', self.reference)
        ])
        
        # If not found, try splitting the reference
        if not invoices:
            base_ref = self.reference.split('-')[0]  # e.g., "INV/2025/00009"
            invoices = self.env['account.invoice'].search([
                ('number', '=', base_ref)
            ])

        if not invoices:
            _logger.warning("No invoice found for reference: %s (or base: %s)", self.reference, self.reference.split('-')[0])
            
            # If there's no direct invoice match, check if this transaction has a related invoice set as metadata
            # We'll try to find if the transaction was created from an invoice by checking other fields
            # Look for invoices associated with this transaction's partner that are still open and match the amount
            invoices = self.env['account.invoice'].search([
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'open'),
                ('amount_total', '=', self.amount),
                ('residual', '>', 0),  # Has outstanding balance
            ], limit=5)  # Limit to prevent too many invoices being affected
            
            if invoices:
                _logger.info("Found %d potential matching invoices based on partner and amount for transaction %s", len(invoices), self.reference)
            else:
                _logger.warning("No matching invoices found for transaction %s based on partner and amount", self.reference)

        for invoice in invoices:
            if invoice.state in ['open']:  # In Odoo 10, 'open' is the state for posted invoices waiting payment
                # Check if the transaction amount matches or is less than the invoice residual
                payment_amount = min(self.amount, invoice.residual)  # Don't overpay
                if payment_amount > 0:
                    # Create payment record
                    payment_method = self.env['account.payment.method'].search([
                        ('payment_type', '=', 'inbound')
                    ], limit=1)
                    
                    if not payment_method:
                        # Search for a default inbound payment method if none found
                        payment_method = self.env['account.payment.method'].search([
                            ('code', '=', 'manual'),
                            ('payment_type', '=', 'inbound')
                        ], limit=1)
                    
                    bank_journal = self.env['account.journal'].search([
                        ('type', '=', 'bank')
                    ], limit=1)

                    if not bank_journal:
                        # Use cash journal as fallback if no bank journal found
                        bank_journal = self.env['account.journal'].search([
                            ('type', 'in', ['bank', 'cash'])
                        ], limit=1)

                    if not bank_journal:
                        # Further fallback: try to find any journal that can handle payments
                        bank_journal = self.env['account.journal'].search([
                            ('type', 'in', ['bank', 'cash', 'general']),
                            ('company_id', '=', self.env.user.company_id.id)
                        ], limit=1)

                    if not bank_journal:
                        # Last resort: try to find any available journal
                        bank_journal = self.env['account.journal'].search([], limit=1)

                    if not bank_journal:
                        _logger.warning("No bank/cash journal found - invoice not marked as paid.")
                        continue

                    # Create the payment
                    payment_vals = {
                        'payment_type': 'inbound',
                        'payment_method_id': payment_method.id if payment_method else False,
                        'partner_type': 'customer',
                        'partner_id': invoice.partner_id.id,
                        'amount': payment_amount,
                        'currency_id': invoice.currency_id.id,
                        'invoice_ids': [(6, 0, invoice.ids)],
                        'journal_id': bank_journal.id,
                        'communication': '%s (BirrLink)' % self.reference,
                    }
                    payment = self.env['account.payment'].create(payment_vals)
                    payment.post()  # In Odoo 10, use post() to validate the payment
                    _logger.info("Invoice %s marked as Paid via BirrLink transaction %s", invoice.number, self.reference)
                else:
                    _logger.info("Invoice %s residual (%s) does not require payment of %s", invoice.number, invoice.residual, self.amount)
            else:
                _logger.info("Invoice %s is already in state %s, not processing payment", invoice.number, invoice.state)