-- Customer Portal credentials and sessions. The existing customers table remains canonical.
CREATE TABLE IF NOT EXISTS customer_credentials (
    customer_id UUID PRIMARY KEY REFERENCES customers(customer_id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL CHECK (password_hash LIKE '$argon2id$%'),
    email_verified_at TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    failed_login_count INTEGER NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0),
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customer_portal_tokens (
    token_hash TEXT PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK (purpose IN ('VERIFY_EMAIL','RESET_PASSWORD')),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customer_portal_sessions (
    token_hash TEXT PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_portal_tokens_customer ON customer_portal_tokens(customer_id,purpose);
CREATE INDEX IF NOT EXISTS idx_portal_sessions_customer ON customer_portal_sessions(customer_id);

ALTER TABLE customer_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_portal_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_portal_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON customer_credentials,customer_portal_tokens,customer_portal_sessions FROM PUBLIC;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
    REVOKE ALL ON customer_credentials,customer_portal_tokens,customer_portal_sessions FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
    REVOKE ALL ON customer_credentials,customer_portal_tokens,customer_portal_sessions FROM authenticated;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role') THEN
    GRANT SELECT,INSERT,UPDATE,DELETE ON customer_credentials,customer_portal_tokens,customer_portal_sessions TO service_role;
  END IF;
END $$;

-- One verified synthetic acceptance account, linked to the canonical customer profile.
INSERT INTO customers(customer_id,first_name,last_name,email,phone,country_code,state,city,
                      account_status,is_synthetic,data_origin)
VALUES('00000000-0000-4000-8000-000000000013','Jess','Carter','jess.carter@nexgen.test',
       '+15550100113','US','NY','New York','ACTIVE',true,'acceptance_test')
ON CONFLICT(email) DO NOTHING;

INSERT INTO customer_addresses(address_id,customer_id,recipient_name,address_line_1,city,state,
                               postal_code,country_code,is_default_shipping,is_default_billing,is_synthetic)
SELECT '00000000-0000-4000-8000-000000000113',customer_id,'Jess Carter','13 Mercer Street',
       'New York','NY','10013','US',true,true,true
FROM customers WHERE lower(email)='jess.carter@nexgen.test'
ON CONFLICT(address_id) DO NOTHING;

INSERT INTO customer_credentials(customer_id,password_hash,email_verified_at)
SELECT customer_id,'$argon2id$v=19$m=65536,t=3,p=4$2STGSgSxeEprO2jZft9RaA$TfnRVqZfwxWL9dR9zAqSW1WJUjp1ZUvNVqOlxKDyZVE',now()
FROM customers WHERE lower(email)='jess.carter@nexgen.test'
ON CONFLICT(customer_id) DO NOTHING;

-- A historical paid order gives the acceptance account a safe tracking/exchange/refund fixture.
INSERT INTO orders(order_id,order_number,customer_id,order_status,shipping_address_id,currency,
                   subtotal,grand_total,payment_status,placed_at,confirmed_at,completed_at,is_synthetic,data_origin)
SELECT 'ACCEPT-ORDER-013','NGR-ACCEPT-013',c.customer_id,'DELIVERED',a.address_id,p.currency,
       p.current_price,p.current_price,'PAID',now()-interval '10 days',now()-interval '10 days',
       now()-interval '3 days',true,'acceptance_test'
FROM customers c JOIN customer_addresses a ON a.customer_id=c.customer_id AND a.is_default_shipping
CROSS JOIN LATERAL (SELECT current_price,currency FROM products WHERE lifecycle_status='ACTIVE' ORDER BY product_id LIMIT 1) p
WHERE lower(c.email)='jess.carter@nexgen.test'
ON CONFLICT(order_id) DO NOTHING;

INSERT INTO order_items(order_item_id,order_id,product_id,variant_id,quantity,unit_price,line_total,
                        product_name_snapshot,size_snapshot,color_snapshot,is_synthetic)
SELECT 'ACCEPT-ITEM-013','ACCEPT-ORDER-013',p.product_id,v.variant_id,1,p.current_price,p.current_price,
       p.exact_product_name,v.size_name,v.color_name,true
FROM products p JOIN LATERAL (SELECT * FROM product_variants WHERE product_id=p.product_id ORDER BY variant_id LIMIT 1) v ON true
WHERE p.lifecycle_status='ACTIVE' ORDER BY p.product_id LIMIT 1
ON CONFLICT(order_item_id) DO NOTHING;

INSERT INTO payments(payment_id,order_id,payment_method,payment_status,amount,currency,provider_reference,
                     authorized_at,captured_at,is_synthetic)
SELECT 'ACCEPT-PAYMENT-013','ACCEPT-ORDER-013','TEST','PAID',grand_total,currency,'acceptance-test',
       placed_at,placed_at,true FROM orders WHERE order_id='ACCEPT-ORDER-013'
ON CONFLICT(payment_id) DO NOTHING;

INSERT INTO shipments(shipment_id,order_id,carrier,tracking_number,shipment_status,shipped_at,
                      estimated_delivery_at,delivered_at,is_synthetic)
SELECT 'ACCEPT-SHIPMENT-013','ACCEPT-ORDER-013','NexGen Test Carrier','NGRTEST000013','DELIVERED',
       now()-interval '8 days',now()-interval '4 days',now()-interval '3 days',true
WHERE EXISTS(SELECT 1 FROM orders WHERE order_id='ACCEPT-ORDER-013')
ON CONFLICT(shipment_id) DO NOTHING;
