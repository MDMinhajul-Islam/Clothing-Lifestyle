"""Return Domain Service with confirmation protocol and quantity verification."""

import time
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
import psycopg2.extensions

from backend.app.schemas.returns import (
    CheckReturnEligibilityInput,
    CheckReturnEligibilityOutput,
    ReturnItemEligibility,
    CreateReturnInput,
    CreateReturnOutput,
)
from backend.app.schemas.common import (
    ErrorCode,
    ToolError,
    ConfirmationPayload,
)
from backend.app.repositories.return_repo import ReturnRepository
from backend.app.repositories.idempotency_repo import IdempotencyRepository
from backend.app.rules.returns import ReturnRules
from backend.app.utils.security import (
    generate_confirmation_token,
    verify_confirmation_token,
    hash_request_payload,
)


class ReturnService:
    """Domain service managing return eligibility and safe return creation."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
        self.return_repo = ReturnRepository(conn)
        self.idem_repo = IdempotencyRepository(conn)

    def check_return_eligibility(
        self,
        input_data: CheckReturnEligibilityInput
    ) -> CheckReturnEligibilityOutput:
        context = self.return_repo.get_return_context_for_order(input_data.order_number)
        if not context:
            raise ValueError(f"Order '{input_data.order_number}' was not found.")

        # Filter items if specific IDs requested
        items = context["items"]
        if input_data.order_item_ids:
            requested_set = set(input_data.order_item_ids)
            items = [i for i in items if i["order_item_id"] in requested_set]

        eval_result = ReturnRules.evaluate_order_return_eligibility(
            order=context,
            items=items
        )

        item_models = [ReturnItemEligibility(**i) for i in eval_result["items"]]

        return CheckReturnEligibilityOutput(
            order_number=input_data.order_number,
            eligible=eval_result["eligible"],
            order_status=eval_result["order_status"],
            reason=eval_result["reason"],
            deadline=eval_result.get("deadline"),
            days_remaining=eval_result.get("days_remaining", 0),
            estimated_total_refund=eval_result.get("estimated_total_refund", 0.0),
            items=item_models
        )

    def create_return(
        self,
        input_data: CreateReturnInput,
        request_id: str
    ) -> Tuple[bool, Optional[CreateReturnOutput], Optional[ToolError], Optional[ConfirmationPayload], bool]:
        """Execute return creation with confirmation and idempotency."""
        # 1. Idempotency check
        req_hash = hash_request_payload(input_data.model_dump())
        if input_data.idempotency_key:
            existing = self.idem_repo.get_idempotency_record(input_data.idempotency_key)
            if existing:
                if existing["request_hash"] == req_hash:
                    return True, CreateReturnOutput(**existing["response_json"]), None, None, True
                else:
                    return False, None, ToolError(
                        code=ErrorCode.IDEMPOTENCY_CONFLICT,
                        message="Idempotency key was previously used with different request parameters."
                    ), None, False

        # 2. Fetch context
        context = self.return_repo.get_return_context_for_order(input_data.order_number)
        if not context:
            return False, None, ToolError(
                code=ErrorCode.ORDER_NOT_FOUND,
                message=f"Order '{input_data.order_number}' was not found."
            ), None, False

        # 3. Verify general order eligibility
        eval_result = ReturnRules.evaluate_order_return_eligibility(
            order=context,
            items=context["items"]
        )
        if not eval_result["eligible"]:
            return False, None, ToolError(
                code=ErrorCode.RETURN_NOT_ELIGIBLE,
                message=eval_result["reason"]
            ), None, False

        # 4. Map and validate requested items against available quantities
        items_by_id = {i["order_item_id"]: i for i in eval_result["items"]}
        validated_items = []
        total_items_qty = 0
        total_estimated_refund = Decimal("0.00")

        for req_item in input_data.items:
            item_id = req_item.order_item_id
            if item_id not in items_by_id:
                return False, None, ToolError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Item '{item_id}' is not part of order '{input_data.order_number}'."
                ), None, False

            available_info = items_by_id[item_id]
            if req_item.quantity > available_info["available_to_return"]:
                return False, None, ToolError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=(
                        f"Requested return quantity ({req_item.quantity}) exceeds remaining "
                        f"returnable quantity ({available_info['available_to_return']}) for item '{item_id}'."
                    )
                ), None, False

            unit_refund = Decimal(str(available_info["effective_unit_price"]))
            item_refund = (unit_refund * req_item.quantity).quantize(Decimal("0.01"))
            total_estimated_refund += item_refund
            total_items_qty += req_item.quantity

            validated_items.append({
                "order_item_id": item_id,
                "quantity": req_item.quantity,
                "reason_code": req_item.reason_code,
                "refund_amount": float(item_refund),
                "name": available_info["product_name"]
            })

        # 5. Confirmation Verification
        is_token_valid = False
        if input_data.confirmation_token:
            is_token_valid = verify_confirmation_token(
                token=input_data.confirmation_token,
                expected_action="create_return",
                expected_entity_id=input_data.order_number
            )

        if not (input_data.confirmed and is_token_valid):
            token = generate_confirmation_token("create_return", input_data.order_number)
            payload = ConfirmationPayload(
                action="create_return",
                entity_id=input_data.order_number,
                confirmation_token=token,
                prompt_message=(
                    f"Please confirm: Initiating return for {total_items_qty} item(s) from order "
                    f"'{input_data.order_number}' with an estimated refund of ${total_estimated_refund:.2f}."
                ),
                summary={
                    "order_number": input_data.order_number,
                    "total_items": total_items_qty,
                    "estimated_refund": float(total_estimated_refund),
                    "items": validated_items
                }
            )
            return False, None, ToolError(
                code=ErrorCode.CONFIRMATION_REQUIRED,
                message="Return creation requires explicit confirmation."
            ), payload, False

        # 6. Execute Atomic Mutation
        return_id = f"RET-{input_data.order_number}-{int(time.time()) % 100000}"
        self.return_repo.create_return_atomic(
            return_id=return_id,
            order_id=context["order_id"],
            return_reason=input_data.return_reason,
            items=validated_items
        )

        output = CreateReturnOutput(
            return_id=return_id,
            order_number=input_data.order_number,
            return_status="REQUESTED",
            return_method="MAIL",
            total_items_returned=total_items_qty,
            estimated_refund=float(total_estimated_refund),
            message=f"Return '{return_id}' successfully created for order '{input_data.order_number}'."
        )

        if input_data.idempotency_key:
            self.idem_repo.record_idempotency(
                key=input_data.idempotency_key,
                tool_name="create_return",
                request_hash=req_hash,
                response_json=output.model_dump(),
                status="SUCCEEDED"
            )

        self.conn.commit()
        return True, output, None, None, False
