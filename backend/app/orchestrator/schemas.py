from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Route(str, Enum):
    GENERAL_CHAT = "GENERAL_CHAT"
    POLICY_RAG = "POLICY_RAG"
    PRODUCT_RECOMMENDATION = "PRODUCT_RECOMMENDATION"
    TOOL_GATEWAY = "TOOL_GATEWAY"


class RouteStatus(str, Enum):
    READY = "READY"
    NEEDS_CONTEXT = "NEEDS_CONTEXT"


class OrchestratorContext(BaseModel):
    customer_type: str | None = None
    auth_level: str | None = None
    access_token: str | None = None
    customer_id: str | None = None
    order_id: str | None = None
    order_item_id: str | None = None
    items: list[dict[str, Any]] | None = None
    product_id: str | None = None
    reference_product_id: str | None = None
    active_variant_id: str | None = None
    category: str | None = None
    occasion: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    size: str | None = None
    fit: str | None = None
    style: str | None = None
    gender: str | None = None
    color: str | None = None
    colors: list[str] | None = None
    materials: list[str] | None = None
    must_have: list[str] | None = None
    avoid: list[str] | None = None
    store_id: str | None = None
    preferred_store: str | None = None
    location: str | None = None
    delivery_deadline: str | None = None
    secondary_intents: list[str] | None = None
    unresolved_issue: str | None = None
    query: str | None = None
    product_reference: str | None = None
    sku: str | None = None
    page_url: str | None = None
    visible_products: list[dict[str, Any]] | None = None
    email: str | None = None
    phone: str | None = None
    verification_value: str | None = None
    promotion_code: str | None = None
    cart_subtotal: float | None = None
    destination: str | None = None
    purpose: str | None = None
    consent_confirmed: bool | None = None
    issue_type: str | None = None
    issue_category: str | None = None
    factual_summary: str | None = None
    requested_outcome: str | None = None
    return_method: str | None = None

    @field_validator("customer_type", "auth_level", "access_token", "customer_id", "order_id",
                     "order_item_id", "product_id", "reference_product_id", "active_variant_id",
                     "category", "occasion", "size", "fit", "style", "gender", "color",
                     "store_id", "query", "product_reference", "sku", "page_url", "email", "phone", "verification_value", "promotion_code",
                     "preferred_store", "location", "delivery_deadline", "unresolved_issue",
                     "destination", "purpose", "issue_type", "issue_category", "factual_summary", "requested_outcome",
                     "return_method")
    @classmethod
    def strip_values(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class RouteRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    context: OrchestratorContext = Field(default_factory=OrchestratorContext)

    @field_validator("message")
    @classmethod
    def nonblank_message(cls, value):
        if not value.strip():
            raise ValueError("message cannot be blank")
        return value.strip()


class RouteDecision(BaseModel):
    status: RouteStatus = RouteStatus.READY
    route: Route
    intent: str
    confidence: float = Field(ge=0, le=1)
    tool_name: str | None = None
    requires_confirmation: bool = False
    requires_customer_context: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    reason_codes: list[str]
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
