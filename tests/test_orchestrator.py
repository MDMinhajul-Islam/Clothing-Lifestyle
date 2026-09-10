import unittest

from backend.app.orchestrator.schemas import Route, RouteRequest, RouteStatus
from backend.app.orchestrator.service import OrchestratorService


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.service = OrchestratorService()

    def route(self, message, **context):
        return self.service.route(RouteRequest(message=message, context=context))

    def test_return_policy(self):
        result = self.route("What is Zara's return policy?")
        self.assertEqual((result.route, result.intent), (Route.POLICY_RAG, "RETRIEVE_POLICY_KNOWLEDGE"))

    def test_return_eligibility_extracts_explicit_order(self):
        result = self.route("Can I return order ORD-123?")
        self.assertEqual(result.tool_name, "check_return_eligibility")
        self.assertEqual(result.tool_arguments["order_number"], "ORD-123")

    def test_create_return_preserves_gateway_confirmation(self):
        result = self.route("Start a return for order ORD-123",
                            access_token="verified-token", return_method="STORE")
        self.assertEqual(result.tool_name, "create_return")
        self.assertTrue(result.requires_confirmation)
        self.assertEqual(result.status, RouteStatus.NEEDS_CONTEXT)
        self.assertEqual(result.missing_fields, ["items"])

    def test_track_order(self):
        self.assertEqual(self.route("Where is my order ORD-123?").tool_name, "track_order")

    def test_inventory_route_can_need_product(self):
        result = self.route("Do you have size M in stock?")
        self.assertEqual(result.tool_name, "check_inventory")
        self.assertEqual(result.status, RouteStatus.NEEDS_CONTEXT)
        self.assertEqual(result.missing_fields, ["product_id"])
        self.assertEqual(result.tool_arguments["size"], "M")

    def test_similar_product(self):
        result = self.route("Show me products similar to this one", reference_product_id="zara-us:00029400")
        self.assertEqual((result.route, result.tool_name),
                         (Route.PRODUCT_RECOMMENDATION, "find_similar_products"))

    def test_outfit_matching(self):
        result = self.route("What pants match this shirt?", reference_product_id="zara-us:00029400")
        self.assertEqual(result.tool_name, "recommend_matching_products")

    def test_faceted_browse_uses_catalogue_search(self):
        result = self.route("Show me black dresses")
        self.assertEqual((result.route, result.tool_name), (Route.TOOL_GATEWAY, "search_products"))

    def test_broad_formal_and_office_requests_ask_for_product_type(self):
        for message in ("Show me black formal pieces under one hundred dollars",
                        "I need something for the office"):
            with self.subTest(message=message):
                result = self.route(message)
                self.assertEqual(result.tool_name, "search_products")
                self.assertEqual(result.status, RouteStatus.NEEDS_CONTEXT)
                self.assertEqual(result.missing_fields, ["category"])

    def test_business_meeting_suggestion_keeps_semantic_recommendation(self):
        result = self.route("Suggest something for a business meeting")
        self.assertEqual(result.tool_name, "recommend_matching_products")

    def test_current_product_order_language_starts_existing_order_workflow(self):
        for message in ("Confirm my order", "Continue with my order",
                        "Check out the product"):
            with self.subTest(message=message):
                result = self.route(message,
                                    reference_product_id="zara-us:00029400",
                                    active_variant_id="zara-us:00029400:sku-1",
                                    size="M", color="Yellow", quantity=1)
                self.assertEqual(result.tool_name, "create_order_request")
                self.assertEqual(result.status, RouteStatus.NEEDS_CONTEXT)
                self.assertIn("access_token", result.missing_fields)

    def test_new_spoken_search_replaces_stale_page_query_and_keeps_structured_context(self):
        result = self.route(
            "Show me black formal dresses under one hundred dollars",
            query="shirts", category="dress", occasion="formal", color="black",
            budget_max=100,
        )
        self.assertEqual(result.tool_arguments["query"],
                         "Show me black formal dresses under one hundred dollars")
        self.assertEqual(result.tool_arguments["product_type"], "dress")
        self.assertEqual(result.tool_arguments["occasion"], "formal")
        self.assertEqual(result.tool_arguments["color"], "black")
        self.assertEqual(result.tool_arguments["max_price"], 100)

    def test_active_product_sentiment_uses_product_details(self):
        for message in ("I love this dress", "I really like it", "I prefer that one"):
            with self.subTest(message=message):
                result = self.route(message, reference_product_id="zara-us:00029400")
                self.assertEqual((result.intent, result.tool_name),
                                 ("GET_PRODUCT_DETAILS", "get_product_details"))
                self.assertEqual(result.tool_arguments["product_id"], "zara-us:00029400")

    def test_expanded_current_product_references_use_existing_capability(self):
        for reference in ("it", "that", "the dress", "the shirt", "the product"):
            with self.subTest(reference=reference):
                result = self.route(f"Tell me about {reference}",
                                    reference_product_id="zara-us:00029400")
                self.assertEqual(result.tool_name, "get_product_details")

    def test_authoritative_product_falls_back_to_product_details(self):
        result = self.route("Tell me more", reference_product_id="zara-us:00029400")
        self.assertEqual(result.intent, "GET_PRODUCT_DETAILS")
        self.assertEqual(result.reason_codes[0], "AUTHORITATIVE_CURRENT_PRODUCT_FALLBACK")

    def test_specialized_route_wins_over_active_product_fallback(self):
        result = self.route("What is the return policy?",
                            reference_product_id="zara-us:00029400")
        self.assertEqual(result.route, Route.POLICY_RAG)

    def test_explicit_unrelated_topic_stays_general(self):
        result = self.route("Explain quantum gravity",
                            reference_product_id="zara-us:00029400")
        self.assertEqual((result.route, result.intent),
                         (Route.GENERAL_CHAT, "GENERAL_CONVERSATION"))

    def test_general_chat(self):
        self.assertEqual(self.route("Hello").route, Route.GENERAL_CHAT)

    def test_missing_order_context(self):
        result = self.route("Cancel my order", access_token="verified-token")
        self.assertEqual(result.status, RouteStatus.NEEDS_CONTEXT)
        self.assertEqual(result.missing_fields, ["order_id"])

    def test_ambiguous_order_return_policy_stays_policy(self):
        result = self.route("What is the return policy for my order?")
        self.assertEqual(result.route, Route.POLICY_RAG)

    def test_policy_timing_without_order_stays_general_policy(self):
        result = self.route("After how many days am I eligible for an exchange or refund?")
        self.assertEqual((result.route,result.tool_name),
                         (Route.POLICY_RAG,"retrieve_policy_knowledge"))

    def test_category_recommendation_ignores_unrelated_active_product(self):
        result = self.route("Recommend a black blazer from your current collection",
                            reference_product_id="zara-us:00029400")
        self.assertEqual((result.intent,result.tool_name),("SEARCH_PRODUCTS","search_products"))
        self.assertIn("black blazer",result.tool_arguments["query"].casefold())

    def test_cancel_action_requires_confirmation(self):
        result = self.route("Cancel my order", order_id="ORD-123",
                            access_token="verified-token")
        self.assertEqual(result.tool_name, "cancel_order")
        self.assertTrue(result.requires_confirmation)

    def test_private_order_action_requires_verification(self):
        result = self.route("Cancel order ORD-123")
        self.assertEqual(result.missing_fields, ["access_token"])


if __name__ == "__main__":
    unittest.main()
