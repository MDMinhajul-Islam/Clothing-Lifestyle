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
    customer_id: str | None = None
    order_id: str | None = None
    order_item_id: str | None = None
    items: list[dict[str, Any]] | None = None
    product_id: str | None = None
    reference_product_id: str | None = None
    size: str | None = None
    color: str | None = None
    store_id: str | None = None
    query: str | None = None

    @field_validator("customer_id", "order_id", "order_item_id", "product_id",
                     "reference_product_id", "size", "color", "store_id", "query")
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
