"""Refund Domain Service."""

from typing import List, Optional
import psycopg2.extensions
from backend.app.schemas.returns import (
    GetRefundStatusInput,
    GetRefundStatusOutput,
    RefundItem,
)
from backend.app.repositories.refund_repo import RefundRepository


class RefundService:
    """Domain service managing refund status inquiries."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.repo = RefundRepository(conn)

    def get_refund_status(self, input_data: GetRefundStatusInput) -> GetRefundStatusOutput:
        if not (input_data.order_number or input_data.return_id or input_data.refund_id):
            raise ValueError("Must provide order_number, return_id, or refund_id.")

        rows = self.repo.get_refunds(
            order_number=input_data.order_number,
            return_id=input_data.return_id,
            refund_id=input_data.refund_id
        )

        items = [RefundItem(**r) for r in rows]
        total_amount = sum(r.amount for r in items)

        return GetRefundStatusOutput(
            total_refunds=len(items),
            total_amount=round(total_amount, 2),
            refunds=items
        )

