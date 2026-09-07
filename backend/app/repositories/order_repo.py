"""Order repository for order details and cancellation mutations."""

from typing import Any, Dict, List, Optional
from backend.app.repositories.base import BaseRepository


class OrderRepository(BaseRepository):
    """Data access methods for orders, order items, and cancellation."""

    def get_order_by_number(self, order_number: str) -> Optional[Dict[str, Any]]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT
                    order_id,
                    order_number,
                    customer_id,
                    order_status,
                    fulfillment_type,
                    shipping_address_id,
                    store_id,
                    currency,
                    subtotal,
                    discount_total,
                    tax_total,
                    shipping_total,
                    grand_total,
                    payment_status,
                    placed_at,
                    confirmed_at,
                    cancelled_at,
                    completed_at
                FROM orders
                WHERE order_number = %s;
                """,
                (order_number.strip(),)
            )
            order = cur.fetchone()
            if not order:
                return None

            order = dict(order)
            order["customer_id"] = str(order["customer_id"])
            order["subtotal"] = float(order["subtotal"])
            order["discount_total"] = float(order["discount_total"])
            order["tax_total"] = float(order["tax_total"])
            order["shipping_total"] = float(order["shipping_total"])
            order["grand_total"] = float(order["grand_total"])
            order["placed_at"] = order["placed_at"].isoformat() if order.get("placed_at") else None

            # Fetch line items
            cur.execute(
                """
                SELECT
                    order_item_id,
                    product_id,
                    variant_id,
                    product_name_snapshot as product_name,
                    size_snapshot as size,
                    color_snapshot as color,
                    quantity,
                    unit_price,
                    line_discount,
                    line_total
                FROM order_items
                WHERE order_id = %s;
                """,
                (order["order_id"],)
            )
            items = [dict(i) for i in cur.fetchall()]
            for i in items:
                i["unit_price"] = float(i["unit_price"])
                i["line_discount"] = float(i["line_discount"])
                i["line_total"] = float(i["line_total"])
            order["items"] = items

            # Fetch payment
            cur.execute(
                """
                SELECT payment_method, payment_status, amount, currency, provider_reference
                FROM payments
                WHERE order_id = %s
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (order["order_id"],)
            )
            payment = cur.fetchone()
            if payment:
                p_dict = dict(payment)
                p_dict["amount"] = float(p_dict["amount"])
                order["payment"] = p_dict
            else:
                order["payment"] = None

            # Fetch shipment
            cur.execute(
                """
                SELECT carrier, tracking_number, shipment_status, shipped_at, delivered_at
                FROM shipments
                WHERE order_id = %s
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (order["order_id"],)
            )
            shipment = cur.fetchone()
            if shipment:
                s_dict = dict(shipment)
                s_dict["shipped_at"] = s_dict["shipped_at"].isoformat() if s_dict.get("shipped_at") else None
                s_dict["delivered_at"] = s_dict["delivered_at"].isoformat() if s_dict.get("delivered_at") else None
                order["shipment"] = s_dict
            else:
                order["shipment"] = None

            # Fetch return status if any
            cur.execute(
                """
                SELECT return_status
                FROM returns
                WHERE order_id = %s
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (order["order_id"],)
            )
            ret = cur.fetchone()
            order["return_status"] = ret["return_status"] if ret else None

            # Fetch refund status if any
            cur.execute(
                """
                SELECT refund_status
                FROM refunds
                WHERE order_id = %s
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (order["order_id"],)
            )
            ref = cur.fetchone()
            order["refund_status"] = ref["refund_status"] if ref else None

            return order

    def cancel_order_atomic(self, order_id: str) -> None:
        """Update order status to CANCELLED in the current database transaction."""
        with self.cursor() as cur:
            cur.execute(
                """
                UPDATE orders
                SET order_status = 'CANCELLED',
                    cancelled_at = now(),
                    updated_at = now()
                WHERE order_id = %s;
                """,
                (order_id,)
            )
