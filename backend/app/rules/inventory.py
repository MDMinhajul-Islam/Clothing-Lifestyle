"""Deterministic Inventory Stock and Status Rules."""

from typing import Tuple


class InventoryRules:
    """Business policies governing inventory calculations and stock classification."""

    LOW_STOCK_THRESHOLD = 5

    @classmethod
    def calculate_availability(cls, on_hand: int, reserved: int) -> Tuple[int, str]:
        """Compute quantity_available and stock status classification.
        
        Returns:
            (quantity_available: int, status: str)
        """
        available = max(0, on_hand - reserved)
        if available == 0:
            status = "OUT_OF_STOCK"
        elif available <= cls.LOW_STOCK_THRESHOLD:
            status = "LOW_STOCK"
        else:
            status = "IN_STOCK"
        return available, status

    @classmethod
    def can_fulfill(cls, on_hand: int, reserved: int, requested: int) -> bool:
        """Check if requested quantity can be fulfilled."""
        available, _ = cls.calculate_availability(on_hand, reserved)
        return available >= requested

