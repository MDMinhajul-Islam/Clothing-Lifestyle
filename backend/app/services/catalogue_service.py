"""Catalogue Domain Service."""

import re
from typing import List, Optional
import psycopg2.extensions
from backend.app.schemas.catalogue import (
    SearchProductsInput,
    SearchProductsOutput,
    ProductCard,
    GetProductDetailsInput,
    ProductDetailsOutput,
    CompareProductsInput,
    CompareProductsOutput,
    ProductComparisonItem,
)
from backend.app.schemas.common import ErrorCode, ToolError
from backend.app.repositories.catalogue_repo import CatalogueRepository


SEARCH_FILLER = {
    "a", "an", "find", "for", "i", "looking", "me", "need", "please",
    "search", "show", "some", "under", "up", "to", "party", "evening",
    "occasion", "wear",
}
SEARCH_PLURALS = {
    "dresses": "dress", "shirts": "shirt", "jackets": "jacket",
    "tops": "top", "skirts": "skirt", "shoes": "shoe", "coats": "coat",
    "blazers": "blazer", "pants": "pant", "trousers": "trouser", "jeans": "jean",
}
SEARCH_COLORS = {
    "black", "white", "navy", "blue", "red", "green", "beige", "brown",
    "gray", "grey", "pink", "yellow", "orange", "purple",
}


class CatalogueService:
    """Domain service managing catalogue queries, faceted search, and comparisons."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.repo = CatalogueRepository(conn)

    def search_products(self, input_data: SearchProductsInput) -> SearchProductsOutput:
        query, color = self._normalize_search(input_data.query, input_data.color)
        total, rows = self.repo.search_products(
            query=query,
            department=input_data.department,
            category_id=input_data.category_id,
            min_price=input_data.min_price,
            max_price=input_data.max_price,
            color=color,
            size=input_data.size,
            on_sale=input_data.on_sale,
            limit=input_data.limit,
        )
        cards = [ProductCard(**r) for r in rows]
        return SearchProductsOutput(
            total_matching=total,
            returned_count=len(cards),
            products=cards
        )

    @staticmethod
    def _normalize_search(query: Optional[str], color: Optional[str]):
        """Separate authoritative facets from conversational catalogue text."""
        if not query or not query.strip():
            return query, color
        tokens = re.findall(r"[a-z]+|\d+(?:\.\d+)?", query.casefold())
        normalized_color = color.strip() if color and color.strip() else next(
            (token for token in tokens if token in SEARCH_COLORS), None
        )
        color_token = normalized_color.casefold() if normalized_color else None
        terms = [
            SEARCH_PLURALS.get(token, token)
            for token in tokens
            if token not in SEARCH_FILLER
            and token != color_token
            and not token.replace(".", "", 1).isdigit()
        ]
        return " ".join(terms) or None, normalized_color

    def get_product_details(self, input_data: GetProductDetailsInput) -> ProductDetailsOutput:
        prod = self.repo.get_product_details(input_data.product_id)
        if not prod:
            raise ValueError(f"Product '{input_data.product_id}' not found.")
        return ProductDetailsOutput(**prod)

    def compare_products(self, input_data: CompareProductsInput) -> CompareProductsOutput:
        products = self.repo.get_products_by_ids(input_data.product_ids)
        items = [ProductComparisonItem(**p) for p in products]
        return CompareProductsOutput(
            compared_count=len(items),
            products=items
        )

