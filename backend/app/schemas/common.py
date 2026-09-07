"""Common API Models, Response Envelopes, and Error Types."""

from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorCode(str, Enum):
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    VARIANT_NOT_FOUND = "VARIANT_NOT_FOUND"
    INVENTORY_UNAVAILABLE = "INVENTORY_UNAVAILABLE"
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_NOT_CANCELLABLE = "ORDER_NOT_CANCELLABLE"
    RETURN_NOT_ELIGIBLE = "RETURN_NOT_ELIGIBLE"
    REFUND_NOT_FOUND = "REFUND_NOT_FOUND"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ToolError(BaseModel):
    """Structured machine-readable error format."""
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None


class ConfirmationPayload(BaseModel):
    """Payload returned when an action requires explicit human/agent confirmation."""
    action: str
    entity_id: str
    confirmation_token: str
    prompt_message: str
    summary: Dict[str, Any]


class ResponseMeta(BaseModel):
    """Metadata about tool execution."""
    tool_name: str
    request_id: str
    duration_ms: int
    cached: bool = False


class ToolResponse(BaseModel, Generic[T]):
    """Standardized Tool Gateway Response Envelope."""
    success: bool
    data: Optional[T] = None
    error: Optional[ToolError] = None
    confirmation: Optional[ConfirmationPayload] = None
    meta: ResponseMeta
