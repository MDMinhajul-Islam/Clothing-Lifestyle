-- ============================================================================
-- Migration: 006_operational_rls.sql
-- Description: Row Level Security for Synthetic Retail Operational Layer.
-- Rules:
--   - stores: Public SELECT allowed (Store locator).
--   - inventory_levels: Public SELECT allowed (Product page inventory check).
--   - customers, orders, payments, shipments, returns, refunds:
--     Restricted to backend service_role. No unrestricted anonymous access.
-- ============================================================================

-- 1. ENABLE RLS ACROSS ALL 13 OPERATIONAL TABLES
ALTER TABLE stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipment_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE returns ENABLE ROW LEVEL SECURITY;
ALTER TABLE return_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE refunds ENABLE ROW LEVEL SECURITY;
ALTER TABLE exchanges ENABLE ROW LEVEL SECURITY;

-- 2. PUBLIC READ ACCESS FOR SHOPPING UTILITY TABLES
DROP POLICY IF EXISTS "Public read access for stores" ON stores;
CREATE POLICY "Public read access for stores"
    ON stores FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Public read access for inventory_levels" ON inventory_levels;
CREATE POLICY "Public read access for inventory_levels"
    ON inventory_levels FOR SELECT
    USING (true);

-- 3. CUSTOMER / ORDER / PAYMENT TABLES
-- No public anonymous access. Backend / service_role bypasses RLS for operations.
