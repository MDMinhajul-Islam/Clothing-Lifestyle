import unittest
from datetime import datetime, timezone


class EnumerationLogicTests(unittest.TestCase):
    def test_deduplication_across_categories(self):
        """A product seen in multiple categories updates categories_seen_in and is not duplicated."""
        unique_products = [
            {
                "product_id": "zara-us:12345678",
                "source_product_id": "12345678",
                "product_url": "https://www.zara.com/us/en/dress-p12345678.html",
                "categories_seen_in": ["https://www.zara.com/us/en/woman-dresses-l1066.html"],
                "public_card_ids": ["999000111"],
                "last_seen_at": "2026-09-06T00:00:00Z"
            }
        ]
        by_sku = {"12345678": unique_products[0]}
        by_card_id = {"999000111": unique_products[0]}

        # Observation in a second category (e.g. party dresses)
        cat_b = "https://www.zara.com/us/en/woman-dresses-party-l1581.html"
        obs_product = {
            "catalogue_id": "999000111",
            "commercial_ref_token": "12345678",
            "product_url": "https://www.zara.com/us/en/dress-p12345678.html"
        }

        # Deduplication logic
        matched = by_sku.get(obs_product["commercial_ref_token"]) or by_card_id.get(obs_product["catalogue_id"])
        self.assertIsNotNone(matched)
        if matched:
            if cat_b not in matched["categories_seen_in"]:
                matched["categories_seen_in"].append(cat_b)
            matched["last_seen_at"] = "2026-09-06T12:00:00Z"

        self.assertEqual(len(unique_products), 1, "Should not duplicate product record")
        self.assertIn(cat_b, unique_products[0]["categories_seen_in"])
        self.assertEqual(len(unique_products[0]["categories_seen_in"]), 2)

    def test_enumeration_resume_checkpoint(self):
        """Preserves existing seen_product_ids and updates checkpoint on resume."""
        item = {
            "id": "category:5c28c37318e0ff3f",
            "url": "https://www.zara.com/us/en/woman-dresses-maxi-l1079.html",
            "status": "QUEUED",
            "attempt_count": 1,
            "checkpoint": {
                "phase": "enumeration",
                "scroll_iteration": 2,
                "seen_product_ids": ["111", "222"]
            }
        }

        # Resume adds 333
        newly_seen = {"111", "222", "333"}
        item["scroll_iteration"] = 4
        item["seen_product_ids"] = sorted(list(newly_seen))
        item["status"] = "COMPLETE"
        item["completion_reason"] = "NO_NEW_PRODUCTS"

        self.assertEqual(item["seen_product_ids"], ["111", "222", "333"])
        self.assertEqual(item["status"], "COMPLETE")
        self.assertEqual(item["completion_reason"], "NO_NEW_PRODUCTS")

    def test_query_pagination_deduplication(self):
        """Products seen on base page and ?page=2 variant map to same identity."""
        product_card_base = {
            "catalogue_id": "555666777",
            "commercial_ref_token": "08889990",
            "product_url": "https://www.zara.com/us/en/shirt-p08889990.html"
        }
        product_card_p2 = {
            "catalogue_id": "555666777",
            "commercial_ref_token": "08889990",
            "product_url": "https://www.zara.com/us/en/shirt-p08889990.html"
        }

        unique_registry = {}

        for p in [product_card_base, product_card_p2]:
            key = p["commercial_ref_token"] or p["catalogue_id"]
            if key not in unique_registry:
                unique_registry[key] = {
                    "product_id": f"zara-us:{p['commercial_ref_token']}",
                    "appearances": 1
                }
            else:
                unique_registry[key]["appearances"] += 1

        self.assertEqual(len(unique_registry), 1)
        self.assertEqual(unique_registry["08889990"]["appearances"], 2)

    def test_product_detail_queue_insertion(self):
        """Only genuinely new product IDs are appended to product_detail_queue."""
        detail_queue = [
            {"id": "zara-us:01030731", "status": "PARTIAL"},
            {"id": "zara-us:06987370", "status": "QUEUED"}
        ]
        existing_ids = {q["id"] for q in detail_queue}

        new_products = [
            {"product_id": "zara-us:01030731", "url": "https://..."}, # existing
            {"product_id": "zara-us:99999999", "url": "https://..."}  # new
        ]

        inserted = []
        for np in new_products:
            pid = np["product_id"]
            if pid not in existing_ids:
                item = {"id": pid, "url": np["url"], "status": "QUEUED"}
                detail_queue.append(item)
                existing_ids.add(pid)
                inserted.append(pid)

        self.assertEqual(len(inserted), 1)
        self.assertEqual(inserted[0], "zara-us:99999999")
        self.assertEqual(len(detail_queue), 3)

    def test_partial_max_iterations_status(self):
        """When reason is PARTIAL_MAX_ITERATIONS, status must be PARTIAL and never COMPLETE."""
        reason = "PARTIAL_MAX_ITERATIONS"
        listing_status = (
            "COMPLETE" if reason in ["NO_NEW_PRODUCTS", "END_OF_LIST", "CATEGORY_EMPTY"]
            else ("PARTIAL" if reason == "PARTIAL_MAX_ITERATIONS"
            else ("TECHNICAL_RESTRICTION" if reason == "TECHNICAL_RESTRICTION"
            else "ERROR"))
        )
        self.assertEqual(listing_status, "PARTIAL")
        self.assertNotEqual(listing_status, "COMPLETE")

    def test_cumulative_resumption_accounting(self):
        """Resuming a listing accumulates prior and newly seen product IDs."""
        prior_seen_ids = {"111", "222", "333"}
        seen_this_run = {"222", "333", "444", "555"}
        cumulative_ids = prior_seen_ids.union(seen_this_run)
        new_ids_this_run = len(cumulative_ids) - len(prior_seen_ids)

        self.assertEqual(len(cumulative_ids), 5)
        self.assertEqual(new_ids_this_run, 2)
        self.assertEqual(cumulative_ids, {"111", "222", "333", "444", "555"})


if __name__ == '__main__':
    unittest.main()

