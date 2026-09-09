-- Commerce MVP: unpaid order requests and compatible notification history.
ALTER TABLE orders DROP CONSTRAINT IF EXISTS check_order_status;
ALTER TABLE orders ADD CONSTRAINT check_order_status CHECK (order_status IN
 ('PENDING','PENDING_PAYMENT','CONFIRMED','PROCESSING','SHIPPED','DELIVERED','CANCELLED',
  'RETURN_REQUESTED','PARTIALLY_RETURNED','RETURNED','REFUNDED'));

DO $$ BEGIN
  IF to_regclass('public.notification_history') IS NOT NULL THEN
    ALTER TABLE notification_history DROP CONSTRAINT IF EXISTS notification_history_order_id_fkey;
    ALTER TABLE notification_history ALTER COLUMN order_id TYPE TEXT USING order_id::text;
    ALTER TABLE notification_history ADD CONSTRAINT notification_history_order_id_fkey
      FOREIGN KEY(order_id) REFERENCES orders(order_id) ON DELETE CASCADE;
  ELSE
    CREATE TABLE notification_history (
      notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
      event_type TEXT NOT NULL, channel TEXT NOT NULL DEFAULT 'EMAIL', provider TEXT NOT NULL,
      recipient_hash TEXT NOT NULL, delivery_status TEXT NOT NULL DEFAULT 'PENDING',
      provider_message_id TEXT, failure_code TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      sent_at TIMESTAMPTZ, delivered_at TIMESTAMPTZ);
  END IF;
END $$;
ALTER TABLE notification_history ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON notification_history FROM PUBLIC;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN REVOKE ALL ON notification_history FROM anon; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN REVOKE ALL ON notification_history FROM authenticated; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role') THEN
    GRANT SELECT, INSERT, UPDATE ON notification_history TO service_role;
  END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(order_status,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_cases_category_created ON support_cases(issue_category,created_at DESC);
