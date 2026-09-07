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
        result = self.route("Start a return for order ORD-123")
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

    def test_general_chat(self):
        self.assertEqual(self.route("Hello").route, Route.GENERAL_CHAT)

    def test_missing_order_context(self):
        result = self.route("Cancel my order")
        self.assertEqual(result.status, RouteStatus.NEEDS_CONTEXT)
        self.assertEqual(result.missing_fields, ["order_id"])

    def test_ambiguous_order_return_policy_stays_policy(self):
        result = self.route("What is the return policy for my order?")
        self.assertEqual(result.route, Route.POLICY_RAG)

    def test_cancel_action_requires_confirmation(self):
        result = self.route("Cancel my order")
        self.assertEqual(result.tool_name, "cancel_order")
        self.assertTrue(result.requires_confirmation)


if __name__ == "__main__":
    unittest.main()
