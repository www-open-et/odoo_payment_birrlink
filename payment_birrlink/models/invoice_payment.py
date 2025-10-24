# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Developed by Fkadeal Matiwos
# GitHub: https://github.com/fkadeal
# Company: BirrLink Financial Technology
#

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def action_pay_with_birrlink(self):
        """Redirect to BirrLink payment for this invoice."""
        self.ensure_one()
        
        _logger.info("Pay with BirrLink button pressed for invoice: %s", self.number)
        
        # Check if invoice is in the right state for payment
        if self.state not in ['open']:
            error_msg = _("The invoice must be in 'Open' state to process payment.")
            _logger.warning("Invoice %s is not in 'open' state. Current state: %s", self.number, self.state)
            raise UserError(error_msg)
        
        _logger.info("Invoice %s is in valid state for payment processing", self.number)
        
        # Find BirrLink acquirer
        birrlink_acquirer = self.env['payment.acquirer'].search([('provider', '=', 'birrlink')], limit=1)
        if not birrlink_acquirer:
            error_msg = _("BirrLink payment acquirer is not configured.")
            _logger.error("No BirrLink acquirer found in the system")
            raise UserError(error_msg)
        
        _logger.info("Found BirrLink acquirer: %s", birrlink_acquirer.name)
        
        # Prepare transaction values
        tx_values = {
            'acquirer_id': birrlink_acquirer.id,
            'reference': self.number,  # Use invoice number as reference
            'amount': self.amount_total,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_name': self.partner_id.name,
            'partner_email': self.partner_id.email,
            'partner_phone': self.partner_id.phone or self.partner_id.mobile,
            'partner_address': self.partner_id.street,
            'partner_city': self.partner_id.city,
            'partner_zip': self.partner_id.zip,
            'partner_country_id': self.partner_id.country_id.id if self.partner_id.country_id else False,
        }
        
        _logger.info("Creating payment transaction with values: %s", tx_values)
        
        # Create payment transaction first
        tx = self.env['payment.transaction'].create(tx_values)
        _logger.info("Successfully created payment transaction with ID: %s and reference: %s", tx.id, tx.reference)
        
        # Link the transaction back to this invoice if possible
        # Note: In Odoo 10, we might need to set invoice_ids field if available
        if hasattr(tx, 'invoice_ids'):
            tx.write({'invoice_ids': [(6, 0, [self.id])]})
        
        # Prepare the payment request to BirrLink based on the model's method
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        _logger.info("Base URL for payment: %s", base_url)
        
        phone_number = tx.validate_and_format_ethiopian_phone(tx.partner_phone)
        if not phone_number:
            phone_number = '251911111111'  # Default fallback number
            _logger.info("Using default phone number as formatting failed")
        else:
            _logger.info("Formatted phone number: %s", phone_number)

        # Prepare payload exactly as in the controller
        payload = {
            'order_id': tx.reference,
            'amount': float(tx.amount),
            'currency': tx.currency_id.name,
            "idempotency_key": str(tx.id),
            'phone_number': phone_number,
            'title': tx.acquirer_id.company_id.name,
            'return_url': (tx.acquirer_id.birrlink_return_url if tx.acquirer_id.birrlink_return_url and tx.acquirer_id.birrlink_return_url.startswith('http') 
                          else base_url + (tx.acquirer_id.birrlink_return_url or '/payment/birrlink/return')),
            'callback_url': (tx.acquirer_id.birrlink_webhook_url if tx.acquirer_id.birrlink_webhook_url and tx.acquirer_id.birrlink_webhook_url.startswith('http') 
                            else base_url + (tx.acquirer_id.birrlink_webhook_url or '/payment/birrlink/webhook')),
        }
        
        _logger.info("Prepared BirrLink payment payload: %s", payload)
        
        # Make the payment request to BirrLink to get the actual checkout URL
        try:
            _logger.info("About to make API request to BirrLink with payload")
            payment_link_data = birrlink_acquirer._birrlink_make_request('/api/v1/payments', payload=payload)
            _logger.info("Received response from BirrLink API: %s", payment_link_data)
            
            redirect_url = payment_link_data.get('redirect_url')
            _logger.info("Extracted redirect URL from response: %s", redirect_url)
            
            if not redirect_url:
                error_msg = _("Could not get payment URL from BirrLink.")
                _logger.error("No redirect URL in BirrLink response: %s", payment_link_data)
                raise UserError(error_msg)
                
            _logger.info("Successfully processing payment, redirecting user to: %s", redirect_url)
            # Return an action that redirects to the actual BirrLink checkout page
            return {
                'type': 'ir.actions.act_url',
                'url': redirect_url,
                'target': 'self',
            }
        except Exception as e:
            error_msg = _("Error creating payment with BirrLink: %s") % str(e)
            _logger.error("Exception occurred while processing BirrLink payment: %s", str(e), exc_info=True)
            raise UserError(error_msg)

    def action_verify_birrlink_payment(self):
        """Verify payment status for this invoice."""
        self.ensure_one()
        
        _logger.info("Verify BirrLink payment button pressed for invoice: %s", self.number)
        
        # Find the transaction related to this invoice
        tx = self.env['payment.transaction'].search([
            ('reference', '=', self.number),
            ('acquirer_id.provider', '=', 'birrlink')
        ], limit=1)
        
        if not tx:
            error_msg = _("No BirrLink payment transaction found for this invoice.")
            _logger.warning("No BirrLink transaction found for invoice: %s", self.number)
            raise UserError(error_msg)
        
        _logger.info("Found transaction %s for invoice %s, proceeding to verify payment status", tx.id, self.number)
        
        # Verify payment status with BirrLink API
        try:
            payload = {"order_id": tx.reference}
            _logger.info("Making status verification request to BirrLink with payload: %s", payload)
            _logger.info("Using acquirer: %s with ID: %s", tx.acquirer_id.name, tx.acquirer_id.id)
            _logger.info("Acquirer provider: %s", tx.acquirer_id.provider)
            
            status_data = tx.acquirer_id._birrlink_make_request(
                '/api/v1/payments/status',
                payload=payload,
                method='GET'
            )
            
            _logger.info("Received status verification response from BirrLink: %s", status_data)
            
            # Update the transaction status based on response
            tx._birrlink_form_validate(status_data.get('data', status_data))
            _logger.info("Successfully updated transaction status for invoice %s", self.number)
            
            status = status_data.get('data', status_data).get('status', 'Unknown')
            _logger.info("Payment status for invoice %s: %s", self.number, status)
            
            # In Odoo 10, we can raise a UserError with info message or just return
            # For now, let's just return and show feedback in the form
            _logger.info("Payment verification completed for invoice %s with status: %s", self.number, status)
            return True
        except Exception as e:
            error_msg = _("Error verifying payment status: %s") % str(e)
            _logger.error("Exception occurred while verifying payment status for invoice %s: %s", self.number, str(e), exc_info=True)
            _logger.error("This may be due to network connectivity issues or BirrLink API being unavailable.")
            raise UserError(error_msg)