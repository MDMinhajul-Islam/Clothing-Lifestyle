"""Shipment repository for order tracking and events."""

from typing import Any, Dict, List, Optional
from backend.app.repositories.base import BaseRepository


class ShipmentRepository(BaseRepository):
    """Data access methods for shipments and tracking events."""

    def get_order_tracking(self, order_number: str) -> Optional[Dict[str, Any]]:
        """Get shipment details and chronological events by order number."""
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT
                    o.order_number,
                    o.order_status,
                    s.shipment_id,
                    s.carrier,
                    s.tracking_number,
                    s.shipment_status,
                    s.shipped_at,
                    s.estimated_delivery_at,
                    s.delivered_at
                FROM orders o
                LEFT JOIN shipments s ON o.order_id = s.order_id
                WHERE o.order_number = %s
                LIMIT 1;
                """,
                (order_number.strip(),)
            )
            row = cur.fetchone()
            if not row:
                return None

            result = dict(row)
            result["shipped_at"] = result["shipped_at"].isoformat() if result.get("shipped_at") else None
            result["estimated_delivery_at"] = result["estimated_delivery_at"].isoformat() if result.get("estimated_delivery_at") else None
            result["delivered_at"] = result["delivered_at"].isoformat() if result.get("delivered_at") else None

            # Fetch chronological events if shipment exists
            events = []
            if result.get("shipment_id"):
                cur.execute(
                    """
                    SELECT event_type, description, location_text, occurred_at
                    FROM shipment_events
                    WHERE shipment_id = %s
                    ORDER BY occurred_at ASC;
                    """,
                    (result["shipment_id"],)
                )
                raw_events = cur.fetchall()
                for e in raw_events:
                    e_dict = dict(e)
                    e_dict["occurred_at"] = e_dict["occurred_at"].isoformat() if e_dict.get("occurred_at") else None
                    events.append(e_dict)

            result["events"] = events
            return result
