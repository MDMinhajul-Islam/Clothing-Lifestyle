import unittest
import json
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/zara_research'))

from enrich_product_details import (
    parse_product_group_jsonld,
    filter_valid_product_images,
    compute_content_hash,
    build_normalized_records,
    canonicalize_image_asset_key
)


class TestProductDetailEnrichment(unittest.TestCase):

    def setUp(self):
        # Sample raw JSON-LD from a real Zara ProductGroup
        self.sample_jsonld = {
            "@context": "https://schema.org/",
            "@type": "ProductGroup",
            "name": "WASHED-EFFECT RELAXED-FIT SHIRT",
            "url": "https://www.zara.com/us/en/relaxed-fit-washed-effect-shirt-p00122342.html",
            "productGroupID": "00122342",
            "brand": {"@type": "Brand", "name": "ZARA"},
            "description": "Relaxed-fit shirt crafted from an ultra-lightweight cotton fabric.",
            "variesBy": ["https://schema.org/size", "https://schema.org/color"],
            "image": [
                "https://static.zara.net/assets/public/daa1/00122342412-p.jpg?ts=123&w=1920",
                "https://static.zara.net/assets/public/088d/00122342412-a1.jpg?ts=123&w=1920"
            ],
            "material": "100% cotton",
            "additionalProperty": [
                {
                    "@type": "PropertyValue",
                    "propertyID": "Composition",
                    "name": "OUTER SHELL",
                    "value": "100% cotton"
                }
            ],
            "hasVariant": [
                {
                    "@type": "Product",
                    "name": "WASHED-EFFECT RELAXED-FIT SHIRT - Blue marl - S",
                    "sku": "551789038-412-2",
                    "mpn": "551789038-412-2",
                    "color": "Blue marl",
                    "size": "S",
                    "image": ["https://static.zara.net/assets/public/daa1/00122342412-p.jpg?ts=123&w=1920"],
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "USD",
                        "price": "69.90",
                        "url": "https://www.zara.com/us/en/relaxed-fit-washed-effect-shirt-p00122342.html?v1=551789038",
                        "availability": "https://schema.org/InStock"
                    }
                },
                {
                    "@type": "Product",
                    "name": "WASHED-EFFECT RELAXED-FIT SHIRT - Blue marl - M",
                    "sku": "551789038-412-3",
                    "mpn": "551789038-412-3",
                    "color": "Blue marl",
                    "size": "M",
                    "image": ["https://static.zara.net/assets/public/daa1/00122342412-p.jpg?ts=123&w=1920"],
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "USD",
                        "price": "69.90",
                        "url": "https://www.zara.com/us/en/relaxed-fit-washed-effect-shirt-p00122342.html?v1=551789038",
                        "availability": "https://schema.org/OutOfStock"
                    }
                }
            ]
        }

    def test_parse_product_group_jsonld(self):
        parsed = parse_product_group_jsonld(self.sample_jsonld)
        self.assertEqual(parsed["name"], "WASHED-EFFECT RELAXED-FIT SHIRT")
        self.assertEqual(parsed["product_group_id"], "00122342")
        self.assertEqual(parsed["brand"], "ZARA")
        self.assertEqual(parsed["material"], "100% cotton")
        self.assertEqual(parsed["composition"], "OUTER SHELL: 100% cotton")
        self.assertEqual(len(parsed["variants"]), 2)
        self.assertEqual(parsed["variants"][0]["size_name"], "S")
        self.assertEqual(parsed["variants"][0]["public_availability_state"], "IN_STOCK")
        self.assertEqual(parsed["variants"][1]["size_name"], "M")
        self.assertEqual(parsed["variants"][1]["public_availability_state"], "OUT_OF_STOCK")

    def test_filter_valid_product_images(self):
        raw_images = [
            {"url": "https://static.zara.net/assets/public/daa1/00122342412-p.jpg?ts=123&w=1024", "alt": "Image 1"},
            {"url": "https://static.zara.net/stdstatic/10.1.1/images/transparent-background.png", "alt": "Transparent"},
            {"url": "https://static.zara.net/static/images/logo.svg", "alt": "Logo"},
            {"url": "https://static.zara.net/assets/public/088d/00122342412-a1.jpg?ts=123&w=1126", "alt": "Image 2"},
            {"url": "https://example.com/pixel.gif", "alt": "Tracking"}
        ]
        valid = filter_valid_product_images(raw_images, product_group_id="00122342")
        valid, dups_removed, raw_obs = filter_valid_product_images(raw_images, product_group_id="00122342")
        self.assertEqual(len(valid), 2)
        self.assertTrue(all("transparent-background" not in img["url"] for img in valid))
        self.assertTrue(all("logo.svg" not in img["url"] for img in valid))
        self.assertTrue(all("pixel.gif" not in img["url"] for img in valid))

    def test_image_delivery_parameter_deduplication(self):
        # Two URLs pointing to the exact same image asset with different delivery parameters (e.g. w=1024 vs w=1920 vs ts=999)
        raw_images = [
            {"url": "https://static.zara.net/assets/public/daa1/00122342412-p.jpg?ts=123&w=1024", "alt": "Image 1"},
            {"url": "https://static.zara.net/assets/public/daa1/00122342412-p.jpg?ts=999&w=1920", "alt": "Image 1 dup"},
            {"url": "https://static.zara.net/assets/public/088d/00122342412-a1.jpg?ts=123&w=1920", "alt": "Image 2"}
        ]
        valid, dups_removed, raw_obs = filter_valid_product_images(raw_images, product_group_id="00122342")
        self.assertEqual(len(valid), 2)
        self.assertEqual(dups_removed, 1)
        self.assertEqual(raw_obs, 3)
        self.assertEqual(valid[0]["asset_key"], "static.zara.net/assets/public/daa1/00122342412-p.jpg")

    def test_reject_foreign_product_images(self):
        # Image from recommendation carousel belonging to another product
        raw_images = [
            {"url": "https://static.zara.net/assets/public/daa1/00122342412-p.jpg?w=1920", "is_structured": False},
            {"url": "https://static.zara.net/assets/public/9999/03046283711-a2.jpg?w=1920", "is_structured": False}  # Other product!
        ]
        valid, dups_removed, _ = filter_valid_product_images(raw_images, product_group_id="00122342")
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]["url"], "https://static.zara.net/assets/public/daa1/00122342412-p.jpg?w=1920")

    def test_non_cartesian_variants(self):
        parsed = parse_product_group_jsonld(self.sample_jsonld)
        variants = parsed["variants"]
        color_sizes = [(v["color_name"], v["size_name"]) for v in variants]
        self.assertIn(("Blue marl", "S"), color_sizes)
        self.assertIn(("Blue marl", "M"), color_sizes)
        self.assertEqual(len(variants), 2)

    def test_content_hash_stability(self):
        product_record = {
            "exact_product_name": "WASHED-EFFECT RELAXED-FIT SHIRT",
            "currency": "USD",
            "current_price": "69.90",
            "original_price": None,
            "sale_price": None,
            "is_on_sale": False,
            "material_text": "100% cotton",
            "composition_text": "OUTER SHELL: 100% cotton"
        }
        colors = [{"color_name": "Blue marl"}]
        variants = [
            {"color_name": "Blue marl", "size_name": "S", "sku": "551789038-412-2", "public_availability_state": "IN_STOCK"},
            {"color_name": "Blue marl", "size_name": "M", "sku": "551789038-412-3", "public_availability_state": "OUT_OF_STOCK"}
        ]
        images = [
            {"source_image_url": "https://static.zara.net/assets/img1.jpg?w=1920", "display_order": 0},
            {"source_image_url": "https://static.zara.net/assets/img2.jpg?w=1920", "display_order": 1}
        ]

        hash1 = compute_content_hash(product_record, colors, variants, images)
        hash2 = compute_content_hash(product_record, colors, variants, images)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)

        product_record_with_time = dict(product_record)
        product_record_with_time["last_seen_at"] = "2026-09-06T14:30:00Z"
        hash3 = compute_content_hash(product_record_with_time, colors, variants, images)
        self.assertEqual(hash1, hash3)

        modified_product = dict(product_record, current_price="79.90")
        hash4 = compute_content_hash(modified_product, colors, variants, images)
        self.assertNotEqual(hash1, hash4)


if __name__ == '__main__':
    unittest.main()

