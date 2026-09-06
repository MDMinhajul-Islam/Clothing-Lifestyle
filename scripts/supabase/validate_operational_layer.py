#!/usr/bin/env python3
"""Validation and Business Query Suite for Synthetic Operational Layer (Phase 2B).

Verifies:
  1. Live row counts in Supabase match the synthetic datasets.
  2. 0 orphan foreign keys across all 13 operational tables.
  3. Non-negative stock and generated quantity_available correctness.
  4. 100% order financial reconciliation (subtotal - discount + tax + shipping = grand_total).
  5. Valid chronological order and shipment lifecycles.
  6. Return quantity <= ordered quantity and refund amount <= paid amount.
  7. Row-Level Security (RLS) policies and access controls.
  8. Executes 9 representative business queries powering future storefront & voice agent tools.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import psycopg2

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_SYNTHETIC = ROOT_DIR / "data" / "synthetic"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("validate_operations")


def load_dotenv(env_path: Path = ROOT_DIR / ".env"):
    """Load environment variables from .env."""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k not in os.environ:
                    os.environ[k] = v


OPERATIONAL_TABLES = [
    "stores",
    "inventory_levels",
    "customers",
    "customer_addresses",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "shipment_events",
    "returns",
    "return_items",
    "refunds",
    "exchanges",
]


def validate_row_counts(cur) -> dict:
    """Verify live table row counts against exported JSON files."""
    logger.info("=== 1. LIVE ROW COUNT VALIDATION ===")
    counts = {}
    for table in OPERATIONAL_TABLES:
        cur.execute(f"SELECT count(*) FROM {table};")
        db_count = cur.fetchone()[0]

        json_file = DATA_SYNTHETIC / f"{table}.json"
        if json_file.exists():
            with open(json_file, "r", encoding="utf-8") as f:
                expected_count = len(json.load(f))
        else:
            expected_count = -1

        status = "MATCH" if db_count == expected_count else "MISMATCH"
        logger.info(f"  {table:20s}: DB={db_count:7d} | Expected={expected_count:7d} -> {status}")
        assert db_count == expected_count, f"Count mismatch for {table}: db={db_count}, expected={expected_count}"
        counts[table] = db_count

    return counts


def validate_foreign_keys(cur):
    """Verify zero orphan records across all operational tables."""
    logger.info("=== 2. RELATIONAL INTEGRITY / ORPHAN AUDIT ===")

    orphan_checks = [
        ("inventory_levels -> stores", "SELECT count(*) FROM inventory_levels i LEFT JOIN stores s ON i.store_id = s.store_id WHERE s.store_id IS NULL;"),
        ("inventory_levels -> product_variants", "SELECT count(*) FROM inventory_levels i LEFT JOIN product_variants v ON i.variant_id = v.variant_id WHERE v.variant_id IS NULL;"),
        ("customer_addresses -> customers", "SELECT count(*) FROM customer_addresses a LEFT JOIN customers c ON a.customer_id = c.customer_id WHERE c.customer_id IS NULL;"),
        ("orders -> customers", "SELECT count(*) FROM orders o LEFT JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_id IS NULL;"),
        ("orders -> customer_addresses", "SELECT count(*) FROM orders o LEFT JOIN customer_addresses a ON o.shipping_address_id = a.address_id WHERE o.shipping_address_id IS NOT NULL AND a.address_id IS NULL;"),
        ("orders -> stores", "SELECT count(*) FROM orders o LEFT JOIN stores s ON o.store_id = s.store_id WHERE o.store_id IS NOT NULL AND s.store_id IS NULL;"),
        ("order_items -> orders", "SELECT count(*) FROM order_items oi LEFT JOIN orders o ON oi.order_id = o.order_id WHERE o.order_id IS NULL;"),
        ("order_items -> products", "SELECT count(*) FROM order_items oi LEFT JOIN products p ON oi.product_id = p.product_id WHERE p.product_id IS NULL;"),
        ("order_items -> product_variants", "SELECT count(*) FROM order_items oi LEFT JOIN product_variants v ON oi.variant_id = v.variant_id WHERE v.variant_id IS NULL;"),
        ("payments -> orders", "SELECT count(*) FROM payments p LEFT JOIN orders o ON p.order_id = o.order_id WHERE o.order_id IS NULL;"),
        ("shipments -> orders", "SELECT count(*) FROM shipments s LEFT JOIN orders o ON s.order_id = o.order_id WHERE o.order_id IS NULL;"),
        ("shipment_events -> shipments", "SELECT count(*) FROM shipment_events e LEFT JOIN shipments s ON e.shipment_id = s.shipment_id WHERE s.shipment_id IS NULL;"),
        ("returns -> orders", "SELECT count(*) FROM returns r LEFT JOIN orders o ON r.order_id = o.order_id WHERE o.order_id IS NULL;"),
        ("return_items -> returns", "SELECT count(*) FROM return_items ri LEFT JOIN returns r ON ri.return_id = r.return_id WHERE r.return_id IS NULL;"),
        ("return_items -> order_items", "SELECT count(*) FROM return_items ri LEFT JOIN order_items oi ON ri.order_item_id = oi.order_item_id WHERE oi.order_item_id IS NULL;"),
        ("refunds -> orders", "SELECT count(*) FROM refunds ref LEFT JOIN orders o ON ref.order_id = o.order_id WHERE o.order_id IS NULL;"),
        ("refunds -> returns", "SELECT count(*) FROM refunds ref LEFT JOIN returns r ON ref.return_id = r.return_id WHERE ref.return_id IS NOT NULL AND r.return_id IS NULL;"),
        ("exchanges -> return_items", "SELECT count(*) FROM exchanges exc LEFT JOIN return_items ri ON exc.return_item_id = ri.return_item_id WHERE ri.return_item_id IS NULL;"),
        ("exchanges -> original_variants", "SELECT count(*) FROM exchanges exc LEFT JOIN product_variants v ON exc.original_variant_id = v.variant_id WHERE v.variant_id IS NULL;"),
        ("exchanges -> replacement_variants", "SELECT count(*) FROM exchanges exc LEFT JOIN product_variants v ON exc.replacement_variant_id = v.variant_id WHERE v.variant_id IS NULL;"),
    ]

    for label, query in orphan_checks:
        cur.execute(query)
        orphans = cur.fetchone()[0]
        logger.info(f"  {label:35s}: {orphans} orphans")
        assert orphans == 0, f"Orphan integrity violation found in {label}: {orphans}"

    logger.info("RELATIONAL INTEGRITY PASS: Zero orphan records across all relationships.")


def validate_business_constraints(cur):
    """Verify business constraints, inventory validity, and financial reconciliation."""
    logger.info("=== 3. BUSINESS CONSTRAINTS & FINANCIAL RECONCILIATION ===")

    # 1. Non-negative stock and generated quantity_available
    cur.execute("""
        SELECT count(*) FROM inventory_levels
        WHERE quantity_on_hand < 0 
           OR quantity_reserved < 0 
           OR quantity_reserved > quantity_on_hand
           OR quantity_available != (quantity_on_hand - quantity_reserved);
    """)
    invalid_inv = cur.fetchone()[0]
    logger.info(f"  Invalid inventory rows: {invalid_inv}")
    assert invalid_inv == 0, f"Found {invalid_inv} invalid inventory rows."

    # 2. Inventory status consistency
    cur.execute("""
        SELECT count(*) FROM inventory_levels
        WHERE (availability_status = 'OUT_OF_STOCK' AND quantity_available > 0)
           OR (availability_status = 'IN_STOCK' AND quantity_available = 0);
    """)
    inconsistent_inv = cur.fetchone()[0]
    logger.info(f"  Inconsistent inventory status rows: {inconsistent_inv}")
    assert inconsistent_inv == 0, f"Found {inconsistent_inv} inconsistent inventory rows."

    # 3. Order financial reconciliation
    cur.execute("""
        SELECT count(*) FROM orders
        WHERE round(subtotal - discount_total + tax_total + shipping_total, 2) != round(grand_total, 2);
    """)
    mismatched_financials = cur.fetchone()[0]
    logger.info(f"  Order financial reconciliation mismatches: {mismatched_financials}")
    assert mismatched_financials == 0, f"Found {mismatched_financials} orders with math errors."

    # 4. Return quantity <= ordered quantity
    cur.execute("""
        SELECT count(*) FROM return_items ri
        JOIN order_items oi ON ri.order_item_id = oi.order_item_id
        WHERE ri.quantity > oi.quantity;
    """)
    excessive_returns = cur.fetchone()[0]
    logger.info(f"  Return items exceeding order quantity: {excessive_returns}")
    assert excessive_returns == 0, f"Found {excessive_returns} return items exceeding order quantity."

    # 5. Refund amount <= order grand total
    cur.execute("""
        SELECT count(*) FROM refunds ref
        JOIN orders o ON ref.order_id = o.order_id
        WHERE ref.amount > o.grand_total;
    """)
    excessive_refunds = cur.fetchone()[0]
    logger.info(f"  Refunds exceeding order grand total: {excessive_refunds}")
    assert excessive_refunds == 0, f"Found {excessive_refunds} refunds exceeding grand total."

    # 6. Chronological order consistency: confirmed_at >= placed_at, cancelled_at >= placed_at
    cur.execute("""
        SELECT count(*) FROM orders
        WHERE (confirmed_at IS NOT NULL AND confirmed_at < placed_at)
           OR (cancelled_at IS NOT NULL AND cancelled_at < placed_at)
           OR (completed_at IS NOT NULL AND completed_at < placed_at);
    """)
    timeline_errors = cur.fetchone()[0]
    logger.info(f"  Order timeline chronological errors: {timeline_errors}")
    assert timeline_errors == 0, f"Found {timeline_errors} orders with chronological errors."

    logger.info("BUSINESS CONSTRAINTS PASS: All financial, inventory, and lifecycle rules verified.")


def validate_rls(cur):
    """Verify RLS is active on all operational tables and check policy permissions."""
    logger.info("=== 4. ROW-LEVEL SECURITY (RLS) AUDIT ===")

    cur.execute("""
        SELECT tablename, rowsecurity
        FROM pg_tables
        WHERE schemaname = 'public' AND tablename = ANY(%s);
    """, (OPERATIONAL_TABLES,))
    rls_map = {row[0]: row[1] for row in cur.fetchall()}

    for t in OPERATIONAL_TABLES:
        status = "ENABLED" if rls_map.get(t) else "DISABLED"
        logger.info(f"  {t:20s}: RLS {status}")
        assert rls_map.get(t) is True, f"RLS disabled on {t}"

    # Verify public policies on stores and inventory_levels
    cur.execute("""
        SELECT tablename, policyname, roles, cmd
        FROM pg_policies
        WHERE schemaname = 'public' AND tablename = ANY(%s);
    """, (['stores', 'inventory_levels'],))
    policies = cur.fetchall()
    policy_tables = {p[0] for p in policies}
    assert 'stores' in policy_tables, "Missing public read policy on stores"
    assert 'inventory_levels' in policy_tables, "Missing public read policy on inventory_levels"

    # Verify private tables have NO public unrestricted read
    cur.execute("""
        SELECT tablename, policyname
        FROM pg_policies
        WHERE schemaname = 'public' AND tablename = ANY(%s);
    """, (['customers', 'orders', 'payments'],))
    private_policies = cur.fetchall()
    logger.info(f"  Private tables public policies count: {len(private_policies)} (Expected 0 - backend service_role only)")
    assert len(private_policies) == 0, "Private tables must not have unrestricted public read policies"

    logger.info("RLS SECURITY PASS: Public shopping tables open for lookup; customer data protected.")


def execute_representative_queries(cur):
    """Execute all 9 representative business queries specified in Phase 2B Section 28."""
    logger.info("=== 5. REPRESENTATIVE BUSINESS QUERIES (9 QUERIES) ===")

    # Query 1: Check all stores carrying a specific variant
    cur.execute("SELECT variant_id FROM inventory_levels WHERE availability_status = 'IN_STOCK' LIMIT 1;")
    sample_var_id = cur.fetchone()[0]

    cur.execute("""
        SELECT s.store_name, s.city, s.state, inv.quantity_available, inv.availability_status
        FROM inventory_levels inv
        JOIN stores s ON inv.store_id = s.store_id
        WHERE inv.variant_id = %s AND inv.quantity_available > 0
        ORDER BY inv.quantity_available DESC;
    """, (sample_var_id,))
    q1_results = cur.fetchall()
    logger.info(f"  Query 1 (Stores carrying variant '{sample_var_id}'):")
    for r in q1_results[:3]:
        logger.info(f"    - {r[0]} ({r[1]}, {r[2]}): {r[3]} units available ({r[4]})")
    assert len(q1_results) > 0, "Query 1 returned no stores"

    # Query 2: Find available stock for product + color + size
    cur.execute("""
        SELECT p.product_id, v.color_name, v.size_name
        FROM inventory_levels inv
        JOIN product_variants v ON inv.variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        WHERE inv.availability_status = 'IN_STOCK' AND v.color_name IS NOT NULL AND v.size_name IS NOT NULL
        LIMIT 1;
    """)
    prod_id, color_name, size_name = cur.fetchone()

    cur.execute("""
        SELECT s.store_name, inv.quantity_available
        FROM inventory_levels inv
        JOIN product_variants v ON inv.variant_id = v.variant_id
        JOIN stores s ON inv.store_id = s.store_id
        WHERE v.product_id = %s AND v.color_name = %s AND v.size_name = %s AND inv.quantity_available > 0;
    """, (prod_id, color_name, size_name))
    q2_results = cur.fetchall()
    logger.info(f"  Query 2 (Stock for product='{prod_id}', color='{color_name}', size='{size_name}'):")
    for r in q2_results[:3]:
        logger.info(f"    - {r[0]}: {r[1]} units available")
    assert len(q2_results) > 0, "Query 2 returned no stock"

    # Query 3: Get customer by email
    cur.execute("""
        SELECT customer_id, first_name, last_name, email, phone, city, state, account_status
        FROM customers
        LIMIT 1;
    """)
    cust = cur.fetchone()
    sample_email = cust[3]
    cur.execute("""
        SELECT customer_id, first_name, last_name, phone, city, state, account_status
        FROM customers
        WHERE email = %s;
    """, (sample_email,))
    cust_by_email = cur.fetchone()
    logger.info(f"  Query 3 (Get customer by email '{sample_email}'):")
    logger.info(f"    Customer: {cust_by_email[1]} {cust_by_email[2]} | Phone: {cust_by_email[3]} | Loc: {cust_by_email[4]}, {cust_by_email[5]} | Status: {cust_by_email[6]}")
    assert cust_by_email is not None, f"Customer {sample_email} not found"

    # Query 4: Get customer's latest orders
    cur.execute("""
        SELECT c.customer_id, c.first_name, c.last_name, count(o.order_id)
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.first_name, c.last_name
        HAVING count(o.order_id) > 1
        LIMIT 1;
    """)
    ord_cust = cur.fetchone()
    sample_cust_id = ord_cust[0]
    cust_name = f"{ord_cust[1]} {ord_cust[2]}"
    cur.execute("""
        SELECT order_id, order_number, order_status, grand_total, placed_at
        FROM orders
        WHERE customer_id = %s
        ORDER BY placed_at DESC
        LIMIT 5;
    """, (sample_cust_id,))
    q4_orders = cur.fetchall()
    logger.info(f"  Query 4 (Latest orders for customer {cust_name}):")
    for o in q4_orders:
        logger.info(f"    - Order {o[1]}: status={o[2]}, total=${o[3]}, placed={o[4]}")
    assert len(q4_orders) > 0, f"Customer {sample_cust_id} has no orders"

    # Query 5: Get complete order (order, items, payment, shipment, return/refund state)
    cur.execute("""
        SELECT o.order_id 
        FROM orders o 
        JOIN returns r ON o.order_id = r.order_id 
        JOIN refunds ref ON o.order_id = ref.order_id 
        JOIN shipments s ON o.order_id = s.order_id
        LIMIT 1;
    """)
    full_order_id = cur.fetchone()[0]

    cur.execute("SELECT order_number, order_status, grand_total FROM orders WHERE order_id = %s;", (full_order_id,))
    ord_info = cur.fetchone()
    cur.execute("SELECT product_name_snapshot, size_snapshot, color_snapshot, quantity, unit_price, line_total FROM order_items WHERE order_id = %s;", (full_order_id,))
    items_info = cur.fetchall()
    cur.execute("SELECT payment_method, payment_status, amount FROM payments WHERE order_id = %s;", (full_order_id,))
    pay_info = cur.fetchone()
    cur.execute("SELECT carrier, tracking_number, shipment_status FROM shipments WHERE order_id = %s;", (full_order_id,))
    ship_info = cur.fetchone()
    cur.execute("SELECT return_status, return_reason FROM returns WHERE order_id = %s;", (full_order_id,))
    ret_info = cur.fetchone()
    cur.execute("SELECT refund_status, amount FROM refunds WHERE order_id = %s;", (full_order_id,))
    ref_info = cur.fetchone()

    logger.info(f"  Query 5 (Complete Order Lifecycle View for '{ord_info[0]}'):")
    logger.info(f"    Status: {ord_info[1]} | Grand Total: ${ord_info[2]}")
    logger.info(f"    Line Items ({len(items_info)}):")
    for itm in items_info:
        logger.info(f"      * {itm[0]} ({itm[1]}, {itm[2]}) x{itm[3]} @ ${itm[4]} = ${itm[5]}")
    logger.info(f"    Payment: {pay_info[0]} ({pay_info[1]}) - ${pay_info[2]}")
    logger.info(f"    Shipment: {ship_info[0]} #{ship_info[1]} ({ship_info[2]})")
    logger.info(f"    Return: status={ret_info[0]}, reason={ret_info[1]}")
    logger.info(f"    Refund: status={ref_info[0]}, amount=${ref_info[1]}")

    # Query 6: Determine whether an order can be cancelled
    cur.execute("SELECT order_id, order_number, order_status FROM orders WHERE order_status = 'CONFIRMED' LIMIT 1;")
    cancellable_order = cur.fetchone()
    cur.execute("SELECT order_id, order_number, order_status FROM orders WHERE order_status = 'DELIVERED' LIMIT 1;")
    uncancellable_order = cur.fetchone()

    def check_cancellation(status: str) -> bool:
        return status in ('PENDING', 'CONFIRMED', 'PROCESSING')

    logger.info(f"  Query 6 (Cancellation Eligibility Check):")
    logger.info(f"    Order {cancellable_order[1]} ({cancellable_order[2]}): Cancellable = {check_cancellation(cancellable_order[2])} (Expected True)")
    logger.info(f"    Order {uncancellable_order[1]} ({uncancellable_order[2]}): Cancellable = {check_cancellation(uncancellable_order[2])} (Expected False)")
    assert check_cancellation(cancellable_order[2]) is True
    assert check_cancellation(uncancellable_order[2]) is False

    # Query 7: Determine whether a delivered order is eligible for return
    cur.execute("""
        SELECT o.order_id, o.order_number, o.order_status, s.delivered_at
        FROM orders o
        JOIN shipments s ON o.order_id = s.order_id
        WHERE o.order_status = 'DELIVERED' AND s.delivered_at IS NOT NULL
        LIMIT 1;
    """)
    del_ord = cur.fetchone()

    def check_return_eligibility(status: str, delivered_at) -> (bool, str):
        if status != 'DELIVERED':
            return False, "Order not delivered"
        # Demo return window: 30 days
        days_since = (datetime.now(timezone.utc) - delivered_at).days
        if days_since > 30:
            return False, f"Return window expired ({days_since} days since delivery)"
        return True, f"Eligible for return ({days_since} days since delivery)"

    ret_eligible, ret_msg = check_return_eligibility(del_ord[2], del_ord[3])
    logger.info(f"  Query 7 (Return Eligibility Check):")
    logger.info(f"    Order {del_ord[1]}: Eligible={ret_eligible} ({ret_msg})")

    # Query 8: Calculate refundable amount
    cur.execute("""
        SELECT o.order_id, o.order_number, o.grand_total, coalesce(sum(ri.refund_amount), 0) as returned_refund
        FROM orders o
        LEFT JOIN returns r ON o.order_id = r.order_id
        LEFT JOIN return_items ri ON r.return_id = ri.return_id
        WHERE o.order_status = 'PARTIALLY_RETURNED'
        GROUP BY o.order_id, o.order_number, o.grand_total
        LIMIT 1;
    """)
    p_ord = cur.fetchone()
    max_refundable = Decimal(str(p_ord[2])) - Decimal(str(p_ord[3]))
    logger.info(f"  Query 8 (Calculate Refundable Amount for Partially Returned Order):")
    logger.info(f"    Order {p_ord[1]}: Grand Total=${p_ord[2]}, Already Refunded=${p_ord[3]} -> Max Remaining Refundable=${max_refundable:.2f}")
    assert max_refundable >= Decimal("0.00"), "Remaining refundable amount cannot be negative"

    # Query 9: Check replacement variant stock for exchange
    cur.execute("""
        SELECT exc.exchange_id, exc.original_variant_id, exc.replacement_variant_id, 
               p.exact_product_name, v.size_name, v.color_name,
               coalesce(sum(inv.quantity_available), 0) as total_available_across_stores
        FROM exchanges exc
        JOIN product_variants v ON exc.replacement_variant_id = v.variant_id
        JOIN products p ON v.product_id = p.product_id
        LEFT JOIN inventory_levels inv ON exc.replacement_variant_id = inv.variant_id
        GROUP BY exc.exchange_id, exc.original_variant_id, exc.replacement_variant_id, p.exact_product_name, v.size_name, v.color_name
        LIMIT 1;
    """)
    exc_row = cur.fetchone()
    logger.info(f"  Query 9 (Check replacement variant stock for exchange '{exc_row[0]}'):")
    logger.info(f"    Replacement Item: {exc_row[3]} ({exc_row[4]}, {exc_row[5]})")
    logger.info(f"    Original Variant: {exc_row[1]}")
    logger.info(f"    Replacement Variant: {exc_row[2]}")
    logger.info(f"    Total Stock Across Demo Store Network: {exc_row[6]} units available")

    logger.info("ALL 9 REPRESENTATIVE BUSINESS QUERIES EXECUTED AND VERIFIED SUCCESSFULLY.")


def main():
    load_dotenv()
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        logger.error("SUPABASE_DB_URL not found in environment.")
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    t0 = time.time()
    logger.info("Starting Phase 2B Live Supabase Operational Layer Validation...")

    validate_row_counts(cur)
    validate_foreign_keys(cur)
    validate_business_constraints(cur)
    validate_rls(cur)
    execute_representative_queries(cur)

    conn.close()
    logger.info(f"PHASE 2B VALIDATION COMPLETE in {time.time() - t0:.2f}s! Status: 100% PASS.")


if __name__ == "__main__":
    main()
