"""Pydantic schemas for order lookup, tracking, and cancellation."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GetOrderInput(BaseModel):
    order_number: str = Field(..., description="Zara order number (e.g. 'ZUS-2025-00002')")
    customer_verification: Optional[str] = Field(None, description="Optional customer email or phone for verification")


class OrderItemSummary(BaseModel):
    order_item_id: str
    product_id: str
    variant_id: str
    product_name: str
    size: Optional[str] = None
    color: Optional[str] = None
    quantity: int
    unit_price: float
    line_discount: float
    line_total: float


class PaymentSummary(BaseModel):
    payment_method: str
    payment_status: str
    amount: float
    currency: str
    provider_reference: str


class ShipmentSummary(BaseModel):
    carrier: str
    tracking_number: str
    shipment_status: str
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None


class GetOrderOutput(BaseModel):
    order_id: str
    order_number: str
    customer_id: str
    order_status: str
    placed_at: str
    currency: str
    subtotal: float
    discount_total: float
    tax_total: float
    shipping_total: float
    grand_total: float
    items: List[OrderItemSummary]
    payment: Optional[PaymentSummary] = None
    shipment: Optional[ShipmentSummary] = None
    return_status: Optional[str] = None
    refund_status: Optional[str] = None


class TrackOrderInput(BaseModel):
    order_number: str = Field(..., description="Order number to track")


class ShipmentEventSummary(BaseModel):
    event_type: str
    description: Optional[str] = None
    location_text: Optional[str] = None
    occurred_at: str


class TrackOrderOutput(BaseModel):
    order_number: str
    order_status: str
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    shipment_status: Optional[str] = None
    shipped_at: Optional[str] = None
    estimated_delivery_at: Optional[str] = None
    delivered_at: Optional[str] = None
    events: List[ShipmentEventSummary] = Field(default_factory=list)


class CheckCancellationEligibilityInput(BaseModel):
    order_number: str = Field(..., description="Order number to check for cancellation")


class CheckCancellationEligibilityOutput(BaseModel):
    order_number: str
    eligible: bool
    current_status: str
    reason: str
    allowed_action: str


class CancelOrderInput(BaseModel):
    order_number: str = Field(..., description="Order number to cancel")
    reason: Optional[str] = Field("Customer requested cancellation via AI assistant", description="Cancellation reason")
    confirmation_token: Optional[str] = Field(None, description="HMAC confirmation token from prior check")
    confirmed: bool = Field(False, description="Explicit confirmation flag")
    idempotency_key: Optional[str] = Field(None, description="Unique client key preventing duplicate cancellation")


class CancelOrderOutput(BaseModel):
    order_number: str
    order_status: str
    cancelled_at: str
    message: str
    inventory_released: bool

