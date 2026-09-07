"""Deterministic Exchange Availability Rules."""

from typing import Dict, Any, List, Optional, Tuple


class ExchangeRules:
    """Business rules governing variant exchanges and replacements."""

    @classmethod
    def evaluate_exchange_eligibility(
        cls,
        order_item: Dict[str, Any],
        is_return_eligible: bool,
        replacement_variant: Optional[Dict[str, Any]],
        available_stock: int,
        requested_qty: int = 1
    ) -> Tuple[bool, str]:
        """Evaluate if an item can be exchanged for a specific replacement variant."""
        if not is_return_eligible:
            return False, "Original order item is not eligible for return or exchange."

        if not replacement_variant:
            return False, "Requested replacement variant (size/color) does not exist in the catalogue."

        if available_stock < requested_qty:
            return False, f"Replacement variant is out of stock (available: {available_stock}, requested: {requested_qty})."

        return True, f"Exchange available. {available_stock} units in stock."

