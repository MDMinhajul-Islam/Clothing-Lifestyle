"""Small grouped signal sets used by the deterministic router."""

POLICY_TOPICS = (
    "return", "exchange", "refund", "shipping", "delivery", "payment", "gift card",
)
POLICY_SIGNALS = (
    "policy", "deadline", "window", "fee", "fees", "condition", "exclusion",
    "how long", "what is", "what's", "how does",
)
RECOMMENDATION_SIGNALS = (
    "similar", "match", "matches", "matching", "go with", "pair with", "outfit",
)
PRODUCT_TERMS = (
    "dress", "dresses", "shirt", "shirts", "pants", "jeans", "jacket", "jackets",
    "top", "tops", "skirt", "skirts", "shoe", "shoes", "coat", "coats", "product",
)

ORDER_TOOLS = {
    "get_order", "track_order", "check_cancellation_eligibility", "cancel_order",
    "check_return_eligibility", "create_return", "get_refund_status",
    "check_exchange_availability",
}

REQUIRED_CONTEXT = {
    "get_product_details": ("product_id",),
    "check_inventory": ("product_id",),
    "get_customer": ("customer_id",),
    "get_order": ("order_id",),
    "track_order": ("order_id",),
    "check_cancellation_eligibility": ("order_id",),
    "cancel_order": ("order_id",),
    "check_return_eligibility": ("order_id",),
    "create_return": ("order_id", "items"),
    "get_refund_status": ("order_id",),
    "check_exchange_availability": ("order_item_id",),
    "find_similar_products": ("reference_product_id",),
    "recommend_matching_products": ("reference_product_id",),
}
