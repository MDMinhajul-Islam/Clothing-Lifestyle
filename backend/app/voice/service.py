"""Stateful provider-neutral voice turn processing without direct data access."""

import re
import time

from backend.app.config import settings
from backend.app.retell.timing import timed
from backend.app.orchestrator.schemas import OrchestratorContext, Route, RouteDecision, RouteRequest, RouteStatus
from backend.app.orchestrator.service import OrchestratorService
from .executor import VoiceCapabilityExecutor
from .composer import VoiceResponseComposer
from .conversation_policy import ConversationPolicy
from .schemas import (
    CreateVoiceSessionRequest, EndVoiceSessionResponse, VoiceSessionView,
    VoiceTurnRequest, VoiceTurnResponse,
)
from .session import InMemoryVoiceSessionStore

YES = {"yes", "confirm", "correct", "that's correct", "thats correct", "proceed",
       "go ahead", "yes please", "do it", "continue", "submit it", "send it"}
NO = {"no", "cancel", "never mind", "nevermind", "stop", "don't", "do not"}
ORDER_ID = re.compile(r"\b(?:ORD|ZUS)-[A-Z0-9-]+\b", re.IGNORECASE)
PRODUCT_ID = re.compile(r"\bzara-us:\d{8}\b", re.IGNORECASE)
BUDGET_MAX = re.compile(r"(?:under|below|less than|up to)\s*\$?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
BUDGET_WORD = re.compile(r"(?:under|below|less than|up to)\s+(one\s+hundred|a\s+hundred|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)", re.IGNORECASE)
BUDGET_VALUES = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
                 "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
                 "one hundred": 100, "a hundred": 100}
SIZE_ONLY = re.compile(r"^(?:size\s+)?(xxs|xs|s|m|l|xl|xxl|small|medium|large)$", re.IGNORECASE)
SIZE_IN_SENTENCE = re.compile(r"\b(?:in|size)\s+(xxs|xs|s|m|l|xl|xxl|small|medium|large)\b", re.IGNORECASE)
SIZE_BEFORE_WORD = re.compile(r"\b(xxs|xs|s|m|l|xl|xxl|small|medium|large)\s+size\b", re.IGNORECASE)
COLORS = {"black", "white", "navy", "blue", "red", "green", "beige", "brown", "gray", "grey", "pink", "yellow", "orange", "purple"}
CATEGORIES = {"dress", "shirt", "pants", "jeans", "jacket", "blazer", "top", "skirt", "shoes", "coat",
              "bag", "hoodie", "sweater", "accessory", "perfume"}
CATEGORY_ALIASES = {"dresses":"dress", "shirts":"shirt", "jackets":"jacket", "tops":"top",
                    "blazers":"blazer", "skirts":"skirt", "coats":"coat", "trousers":"pants", "sneakers":"shoes",
                    "bags":"bag", "handbag":"bag", "handbags":"bag", "purse":"bag", "purses":"bag",
                    "backpack":"bag", "backpacks":"bag", "hoodies":"hoodie", "sweaters":"sweater",
                    "accessories":"accessory"}
OCCASIONS = {"wedding", "bridal", "office", "work", "business", "interview", "formal",
             "evening", "cocktail", "party", "casual", "vacation", "beach", "date",
             "festival", "eid", "graduation", "everyday", "winter", "summer", "gym"}
STYLES = {"elegant", "casual", "formal", "minimal", "classic", "modern", "modest",
          "relaxed", "tailored", "oversized", "smart casual", "luxury minimalist"}
CLARIFICATIONS = {
    "product_id": "Which product are you asking about?",
    "category": "What kind of item would you like?",
    "occasion": "What kind of occasion are you shopping for?",
    "style": "Would you prefer something more polished, relaxed, or modern?",
    "order_id": "Could you give me your order number?",
    "items": "Which item or items from the order would you like to return?",
    "return_method": "Would you prefer a free store return or a drop-off return with the $4.95 fee?",
    "reference_product_id": "Which product would you like recommendations for?",
    "order_item_id": "Which order item would you like to exchange?",
    "customer_id": "Could you provide your customer ID?",
    "access_token": "Please verify your identity before I access that information.",
    "store_id": "Which store should I check?",
    "promotion_code": "What promotion code should I check?",
    "cart_subtotal": "What is the current cart subtotal?",
    "issue_type": "What type of issue occurred with the item?",
    "factual_summary": "Could you briefly describe what happened?",
    "email_or_phone_or_order_id": "Please provide your email, phone number, or order number.",
    "verification_value": "What verification value should I use?",
    "destination": "Which verified email address or phone number should receive the link?",
    "purpose": "What should the secure link be used for?",
    "consent_confirmed": "Do I have your consent to use that verified destination?",
    "quantity": "How many would you like?",
    "active_variant_id": "Which size and color would you like?",
    "size": "Which size would you like?",
    "color": "Which color would you like?",
}
RESUME_MESSAGES = {
    "search_products": "Show me products",
    "track_order": "Track my order",
    "check_inventory": "Check inventory",
    "get_product_details": "Show product details",
    "check_cancellation_eligibility": "Can I cancel my order?",
    "cancel_order": "Cancel my order",
    "check_return_eligibility": "Can I return my order?",
    "create_return": "Start a return",
    "get_refund_status": "What is my refund status?",
    "check_exchange_availability": "Check exchange availability",
    "find_similar_products": "Show similar products",
    "recommend_matching_products": "What matches this product?",
    "get_size_guidance": "Give me size guidance",
    "check_pickup_availability": "Check store pickup",
    "get_customer_orders": "Show my order history",
    "get_loyalty_status": "Show my loyalty points",
    "check_promotion": "Check my promotion code",
    "check_exchange_inventory": "Check exchange inventory",
    "create_exchange": "Start an exchange",
    "create_incident": "Create an item incident",
    "create_support_case": "Create a support case",
    "send_secure_link": "Send me a secure link",
    "create_order_request": "Submit this order request",
}


class VoiceService:
    def __init__(self, *, sessions=None, orchestrator=None, executor=None):
        self.sessions = sessions or InMemoryVoiceSessionStore()
        self.orchestrator = orchestrator or OrchestratorService()
        self.executor = executor or VoiceCapabilityExecutor()
        self.composer = VoiceResponseComposer()
        self.conversation_policy = ConversationPolicy()

    def create_session(self, request: CreateVoiceSessionRequest):
        session = self.sessions.create_session(request.provider, request.customer_id)
        return VoiceSessionView(**session.model_dump())

    def get_session(self, session_id):
        return self.sessions.get_session(session_id)

    def end_session(self, session_id):
        self.sessions.end_session(session_id)
        return EndVoiceSessionResponse(session_id=session_id, ended=True)

    def process_voice_turn(self, request: VoiceTurnRequest, *, executor=None, communicator=None):
        executor = executor or self.executor
        session_started = time.perf_counter()
        try:
            session = self.sessions.get_session(request.session_id)
        finally:
            timed("session_restoration", session_started)
        session.conversation_turn += 1
        recovered = self._recover_fashion_asr(request.transcript, session)
        if recovered != request.transcript:
            request = request.model_copy(update={"transcript": recovered})
        text = " ".join(request.transcript.casefold().split())

        if text in {"start over", "let's start over", "lets start over"}:
            self._clear_shopping_context(session)
            self.sessions.update_session(session)
            return self._response(session, "READY", "CONTEXT_RESET",
                "Of course. What would you like to shop for?", tool_name=None)

        if any(signal in text for signal in (
            "ignore your rules", "bypass privacy", "another customer's", "another customer’s",
        )):
            decision = self.orchestrator.route(RouteRequest(message=request.transcript))
            self.sessions.update_session(session)
            return self._response(session, "READY", "SECURITY_REFUSED",
                self.composer.general(text, decision.intent), decision=decision)

        if session.pending_confirmation:
            confirmation = self._confirmation_answer(text)
            if confirmation is False:
                tool = session.pending_tool_name
                self._clear_pending(session)
                self.sessions.update_session(session)
                return self._response(session, "READY", "CANCELLED_BY_USER",
                    "Okay, I won't proceed with that action.", tool_name=tool)
            if confirmation is True:
                return self._confirm_pending(session, executor, communicator)
            self.sessions.update_session(session)
            return self._response(session, "NEEDS_CONFIRMATION", "AWAITING_EXPLICIT_CONFIRMATION",
                "Please say yes to proceed or no to cancel.", needs_user_input=True,
                requires_confirmation=True, tool_name=session.pending_tool_name)

        if session.pending_asr_correction:
            if self._confirmation_answer(text) is True:
                request = request.model_copy(update={"transcript": session.pending_asr_correction})
                text = " ".join(request.transcript.casefold().split())
                session.pending_asr_correction = None
            elif self._confirmation_answer(text) is False:
                session.pending_asr_correction = None
                self.sessions.update_session(session)
                return self._response(session, "READY", "ASR_CORRECTION_DECLINED",
                    "No problem. Please tell me what you would like to find.")
            else:
                session.pending_asr_correction = None

        spoken_email = self._spoken_email(request.transcript)
        if session.pending_spoken_email:
            corrected_email = self._correct_pending_email(
                session.pending_spoken_email, request.transcript)
            if corrected_email:
                session.pending_spoken_email = corrected_email
                session.pending_spoken_email_transcript = request.transcript
                self.sessions.update_session(session)
                return self._response(session, "NEEDS_CONTEXT", "AWAITING_EMAIL_CONFIRMATION",
                    f"I've corrected that to {corrected_email}. Is that right?",
                    needs_user_input=True)
            if self._confirmation_answer(text) is True:
                session.confirmed_spoken_email = session.pending_spoken_email
                resumed = session.pending_spoken_email_transcript or request.transcript
                session.pending_spoken_email = None
                session.pending_spoken_email_transcript = None
                if (session.pending_tool_name and
                        "access_token" in session.pending_missing_fields):
                    return self._begin_customer_verification(session, executor)
                request = request.model_copy(update={"transcript": resumed})
                text = " ".join(request.transcript.casefold().split())
            elif self._confirmation_answer(text) is False:
                session.pending_spoken_email = None
                session.pending_spoken_email_transcript = None
                self.sessions.update_session(session)
                return self._response(session, "NEEDS_CONTEXT", "EMAIL_CONFIRMATION_DECLINED",
                    "No problem. Please say the email address again.", needs_user_input=True)
            elif spoken_email:
                session.pending_spoken_email = spoken_email
                session.pending_spoken_email_transcript = request.transcript
                self.sessions.update_session(session)
                return self._response(session, "NEEDS_CONTEXT", "AWAITING_EMAIL_CONFIRMATION",
                    f"I heard {spoken_email}. Is that correct?", needs_user_input=True)
            else:
                self.sessions.update_session(session)
                return self._response(session, "NEEDS_CONTEXT", "AWAITING_EMAIL_CONFIRMATION",
                    f"I heard {session.pending_spoken_email}. Is that correct?", needs_user_input=True)
        elif spoken_email and spoken_email != session.confirmed_spoken_email:
            session.pending_spoken_email = spoken_email
            session.pending_spoken_email_transcript = request.transcript
            self.sessions.update_session(session)
            return self._response(session, "NEEDS_CONTEXT", "AWAITING_EMAIL_CONFIRMATION",
                f"I heard {spoken_email}. Is that correct?", needs_user_input=True)

        if session.awaiting_verification_value:
            verified = self._verify_customer_for_pending_action(
                request.transcript, session, executor)
            if verified:
                return verified

        if (session.pending_tool_name == "search_products" and session.pending_missing_fields
                and self._interrupts_pending_clarification(text)):
            self._clear_pending(session)

        context = self._merged_context(session, request)
        self._apply_explicit_search_relaxation(text, context, session)
        self._resolve_product_reference(text, context, session)
        policy = self.conversation_policy.evaluate(request.transcript, context)
        session.conversational_goal = policy.goal
        session.shopping_scenario = policy.scenario
        session.intent_confidence = policy.confidence
        if policy.clarification and policy.suggested_transcript:
            session.pending_asr_correction = policy.suggested_transcript
            self.sessions.update_session(session)
            return self._response(session, "NEEDS_CONTEXT", "ASR_CLARIFICATION_REQUIRED",
                                  policy.clarification, needs_user_input=True)
        email_response = self._handle_email_request(
            request.transcript, text, context, session, executor, communicator)
        if email_response:
            return email_response
        purchase_availability = self._answer_purchase_availability_before_auth(
            request.transcript, text, context, session, executor)
        if purchase_availability:
            return purchase_availability
        compound = self._answer_compound_product_question(
            request.transcript, text, context, session, executor)
        if compound:
            return compound
        clarification = (None if self._is_search_continuation(text)
                         else self._shopping_clarification(text, context, session))
        if clarification:
            field, prompt = clarification
            decision = RouteDecision(status=RouteStatus.NEEDS_CONTEXT, route=Route.TOOL_GATEWAY,
                intent="SEARCH_PRODUCTS", confidence=.94, tool_name="search_products",
                missing_fields=[field], reason_codes=["HIGH_VALUE_STYLING_CLARIFICATION"],
                tool_arguments={"query": context.get("query", request.transcript)})
            self._remember_decision(session, decision, context)
            session.pending_tool_name = "search_products"
            session.pending_arguments = dict(decision.tool_arguments)
            session.pending_missing_fields = [field]
            self.sessions.update_session(session)
            return self._response(session, "NEEDS_CONTEXT", "AWAITING_CONTEXT", prompt,
                decision=decision, needs_user_input=True)
        message = request.transcript
        if session.pending_tool_name and session.pending_missing_fields:
            if session.pending_tool_name == "search_products" and context.get("query"):
                context["query"] = f"{context['query']} {request.transcript}".strip()
            message = RESUME_MESSAGES.get(session.pending_tool_name, request.transcript)
        elif session.last_intent == "SEARCH_PRODUCTS" and self._is_search_continuation(text):
            message = "Show me products"
        elif (session.last_intent == "SEARCH_PRODUCTS" or session.category) and self._is_preference_update(text):
            message = "Show me products"

        if any(signal in text for signal in
               ("speak to a person", "talk to a person", "human support", "human agent", "speak to an agent")):
            context["factual_summary"] = self._handoff_summary(session, request.transcript)
        decision = self.orchestrator.route(RouteRequest(message=message,
            context=OrchestratorContext(**context)))
        if decision.tool_name == "search_products" and decision.tool_arguments.get("query"):
            context["query"] = decision.tool_arguments["query"]
        self._remember_decision(session, decision, context)

        if decision.status.value == "NEEDS_CONTEXT":
            session.pending_tool_name = decision.tool_name
            session.pending_arguments = dict(decision.tool_arguments)
            session.pending_missing_fields = list(decision.missing_fields)
            self.sessions.update_session(session)
            prompt = CLARIFICATIONS.get(decision.missing_fields[0],
                                        "What information should I use for that request?")
            return self._response(session, "NEEDS_CONTEXT", "AWAITING_CONTEXT", prompt,
                decision=decision, needs_user_input=True)

        session.pending_missing_fields = []
        if decision.requires_confirmation:
            prepared = executor.prepare_write(decision)
            if not prepared.confirmation_token:
                session.pending_tool_name = None
                session.pending_arguments = {}
                self.sessions.update_session(session)
                spoken = prepared.spoken_text or self.composer.compose(decision, prepared.data,
                                                                        prepared.execution_status)
                return self._response(session, "READY", prepared.execution_status, spoken,
                                      decision=decision,
                                      metadata={"capability_data": self._safe_metadata(prepared.data)})
            session.pending_tool_name = decision.tool_name
            session.pending_arguments = dict(prepared.data.get("prepared_arguments",
                                                               decision.tool_arguments))
            session.pending_confirmation = True
            session.pending_confirmation_token = prepared.confirmation_token
            self.sessions.update_session(session)
            prompt = prepared.confirmation_prompt or self._confirmation_prompt(decision)
            if decision.tool_name == "create_order_request":
                prompt = ("That selection is available. I have the order request ready, but nothing has been submitted yet. "
                          "Would you like me to submit it?")
            return self._response(session, "NEEDS_CONFIRMATION", prepared.execution_status,
                prompt, decision=decision, needs_user_input=True, requires_confirmation=True,
                metadata={"gateway_preflight_status": prepared.execution_status})

        session.pending_tool_name = None
        session.pending_arguments = {}
        if decision.route == Route.GENERAL_CHAT:
            self.sessions.update_session(session)
            execution = "SECURITY_REFUSED" if decision.intent == "SECURITY_REFUSAL" else "LLM_NOT_CONFIGURED"
            spoken = self.composer.general(text, decision.intent)
            return self._response(session, "READY", execution, spoken,
                                  decision=decision)

        result = executor.execute(decision)
        result = self._relax_unavailable_color(decision, result, executor)
        self._apply_capability_context(session, decision, result.data)
        self.sessions.update_session(session)
        spoken = result.spoken_text or self.composer.compose(decision, result.data,
                                                              result.execution_status)
        if not result.spoken_text and decision.intent == "GET_PRODUCT_DETAILS":
            spoken = self._focused_product_detail_response(text, result.data, spoken)
        return self._response(session, "READY", result.execution_status, spoken,
                              decision=decision, metadata={"capability_data": self._safe_metadata(result.data)})

    def _handle_email_request(self, transcript, text, context, session, executor, communicator):
        email_requested = (bool(re.match(r"^(?:please\s+)?email\b", text)) or
                           ("send" in text and "email" in text) or
                           ("send me" in text and "return instructions" in text))
        if not email_requested:
            return None
        if not context.get("access_token"):
            self.sessions.update_session(session)
            return self._response(session, "NEEDS_CONTEXT", "AUTHORIZATION_REQUIRED",
                "I'll need to verify your identity before I send anything to your email.",
                needs_user_input=True)
        if communicator is None:
            self.sessions.update_session(session)
            return self._response(session, "READY", "COMMUNICATION_UNAVAILABLE",
                "Email is temporarily unavailable. I can still help you here.")
        subject = "Your NexGen shopping summary"
        lines = []
        try:
            if "tracking" in text:
                decision = self.orchestrator.route(RouteRequest(
                    message="Track my order", context=OrchestratorContext(**context)))
                if decision.status != RouteStatus.READY:
                    return self._response(session, "NEEDS_CONTEXT", "AWAITING_CONTEXT",
                        "Could you give me your order number?", needs_user_input=True)
                result = executor.execute(decision)
                if result.execution_status != "SUCCESS":
                    return self._response(session, "READY", result.execution_status,
                        result.spoken_text or "I couldn't verify the tracking details to email them.")
                subject = "Your NexGen tracking summary"
                lines = [f"Order: {result.data.get('order_number', context.get('order_id'))}",
                         f"Status: {result.data.get('shipment_status') or result.data.get('order_status', 'Unavailable')}"]
            elif "return" in text:
                subject = "Your NexGen return guidance"
                lines = ["For the latest return eligibility and instructions, use your verified order details with NexGen support.",
                         "Eligibility and refund timing must be confirmed against the current order record."]
            elif session.previous_recommendations:
                subject = "Your NexGen recommendations"
                lines = ["Pieces selected during your conversation:"] + [
                    f"{item.get('name', 'Product')} ({item.get('product_id', 'reference unavailable')})"
                    for item in session.previous_recommendations[:5]]
            elif context.get("product_id"):
                subject = "A NexGen product you selected"
                decision = self.orchestrator.route(RouteRequest(
                    message="Show product details", context=OrchestratorContext(**context)))
                result = executor.execute(decision)
                details = result.data if result.execution_status == "SUCCESS" else {}
                lines = [str(details.get("name") or "Your selected product"),
                         f"Product reference: {context['product_id']}"]
                if details.get("price") is not None:
                    lines.append(f"Price: {details['price']} {details.get('currency', 'USD')}")
                if context.get("sku"): lines.append(f"SKU: {context['sku']}")
            else:
                lines = [self._handoff_summary(session, transcript)]
            communicator.send(access_token=context["access_token"], subject=subject, lines=lines)
        except PermissionError:
            return self._response(session, "NEEDS_CONTEXT", "AUTHORIZATION_REQUIRED",
                "I'll need to verify your identity again before I send that email.", needs_user_input=True)
        except Exception:
            return self._response(session, "READY", "COMMUNICATION_UNAVAILABLE",
                "I couldn't send the email just now. I can still help you here.")
        self.sessions.update_session(session)
        return self._response(session, "READY", "EMAIL_SENT",
            "I've sent that to your verified email address.")

    def _begin_customer_verification(self, session, executor):
        context = self._merged_context(session, VoiceTurnRequest(
            session_id=session.session_id, transcript="Find my account"))
        decision = self.orchestrator.route(RouteRequest(
            message="Find my account", context=OrchestratorContext(**context)))
        result = executor.execute(decision)
        if result.execution_status != "SUCCESS" or not result.data.get("found"):
            self.sessions.update_session(session)
            return self._response(session, "NEEDS_CONTEXT", "CUSTOMER_NOT_FOUND",
                "I couldn't find a customer account for that email. Please check the address or use human support.",
                needs_user_input=True, decision=decision)
        session.awaiting_verification_value = True
        self.sessions.update_session(session)
        method = str(result.data.get("verification_method") or "POSTAL_CODE")
        prompt = ("What is the postal code on your saved address?"
                  if method == "POSTAL_CODE" else
                  "What verification value should I use for your account?")
        return self._response(session, "NEEDS_CONTEXT", "AWAITING_VERIFICATION_VALUE",
            prompt, needs_user_input=True, decision=decision)

    def _verify_customer_for_pending_action(self, transcript, session, executor):
        value = " ".join(transcript.strip().split())
        context = self._merged_context(session, VoiceTurnRequest(
            session_id=session.session_id, transcript=value))
        context["verification_value"] = value
        decision = self.orchestrator.route(RouteRequest(
            message="Verify my account", context=OrchestratorContext(**context)))
        result = executor.execute(decision)
        if result.execution_status != "SUCCESS" or not result.data.get("verified"):
            self.sessions.update_session(session)
            return self._response(session, "NEEDS_CONTEXT", "VERIFICATION_FAILED",
                "I couldn't verify that postal code. Please try again or use human support.",
                needs_user_input=True, decision=decision)
        session.awaiting_verification_value = False
        self._apply_capability_context(session, decision, result.data)
        self.sessions.update_session(session)
        return None

    @staticmethod
    def _relax_unavailable_color(decision, result, executor):
        if (decision.intent != "SEARCH_PRODUCTS" or result.execution_status != "SUCCESS" or
                (result.data.get("products") or []) or not decision.tool_arguments.get("color")):
            return result
        color = str(decision.tool_arguments["color"])
        arguments = dict(decision.tool_arguments)
        arguments.pop("color", None)
        query = str(arguments.get("query") or "")
        arguments["query"] = re.sub(rf"(?<!\w){re.escape(color)}(?!\w)", "", query,
                                    flags=re.IGNORECASE).strip()
        if not arguments["query"]:
            return result
        relaxed_decision = decision.model_copy(update={"tool_arguments": arguments})
        relaxed = executor.execute(relaxed_decision)
        if relaxed.execution_status == "SUCCESS" and relaxed.data.get("products"):
            relaxed.data["fallback_message"] = (
                f"I couldn't find that item in {color}. I kept the rest of your request and found available colors instead.")
            return relaxed
        return result

    @staticmethod
    def _handoff_summary(session, current_request):
        facts = [f"Customer goal: {session.conversational_goal or 'human assistance'}",
                 f"Current request: {current_request}"]
        if session.current_product_id: facts.append(f"Product: {session.current_product_id}")
        if session.current_order_id: facts.append(f"Order: {session.current_order_id}")
        if session.category: facts.append(f"Category: {session.category}")
        if session.occasion: facts.append(f"Occasion: {session.occasion}")
        if session.budget_max is not None: facts.append(f"Budget maximum: {session.budget_max}")
        if session.colors: facts.append("Colors: " + ", ".join(session.colors))
        if session.unresolved_issue: facts.append(f"Required follow-up: {session.unresolved_issue}")
        return "; ".join(facts)

    def _confirm_pending(self, session, executor, communicator=None):
        tool = session.pending_tool_name
        prepared_arguments = dict(session.pending_arguments)
        result = executor.confirm_write(tool, session.pending_arguments,
                                        session.pending_confirmation_token)
        email_sent = None
        if result.execution_status in {"SUCCESS", "CONFIRMED_BY_GATEWAY"}:
            self._clear_pending(session)
            if communicator and session.access_token and tool in {"create_order_request", "create_support_case"}:
                try:
                    if tool == "create_order_request":
                        data=result.data; communicator.send(access_token=session.access_token,
                            subject=f"NexGen order request {data.get('order_number','')}",
                            lines=[f"Order: {data.get('order_number')}",f"Product: {data.get('product_name')}",
                                   f"Variant: {data.get('variant_id')}",f"Color: {data.get('color')}",
                                   f"Size: {data.get('size')}",f"Quantity: {data.get('quantity')}",
                                   f"Shipping: {data.get('shipping_summary')}","Status: PENDING_PAYMENT"],
                            action_label="Complete Payment",action_url=data.get("payment_url"),
                            order_id=data.get("order_id"),event_type="ORDER_REQUEST_RECEIVED"); email_sent=True
                    else:
                        category=prepared_arguments.get("issue_category","SUPPORT_REQUEST")
                        label=category.replace('_',' ').title()
                        communicator.send(access_token=session.access_token,subject=f"NexGen {label.lower()} received",
                            lines=[f"Case: {result.data.get('case_id')}",
                                   f"Order: {prepared_arguments.get('order_number')}","Status: OPEN",
                                   f"Request: {label}",f"Summary: {prepared_arguments.get('factual_summary')}",
                                   "Our support team will review your request and contact you."]); email_sent=True
                except Exception: email_sent=False
        self.sessions.update_session(session)
        if tool == "create_order_request" and result.execution_status in {"SUCCESS", "CONFIRMED_BY_GATEWAY"}:
            spoken = ("Your order request has been received successfully. I've sent the order details to your email. "
                      "Please complete the payment using the link in the email to confirm your purchase." if email_sent
                      else "Your order request has been received successfully, but I couldn't send the payment email. Our support team can help you complete it.")
        elif tool == "create_support_case" and result.execution_status in {"SUCCESS", "CONFIRMED_BY_GATEWAY"}:
            category=prepared_arguments.get("issue_category")
            success_text=("Your exchange request has been created successfully. Our support team will review it and contact you shortly."
                          if category=="EXCHANGE_REQUEST" else
                          "Your refund request has been submitted successfully. Our support team will review your request and contact you."
                          if category=="REFUND_REQUEST" else
                          "Your request has been submitted successfully. Our support team will review it and contact you.")
            spoken = (success_text
                      if email_sent is not False else "Your request was created, but the confirmation email could not be sent. Our support team will still review it.")
        else: spoken = result.spoken_text or ("The action was completed." if not session.pending_confirmation
            else "I couldn't safely complete that action. Please try again later.")
        return self._response(session, "READY", result.execution_status, spoken,
            needs_user_input=session.pending_confirmation,
            requires_confirmation=session.pending_confirmation, tool_name=tool,
            metadata={"capability_data": self._safe_metadata(result.data)})

    @staticmethod
    def _apply_capability_context(session, decision, data):
        if decision.intent == "VERIFY_CUSTOMER" and data.get("verified"):
            session.access_token=data.get("access_token")
            session.auth_level=str(data.get("auth_level","PUBLIC"))
            session.customer_type=data.get("customer_type") or session.customer_type
        if decision.intent in {"SEARCH_PRODUCTS", "FIND_SIMILAR_PRODUCTS", "RECOMMEND_MATCHING_PRODUCTS"}:
            products = data.get("results") or data.get("products") or []
            recommendations = []
            for item in products[:5]:
                matched = item.get("matched_variant") or {}
                recommendation = {
                    key: item[key]
                    for key in ("product_id", "name") if item.get(key)
                }
                for key in ("variant_id", "sku", "color", "size"):
                    value = item.get(key) or matched.get(key)
                    if value:
                        recommendation[key] = value
                recommendations.append(recommendation)
            session.previous_recommendations = recommendations
            if session.previous_recommendations:
                session.current_product_id = session.previous_recommendations[0].get("product_id")

    @classmethod
    def _safe_metadata(cls, value):
        sensitive={"access_token","confirmation_token","verification_value","email","phone","destination"}
        if isinstance(value,dict):
            return {key:("[REDACTED]" if key in sensitive else cls._safe_metadata(item))
                    for key,item in value.items() if key != "prepared_arguments"}
        if isinstance(value,list):return [cls._safe_metadata(item) for item in value]
        return value

    @classmethod
    def _merged_context(cls, session, request):
        context = {
            "customer_id": session.customer_id,
            "customer_type": session.customer_type,
            "auth_level": session.auth_level,
            "access_token": session.access_token,
            "order_id": session.current_order_id,
            "product_id": session.current_product_id,
            "reference_product_id": session.reference_product_id,
            "store_id": session.current_store_id,
            "order_item_id": session.active_order_item_id,
            "active_variant_id": session.active_variant_id,
            "category": session.category,
            "occasion": session.occasion,
            "budget_min": session.budget_min,
            "budget_max": session.budget_max,
            "size": session.size,
            "fit": session.fit,
            "style": session.style,
            "gender": session.gender,
            "colors": list(session.colors),
            "materials": list(session.materials),
            "must_have": list(session.must_have),
            "avoid": list(session.avoid),
            "preferred_store": session.preferred_store,
            "location": session.location,
            "delivery_deadline": session.delivery_deadline,
            "secondary_intents": list(session.secondary_intents),
            "unresolved_issue": session.unresolved_issue,
            "query": session.current_search_query,
            "product_reference": session.current_product_reference,
            "sku": session.current_sku,
            "page_url": session.current_page_url,
            "visible_products": list(session.previous_recommendations),
            "quantity": session.quantity,
        }
        context.update(session.pending_arguments)
        context.update(request.context.model_dump(exclude_none=True))
        variant_size = context.get("size")
        variant_color = context.get("color") or ((context.get("colors") or [None])[-1])
        if (session.previous_recommendations and
                session.last_intent in {"SEARCH_PRODUCTS", "FIND_SIMILAR_PRODUCTS", "RECOMMEND_MATCHING_PRODUCTS"}):
            context["visible_products"] = list(session.previous_recommendations)
        if session.confirmed_spoken_email:
            context["email"] = session.confirmed_spoken_email
        # Webpage product context is authoritative even when the integration supplies
        # only its recommendation/reference identifier.
        if context.get("reference_product_id"):
            context["product_id"] = context["reference_product_id"]
        order = ORDER_ID.search(request.transcript)
        product = PRODUCT_ID.search(request.transcript)
        if order: context["order_id"] = order.group(0).upper()
        if product: context["product_id"] = product.group(0).lower()
        budget=BUDGET_MAX.search(request.transcript)
        if budget: context["budget_max"]=float(budget.group(1))
        budget_word=BUDGET_WORD.search(request.transcript)
        if budget_word: context["budget_max"]=float(BUDGET_VALUES[budget_word.group(1).casefold()])
        size=SIZE_ONLY.match(" ".join(request.transcript.casefold().split()).rstrip("?!."))
        if not size: size=SIZE_IN_SENTENCE.search(request.transcript)
        if not size: size=SIZE_BEFORE_WORD.search(request.transcript)
        if size:
            selected_size={"small":"S","medium":"M","large":"L"}.get(size.group(1).lower(),size.group(1).upper())
            if (context.get("active_variant_id") and variant_size and
                    str(variant_size).casefold() != selected_size.casefold()):
                context.pop("active_variant_id", None)
            context["size"]=selected_size
        words=set(re.findall(r"[a-z]+",request.transcript.casefold()))
        found_colors=[color for color in COLORS if color in words]
        if found_colors:
            folded = request.transcript.casefold()
            if (context.get("active_variant_id") and variant_color and
                    str(variant_color).casefold() != found_colors[-1].casefold()):
                context.pop("active_variant_id", None)
            correcting = (any(signal in folded for signal in ("meant", "instead", "not "))
                          or ("actually" in folded and not any(signal in folded for signal in (" too", "also"))))
            prior = [] if correcting else (context.get("colors") or [])
            context["colors"]=list(dict.fromkeys([*prior,*found_colors]))
            context["color"]=found_colors[-1]
        found_category=next((item for item in CATEGORIES if item in words),None)
        if not found_category:
            found_category=next((value for key,value in CATEGORY_ALIASES.items() if key in words),None)
        if found_category: context["category"]=found_category
        workplace = bool(words & {"office", "corporate", "work", "workwear"})
        found_occasion = "office" if workplace else next(
            (item for item in sorted(OCCASIONS) if item in words), None)
        if "official meeting" in request.transcript.casefold() or "business meeting" in request.transcript.casefold():
            found_occasion="business"
        if found_occasion: context["occasion"]="office" if found_occasion == "work" else found_occasion
        found_style=next((item for item in STYLES if item in request.transcript.casefold()),None)
        if found_style: context["style"]=found_style
        folded = request.transcript.casefold()
        numeric_age = re.search(r"\b(\d{1,2})[- ]?years?[- ]?old\b", folded)
        word_age = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen)\s+years?\s+old\b", folded)
        child_age = bool(word_age or (numeric_age and int(numeric_age.group(1)) < 18))
        if child_age or words & {"kid", "kids", "child", "children", "baby", "toddler", "teenager"}:
            context["gender"]="kids"
        elif words & {"women", "woman", "wife", "daughter", "mother", "mom", "mum", "her"}:
            context["gender"]="women"
        elif words & {"men", "man", "husband", "son", "father", "dad", "him"}:
            context["gender"]="men"
        if "drop off" in request.transcript.casefold() or "drop-off" in request.transcript.casefold():
            context["return_method"]="DROP_OFF"
        elif " ".join(request.transcript.casefold().split()) in {"store", "store return", "return in store"}:
            context["return_method"]="STORE"
        if "order" in words and "exchange" in words:
            context["secondary_intents"]=["CHECK_EXCHANGE_INVENTORY"]
        quantity_match=re.fullmatch(r"(?:quantity\s+)?(one|two|three|four|five|[1-9]|10)", " ".join(request.transcript.casefold().split()).strip(" .?!"))
        if quantity_match:
            context["quantity"]={"one":1,"two":2,"three":3,"four":4,"five":5}.get(quantity_match.group(1),int(quantity_match.group(1)) if quantity_match.group(1).isdigit() else 1)
        if context.get("product_id") and not context.get("reference_product_id"):
            context["reference_product_id"] = context["product_id"]
        purchase = any(signal in request.transcript.casefold() for signal in (
            "buy", "purchase", "order this", "order it", "place my order", "checkout", "check out"))
        if purchase and context.get("product_id") and context.get("quantity") is None:
            context["quantity"] = 1
        return {key:value for key,value in context.items() if value is not None}

    @staticmethod
    def _remember_decision(session, decision, context):
        session.last_intent = decision.intent
        session.last_route = decision.route.value
        if context.get("customer_id"): session.customer_id = context["customer_id"]
        if context.get("customer_type"): session.customer_type = context["customer_type"]
        if context.get("auth_level"): session.auth_level = context["auth_level"]
        if context.get("access_token"): session.access_token = context["access_token"]
        if context.get("order_id"): session.current_order_id = context["order_id"]
        if context.get("product_id"): session.current_product_id = context["product_id"]
        if context.get("reference_product_id"):
            session.reference_product_id = context["reference_product_id"]
        if context.get("store_id"): session.current_store_id = context["store_id"]
        if context.get("order_item_id"): session.active_order_item_id=context["order_item_id"]
        if context.get("active_variant_id"): session.active_variant_id=context["active_variant_id"]
        if context.get("product_reference") is not None: session.current_product_reference=context["product_reference"]
        if context.get("sku") is not None: session.current_sku=context["sku"]
        if context.get("page_url") is not None: session.current_page_url=context["page_url"]
        if context.get("query") is not None: session.current_search_query=context["query"]
        if context.get("visible_products") is not None:
            session.previous_recommendations = list(context["visible_products"][:10])
        for field in ("category","occasion","budget_min","budget_max","size","fit","style","gender",
                      "preferred_store","location","delivery_deadline","unresolved_issue"):
            if context.get(field) is not None:setattr(session,field,context[field])
        for field in ("colors","materials","must_have","avoid","secondary_intents"):
            if context.get(field) is not None:setattr(session,field,list(context[field]))
        if context.get("quantity") is not None: session.quantity=context["quantity"]

    @staticmethod
    def _clear_pending(session):
        session.pending_tool_name = None
        session.pending_arguments = {}
        session.pending_missing_fields = []
        session.pending_confirmation = False
        session.pending_confirmation_token = None

    @staticmethod
    def _confirmation_answer(text):
        normalized = " ".join(text.casefold().strip(" .?!").split())
        if normalized in YES or re.match(
                r"^(?:yes|correct|that's correct|thats correct|please proceed|go ahead|confirm|submit it)\b",
                normalized):
            return True
        if normalized in NO or re.match(
                r"^(?:no|cancel|stop|never mind|nevermind)\b", normalized):
            return False
        return None

    @staticmethod
    def _is_search_continuation(text):
        return any(signal in text for signal in (
            "broaden the search", "broaden search", "more in the search", "show more",
            "more options", "something else", "other options", "just my budget",
            "adjust my budget", "change my budget", "increase my budget",
            "remove the budget", "ignore the budget", "no budget limit",
        ))

    @staticmethod
    def _apply_explicit_search_relaxation(text, context, session):
        clear_formal = any(signal in text for signal in (
            "whether formal or not", "formal or not formal", "doesn't have to be formal",
            "does not have to be formal", "no matter if it is formal", "any style",
        ))
        no_color = any(signal in text for signal in (
            "no particular color", "no colour preference", "no color preference", "any color", "any colour",
        ))
        no_budget = any(signal in text for signal in (
            "just my budget", "adjust my budget", "change my budget", "increase my budget",
            "remove the budget", "ignore the budget", "no budget limit",
        ))
        broaden = VoiceService._is_search_continuation(text) and not (
            clear_formal or no_color or no_budget)
        removed = []
        if clear_formal:
            if context.get("occasion") == "formal":
                context.pop("occasion", None)
                session.occasion = None
                removed.append("formal")
            if context.get("style") == "formal":
                context.pop("style", None)
                session.style = None
                removed.append("formal")
        if no_color:
            removed.extend(str(value) for value in context.get("colors") or [])
            context.pop("color", None)
            context["colors"] = []
            session.colors = []
        if no_budget:
            context.pop("min_price", None)
            context.pop("max_price", None)
            context.pop("budget_min", None)
            context.pop("budget_max", None)
            session.budget_min = None
            session.budget_max = None
        if broaden:
            if context.get("occasion"):
                removed.append(str(context.pop("occasion")))
                session.occasion = None
            elif context.get("style"):
                removed.append(str(context.pop("style")))
                session.style = None
            elif context.get("colors"):
                removed.extend(str(value) for value in context.get("colors") or [])
                context.pop("color", None)
                context["colors"] = []
                session.colors = []
        query = str(context.get("query") or session.current_search_query or "")
        if no_budget:
            query = BUDGET_MAX.sub("", query)
            query = BUDGET_WORD.sub("", query)
            query = re.sub(r"\bdollars?\b", "", query, flags=re.IGNORECASE)
        for value in set(removed):
            query = re.sub(rf"(?<!\w){re.escape(value)}(?!\w)", "", query, flags=re.IGNORECASE)
        if query:
            context["query"] = " ".join(query.split())
            session.current_search_query = context["query"]

    @staticmethod
    def _recover_fashion_asr(transcript, session):
        text = transcript
        folded = text.casefold()
        shopping_cues = any(signal in folded for signal in (
            "wedding", "outfit", "formal", "size", "color", "colour", "under ",
            "five years old", "baby", "child", "wear",
        )) or bool(session.category or session.occasion)
        if not shopping_cues:
            return text
        if not any(signal in folded for signal in (
                "shipping address", "home address", "delivery address")):
            text = re.sub(r"\b(need|want|looking for)\s+(?:an?\s+)?address\b",
                          lambda match: f"{match.group(1)} a dress", text, flags=re.IGNORECASE)
        text = re.sub(r"\bformal\s+list\b", "formal dress", text, flags=re.IGNORECASE)
        text = re.sub(r"\bblacklist\b", "black dress", text, flags=re.IGNORECASE)
        if any(signal in folded for signal in ("wedding", "guest", "outfit")):
            text = re.sub(r"\b(?:coding|clothing)\s+desk\b", "dress", text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def _clear_shopping_context(session):
        for field in ("current_product_id", "reference_product_id", "active_variant_id", "category",
                      "occasion", "budget_min", "budget_max", "size", "fit", "style", "gender"):
            setattr(session, field, None)
        for field in ("colors", "materials", "must_have", "avoid", "previous_recommendations"):
            setattr(session, field, [])
        VoiceService._clear_pending(session)

    @staticmethod
    def _resolve_product_reference(text, context, session):
        visible = context.get("visible_products") or session.previous_recommendations
        ordinal = re.search(r"\b(?:the\s+)?(first|second|third|fourth|fifth)\s+(?:one|item|piece)\b", text)
        if ordinal and visible:
            index = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4}[ordinal.group(1)]
            if index < len(visible):
                selected = visible[index]
                context["product_id"] = selected.get("product_id")
                context["reference_product_id"] = selected.get("product_id")
                if selected.get("variant_id"): context["active_variant_id"] = selected["variant_id"]
                if selected.get("color"): context["color"] = selected["color"]
                if selected.get("size"): context["size"] = selected["size"]
        elif any(reference in text for reference in ("this one", "this item", "this piece")):
            if context.get("product_id"):
                context.setdefault("reference_product_id", context["product_id"])

    @staticmethod
    def _spoken_email(transcript):
        normalized = transcript.casefold()
        normalized = re.sub(r"\bg\s+mail\b", "gmail", normalized)
        digits = {"zero":"0", "one":"1", "two":"2", "three":"3", "four":"4",
                  "five":"5", "six":"6", "seven":"7", "eight":"8", "nine":"9"}
        normalized = re.sub(r"\b(zero|one|two|three|four|five|six|seven|eight|nine)\b",
                            lambda match: digits[match.group(1)], normalized)
        normalized = re.sub(r"\s+(?:at the rate|at sign|at direct|at)\s+", "@", normalized)
        normalized = re.sub(r"\s+dot\s+", ".", normalized)
        normalized = re.sub(r"\s*@\s*", "@", normalized)
        normalized = re.sub(r"\s*\.\s*", ".", normalized)
        marker = re.search(r"\b(?:email(?: address)?(?: is| as)?|using)\s+(.+)$", normalized)
        if marker:
            normalized = marker.group(1)
        normalized = re.sub(r"\s+", "", normalized)
        match = re.search(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+", normalized)
        return match.group(0).strip(".,") if match else None

    @staticmethod
    def _correct_pending_email(pending_email, transcript):
        """Apply an explicit spoken correction to a pending numeric local-part suffix."""
        folded = " ".join(transcript.casefold().split())
        if not re.search(r"\b(no|actually|correction|correct|meant|should be|i said)\b", folded):
            return None
        digit_words = {
            "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3",
            "four": "4", "five": "5", "six": "6", "seven": "7",
            "eight": "8", "nine": "9",
        }
        normalized = re.sub(
            r"\b(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)\b",
            lambda match: digit_words[match.group(0)], folded)
        groups = re.findall(r"(?<![a-z0-9])(?:\d[\s.-]*){2,}(?![a-z0-9])", normalized)
        if not groups or "@" not in pending_email:
            return None
        replacement = re.sub(r"\D", "", groups[-1])
        local, domain = pending_email.split("@", 1)
        if not replacement or not re.search(r"\d+$", local):
            return None
        return f"{re.sub(r'\d+$', replacement, local)}@{domain}"

    def _answer_purchase_availability_before_auth(self, transcript, text, context, session, executor):
        purchase = any(signal in text for signal in (
            "want to buy", "like to buy", "want to order", "like to order", "order this",
            "order it", "purchase this", "purchase it", "i'll take", "ill take"))
        availability = any(signal in text for signal in (
            "available", "in stock", "do you have", "have it", "is that possible"))
        if (not context.get("product_id") or context.get("access_token") or
                not purchase or not availability):
            return None
        inventory_decision = self.orchestrator.route(RouteRequest(
            message="Check inventory", context=OrchestratorContext(**context)))
        if inventory_decision.status != RouteStatus.READY:
            return None
        inventory = executor.execute(inventory_decision)
        self._remember_decision(session, inventory_decision, context)
        state = str(inventory.data.get("overall_status") or inventory.data.get("status") or "UNKNOWN")
        if inventory.execution_status != "SUCCESS" or state.upper() == "OUT_OF_STOCK":
            self.sessions.update_session(session)
            spoken = inventory.spoken_text or self.composer.compose(
                inventory_decision, inventory.data, inventory.execution_status)
            return self._response(session, "READY", inventory.execution_status, spoken,
                                  decision=inventory_decision,
                                  metadata={"capability_data": self._safe_metadata(inventory.data)})
        variants = inventory.data.get("matching_variants") or []
        if len(variants) == 1 and isinstance(variants[0], dict):
            variant_id = variants[0].get("variant_id")
            if variant_id:
                context["active_variant_id"] = variant_id
                session.active_variant_id = variant_id
        order_decision = self.orchestrator.route(RouteRequest(
            message="I want to order this", context=OrchestratorContext(**context)))
        session.pending_tool_name = order_decision.tool_name
        session.pending_arguments = dict(order_decision.tool_arguments)
        session.pending_missing_fields = list(order_decision.missing_fields)
        self.sessions.update_session(session)
        size = context.get("size")
        color = context.get("color") or ((context.get("colors") or [None])[-1])
        selection = " ".join(value for value in (
            str(color) if color else None, f"size {size}" if size else None) if value)
        quantity = inventory.data.get("total_network_available")
        stock = f" with {quantity} available" if quantity is not None else ""
        prefix = (f"The {selection} selection is {state.replace('_', ' ').lower()}{stock}."
                  if selection else f"It is {state.replace('_', ' ').lower()}{stock}.")
        return self._response(session, "NEEDS_CONTEXT", "AWAITING_CONTEXT",
                              prefix + " To prepare the order request, please provide your email address.",
                              decision=order_decision, needs_user_input=True,
                              metadata={"capability_data": self._safe_metadata(inventory.data)})

    def _answer_compound_product_question(self, transcript, text, context, session, executor):
        asks_inventory = any(signal in text for signal in
                             ("do you have", "in stock", "available in size", "have size")) or bool(
            re.search(r"\b(?:is|are)\s+(?:this|it|that|these|they)\s+(?:available\s+)?in\s+(?:size\s+)?(?:xxs|xs|s|m|l|xl|xxl|small|medium|large)\b", text))
        asks_colors = any(signal in text for signal in
                          ("what other color", "what other colour", "what colors", "what colours",
                           "available colors", "available colours")) or bool(re.search(r"\bcolou?rs\b", text))
        asks_price = any(signal in text for signal in ("price", "how much", "cost"))
        asks_material = any(signal in text for signal in ("material", "fabric", "made from"))
        asks_sizes = any(signal in text for signal in ("what sizes", "available sizes")) or bool(
            re.search(r"\bsizes\b", text))
        detail_requests = sum((asks_colors, asks_price, asks_material, asks_sizes))
        if not context.get("product_id") or not (asks_inventory and detail_requests):
            return None
        request_context = OrchestratorContext(**context)
        inventory_decision = self.orchestrator.route(RouteRequest(
            message=transcript, context=request_context))
        details_decision = self.orchestrator.route(RouteRequest(
            message="Show product details", context=request_context))
        if inventory_decision.tool_name != "check_inventory" or details_decision.tool_name != "get_product_details":
            return None
        inventory = executor.execute(inventory_decision)
        details = executor.execute(details_decision)
        self._remember_decision(session, inventory_decision, context)
        self.sessions.update_session(session)
        size = context.get("size")
        state = inventory.data.get("overall_status") or inventory.data.get("status")
        if state:
            availability = f"Size {size} is {str(state).replace('_', ' ').lower()}" if size else f"It is {str(state).replace('_', ' ').lower()}"
        else:
            availability = f"I couldn't confirm size {size} availability" if size else "I couldn't confirm availability"
        colors = []
        for color in details.data.get("colors") or []:
            value = color.get("color_name") or color.get("name") if isinstance(color, dict) else color
            if value and value not in colors:
                colors.append(str(value))
        color_text = ("The available colors are " + ", ".join(colors)) if colors else "I couldn't confirm the available colors"
        facts = [availability]
        if asks_price:
            price = details.data.get("price")
            facts.append((f"The current price is {price} {details.data.get('currency', 'USD')}"
                          if price is not None else "I couldn't confirm the current price"))
        if asks_material:
            material = details.data.get("materials_care") or details.data.get("description")
            facts.append(str(material) if material else "I couldn't confirm the material")
        if asks_colors:
            facts.append(color_text)
        if asks_sizes:
            sizes=[]
            for variant in details.data.get("variants") or []:
                value=(variant.get("size_name") or variant.get("size")) if isinstance(variant,dict) else None
                if value and value not in sizes: sizes.append(str(value))
            facts.append(("The available sizes are " + ", ".join(sizes)) if sizes
                         else "I couldn't confirm the available sizes")
        status = ("SUCCESS" if inventory.execution_status == "SUCCESS" and
                  details.execution_status == "SUCCESS" else "PARTIAL_RESULT")
        return self._response(session, "READY", status,
                              facts[0] + ". " + "; ".join(facts[1:]) + ".",
                              decision=inventory_decision,
                              metadata={"capability_data": self._safe_metadata({
                                  "inventory": inventory.data, "product_details": details.data,
                              })})

    @staticmethod
    def _focused_product_detail_response(text, data, default):
        """Answer one requested product fact without repeating the full detail card."""
        asks = {
            "price": any(signal in text for signal in ("price", "how much", "cost")),
            "colors": any(signal in text for signal in
                          ("what color", "what colour", "available color", "available colour")),
            "sizes": any(signal in text for signal in
                         ("what size", "what sizes", "available size")),
            "material": any(signal in text for signal in
                            ("material", "fabric", "made from", "composition", "cotton",
                             "synthetic", "leather")),
            "care": any(signal in text for signal in ("care", "wash", "clean")),
        }
        requested = [name for name, selected in asks.items() if selected]
        if len(requested) != 1:
            return default
        name = str(data.get("name") or "This item")
        field = requested[0]
        if field == "price":
            price = data.get("price")
            fact = (f"The current price is {price} {data.get('currency', 'USD')}"
                    if price is not None else "The current price is unavailable")
        elif field == "colors":
            colors = []
            for color in data.get("colors") or []:
                value = (color.get("color_name") or color.get("name")) if isinstance(color, dict) else color
                if value and value not in colors:
                    colors.append(str(value))
            fact = ("The available colors are " + ", ".join(colors) if colors
                    else "Color information is unavailable for this item")
        elif field == "sizes":
            sizes = []
            for variant in data.get("variants") or []:
                value = (variant.get("size_name") or variant.get("size")) if isinstance(variant, dict) else None
                if value and value not in sizes:
                    sizes.append(str(value))
            fact = ("The available sizes are " + ", ".join(sizes) if sizes
                    else "Size information is unavailable for this item")
        elif field == "care":
            care = data.get("care") or data.get("materials_care")
            fact = str(care) if care else "Care information is unavailable for this item"
        else:
            material = data.get("materials_care") or data.get("composition") or data.get("description")
            fact = (str(material) if material else
                    "Material information is unavailable for this item. I can ask human support to confirm the composition")
        return f"{name}. {fact}."

    @staticmethod
    def _shopping_clarification(text, context, session):
        if context.get("product_id"):
            return None
        if session.pending_tool_name == "search_products" and session.pending_missing_fields:
            field = session.pending_missing_fields[0]
            if not context.get(field):
                return field, CLARIFICATIONS[field]
            return None
        broad_request = any(signal in text for signal in ("i need", "looking for", "find me", "something"))
        if context.get("category") == "dress" and broad_request and not context.get("occasion"):
            context.setdefault("query", text)
            return "occasion", CLARIFICATIONS["occasion"]
        if context.get("style") in {"elegant", "formal", "modest"} and not context.get("occasion"):
            context.setdefault("query", text)
            return "occasion", CLARIFICATIONS["occasion"]
        return None

    @staticmethod
    def _interrupts_pending_clarification(text):
        return any(signal in text for signal in (
            "return", "exchange", "refund", "track", "where is my order", "policy",
            "shipping", "delivery", "payment method", "wishlist", "store", "human support",
            "speak to a person", "another customer's", "another customer’s",
        ))

    @staticmethod
    def _confirmation_prompt(decision):
        order = decision.tool_arguments.get("order_number")
        actions={"cancel_order":"cancel","create_return":"start a return for",
                 "create_exchange":"create an exchange for","create_incident":"create an incident for",
                 "create_support_case":"create a support case for"}
        action=actions.get(decision.tool_name,"complete")
        target=f" order {order}" if order else " this request"
        return f"You'd like me to {action}{target}. Should I proceed?"

    @staticmethod
    def _is_preference_update(text):
        return bool(SIZE_ONLY.match(text.rstrip("?!.")) or BUDGET_MAX.search(text) or BUDGET_WORD.search(text)
                    or any(color in text.split() for color in COLORS)
                    or any(style in text for style in STYLES))

    @staticmethod
    def _response(session, status, execution_status, spoken_text, *, decision=None,
                  needs_user_input=False, requires_confirmation=False, tool_name=None,
                  metadata=None):
        return VoiceTurnResponse(session_id=session.session_id, status=status,
            route=decision.route if decision else (Route(session.last_route) if session.last_route else None),
            intent=decision.intent if decision else session.last_intent,
            execution_status=execution_status, spoken_text=VoiceService._voice_text(spoken_text),
            needs_user_input=needs_user_input,
            missing_fields=list(decision.missing_fields) if decision else [],
            requires_confirmation=requires_confirmation,
            tool_name=tool_name or (decision.tool_name if decision else None),
            metadata={"provider": session.provider.value, "assistant_brand": settings.brand_name,
                      "conversation_turn": session.conversation_turn,
                      "session_state":{"category":session.category,"occasion":session.occasion,
                          "budget_min":session.budget_min,"budget_max":session.budget_max,
                          "size":session.size,"fit":session.fit,"style":session.style,
                          "gender":session.gender,"colors":session.colors,
                          "previous_recommendations":session.previous_recommendations,
                          "conversational_goal":session.conversational_goal,
                          "shopping_scenario":session.shopping_scenario,
                          "secondary_intents":session.secondary_intents},
                      **(metadata or {})})

    @staticmethod
    def _voice_text(value):
        text = str(value).translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'}))
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"[*_`#]+", "", text)
        text = " ".join(text.split())
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return " ".join(sentences[:4])[:600]
