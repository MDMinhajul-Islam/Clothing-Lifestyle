"""Small grouped signal sets used by the deterministic router."""

POLICY_TOPICS = (
    "return", "exchange", "refund", "shipping", "delivery", "payment", "gift card",
)
POLICY_SIGNALS = (
    "policy", "deadline", "window", "fee", "fees", "condition", "exclusion",
    "how long", "how many days", "after how many days", "what is", "what's", "how does",
)
RECOMMENDATION_SIGNALS = (
    "recommend", "suggest", "similar", "match", "matches", "matching", "go with", "pair with", "outfit",
)
PRODUCT_TERMS = (
    "dress", "dresses", "shirt", "shirts", "pants", "jeans", "jacket", "jackets",
    "blazer", "blazers", "top", "tops", "skirt", "skirts", "shoe", "shoes", "coat", "coats", "product",
)

ORDER_TOOLS = {
    "get_order", "track_order", "check_cancellation_eligibility", "cancel_order",
    "check_return_eligibility", "create_return", "get_refund_status",
    "check_exchange_availability", "get_customer_orders", "check_exchange_inventory",
    "create_exchange", "create_incident", "create_support_case", "create_order_request", "prepare_handoff",
}

REQUIRED_CONTEXT = {
    "get_product_details": ("product_id",),
    "check_inventory": ("product_id",),
    "get_customer": ("customer_id",),
    "get_order": ("order_id", "access_token"),
    "track_order": ("order_id", "access_token"),
    "check_cancellation_eligibility": ("order_id", "access_token"),
    "cancel_order": ("order_id", "access_token"),
    "check_return_eligibility": ("order_id", "access_token"),
    "create_return": ("order_id", "access_token", "items", "return_method"),
    "get_refund_status": ("order_id", "access_token"),
    "check_exchange_availability": ("order_item_id", "access_token"),
    "find_similar_products": ("reference_product_id",),
    "recommend_matching_products": ("reference_product_id",),
    "get_size_guidance": ("product_id",),
    "check_pickup_availability": ("product_id", "store_id"),
    "get_customer_profile": ("access_token",),
    "get_customer_orders": ("access_token",),
    "get_loyalty_status": ("access_token",),
    "check_promotion": ("promotion_code", "cart_subtotal"),
    "check_exchange_inventory": ("access_token", "order_item_id"),
    "create_exchange": ("access_token", "order_item_id"),
    "create_incident": ("access_token", "order_id", "order_item_id", "issue_type", "factual_summary"),
    "create_support_case": ("access_token", "issue_category", "factual_summary"),
    "create_order_request": ("access_token", "product_id", "active_variant_id", "quantity"),
    "send_secure_link": ("access_token", "destination", "purpose", "consent_confirmed"),
}
