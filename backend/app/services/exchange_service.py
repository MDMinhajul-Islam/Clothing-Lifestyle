"""Exchange Domain Service."""

from typing import Any, Dict, Optional
import psycopg2.extensions
from backend.app.schemas.returns import (
    CheckExchangeAvailabilityInput,
    CheckExchangeAvailabilityOutput,
)
from backend.app.repositories.exchange_repo import ExchangeRepository
from backend.app.repositories.inventory_repo import InventoryRepository
from backend.app.repositories.return_repo import ReturnRepository
from backend.app.rules.returns import ReturnRules
from backend.app.rules.exchanges import ExchangeRules


class ExchangeService:
    """Domain service evaluating replacement item and stock availability."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
        self.exchange_repo = ExchangeRepository(conn)
        self.inv_repo = InventoryRepository(conn)
        self.return_repo = ReturnRepository(conn)

    def check_exchange_availability(
        self,
        input_data: CheckExchangeAvailabilityInput
    ) -> CheckExchangeAvailabilityOutput:
        # 1. Fetch original order item
        item = self.exchange_repo.get_order_item_details(input_data.order_item_id)
        if not item:
            raise ValueError(f"Order item '{input_data.order_item_id}' was not found.")

        # 2. Check return eligibility of the order
        return_context = self.return_repo.get_return_context_for_order(item["order_number"])
        order_eligible = False
        if return_context:
            eval_res = ReturnRules.evaluate_order_return_eligibility(
                order=return_context,
                items=return_context["items"]
            )
            # Find item in eval_res
            for i in eval_res["items"]:
                if i["order_item_id"] == input_data.order_item_id and i["eligible"]:
                    order_eligible = True
                    break

        # 3. Find replacement variant
        repl_variant = self.exchange_repo.find_replacement_variant(
            product_id=item["product_id"],
            size_name=input_data.replacement_size,
            color_name=input_data.replacement_color
        )

        # 4. Check inventory for replacement variant
        available_stock = 0
        stock_status = "OUT_OF_STOCK"
        if repl_variant:
            inv_rows = self.inv_repo.get_inventory(
                variant_id=repl_variant["variant_id"],
                store_id=input_data.store_id
            )
            available_stock = sum(r["quantity_available"] for r in inv_rows)
            stock_status = "IN_STOCK" if available_stock > 5 else ("LOW_STOCK" if available_stock > 0 else "OUT_OF_STOCK")

        # 5. Evaluate Exchange Rules
        eligible, reason = ExchangeRules.evaluate_exchange_eligibility(
            order_item=item,
            is_return_eligible=order_eligible,
            replacement_variant=repl_variant,
            available_stock=available_stock,
            requested_qty=1
        )

        return CheckExchangeAvailabilityOutput(
            eligible=eligible,
            reason=reason,
            original_item={
                "order_item_id": item["order_item_id"],
                "product_id": item["product_id"],
                "variant_id": item["variant_id"],
                "product_name": item["product_name"],
                "size": item["size"],
                "color": item["color"],
                "unit_price": item["unit_price"]
            },
            replacement_variant=repl_variant,
            quantity_available=available_stock,
            stock_status=stock_status
        )
