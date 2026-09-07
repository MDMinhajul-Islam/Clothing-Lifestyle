"""Deterministic Order Cancellation Business Rules."""

from typing import Dict, Any, Tuple


class CancellationRules:
    """Business policies governing order cancellation eligibility."""

    CANCELLABLE_STATUSES = {"PENDING", "CONFIRMED", "PROCESSING"}
    NON_CANCELLABLE_STATUSES = {
        "SHIPPED": "Order has already been shipped and handed to carrier. Please initiate a return upon receipt.",
        "DELIVERED": "Order has already been delivered. Please use the return service.",
        "CANCELLED": "Order is already cancelled.",
        "RETURN_REQUESTED": "Order already has an active return request.",
        "PARTIALLY_RETURNED": "Order is partially returned and cannot be cancelled.",
        "RETURNED": "Order has already been returned.",
        "REFUNDED": "Order has already been refunded.",
    }

    @classmethod
    def evaluate_cancellation_eligibility(cls, order: Dict[str, Any]) -> Tuple[bool, str, str]:
        """Evaluate if an order is eligible for cancellation.
        
        Returns:
            (eligible: bool, reason: str, allowed_action: str)
        """
        status = order.get("order_status", "").upper()
        
        if status in cls.CANCELLABLE_STATUSES:
            return True, f"Order status is {status}. Eligible for cancellation.", "CANCEL_ORDER"
        
        reason = cls.NON_CANCELLABLE_STATUSES.get(
            status,
            f"Order status '{status}' is not eligible for cancellation."
        )
        allowed_action = "INITIATE_RETURN" if status == "DELIVERED" else "NONE"
        return False, reason, allowed_action

