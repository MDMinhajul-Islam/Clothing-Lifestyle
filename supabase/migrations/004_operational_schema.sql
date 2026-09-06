-- ============================================================================
-- Migration: 004_operational_schema.sql
-- Description: Synthetic Retail Operational Layer Schema (Phase 2B).
-- Notice: Contains DEMO/SYNTHETIC retail operational records.
-- Catalogue tables (products, variants, etc.) remain real public data.
-- ============================================================================

-- 1. STORES TABLE
CREATE TABLE IF NOT EXISTS stores (
    store_id TEXT PRIMARY KEY,
    store_code TEXT UNIQUE NOT NULL,
    store_name TEXT NOT NULL,
    country_code TEXT NOT NULL DEFAULT 'US',
    country_name TEXT NOT NULL DEFAULT 'United States',
    state TEXT NOT NULL,
    city TEXT NOT NULL,
    address_line_1 TEXT NOT NULL,
    address_line_2 TEXT,
    postal_code TEXT NOT NULL,
    latitude NUMERIC(10,6),
    longitude NUMERIC(10,6),
    timezone TEXT NOT NULL DEFAULT 'America/New_York',
    phone TEXT,
    store_type TEXT NOT NULL DEFAULT 'RETAIL',
    status TEXT NOT NULL DEFAULT 'OPEN',
    opening_hours JSONB,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    data_origin TEXT NOT NULL DEFAULT 'synthetic',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. INVENTORY LEVELS TABLE
CREATE TABLE IF NOT EXISTS inventory_levels (
    inventory_id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    variant_id TEXT NOT NULL REFERENCES product_variants(variant_id) ON DELETE CASCADE,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER NOT NULL DEFAULT 0,
    quantity_available INTEGER GENERATED ALWAYS AS (quantity_on_hand - quantity_reserved) STORED,
    availability_status TEXT NOT NULL DEFAULT 'IN_STOCK',
    reorder_threshold INTEGER NOT NULL DEFAULT 5,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    data_origin TEXT NOT NULL DEFAULT 'synthetic',
    CONSTRAINT uq_store_variant UNIQUE (store_id, variant_id),
    CONSTRAINT check_inventory_on_hand CHECK (quantity_on_hand >= 0),
    CONSTRAINT check_inventory_reserved CHECK (quantity_reserved >= 0),
    CONSTRAINT check_inventory_reserved_lte_on_hand CHECK (quantity_reserved <= quantity_on_hand),
    CONSTRAINT check_inventory_status CHECK (availability_status IN ('IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK'))
);

-- 3. CUSTOMERS TABLE
CREATE TABLE IF NOT EXISTS customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    country_code TEXT NOT NULL DEFAULT 'US',
    state TEXT,
    city TEXT,
    preferred_language TEXT NOT NULL DEFAULT 'en',
    preferred_currency TEXT NOT NULL DEFAULT 'USD',
    marketing_opt_in BOOLEAN NOT NULL DEFAULT false,
    account_status TEXT NOT NULL DEFAULT 'ACTIVE',
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    data_origin TEXT NOT NULL DEFAULT 'synthetic',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. CUSTOMER ADDRESSES TABLE
CREATE TABLE IF NOT EXISTS customer_addresses (
    address_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    address_type TEXT NOT NULL DEFAULT 'SHIPPING',
    recipient_name TEXT NOT NULL,
    address_line_1 TEXT NOT NULL,
    address_line_2 TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    country_code TEXT NOT NULL DEFAULT 'US',
    is_default_shipping BOOLEAN NOT NULL DEFAULT true,
    is_default_billing BOOLEAN NOT NULL DEFAULT true,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. ORDERS TABLE
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    order_number TEXT UNIQUE NOT NULL,
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    order_status TEXT NOT NULL,
    fulfillment_type TEXT NOT NULL DEFAULT 'DELIVERY',
    shipping_address_id UUID REFERENCES customer_addresses(address_id) ON DELETE SET NULL,
    store_id TEXT REFERENCES stores(store_id) ON DELETE SET NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    subtotal NUMERIC(12,2) NOT NULL,
    discount_total NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    tax_total NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    shipping_total NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    grand_total NUMERIC(12,2) NOT NULL,
    payment_status TEXT NOT NULL DEFAULT 'PAID',
    placed_at TIMESTAMPTZ NOT NULL,
    confirmed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    data_origin TEXT NOT NULL DEFAULT 'synthetic',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_order_status CHECK (order_status IN ('PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURN_REQUESTED', 'PARTIALLY_RETURNED', 'RETURNED', 'REFUNDED')),
    CONSTRAINT check_order_subtotal CHECK (subtotal >= 0),
    CONSTRAINT check_order_grand_total CHECK (grand_total >= 0)
);

-- 6. ORDER ITEMS TABLE
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    variant_id TEXT NOT NULL REFERENCES product_variants(variant_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    line_discount NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (line_discount >= 0),
    line_total NUMERIC(12,2) NOT NULL CHECK (line_total >= 0),
    product_name_snapshot TEXT NOT NULL,
    size_snapshot TEXT,
    color_snapshot TEXT,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7. PAYMENTS TABLE
CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    payment_method TEXT NOT NULL,
    payment_status TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    provider_reference TEXT NOT NULL,
    authorized_at TIMESTAMPTZ,
    captured_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8. SHIPMENTS TABLE
CREATE TABLE IF NOT EXISTS shipments (
    shipment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    carrier TEXT NOT NULL,
    tracking_number TEXT NOT NULL UNIQUE,
    shipment_status TEXT NOT NULL,
    shipped_at TIMESTAMPTZ,
    estimated_delivery_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    origin_store_id TEXT REFERENCES stores(store_id) ON DELETE SET NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 9. SHIPMENT EVENTS TABLE
CREATE TABLE IF NOT EXISTS shipment_events (
    event_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(shipment_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    description TEXT,
    location_text TEXT,
    occurred_at TIMESTAMPTZ NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 10. RETURNS TABLE
CREATE TABLE IF NOT EXISTS returns (
    return_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    return_status TEXT NOT NULL,
    return_reason TEXT NOT NULL,
    return_method TEXT NOT NULL DEFAULT 'MAIL',
    requested_at TIMESTAMPTZ NOT NULL,
    approved_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_return_status CHECK (return_status IN ('REQUESTED', 'APPROVED', 'IN_TRANSIT', 'RECEIVED', 'REJECTED', 'COMPLETED', 'CANCELLED'))
);

-- 11. RETURN ITEMS TABLE
CREATE TABLE IF NOT EXISTS return_items (
    return_item_id TEXT PRIMARY KEY,
    return_id TEXT NOT NULL REFERENCES returns(return_id) ON DELETE CASCADE,
    order_item_id TEXT NOT NULL REFERENCES order_items(order_item_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    reason_code TEXT,
    condition TEXT,
    resolution TEXT NOT NULL DEFAULT 'REFUND',
    refund_amount NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (refund_amount >= 0),
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 12. REFUNDS TABLE
CREATE TABLE IF NOT EXISTS refunds (
    refund_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    return_id TEXT REFERENCES returns(return_id) ON DELETE SET NULL,
    refund_status TEXT NOT NULL DEFAULT 'PROCESSED',
    refund_method TEXT NOT NULL DEFAULT 'ORIGINAL_PAYMENT',
    amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    requested_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    provider_reference TEXT NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 13. EXCHANGES TABLE
CREATE TABLE IF NOT EXISTS exchanges (
    exchange_id TEXT PRIMARY KEY,
    return_item_id TEXT NOT NULL REFERENCES return_items(return_item_id) ON DELETE CASCADE,
    original_variant_id TEXT NOT NULL REFERENCES product_variants(variant_id),
    replacement_variant_id TEXT NOT NULL REFERENCES product_variants(variant_id),
    exchange_status TEXT NOT NULL DEFAULT 'APPROVED',
    requested_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    is_synthetic BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
