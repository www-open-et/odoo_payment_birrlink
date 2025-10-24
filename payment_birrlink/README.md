# BirrLink Payment Gateway Integration

## Overview

This module integrates BirrLink payment gateway with Odoo ERP system, providing seamless payment processing capabilities for businesses operating in Ethiopia and the African region. The module implements a secure and efficient payment flow that allows customers to make payments through the BirrLink platform.

### Developed by

- **Developer**: Fkadeal Matiwos
- **GitHub**: [https://github.com/fkadeal](https://github.com/fkadeal)
- **Company**: BirrLink Financial Technology

## Technical Details

- **API**: [BirrLink Standard API](https://docs.birrlink.et/)
- **Version**: `3`
- **Integration Method**: Generic payment with redirection flow based on form submission
- **Framework**: Built using Odoo's `payment` module infrastructure

## Supported Features

- **Payment with Redirection Flow**: Secure redirect to BirrLink payment page for transaction processing
- **Webhook Notifications**: Automatic payment status updates via webhook notifications
- **Tokenization**: Secure storage of payment tokens for recurring transactions
- **Invoice Integration**: Direct payment processing from invoice forms
- **Payment Verification**: Real-time payment status verification functionality
- **Multiple Currency Support**: Supports various currencies ETB for current version.

## Installation

1. Copy the `payment_birrlink` module to your Odoo `custom_addons` directory
2. Update your Odoo application list
3. Install the module from the Apps menu
4. Configure the payment acquirer with your BirrLink credentials

## Configuration

1. Go to **Website > Configuration > Payment Acquirers**
2. Find and configure the **BirrLink** payment acquirer with:
   - Public Key
   - Secret Key
   - Webhook Secret
   - Return URLs
   - webhook URLs

## Testing Instructions

For testing purposes, use the following test credentials:

### Test with wallet

**TeleBirr**

- phone Number: `251 932970631`
- OTP: `12345`

### Test Process

1. Create an invoice or sales order
2. Click "Pay with BirrLink" button
3. Complete the test payment using provided credentials
4. Verify payment status

## API Endpoints

The module implements the following endpoints:

- `/payment/birrlink/return` - Payment return URL
- `/payment/birrlink/auth_return` - Authorization return URL
- `/payment/birrlink/webhook` - Webhook notifications
- `/payment/birrlink/redirect` - Payment redirect
- `/payment/birrlink/s2s/create` - Server-to-server payment creation

## Security Features

- Secure tokenization of payment information
- Protected webhook endpoints with signature verification
- Encrypted storage of sensitive credentials
- CSRF protection for payment forms

## Invoice Integration

The module adds two buttons to invoice forms:

- **Pay with BirrLink**: Redirect to BirrLink payment page
- **Verify Payment**: Check payment status with BirrLink API

## Code Documentation

All code files include comprehensive headers with:

- Developer information
- Company details
- GitHub profile link
- File description and purpose

## License

This module is released under the LGPL-3 license. See the LICENSE file for more details.

## Support

For support and inquiries, please contact BirrLink Financial Technology
