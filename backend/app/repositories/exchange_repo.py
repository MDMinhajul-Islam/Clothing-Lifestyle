"""Exchange repository for validating replacement items and inventory."""

from typing import Any, Dict, List, Optional
from backend.app.repositories.base import BaseRepository


class ExchangeRepository(BaseRepository):
    """Data access methods for checking exchange replacement items."""

    def get_order_item_details(self, order_item_id: str) -> Optional[Dict[str, Any]]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT
                    oi.order_item_id,
                    oi.order_id,
                    o.order_number,
                    o.order_status,
                    oi.product_id,
                    oi.variant_id,
                    oi.product_name_snapshot as product_name,
                    oi.size_snapshot as size,
                    oi.color_snapshot as color,
                    oi.quantity,
                    oi.unit_price,
                    oi.line_total
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                WHERE oi.order_item_id = %s;
                """,
                (order_item_id.strip(),)
            )
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["unit_price"] = float(res["unit_price"])
            res["line_total"] = float(res["line_total"])
            return res

    def find_replacement_variant(
        self,
        product_id: str,
        size_name: Optional[str] = None,
        color_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Find matching variant for the same product with target size/color."""
        where_clauses = ["product_id = %s"]
        params: List[Any] = [product_id]

        if size_name and size_name.strip():
            where_clauses.append("size_name ILIKE %s")
            params.append(size_name.strip())

        if color_name and color_name.strip():
            where_clauses.append("color_name ILIKE %s")
            params.append(color_name.strip())

        sql = f"""
            SELECT variant_id, product_id, sku, size_name, color_name, (public_availability_state = 'IN_STOCK') as in_stock
            FROM product_variants
            WHERE {" AND ".join(where_clauses)}
            LIMIT 1;
        """
        with self.cursor() as cur:
            cur.execute(sql, tuple(params))
            row = cur.fetchone()
            return dict(row) if row else None
