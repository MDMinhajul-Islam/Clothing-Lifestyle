"""Order Domain Service with strict cancellation safety flows."""

import time
from typing import Any, Dict, Optional, Tuple
import psycopg2.extensions

from backend.app.schemas.order import (
    GetOrderInput,
    GetOrderOutput,
    OrderItemSummary,
    PaymentSummary,
    ShipmentSummary,
    CheckCancellationEligibilityInput,
    CheckCancellationEligibilityOutput,
    CancelOrderInput,
    CancelOrderOutput,
)
from backend.app.schemas.common import (
    ErrorCode,
    ToolError,
    ConfirmationPayload,
)
from backend.app.repositories.order_repo import OrderRepository
from backend.app.repositories.inventory_repo import InventoryRepository
from backend.app.repositories.idempotency_repo import IdempotencyRepository
from backend.app.rules.cancellation import CancellationRules
from backend.app.utils.security import (
    generate_confirmation_token,
    verify_confirmation_token,
    hash_request_payload,
)


class OrderService:
    """Domain service managing orders and safe cancellation flows."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
        self.order_repo = OrderRepository(conn)
        self.inv_repo = InventoryRepository(conn)
        self.idem_repo = IdempotencyRepository(conn)

    def get_order(self, input_data: GetOrderInput) -> GetOrderOutput:
        order = self.order_repo.get_order_by_number(input_data.order_number)
        if not order:
            raise ValueError(f"Order '{input_data.order_number}' not found.")

        # Optional customer ownership verification
        if input_data.customer_verification:
            # Check against customer_id directly or email
            verify_val = input_data.customer_verification.strip()
            if order["customer_id"] != verify_val:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT email, phone FROM customers WHERE customer_id = %s;", (order["customer_id"],))
                    cust = cur.fetchone()
                    if not cust or (verify_val.lower() != cust[0].lower() and verify_val != cust[1]):
                        raise PermissionError("Verification identifier does not match order owner.")

        items = [OrderItemSummary(**i) for i in order["items"]]
        payment = PaymentSummary(**order["payment"]) if order.get("payment") else None
        shipment = ShipmentSummary(**order["shipment"]) if order.get("shipment") else None

        return GetOrderOutput(
            order_id=order["order_id"],
            order_number=order["order_number"],
            customer_id=order["customer_id"],
            order_status=order["order_status"],
            placed_at=order["placed_at"],
            currency=order["currency"],
            subtotal=order["subtotal"],
            discount_total=order["discount_total"],
            tax_total=order["tax_total"],
            shipping_total=order["shipping_total"],
            grand_total=order["grand_total"],
            items=items,
            payment=payment,
            shipment=shipment,
            return_status=order.get("return_status"),
            refund_status=order.get("refund_status")
        )

    def check_cancellation_eligibility(
        self,
        input_data: CheckCancellationEligibilityInput
    ) -> CheckCancellationEligibilityOutput:
        order = self.order_repo.get_order_by_number(input_data.order_number)
        if not order:
            raise ValueError(f"Order '{input_data.order_number}' not found.")

        eligible, reason, allowed_action = CancellationRules.evaluate_cancellation_eligibility(order)

        return CheckCancellationEligibilityOutput(
            order_number=order["order_number"],
            eligible=eligible,
            current_status=order["order_status"],
            reason=reason,
            allowed_action=allowed_action
        )

    def cancel_order(
        self,
        input_data: CancelOrderInput,
        request_id: str
    ) -> Tuple[bool, Optional[CancelOrderOutput], Optional[ToolError], Optional[ConfirmationPayload], bool]:
        """Execute the cancellation flow enforcing confirmation and idempotency.
        
        Returns:
            (success: bool, data: Optional[CancelOrderOutput], error: Optional[ToolError], confirmation: Optional[ConfirmationPayload], cached: bool)
        """
        # 1. Idempotency Check
        req_hash = hash_request_payload(input_data.dict())
        if input_data.idempotency_key:
            existing = self.idem_repo.get_idempotency_record(input_data.idempotency_key)
            if existing:
                if existing["request_hash"] == req_hash:
                    return True, CancelOrderOutput(**existing["response_json"]), None, None, True
                else:
                    return False, None, ToolError(
                        code=ErrorCode.IDEMPOTENCY_CONFLICT,
                        message="Idempotency key was previously used with different request parameters."
                    ), None, False

        # 2. Load order
        order = self.order_repo.get_order_by_number(input_data.order_number)
        if not order:
            return False, None, ToolError(
                code=ErrorCode.ORDER_NOT_FOUND,
                message=f"Order '{input_data.order_number}' was not found."
            ), None, False

        # 3. Verify eligibility
        eligible, reason, _ = CancellationRules.evaluate_cancellation_eligibility(order)
        if not eligible:
            return False, None, ToolError(
                code=ErrorCode.ORDER_NOT_CANCELLABLE,
                message=reason,
                details={"current_status": order["order_status"]}
            ), None, False

        # 4. Enforce Confirmation Protocol
        is_token_valid = False
        if input_data.confirmation_token:
            is_token_valid = verify_confirmation_token(
                token=input_data.confirmation_token,
                expected_action="cancel_order",
                expected_entity_id=order["order_number"]
            )

        if not (input_data.confirmed and is_token_valid):
            # Generate new confirmation token
            token = generate_confirmation_token("cancel_order", order["order_number"])
            payload = ConfirmationPayload(
                action="cancel_order",
                entity_id=order["order_number"],
                confirmation_token=token,
                prompt_message=(
                    f"Please confirm: Are you sure you want to cancel order '{order['order_number']}' "
                    f"totaling ${order['grand_total']:.2f}? This action will halt fulfillment and cannot be undone."
                ),
                summary={
                    "order_number": order["order_number"],
                    "grand_total": order["grand_total"],
                    "current_status": order["order_status"],
                    "items_count": len(order["items"])
                }
            )
            return False, None, ToolError(
                code=ErrorCode.CONFIRMATION_REQUIRED,
                message="Order cancellation requires explicit confirmation."
            ), payload, False

        # 5. Execute Atomic Mutation
        self.order_repo.cancel_order_atomic(order["order_id"])
        released_count = self.inv_repo.release_reserved_stock_for_order(order["order_id"])

        output = CancelOrderOutput(
            order_number=order["order_number"],
            order_status="CANCELLED",
            cancelled_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            message=f"Order '{order['order_number']}' was successfully cancelled.",
            inventory_released=released_count > 0
        )

        # Record idempotency if key provided
        if input_data.idempotency_key:
            self.idem_repo.record_idempotency(
                key=input_data.idempotency_key,
                tool_name="cancel_order",
                request_hash=req_hash,
                response_json=output.dict(),
                status="SUCCEEDED"
            )

        self.conn.commit()
        return True, output, None, None, False

