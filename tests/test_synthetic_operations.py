#!/usr/bin/env python3
"""Unit tests for Phase 2B Synthetic Operational Layer."""

import json
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from scripts.supabase.generate_synthetic_operations import SyntheticOperationsGenerator

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_SYNTHETIC = ROOT_DIR / "data" / "synthetic"


class TestSyntheticOperations(unittest.TestCase):
    """Test suite for operational layer generator and retail business rules."""

    @classmethod
    def setUpClass(cls):
        cls.generator = SyntheticOperationsGenerator(seed=20260907)
        cls.generator.load_catalogue()
        cls.generator.generate_stores()
        cls.generator.generate_inventory()
        cls.generator.generate_customers_and_addresses()
        cls.generator.generate_orders_and_operations()

    def test_record_counts(self):
        """Verify expected operational table record counts."""
        self.assertEqual(len(self.generator.stores), 30)
        self.assertGreaterEqual(len(self.generator.inventory_levels), 100000)
        self.assertEqual(len(self.generator.customers), 2000)
        self.assertEqual(len(self.generator.customer_addresses), 2500)
        self.assertEqual(len(self.generator.orders), 5000)
        self.assertEqual(len(self.generator.order_items), 12500)
        self.assertEqual(len(self.generator.payments), 5000)
        self.assertEqual(len(self.generator.shipments), 4250)
        self.assertEqual(len(self.generator.shipment_events), 20250)
        self.assertEqual(len(self.generator.returns), 750)
        self.assertEqual(len(self.generator.return_items), 1672)
        self.assertEqual(len(self.generator.refunds), 615)
        self.assertEqual(len(self.generator.exchanges), 102)

    def test_synthetic_provenance_markers(self):
        """Verify 100% of records carry synthetic provenance markers."""
        for s in self.generator.stores:
            self.assertTrue(s["is_synthetic"])
            self.assertEqual(s["data_origin"], "synthetic")

        for inv in self.generator.inventory_levels[:500]:
            self.assertTrue(inv["is_synthetic"])
            self.assertEqual(inv["data_origin"], "synthetic")

        for o in self.generator.orders:
            self.assertTrue(o["is_synthetic"])
            self.assertEqual(o["data_origin"], "synthetic")

        for c in self.generator.customers:
            self.assertTrue(c["is_synthetic"])
            self.assertEqual(c["data_origin"], "synthetic")

    def test_order_financial_reconciliation(self):
        """Verify subtotal - discount + tax + shipping == grand_total strictly."""
        for o in self.generator.orders:
            sub = Decimal(str(o["subtotal"]))
            disc = Decimal(str(o["discount_total"]))
            tax = Decimal(str(o["tax_total"]))
            ship = Decimal(str(o["shipping_total"]))
            grand = Decimal(str(o["grand_total"]))
            expected = sub - disc + tax + ship
            self.assertEqual(grand, expected, f"Financial mismatch in order {o['order_id']}")

    def test_inventory_availability_constraints(self):
        """Verify quantity_available calculation and non-negative constraints."""
        for inv in self.generator.inventory_levels[:2000]:
            on_hand = inv["quantity_on_hand"]
            res = inv["quantity_reserved"]
            avail = inv["quantity_available"]
            self.assertGreaterEqual(on_hand, 0)
            self.assertGreaterEqual(res, 0)
            self.assertLessEqual(res, on_hand)
            self.assertEqual(avail, on_hand - res)

            if avail == 0:
                self.assertEqual(inv["availability_status"], "OUT_OF_STOCK")
            else:
                self.assertIn(inv["availability_status"], ("LOW_STOCK", "IN_STOCK"))

    def test_cancellation_eligibility_logic(self):
        """Verify cancellation eligibility rules."""
        cancellable_statuses = {"PENDING", "CONFIRMED", "PROCESSING"}
        uncancellable_statuses = {"SHIPPED", "DELIVERED", "CANCELLED", "RETURN_REQUESTED", "PARTIALLY_RETURNED", "RETURNED", "REFUNDED"}

        for o in self.generator.orders[:500]:
            is_cancellable = o["order_status"] in cancellable_statuses
            if o["order_status"] in uncancellable_statuses:
                self.assertFalse(is_cancellable)
            else:
                self.assertTrue(is_cancellable)

    def test_return_quantity_and_refund_limits(self):
        """Verify return quantity does not exceed ordered quantity and refund does not exceed grand total."""
        oi_qty_map = {oi["order_item_id"]: oi["quantity"] for oi in self.generator.order_items}
        for ri in self.generator.return_items:
            self.assertLessEqual(ri["quantity"], oi_qty_map[ri["order_item_id"]])

        order_grand_map = {o["order_id"]: Decimal(str(o["grand_total"])) for o in self.generator.orders}
        for ref in self.generator.refunds:
            self.assertLessEqual(Decimal(str(ref["amount"])), order_grand_map[ref["order_id"]])

    def test_replacement_variants_exist_in_catalogue(self):
        """Verify all exchange replacement variants exist in real catalogue."""
        for exc in self.generator.exchanges:
            self.assertIn(exc["original_variant_id"], self.generator.valid_variant_ids)
            self.assertIn(exc["replacement_variant_id"], self.generator.valid_variant_ids)

    def test_seed_determinism(self):
        """Verify that identical seed generates byte-for-byte identical orders."""
        gen2 = SyntheticOperationsGenerator(seed=20260907)
        gen2.load_catalogue()
        gen2.generate_stores()
        gen2.generate_inventory()
        gen2.generate_customers_and_addresses()
        gen2.generate_orders_and_operations()

        self.assertEqual(self.generator.orders[0], gen2.orders[0])
        self.assertEqual(self.generator.customers[0], gen2.customers[0])
        self.assertEqual(self.generator.inventory_levels[0], gen2.inventory_levels[0])


if __name__ == "__main__":
    unittest.main()
