"""Return repository for return eligibility checks and atomic return creation."""

from typing import Any, Dict, List, Optional
from decimal import Decimal
from backend.app.repositories.base import BaseRepository


class ReturnRepository(BaseRepository):
    """Data access methods for returns and return items."""

    def get_return_context_for_order(self, order_number: str) -> Optional[Dict[str, Any]]:
        """Fetch order details and items with cumulative returned quantities."""
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT
                    o.order_id,
                    o.order_number,
                    o.order_status,
                    o.placed_at,
                    o.updated_at,
                    s.delivered_at
                FROM orders o
                LEFT JOIN shipments s ON o.order_id = s.order_id
                WHERE o.order_number = %s;
                """,
                (order_number.strip(),)
            )
            order = cur.fetchone()
            if not order:
                return None

            order = dict(order)

            # Fetch line items along with sum of previously returned quantities
            cur.execute(
                """
                SELECT
                    oi.order_item_id,
                    oi.product_id,
                    oi.variant_id,
                    oi.product_name_snapshot,
                    oi.size_snapshot,
                    oi.color_snapshot,
                    oi.quantity,
                    oi.unit_price,
                    oi.line_discount,
                    oi.line_total,
                    COALESCE(SUM(ri.quantity), 0)::INTEGER as already_returned_quantity
                FROM order_items oi
                LEFT JOIN return_items ri ON oi.order_item_id = ri.order_item_id
                WHERE oi.order_id = %s
                GROUP BY oi.order_item_id, oi.product_id, oi.variant_id, oi.product_name_snapshot,
                         oi.size_snapshot, oi.color_snapshot, oi.quantity, oi.unit_price,
                         oi.line_discount, oi.line_total;
                """,
                (order["order_id"],)
            )
            items = [dict(r) for r in cur.fetchall()]
            for item in items:
                item["unit_price"] = float(item["unit_price"])
                item["line_discount"] = float(item["line_discount"])
                item["line_total"] = float(item["line_total"])

            order["items"] = items
            return order

    def create_return_atomic(
        self,
        return_id: str,
        order_id: str,
        return_reason: str,
        items: List[Dict[str, Any]]
    ) -> None:
        """Atomically insert return and return items, updating order status."""
        with self.cursor() as cur:
            # 1. Insert return record
            cur.execute(
                """
                INSERT INTO returns (
                    return_id,
                    order_id,
                    return_status,
                    return_reason,
                    return_method,
                    requested_at,
                    is_synthetic
                ) VALUES (%s, %s, 'REQUESTED', %s, 'MAIL', now(), true);
                """,
                (return_id, order_id, return_reason)
            )

            # 2. Insert return items
            for idx, item in enumerate(items):
                item_id = f"RETITEM-{return_id}-{idx+1:02d}"
                cur.execute(
                    """
                    INSERT INTO return_items (
                        return_item_id,
                        return_id,
                        order_item_id,
                        quantity,
                        reason_code,
                        resolution,
                        refund_amount,
                        is_synthetic
                    ) VALUES (%s, %s, %s, %s, %s, 'REFUND', %s, true);
                    """,
                    (
                        item_id,
                        return_id,
                        item["order_item_id"],
                        item["quantity"],
                        item.get("reason_code", "DOES_NOT_FIT"),
                        Decimal(str(item.get("refund_amount", 0.00)))
                    )
                )

            # 3. Update order status to RETURN_REQUESTED
            cur.execute(
                """
                UPDATE orders
                SET order_status = 'RETURN_REQUESTED',
                    updated_at = now()
                WHERE order_id = %s;
                """,
                (order_id,)
            )
