import unittest
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/zara_research'))

from card_id_resolver import extract_url_token, resolve_single_card_identity


class TestCardIdResolver(unittest.TestCase):

    def setUp(self):
        self.mock_unique_map = {
            "zara-us:01030731": {
                "product_id": "zara-us:01030731",
                "source_product_id": "01030731",
                "public_card_ids": ["9062989924", "571545044"],
                "product_url": "https://www.zara.com/us/en/striped-boxy-fit-shirt-p01030731.html"
            },
            "zara-us:9803295922": {
                "product_id": "zara-us:9803295922",
                "source_product_id": "9803295922",
                "public_card_ids": [],
                "product_url": "https://www.zara.com/us/en/checked-regular-fit-suit-pT9803295922.html"
            }
        }

    def test_extract_url_token(self):
        self.assertEqual(extract_url_token("https://www.zara.com/us/en/shirt-p01030731.html"), "01030731")
        self.assertEqual(extract_url_token("https://www.zara.com/us/en/suit-pT9803295922.html"), "9803295922")
        self.assertIsNone(extract_url_token(None))
        self.assertIsNone(extract_url_token(""))

    def test_non_card_id_passthrough(self):
        res = resolve_single_card_identity("zara-us:01030731", unique_products_map=self.mock_unique_map)
        self.assertEqual(res["status"], "RESOLVED")
        self.assertEqual(res["canonical_product_id"], "zara-us:01030731")

    def test_resolve_via_public_card_id_association(self):
        # Card ID '571545044' is already known to belong to 'zara-us:01030731'
        res = resolve_single_card_identity(
            "zara-us:card-571545044",
            url=None,
            unique_products_map=self.mock_unique_map
        )
        self.assertEqual(res["status"], "RESOLVED")
        self.assertEqual(res["canonical_product_id"], "zara-us:01030731")
        self.assertIn("PUBLIC_CARD_ID_ASSOCIATION", res["evidence"])

    def test_resolve_via_direct_url(self):
        # Card ID with a direct URL that points to a distinct product token
        res = resolve_single_card_identity(
            "zara-us:card-575713575",
            url="https://www.zara.com/us/en/checked-regular-fit-suit-pT9803295922.html",
            unique_products_map=self.mock_unique_map
        )
        self.assertEqual(res["status"], "RESOLVED")
        self.assertEqual(res["canonical_product_id"], "zara-us:9803295922")

    def test_unresolved_listing_card_without_url(self):
        # Card ID with no URL, no matching public_card_id, no source ID match
        res = resolve_single_card_identity(
            "zara-us:card-587709140",
            url=None,
            unique_products_map=self.mock_unique_map
        )
        self.assertEqual(res["status"], "UNRESOLVED")
        self.assertIsNone(res["canonical_product_id"])
        self.assertEqual(res["failure_reason"], "UNRESOLVED_LISTING_CARD_IDENTITY")


if __name__ == '__main__':
    unittest.main()
