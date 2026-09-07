"""Stateful provider-neutral voice turn processing without direct data access."""

import re

from backend.app.config import settings
from backend.app.orchestrator.schemas import OrchestratorContext, Route, RouteRequest
from backend.app.orchestrator.service import OrchestratorService
from .executor import VoiceCapabilityExecutor
from .composer import VoiceResponseComposer
from .schemas import (
    CreateVoiceSessionRequest, EndVoiceSessionResponse, VoiceSessionView,
    VoiceTurnRequest, VoiceTurnResponse,
)
from .session import InMemoryVoiceSessionStore

YES = {"yes", "confirm", "proceed", "go ahead", "yes please", "do it"}
NO = {"no", "cancel", "never mind", "nevermind", "stop", "don't", "do not"}
ORDER_ID = re.compile(r"\b(?:ORD|ZUS)-[A-Z0-9-]+\b", re.IGNORECASE)
PRODUCT_ID = re.compile(r"\bzara-us:\d{8}\b", re.IGNORECASE)
BUDGET_MAX = re.compile(r"(?:under|below|less than|up to)\s*\$?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
SIZE_ONLY = re.compile(r"^(?:size\s+)?(xxs|xs|s|m|l|xl|xxl|small|medium|large)$", re.IGNORECASE)
COLORS = {"black", "white", "navy", "blue", "red", "green", "beige", "brown", "gray", "grey", "pink", "yellow", "orange", "purple"}
CATEGORIES = {"dress", "shirt", "pants", "jeans", "jacket", "top", "skirt", "shoes", "coat"}
CLARIFICATIONS = {
    "product_id": "Which product are you asking about?",
    "category": "What kind of item would you like?",
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
}
RESUME_MESSAGES = {
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
}


class VoiceService:
    def __init__(self, *, sessions=None, orchestrator=None, executor=None):
        self.sessions = sessions or InMemoryVoiceSessionStore()
        self.orchestrator = orchestrator or OrchestratorService()
        self.executor = executor or VoiceCapabilityExecutor()
        self.composer = VoiceResponseComposer()

    def create_session(self, request: CreateVoiceSessionRequest):
        session = self.sessions.create_session(request.provider, request.customer_id)
        return VoiceSessionView(**session.model_dump())

    def get_session(self, session_id):
        return self.sessions.get_session(session_id)

    def end_session(self, session_id):
        self.sessions.end_session(session_id)
        return EndVoiceSessionResponse(session_id=session_id, ended=True)

    def process_voice_turn(self, request: VoiceTurnRequest, *, executor=None):
        executor = executor or self.executor
        session = self.sessions.get_session(request.session_id)
        session.conversation_turn += 1
        text = " ".join(request.transcript.casefold().split())

        if any(signal in text for signal in (
            "ignore your rules", "bypass privacy", "another customer's", "another customer’s",
        )):
            decision = self.orchestrator.route(RouteRequest(message=request.transcript))
            self.sessions.update_session(session)
            return self._response(session, "READY", "SECURITY_REFUSED",
                self.composer.general(text, decision.intent), decision=decision)

        if session.pending_confirmation:
            if text in NO:
                tool = session.pending_tool_name
                self._clear_pending(session)
                self.sessions.update_session(session)
                return self._response(session, "READY", "CANCELLED_BY_USER",
                    "Okay, I won't proceed with that action.", tool_name=tool)
            if text in YES:
                return self._confirm_pending(session, executor)
            self.sessions.update_session(session)
            return self._response(session, "NEEDS_CONFIRMATION", "AWAITING_EXPLICIT_CONFIRMATION",
                "Please say yes to proceed or no to cancel.", needs_user_input=True,
                requires_confirmation=True, tool_name=session.pending_tool_name)

        context = self._merged_context(session, request)
        message = request.transcript
        if session.pending_tool_name and session.pending_missing_fields:
            message = RESUME_MESSAGES.get(session.pending_tool_name, request.transcript)
        elif (session.last_intent == "SEARCH_PRODUCTS" or session.category) and self._is_preference_update(text):
            message = "Show me products"

        decision = self.orchestrator.route(RouteRequest(message=message,
            context=OrchestratorContext(**context)))
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
        self._apply_capability_context(session, decision, result.data)
        self.sessions.update_session(session)
        spoken = result.spoken_text or self.composer.compose(decision, result.data,
                                                              result.execution_status)
        return self._response(session, "READY", result.execution_status, spoken,
                              decision=decision, metadata={"capability_data": self._safe_metadata(result.data)})

    def _confirm_pending(self, session, executor):
        tool = session.pending_tool_name
        result = executor.confirm_write(tool, session.pending_arguments,
                                        session.pending_confirmation_token)
        if result.execution_status in {"SUCCESS", "CONFIRMED_BY_GATEWAY"}:
            self._clear_pending(session)
        self.sessions.update_session(session)
        spoken = result.spoken_text or ("The action was completed." if not session.pending_confirmation
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
            "colors": list(session.colors),
            "materials": list(session.materials),
            "must_have": list(session.must_have),
            "avoid": list(session.avoid),
            "preferred_store": session.preferred_store,
            "location": session.location,
            "delivery_deadline": session.delivery_deadline,
            "secondary_intents": list(session.secondary_intents),
            "unresolved_issue": session.unresolved_issue,
        }
        context.update(session.pending_arguments)
        context.update(request.context.model_dump(exclude_none=True))
        order = ORDER_ID.search(request.transcript)
        product = PRODUCT_ID.search(request.transcript)
        if order: context["order_id"] = order.group(0).upper()
        if product: context["product_id"] = product.group(0).lower()
        budget=BUDGET_MAX.search(request.transcript)
        if budget: context["budget_max"]=float(budget.group(1))
        size=SIZE_ONLY.match(" ".join(request.transcript.casefold().split()))
        if size:
            context["size"]={"small":"S","medium":"M","large":"L"}.get(size.group(1).lower(),size.group(1).upper())
        words=set(re.findall(r"[a-z]+",request.transcript.casefold()))
        found_colors=[color for color in COLORS if color in words]
        if found_colors:
            context["colors"]=list(dict.fromkeys([*(context.get("colors") or []),*found_colors]))
            context["color"]=found_colors[-1]
        found_category=next((item for item in CATEGORIES if item in words),None)
        if found_category: context["category"]=found_category
        if "wedding" in words: context["occasion"]="wedding"
        if "drop off" in request.transcript.casefold() or "drop-off" in request.transcript.casefold():
            context["return_method"]="DROP_OFF"
        elif " ".join(request.transcript.casefold().split()) in {"store", "store return", "return in store"}:
            context["return_method"]="STORE"
        if "order" in words and "exchange" in words:
            context["secondary_intents"]=["CHECK_EXCHANGE_INVENTORY"]
        if context.get("product_id") and not context.get("reference_product_id"):
            context["reference_product_id"] = context["product_id"]
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
        for field in ("category","occasion","budget_min","budget_max","size","fit",
                      "preferred_store","location","delivery_deadline","unresolved_issue"):
            if context.get(field) is not None:setattr(session,field,context[field])
        for field in ("colors","materials","must_have","avoid","secondary_intents"):
            if context.get(field) is not None:setattr(session,field,list(context[field]))

    @staticmethod
    def _clear_pending(session):
        session.pending_tool_name = None
        session.pending_arguments = {}
        session.pending_missing_fields = []
        session.pending_confirmation = False
        session.pending_confirmation_token = None

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
        return bool(SIZE_ONLY.match(text) or any(color in text.split() for color in COLORS))

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
                          "size":session.size,"colors":session.colors,
                          "secondary_intents":session.secondary_intents},
                      **(metadata or {})})

    @staticmethod
    def _voice_text(value):
        text = re.sub(r"https?://\S+", "", str(value))
        text = re.sub(r"[*_`#]+", "", text)
        text = " ".join(text.split())
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return " ".join(sentences[:4])[:600]
