"""Lightweight conversational strategy evaluated before capability selection."""

from dataclasses import dataclass
import re
from typing import Mapping, Any


GOALS = (
    ("HUMAN_ASSISTANCE", ("human", "person", "agent", "support")),
    ("ORDER_TRACKING", ("track order", "where is my order", "package")),
    ("POLICY", ("policy",)),
    ("RETURNS", ("return",)),
    ("REFUNDS", ("refund",)),
    ("EXCHANGES", ("exchange", "instead")),
    ("FAQ", ("how does voice shopping work", "can i shop without", "wishlist", "payment methods")),
    ("STORE_INQUIRY", ("store", "opening hours", "close")),
    ("AVAILABILITY", ("in stock", "available", "do you have")),
    ("SIZE_INQUIRY", ("size", "medium", "small", "large")),
    ("COLOR_INQUIRY", ("color", "colour")),
    ("PRICE_INQUIRY", ("price", "how much", "cost", "under", "cheaper")),
    ("MATERIAL_INQUIRY", ("material", "fabric", "cotton", "linen", "wool")),
    ("PRODUCT_COMPARISON", ("compare", "difference between")),
    ("PRODUCT_RECOMMENDATION", ("recommend", "similar", "match", "outfit")),
    ("PRODUCT_DETAILS", ("this one", "this item", "this piece", "first one", "second one")),
    ("PRODUCT_SEARCH", ("show me", "find", "looking for", "i need")),
)

SCENARIOS = (
    "formal event", "date night", "business", "interview", "wedding", "party",
    "office", "casual", "vacation", "travel", "gym", "birthday", "gift",
    "winter", "summer", "seasonal shopping", "seasonal", "formal", "luxury",
)

ASR_CORRECTIONS = {
    "blank waiting list": "black wedding dress",
    "blank wedding list": "black wedding dress",
    "black waiting list": "black wedding dress",
}


@dataclass(frozen=True)
class ConversationPolicyDecision:
    goal: str
    scenario: str | None
    strategy: str
    confidence: float
    clarification_field: str | None = None
    clarification: str | None = None
    suggested_transcript: str | None = None


class ConversationPolicy:
    """Decide how to conduct a turn without selecting or executing a capability."""

    def evaluate(self, transcript: str, context: Mapping[str, Any]) -> ConversationPolicyDecision:
        text = " ".join(transcript.casefold().split()).strip(" .?!")
        correction = ASR_CORRECTIONS.get(text)
        if correction and self._shopping_context_supports_correction(context):
            return ConversationPolicyDecision(
                goal="PRODUCT_SEARCH", scenario="wedding", strategy="clarify_asr",
                confidence=.93,
                clarification="Did you mean a black wedding dress?",
                suggested_transcript=correction,
            )
        match = next(((name, signals) for name, signals in GOALS
                      if any(signal in text for signal in signals)), None)
        goal = match[0] if match else "GENERAL_ASSISTANCE"
        scenario = next((item for item in SCENARIOS
                         if re.search(rf"(?<!\w){re.escape(item)}(?!\w)", text)), None)
        enough = self._has_actionable_context(goal, text, context)
        strategy = "recommend_or_execute" if enough else "clarify_once"
        confidence = .92 if match else .55
        clarification_field = None if enough else self._highest_value_missing(text, context)
        return ConversationPolicyDecision(goal=goal, scenario=scenario, strategy=strategy,
                                          confidence=confidence,
                                          clarification_field=clarification_field)

    @staticmethod
    def _highest_value_missing(text: str, context: Mapping[str, Any]) -> str | None:
        """Return one material clarification using the approved retail priority."""
        product_terms = re.search(r"\b(dress|shirt|jeans|jacket|shoe|coat|clothes|outfit)s?\b", text)
        if not context.get("category") and not product_terms:
            return "category"
        if context.get("category") == "dress" and not context.get("occasion"):
            return "occasion"
        return None

    @staticmethod
    def _shopping_context_supports_correction(context: Mapping[str, Any]) -> bool:
        return bool(context.get("category") or context.get("occasion") or
                    context.get("query") or context.get("visible_products") or
                    context.get("product_id"))

    @staticmethod
    def _has_actionable_context(goal: str, text: str, context: Mapping[str, Any]) -> bool:
        if goal in {"PRODUCT_DETAILS", "AVAILABILITY", "SIZE_INQUIRY", "COLOR_INQUIRY",
                    "PRICE_INQUIRY", "MATERIAL_INQUIRY"}:
            return bool(context.get("product_id") or context.get("visible_products"))
        if goal in {"PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION"}:
            workplace = (context.get("occasion") == "office" or
                           re.search(r"\b(office|corporate|workwear)\b", text))
            return bool(context.get("category") or workplace or context.get("query") or
                        re.search(r"\b(dress|shirt|jeans|jacket|shoe|coat|clothes|outfit)s?\b", text))
        return True
