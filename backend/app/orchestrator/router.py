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


def _has(text, values):
    return any(value in text for value in values)


class IntentRouter:
    def route(self, request: RouteRequest) -> RouteDecision:
        text = " ".join(request.message.casefold().split())
        context = request.context.model_dump(exclude_none=True)
        order_match = ORDER_ID.search(request.message)
        product_match = PRODUCT_ID.search(request.message)
        if order_match and "order_id" not in context:
            context["order_id"] = order_match.group(0).upper()
        if product_match and "product_id" not in context:
            context["product_id"] = product_match.group(0).lower()
        size_match = SIZE.search(request.message)
        if size_match and "size" not in context:
            context["size"] = size_match.group(1).upper()

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

        # 2. Dynamic account, order, catalogue, and inventory facts.
        has_order_id = "order_id" in context
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
            return self._tool("CHECK_EXCHANGE_AVAILABILITY", "check_exchange_availability",
                              context, .97, "DYNAMIC_EXCHANGE_FACT")
        if _has(text, ("in stock", "inventory", "available in size", "have size")):
            return self._tool("CHECK_INVENTORY", "check_inventory", context, .98,
                              "DYNAMIC_INVENTORY_FACT")
        if _has(text, ("current price", "product details", "available colors", "available sizes")):
            return self._tool("GET_PRODUCT_DETAILS", "get_product_details", context, .97,
                              "DYNAMIC_CATALOGUE_FACT")
        if _has(text, ("find a store", "find store", "nearest store", "store near")):
            return self._tool("FIND_STORES", "find_stores", context, .96,
                              "DYNAMIC_STORE_FACT")
        if _has(text, ("my profile", "customer profile", "customer account")):
            return self._tool("GET_CUSTOMER", "get_customer", context, .96,
                              "DYNAMIC_CUSTOMER_FACT")
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

        # 4. Reference-based semantic recommendation.
        if _has(text, RECOMMENDATION_SIGNALS):
            tool = "find_similar_products" if "similar" in text else "recommend_matching_products"
            intent = "FIND_SIMILAR_PRODUCTS" if tool == "find_similar_products" else "RECOMMEND_MATCHING_PRODUCTS"
            return self._tool(intent, tool, context, .95, "SEMANTIC_PRODUCT_INTENT",
                              route=Route.PRODUCT_RECOMMENDATION)

        # Attribute/category browsing uses the authoritative catalogue search tool.
        if _has(text, ("show me", "find", "search", "looking for")) and _has(text, PRODUCT_TERMS):
            context.setdefault("query", request.message)
            return self._tool("SEARCH_PRODUCTS", "search_products", context, .92,
                              "CATALOGUE_DISCOVERY_INTENT")

        return RouteDecision(route=Route.GENERAL_CHAT, intent="GENERAL_CONVERSATION",
            confidence=.70, reason_codes=["NO_AUTHORITATIVE_CAPABILITY_REQUIRED"])

    def _tool(self, intent, tool_name, context, confidence, reason, route=Route.TOOL_GATEWAY):
        definition = TOOL_REGISTRY[tool_name]
        missing = [field for field in REQUIRED_CONTEXT.get(tool_name, ()) if not context.get(field)]
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
            "search_products": ("query", "size", "color"),
            "get_product_details": ("product_id",),
            "check_inventory": ("product_id", "size", "color", "store_id"),
            "get_customer": ("customer_id",),
            "find_similar_products": ("reference_product_id", "size", "color"),
            "recommend_matching_products": ("reference_product_id", "size", "color"),
        }
        arguments = {key: context[key] for key in allowed.get(tool_name, ()) if context.get(key)}
        if tool_name in ORDER_TOOLS and context.get("order_id"):
            arguments["order_number"] = context["order_id"]
        if tool_name == "create_return" and context.get("items"):
            arguments["items"] = context["items"]
        if tool_name == "check_exchange_availability":
            if context.get("order_item_id"): arguments["order_item_id"] = context["order_item_id"]
            if context.get("size"): arguments["replacement_size"] = context["size"]
            if context.get("color"): arguments["replacement_color"] = context["color"]
            if context.get("store_id"): arguments["store_id"] = context["store_id"]
        return arguments
