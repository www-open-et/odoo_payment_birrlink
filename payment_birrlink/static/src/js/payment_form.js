/**
 * BirrLink Payment Form Module for Odoo
 * 
 * Developed by Fkadeal Matiwos
 * GitHub: https://github.com/fkadeal
 * Company: BirrLink Financial Technology
 */

odoo.define('payment_birrlink.payment_form', function (require) {
    'use strict';

    var payment = require('payment.payment_form');
    var ajax = require('web.ajax');
    var core = require('web.core');

    payment.renderPaymentButton = payment.renderPaymentButton || {};

    payment.renderPaymentButton.birrlink = function (acquirer_id, payment_method, type, no_tokenize, form_error_callback, customer_values) {
        // For BirrLink, we need to render a hidden form that will be submitted automatically
        var deferred = $.Deferred();
        
        // Create a form dynamically and submit it
        var $form = $('<form>', {
            action: '/payment/birrlink/redirect',
            method: 'POST',
            style: 'display:none;'
        });
        
        // Add CSRF token
        $form.append($('<input>', {
            type: 'hidden',
            name: 'csrf_token',
            value: core.csrf_token
        }));
        
        // Add form fields that will be populated during checkout
        $form.append($('<input>', { name: 'acquirer_id', type: 'hidden' }));
        $form.append($('<input>', { name: 'reference', type: 'hidden' }));
        $form.append($('<input>', { name: 'amount', type: 'hidden' }));
        $form.append($('<input>', { name: 'currency', type: 'hidden' }));
        $form.append($('<input>', { name: 'partner_name', type: 'hidden' }));
        $form.append($('<input>', { name: 'partner_email', type: 'hidden' }));
        $form.append($('<input>', { name: 'partner_phone', type: 'hidden' }));
        
        $('body').append($form);
        
        // Submit the form when payment is processed
        payment.current_aquirer = acquirer_id;
        deferred.resolve($form);
        
        return deferred;
    };
    
    // Store original function
    var _processPayment = payment.TransactionForm.prototype._processPayment;
    
    payment.TransactionForm.prototype._processPayment = function (provider, acquirer_id, type, no_tokenize, form_error_callback, customer_values) {
        if (provider === 'birrlink') {
            var self = this;
            var def = $.Deferred();
            
            // Process payment data using the standard Odoo method
            this._getPartnerId().then(function(partner_id) {
                var payment_data = {
                    acquirer_id: acquirer_id,
                    partner_id: partner_id,
                };
                
                if (type === 'form_save') {
                    payment_data.type = 'form_save';
                }
                
                return ajax.jsonRpc('/payment/process', 'call', payment_data);
            }).then(function(result) {
                // Handle the result - if it's a redirect URL, redirect immediately
                if (result.redirect) {
                    window.location.href = result.redirect;
                } else if (result.html) {
                    // Process the form HTML and submit it
                    var $form = $(result.html);
                    $('body').append($form);
                    $form.submit();
                } else {
                    def.resolve();
                }
            }).fail(function(error) {
                console.error('Payment processing error:', error);
                if (form_error_callback) {
                    form_error_callback(error);
                }
                def.reject(error);
            });
            
            return def;
        } else {
            // For other providers, use the default behavior
            return _processPayment.apply(this, arguments);
        }
    };

    return payment;
});