"""Inventory repository for store availability and stock management."""

from typing import Any, Dict, List, Optional
from backend.app.repositories.base import BaseRepository


class InventoryRepository(BaseRepository):
    """Data access methods for inventory levels and store stock."""

    def get_inventory(
        self,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        store_id: Optional[str] = None,
        size: Optional[str] = None,
        color: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query inventory levels joined with variant and store information."""
        where_clauses = ["1=1"]
        params: List[Any] = []

        if variant_id:
            where_clauses.append("i.variant_id = %s")
            params.append(variant_id)
        elif product_id:
            where_clauses.append("v.product_id = %s")
            params.append(product_id)

        if store_id:
            where_clauses.append("i.store_id = %s")
            params.append(store_id)

        if size and size.strip():
            where_clauses.append("v.size_name ILIKE %s")
            params.append(size.strip())

        if color and color.strip():
            where_clauses.append("v.color_name ILIKE %s")
            params.append(color.strip())

        sql = f"""
            SELECT
                i.inventory_id,
                i.store_id,
                s.store_name,
                s.city,
                s.state,
                i.variant_id,
                v.product_id,
                v.size_name,
                v.color_name,
                i.quantity_on_hand,
                i.quantity_reserved,
                i.quantity_available,
                i.availability_status
            FROM inventory_levels i
            JOIN stores s ON i.store_id = s.store_id
            JOIN product_variants v ON i.variant_id = v.variant_id
            WHERE {" AND ".join(where_clauses)}
            ORDER BY s.state ASC, s.city ASC, v.size_name ASC;
        """
        with self.cursor() as cur:
            cur.execute(sql, tuple(params))
            return [dict(r) for r in cur.fetchall()]

    def release_reserved_stock_for_order(self, order_id: str) -> int:
        """Release any reserved inventory attached to an order's items if store-fulfilled."""
        with self.cursor() as cur:
            # Check if order was assigned to a store
            cur.execute("SELECT store_id FROM orders WHERE order_id = %s;", (order_id,))
            row = cur.fetchone()
            if not row or not row["store_id"]:
                return 0
            
            store_id = row["store_id"]
            # Fetch ordered line items
            cur.execute("SELECT variant_id, quantity FROM order_items WHERE order_id = %s;", (order_id,))
            items = cur.fetchall()
            
            released_count = 0
            for item in items:
                v_id = item["variant_id"]
                qty = item["quantity"]
                cur.execute(
                    """
                    UPDATE inventory_levels
                    SET quantity_reserved = GREATEST(0, quantity_reserved - %s),
                        availability_status = CASE
                            WHEN (quantity_on_hand - GREATEST(0, quantity_reserved - %s)) <= 0 THEN 'OUT_OF_STOCK'
                            WHEN (quantity_on_hand - GREATEST(0, quantity_reserved - %s)) <= 5 THEN 'LOW_STOCK'
                            ELSE 'IN_STOCK'
                        END,
                        last_updated_at = now()
                    WHERE store_id = %s AND variant_id = %s;
                    """,
                    (qty, qty, qty, store_id, v_id)
                )
                released_count += 1
            return released_count
