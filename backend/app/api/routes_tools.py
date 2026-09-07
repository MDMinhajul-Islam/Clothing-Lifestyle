"""Tool Gateway Endpoints for AI / Voice-Agent Orchestration."""

import time
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, Request
import psycopg2.extensions

from backend.app.api.deps import get_db, verify_tool_secret, log_tool_audit
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
from backend.app.services.catalogue_service import CatalogueService
from backend.app.services.inventory_service import InventoryService
from backend.app.services.customer_service import CustomerService
from backend.app.services.order_service import OrderService
from backend.app.services.shipment_service import ShipmentService
from backend.app.services.return_service import ReturnService
from backend.app.services.refund_service import RefundService
from backend.app.services.exchange_service import ExchangeService

router = APIRouter(
    prefix="/v1/tools",
    tags=["AI Tool Gateway"],
    dependencies=[Depends(verify_tool_secret)],
)


def _get_request_id(x_request_id: Optional[str] = Header(None, alias="X-Request-ID")) -> str:
    return x_request_id or f"req-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# 1. CATALOGUE TOOLS
# ---------------------------------------------------------------------------

@router.post("/search-products", response_model=ToolResponse[SearchProductsOutput])
def search_products_tool(
    payload: SearchProductsInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = CatalogueService(conn)
        res = service.search_products(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "search_products", request_id, payload.dict(), "SUCCESS", dur)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="search_products", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "search_products", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="search_products", request_id=request_id, duration_ms=dur)
        )


@router.post("/get-product-details", response_model=ToolResponse[ProductDetailsOutput])
def get_product_details_tool(
    payload: GetProductDetailsInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = CatalogueService(conn)
        res = service.get_product_details(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_product_details", request_id, payload.dict(), "SUCCESS", dur)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="get_product_details", request_id=request_id, duration_ms=dur)
        )
    except ValueError as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_product_details", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.PRODUCT_NOT_FOUND)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.PRODUCT_NOT_FOUND, message=str(e)),
            meta=ResponseMeta(tool_name="get_product_details", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_product_details", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="get_product_details", request_id=request_id, duration_ms=dur)
        )


@router.post("/compare-products", response_model=ToolResponse[CompareProductsOutput])
def compare_products_tool(
    payload: CompareProductsInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = CatalogueService(conn)
        res = service.compare_products(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "compare_products", request_id, payload.dict(), "SUCCESS", dur)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="compare_products", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "compare_products", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="compare_products", request_id=request_id, duration_ms=dur)
        )


# ---------------------------------------------------------------------------
# 2. INVENTORY & STORE TOOLS
# ---------------------------------------------------------------------------

@router.post("/check-inventory", response_model=ToolResponse[CheckInventoryOutput])
def check_inventory_tool(
    payload: CheckInventoryInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = InventoryService(conn)
        res = service.check_inventory(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_inventory", request_id, payload.dict(), "SUCCESS", dur)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="check_inventory", request_id=request_id, duration_ms=dur)
        )
    except ValueError as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_inventory", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.VALIDATION_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.VALIDATION_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="check_inventory", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_inventory", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="check_inventory", request_id=request_id, duration_ms=dur)
        )


@router.post("/find-stores", response_model=ToolResponse[FindStoresOutput])
def find_stores_tool(
    payload: FindStoresInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = InventoryService(conn)
        res = service.find_stores(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "find_stores", request_id, payload.dict(), "SUCCESS", dur)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="find_stores", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "find_stores", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="find_stores", request_id=request_id, duration_ms=dur)
        )


# ---------------------------------------------------------------------------
# 3. CUSTOMER TOOLS
# ---------------------------------------------------------------------------

@router.post("/get-customer", response_model=ToolResponse[CustomerProfileOutput])
def get_customer_tool(
    payload: GetCustomerInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = CustomerService(conn)
        res = service.get_customer(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_customer", request_id, payload.dict(), "SUCCESS", dur, customer_id=res.customer_id)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="get_customer", request_id=request_id, duration_ms=dur)
        )
    except ValueError as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_customer", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.CUSTOMER_NOT_FOUND)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.CUSTOMER_NOT_FOUND, message=str(e)),
            meta=ResponseMeta(tool_name="get_customer", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_customer", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="get_customer", request_id=request_id, duration_ms=dur)
        )


# ---------------------------------------------------------------------------
# 4. ORDER & TRACKING TOOLS
# ---------------------------------------------------------------------------

@router.post("/get-order", response_model=ToolResponse[GetOrderOutput])
def get_order_tool(
    payload: GetOrderInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = OrderService(conn)
        res = service.get_order(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_order", request_id, payload.dict(), "SUCCESS", dur, order_id=res.order_number, customer_id=res.customer_id)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="get_order", request_id=request_id, duration_ms=dur)
        )
    except PermissionError as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_order", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.UNAUTHORIZED)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.UNAUTHORIZED, message=str(e)),
            meta=ResponseMeta(tool_name="get_order", request_id=request_id, duration_ms=dur)
        )
    except ValueError as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_order", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.ORDER_NOT_FOUND)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.ORDER_NOT_FOUND, message=str(e)),
            meta=ResponseMeta(tool_name="get_order", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_order", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="get_order", request_id=request_id, duration_ms=dur)
        )


@router.post("/track-order", response_model=ToolResponse[TrackOrderOutput])
def track_order_tool(
    payload: TrackOrderInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = ShipmentService(conn)
        res = service.track_order(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "track_order", request_id, payload.dict(), "SUCCESS", dur, order_id=payload.order_number)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="track_order", request_id=request_id, duration_ms=dur)
        )
    except ValueError as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "track_order", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.ORDER_NOT_FOUND)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.ORDER_NOT_FOUND, message=str(e)),
            meta=ResponseMeta(tool_name="track_order", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "track_order", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="track_order", request_id=request_id, duration_ms=dur)
        )


@router.post("/check-cancellation-eligibility", response_model=ToolResponse[CheckCancellationEligibilityOutput])
def check_cancellation_eligibility_tool(
    payload: CheckCancellationEligibilityInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = OrderService(conn)
        res = service.check_cancellation_eligibility(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_cancellation_eligibility", request_id, payload.dict(), "SUCCESS", dur, order_id=payload.order_number)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="check_cancellation_eligibility", request_id=request_id, duration_ms=dur)
        )
    except ValueError as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_cancellation_eligibility", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.ORDER_NOT_FOUND)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.ORDER_NOT_FOUND, message=str(e)),
            meta=ResponseMeta(tool_name="check_cancellation_eligibility", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_cancellation_eligibility", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="check_cancellation_eligibility", request_id=request_id, duration_ms=dur)
        )


@router.post("/cancel-order", response_model=ToolResponse[CancelOrderOutput])
def cancel_order_tool(
    payload: CancelOrderInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    service = OrderService(conn)
    success, data, error, confirmation, cached = service.cancel_order(payload, request_id)
    dur = int((time.time() - t0) * 1000)

    result_status = "SUCCESS" if success else ("CONFIRMATION_REQUIRED" if confirmation else "ERROR")
    error_code = error.code if error else None
    log_tool_audit(
        conn, "cancel_order", request_id, payload.dict(), result_status, dur,
        order_id=payload.order_number, error_code=error_code, idempotency_key=payload.idempotency_key
    )

    return ToolResponse(
        success=success,
        data=data,
        error=error,
        confirmation=confirmation,
        meta=ResponseMeta(tool_name="cancel_order", request_id=request_id, duration_ms=dur, cached=cached)
    )


# ---------------------------------------------------------------------------
# 5. RETURN & REFUND TOOLS
# ---------------------------------------------------------------------------

@router.post("/check-return-eligibility", response_model=ToolResponse[CheckReturnEligibilityOutput])
def check_return_eligibility_tool(
    payload: CheckReturnEligibilityInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = ReturnService(conn)
        res = service.check_return_eligibility(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_return_eligibility", request_id, payload.dict(), "SUCCESS", dur, order_id=payload.order_number)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="check_return_eligibility", request_id=request_id, duration_ms=dur)
        )
    except ValueError as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_return_eligibility", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.ORDER_NOT_FOUND)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.ORDER_NOT_FOUND, message=str(e)),
            meta=ResponseMeta(tool_name="check_return_eligibility", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_return_eligibility", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="check_return_eligibility", request_id=request_id, duration_ms=dur)
        )


@router.post("/create-return", response_model=ToolResponse[CreateReturnOutput])
def create_return_tool(
    payload: CreateReturnInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    service = ReturnService(conn)
    success, data, error, confirmation, cached = service.create_return(payload, request_id)
    dur = int((time.time() - t0) * 1000)

    result_status = "SUCCESS" if success else ("CONFIRMATION_REQUIRED" if confirmation else "ERROR")
    error_code = error.code if error else None
    log_tool_audit(
        conn, "create_return", request_id, payload.dict(), result_status, dur,
        order_id=payload.order_number, error_code=error_code, idempotency_key=payload.idempotency_key
    )

    return ToolResponse(
        success=success,
        data=data,
        error=error,
        confirmation=confirmation,
        meta=ResponseMeta(tool_name="create_return", request_id=request_id, duration_ms=dur, cached=cached)
    )


@router.post("/get-refund-status", response_model=ToolResponse[GetRefundStatusOutput])
def get_refund_status_tool(
    payload: GetRefundStatusInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = RefundService(conn)
        res = service.get_refund_status(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_refund_status", request_id, payload.dict(), "SUCCESS", dur, order_id=payload.order_number)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="get_refund_status", request_id=request_id, duration_ms=dur)
        )
    except ValueError as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_refund_status", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.VALIDATION_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.VALIDATION_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="get_refund_status", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "get_refund_status", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="get_refund_status", request_id=request_id, duration_ms=dur)
        )


@router.post("/check-exchange-availability", response_model=ToolResponse[CheckExchangeAvailabilityOutput])
def check_exchange_availability_tool(
    payload: CheckExchangeAvailabilityInput,
    conn: psycopg2.extensions.connection = Depends(get_db),
    request_id: str = Depends(_get_request_id),
):
    t0 = time.time()
    try:
        service = ExchangeService(conn)
        res = service.check_exchange_availability(payload)
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_exchange_availability", request_id, payload.dict(), "SUCCESS", dur)
        return ToolResponse(
            success=True,
            data=res,
            meta=ResponseMeta(tool_name="check_exchange_availability", request_id=request_id, duration_ms=dur)
        )
    except ValueError as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_exchange_availability", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.VALIDATION_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.VALIDATION_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="check_exchange_availability", request_id=request_id, duration_ms=dur)
        )
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_tool_audit(conn, "check_exchange_availability", request_id, payload.dict(), "ERROR", dur, error_code=ErrorCode.INTERNAL_ERROR)
        return ToolResponse(
            success=False,
            error=ToolError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            meta=ResponseMeta(tool_name="check_exchange_availability", request_id=request_id, duration_ms=dur)
        )

