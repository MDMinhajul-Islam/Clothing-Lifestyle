"""Deterministic Return Eligibility Business Rules."""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple
from decimal import Decimal


class ReturnRules:
    """Business policies governing item returns, windows, and refund estimates."""

    RETURN_WINDOW_DAYS = 30
    ELIGIBLE_ORDER_STATUSES = {"DELIVERED", "PARTIALLY_RETURNED"}

    @classmethod
    def evaluate_order_return_eligibility(
        cls,
        order: Dict[str, Any],
        items: List[Dict[str, Any]],
        now: datetime | None = None
    ) -> Dict[str, Any]:
        """Evaluate return eligibility for an order and its items.
        
        Args:
            order: Order dict including order_status and shipped_at.
            items: List of line items with ordered quantity and previously returned quantities.
            now: Current timestamp (defaults to UTC now).
        """
        now = now or datetime.now(timezone.utc)
        status = order.get("order_status", "").upper()

        if status not in cls.ELIGIBLE_ORDER_STATUSES:
            return {
                "eligible": False,
                "order_status": status,
                "reason": f"Order status '{status}' is not eligible for return. Orders must be delivered.",
                "deadline": None,
                "days_remaining": 0,
                "items": []
            }

        shipped_at = order.get("shipped_at")
        if not shipped_at:
            return {
                "eligible": False,
                "order_status": status,
                "reason": "Shipment date is unavailable, so return eligibility cannot be verified automatically. Human support can review this order.",
                "deadline": None,
                "days_remaining": 0,
                "estimated_total_refund": 0.0,
                "items": []
            }

        if isinstance(shipped_at, str):
            shipped_at = datetime.fromisoformat(shipped_at.replace("Z", "+00:00"))

        if shipped_at.tzinfo is None:
            shipped_at = shipped_at.replace(tzinfo=timezone.utc)

        deadline = shipped_at + timedelta(days=cls.RETURN_WINDOW_DAYS)
        days_remaining = (deadline - now).days

        if now > deadline:
            return {
                "eligible": False,
                "order_status": status,
                "reason": f"Return window has expired ({cls.RETURN_WINDOW_DAYS} days from shipment on {shipped_at.strftime('%Y-%m-%d')}).",
                "deadline": deadline.isoformat(),
                "days_remaining": 0,
                "items": []
            }

        item_evaluations = []
        any_eligible = False
        total_estimated_refund = Decimal("0.00")

        for item in items:
            ordered_qty = item.get("quantity", 0)
            returned_qty = item.get("already_returned_quantity", 0)
            available_to_return = max(0, ordered_qty - returned_qty)
            
            unit_price = Decimal(str(item.get("unit_price", 0)))
            line_total = Decimal(str(item.get("line_total", 0)))
            # Effective price per unit after line discount
            effective_unit_price = (line_total / ordered_qty) if ordered_qty > 0 else unit_price

            is_item_eligible = available_to_return > 0
            if is_item_eligible:
                any_eligible = True
                est_refund = (effective_unit_price * available_to_return).quantize(Decimal("0.01"))
                total_estimated_refund += est_refund
            else:
                est_refund = Decimal("0.00")

            item_evaluations.append({
                "order_item_id": item.get("order_item_id"),
                "product_name": item.get("product_name_snapshot"),
                "size": item.get("size_snapshot"),
                "color": item.get("color_snapshot"),
                "ordered_quantity": ordered_qty,
                "already_returned_quantity": returned_qty,
                "available_to_return": available_to_return,
                "eligible": is_item_eligible,
                "reason": "Available for return" if is_item_eligible else "All units already returned",
                "effective_unit_price": float(effective_unit_price),
                "estimated_refundable_amount": float(est_refund)
            })

        return {
            "eligible": any_eligible,
            "order_status": status,
            "reason": "Backend state is within the 30-day shipment window; item condition, labels, market, and special restrictions must still be verified." if any_eligible else "No remaining returnable items",
            "deadline": deadline.isoformat(),
            "days_remaining": max(0, days_remaining),
            "estimated_total_refund": float(total_estimated_refund),
            "items": item_evaluations
        }

