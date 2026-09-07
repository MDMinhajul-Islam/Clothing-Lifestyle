"""Catalogue Domain Service."""

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


class CatalogueService:
    """Domain service managing catalogue queries, faceted search, and comparisons."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.repo = CatalogueRepository(conn)

    def search_products(self, input_data: SearchProductsInput) -> SearchProductsOutput:
        total, rows = self.repo.search_products(
            query=input_data.query,
            department=input_data.department,
            category_id=input_data.category_id,
            min_price=input_data.min_price,
            max_price=input_data.max_price,
            color=input_data.color,
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

