"""Offline customer-journey acceptance tests for the production voice assistant."""

import re
import unittest

from backend.app.voice.executor import VoiceCapabilityExecutor
from backend.app.voice.schemas import CapabilityResult, CreateVoiceSessionRequest, VoiceTurnRequest
from backend.app.voice.service import VoiceService


class GroundedCommerceBackend:
    def __init__(self):
        self.calls = []

    def execute(self, decision):
        self.calls.append(decision)
        tool = decision.tool_name
        args = decision.tool_arguments
        if tool == "search_products":
            if "impossible" in str(args.get("query", "")).casefold():
                return CapabilityResult(execution_status="SUCCESS", data={"products": []})
            department = args.get("department")
            name = "KIDS COTTON OCCASION DRESS" if department == "KIDS" else "TAILORED LINEN DRESS"
            return CapabilityResult(execution_status="SUCCESS", data={"products": [{
                "product_id": "zara-us:00000001", "name": name, "price": 79.9,
                "currency": "USD", "matched_variant": {
                    "variant_id": "black-m", "sku": "BLACK-M", "color": "Black", "size": "M",
                },
            }]})
        if tool == "get_product_details":
            missing_material = args.get("product_id") == "zara-us:00000099"
            data = {
                "name": "TAILORED LINEN DRESS", "price": 79.9, "currency": "USD",
                "colors": [{"color_name": "Black"}, {"color_name": "Navy"}],
                "variants": [{"size_name": "S", "in_stock": True}, {"size_name": "M", "in_stock": True}],
                "available": True,
            }
            if not missing_material:
                data["materials_care"] = "100% linen. Machine wash on a gentle cycle."
            return CapabilityResult(execution_status="SUCCESS", data=data)
        if tool == "check_inventory":
            return CapabilityResult(execution_status="SUCCESS", data={
                "overall_status": "IN_STOCK", "total_network_available": 8,
                "matching_variants": [{"variant_id": "yellow-l", "size_name": "L",
                                       "color_name": "Yellow"}],
            })
        if tool == "identify_customer":
            return CapabilityResult(execution_status="SUCCESS", data={
                "found": True, "customer_type": "REGISTERED",
                "masked_destination": "j***@example.test",
                "verification_method": "POSTAL_CODE",
            })
        if tool == "verify_customer":
            return CapabilityResult(execution_status="SUCCESS", data={
                "verified": True, "access_token": "verified-access-token",
                "auth_level": "TRANSACTION_VERIFIED", "customer_type": "REGISTERED",
            })
        if tool == "track_order":
            return CapabilityResult(execution_status="SUCCESS", data={
                "order_number": args.get("order_number", "ORD-100"),
                "shipment_status": "IN_TRANSIT",
            })
        if tool == "check_return_eligibility":
            return CapabilityResult(execution_status="SUCCESS", data={
                "eligible": True, "reason": "This item is within the recorded return window.",
            })
        if tool == "check_exchange_inventory":
            return CapabilityResult(execution_status="SUCCESS", data={
                "eligible": True, "reason": "The requested replacement is available.",
                "quantity_available": 2, "status": "IN_STOCK",
            })
        if tool == "get_refund_status":
            return CapabilityResult(execution_status="SUCCESS", data={
                "refunds": [{"refund_status": "PROCESSING"}],
            })
        if tool in {"find_similar_products", "recommend_matching_products"}:
            return CapabilityResult(execution_status="SUCCESS", data={"results": [{
                "product_id": "zara-us:00000002", "name": "LINEN EVENING DRESS",
                "price": 89.9, "currency": "USD",
            }]})
        if tool == "retrieve_policy_knowledge":
            return CapabilityResult(execution_status="SUCCESS", data={"evidence": [{
                "chunk_text": "Eligibility and timing are checked against the current order and the latest policy.",
            }]})
        if tool == "prepare_handoff":
            return CapabilityResult(execution_status="SUCCESS", data={"handoff_id": "HANDOFF-1"})
        return CapabilityResult(execution_status="SUCCESS", data={})

    def prepare_write(self, tool_name, arguments):
        self.calls.append(("prepare", tool_name, dict(arguments)))
        return CapabilityResult(
            execution_status="CONFIRMATION_REQUIRED",
            confirmation_token=f"confirm-{tool_name}",
            confirmation_prompt="Would you like me to submit this request?",
            data={"prepared_arguments": dict(arguments)},
        )

    def confirm_write(self, tool_name, arguments, confirmation_token):
        self.calls.append(("confirm", tool_name, dict(arguments), confirmation_token))
        if tool_name == "create_order_request":
            return CapabilityResult(execution_status="SUCCESS", data={
                "order_id": "order-1", "order_number": "NGR-1001",
                "product_name": "TAILORED LINEN DRESS", "variant_id": "black-m",
                "color": "Black", "size": "M", "quantity": 1,
                "shipping_summary": "Saved address", "payment_url": "https://example.test/payment/NGR-1001",
            })
        return CapabilityResult(execution_status="SUCCESS", data={"case_id": "CASE-1001"})


class CapturingCommunicator:
    def __init__(self):
        self.messages = []

    def send(self, **message):
        self.messages.append(message)
        return "accepted"


class VoiceCustomerAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.backend = GroundedCommerceBackend()
        self.service = VoiceService(executor=VoiceCapabilityExecutor(self.backend))
        self.session = self.service.create_session(CreateVoiceSessionRequest()).session_id

    def turn(self, transcript, **context):
        return self.service.process_voice_turn(VoiceTurnRequest(
            session_id=self.session, transcript=transcript, context=context,
        ))

    def verify_session(self):
        state = self.service.get_session(self.session)
        state.access_token = "verified-access-token"
        state.auth_level = "TRANSACTION_VERIFIED"
        state.customer_type = "REGISTERED"
        self.service.sessions.update_session(state)

    def assert_no_duplicate_sentences(self, spoken_text):
        sentences = [re.sub(r"\s+", " ", item).strip().casefold()
                     for item in re.split(r"(?<=[.!?])\s+", spoken_text) if item.strip()]
        self.assertEqual(len(sentences), len(set(sentences)), spoken_text)

    def test_01_wedding_search_preserves_all_constraints(self):
        result = self.turn("Show me black dresses under $100 for a wedding guest")
        args = self.backend.calls[-1].tool_arguments
        self.assertEqual(result.tool_name, "search_products")
        self.assertEqual((args["product_type"], args["color"], args["occasion"], args["max_price"]),
                         ("dress", "black", "wedding", 100.0))
        self.assertIn("TAILORED LINEN DRESS", result.spoken_text)

    def test_02_office_recommendation_routes_to_catalogue_without_interrogation(self):
        result = self.turn("Recommend a modern shirt for my husband to wear at the office")
        args = self.backend.calls[-1].tool_arguments
        self.assertEqual(result.tool_name, "search_products")
        self.assertEqual(args["department"], "MAN")
        self.assertEqual(args["occasion"], "office")
        self.assertFalse(result.needs_user_input)

    def test_03_child_age_overrides_relationship_word_for_department(self):
        result = self.turn("Find a dress for my five year old daughter under $60")
        self.assertEqual(result.tool_name, "search_products")
        self.assertEqual(self.backend.calls[-1].tool_arguments["department"], "KIDS")
        self.assertIn("KIDS COTTON OCCASION DRESS", result.spoken_text)

    def test_04_adult_age_and_recipient_remain_in_semantic_query(self):
        result = self.turn("Recommend a comfortable dress for my 70-year-old mother under $120")
        args = self.backend.calls[-1].tool_arguments
        self.assertEqual(result.tool_name, "search_products")
        self.assertEqual(args["department"], "WOMAN")
        self.assertIn("70-year-old", args["query"])

    def test_05_gift_discovery_asks_once_then_uses_requested_category(self):
        first = self.turn("I need a birthday gift for my wife under $80")
        self.assertEqual(first.missing_fields, ["category"])
        second = self.turn("A handbag")
        self.assertEqual(second.tool_name, "search_products")
        self.assertEqual(self.backend.calls[-1].tool_arguments["product_type"], "bag")
        self.assertEqual(self.backend.calls[-1].tool_arguments["department"], "WOMAN")
        self.assertEqual(self.backend.calls[-1].tool_arguments["max_price"], 80.0)

    def test_06_product_card_context_answers_without_asking_which_product(self):
        result = self.turn("Tell me about this", reference_product_id="zara-us:00000001",
                           active_variant_id="black-m", sku="BLACK-M", color="Black", size="M")
        self.assertEqual(result.tool_name, "get_product_details")
        self.assertNotIn("which product", result.spoken_text.casefold())
        self.assertEqual(self.backend.calls[-1].tool_arguments["product_id"], "zara-us:00000001")

    def test_07_compound_details_are_complete_and_grounded_in_one_turn(self):
        result = self.turn("Is this in medium, and what is the price, material, colors, and sizes?",
                           reference_product_id="zara-us:00000001", active_variant_id="black-m")
        self.assertIn("79.9 USD", result.spoken_text)
        self.assertIn("100% linen", result.spoken_text)
        self.assertIn("Black, Navy", result.spoken_text)
        self.assertIn("S, M", result.spoken_text)
        self.assert_no_duplicate_sentences(result.spoken_text)

    def test_08_unknown_material_does_not_hallucinate_and_offers_handoff(self):
        result = self.turn("What exact fabric blend is this?",
                           reference_product_id="zara-us:00000099")
        self.assertIn("Material information is unavailable", result.spoken_text)
        self.assertIn("human support", result.spoken_text.casefold())
        self.assertNotIn("100%", result.spoken_text)

    def test_09_size_color_and_budget_memory_survive_natural_correction(self):
        self.turn("Show me black dresses under $100")
        self.turn("Actually navy, in medium")
        state = self.service.get_session(self.session)
        self.assertEqual((state.category, state.budget_max, state.colors, state.size),
                         ("dress", 100.0, ["navy"], "M"))

    def test_10_similar_products_keep_current_constraints(self):
        self.turn("Show me black dresses under $100")
        result = self.turn("Show me something similar",
                           reference_product_id="zara-us:00000001")
        args = self.backend.calls[-1].tool_arguments
        self.assertEqual(result.tool_name, "find_similar_products")
        self.assertEqual((args["target_category"], args["color"], args["max_price"]),
                         ("dress", "black", 100.0))

    def test_11_no_result_response_is_honest_and_recoverable(self):
        result = self.turn("Show me impossible dresses under $1")
        self.assertIn("couldn't find matching products", result.spoken_text)
        self.assertIn("broaden", result.spoken_text)
        self.assertNotIn("TAILORED LINEN DRESS", result.spoken_text)

    def test_12_return_exchange_and_refund_policy_questions_use_rag(self):
        for question in ("What is your return policy?", "How does the exchange policy work?",
                         "How long does a refund take?"):
            result = self.turn(question)
            self.assertEqual(result.tool_name, "retrieve_policy_knowledge")
            self.assertEqual(result.route.value, "POLICY_RAG")
            self.assertIn("current order", result.spoken_text)

    def test_13_verified_order_requires_confirmation_then_creates_request_and_email(self):
        self.verify_session()
        prepared = self.turn("I would like to order this in medium", reference_product_id="zara-us:00000001",
                             active_variant_id="black-m", color="Black", size="M", quantity=1)
        self.assertTrue(prepared.requires_confirmation)
        self.assertNotIn("received successfully", prepared.spoken_text)
        communicator = CapturingCommunicator()
        confirmed = self.service.process_voice_turn(VoiceTurnRequest(
            session_id=self.session, transcript="Yes, please submit my order request"),
            communicator=communicator)
        self.assertEqual(confirmed.execution_status, "SUCCESS")
        self.assertIn("order request has been received", confirmed.spoken_text)
        self.assertIn("complete the payment", confirmed.spoken_text.casefold())
        self.assertEqual(len(communicator.messages), 1)

    def test_14_verified_exchange_and_refund_create_review_cases_only(self):
        for request, expected in (
            ("I want to request an exchange because it is too small", "exchange request has been created"),
            ("I want to request a refund because the item arrived damaged", "refund request has been submitted"),
        ):
            backend = GroundedCommerceBackend()
            service = VoiceService(executor=VoiceCapabilityExecutor(backend))
            session = service.create_session(CreateVoiceSessionRequest()).session_id
            state = service.get_session(session)
            state.access_token = "verified-access-token"
            state.auth_level = "TRANSACTION_VERIFIED"
            service.sessions.update_session(state)
            context = {"order_id": "ORD-100", "order_item_id": "ITEM-1",
                       "product_id": "zara-us:00000001", "size": "L", "color": "Black"}
            prepared = service.process_voice_turn(VoiceTurnRequest(
                session_id=session, transcript=request, context=context))
            self.assertTrue(prepared.requires_confirmation)
            communicator = CapturingCommunicator()
            confirmed = service.process_voice_turn(VoiceTurnRequest(
                session_id=session, transcript="Yes"), communicator=communicator)
            self.assertIn(expected, confirmed.spoken_text.casefold())
            self.assertNotIn("refund issued", confirmed.spoken_text.casefold())
            self.assertEqual(len(communicator.messages), 1)

    def test_15_human_handoff_carries_context_without_repeating_the_journey(self):
        self.verify_session()
        self.turn("Show me black dresses under $100 for a wedding")
        result = self.turn("Please connect me to human support")
        self.assertEqual(result.tool_name, "prepare_handoff")
        summary = self.backend.calls[-1].tool_arguments["factual_summary"]
        self.assertIn("Product: zara-us:00000001", summary)
        self.assertIn("Category: dress", summary)
        self.assertIn("Occasion: wedding", summary)
        self.assertIn("Colors: black", summary)
        self.assertIn("won't need to repeat", result.spoken_text)

    def test_16_broad_occasion_asks_one_useful_question_then_recommends(self):
        first = self.turn("I need something for a business meeting under $120")
        self.assertEqual(first.missing_fields, ["category"])
        second = self.turn("A blazer")
        self.assertEqual(second.tool_name, "search_products")
        args = self.backend.calls[-1].tool_arguments
        self.assertEqual((args["product_type"], args["occasion"], args["max_price"]),
                         ("blazer", "business", 120.0))
        self.assertFalse(second.needs_user_input)

    def test_17_eid_request_retains_occasion_after_clarification(self):
        first = self.turn("Find something modest for Eid for my mother")
        self.assertEqual(first.missing_fields, ["category"])
        second = self.turn("A dress")
        args = self.backend.calls[-1].tool_arguments
        self.assertEqual(second.tool_name, "search_products")
        self.assertEqual((args["occasion"], args["department"], args["product_type"]),
                         ("eid", "WOMAN", "dress"))

    def test_18_child_recommendation_keeps_age_and_season_in_grounded_query(self):
        result = self.turn("Show me summer shirts for my 12-year-old son under $50")
        args = self.backend.calls[-1].tool_arguments
        self.assertEqual(result.tool_name, "search_products")
        self.assertEqual((args["department"], args["product_type"], args["max_price"]),
                         ("KIDS", "shirt", 50.0))
        self.assertIn("12-year-old", args["query"])

    def test_19_second_visible_product_becomes_authoritative_context(self):
        visible = [
            {"product_id": "zara-us:00000001", "name": "FIRST DRESS", "variant_id": "first-m"},
            {"product_id": "zara-us:00000002", "name": "SECOND DRESS", "variant_id": "second-m"},
        ]
        result = self.turn("Tell me about the second one", visible_products=visible)
        self.assertEqual(result.tool_name, "get_product_details")
        self.assertEqual(self.backend.calls[-1].tool_arguments["product_id"], "zara-us:00000002")
        state = self.service.get_session(self.session)
        self.assertEqual((state.current_product_id, state.active_variant_id),
                         ("zara-us:00000002", "second-m"))

    def test_20_successive_product_questions_are_focused_not_repeated(self):
        context = {"reference_product_id": "zara-us:00000001", "active_variant_id": "black-m"}
        price = self.turn("How much is it?", **context)
        colors = self.turn("What colors are available?")
        sizes = self.turn("What sizes do you have?")
        self.assertIn("79.9 USD", price.spoken_text)
        self.assertNotIn("available colors", price.spoken_text.casefold())
        self.assertIn("Black, Navy", colors.spoken_text)
        self.assertNotIn("current price", colors.spoken_text.casefold())
        self.assertIn("S, M", sizes.spoken_text)
        self.assertEqual(len({price.spoken_text, colors.spoken_text, sizes.spoken_text}), 3)

    def test_21_price_and_color_correction_continues_existing_search(self):
        self.turn("Show me black dresses under $100")
        result = self.turn("Actually navy and under $90")
        args = self.backend.calls[-1].tool_arguments
        self.assertEqual(result.tool_name, "search_products")
        self.assertEqual((args["product_type"], args["color"], args["max_price"]),
                         ("dress", "navy", 90.0))

    def test_22_start_over_clears_stale_product_and_preferences(self):
        self.turn("Show me black dresses under $100")
        reset = self.turn("Let's start over")
        state = self.service.get_session(self.session)
        self.assertEqual(reset.execution_status, "CONTEXT_RESET")
        self.assertIsNone(state.current_product_id)
        self.assertIsNone(state.category)
        self.assertIsNone(state.budget_max)
        self.assertEqual(state.colors, [])

    def test_23_unverified_order_never_claims_success(self):
        result = self.turn("I want to order this in medium",
                           reference_product_id="zara-us:00000001",
                           active_variant_id="black-m", color="Black", size="M")
        self.assertEqual(result.execution_status, "AWAITING_CONTEXT")
        self.assertEqual(result.missing_fields, ["access_token"])
        self.assertIn("verify", result.spoken_text.casefold())
        self.assertNotIn("received successfully", result.spoken_text.casefold())

    def test_24_spoken_email_verification_then_order_sends_grounded_email(self):
        self.turn("I want to order this in medium", reference_product_id="zara-us:00000001",
                  active_variant_id="black-m", color="Black", size="M")
        heard = self.turn("My email is jess dot carter at example dot test")
        self.assertEqual(heard.execution_status, "AWAITING_EMAIL_CONFIRMATION")
        self.assertIn("jess.carter@example.test", heard.spoken_text)
        challenge = self.turn("Yes, correct")
        self.assertEqual(challenge.execution_status, "AWAITING_VERIFICATION_VALUE")
        prepared = self.turn("10001")
        self.assertTrue(prepared.requires_confirmation)
        communicator = CapturingCommunicator()
        confirmed = self.service.process_voice_turn(VoiceTurnRequest(
            session_id=self.session, transcript="Yes, submit it"), communicator=communicator)
        self.assertEqual(confirmed.execution_status, "SUCCESS")
        self.assertEqual(len(communicator.messages), 1)
        message = communicator.messages[0]
        self.assertIn("NGR-1001", message["subject"])
        self.assertIn("Product: TAILORED LINEN DRESS", message["lines"])
        self.assertEqual(message["action_label"], "Complete Payment")
        self.assertIn("sent the order details", confirmed.spoken_text)

    def test_25_order_email_failure_is_disclosed_without_losing_order(self):
        class FailingCommunicator:
            def send(self, **_message):
                raise RuntimeError("SMTP unavailable")

        self.verify_session()
        prepared = self.turn("Order this in medium", reference_product_id="zara-us:00000001",
                             active_variant_id="black-m", color="Black", size="M")
        self.assertTrue(prepared.requires_confirmation)
        confirmed = self.service.process_voice_turn(VoiceTurnRequest(
            session_id=self.session, transcript="Yes"), communicator=FailingCommunicator())
        self.assertEqual(confirmed.execution_status, "SUCCESS")
        self.assertIn("order request has been received", confirmed.spoken_text.casefold())
        self.assertIn("couldn't send", confirmed.spoken_text.casefold())

    def test_26_repeated_confirmation_cannot_create_duplicate_order(self):
        self.verify_session()
        self.turn("Order this in medium", reference_product_id="zara-us:00000001",
                  active_variant_id="black-m", color="Black", size="M")
        self.service.process_voice_turn(VoiceTurnRequest(
            session_id=self.session, transcript="Yes"), communicator=CapturingCommunicator())
        repeated = self.turn("Yes, confirm it again")
        confirms = [call for call in self.backend.calls
                    if isinstance(call, tuple) and call[0] == "confirm"
                    and call[1] == "create_order_request"]
        self.assertEqual(len(confirms), 1)
        self.assertNotIn("order request has been received", repeated.spoken_text.casefold())

    def test_27_tracking_requires_verification_then_uses_order_number(self):
        unverified = self.turn("Track order ORD-100")
        self.assertEqual(unverified.missing_fields, ["access_token"])
        self.verify_session()
        tracked = self.turn("Track order ORD-100")
        self.assertEqual(tracked.tool_name, "track_order")
        self.assertIn("in transit", tracked.spoken_text.casefold())
        self.assertEqual(self.backend.calls[-1].tool_arguments["order_number"], "ORD-100")

    def test_28_return_policy_and_order_eligibility_stay_separate(self):
        policy = self.turn("What is your return policy?")
        self.assertEqual(policy.tool_name, "retrieve_policy_knowledge")
        self.verify_session()
        eligibility = self.turn("Is order ORD-100 eligible for return?")
        self.assertEqual(eligibility.tool_name, "check_return_eligibility")
        self.assertIn("within the recorded return window", eligibility.spoken_text)

    def test_29_exchange_eligibility_checks_replacement_without_creating_case(self):
        self.verify_session()
        result = self.turn("Can I exchange this for size large?", order_id="ORD-100",
                           order_item_id="ITEM-1", size="L", color="Black")
        self.assertEqual(result.tool_name, "check_exchange_inventory")
        self.assertIn("in stock", result.spoken_text.casefold())
        self.assertFalse(any(isinstance(call, tuple) and call[0] == "prepare"
                             for call in self.backend.calls))

    def test_30_refund_status_is_grounded_and_does_not_claim_refund_issued(self):
        self.verify_session()
        result = self.turn("What is the refund status for order ORD-100?")
        self.assertEqual(result.tool_name, "get_refund_status")
        self.assertIn("processing", result.spoken_text.casefold())
        self.assertNotIn("refund issued", result.spoken_text.casefold())
        self.assert_no_duplicate_sentences(result.spoken_text)

    def test_31_customer_can_relax_only_budget_after_no_results(self):
        class BudgetSensitiveBackend(GroundedCommerceBackend):
            def execute(self, decision):
                if decision.tool_name == "search_products" and decision.tool_arguments.get("max_price"):
                    self.calls.append(decision)
                    return CapabilityResult(execution_status="SUCCESS", data={
                        "products": [],
                        "fallback_message": "I couldn't find office-specific shirts matching the rest of your request.",
                    })
                return super().execute(decision)

        backend = BudgetSensitiveBackend()
        service = VoiceService(executor=VoiceCapabilityExecutor(backend))
        session = service.create_session(CreateVoiceSessionRequest()).session_id
        first = service.process_voice_turn(VoiceTurnRequest(
            session_id=session,
            transcript="I need a men's polo shirt under sixty dollars for the office."))
        self.assertEqual(first.execution_status, "SUCCESS")
        second = service.process_voice_turn(VoiceTurnRequest(
            session_id=session, transcript="Just my budget. I couldn't"))
        args = backend.calls[-1].tool_arguments
        self.assertEqual(second.tool_name, "search_products")
        self.assertNotIn("max_price", args)
        self.assertEqual((args["product_type"], args["occasion"], args["department"]),
                         ("shirt", "office", "MAN"))
        self.assertIn("TAILORED LINEN DRESS", second.spoken_text)

    def test_32_guest_checks_availability_before_order_verification(self):
        result = self.turn("I want to order this product, large size, in yellow. Is that available?",
                           reference_product_id="zara-us:00000001",
                           active_variant_id="black-m", color="Black", size="M")
        self.assertEqual(self.backend.calls[-1].tool_name, "check_inventory")
        self.assertIn("yellow size l", result.spoken_text.casefold())
        self.assertIn("in stock", result.spoken_text.casefold())
        self.assertIn("provide your email", result.spoken_text.casefold())
        state = self.service.get_session(self.session)
        self.assertEqual(state.pending_tool_name, "create_order_request")
        self.assertEqual(state.active_variant_id, "yellow-l")

    def test_33_public_product_details_and_inventory_never_require_email(self):
        details = self.turn("Tell me the price and available colors",
                            reference_product_id="zara-us:00000001")
        stock = self.turn("Do you have this in medium?")
        self.assertEqual(details.tool_name, "get_product_details")
        self.assertEqual(stock.tool_name, "check_inventory")
        self.assertNotIn("verify", details.spoken_text.casefold())
        self.assertNotIn("verify", stock.spoken_text.casefold())


if __name__ == "__main__":
    unittest.main()
