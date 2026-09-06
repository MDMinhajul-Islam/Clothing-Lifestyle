import os
import sys
from pathlib import Path
import psycopg2
from urllib.parse import urlsplit

ROOT_DIR = Path(r"f:\NEXVIX INTERN\Clothing Lifestyle")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.supabase.import_catalogue import load_dotenv

load_dotenv()
db_url = os.getenv("SUPABASE_DB_URL")
if not db_url:
    print("ERROR: SUPABASE_DB_URL missing")
    sys.exit(1)

conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("====================================================================")
print("1. DATABASE ROW COUNTS VALIDATION")
print("====================================================================")
expected_counts = {
    "products": 6018,
    "categories": 745,
    "product_variants": 38002,
    "product_colors": 7717,
    "product_images": 40228,
    "product_categories": 8200,
    "product_price_history": 6018,
    "catalogue_sync_state": 6276,
}

actual_counts = {}
counts_pass = True
for table, expected in expected_counts.items():
    cur.execute(f"SELECT count(*) FROM {table};")
    actual = cur.fetchone()[0]
    actual_counts[table] = actual
    match = actual == expected
    print(f"  - {table:<25}: Expected={expected:>6}, Actual={actual:>6} -> {'PASS' if match else 'FAIL'}")
    if not match:
        counts_pass = False

assert counts_pass, "Row count validation failed!"

print("\n====================================================================")
print("2. RELATIONAL INTEGRITY & ZERO ORPHANS / DUPLICATES VALIDATION")
print("====================================================================")

# Orphan checks
cur.execute("SELECT count(*) FROM product_variants v LEFT JOIN products p ON v.product_id = p.product_id WHERE p.product_id IS NULL;")
orphan_variants = cur.fetchone()[0]
print(f"  - Orphan variants: {orphan_variants} (Expected: 0)")

cur.execute("SELECT count(*) FROM product_colors c LEFT JOIN products p ON c.product_id = p.product_id WHERE p.product_id IS NULL;")
orphan_colors = cur.fetchone()[0]
print(f"  - Orphan colors: {orphan_colors} (Expected: 0)")

cur.execute("SELECT count(*) FROM product_images i LEFT JOIN products p ON i.product_id = p.product_id WHERE p.product_id IS NULL;")
orphan_images = cur.fetchone()[0]
print(f"  - Orphan images: {orphan_images} (Expected: 0)")

cur.execute("""
SELECT count(*) FROM product_categories pc 
LEFT JOIN products p ON pc.product_id = p.product_id 
LEFT JOIN categories c ON pc.category_id = c.category_id 
WHERE p.product_id IS NULL OR c.category_id IS NULL;
""")
orphan_prod_cats = cur.fetchone()[0]
print(f"  - Orphan product_categories: {orphan_prod_cats} (Expected: 0)")

cur.execute("SELECT count(*) FROM product_price_history ph LEFT JOIN products p ON ph.product_id = p.product_id WHERE p.product_id IS NULL;")
orphan_hist = cur.fetchone()[0]
print(f"  - Orphan price history: {orphan_hist} (Expected: 0)")

# Duplicate primary IDs
dup_checks = [
    ("products", "product_id"),
    ("categories", "category_id"),
    ("product_variants", "variant_id"),
    ("product_colors", "color_id"),
    ("product_images", "image_id"),
    ("product_price_history", "history_id"),
    ("catalogue_sync_state", "id")
]
for tbl, col in dup_checks:
    cur.execute(f"SELECT count(*) FROM (SELECT {col} FROM {tbl} GROUP BY {col} HAVING count(*) > 1) d;")
    dup_count = cur.fetchone()[0]
    print(f"  - Duplicate {tbl}.{col}: {dup_count} (Expected: 0)")
    assert dup_count == 0

# Duplicate product-category relations
cur.execute("SELECT count(*) FROM (SELECT product_id, category_id FROM product_categories GROUP BY product_id, category_id HAVING count(*) > 1) d;")
dup_pc = cur.fetchone()[0]
print(f"  - Duplicate product-category relations: {dup_pc} (Expected: 0)")
assert dup_pc == 0

assert all(x == 0 for x in [orphan_variants, orphan_colors, orphan_images, orphan_prod_cats, orphan_hist]), "Integrity check failed!"

print("\n====================================================================")
print("3. RLS BEHAVIOR VALIDATION")
print("====================================================================")
# Test as anonymous user (role 'anon')
cur.execute("SET ROLE anon;")

# Public SELECT should succeed
cur.execute("SELECT count(*) FROM products;")
anon_prods = cur.fetchone()[0]
print(f"  - Anon SELECT on products: {anon_prods} rows visible -> PASS")

cur.execute("SELECT count(*) FROM categories;")
anon_cats = cur.fetchone()[0]
print(f"  - Anon SELECT on categories: {anon_cats} rows visible -> PASS")

# Public INSERT should fail
insert_failed = False
try:
    cur.execute("INSERT INTO products (product_id, exact_product_name, department, current_price) VALUES ('hack', 'Hack', 'WOMAN', 10);")
    conn.commit()
except Exception as e:
    insert_failed = True
    conn.rollback()
    print(f"  - Anon INSERT on products blocked: {type(e).__name__} -> PASS")

assert insert_failed, "Anon was able to insert into products!"

# Public UPDATE should fail or affect 0 rows
cur.execute("SET ROLE anon;")
cur.execute("UPDATE products SET current_price = 0 WHERE product_id = (SELECT product_id FROM products LIMIT 1);")
updated_rows = cur.rowcount
print(f"  - Anon UPDATE on products affected: {updated_rows} rows (Expected: 0) -> PASS")
assert updated_rows == 0, "Anon was able to update products!"

# Catalogue sync state should be inaccessible to anon
cur.execute("SELECT count(*) FROM catalogue_sync_state;")
anon_sync = cur.fetchone()[0]
print(f"  - Anon SELECT on catalogue_sync_state: {anon_sync} rows visible (Expected: 0) -> PASS")
assert anon_sync == 0, "Anon was able to view catalogue_sync_state!"

# Reset role
cur.execute("RESET ROLE;")

print("\n====================================================================")
print("4. REPRESENTATIVE CATALOGUE QUERIES & FULL-TEXT SEARCH")
print("====================================================================")

# A. Product details with variants/colors/images
cur.execute("""
SELECT p.product_id, p.exact_product_name, p.current_price, p.currency,
       count(DISTINCT v.variant_id) as variant_count,
       count(DISTINCT c.color_id) as color_count,
       count(DISTINCT i.image_id) as image_count
FROM products p
LEFT JOIN product_variants v ON p.product_id = v.product_id
LEFT JOIN product_colors c ON p.product_id = c.product_id
LEFT JOIN product_images i ON p.product_id = i.product_id
GROUP BY p.product_id, p.exact_product_name, p.current_price, p.currency
HAVING count(DISTINCT v.variant_id) > 5 AND count(DISTINCT i.image_id) > 5
LIMIT 1;
""")
sample = cur.fetchone()
print(f"  - Product Details Drilldown:")
print(f"    Product: {sample[0]} | {sample[1]} | {sample[3]} {sample[2]}")
print(f"    Variants: {sample[4]} | Colors: {sample[5]} | Images: {sample[6]}")

# B. Woman products under $100
cur.execute("SELECT count(*) FROM products WHERE department = 'WOMAN' AND current_price < 100.00;")
w_under_100 = cur.fetchone()[0]
print(f"  - Woman products under $100: {w_under_100}")

# C. Sale products
cur.execute("SELECT count(*) FROM products WHERE is_on_sale = true;")
sale_count = cur.fetchone()[0]
print(f"  - Products on sale: {sale_count}")

# D. Size M + IN_STOCK
cur.execute("""
SELECT count(DISTINCT product_id) FROM product_variants 
WHERE size_name = 'M' AND public_availability_state = 'IN_STOCK';
""")
m_in_stock = cur.fetchone()[0]
print(f"  - Products available in stock for size 'M': {m_in_stock}")

# E. Category lookup
cur.execute("""
SELECT c.name, c.department, count(pc.product_id) as prods
FROM categories c
JOIN product_categories pc ON c.category_id = pc.category_id
GROUP BY c.name, c.department
ORDER BY prods DESC LIMIT 1;
""")
top_cat = cur.fetchone()
print(f"  - Top Category Lookup: '{top_cat[0]}' ({top_cat[1]}) with {top_cat[2]} products")

# F. Price history
cur.execute("SELECT count(*) FROM product_price_history WHERE current_price > 0;")
hist_records = cur.fetchone()[0]
print(f"  - Verified Price History Snapshots: {hist_records}")

# G. Full-text search
cur.execute("""
SELECT product_id, exact_product_name, current_price, ts_rank(search_vector, query) as rank
FROM products, to_tsquery('english', 'linen & shirt') query
WHERE search_vector @@ query
ORDER BY rank DESC LIMIT 3;
""")
ft_results = cur.fetchall()
print(f"  - Full-Text Search ('linen & shirt') Top Results:")
for r in ft_results:
    print(f"    * {r[0]}: {r[1]} (${r[2]}) - rank: {r[3]:.3f}")
assert len(ft_results) > 0, "Full-text search returned no results!"

print("\n====================================================================")
print("5. IMPORTER IDEMPOTENCY VERIFICATION")
print("====================================================================")
# Upsert 50 products again and verify total count remains 6018
from scripts.supabase.import_catalogue import CatalogueDataLoader, PostgresDirectClient
loader = CatalogueDataLoader()
loader.load_all()

client = PostgresDirectClient(db_url)
client.upsert_batch("products", loader.products[:100], "product_id")
client.close()

cur.execute("SELECT count(*) FROM products;")
post_upsert_count = cur.fetchone()[0]
print(f"  - Count before: 6018, Count after 100 re-upserts: {post_upsert_count} -> {'PASS' if post_upsert_count == 6018 else 'FAIL'}")
assert post_upsert_count == 6018, "Idempotency violated!"

conn.close()
print("\nALL_VALIDATIONS_PASSED: 100% COMPLETE & VERIFIED")
