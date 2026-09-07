"""Public read-only catalogue browsing service."""

import re
from typing import Optional
import psycopg2.extensions

from backend.app.repositories.catalogue_repo import CatalogueRepository
from backend.app.schemas.public_catalogue import CatalogueFacets, PublicProduct, PublicProductList, StyledEditResponse
from backend.app.services.catalogue_service import CatalogueService


class PublicCatalogueService:
    def __init__(self, conn: psycopg2.extensions.connection, repo: Optional[CatalogueRepository] = None):
        self.repo = repo or CatalogueRepository(conn)

    def products(self, *, query=None, category=None, department=None, color=None, min_price=None, max_price=None, sort="featured", limit=24, offset=0, available_only=False):
        raw_query = query
        if max_price is None and raw_query:
            price_match = re.search(r"(?:under|below|max)\s*\$?\s*(\d+(?:\.\d+)?)", raw_query, re.I)
            if price_match:
                max_price = float(price_match.group(1))
                raw_query = re.sub(r"(?:under|below|max)\s*\$?\s*\d+(?:\.\d+)?", "", raw_query, flags=re.I).strip() or None
        query, color = CatalogueService._normalize_search(raw_query, color)
        total, rows = self.repo.list_public_products(query=query, category=category, department=department, color=color, min_price=min_price, max_price=max_price, sort=sort, limit=limit, offset=offset, available_only=available_only)
        items = [PublicProduct(**row) for row in rows]
        return PublicProductList(items=items, total=total, limit=limit, offset=offset, has_more=offset + len(items) < total)

    def product(self, product_id: str) -> Optional[PublicProduct]:
        row = self.repo.get_public_product(product_id)
        return PublicProduct(**row) if row else None

    def facets(self) -> CatalogueFacets:
        return CatalogueFacets(**self.repo.get_public_facets())

    def styled_edit(self, limit: int = 8) -> StyledEditResponse:
        rows = self.repo.get_styled_edit(limit)
        return StyledEditResponse(items=[PublicProduct(**row) for row in rows])
