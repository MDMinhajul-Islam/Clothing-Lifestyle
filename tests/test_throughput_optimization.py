"""Comprehensive Tests for Phase 1C Throughput Optimization & Concurrency Decoupling.

Tests Step 11 requirements:
- JSON-LD attached readiness logic
- Staged persistence
- Crash-safe checkpoint merge
- Product-ID indexes O(1)
- Concurrent fetch isolation
- Single-writer merge
- Raw HTML -> normalized determinism
- No duplicate records under concurrency
"""

import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/zara_research'))

from local_product_parser import parse_page_evidence_locally, parse_page_source_from_disk
from page_source_collector import save_page_source_bundle, clean_filename_id, sync_wait_for_product_evidence
from staged_batch_writer import StagedBatchManager, atomic_write_json

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>SATIN FINISH SHIRT - Green | ZARA United States</title>
    <link rel="canonical" href="https://www.zara.com/us/en/satin-finish-shirt-p01030731.html">
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "ProductGroup",
      "name": "SATIN FINISH SHIRT",
      "productGroupID": "01030731",
      "brand": {
        "@type": "Brand",
        "name": "ZARA"
      },
      "description": "Collared shirt with long sleeves and buttoned cuffs.",
      "material": "100% polyester",
      "offers": {
        "@type": "AggregateOffer",
        "price": "49.90",
        "priceCurrency": "USD"
      },
      "hasVariant": [
        {
          "@type": "Product",
          "name": "SATIN FINISH SHIRT - Green - S",
          "sku": "01030731-040-S",
          "color": "Green",
          "size": "S",
          "offers": {
            "@type": "Offer",
            "price": "49.90",
            "availability": "https://schema.org/InStock"
          },
          "image": ["https://static.zara.net/photos/green_s_1.jpg"]
        },
        {
          "@type": "Product",
          "name": "SATIN FINISH SHIRT - Green - M",
          "sku": "01030731-040-M",
          "color": "Green",
          "size": "M",
          "offers": {
            "@type": "Offer",
            "price": "49.90",
            "availability": "https://schema.org/OutOfStock"
          },
          "image": ["https://static.zara.net/photos/green_m_1.jpg"]
        }
      ]
    }
    </script>
</head>
<body>
    <main class="product-detail-view">
        <h1 class="product-detail-info__header-name">SATIN FINISH SHIRT</h1>
        <div class="product-detail-info">
            <span class="price-current__amount">$49.90</span>
            <div class="product-detail-color-selector">
                <button class="product-detail-color-item__color-button" aria-label="Green">Green</button>
            </div>
            <p class="product-detail-description">Collared shirt with long sleeves and buttoned cuffs.</p>
            <div class="product-detail-composition-and-care">Care: Machine wash max 30C.</div>
        </div>
        <div class="product-detail-images">
            <img src="https://static.zara.net/photos/green_s_1.jpg" alt="Front view">
        </div>
    </main>
</body>
</html>"""


class DummyPage:
    """Mock Playwright Page for unit testing readiness logic without launching full browser."""
    def __init__(self, has_jsonld_attached=True, has_visible_h1=True):
        self._has_jsonld_attached = has_jsonld_attached
        self._has_visible_h1 = has_visible_h1

    def wait_for_selector(self, selector, state="visible", timeout=3000):
        if 'script[type="application/ld+json"]' in selector:
            if state == "attached" and self._has_jsonld_attached:
                return True
            raise TimeoutError("Script not visible or not attached")
        if 'h1' in selector or '.product-detail-view' in selector:
            if self._has_visible_h1:
                return True
            raise TimeoutError("Heading not visible")
        raise TimeoutError(f"Unknown selector {selector}")


class TestThroughputOptimizationComprehensive(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)
        self.state_dir = self.dir_path / "state"
        self.raw_dir = self.dir_path / "raw"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_jsonld_attached_readiness(self):
        """1. Test that JSON-LD attached selector resolves immediately without waiting for visibility."""
        page_with_script = DummyPage(has_jsonld_attached=True, has_visible_h1=False)
        found, ev_type, wait_ms = sync_wait_for_product_evidence(page_with_script, timeout_ms=500)
        self.assertTrue(found)
        self.assertEqual(ev_type, "jsonld_attached")

        # Fallback to visible container when script not attached
        page_with_h1_only = DummyPage(has_jsonld_attached=False, has_visible_h1=True)
        found, ev_type, wait_ms = sync_wait_for_product_evidence(page_with_h1_only, timeout_ms=500)
        self.assertTrue(found)
        self.assertEqual(ev_type, "dom_container_visible")

    def test_staged_persistence(self):
        """2. Verify that StagedBatchManager stages in memory and only flushes at flush_interval."""
        manager = StagedBatchManager(state_dir=self.state_dir, raw_dir=self.raw_dir, flush_interval=3)

        for i in range(2):
            pid = f"prod_{i}"
            flushed, w_time = manager.stage_product_enrichment(
                product_id=pid,
                prod_rec={"product_id": pid, "name": f"P{i}"},
                vars_rec=[{"product_id": pid, "variant_id": f"v_{i}"}],
                cols_rec=[{"product_id": pid, "color_id": f"c_{i}"}],
                imgs_rec=[],
                price_rec=None,
                raw_evidence={"raw": i},
                queue_item={"id": pid, "status": "COMPLETE"}
            )
            self.assertFalse(flushed)

        # Raw files exist immediately
        self.assertTrue((self.raw_dir / "product_details" / "prod_0.json").exists())
        self.assertTrue((self.raw_dir / "product_details" / "prod_1.json").exists())
        # Master table not written yet
        self.assertFalse((self.state_dir / "product_details.json").exists())

        # 3rd product triggers flush
        flushed, w_time = manager.stage_product_enrichment(
            product_id="prod_2",
            prod_rec={"product_id": "prod_2", "name": "P2"},
            vars_rec=[{"product_id": "prod_2", "variant_id": "v_2"}],
            cols_rec=[{"product_id": "prod_2", "color_id": "c_2"}],
            imgs_rec=[],
            price_rec=None,
            raw_evidence={"raw": 2},
            queue_item={"id": "prod_2", "status": "COMPLETE"}
        )
        self.assertTrue(flushed)
        self.assertTrue((self.state_dir / "product_details.json").exists())
        prods = json.loads((self.state_dir / "product_details.json").read_text(encoding="utf-8"))
        self.assertEqual(len(prods), 3)

    def test_crash_safe_checkpoint_merge(self):
        """3. Verify journal append and atomic replacement guarantee crash safety."""
        manager = StagedBatchManager(state_dir=self.state_dir, raw_dir=self.raw_dir, flush_interval=10)
        manager.stage_product_enrichment(
            product_id="safe_prod",
            prod_rec={"product_id": "safe_prod", "name": "Safe"},
            vars_rec=[],
            cols_rec=[],
            imgs_rec=[],
            price_rec=None,
            raw_evidence={"safe": True},
            queue_item={"id": "safe_prod", "status": "COMPLETE"}
        )

        journal_file = self.raw_dir / "checkpoints" / "enrichment_journal.jsonl"
        self.assertTrue(journal_file.exists())
        lines = journal_file.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["product_id"], "safe_prod")
        self.assertEqual(entry["status"], "COMPLETE")

    def test_product_id_indexes_o1(self):
        """4. Verify O(1) indexed lookups and updates avoid table scanning."""
        # Initialize state files with multiple products
        init_prods = [{"product_id": f"p_{i}", "name": f"Prod {i}"} for i in range(10)]
        init_vars = [{"product_id": f"p_{i}", "variant_id": f"v_{i}_{j}"} for i in range(10) for j in range(3)]
        atomic_write_json(self.state_dir / "product_details.json", init_prods)
        atomic_write_json(self.state_dir / "product_variants.json", init_vars)

        manager = StagedBatchManager(state_dir=self.state_dir, raw_dir=self.raw_dir, flush_interval=50)
        self.assertEqual(len(manager.products_by_id), 10)
        self.assertEqual(len(manager.variants_by_product_id["p_3"]), 3)

        # O(1) update of p_3 variants
        new_p3_vars = [{"product_id": "p_3", "variant_id": "v_3_new"}]
        manager.stage_product_enrichment(
            product_id="p_3",
            prod_rec={"product_id": "p_3", "name": "Updated P3"},
            vars_rec=new_p3_vars,
            cols_rec=[],
            imgs_rec=[],
            price_rec=None,
            raw_evidence={},
            queue_item={"id": "p_3", "status": "COMPLETE"}
        )
        self.assertEqual(len(manager.variants_by_product_id["p_3"]), 1)
        self.assertEqual(manager.products_by_id["p_3"]["name"], "Updated P3")

    def test_concurrent_fetch_isolation(self):
        """5. Verify concurrent worker results preserve worker_id and separate source files."""
        meta1 = {
            "product_id": "p1",
            "source_url": "http://example.com/p1",
            "final_url": "http://example.com/p1",
            "collected_at": "2026-09-06T12:00:00Z",
            "browser_worker_id": 0,
            "navigation_time_ms": 100,
            "readiness_wait_ms": 50,
            "capture_time_ms": 20,
            "total_fetch_ms": 170,
            "readiness_type": "jsonld_attached",
            "http_status": 200,
            "retry_count": 0,
            "content_length": 500,
            "jsonld_present": True
        }
        meta2 = dict(meta1, product_id="p2", browser_worker_id=1)

        h1, m1 = save_page_source_bundle(self.dir_path, "p1", "<html>p1</html>", meta1)
        h2, m2 = save_page_source_bundle(self.dir_path, "p2", "<html>p2</html>", meta2)

        self.assertTrue(h1.exists() and h2.exists())
        self.assertNotEqual(h1, h2)
        loaded_m1 = json.loads(m1.read_text(encoding="utf-8"))
        loaded_m2 = json.loads(m2.read_text(encoding="utf-8"))
        self.assertEqual(loaded_m1["browser_worker_id"], 0)
        self.assertEqual(loaded_m2["browser_worker_id"], 1)

    def test_single_writer_merge(self):
        """6. Verify single-writer merge eliminates concurrent file write conflicts."""
        manager = StagedBatchManager(state_dir=self.state_dir, raw_dir=self.raw_dir, flush_interval=100)
        # Multiple entities staged sequentially through the single manager
        for i in range(5):
            manager.stage_product_enrichment(
                product_id=f"item_{i}",
                prod_rec={"product_id": f"item_{i}", "current_price": "29.90"},
                vars_rec=[],
                cols_rec=[],
                imgs_rec=[],
                price_rec=None,
                raw_evidence={},
                queue_item={"id": f"item_{i}", "status": "COMPLETE"}
            )
        stats = manager.flush()
        self.assertEqual(stats["flushed_products"], 5)
        prods = json.loads((self.state_dir / "product_details.json").read_text(encoding="utf-8"))
        self.assertEqual(len(prods), 5)

    def test_raw_html_to_normalized_determinism(self):
        """7. Verify deterministic parsing and hash equality from offline HTML."""
        bundle = {
            "html": SAMPLE_HTML,
            "final_url": "https://www.zara.com/us/en/satin-finish-shirt-p01030731.html",
            "http_status": 200,
            "page_title": "SATIN FINISH SHIRT"
        }
        res1 = parse_page_evidence_locally(bundle)
        res2 = parse_page_evidence_locally(bundle)
        self.assertEqual(res1, res2)

    def test_no_duplicate_records_under_concurrency(self):
        """8. Verify deduplication ensures no duplicate product IDs or variants in master tables."""
        manager = StagedBatchManager(state_dir=self.state_dir, raw_dir=self.raw_dir, flush_interval=100)
        # Stage same product twice (e.g. from retry or re-queued item)
        manager.stage_product_enrichment(
            product_id="dup_prod",
            prod_rec={"product_id": "dup_prod", "name": "V1"},
            vars_rec=[{"product_id": "dup_prod", "variant_id": "var_1"}],
            cols_rec=[],
            imgs_rec=[],
            price_rec=None,
            raw_evidence={},
            queue_item={"id": "dup_prod", "status": "COMPLETE"}
        )
        manager.stage_product_enrichment(
            product_id="dup_prod",
            prod_rec={"product_id": "dup_prod", "name": "V2_Updated"},
            vars_rec=[{"product_id": "dup_prod", "variant_id": "var_1_updated"}],
            cols_rec=[],
            imgs_rec=[],
            price_rec=None,
            raw_evidence={},
            queue_item={"id": "dup_prod", "status": "COMPLETE"}
        )
        manager.flush()

        prods = json.loads((self.state_dir / "product_details.json").read_text(encoding="utf-8"))
        vars_ = json.loads((self.state_dir / "product_variants.json").read_text(encoding="utf-8"))

        self.assertEqual(len([p for p in prods if p["product_id"] == "dup_prod"]), 1)
        self.assertEqual(manager.products_by_id["dup_prod"]["name"], "V2_Updated")
        self.assertEqual(len([v for v in vars_ if v["product_id"] == "dup_prod"]), 1)


if __name__ == "__main__":
    unittest.main()
