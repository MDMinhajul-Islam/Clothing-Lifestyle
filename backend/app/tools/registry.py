"""Tool Registry and Schema Definitions for AI / Voice-Agent Orchestration."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Type
from pydantic import BaseModel

from backend.app.schemas.catalogue import (
    SearchProductsInput,
    SearchProductsOutput,
    GetProductDetailsInput,
    ProductDetailsOutput,
    CompareProductsInput,
    CompareProductsOutput,
)
from backend.app.schemas.inventory import (
    CheckInventoryInput,
    CheckInventoryOutput,
    FindStoresInput,
    FindStoresOutput,
)
from backend.app.schemas.customer import (
    GetCustomerInput,
    CustomerProfileOutput,
)
from backend.app.schemas.order import (
    GetOrderInput,
    GetOrderOutput,
    TrackOrderInput,
    TrackOrderOutput,
    CheckCancellationEligibilityInput,
    CheckCancellationEligibilityOutput,
    CancelOrderInput,
    CancelOrderOutput,
)
from backend.app.schemas.returns import (
    CheckReturnEligibilityInput,
    CheckReturnEligibilityOutput,
    CreateReturnInput,
    CreateReturnOutput,
    GetRefundStatusInput,
    GetRefundStatusOutput,
    CheckExchangeAvailabilityInput,
    CheckExchangeAvailabilityOutput,
)


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    is_write: bool
    requires_confirmation: bool
    category: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "is_write": self.is_write,
            "requires_confirmation": self.requires_confirmation,
            "input_schema": self.input_model.model_json_schema(),
            "output_schema": self.output_model.model_json_schema(),
        }


TOOL_REGISTRY: Dict[str, ToolDefinition] = {
    "search_products": ToolDefinition(
        name="search_products",
        description="Search Zara catalogue using full-text search and faceted filters (department, category, price range, color, size, on sale). Returns compact product cards.",
        input_model=SearchProductsInput,
        output_model=SearchProductsOutput,
        is_write=False,
        requires_confirmation=False,
        category="catalogue",
    ),
    "get_product_details": ToolDefinition(
        name="get_product_details",
        description="Fetch authoritative, full relational details for a Zara product by ID, including current price, variants, sizes, colors, swatches, images, and category hierarchy.",
        input_model=GetProductDetailsInput,
        output_model=ProductDetailsOutput,
        is_write=False,
        requires_confirmation=False,
        category="catalogue",
    ),
    "compare_products": ToolDefinition(
        name="compare_products",
        description="Compare 2 to 4 Zara products side-by-side across key attributes including name, price, sale status, materials, available colors, and sizes.",
        input_model=CompareProductsInput,
        output_model=CompareProductsOutput,
        is_write=False,
        requires_confirmation=False,
        category="catalogue",
    ),
    "check_inventory": ToolDefinition(
        name="check_inventory",
        description="Check real-time stock levels across retail stores and online network by product ID, variant SKU, size, or color. Never hallucinates stock.",
        input_model=CheckInventoryInput,
        output_model=CheckInventoryOutput,
        is_write=False,
        requires_confirmation=False,
        category="inventory",
    ),
    "find_stores": ToolDefinition(
        name="find_stores",
        description="Search synthetic demo Zara store locations by city, state, zip code, or geographical coordinates (ranked by distance in miles).",
        input_model=FindStoresInput,
        output_model=FindStoresOutput,
        is_write=False,
        requires_confirmation=False,
        category="stores",
    ),
    "get_customer": ToolDefinition(
        name="get_customer",
        description="Securely look up a customer profile by exact customer_id, email, or phone number. Blocks unconstrained enumeration.",
        input_model=GetCustomerInput,
        output_model=CustomerProfileOutput,
        is_write=False,
        requires_confirmation=False,
        category="customer",
    ),
    "get_order": ToolDefinition(
        name="get_order",
        description="Retrieve full details for an order by order number, including line items, payment status, shipment status, returns, and refunds.",
        input_model=GetOrderInput,
        output_model=GetOrderOutput,
        is_write=False,
        requires_confirmation=False,
        category="order",
    ),
    "track_order": ToolDefinition(
        name="track_order",
        description="Track carrier status and chronological tracking events for an order by order number.",
        input_model=TrackOrderInput,
        output_model=TrackOrderOutput,
        is_write=False,
        requires_confirmation=False,
        category="shipment",
    ),
    "check_cancellation_eligibility": ToolDefinition(
        name="check_cancellation_eligibility",
        description="Evaluate deterministic business rules to determine whether an order is eligible for cancellation before initiating any changes.",
        input_model=CheckCancellationEligibilityInput,
        output_model=CheckCancellationEligibilityOutput,
        is_write=False,
        requires_confirmation=False,
        category="order",
    ),
    "cancel_order": ToolDefinition(
        name="cancel_order",
        description="Cancel an eligible order with mandatory two-step confirmation protocol and idempotency. Releases reserved store inventory.",
        input_model=CancelOrderInput,
        output_model=CancelOrderOutput,
        is_write=True,
        requires_confirmation=True,
        category="order",
    ),
    "check_return_eligibility": ToolDefinition(
        name="check_return_eligibility",
        description="Evaluate 30-day return window, remaining returnable item quantities, and calculate estimated refundable amounts for an order.",
        input_model=CheckReturnEligibilityInput,
        output_model=CheckReturnEligibilityOutput,
        is_write=False,
        requires_confirmation=False,
        category="returns",
    ),
    "create_return": ToolDefinition(
        name="create_return",
        description="Initiate a customer return for eligible items with mandatory two-step confirmation, quantity validation, and idempotency.",
        input_model=CreateReturnInput,
        output_model=CreateReturnOutput,
        is_write=True,
        requires_confirmation=True,
        category="returns",
    ),
    "get_refund_status": ToolDefinition(
        name="get_refund_status",
        description="Inquire about processed refunds by order number, return ID, or refund ID.",
        input_model=GetRefundStatusInput,
        output_model=GetRefundStatusOutput,
        is_write=False,
        requires_confirmation=False,
        category="returns",
    ),
    "check_exchange_availability": ToolDefinition(
        name="check_exchange_availability",
        description="Check if an order item can be exchanged for an alternate size or color and verify stock availability for the replacement variant.",
        input_model=CheckExchangeAvailabilityInput,
        output_model=CheckExchangeAvailabilityOutput,
        is_write=False,
        requires_confirmation=False,
        category="returns",
    ),
}


def export_tool_definitions() -> Dict[str, Any]:
    """Export all registered tools as a structured JSON catalog."""
    return {
        "gateway_version": "1.0.0",
        "total_tools": len(TOOL_REGISTRY),
        "tools": {name: tool.to_dict() for name, tool in TOOL_REGISTRY.items()}
    }
