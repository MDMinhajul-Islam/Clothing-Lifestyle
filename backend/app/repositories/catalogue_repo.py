"""Catalogue repository for Zara products, variants, colors, and images."""

from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
from backend.app.repositories.base import BaseRepository


class CatalogueRepository(BaseRepository):
    """Data access methods for products, variants, colors, and images."""

    def search_products(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        category_id: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        color: Optional[str] = None,
        size: Optional[str] = None,
        on_sale: Optional[bool] = None,
        limit: int = 20
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Search products with full-text search and faceted filters."""
        where_clauses = ["1=1"]
        params: List[Any] = []

        if query and query.strip():
            where_clauses.append("p.search_vector @@ websearch_to_tsquery('english', %s)")
            params.append(query.strip())

        if department and department.strip():
            where_clauses.append("p.department ILIKE %s")
            params.append(department.strip())

        if category_id and category_id.strip():
            where_clauses.append("EXISTS (SELECT 1 FROM product_categories pc WHERE pc.product_id = p.product_id AND pc.category_id = %s)")
            params.append(category_id.strip())

        if min_price is not None:
            where_clauses.append("p.current_price >= %s")
            params.append(Decimal(str(min_price)))

        if max_price is not None:
            where_clauses.append("p.current_price <= %s")
            params.append(Decimal(str(max_price)))

        if color and color.strip():
            where_clauses.append("EXISTS (SELECT 1 FROM product_colors col WHERE col.product_id = p.product_id AND col.color_name ILIKE %s)")
            params.append(f"%{color.strip()}%")

        if size and size.strip():
            where_clauses.append("EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id = p.product_id AND v.size_name ILIKE %s)")
            params.append(f"%{size.strip()}%")

        if on_sale is not None:
            where_clauses.append("p.is_on_sale = %s")
            params.append(on_sale)

        where_sql = " AND ".join(where_clauses)

        # Count total matching query
        count_sql = f"SELECT count(*) as cnt FROM products p WHERE {where_sql};"
        with self.cursor() as cur:
            cur.execute(count_sql, tuple(params))
            total_matching = cur.fetchone()["cnt"]

            # Select products with aggregated colors, sizes, and primary image
            order_prefix = (
                "ts_rank(p.search_vector, websearch_to_tsquery('english', %s)) DESC, "
                if query and query.strip() else ""
            )
            select_sql = f"""
                SELECT
                    p.product_id,
                    p.exact_product_name as name,
                    p.department,
                    p.current_price as price,
                    p.currency as currency,
                    p.is_on_sale,
                    p.original_price as original_price,
                    COALESCE((
                        SELECT array_agg(DISTINCT c.color_name)
                        FROM product_colors c
                        WHERE c.product_id = p.product_id
                    ), ARRAY[]::TEXT[]) as colors,
                    COALESCE((
                        SELECT array_agg(DISTINCT v.size_name)
                        FROM product_variants v
                        WHERE v.product_id = p.product_id
                    ), ARRAY[]::TEXT[]) as sizes,
                    (
                        SELECT img.source_image_url
                        FROM product_images img
                        WHERE img.product_id = p.product_id
                        ORDER BY (img.image_role = 'PRIMARY') DESC, img.display_order ASC
                        LIMIT 1
                    ) as primary_image_url
                FROM products p
                WHERE {where_sql}
                ORDER BY {order_prefix}p.product_id ASC
                LIMIT %s;
            """
            select_params = list(params)
            if query and query.strip():
                select_params.append(query.strip())
            select_params.append(limit)

            cur.execute(select_sql, tuple(select_params))
            rows = [dict(r) for r in cur.fetchall()]

            # Format types
            for r in rows:
                r["price"] = float(r["price"])
                r["original_price"] = float(r["original_price"]) if r.get("original_price") else None
                r["colors"] = [c for c in r["colors"] if c]
                r["sizes"] = [s for s in r["sizes"] if s]

            return total_matching, rows

    def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full authoritative product hierarchy."""
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT
                    product_id,
                    exact_product_name as name,
                    COALESCE(long_description, short_description) as description,
                    COALESCE(care_information, material_text) as materials_care,
                    department,
                    current_price as price,
                    currency as currency,
                    is_on_sale,
                    original_price as original_price
                FROM products
                WHERE product_id = %s;
                """,
                (product_id,)
            )
            prod = cur.fetchone()
            if not prod:
                return None

            prod = dict(prod)
            prod["price"] = float(prod["price"])
            prod["original_price"] = float(prod["original_price"]) if prod.get("original_price") else None

            # Fetch variants
            cur.execute(
                """
                SELECT
                    variant_id,
                    sku,
                    size_name,
                    color_name,
                    public_availability_state as availability_state,
                    (public_availability_state = 'IN_STOCK') as in_stock
                FROM product_variants
                WHERE product_id = %s
                ORDER BY size_name ASC;
                """,
                (product_id,)
            )
            prod["variants"] = [dict(r) for r in cur.fetchall()]

            # Fetch colors
            cur.execute(
                """
                SELECT color_id, color_name, color_code, color_reference, color_specific_url
                FROM product_colors
                WHERE product_id = %s
                ORDER BY display_order ASC;
                """,
                (product_id,)
            )
            prod["colors"] = [dict(r) for r in cur.fetchall()]

            # Fetch images
            cur.execute(
                """
                SELECT
                    image_id,
                    source_image_url as image_url,
                    image_role,
                    alt_text
                FROM product_images
                WHERE product_id = %s
                ORDER BY (image_role = 'PRIMARY') DESC, display_order ASC;
                """,
                (product_id,)
            )
            prod["images"] = [dict(r) for r in cur.fetchall()]

            # Fetch categories
            cur.execute(
                """
                SELECT c.category_id, c.name, c.department
                FROM product_categories pc
                JOIN categories c ON pc.category_id = c.category_id
                WHERE pc.product_id = %s;
                """,
                (product_id,)
            )
            prod["categories"] = [dict(r) for r in cur.fetchall()]

            return prod

    def get_products_by_ids(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch multiple products for comparison."""
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT
                    p.product_id,
                    p.exact_product_name as name,
                    p.department,
                    p.current_price as price,
                    p.currency as currency,
                    p.is_on_sale,
                    COALESCE(p.care_information, p.material_text) as materials_care,
                    COALESCE((
                        SELECT array_agg(DISTINCT c.color_name)
                        FROM product_colors c
                        WHERE c.product_id = p.product_id
                    ), ARRAY[]::TEXT[]) as colors,
                    COALESCE((
                        SELECT array_agg(DISTINCT v.size_name)
                        FROM product_variants v
                        WHERE v.product_id = p.product_id
                    ), ARRAY[]::TEXT[]) as sizes,
                    (
                        SELECT img.source_image_url
                        FROM product_images img
                        WHERE img.product_id = p.product_id
                        ORDER BY (img.image_role = 'PRIMARY') DESC, img.display_order ASC
                        LIMIT 1
                    ) as primary_image_url
                FROM products p
                WHERE p.product_id = ANY(%s);
                """,
                (product_ids,)
            )
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                r["price"] = float(r["price"])
                r["colors"] = [c for c in r["colors"] if c]
                r["sizes"] = [s for s in r["sizes"] if s]
            return rows

    def list_public_products(
        self, query: Optional[str] = None, category: Optional[str] = None,
        department: Optional[str] = None, color: Optional[str] = None,
        min_price: Optional[float] = None, max_price: Optional[float] = None,
        sort: str = "featured", limit: int = 24, offset: int = 0,
        available_only: bool = False, product_id: Optional[str] = None,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """List lifecycle-active products through the public response allowlist."""
        where = ["p.lifecycle_status = 'ACTIVE'", "p.exact_product_name !~* '(magnetic board|towel|candle|candlestick)'"]
        params: List[Any] = []
        if product_id:
            where.append("p.product_id = %s"); params.append(product_id)
        if query:
            where.append("p.search_vector @@ websearch_to_tsquery('english', %s)"); params.append(query)
        if department:
            where.append("p.department ILIKE %s"); params.append(department)
        if category:
            where.append("EXISTS (SELECT 1 FROM product_categories pc JOIN categories cat ON cat.category_id = pc.category_id WHERE pc.product_id = p.product_id AND (cat.name ILIKE %s OR cat.slug ILIKE %s))")
            params.extend([f"%{category}%", f"%{category}%"])
        if color:
            where.append("EXISTS (SELECT 1 FROM product_colors c WHERE c.product_id = p.product_id AND c.color_name ILIKE %s)"); params.append(f"%{color}%")
        if min_price is not None:
            where.append("p.current_price >= %s"); params.append(Decimal(str(min_price)))
        if max_price is not None:
            where.append("p.current_price <= %s"); params.append(Decimal(str(max_price)))
        if available_only:
            where.append("EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id = p.product_id AND v.public_availability_state = 'IN_STOCK')")
        where_sql = " AND ".join(where)
        order_sql = {
            "price_low_high": "p.current_price ASC, p.product_id ASC",
            "price_high_low": "p.current_price DESC, p.product_id ASC",
            "newest": "p.first_seen_at DESC NULLS LAST, p.product_id ASC",
        }.get(sort, "p.is_on_sale DESC, p.last_seen_at DESC NULLS LAST, p.product_id ASC")
        if query:
            order_sql = "ts_rank(p.search_vector, websearch_to_tsquery('english', %s)) DESC, " + order_sql

        with self.cursor() as cur:
            cur.execute(f"SELECT count(*) AS cnt FROM products p WHERE {where_sql}", tuple(params))
            total = cur.fetchone()["cnt"]
            select_params = list(params)
            if query:
                select_params.append(query)
            select_params.extend([limit, offset])
            cur.execute(f"""
                SELECT p.product_id, p.exact_product_name AS name, p.department,
                    (SELECT cat.name FROM product_categories pc JOIN categories cat ON cat.category_id = pc.category_id WHERE pc.product_id = p.product_id ORDER BY cat.name LIMIT 1) AS category,
                    COALESCE(p.long_description, p.short_description) AS description,
                    p.current_price AS price, p.original_price, p.currency, p.is_on_sale,
                    COALESCE((SELECT array_agg(DISTINCT c.color_name) FROM product_colors c WHERE c.product_id = p.product_id AND c.color_name IS NOT NULL), ARRAY[]::TEXT[]) AS colors,
                    COALESCE((SELECT array_agg(DISTINCT v.size_name) FROM product_variants v WHERE v.product_id = p.product_id AND v.size_name IS NOT NULL), ARRAY[]::TEXT[]) AS sizes,
                    COALESCE((SELECT array_agg(i.source_image_url ORDER BY (i.image_role = 'PRIMARY') DESC, i.display_order) FROM product_images i WHERE i.product_id = p.product_id), ARRAY[]::TEXT[]) AS image_urls,
                    EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id = p.product_id AND v.public_availability_state = 'IN_STOCK') AS available,
                    'catalogue' AS source
                FROM products p WHERE {where_sql}
                ORDER BY {order_sql} LIMIT %s OFFSET %s
            """, tuple(select_params))
            return total, [self._format_public_product(dict(row)) for row in cur.fetchall()]

    def get_public_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        _, rows = self.list_public_products(product_id=product_id, limit=1)
        return rows[0] if rows else None

    def get_public_facets(self) -> Dict[str, Any]:
        """Return filter values derived only from active public products."""
        with self.cursor() as cur:
            cur.execute("""
                SELECT count(*) AS total_products, COALESCE(min(current_price), 0) AS price_min,
                    COALESCE(max(current_price), 0) AS price_max,
                    ARRAY(SELECT DISTINCT department FROM products WHERE lifecycle_status = 'ACTIVE' ORDER BY department) AS departments,
                    ARRAY(SELECT DISTINCT cat.name FROM categories cat JOIN product_categories pc ON pc.category_id = cat.category_id JOIN products p2 ON p2.product_id = pc.product_id WHERE p2.lifecycle_status = 'ACTIVE' ORDER BY cat.name) AS categories,
                    ARRAY(SELECT DISTINCT c.color_name FROM product_colors c JOIN products p3 ON p3.product_id = c.product_id WHERE p3.lifecycle_status = 'ACTIVE' AND c.color_name IS NOT NULL ORDER BY c.color_name) AS colors
                FROM products WHERE lifecycle_status = 'ACTIVE'
            """)
            row = dict(cur.fetchone())
            row["price_min"] = float(row["price_min"]); row["price_max"] = float(row["price_max"])
            return row

    def get_styled_edit(self, limit: int = 8) -> List[Dict[str, Any]]:
        """Select current image-backed fashion products for an editorial rail."""
        _, rows = self.list_public_products(available_only=True, sort="newest", limit=limit * 3)
        excluded = ("board", "towel", "candle", "home", "perfume", "parfum", "lipstick", "eyeliner", "edp")
        return [row for row in rows if row["image_urls"] and not any(term in row["name"].casefold() for term in excluded)][:limit]

    @staticmethod
    def _format_public_product(row: Dict[str, Any]) -> Dict[str, Any]:
        row["price"] = float(row["price"])
        row["original_price"] = float(row["original_price"]) if row.get("original_price") is not None else None
        row["colors"] = [value for value in row.get("colors", []) if value]
        row["sizes"] = [value for value in row.get("sizes", []) if value]
        row["image_urls"] = [value for value in row.get("image_urls", []) if value]
        return row
