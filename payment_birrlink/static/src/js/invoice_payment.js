/**
 * BirrLink Payment Module for Odoo
 * 
 * Developed by Fkadeal Matiwos
 * GitHub: https://github.com/fkadeal
 * Company: BirrLink Financial Technology
 */

// JavaScript to handle BirrLink payment for invoices
odoo.define('payment_birrlink.invoice_payment', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var session = require('web.session');

    var QWeb = core.qweb;

    var BirrlinkInvoicePayment = AbstractAction.extend({
        events: {
            'click .o_birrlink_pay_button': 'pay_with_birrlink',
        },

        init: function(parent, action) {
            this._super.apply(this, arguments);
            this.invoice_id = action.invoice_id;
        },

        start: function() {
            var self = this;
            // Render the payment form
            this.$el.html(QWeb.render("BirrlinkInvoicePayment", {
                'invoice_id': this.invoice_id
            }));
            
            // Auto-submit the form to BirrLink redirect endpoint
            this.$el.find('#birrlink_payment_form').submit();
        },

        pay_with_birrlink: function(e) {
            e.preventDefault();
            var self = this;
            
            // Create payment transaction and redirect
            this._rpc({
                model: 'account.invoice',
                method: 'action_pay_with_birrlink',
                args: [this.invoice_id],
            }).then(function(result) {
                if (result && result.url) {
                    window.location.href = result.url;
                }
            });
        }
    });

    core.action_registry.add('birrlink_invoice_payment', BirrlinkInvoicePayment);

    return BirrlinkInvoicePayment;
});