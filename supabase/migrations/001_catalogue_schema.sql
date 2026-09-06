-- ============================================================================
-- Migration: 001_catalogue_schema.sql
-- Description: Core schema for Zara US normalized catalogue in Supabase/PostgreSQL.
-- Tables:
--   1. products
--   2. categories
--   3. product_variants
--   4. product_colors
--   5. product_images
--   6. product_categories
--   7. product_price_history
--   8. catalogue_sync_state
-- ============================================================================

-- Ensure pgcrypto extension is available
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. PRODUCTS TABLE
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    source_product_id TEXT,
    product_group_id TEXT,
    commercial_reference TEXT,
    sku TEXT,
    brand TEXT NOT NULL DEFAULT 'ZARA',
    department TEXT NOT NULL,
    market TEXT NOT NULL DEFAULT 'US',
    locale TEXT NOT NULL DEFAULT 'en',
    exact_product_name TEXT NOT NULL,
    short_description TEXT,
    long_description TEXT,
    fit_information TEXT,
    care_information TEXT,
    composition_text TEXT,
    material_text TEXT,
    currency TEXT NOT NULL DEFAULT 'USD',
    current_price NUMERIC(12,2) NOT NULL,
    original_price NUMERIC(12,2),
    sale_price NUMERIC(12,2),
    is_on_sale BOOLEAN NOT NULL DEFAULT false,
    product_url TEXT,
    canonical_url TEXT,
    source_content_hash TEXT,
    lifecycle_status TEXT NOT NULL DEFAULT 'ACTIVE',
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    last_synced_at TIMESTAMPTZ,
    price_last_verified_at TIMESTAMPTZ,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(exact_product_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(short_description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(long_description, '')), 'C') ||
        setweight(to_tsvector('english', coalesce(material_text, '')), 'D')
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_product_current_price CHECK (current_price >= 0),
    CONSTRAINT check_product_original_price CHECK (original_price IS NULL OR original_price >= 0),
    CONSTRAINT check_product_sale_price CHECK (sale_price IS NULL OR sale_price >= 0),
    CONSTRAINT check_product_lifecycle_status CHECK (lifecycle_status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED'))
);

-- 2. CATEGORIES TABLE
CREATE TABLE IF NOT EXISTS categories (
    category_id TEXT PRIMARY KEY,
    parent_category_id TEXT REFERENCES categories(category_id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
    department TEXT,
    name TEXT NOT NULL,
    slug TEXT,
    source_url TEXT,
    category_type TEXT,
    status TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. PRODUCT VARIANTS TABLE
CREATE TABLE IF NOT EXISTS product_variants (
    variant_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    source_product_id TEXT,
    commercial_reference TEXT,
    sku TEXT,
    color_name TEXT,
    color_code TEXT,
    size_name TEXT,
    size_code TEXT,
    size_label TEXT,
    public_availability_state TEXT NOT NULL DEFAULT 'UNKNOWN',
    availability_last_verified_at TIMESTAMPTZ,
    variant_url TEXT,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_variant_availability CHECK (public_availability_state IN ('IN_STOCK', 'OUT_OF_STOCK', 'UNKNOWN'))
);

-- 4. PRODUCT COLORS TABLE
CREATE TABLE IF NOT EXISTS product_colors (
    color_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    color_name TEXT,
    color_code TEXT,
    color_reference TEXT,
    color_specific_url TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. PRODUCT IMAGES TABLE
CREATE TABLE IF NOT EXISTS product_images (
    image_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    variant_id TEXT REFERENCES product_variants(variant_id) ON DELETE SET NULL,
    color_name TEXT,
    color_code TEXT,
    source_image_url TEXT NOT NULL,
    image_role TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    alt_text TEXT,
    image_asset_key TEXT,
    image_last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. PRODUCT CATEGORIES TABLE (MANY-TO-MANY)
CREATE TABLE IF NOT EXISTS product_categories (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    category_id TEXT NOT NULL REFERENCES categories(category_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_product_category UNIQUE (product_id, category_id)
);

-- 7. PRODUCT PRICE HISTORY TABLE
CREATE TABLE IF NOT EXISTS product_price_history (
    history_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    observed_at TIMESTAMPTZ NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    original_price NUMERIC(12,2),
    current_price NUMERIC(12,2) NOT NULL,
    sale_price NUMERIC(12,2),
    is_on_sale BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_price_history_current_price CHECK (current_price >= 0),
    CONSTRAINT check_price_history_original_price CHECK (original_price IS NULL OR original_price >= 0),
    CONSTRAINT check_price_history_sale_price CHECK (sale_price IS NULL OR sale_price >= 0)
);

-- 8. CATALOGUE SYNC STATE TABLE
CREATE TABLE IF NOT EXISTS catalogue_sync_state (
    id TEXT PRIMARY KEY,
    product_id TEXT,
    status TEXT NOT NULL,
    source_url TEXT,
    canonical_url TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    last_attempt_at TIMESTAMPTZ,
    last_synced_at TIMESTAMPTZ,
    source_content_hash TEXT,
    lifecycle_status TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
