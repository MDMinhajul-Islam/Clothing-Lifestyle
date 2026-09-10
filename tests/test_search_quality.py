import unittest
from types import SimpleNamespace

from backend.app.orchestrator.schemas import Route
from backend.app.schemas.catalogue import SearchProductsInput
from backend.app.services.catalogue_service import CatalogueService
from backend.app.voice.composer import VoiceResponseComposer


BLACK_VARIANT = {
    "variant_id": "zara-us:00387161:black-m", "sku": "BLACK-M", "color": "Black",
    "size": "M", "availability_state": "IN_STOCK", "in_stock": True,
    "image_url": "https://example.test/black-dress.jpg",
    "gallery_urls": ["https://example.test/black-dress.jpg", "https://example.test/black-detail.jpg"],
    "price": 69.9,
}
ROW = {
    "product_id": "zara-us:00387161", "name": "DRAPED MINI DRESS WITH HARDWARE",
    "department": "WOMAN", "price": 69.9, "currency": "USD", "is_on_sale": False,
    "original_price": None, "colors": ["Black", "Blue"], "sizes": ["S", "M"],
    "primary_image_url": BLACK_VARIANT["image_url"], "matched_variant": BLACK_VARIANT,
}


class FakeEmbedding:
    def embed(self, texts):
        self.texts = texts
        return [[0.01] * 384]


class FakeRepo:
    def search_products(self, **kwargs):
        self.calls = getattr(self, "calls", []) + [kwargs]
        self.arguments = kwargs
        return (0, []) if kwargs.get("occasion") in {"wedding", "office", "evening", "casual", "eid"} else (1, [ROW])


class EmptyRepo(FakeRepo):
    def search_products(self, **kwargs):
        self.calls = getattr(self, "calls", []) + [kwargs]
        self.arguments = kwargs
        return 0, []


class ExactPhraseMissRepo(FakeRepo):
    def search_products(self, **kwargs):
        self.calls = getattr(self, "calls", []) + [kwargs]
        self.arguments = kwargs
        return (0, []) if kwargs.get("query") else (1, [ROW])


class SearchQualityTests(unittest.TestCase):
    def service(self):
        service = CatalogueService.__new__(CatalogueService)
        service.repo = FakeRepo()
        service.embedding_client = FakeEmbedding()
        return service

    def assert_facets(self, query, *, product_type, color=None, residual=None):
        service = self.service()
        service.search_products(SearchProductsInput(query=query))
        args = service.repo.arguments
        self.assertEqual(args["product_type"], product_type)
        self.assertEqual(args["color"], color)
        self.assertEqual(args["query"], residual)
        self.assertEqual(len(args["semantic_vector"]), 384)
        return args

    def test_structured_facets_precede_semantic_ranking(self):
        for query, kind, color in (("black dress", "dress", "black"),
                                   ("white shirt", "shirt", "white"),
                                   ("blue jeans", "jeans", "blue"),
                                   ("red blazer", "blazer", "red")):
            with self.subTest(query=query):
                self.assert_facets(query, product_type=kind, color=color)

    def test_wedding_requests_extract_an_occasion_without_ignoring_it(self):
        service = self.service()
        result = service.search_products(SearchProductsInput(query="black wedding dress"))
        initial = service.repo.calls[0]
        self.assertIsNone(initial["query"])
        self.assertEqual(initial["occasion"], "wedding")
        self.assertEqual(initial["product_type"], "dress")
        self.assertEqual(initial["color"], "black")
        self.assertEqual(service.repo.calls[1]["occasion"], None)
        self.assertEqual(result.total_matching, 1)

    def test_spoken_hundred_is_an_authoritative_price_filter(self):
        args = self.assert_facets(
            "black formal dresses under one hundred dollars",
            product_type="dress", color="black", residual=None,
        )
        self.assertEqual(args["occasion"], "formal")
        self.assertEqual(args["max_price"], 100.0)

    def test_spoken_polo_request_removes_conversational_fillers(self):
        args = self.assert_facets(
            "Hi. I am looking for a Polo t shirt. Under one hundred dollars. Can you help me?",
            product_type="shirt", residual="polo",
        )
        self.assertEqual(args["max_price"], 100.0)

    def test_empty_occasion_fallback_never_claims_products_were_found(self):
        service = self.service()
        service.repo = EmptyRepo()
        result = service.search_products(SearchProductsInput(
            query="black formal dresses under one hundred dollars"))
        self.assertEqual(result.products, [])
        self.assertNotIn("I found", result.fallback_message)
        self.assertIn("formal-specific dress", result.fallback_message)
        self.assertEqual(service.repo.calls[-1]["product_type"], "dress")
        self.assertEqual(service.repo.calls[-1]["color"], "black")
        self.assertEqual(service.repo.calls[-1]["max_price"], 100.0)

    def test_dress_shoes_are_shoes_not_dresses(self):
        self.assert_facets("dress shoes", product_type="shoes", residual="dress")

    def test_matching_variant_is_preserved_in_result(self):
        result = self.service().search_products(SearchProductsInput(query="black dress"))
        card = result.products[0]
        self.assertEqual(card.matched_variant.color, "Black")
        self.assertEqual(card.matched_variant.sku, "BLACK-M")
        self.assertTrue(card.matched_variant.in_stock)
        self.assertEqual(card.primary_image_url, card.matched_variant.image_url)
        self.assertEqual(card.matched_variant.gallery_urls[1], "https://example.test/black-detail.jpg")

    def test_occasion_taxonomy_and_graceful_fallbacks(self):
        cases = (
            ("wedding dress", "wedding", "dress", True),
            ("office outfit", "office", None, True),
            ("party dress", "party", "dress", False),
            ("evening dress", "evening", "dress", True),
            ("casual shirt", "casual", "shirt", True),
            ("Eid collection", "eid", None, True),
        )
        for query, occasion, product_type, unavailable in cases:
            with self.subTest(query=query):
                service = self.service()
                result = service.search_products(SearchProductsInput(query=query))
                self.assertEqual(service.repo.calls[0]["occasion"], occasion)
                self.assertEqual(service.repo.calls[0]["product_type"], product_type)
                if unavailable:
                    self.assertEqual(result.returned_count, 1)
                    self.assertIsNone(service.repo.calls[1]["occasion"])
                    self.assertIn(f"{occasion}-specific", result.fallback_message)
                    self.assertIn("I found", result.fallback_message)
                else:
                    self.assertEqual(result.returned_count, 1)
                    self.assertIsNone(result.fallback_message)

    def test_voice_composer_speaks_grounded_occasion_fallback(self):
        decision = SimpleNamespace(route=Route.TOOL_GATEWAY, intent="SEARCH_PRODUCTS")
        message = VoiceResponseComposer().compose(decision, {
            "products": [], "fallback_message": "I couldn't find wedding-specific dresses. I can show elegant formal dresses."
        }, "SUCCESS")
        self.assertIn("wedding-specific", message)
        self.assertNotIn("completed successfully", message)

    def test_residual_wording_relaxes_to_semantic_ranking_inside_structured_candidates(self):
        service = self.service()
        service.repo = ExactPhraseMissRepo()
        result = service.search_products(SearchProductsInput(
            query="premium ribbed black polo shirt for the office under one hundred dollars",
            department="MAN",
        ))
        relaxed = service.repo.calls[-1]
        self.assertEqual(len(service.repo.calls), 3)
        self.assertIsNone(relaxed["query"])
        self.assertIsNone(relaxed["occasion"])
        self.assertEqual(relaxed["product_type"], "shirt")
        self.assertEqual(relaxed["department"], "MAN")
        self.assertEqual(relaxed["color"], "black")
        self.assertEqual(relaxed["max_price"], 100.0)
        self.assertEqual(len(relaxed["semantic_vector"]), 384)
        self.assertEqual(result.returned_count, 1)
        self.assertIn("closest shirt options", result.fallback_message)


if __name__ == "__main__":
    unittest.main()
