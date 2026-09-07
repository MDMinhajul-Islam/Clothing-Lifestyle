-- Phase 2F.1: private synthetic retail capability state.
SET LOCAL search_path = public, pg_catalog;

CREATE TABLE IF NOT EXISTS customer_auth_sessions (
    auth_session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash TEXT UNIQUE NOT NULL CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    customer_id UUID REFERENCES customers(customer_id) ON DELETE CASCADE,
    order_id TEXT REFERENCES orders(order_id) ON DELETE CASCADE,
    auth_level TEXT NOT NULL CHECK (auth_level IN ('ORDER_VERIFIED','TRANSACTION_VERIFIED')),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    data_origin TEXT NOT NULL DEFAULT 'synthetic_operational_layer',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((auth_level='TRANSACTION_VERIFIED' AND customer_id IS NOT NULL) OR
           (auth_level='ORDER_VERIFIED' AND order_id IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS loyalty_accounts (
    loyalty_account_id TEXT PRIMARY KEY,
    customer_id UUID UNIQUE NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('MEMBER','SILVER','GOLD')),
    points_balance INTEGER NOT NULL CHECK (points_balance >= 0),
    benefits JSONB NOT NULL DEFAULT '[]'::jsonb,
    points_expire_at TIMESTAMPTZ,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    data_origin TEXT NOT NULL DEFAULT 'synthetic_operational_layer',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS promotions (
    promotion_code TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','INACTIVE')),
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    minimum_spend NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (minimum_spend >= 0),
    discount_type TEXT NOT NULL CHECK (discount_type IN ('PERCENT','FIXED')),
    discount_value NUMERIC(12,2) NOT NULL CHECK (discount_value > 0),
    eligible_product_ids TEXT[],
    stacking_allowed BOOLEAN NOT NULL DEFAULT false,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    data_origin TEXT NOT NULL DEFAULT 'synthetic_operational_layer',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (ends_at > starts_at)
);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE RESTRICT,
    order_item_id TEXT NOT NULL REFERENCES order_items(order_item_id) ON DELETE RESTRICT,
    issue_type TEXT NOT NULL CHECK (issue_type IN
        ('MISSING_ITEM','WRONG_ITEM','DAMAGED_ITEM','DEFECTIVE_ITEM','DELIVERED_NOT_RECEIVED')),
    factual_summary TEXT NOT NULL,
    incident_status TEXT NOT NULL DEFAULT 'OPEN',
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    data_origin TEXT NOT NULL DEFAULT 'synthetic_operational_layer',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS support_cases (
    case_id TEXT PRIMARY KEY,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    order_id TEXT REFERENCES orders(order_id) ON DELETE SET NULL,
    product_id TEXT REFERENCES products(product_id) ON DELETE SET NULL,
    issue_category TEXT NOT NULL,
    requested_outcome TEXT,
    factual_summary TEXT NOT NULL,
    verified_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
    attempted_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    tool_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    case_status TEXT NOT NULL DEFAULT 'OPEN',
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    data_origin TEXT NOT NULL DEFAULT 'synthetic_operational_layer',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_session_token ON customer_auth_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_auth_session_customer ON customer_auth_sessions(customer_id);
CREATE INDEX IF NOT EXISTS idx_incidents_order ON incidents(order_id);
CREATE INDEX IF NOT EXISTS idx_support_cases_customer ON support_cases(customer_id);

ALTER TABLE customer_auth_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE loyalty_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE promotions ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_cases ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON customer_auth_sessions, loyalty_accounts, promotions, incidents, support_cases FROM PUBLIC;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
        REVOKE ALL ON customer_auth_sessions, loyalty_accounts, promotions, incidents, support_cases FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
        REVOKE ALL ON customer_auth_sessions, loyalty_accounts, promotions, incidents, support_cases FROM authenticated;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role') THEN
        GRANT SELECT, INSERT, UPDATE ON customer_auth_sessions, loyalty_accounts, promotions, incidents, support_cases TO service_role;
    END IF;
END $$;
