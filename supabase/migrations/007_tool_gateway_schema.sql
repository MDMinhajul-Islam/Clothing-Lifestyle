-- ============================================================================
-- Migration: 007_tool_gateway_schema.sql
-- Description: AI Tool Gateway Idempotency and Audit Logging Tables (Phase 2C).
-- Protects write operations against replay attacks and records execution history.
-- ============================================================================

-- 1. TOOL IDEMPOTENCY KEYS TABLE
CREATE TABLE IF NOT EXISTS tool_idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_json JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tool_idempotency_tool ON tool_idempotency_keys(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_idempotency_created_at ON tool_idempotency_keys(created_at DESC);

-- 2. TOOL AUDIT LOG TABLE
CREATE TABLE IF NOT EXISTS tool_audit_log (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name TEXT NOT NULL,
    request_id TEXT NOT NULL,
    customer_id UUID,
    order_id TEXT,
    request_summary JSONB NOT NULL,
    result_status TEXT NOT NULL,
    error_code TEXT,
    idempotency_key TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    duration_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tool_audit_tool_name ON tool_audit_log(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_audit_order_id ON tool_audit_log(order_id);
CREATE INDEX IF NOT EXISTS idx_tool_audit_customer_id ON tool_audit_log(customer_id);
CREATE INDEX IF NOT EXISTS idx_tool_audit_executed_at ON tool_audit_log(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_audit_request_id ON tool_audit_log(request_id);

-- 3. ROW-LEVEL SECURITY (SERVICE-ROLE ONLY)
ALTER TABLE tool_idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_audit_log ENABLE ROW LEVEL SECURITY;

-- Anonymous users cannot read or write to gateway internal tables
DROP POLICY IF EXISTS tool_idempotency_service_policy ON tool_idempotency_keys;
DROP POLICY IF EXISTS tool_audit_log_service_policy ON tool_audit_log;

