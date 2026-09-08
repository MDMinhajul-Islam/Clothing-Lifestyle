import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from backend.app.voice.executor import VoiceCapabilityExecutor
from backend.app.voice.composer import VoiceResponseComposer
from backend.app.orchestrator.schemas import Route
from backend.app.voice.providers.mock import MockVoiceProviderAdapter
from backend.app.voice.schemas import (
    CapabilityResult, CreateVoiceSessionRequest, VoiceTurnRequest,
)
from backend.app.voice.service import VoiceService
from backend.app.voice.session import VoiceSessionNotFound


class FakeCapabilityBackend:
    def __init__(self):
        self.calls = []

    def execute(self, decision):
        self.calls.append(("execute", decision.tool_name, dict(decision.tool_arguments)))
        if decision.route.value == "POLICY_RAG":
            return CapabilityResult(execution_status="SUCCESS",
                spoken_text="The official Zara US policy evidence was found.",
                data={"status":"EVIDENCE_FOUND", "sources":["official-zara-us"]})
        if decision.tool_name == "check_inventory":
            return CapabilityResult(execution_status="SUCCESS",
                spoken_text="That product has demo inventory available.",
                data={"availability_origin":"synthetic_operational_layer"})
        if decision.tool_name == "track_order":
            return CapabilityResult(execution_status="SUCCESS",
                spoken_text="I found the shipment status.")
        if decision.tool_name in {"find_similar_products", "recommend_matching_products"}:
            return CapabilityResult(execution_status="SUCCESS",
                data={"results":[{"name":"Grounded catalogue option"}]})
        return CapabilityResult(execution_status="SUCCESS", spoken_text="Done.")

    def prepare_write(self, tool_name, arguments):
        self.calls.append(("prepare", tool_name, dict(arguments)))
        return CapabilityResult(execution_status="CONFIRMATION_REQUIRED",
            confirmation_token="gateway-issued-token",
            confirmation_prompt="The gateway requires confirmation. Should I proceed?")

    def confirm_write(self, tool_name, arguments, confirmation_token):
        self.calls.append(("confirm", tool_name, dict(arguments), confirmation_token))
        if confirmation_token != "gateway-issued-token":
            raise AssertionError("voice bypassed the gateway token")
        return CapabilityResult(execution_status="CONFIRMED_BY_GATEWAY",
            spoken_text="The gateway confirmed the action.")


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeCapabilityBackend()
        self.service = VoiceService(executor=VoiceCapabilityExecutor(self.backend))
        self.session = self.service.create_session(CreateVoiceSessionRequest()).session_id
        state = self.service.get_session(self.session)
        state.access_token = "verified-access-token-1234567890"
        state.auth_level = "TRANSACTION_VERIFIED"
        self.service.sessions.update_session(state)

    def turn(self, transcript, **context):
        return self.service.process_voice_turn(VoiceTurnRequest(
            session_id=self.session, transcript=transcript, context=context))

    def test_01_create_session(self):
        session = self.service.get_session(self.session)
        self.assertEqual(session.provider.value, "mock")
        self.assertEqual(session.conversation_turn, 0)

    def test_02_general_greeting(self):
        result = self.turn("Hello")
        self.assertEqual(result.execution_status, "LLM_NOT_CONFIGURED")
        self.assertIn("Hello", result.spoken_text)

    def test_03_policy_execution_path(self):
        result = self.turn("What's Zara's return policy?")
        self.assertEqual(result.route.value, "POLICY_RAG")
        self.assertEqual(result.execution_status, "SUCCESS")

    def test_04_inventory_missing_product_clarifies(self):
        result = self.turn("Do you have size M in stock?")
        self.assertEqual(result.missing_fields, ["product_id"])
        self.assertIn("Which product", result.spoken_text)

    def test_05_inventory_with_context_executes(self):
        result = self.turn("Do you have size M in stock?", product_id="zara-us:00029400")
        self.assertEqual(result.tool_name, "check_inventory")
        self.assertEqual(self.backend.calls[-1][0], "execute")

    def test_06_track_order_missing_context(self):
        result = self.turn("Where is my order?")
        self.assertEqual(result.missing_fields, ["order_id"])
        self.assertIn("order number", result.spoken_text)

    def test_07_explicit_order_is_retained_and_resumes(self):
        self.turn("Where is my order?")
        result = self.turn("ORD-123")
        self.assertEqual(result.tool_name, "track_order")
        self.assertEqual(self.service.get_session(self.session).current_order_id, "ORD-123")

    def test_08_similar_product(self):
        result = self.turn("Show me products similar to this one",
                           reference_product_id="zara-us:00029400")
        self.assertEqual(result.tool_name, "find_similar_products")
        self.assertIn("Grounded catalogue option", result.spoken_text)

    def test_09_outfit_matching(self):
        result = self.turn("What pants match this shirt?",
                           reference_product_id="zara-us:00029400")
        self.assertEqual(result.tool_name, "recommend_matching_products")

    def test_10_cancel_does_not_execute_immediately(self):
        result = self.turn("Cancel my order", order_id="ORD-123")
        self.assertEqual(result.status, "NEEDS_CONFIRMATION")
        self.assertNotIn("execute", [call[0] for call in self.backend.calls])
        self.assertNotIn("confirm", [call[0] for call in self.backend.calls])

    def test_11_cancel_sets_pending_confirmation(self):
        self.turn("Cancel my order", order_id="ORD-123")
        session = self.service.get_session(self.session)
        self.assertTrue(session.pending_confirmation)
        self.assertEqual(session.pending_tool_name, "cancel_order")

    def test_12_confirmation_uses_gateway_token(self):
        self.turn("Cancel my order", order_id="ORD-123")
        result = self.turn("Yes")
        self.assertEqual(result.execution_status, "CONFIRMED_BY_GATEWAY")
        self.assertEqual(self.backend.calls[-1][-1], "gateway-issued-token")
        self.assertFalse(self.service.get_session(self.session).pending_confirmation)

    def test_13_no_clears_pending_write(self):
        self.turn("Cancel my order", order_id="ORD-123")
        result = self.turn("No")
        self.assertEqual(result.execution_status, "CANCELLED_BY_USER")
        self.assertFalse(self.service.get_session(self.session).pending_confirmation)
        self.assertFalse(any(call[0] == "confirm" for call in self.backend.calls))

    def test_14_session_context_persists(self):
        self.turn("Do you have this in stock?", product_id="zara-us:00029400")
        result = self.turn("Show me products similar to this one")
        self.assertEqual(result.tool_name, "find_similar_products")

    def test_15_end_session(self):
        self.assertTrue(self.service.end_session(self.session).ended)
        with self.assertRaises(VoiceSessionNotFound):
            self.service.get_session(self.session)

    def test_16_invalid_session_is_safe(self):
        with self.assertRaisesRegex(VoiceSessionNotFound, "Voice session was not found"):
            self.service.process_voice_turn(VoiceTurnRequest(
                session_id="missing", transcript="Hello"))

    def test_17_unsupported_provider_rejected(self):
        with self.assertRaises(ValidationError):
            CreateVoiceSessionRequest(provider="unsupported")

    def test_18_general_chat_never_calls_backend(self):
        self.turn("Tell me about linen")
        self.assertEqual(self.backend.calls, [])

    def test_mock_provider_contract(self):
        adapter = MockVoiceProviderAdapter()
        request = adapter.normalize_event({"session_id":self.session, "transcript":"Hello"})
        response = self.service.process_voice_turn(request)
        self.assertTrue(adapter.verify_webhook({}, b""))
        self.assertEqual(adapter.build_response(response)["session_id"], self.session)

    def test_voice_turn_accepts_message_as_transcript(self):
        request = VoiceTurnRequest.model_validate({
            "session_id": self.session, "message": "Hello",
        })
        self.assertEqual(request.transcript, "Hello")

    def test_anonymous_cancel_requires_verification(self):
        anonymous = self.service.create_session(CreateVoiceSessionRequest()).session_id
        result = self.service.process_voice_turn(VoiceTurnRequest(
            session_id=anonymous, transcript="Cancel order ORD-123"))
        self.assertEqual(result.missing_fields, ["access_token"])
        self.assertIn("verify", result.spoken_text.lower())

    def test_return_method_can_be_answered_one_question_at_a_time(self):
        first=self.turn("Start a return",order_id="ORD-123",
                        items=[{"order_item_id":"ITEM-1","quantity":1}])
        self.assertEqual(first.missing_fields,["return_method"])
        second=self.turn("store")
        self.assertTrue(second.requires_confirmation)
        self.assertEqual(self.backend.calls[-1][2]["return_method"],"STORE")

    def test_transcript_wins_when_message_is_also_present(self):
        request = VoiceTurnRequest.model_validate({
            "session_id": self.session,
            "transcript": "Hello",
            "message": "Goodbye",
        })
        self.assertEqual(request.transcript, "Hello")

    def test_refund_without_record_is_explicit(self):
        spoken=VoiceResponseComposer().compose(
            SimpleNamespace(route=Route.TOOL_GATEWAY,intent="GET_REFUND_STATUS"),
            {"total_refunds":0,"refunds":[]},"SUCCESS")
        self.assertIn("No refund is currently recorded",spoken)

    def test_refund_uses_newest_backend_record(self):
        spoken=VoiceResponseComposer().compose(
            SimpleNamespace(route=Route.TOOL_GATEWAY,intent="GET_REFUND_STATUS"),
            {"refunds":[{"refund_status":"PROCESSING"}]},"SUCCESS")
        self.assertIn("processing",spoken)
        self.assertNotIn("14 days",spoken)

    def test_non_cancellable_voice_offers_next_step(self):
        spoken=VoiceResponseComposer().compose(
            SimpleNamespace(route=Route.TOOL_GATEWAY,intent="CANCEL_ORDER"),
            {"error":{"message":"The order has shipped."}},"ORDER_NOT_CANCELLABLE")
        self.assertIn("track it",spoken)

    def test_insufficient_policy_offers_human_support(self):
        spoken=VoiceResponseComposer().compose(
            SimpleNamespace(route=Route.POLICY_RAG,intent="RETRIEVE_POLICY_KNOWLEDGE"),
            {"status":"INSUFFICIENT_EVIDENCE"},"INSUFFICIENT_EVIDENCE")
        self.assertIn("reference policy",spoken)
        self.assertIn("human support",spoken)


if __name__ == "__main__":
    unittest.main()
