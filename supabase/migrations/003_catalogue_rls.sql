-- ============================================================================
-- Migration: 003_catalogue_rls.sql
-- Description: Supabase Row Level Security (RLS) policies for Zara US catalogue.
-- Rules:
--   - Public read access enabled for catalogue browsing tables.
--   - Mutations restricted to backend service_role (bypasses RLS).
--   - Internal sync state protected from unrestricted public access.
-- ============================================================================

-- 1. ENABLE RLS ON ALL TABLES
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_colors ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalogue_sync_state ENABLE ROW LEVEL SECURITY;

-- 2. PUBLIC READ ACCESS POLICIES (ANONYMOUS & AUTHENTICATED SELECT)
DROP POLICY IF EXISTS "Public read access for products" ON products;
CREATE POLICY "Public read access for products"
    ON products FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Public read access for categories" ON categories;
CREATE POLICY "Public read access for categories"
    ON categories FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Public read access for product_variants" ON product_variants;
CREATE POLICY "Public read access for product_variants"
    ON product_variants FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Public read access for product_colors" ON product_colors;
CREATE POLICY "Public read access for product_colors"
    ON product_colors FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Public read access for product_images" ON product_images;
CREATE POLICY "Public read access for product_images"
    ON product_images FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Public read access for product_categories" ON product_categories;
CREATE POLICY "Public read access for product_categories"
    ON product_categories FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Public read access for product_price_history" ON product_price_history;
CREATE POLICY "Public read access for product_price_history"
    ON product_price_history FOR SELECT
    USING (true);

-- 3. INTERNAL TABLES (catalogue_sync_state)
-- Only service_role can access catalogue_sync_state. No public anon policy created.
