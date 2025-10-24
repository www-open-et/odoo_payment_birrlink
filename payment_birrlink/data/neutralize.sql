-- disable birrlink payment acquirer
UPDATE payment_acquirer
   SET birrlink_public_key = NULL,
       birrlink_secret_key = NULL,
       birrlink_webhook_secret = NULL;
