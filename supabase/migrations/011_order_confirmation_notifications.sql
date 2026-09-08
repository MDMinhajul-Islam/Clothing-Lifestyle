-- Secure order confirmation lifecycle and provider-neutral email delivery history.
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS confirmation_token_hash TEXT,
    ADD COLUMN IF NOT EXISTS confirmation_token_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS confirmation_sent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS email_sent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS email_delivery_status TEXT;

CREATE TABLE IF NOT EXISTS notification_history (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'EMAIL',
    provider TEXT NOT NULL,
    recipient_hash TEXT NOT NULL,
    delivery_status TEXT NOT NULL DEFAULT 'PENDING',
    provider_message_id TEXT,
    failure_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_notification_history_order_created
    ON notification_history(order_id, created_at DESC);

ALTER TABLE notification_history ENABLE ROW LEVEL SECURITY;
