import unittest

from backend.app.voice.conversation_policy import ConversationPolicy


class ConversationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = ConversationPolicy()

    def test_detects_customer_goal_and_scenario(self):
        decision = self.policy.evaluate("Show me a black dress for a wedding", {})
        self.assertEqual(decision.goal, "PRODUCT_SEARCH")
        self.assertEqual(decision.scenario, "wedding")
        self.assertEqual(decision.strategy, "recommend_or_execute")
        self.assertGreaterEqual(decision.confidence, .9)

    def test_product_context_avoids_unnecessary_clarification(self):
        decision = self.policy.evaluate("How much is this?", {"product_id": "zara-us:00000001"})
        self.assertEqual(decision.goal, "PRICE_INQUIRY")
        self.assertEqual(decision.strategy, "recommend_or_execute")

    def test_policy_and_faq_are_distinct_customer_goals(self):
        policy = self.policy.evaluate("What is your return policy?", {})
        faq = self.policy.evaluate("What payment methods are accepted?", {})
        self.assertEqual(policy.goal, "POLICY")
        self.assertEqual(faq.goal, "FAQ")

    def test_clarification_selects_only_highest_value_field(self):
        decision = self.policy.evaluate("I need something for a wedding", {"occasion": "wedding"})
        self.assertEqual(decision.strategy, "clarify_once")
        self.assertEqual(decision.clarification_field, "category")

    def test_luxury_and_formal_are_shopping_scenarios(self):
        self.assertEqual(self.policy.evaluate("I want a luxury outfit", {}).scenario, "luxury")
        self.assertEqual(self.policy.evaluate("I need something formal", {}).scenario, "formal")

    def test_high_confidence_asr_recovery_requires_shopping_context(self):
        recovered = self.policy.evaluate("blank waiting list", {"query": "wedding outfits"})
        self.assertEqual(recovered.suggested_transcript, "black wedding dress")
        self.assertEqual(recovered.clarification, "Did you mean a black wedding dress?")
        unrelated = self.policy.evaluate("blank waiting list", {})
        self.assertIsNone(unrelated.suggested_transcript)


if __name__ == "__main__":
    unittest.main()
