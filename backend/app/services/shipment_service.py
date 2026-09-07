"""Shipment Domain Service."""

from typing import Optional
import psycopg2.extensions
from backend.app.schemas.order import (
    TrackOrderInput,
    TrackOrderOutput,
    ShipmentEventSummary,
)
from backend.app.repositories.shipment_repo import ShipmentRepository


class ShipmentService:
    """Domain service managing order shipment tracking and milestone events."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.repo = ShipmentRepository(conn)

    def track_order(self, input_data: TrackOrderInput) -> TrackOrderOutput:
        data = self.repo.get_order_tracking(input_data.order_number)
        if not data:
            raise ValueError(f"Order '{input_data.order_number}' not found.")

        events = [ShipmentEventSummary(**e) for e in data.get("events", [])]

        return TrackOrderOutput(
            order_number=data["order_number"],
            order_status=data["order_status"],
            carrier=data.get("carrier"),
            tracking_number=data.get("tracking_number"),
            shipment_status=data.get("shipment_status"),
            shipped_at=data.get("shipped_at"),
            estimated_delivery_at=data.get("estimated_delivery_at"),
            delivered_at=data.get("delivered_at"),
            events=events
        )
