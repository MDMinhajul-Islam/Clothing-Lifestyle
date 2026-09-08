"""Catalogue repository for Zara products, variants, colors, and images."""

from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
from re import escape as re_escape
from backend.app.repositories.base import BaseRepository


class CatalogueRepository(BaseRepository):
    """Data access methods for products, variants, colors, and images."""

    def search_products(
        self,
        query: Optional[str] = None,
        semantic_vector: Optional[List[float]] = None,
        department: Optional[str] = None,
        category_id: Optional[str] = None,
        category: Optional[str] = None,
        product_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        color: Optional[str] = None,
        size: Optional[str] = None,
        material: Optional[str] = None,
        brand: Optional[str] = None,
        occasion: Optional[str] = None,
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

        if category and category.strip():
            where_clauses.append("EXISTS (SELECT 1 FROM product_categories pc JOIN categories cat USING(category_id) WHERE pc.product_id=p.product_id AND (cat.name ILIKE %s OR cat.slug ILIKE %s))")
            params.extend([f"%{category.strip()}%", f"%{category.strip()}%"])

        if product_type and product_type.strip():
            product_pattern = rf"\m{product_type.strip()}(?:es|s)?\M"
            aliases = {
                "dress": r"\m(dress(?:es)?|gown(?:s)?)\M",
                "shirt": r"\m(shirt(?:s)?|blouse(?:s)?)\M",
                "jeans": r"\mjeans?\M",
                "pants": r"\m(pants?|trousers?|slacks)\M",
                "shoes": r"\m(shoes?|sneakers?|trainers?|loafers?)\M",
                "top": r"\m(tops?|tees?|t-shirts?)\M",
            }
            product_pattern = aliases.get(product_type.strip().casefold(), product_pattern)
            where_clauses.append("p.exact_product_name ~* %s")
            params.append(product_pattern)
            if product_type.strip().casefold() == "dress":
                where_clauses.append("p.exact_product_name !~* '\\mdress shoes?\\M'")

        if min_price is not None:
            where_clauses.append("p.current_price >= %s")
            params.append(Decimal(str(min_price)))

        if max_price is not None:
            where_clauses.append("p.current_price <= %s")
            params.append(Decimal(str(max_price)))

        if color and color.strip():
            where_clauses.append("EXISTS (SELECT 1 FROM product_colors col WHERE col.product_id = p.product_id AND col.color_name ~* %s)")
            params.append(rf"\m{re_escape(color.strip())}\M")

        if size and size.strip():
            where_clauses.append("EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id = p.product_id AND v.size_name ILIKE %s)")
            params.append(f"%{size.strip()}%")

        if material and material.strip():
            where_clauses.append("(COALESCE(p.material_text,'') ILIKE %s OR COALESCE(p.composition_text,'') ILIKE %s OR p.exact_product_name ILIKE %s)")
            params.extend([f"%{material.strip()}%"] * 3)

        if brand and brand.strip():
            where_clauses.append("p.brand ILIKE %s")
            params.append(brand.strip())

        if occasion and occasion.strip():
            occasion_pattern = re_escape(occasion.strip()).replace(r"\ ", r"\s+")
            pattern = rf"\m{occasion_pattern}\M"
            where_clauses.append("""(p.exact_product_name ~* %s OR COALESCE(p.short_description,'') ~* %s
                OR COALESCE(p.long_description,'') ~* %s OR EXISTS (SELECT 1 FROM product_categories pc
                JOIN categories cat USING(category_id) WHERE pc.product_id=p.product_id
                AND (cat.name ~* %s OR cat.slug ~* %s)))""")
            params.extend([pattern] * 5)

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
            embedding_join = ""
            if semantic_vector:
                embedding_join = "LEFT JOIN product_embeddings pe ON pe.product_id=p.product_id AND pe.embedding_provider='local_sentence_transformers' AND pe.embedding_model='sentence-transformers/all-MiniLM-L6-v2' AND pe.embedding_version='v1' AND pe.embedding_dimension=384"
            order_parts = []
            if query and query.strip():
                order_parts.append("ts_rank(p.search_vector, websearch_to_tsquery('english', %s)) DESC")
            if semantic_vector:
                order_parts.append("pe.embedding <=> %s::vector")
            order_sql = ", ".join([*order_parts, "p.product_id ASC"])
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
                    ,CASE WHEN %s::text IS NOT NULL OR %s::text IS NOT NULL THEN (
                        SELECT jsonb_build_object(
                            'variant_id', v.variant_id, 'sku', v.sku, 'color', v.color_name,
                            'size', v.size_name, 'availability_state', v.public_availability_state,
                            'in_stock', v.public_availability_state='IN_STOCK', 'price', p.current_price,
                            'image_url', (SELECT i.source_image_url FROM product_images i
                                WHERE i.product_id=p.product_id AND
                                (i.variant_id=v.variant_id OR i.color_name ILIKE v.color_name)
                                ORDER BY (i.variant_id=v.variant_id) DESC,
                                    (i.image_role IN ('PRIMARY','COLOR_SPECIFIC')) DESC, i.display_order LIMIT 1))
                        FROM product_variants v WHERE v.product_id=p.product_id
                            AND (%s::text IS NULL OR v.color_name ILIKE %s)
                            AND (%s::text IS NULL OR v.size_name ILIKE %s)
                        ORDER BY (v.public_availability_state='IN_STOCK') DESC, v.variant_id LIMIT 1
                    ) END AS matched_variant
                FROM products p
                {embedding_join}
                WHERE {where_sql}
                ORDER BY {order_sql}
                LIMIT %s;
            """
            select_params = [
                color.strip() if color and color.strip() else None,
                size.strip() if size and size.strip() else None,
                color.strip() if color and color.strip() else None,
                f"%{color.strip()}%" if color and color.strip() else None,
                size.strip() if size and size.strip() else None,
                f"%{size.strip()}%" if size and size.strip() else None,
            ]
            select_params.extend(params)
            if query and query.strip():
                select_params.append(query.strip())
            if semantic_vector:
                import json
                select_params.append(json.dumps(semantic_vector))
            select_params.append(limit)

            cur.execute(select_sql, tuple(select_params))
            rows = [dict(r) for r in cur.fetchall()]

            # Format types
            for r in rows:
                r["price"] = float(r["price"])
                r["original_price"] = float(r["original_price"]) if r.get("original_price") else None
                r["colors"] = [c for c in r["colors"] if c]
                r["sizes"] = [s for s in r["sizes"] if s]
                if r.get("matched_variant") and r["matched_variant"].get("image_url"):
                    r["primary_image_url"] = r["matched_variant"]["image_url"]

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
        product_type: Optional[str] = None, size: Optional[str] = None,
        material: Optional[str] = None, brand: Optional[str] = None,
        occasion: Optional[str] = None,
        semantic_vector: Optional[List[float]] = None,
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
        if product_type:
            patterns = {
                "dress": r"\m(dress(?:es)?|gown(?:s)?)\M",
                "shirt": r"\m(shirt(?:s)?|blouse(?:s)?)\M",
                "jeans": r"\mjeans?\M",
                "pants": r"\m(pants?|trousers?|slacks)\M",
                "shoes": r"\m(shoes?|sneakers?|trainers?|loafers?)\M",
                "top": r"\m(tops?|tees?|t-shirts?)\M",
            }
            pattern = patterns.get(product_type, rf"\m{product_type}(?:s)?\M")
            where.append("p.exact_product_name ~* %s")
            params.append(pattern)
            if product_type == "dress": where.append("p.exact_product_name !~* '\\mdress shoes?\\M'")
        if color:
            where.append("EXISTS (SELECT 1 FROM product_colors c WHERE c.product_id = p.product_id AND c.color_name ~* %s)"); params.append(rf"\m{re_escape(color)}\M")
        if size:
            where.append("EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id=p.product_id AND v.size_name ILIKE %s)"); params.append(f"%{size}%")
        if material:
            where.append("(COALESCE(p.material_text,'') ILIKE %s OR COALESCE(p.composition_text,'') ILIKE %s OR p.exact_product_name ILIKE %s)"); params.extend([f"%{material}%"] * 3)
        if brand:
            where.append("p.brand ILIKE %s"); params.append(brand)
        if occasion:
            occasion_pattern = re_escape(occasion).replace(r"\ ", r"\s+")
            pattern = rf"\m{occasion_pattern}\M"
            where.append("""(p.exact_product_name ~* %s OR COALESCE(p.short_description,'') ~* %s
                OR COALESCE(p.long_description,'') ~* %s OR EXISTS (SELECT 1 FROM product_categories pc
                JOIN categories cat USING(category_id) WHERE pc.product_id=p.product_id
                AND (cat.name ~* %s OR cat.slug ~* %s)))""")
            params.extend([pattern] * 5)
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
        embedding_join = ""
        if semantic_vector:
            embedding_join = "LEFT JOIN product_embeddings pe ON pe.product_id=p.product_id AND pe.embedding_provider='local_sentence_transformers' AND pe.embedding_model='sentence-transformers/all-MiniLM-L6-v2' AND pe.embedding_version='v1' AND pe.embedding_dimension=384"
            order_sql = "pe.embedding <=> %s::vector, " + order_sql

        with self.cursor() as cur:
            cur.execute(f"SELECT count(*) AS cnt FROM products p WHERE {where_sql}", tuple(params))
            total = cur.fetchone()["cnt"]
            requested_color = color.strip() if color else None
            requested_size = size.strip() if size else None
            select_params = [requested_color, f"%{requested_color}%" if requested_color else None,
                requested_color, requested_size, requested_color,
                f"%{requested_color}%" if requested_color else None,
                requested_size, f"%{requested_size}%" if requested_size else None,
            ]
            select_params.extend(params)
            if semantic_vector:
                import json
                select_params.append(json.dumps(semantic_vector))
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
                    COALESCE((SELECT array_agg(i.source_image_url ORDER BY
                        (CASE WHEN %s::text IS NOT NULL AND i.color_name ILIKE %s THEN 1 ELSE 0 END) DESC,
                        (i.image_role IN ('PRIMARY','COLOR_SPECIFIC')) DESC, i.display_order)
                        FROM product_images i WHERE i.product_id = p.product_id), ARRAY[]::TEXT[]) AS image_urls,
                    EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id = p.product_id AND v.public_availability_state = 'IN_STOCK') AS available,
                    'catalogue' AS source,
                    CASE WHEN %s::text IS NOT NULL OR %s::text IS NOT NULL THEN (
                        SELECT jsonb_build_object('variant_id',v.variant_id,'sku',v.sku,'color',v.color_name,
                            'size',v.size_name,'availability_state',v.public_availability_state,
                            'in_stock',v.public_availability_state='IN_STOCK','price',p.current_price,
                            'image_url',(SELECT i.source_image_url FROM product_images i WHERE i.product_id=p.product_id
                                AND (i.variant_id=v.variant_id OR i.color_name ILIKE v.color_name)
                                ORDER BY (i.variant_id=v.variant_id) DESC,
                                    (i.image_role IN ('PRIMARY','COLOR_SPECIFIC')) DESC,i.display_order LIMIT 1))
                        FROM product_variants v WHERE v.product_id=p.product_id
                            AND (%s::text IS NULL OR v.color_name ILIKE %s)
                            AND (%s::text IS NULL OR v.size_name ILIKE %s)
                        ORDER BY (v.public_availability_state='IN_STOCK') DESC,v.variant_id LIMIT 1
                    ) END AS matched_variant
                FROM products p {embedding_join} WHERE {where_sql}
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
