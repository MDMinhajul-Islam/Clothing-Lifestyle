"""Pydantic schemas for return eligibility, create return, refund status, and exchanges."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CheckReturnEligibilityInput(BaseModel):
    order_number: str = Field(..., description="Zara order number to check for return eligibility")
    order_item_ids: Optional[List[str]] = Field(None, description="Optional list of specific order_item_ids")


class ReturnItemEligibility(BaseModel):
    order_item_id: str
    product_name: str
    size: Optional[str] = None
    color: Optional[str] = None
    ordered_quantity: int
    already_returned_quantity: int
    available_to_return: int
    eligible: bool
    reason: str
    effective_unit_price: float
    estimated_refundable_amount: float


class CheckReturnEligibilityOutput(BaseModel):
    order_number: str
    eligible: bool
    order_status: str
    reason: str
    deadline: Optional[str] = None
    days_remaining: int
    estimated_total_refund: float
    items: List[ReturnItemEligibility]


class ReturnItemRequest(BaseModel):
    order_item_id: str = Field(..., description="ID of line item to return")
    quantity: int = Field(1, ge=1, description="Quantity to return")
    reason_code: str = Field("DOES_NOT_FIT", description="Reason code: DOES_NOT_FIT, DEFECTIVE, WRONG_ITEM, NOT_AS_DESCRIBED, CHANGED_MIND")


class CreateReturnInput(BaseModel):
    order_number: str = Field(..., description="Order number")
    items: List[ReturnItemRequest] = Field(..., min_length=1, description="Items to return")
    return_reason: str = Field("Customer initiated return via AI assistant", description="High-level return reason")
    confirmation_token: Optional[str] = Field(None, description="HMAC confirmation token from prior check")
    confirmed: bool = Field(False, description="Explicit confirmation flag")
    idempotency_key: Optional[str] = Field(None, description="Unique client key preventing duplicate return")


class CreateReturnOutput(BaseModel):
    return_id: str
    order_number: str
    return_status: str
    return_method: str
    total_items_returned: int
    estimated_refund: float
    message: str


class GetRefundStatusInput(BaseModel):
    order_number: Optional[str] = Field(None, description="Lookup refunds by order number")
    return_id: Optional[str] = Field(None, description="Lookup refunds by return ID")
    refund_id: Optional[str] = Field(None, description="Lookup by specific refund ID")


class RefundItem(BaseModel):
    refund_id: str
    order_id: str
    return_id: Optional[str] = None
    refund_status: str
    refund_method: str
    amount: float
    currency: str
    requested_at: str
    processed_at: Optional[str] = None
    provider_reference: str


class GetRefundStatusOutput(BaseModel):
    total_refunds: int
    total_amount: float
    refunds: List[RefundItem]


class CheckExchangeAvailabilityInput(BaseModel):
    order_item_id: str = Field(..., description="Original order_item_id to exchange")
    replacement_size: Optional[str] = Field(None, description="Requested replacement size (e.g. 'L')")
    replacement_color: Optional[str] = Field(None, description="Requested replacement color")
    store_id: Optional[str] = Field(None, description="Optional store ID to check local availability")


class CheckExchangeAvailabilityOutput(BaseModel):
    eligible: bool
    reason: str
    original_item: Dict[str, Any]
    replacement_variant: Optional[Dict[str, Any]] = None
    quantity_available: int = 0
    stock_status: str = "OUT_OF_STOCK"

