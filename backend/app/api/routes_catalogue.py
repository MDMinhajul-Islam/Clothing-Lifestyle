"""Public-safe, read-only catalogue endpoints."""

from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg2.extensions

from backend.app.api.deps import get_db
from backend.app.schemas.public_catalogue import CatalogueFacets, PublicProduct, PublicProductList, StyledEditResponse
from backend.app.services.public_catalogue_service import PublicCatalogueService

router = APIRouter(prefix="/v1/catalogue", tags=["Public Catalogue"])


def get_public_catalogue(conn: psycopg2.extensions.connection = Depends(get_db)) -> PublicCatalogueService:
    return PublicCatalogueService(conn)


@router.get("/products", response_model=PublicProductList)
def list_products(q: Optional[str] = None, category: Optional[str] = None, department: Optional[str] = None, color: Optional[str] = None, min_price: Optional[float] = Query(None, ge=0), max_price: Optional[float] = Query(None, ge=0), sort: Literal["featured", "price_low_high", "price_high_low", "newest"] = "featured", limit: int = Query(24, ge=1, le=60), offset: int = Query(0, ge=0), available_only: bool = False, service: PublicCatalogueService = Depends(get_public_catalogue)):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price must not exceed max_price")
    return service.products(query=q, category=category, department=department, color=color, min_price=min_price, max_price=max_price, sort=sort, limit=limit, offset=offset, available_only=available_only)


@router.get("/products/{product_id}", response_model=PublicProduct)
def get_product(product_id: str, service: PublicCatalogueService = Depends(get_public_catalogue)):
    product = service.product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/facets", response_model=CatalogueFacets)
def get_facets(service: PublicCatalogueService = Depends(get_public_catalogue)):
    return service.facets()


@router.get("/styled-edit", response_model=StyledEditResponse)
def get_styled_edit(limit: int = Query(8, ge=3, le=12), service: PublicCatalogueService = Depends(get_public_catalogue)):
    return service.styled_edit(limit)

