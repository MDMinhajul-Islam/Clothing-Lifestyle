"""Public read-only catalogue browsing service."""

import re
from typing import Optional
import psycopg2.extensions

from backend.app.repositories.catalogue_repo import CatalogueRepository
from backend.app.schemas.catalogue import SearchProductsInput
from backend.app.schemas.public_catalogue import CatalogueFacets, PublicProduct, PublicProductList, StyledEditResponse
from backend.app.services.catalogue_service import CatalogueService


class PublicCatalogueService:
    def __init__(self, conn: psycopg2.extensions.connection, repo: Optional[CatalogueRepository] = None,
                 embedding_client=None):
        self.repo = repo or CatalogueRepository(conn)
        self.conn = conn
        if embedding_client is not None:
            self.embedding_client = embedding_client
        elif repo is None:
            from backend.app.rag.embeddings import get_embedding_client
            self.embedding_client = get_embedding_client()
        else:
            self.embedding_client = None

    def products(self, *, query=None, category=None, department=None, color=None, min_price=None, max_price=None, sort="featured", limit=24, offset=0, available_only=False):
        raw_query = query
        if max_price is None and raw_query:
            price_match = re.search(r"(?:under|below|max)\s*\$?\s*(\d+(?:\.\d+)?)", raw_query, re.I)
            if price_match:
                max_price = float(price_match.group(1))
                raw_query = re.sub(r"(?:under|below|max)\s*\$?\s*\d+(?:\.\d+)?", "", raw_query, flags=re.I).strip() or None
        parsed = CatalogueService._extract_facets(SearchProductsInput(
            query=raw_query, category=category, department=department, color=color,
            min_price=min_price, max_price=max_price, limit=min(limit, 50)))
        semantic_vector = None
        if raw_query and self.embedding_client:
            semantic_vector = self.embedding_client.embed([raw_query])[0]
        total, rows = self.repo.list_public_products(query=parsed.query, category=category,
            department=parsed.department, color=parsed.color, min_price=parsed.min_price,
            max_price=parsed.max_price, product_type=parsed.product_type, material=parsed.material,
            brand=parsed.brand, occasion=parsed.occasion, semantic_vector=semantic_vector, sort=sort, limit=limit,
            offset=offset, available_only=available_only)
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
