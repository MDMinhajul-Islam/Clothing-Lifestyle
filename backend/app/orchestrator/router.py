"""Priority-ordered deterministic intent router. It never accesses a database."""

import re

from backend.app.tools.registry import TOOL_REGISTRY
from .intent_rules import (
    ORDER_TOOLS, POLICY_SIGNALS, POLICY_TOPICS, PRODUCT_TERMS,
    RECOMMENDATION_SIGNALS, REQUIRED_CONTEXT,
)
from .schemas import Route, RouteDecision, RouteRequest, RouteStatus

ORDER_ID = re.compile(r"\b(?:ORD|ZUS)-[A-Z0-9-]+\b", re.IGNORECASE)
PRODUCT_ID = re.compile(r"\bzara-us:\d{8}\b", re.IGNORECASE)
SIZE = re.compile(r"\bsize\s+([A-Z0-9]+)\b", re.IGNORECASE)
CURRENT_PRODUCT_REFERENCE = re.compile(
    r"\b(?:it|that|that one|the product|the item|the piece|the dress|the shirt|"
    r"the shoes?|the jeans|the trousers|the pants|the blazer|the jacket|the coat|"
    r"the skirt|the top|the bag|the handbag|the hoodie|the sweater)\b",
    re.IGNORECASE,
)
POSITIVE_PRODUCT_SENTIMENT = re.compile(
    r"\b(?:i\s+)?(?:love|like|really like|prefer|adore)\b",
    re.IGNORECASE,
)
EXPLICIT_EXTERNAL_TOPIC = re.compile(
    r"^(?:explain|define|who is|what is|tell me about)\s+"
    r"(?!(?:it|that|this|the (?:product|item|piece|dress|shirt|shoes?|jeans|"
    r"trousers|pants|blazer|jacket|coat|skirt|top|bag|handbag|hoodie|sweater))\b)",
    re.IGNORECASE,
)


def _has(text, values):
    return any(value in text for value in values)


class IntentRouter:
    def route(self, request: RouteRequest) -> RouteDecision:
        text = " ".join(request.message.casefold().split())
        context = request.context.model_dump(exclude_none=True)
        if _has(text, ("ignore your rules", "bypass privacy", "another customer's", "another customer’s")):
            return RouteDecision(route=Route.GENERAL_CHAT, intent="SECURITY_REFUSAL",
                confidence=.99, reason_codes=["PROMPT_INJECTION_BLOCKED", "PRIVACY_BOUNDARY"])
        order_match = ORDER_ID.search(request.message)
        product_match = PRODUCT_ID.search(request.message)
        if order_match and "order_id" not in context:
            context["order_id"] = order_match.group(0).upper()
        if product_match and "product_id" not in context:
            context["product_id"] = product_match.group(0).lower()
        if context.get("reference_product_id") and not context.get("product_id"):
            context["product_id"] = context["reference_product_id"]
        size_match = SIZE.search(request.message)
        if size_match and "size" not in context:
            context["size"] = size_match.group(1).upper()

        current_product = bool(context.get("product_id") or context.get("active_variant_id"))
        purchase_intent = _has(text, ("want to buy", "like to buy", "want to order",
                                      "like to order", "place my order", "confirm my order",
                                      "continue with my order", "proceed with my order",
                                      "check out", "checkout", "i'll take", "ill take"))
        requested_size = bool(SIZE.search(request.message) or re.search(
            r"\b(?:xs|s|m|l|xl|xxl|small|medium|large)(?:\s+size)?\b", text))
        refers_to_current_product = (
            _has(text, ("this", "this one", "this item", "this piece"))
            or bool(CURRENT_PRODUCT_REFERENCE.search(text))
        )
        if current_product and (purchase_intent or (requested_size and refers_to_current_product)):
            if purchase_intent:
                return self._tool("CREATE_ORDER_REQUEST", "create_order_request", context, .99,
                                  "CURRENT_PRODUCT_ORDER_REQUEST")
            return self._tool("PURCHASE_GUIDANCE", "check_inventory", context, .98,
                              "CURRENT_PRODUCT_PURCHASE_GUIDANCE")
        if current_product and re.fullmatch(r"(?:do you have (?:this|it) in )?(?:size )?(?:xs|s|m|l|xl|xxl|small|medium|large)\??", text):
            return self._tool("CHECK_INVENTORY", "check_inventory", context, .98,
                              "CURRENT_PRODUCT_INVENTORY")
        if current_product and not _has(text, RECOMMENDATION_SIGNALS) and _has(text, ("how much", "what does it cost", "what colors", "what other colors", "which colors", "what colour", "what other colours", "this one", "this item", "this piece", "first one", "second one", "third one", "fourth one", "fifth one", "tell me about")):
            return self._tool("GET_PRODUCT_DETAILS", "get_product_details", context, .97,
                              "CURRENT_PRODUCT_CONTEXT")
        if current_product and refers_to_current_product and POSITIVE_PRODUCT_SENTIMENT.search(text):
            return self._tool("GET_PRODUCT_DETAILS", "get_product_details", context, .96,
                              "CURRENT_PRODUCT_SENTIMENT")

        # 1. Explicit writes. Confirmation remains owned by the Tool Gateway.
        return_action = "return" in text and (
            re.search(r"\b(start|initiate|create|open|begin|file)\b.*\breturn\b", text)
            or re.search(r"\breturn\b.*\b(start|initiate|create|open|begin|file)\b", text)
        )
        cancel_action = bool(re.search(r"^(please\s+)?cancel\b", text) or
                             re.search(r"\b(want|need|please)\b.*\bcancel\b", text))
        if return_action:
            return self._tool("CREATE_RETURN", "create_return", context, .99,
                              "WRITE_ACTION_INTENT")
        if cancel_action:
            return self._tool("CANCEL_ORDER", "cancel_order", context, .99,
                              "WRITE_ACTION_INTENT")
        if "exchange" in text and _has(text,("start", "create", "request", "want", "need", "process", "place the exchange")):
            context.setdefault("issue_category","EXCHANGE_REQUEST")
            context.setdefault("requested_outcome", "Human review for an exchange" +
                               (f" in size {context['size']}" if context.get('size') else "") +
                               (f" and color {context['color']}" if context.get('color') else ""))
            if _has(text,("because", "too small", "too large", "wrong", "damaged", "doesn't fit", "does not fit")):
                context.setdefault("factual_summary",request.message)
            return self._tool("CREATE_EXCHANGE_CASE","create_support_case",context,.99,"HUMAN_REVIEW_CASE")
        if "refund" in text and _has(text,("request", "want", "need", "start", "submit")):
            context.setdefault("issue_category","REFUND_REQUEST")
            context.setdefault("requested_outcome","Human refund review")
            if _has(text,("because", "reason", "damaged", "wrong", "missing", "late", "not received")):
                context.setdefault("factual_summary",request.message)
            return self._tool("CREATE_REFUND_CASE","create_support_case",context,.99,"HUMAN_REVIEW_CASE")
        if _has(text,("arrived damaged","damaged item","wrong item","missing item","defective item","delivered but")):
            context.setdefault("factual_summary",request.message)
            if not context.get("issue_type"):
                signals=(("damaged","DAMAGED_ITEM"),("wrong","WRONG_ITEM"),("missing","MISSING_ITEM"),("defective","DEFECTIVE_ITEM"),("delivered","DELIVERED_NOT_RECEIVED"))
                context["issue_type"]=next((kind for word,kind in signals if word in text),None)
            return self._tool("CREATE_INCIDENT","create_incident",context,.98,"VERIFIED_INCIDENT_INTAKE")
        if _has(text,("open a support case","create a support case","file a support case")):
            context.setdefault("factual_summary",request.message)
            context.setdefault("issue_category","GENERAL_SUPPORT")
            return self._tool("CREATE_SUPPORT_CASE","create_support_case",context,.98,"SUPPORT_CASE_ACTION")

        # 2. Dynamic account, order, catalogue, and inventory facts.
        has_order_id = "order_id" in context
        if not has_order_id and _has(text, POLICY_TOPICS) and _has(text, POLICY_SIGNALS):
            return RouteDecision(route=Route.POLICY_RAG, intent="RETRIEVE_POLICY_KNOWLEDGE",
                confidence=.96, tool_name="retrieve_policy_knowledge",
                reason_codes=["GENERAL_POLICY_QUESTION", "OFFICIAL_RAG_REQUIRED"],
                tool_arguments={"query": request.message, "market": "US", "locale": "en"})
        if "cancel" in text and _has(text, ("can i", "eligible", "eligibility")):
            return self._tool("CHECK_CANCELLATION_ELIGIBILITY",
                              "check_cancellation_eligibility", context, .98,
                              "DYNAMIC_ORDER_FACT")
        if "return" in text and has_order_id and _has(text, ("can i", "eligible", "eligibility")):
            return self._tool("CHECK_RETURN_ELIGIBILITY", "check_return_eligibility",
                              context, .98, "DYNAMIC_ORDER_FACT")
        if _has(text, ("track order", "track my order", "where is my order", "shipment status")):
            return self._tool("TRACK_ORDER", "track_order", context, .98,
                              "DYNAMIC_SHIPMENT_FACT")
        if "refund" in text and _has(text, ("status", "where", "processed")):
            return self._tool("GET_REFUND_STATUS", "get_refund_status", context, .97,
                              "DYNAMIC_REFUND_FACT")
        if "exchange" in text and _has(text, ("available", "availability", "size", "color")):
            return self._tool("CHECK_EXCHANGE_INVENTORY", "check_exchange_inventory",
                              context, .97, "DYNAMIC_EXCHANGE_FACT")
        if _has(text, ("in stock", "inventory", "available in size", "have size", "do you have")):
            return self._tool("CHECK_INVENTORY", "check_inventory", context, .98,
                              "DYNAMIC_INVENTORY_FACT")
        if _has(text,("pick up","pick this up","pickup","collect in store","store pickup")):
            return self._tool("CHECK_PICKUP_AVAILABILITY","check_pickup_availability",context,.98,"DYNAMIC_PICKUP_FACT")
        if _has(text,("points","loyalty","rewards","reward tier","member tier")):
            return self._tool("GET_LOYALTY_STATUS","get_loyalty_status",context,.98,"PRIVATE_LOYALTY_FACT")
        if _has(text,("coupon","promotion code","promo code","discount code")):
            return self._tool("CHECK_PROMOTION","check_promotion",context,.97,"SYNTHETIC_PROMOTION_CHECK")
        if _has(text,("what size did i buy","purchase recently","purchased recently","bought last time","order history","buy the same","latest order","recent orders")):
            return self._tool("GET_CUSTOMER_ORDERS","get_customer_orders",context,.97,"PRIVATE_ORDER_HISTORY")
        if "exchange" in text and _has(text,("next size","too small","too large","replacement","available")):
            return self._tool("CHECK_EXCHANGE_INVENTORY","check_exchange_inventory",context,.97,"EXCHANGE_ELIGIBILITY_AND_INVENTORY")
        if _has(text,("size guidance","what size","which size","fit guidance","how does this fit")):
            return self._tool("GET_SIZE_GUIDANCE","get_size_guidance",context,.95,"DOCUMENTED_SIZE_EVIDENCE")
        if _has(text,("speak to a person","talk to a person","human support","human agent","speak to an agent")):
            context.setdefault("factual_summary",request.message); context.setdefault("intent","HUMAN_SUPPORT_REQUEST")
            return self._tool("PREPARE_HANDOFF","prepare_handoff",context,.99,"HUMAN_HANDOFF_REQUEST")
        if _has(text,("send me a link","text me a link","email me a link","secure link")):
            return self._tool("SEND_SECURE_LINK","send_secure_link",context,.96,"SECURE_LINK_REQUEST")
        if _has(text,("verify my account","verify me","verify my order")):
            return self._tool("VERIFY_CUSTOMER","verify_customer",context,.96,"CUSTOMER_VERIFICATION_REQUEST")
        if _has(text,("identify me","find my account","recognize my account")):
            return self._tool("IDENTIFY_CUSTOMER","identify_customer",context,.95,"CUSTOMER_IDENTIFICATION_REQUEST")
        if _has(text, ("current price", "product details", "available colors", "available sizes")):
            return self._tool("GET_PRODUCT_DETAILS", "get_product_details", context, .97,
                              "DYNAMIC_CATALOGUE_FACT")
        if _has(text, ("cotton", "material", "fabric", "machine wash", "care instructions")):
            return self._tool("GET_PRODUCT_DETAILS", "get_product_details", context, .96,
                              "PRODUCT_SPECIFIC_FACT")
        if _has(text, ("find a store", "find store", "nearest store", "store near")):
            return self._tool("FIND_STORES", "find_stores", context, .96,
                              "DYNAMIC_STORE_FACT")
        if _has(text, ("my profile", "customer profile", "customer account")):
            return self._tool("GET_CUSTOMER_PROFILE", "get_customer_profile", context, .96,
                              "PRIVATE_CUSTOMER_FACT")
        if has_order_id and _has(text, ("order details", "order information", "order status")):
            return self._tool("GET_ORDER", "get_order", context, .96,
                              "DYNAMIC_ORDER_FACT")

        # 3. Official policies. A policy mention without a concrete eligibility/action
        # request stays here even when it says "my order".
        if _has(text, POLICY_TOPICS) and _has(text, POLICY_SIGNALS):
            return RouteDecision(route=Route.POLICY_RAG, intent="RETRIEVE_POLICY_KNOWLEDGE",
                confidence=.96, tool_name="retrieve_policy_knowledge",
                reason_codes=["OFFICIAL_POLICY_QUESTION", "OFFICIAL_RAG_REQUIRED"],
                tool_arguments={"query": request.message, "market": "US", "locale": "en"})

        # A category-specific request asks the catalogue for grounded choices even
        # when an unrelated webpage product remains in session context.
        if _has(text, ("recommend", "suggest")) and _has(text, PRODUCT_TERMS):
            context["query"] = request.message
            return self._tool("SEARCH_PRODUCTS", "search_products", context, .95,
                              "GROUNDED_CATEGORY_RECOMMENDATION")

        # 4. Reference-based semantic recommendation.
        if _has(text, RECOMMENDATION_SIGNALS):
            tool = "find_similar_products" if "similar" in text else "recommend_matching_products"
            intent = "FIND_SIMILAR_PRODUCTS" if tool == "find_similar_products" else "RECOMMEND_MATCHING_PRODUCTS"
            return self._tool(intent, tool, context, .95, "SEMANTIC_PRODUCT_INTENT",
                              route=Route.PRODUCT_RECOMMENDATION)

        if context.get("occasion") and _has(text, ("clothes", "clothing", "outfit")):
            if text != "show me products" or not context.get("query"):
                context["query"] = request.message
            return self._tool("SEARCH_PRODUCTS", "search_products", context, .92,
                              "OCCASION_DISCOVERY_INTENT")

        if _has(text, ("wedding", "bridal", "occasion", "party", "formal", "evening",
                       "office", "business", "work event", "business meeting", "interview",
                       "date night", "vacation", "festival", "eid", "gift")) and not _has(text, PRODUCT_TERMS):
            return RouteDecision(status=RouteStatus.NEEDS_CONTEXT, route=Route.TOOL_GATEWAY,
                intent="SEARCH_PRODUCTS", confidence=.91, tool_name="search_products",
                missing_fields=["category"], reason_codes=["BROAD_SHOPPING_INTENT", "HIGH_VALUE_CLARIFICATION"],
                tool_arguments={"query": request.message})

        # Attribute/category browsing uses the authoritative catalogue search tool.
        if _has(text, ("show me", "find", "search", "looking for", "i need", "need a")) and _has(text, PRODUCT_TERMS):
            if text != "show me products" or not context.get("query"):
                context["query"] = request.message
            return self._tool("SEARCH_PRODUCTS", "search_products", context, .92,
                              "CATALOGUE_DISCOVERY_INTENT")

        if (request.context.reference_product_id
                and not EXPLICIT_EXTERNAL_TOPIC.search(text)):
            return self._tool("GET_PRODUCT_DETAILS", "get_product_details", context, .90,
                              "AUTHORITATIVE_CURRENT_PRODUCT_FALLBACK")

        return RouteDecision(route=Route.GENERAL_CHAT, intent="GENERAL_CONVERSATION",
            confidence=.70, reason_codes=["NO_AUTHORITATIVE_CAPABILITY_REQUIRED"])

    def _tool(self, intent, tool_name, context, confidence, reason, route=Route.TOOL_GATEWAY):
        definition = TOOL_REGISTRY[tool_name]
        missing = [field for field in REQUIRED_CONTEXT.get(tool_name, ()) if not context.get(field)]
        if tool_name == "check_inventory" and context.get("active_variant_id"):
            missing = [field for field in missing if field != "product_id"]
        if tool_name == "create_support_case" and context.get("issue_category") in {"EXCHANGE_REQUEST","REFUND_REQUEST"}:
            if not context.get("order_id"): missing.append("order_id")
            if context.get("issue_category") == "EXCHANGE_REQUEST":
                for field in ("size","color"):
                    if not context.get(field): missing.append(field)
        if tool_name in {"identify_customer","verify_customer"} and not any(context.get(k) for k in ("email","phone","order_id")):
            missing.append("email_or_phone_or_order_id")
        if tool_name=="verify_customer" and not context.get("verification_value"):
            missing.append("verification_value")
        arguments = self._arguments(tool_name, context)
        return RouteDecision(status=RouteStatus.NEEDS_CONTEXT if missing else RouteStatus.READY,
            route=route, intent=intent, confidence=confidence, tool_name=tool_name,
            requires_confirmation=definition.requires_confirmation,
            requires_customer_context=tool_name in ORDER_TOOLS or tool_name == "get_customer",
            missing_fields=missing,
            reason_codes=[reason, "AUTHORITATIVE_TOOL_REQUIRED"], tool_arguments=arguments)

    @staticmethod
    def _arguments(tool_name, context):
        allowed = {
            "search_products": ("query", "size", "color", "min_price", "max_price",
                                "product_type", "department", "occasion", "material", "brand"),
            "get_product_details": ("product_id",),
            "check_inventory": ("product_id", "size", "color", "store_id"),
            "get_size_guidance": ("product_id",),
            "check_pickup_availability": ("product_id","store_id","size","color"),
            "identify_customer": ("email","phone"),
            "verify_customer": ("email","phone","verification_value"),
            "get_customer_profile": ("access_token",),
            "get_customer_orders": ("access_token",),
            "get_loyalty_status": ("access_token",),
            "check_promotion": ("promotion_code","cart_subtotal","product_id"),
            "get_order": ("access_token",),
            "track_order": ("access_token",),
            "check_cancellation_eligibility": ("access_token",),
            "cancel_order": ("access_token",),
            "check_return_eligibility": ("access_token",),
            "create_return": ("access_token","return_method"),
            "get_refund_status": ("access_token",),
            "check_exchange_availability": ("access_token",),
            "check_exchange_inventory": ("access_token","order_item_id","size","color","store_id"),
            "create_exchange": ("access_token","order_item_id","size","color","store_id"),
            "create_incident": ("access_token","order_item_id","issue_type","factual_summary"),
            "create_support_case": ("access_token","product_id","issue_category","factual_summary","requested_outcome"),
            "create_order_request": ("access_token","product_id","size","quantity","shipping_address_id","shipping_address"),
            "prepare_handoff": ("access_token","product_id","factual_summary","requested_outcome"),
            "send_secure_link": ("access_token","destination","purpose","consent_confirmed"),
            "get_customer": ("customer_id",),
            "find_similar_products": ("reference_product_id", "size", "color", "min_price", "max_price", "target_category", "department"),
            "recommend_matching_products": ("reference_product_id", "size", "color", "min_price", "max_price", "target_category", "department"),
        }
        arguments = {key: context[key] for key in allowed.get(tool_name, ()) if context.get(key)}
        if tool_name == "search_products":
            if context.get("budget_min") is not None: arguments["min_price"] = context["budget_min"]
            if context.get("budget_max") is not None: arguments["max_price"] = context["budget_max"]
            if context.get("category"): arguments["product_type"] = context["category"]
            if context.get("occasion"): arguments["occasion"] = context["occasion"]
            if not arguments.get("color") and context.get("colors"):
                arguments["color"] = context["colors"][-1]
            if context.get("materials"): arguments["material"] = context["materials"][-1]
            if context.get("gender"):
                arguments["department"] = {"women":"WOMAN", "men":"MAN", "kids":"KIDS"}.get(
                    str(context["gender"]).casefold(), context["gender"])
        if tool_name in {"find_similar_products", "recommend_matching_products"}:
            if context.get("budget_min") is not None: arguments["min_price"] = context["budget_min"]
            if context.get("budget_max") is not None: arguments["max_price"] = context["budget_max"]
            if context.get("category") is not None: arguments["target_category"] = context["category"]
            if context.get("gender") is not None:
                arguments["department"] = {"women":"WOMAN", "men":"MAN", "kids":"KIDS"}.get(
                    str(context["gender"]).casefold(), context["gender"])
        if tool_name == "check_inventory" and context.get("active_variant_id"):
            arguments["variant_id"] = context["active_variant_id"]
        if tool_name == "create_order_request" and context.get("active_variant_id"):
            arguments["variant_id"] = context["active_variant_id"]
        if tool_name in ORDER_TOOLS and context.get("order_id"):
            arguments["order_number"] = context["order_id"]
        if tool_name == "create_return" and context.get("items"):
            arguments["items"] = context["items"]
        if tool_name == "check_exchange_availability":
            if context.get("order_item_id"): arguments["order_item_id"] = context["order_item_id"]
            if context.get("size"): arguments["replacement_size"] = context["size"]
            if context.get("color"): arguments["replacement_color"] = context["color"]
            if context.get("store_id"): arguments["store_id"] = context["store_id"]
        if context.get("order_id") and tool_name in {"identify_customer","verify_customer"}:
            arguments["order_number"]=context["order_id"]
        if context.get("order_id") and tool_name in {"create_incident","create_support_case","prepare_handoff"}:
            arguments["order_number"]=context["order_id"]
        if tool_name in {"check_exchange_inventory","create_exchange"}:
            if arguments.pop("size",None): arguments["replacement_size"]=context["size"]
            if arguments.pop("color",None): arguments["replacement_color"]=context["color"]
        if tool_name=="prepare_handoff":
            arguments["intent"]=context.get("intent","HUMAN_SUPPORT_REQUEST")
        return arguments
