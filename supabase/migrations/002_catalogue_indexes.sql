-- ============================================================================
-- Migration: 002_catalogue_indexes.sql
-- Description: Indexes for performance and full-text search across Zara US catalogue.
-- ============================================================================

-- 1. PRODUCTS INDEXES
CREATE INDEX IF NOT EXISTS idx_products_department ON products(department);
CREATE INDEX IF NOT EXISTS idx_products_current_price ON products(current_price);
CREATE INDEX IF NOT EXISTS idx_products_is_on_sale ON products(is_on_sale);
CREATE INDEX IF NOT EXISTS idx_products_commercial_ref ON products(commercial_reference);
CREATE INDEX IF NOT EXISTS idx_products_source_product_id ON products(source_product_id);
CREATE INDEX IF NOT EXISTS idx_products_lifecycle_status ON products(lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_products_exact_product_name ON products(exact_product_name);
CREATE INDEX IF NOT EXISTS idx_products_search_vector ON products USING gin(search_vector);

-- 2. PRODUCT VARIANTS INDEXES
CREATE INDEX IF NOT EXISTS idx_variants_product_id ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_variants_sku ON product_variants(sku);
CREATE INDEX IF NOT EXISTS idx_variants_color_name ON product_variants(color_name);
CREATE INDEX IF NOT EXISTS idx_variants_size_name ON product_variants(size_name);
CREATE INDEX IF NOT EXISTS idx_variants_availability ON product_variants(public_availability_state);

-- 3. PRODUCT COLORS INDEXES
CREATE INDEX IF NOT EXISTS idx_colors_product_id ON product_colors(product_id);

-- 4. PRODUCT IMAGES INDEXES
CREATE INDEX IF NOT EXISTS idx_images_product_id ON product_images(product_id);
CREATE INDEX IF NOT EXISTS idx_images_variant_id ON product_images(variant_id);
CREATE INDEX IF NOT EXISTS idx_images_image_role ON product_images(image_role);
CREATE INDEX IF NOT EXISTS idx_images_image_asset_key ON product_images(image_asset_key);

-- 5. CATEGORIES INDEXES
CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_category_id);
CREATE INDEX IF NOT EXISTS idx_categories_department ON categories(department);
CREATE INDEX IF NOT EXISTS idx_categories_category_type ON categories(category_type);

-- 6. PRODUCT CATEGORIES INDEXES
CREATE INDEX IF NOT EXISTS idx_prod_cats_product_id ON product_categories(product_id);
CREATE INDEX IF NOT EXISTS idx_prod_cats_category_id ON product_categories(category_id);

-- 7. PRODUCT PRICE HISTORY INDEXES
CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON product_price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_observed_at ON product_price_history(observed_at);
CREATE INDEX IF NOT EXISTS idx_price_history_prod_observed ON product_price_history(product_id, observed_at DESC);

-- 8. CATALOGUE SYNC STATE INDEXES
CREATE INDEX IF NOT EXISTS idx_sync_state_status ON catalogue_sync_state(status);
CREATE INDEX IF NOT EXISTS idx_sync_state_product_id ON catalogue_sync_state(product_id);
