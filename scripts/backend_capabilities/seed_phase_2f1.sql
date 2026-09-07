SET LOCAL search_path = public, pg_catalog;

INSERT INTO loyalty_accounts (loyalty_account_id, customer_id, tier, points_balance, benefits, points_expire_at)
SELECT 'LOY-' || substr(md5(customer_id::text),1,12), customer_id,
       CASE abs(hashtext(customer_id::text)::bigint) % 3 WHEN 0 THEN 'MEMBER' WHEN 1 THEN 'SILVER' ELSE 'GOLD' END,
       abs(hashtext(customer_id::text)::bigint) % 5000,
       CASE abs(hashtext(customer_id::text)::bigint) % 3
         WHEN 0 THEN '["Demo member offers"]'::jsonb
         WHEN 1 THEN '["Demo member offers","Demo early access"]'::jsonb
         ELSE '["Demo member offers","Demo early access","Demo priority support"]'::jsonb END,
       TIMESTAMPTZ '2099-12-31T23:59:59Z'
FROM customers WHERE is_synthetic=true
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO promotions (promotion_code, display_name, status, starts_at, ends_at,
 minimum_spend, discount_type, discount_value, stacking_allowed)
VALUES
 ('DEMO10','Synthetic demo 10 percent','ACTIVE','2020-01-01Z','2099-12-31Z',50,'PERCENT',10,false),
 ('EXPIRED20','Expired synthetic demo','INACTIVE','2020-01-01Z','2021-01-01Z',0,'PERCENT',20,false),
 ('DEMO25','Synthetic demo minimum-spend offer','ACTIVE','2020-01-01Z','2099-12-31Z',200,'FIXED',25,false)
ON CONFLICT (promotion_code) DO NOTHING;
