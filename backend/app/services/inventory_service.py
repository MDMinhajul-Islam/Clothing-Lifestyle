"""Inventory and Store Domain Service."""

from typing import Dict, List, Optional
import psycopg2.extensions
from backend.app.schemas.inventory import (
    CheckInventoryInput,
    CheckInventoryOutput,
    VariantInventoryResult,
    StoreStockItem,
    FindStoresInput,
    FindStoresOutput,
    StoreItem,
)
from backend.app.repositories.inventory_repo import InventoryRepository
from backend.app.repositories.store_repo import StoreRepository
from backend.app.rules.inventory import InventoryRules
from backend.app.utils.geo import haversine_distance_miles


class InventoryService:
    """Domain service managing inventory lookups and store searches."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.inv_repo = InventoryRepository(conn)
        self.store_repo = StoreRepository(conn)

    def check_inventory(self, input_data: CheckInventoryInput) -> CheckInventoryOutput:
        if not (input_data.product_id or input_data.variant_id):
            raise ValueError("Either product_id or variant_id must be provided to check inventory.")

        rows = self.inv_repo.get_inventory(
            product_id=input_data.product_id,
            variant_id=input_data.variant_id,
            store_id=input_data.store_id,
            size=input_data.size,
            color=input_data.color
        )

        variants_map: Dict[str, Dict] = {}
        total_network = 0

        for r in rows:
            v_id = r["variant_id"]
            if v_id not in variants_map:
                variants_map[v_id] = {
                    "variant_id": v_id,
                    "size_name": r["size_name"],
                    "color_name": r["color_name"],
                    "total_available_in_network": 0,
                    "stores": []
                }

            avail = r["quantity_available"]
            variants_map[v_id]["total_available_in_network"] += avail
            total_network += avail

            variants_map[v_id]["stores"].append(
                StoreStockItem(
                    store_id=r["store_id"],
                    store_name=r["store_name"],
                    city=r["city"],
                    state=r["state"],
                    quantity_on_hand=r["quantity_on_hand"],
                    quantity_reserved=r["quantity_reserved"],
                    quantity_available=avail,
                    availability_status=r["availability_status"]
                )
            )

        overall_status = "IN_STOCK" if total_network > 10 else ("LOW_STOCK" if total_network > 0 else "OUT_OF_STOCK")

        variant_results = [
            VariantInventoryResult(**v_data)
            for v_data in variants_map.values()
        ]

        return CheckInventoryOutput(
            product_id=input_data.product_id,
            total_network_available=total_network,
            overall_status=overall_status,
            matching_variants=variant_results
        )

    def find_stores(self, input_data: FindStoresInput) -> FindStoresOutput:
        if input_data.latitude is not None and input_data.longitude is not None:
            # Fetch all stores and rank by Haversine distance
            all_stores = self.store_repo.get_all_stores()
            for s in all_stores:
                if s.get("latitude") and s.get("longitude"):
                    s["distance_miles"] = haversine_distance_miles(
                        input_data.latitude,
                        input_data.longitude,
                        s["latitude"],
                        s["longitude"]
                    )
                else:
                    s["distance_miles"] = None

            # Filter by city or state if also provided
            filtered = all_stores
            if input_data.city:
                filtered = [s for s in filtered if input_data.city.lower() in s["city"].lower()]
            if input_data.state:
                filtered = [s for s in filtered if input_data.state.lower() in s["state"].lower()]

            sorted_stores = sorted(
                filtered,
                key=lambda x: (x["distance_miles"] is None, x["distance_miles"] or 999999)
            )[:input_data.limit]

            return FindStoresOutput(
                total_matching=len(sorted_stores),
                stores=[StoreItem(**s) for s in sorted_stores]
            )
        else:
            stores = self.store_repo.find_stores(
                city=input_data.city,
                state=input_data.state,
                postal_code=input_data.postal_code,
                limit=input_data.limit
            )
            return FindStoresOutput(
                total_matching=len(stores),
                stores=[StoreItem(**s) for s in stores]
            )

