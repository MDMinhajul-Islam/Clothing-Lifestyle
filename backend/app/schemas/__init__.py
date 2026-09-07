"""Export all schemas."""

from backend.app.schemas.common import (
    ErrorCode,
    ToolError,
    ConfirmationPayload,
    ResponseMeta,
    ToolResponse,
)
from backend.app.schemas.catalogue import (
    SearchProductsInput,
    SearchProductsOutput,
    ProductCard,
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

__all__ = [
    "ErrorCode",
    "ToolError",
    "ConfirmationPayload",
    "ResponseMeta",
    "ToolResponse",
    "SearchProductsInput",
    "SearchProductsOutput",
    "ProductCard",
    "GetProductDetailsInput",
    "ProductDetailsOutput",
    "CompareProductsInput",
    "CompareProductsOutput",
    "CheckInventoryInput",
    "CheckInventoryOutput",
    "FindStoresInput",
    "FindStoresOutput",
    "GetCustomerInput",
    "CustomerProfileOutput",
    "GetOrderInput",
    "GetOrderOutput",
    "TrackOrderInput",
    "TrackOrderOutput",
    "CheckCancellationEligibilityInput",
    "CheckCancellationEligibilityOutput",
    "CancelOrderInput",
    "CancelOrderOutput",
    "CheckReturnEligibilityInput",
    "CheckReturnEligibilityOutput",
    "CreateReturnInput",
    "CreateReturnOutput",
    "GetRefundStatusInput",
    "GetRefundStatusOutput",
    "CheckExchangeAvailabilityInput",
    "CheckExchangeAvailabilityOutput",
]

