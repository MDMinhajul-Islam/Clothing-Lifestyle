import unittest
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/zara_research'))

from local_product_parser import (
    parse_price,
    parse_product_group_jsonld,
    parse_page_evidence_locally
)
from enrich_product_details import (
    build_normalized_records,
    compute_content_hash,
    filter_valid_product_images,
    canonicalize_image_asset_key
)


class TestLocalProductParser(unittest.TestCase):

    def setUp(self):
        self.sample_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>ZW COLLECTION POPLIN SHIRT - White | ZARA United States</title>
            <link rel="canonical" href="https://www.zara.com/us/en/zw-collection-poplin-shirt-p02157232.html" />
            <script type="application/ld+json">
            {
                "@context": "https://schema.org/",
                "@type": "ProductGroup",
                "name": "ZW COLLECTION POPLIN SHIRT",
                "url": "https://www.zara.com/us/en/zw-collection-poplin-shirt-p02157232.html",
                "productGroupID": "02157232",
                "brand": {"@type": "Brand", "name": "ZARA"},
                "description": "Shirt made of poplin fabric with lapel collar.",
                "material": "100% cotton",
                "additionalProperty": [
                    {"@type": "PropertyValue", "name": "OUTER SHELL", "value": "100% cotton"}
                ],
                "offers": {
                    "@type": "Offer",
                    "priceCurrency": "USD",
                    "price": "49.90"
                },
                "hasVariant": [
                    {
                        "@type": "Product",
                        "name": "ZW COLLECTION POPLIN SHIRT - White - XS",
                        "sku": "551234567-250-1",
                        "color": "White",
                        "size": "XS",
                        "offers": {
                            "@type": "Offer",
                            "priceCurrency": "USD",
                            "price": "49.90",
                            "availability": "https://schema.org/InStock"
                        }
                    },
                    {
                        "@type": "Product",
                        "name": "ZW COLLECTION POPLIN SHIRT - White - S",
                        "sku": "551234567-250-2",
                        "color": "White",
                        "size": "S",
                        "offers": {
                            "@type": "Offer",
                            "priceCurrency": "USD",
                            "price": "49.90",
                            "availability": "https://schema.org/OutOfStock"
                        }
                    }
                ]
            }
            </script>
        </head>
        <body>
            <h1>ZW COLLECTION POPLIN SHIRT</h1>
            <div class="product-detail-description">Shirt made of poplin fabric with lapel collar. Long sleeves.</div>
            <div class="product-detail-extra-detail">COMPOSITION: 100% cotton</div>
            <div class="price-current__amount">$49.90</div>
            <div class="price-old__amount">$69.90</div>
            <div class="price-sale__amount">$49.90</div>
            <div class="product-detail-color-selector">
                <button aria-label="White">White</button>
                <button aria-label="Sky Blue">Sky Blue</button>
            </div>
            <div class="product-detail-images">
                <img src="https://static.zara.net/assets/public/1234/02157232250-p/02157232250-p.jpg?w=1024" alt="Front view" />
                <img src="https://static.zara.net/assets/public/1234/02157232250-a1/02157232250-a1.jpg?w=1024" alt="Back view" />
            </div>
            <span>Ref: 2157/232/250</span>
        </body>
        </html>
        """

    def test_parse_price(self):
        self.assertEqual(parse_price("49.90"), "49.90")
        self.assertEqual(parse_price("$69.90"), "69.90")
        self.assertEqual(parse_price("  $ 129.00 USD "), "129.00")
        self.assertEqual(parse_price(45.5), "45.50")
        self.assertIsNone(parse_price("N/A"))
        self.assertIsNone(parse_price(None))

    def test_soup_local_parsing(self):
        bundle = {
            "html": self.sample_html,
            "final_url": "https://www.zara.com/us/en/zw-collection-poplin-shirt-p02157232.html",
            "http_status": 200,
            "page_title": "ZW COLLECTION POPLIN SHIRT - White | ZARA United States"
        }
        evidence = parse_page_evidence_locally(bundle)

        self.assertEqual(evidence["canonical_url"], "https://www.zara.com/us/en/zw-collection-poplin-shirt-p02157232.html")
        self.assertEqual(evidence["main_heading"], "ZW COLLECTION POPLIN SHIRT")
        self.assertEqual(len(evidence["parsed_product_groups"]), 1)
        self.assertEqual(evidence["commercial_ref"], "2157/232/250")
        self.assertEqual(evidence["rendered_price"], "49.90")
        self.assertEqual(evidence["rendered_old_price"], "69.90")
        self.assertEqual(evidence["rendered_sale_price"], "49.90")
        self.assertIn("White", evidence["dom_colors"])
        self.assertIn("Sky Blue", evidence["dom_colors"])
        self.assertEqual(len(evidence["raw_images"]), 2)

    def test_has_variant_non_cartesian(self):
        bundle = {
            "html": self.sample_html,
            "final_url": "https://www.zara.com/us/en/zw-collection-poplin-shirt-p02157232.html",
            "http_status": 200,
            "page_title": "ZW COLLECTION POPLIN SHIRT"
        }
        evidence = parse_page_evidence_locally(bundle)
        global_p = {
            "product_id": "zara-us:02157232",
            "source_product_id": "02157232",
            "product_url": bundle["final_url"],
            "first_seen_category": "/woman-shirts-l1221.html"
        }
        prod, variants, colors, images, img_stats, price_stats = build_normalized_records(evidence, global_p, "2026-09-06T12:00:00Z")

        # Explicit non-Cartesian check: exactly 2 variants matching JSON-LD, not 2 sizes x 2 colors = 4!
        self.assertEqual(len(variants), 2)
        skus = [v["sku"] for v in variants]
        self.assertEqual(skus, ["551234567-250-1", "551234567-250-2"])
        self.assertEqual(variants[0]["public_availability_state"], "IN_STOCK")
        self.assertEqual(variants[1]["public_availability_state"], "OUT_OF_STOCK")

    def test_sale_detection_and_pricing(self):
        bundle = {
            "html": self.sample_html,
            "final_url": "https://www.zara.com/us/en/zw-collection-poplin-shirt-p02157232.html",
            "http_status": 200,
            "page_title": "ZW COLLECTION POPLIN SHIRT"
        }
        evidence = parse_page_evidence_locally(bundle)
        global_p = {
            "product_id": "zara-us:02157232",
            "source_product_id": "02157232",
            "product_url": bundle["final_url"],
            "first_seen_category": "/woman-shirts-l1221.html"
        }
        prod, variants, colors, images, img_stats, price_stats = build_normalized_records(evidence, global_p, "2026-09-06T12:00:00Z")

        self.assertEqual(prod["current_price"], "49.90")
        self.assertEqual(prod["original_price"], "69.90")
        self.assertEqual(prod["sale_price"], "49.90")
        self.assertTrue(prod["is_on_sale"])

    def test_deterministic_content_hash(self):
        bundle = {
            "html": self.sample_html,
            "final_url": "https://www.zara.com/us/en/zw-collection-poplin-shirt-p02157232.html",
            "http_status": 200,
            "page_title": "ZW COLLECTION POPLIN SHIRT"
        }
        evidence = parse_page_evidence_locally(bundle)
        global_p = {
            "product_id": "zara-us:02157232",
            "source_product_id": "02157232",
            "product_url": bundle["final_url"],
            "first_seen_category": "/woman-shirts-l1221.html"
        }
        prod, variants, colors, images, _, _ = build_normalized_records(evidence, global_p, "2026-09-06T12:00:00Z")
        hash1 = prod["source_content_hash"]
        
        # Second run with identical content
        prod2, variants2, colors2, images2, _, _ = build_normalized_records(evidence, global_p, "2026-09-06T12:05:00Z")
        hash2 = prod2["source_content_hash"]
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)


if __name__ == '__main__':
    unittest.main()
