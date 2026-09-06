import os
import unittest
from decimal import Decimal
from pathlib import Path

import sys
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.supabase.import_catalogue import (
    CatalogueDataLoader,
    DryRunRelationalValidator,
    canonicalize_image_asset_key,
    chunk_list,
    extract_category_slug,
    slugify,
)


class TestSupabaseImport(unittest.TestCase):
    """Test suite for Supabase schema mapping, transformation, batching, and import pipeline."""

    def setUp(self):
        self.loader = CatalogueDataLoader()

    def test_numeric_price_parsing(self):
        """Test transformation of price fields to numeric floats/decimals."""
        sample_raw = [{
            "product_id": "zara-us:test01",
            "exact_product_name": "Test Shirt",
            "department": "MAN",
            "current_price": "49.90",
            "original_price": "79.90",
            "sale_price": "49.90",
            "is_on_sale": True,
        }]
        transformed = self.loader._transform_products(sample_raw)
        self.assertEqual(len(transformed), 1)
        p = transformed[0]
        self.assertEqual(p["current_price"], 49.90)
        self.assertEqual(p["original_price"], 79.90)
        self.assertEqual(p["sale_price"], 49.90)
        self.assertTrue(p["is_on_sale"])

    def test_null_price_handling(self):
        """Test that missing or null prices map to None safely."""
        sample_raw = [{
            "product_id": "zara-us:test02",
            "exact_product_name": "Test Jacket",
            "department": "WOMAN",
            "current_price": "129.00",
            "original_price": None,
            "sale_price": None,
            "is_on_sale": False,
        }]
        transformed = self.loader._transform_products(sample_raw)
        p = transformed[0]
        self.assertEqual(p["current_price"], 129.00)
        self.assertIsNone(p["original_price"])
        self.assertIsNone(p["sale_price"])
        self.assertFalse(p["is_on_sale"])

    def test_category_topological_sorting(self):
        """Test that categories with parent references are topologically ordered."""
        raw_cats = [
            {"category_id": "child_1", "parent_category_id": "parent_1", "name": "Child Category"},
            {"category_id": "grandchild_1", "parent_category_id": "child_1", "name": "Grandchild"},
            {"category_id": "parent_1", "parent_category_id": None, "name": "Root Parent"},
            {"category_id": "independent", "parent_category_id": None, "name": "Independent"},
        ]
        ordered = self.loader._transform_categories(raw_cats)
        self.assertEqual(len(ordered), 4)

        seen = set()
        for c in ordered:
            pid = c.get("parent_category_id")
            if pid:
                self.assertIn(pid, seen, f"Parent {pid} must be ordered before child {c['category_id']}")
            seen.add(c["category_id"])

    def test_product_colors_disambiguation(self):
        """Test that casing duplicates in color slugs are disambiguated."""
        raw_colors = [
            {"color_id": "zara-us:01:striped", "product_id": "zara-us:01", "color_name": "Striped", "display_order": 0},
            {"color_id": "zara-us:01:striped", "product_id": "zara-us:01", "color_name": "striped", "display_order": 1},
        ]
        transformed = self.loader._transform_colors(raw_colors)
        self.assertEqual(len(transformed), 2)
        color_ids = [c["color_id"] for c in transformed]
        self.assertEqual(len(set(color_ids)), 2, "Color IDs must be unique after disambiguation")
        self.assertEqual(color_ids[0], "zara-us:01:striped")
        self.assertEqual(color_ids[1], "zara-us:01:striped-1")

    def test_canonicalize_image_asset_key(self):
        """Test extraction of clean image asset key without CDN query parameters."""
        url = "https://static.zara.net/assets/public/c3e1/96d8/4e18/03152205485-p.jpg?ts=1783689777150&w=1920"
        key = canonicalize_image_asset_key(url)
        self.assertEqual(key, "static.zara.net/assets/public/c3e1/96d8/4e18/03152205485-p.jpg")

    def test_batching_generator(self):
        """Test chunk_list generator splits items correctly."""
        items = list(range(105))
        chunks = list(chunk_list(items, batch_size=50))
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 50)
        self.assertEqual(len(chunks[1]), 50)
        self.assertEqual(len(chunks[2]), 5)

    def test_product_categories_skips_unresolved_cards(self):
        """Test that product-category edges pointing to un-enriched card identities are skipped."""
        self.loader.valid_product_ids = {"zara-us:valid_p1", "zara-us:valid_p2"}
        raw_edges = [
            {"product_id": "zara-us:valid_p1", "category_id": "cat_1"},
            {"product_id": "zara-us:card-99999", "category_id": "cat_1"},  # un-enriched card
            {"product_id": "zara-us:valid_p2", "category_id": "cat_2"},
        ]
        transformed = self.loader._transform_product_categories(raw_edges)
        self.assertEqual(len(transformed), 2)
        self.assertEqual(self.loader.skipped_card_category_edges, 1)
        self.assertEqual([e["product_id"] for e in transformed], ["zara-us:valid_p1", "zara-us:valid_p2"])

    def test_price_history_deterministic_keys(self):
        """Test deterministic primary key generation for price history snapshots."""
        raw_hist = [
            {"product_id": "zara-us:01", "observed_at": "2026-09-06T12:00:00Z", "current_price": "59.90", "is_on_sale": False},
            {"product_id": "zara-us:02", "observed_at": "2026-09-06T12:00:00Z", "current_price": "89.90", "is_on_sale": True},
        ]
        transformed = self.loader._transform_price_history(raw_hist)
        self.assertEqual(len(transformed), 2)
        self.assertEqual(transformed[0]["history_id"], "zara-us:01:2026-09-06T12:00:00Z")
        self.assertEqual(transformed[1]["history_id"], "zara-us:02:2026-09-06T12:00:00Z")

    def test_sync_state_preserves_failed_terminal_cards(self):
        """Test that FAILED_TERMINAL card identities are preserved in catalogue_sync_state."""
        self.loader.products = [{"product_id": "zara-us:prod1", "canonical_url": "https://zara.com/p1", "first_seen_at": "t1", "last_seen_at": "t2"}]
        raw_queue = [
            {"id": "zara-us:prod1", "status": "COMPLETE", "url": "https://zara.com/p1", "attempt_count": 1, "last_attempt_at": "t2"},
            {"id": "zara-us:card-555", "status": "FAILED_TERMINAL", "url": None, "attempt_count": 0, "last_attempt_at": "t3", "error": "UNRESOLVED_CARD"},
        ]
        transformed = self.loader._transform_sync_state(raw_queue)
        self.assertEqual(len(transformed), 2)
        self.assertEqual(transformed[0]["product_id"], "zara-us:prod1")
        self.assertEqual(transformed[0]["status"], "COMPLETE")
        self.assertIsNone(transformed[1]["product_id"])
        self.assertEqual(transformed[1]["status"], "FAILED_TERMINAL")
        self.assertEqual(transformed[1]["last_error"], "UNRESOLVED_CARD")


if __name__ == "__main__":
    unittest.main()
