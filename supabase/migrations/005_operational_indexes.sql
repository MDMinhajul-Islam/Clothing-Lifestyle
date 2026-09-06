-- ============================================================================
-- Migration: 005_operational_indexes.sql
-- Description: Indexes for Synthetic Retail Operational Layer.
-- ============================================================================

-- 1. STORES INDEXES
CREATE INDEX IF NOT EXISTS idx_stores_state ON stores(state);
CREATE INDEX IF NOT EXISTS idx_stores_city ON stores(city);
CREATE INDEX IF NOT EXISTS idx_stores_status ON stores(status);

-- 2. INVENTORY INDEXES
CREATE INDEX IF NOT EXISTS idx_inventory_store_id ON inventory_levels(store_id);
CREATE INDEX IF NOT EXISTS idx_inventory_variant_id ON inventory_levels(variant_id);
CREATE INDEX IF NOT EXISTS idx_inventory_availability ON inventory_levels(availability_status);
CREATE INDEX IF NOT EXISTS idx_inventory_var_avail ON inventory_levels(variant_id, availability_status);

-- 3. CUSTOMERS INDEXES
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(state);

-- 4. CUSTOMER ADDRESSES INDEXES
CREATE INDEX IF NOT EXISTS idx_addresses_customer_id ON customer_addresses(customer_id);

-- 5. ORDERS INDEXES
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_orders_placed_at ON orders(placed_at DESC);

-- 6. ORDER ITEMS INDEXES
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_variant_id ON order_items(variant_id);

-- 7. PAYMENTS INDEXES
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(payment_status);

-- 8. SHIPMENTS INDEXES
CREATE INDEX IF NOT EXISTS idx_shipments_order_id ON shipments(order_id);
CREATE INDEX IF NOT EXISTS idx_shipments_tracking ON shipments(tracking_number);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(shipment_status);

-- 9. SHIPMENT EVENTS INDEXES
CREATE INDEX IF NOT EXISTS idx_shipment_events_shipment_id ON shipment_events(shipment_id);
CREATE INDEX IF NOT EXISTS idx_shipment_events_occurred_at ON shipment_events(occurred_at);

-- 10. RETURNS INDEXES
CREATE INDEX IF NOT EXISTS idx_returns_order_id ON returns(order_id);
CREATE INDEX IF NOT EXISTS idx_returns_status ON returns(return_status);

-- 11. RETURN ITEMS INDEXES
CREATE INDEX IF NOT EXISTS idx_return_items_return_id ON return_items(return_id);
CREATE INDEX IF NOT EXISTS idx_return_items_order_item_id ON return_items(order_item_id);

-- 12. REFUNDS INDEXES
CREATE INDEX IF NOT EXISTS idx_refunds_order_id ON refunds(order_id);
CREATE INDEX IF NOT EXISTS idx_refunds_return_id ON refunds(return_id);
CREATE INDEX IF NOT EXISTS idx_refunds_status ON refunds(refund_status);

-- 13. EXCHANGES INDEXES
CREATE INDEX IF NOT EXISTS idx_exchanges_return_item_id ON exchanges(return_item_id);
CREATE INDEX IF NOT EXISTS idx_exchanges_orig_var ON exchanges(original_variant_id);
CREATE INDEX IF NOT EXISTS idx_exchanges_repl_var ON exchanges(replacement_variant_id);
