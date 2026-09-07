"""Public, read-only catalogue response contracts."""

from typing import List, Optional
from pydantic import BaseModel, Field


class PublicProduct(BaseModel):
    product_id: str
    name: str
    department: str
    category: Optional[str] = None
    description: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    currency: str
    colors: List[str] = Field(default_factory=list)
    sizes: List[str] = Field(default_factory=list)
    image_urls: List[str] = Field(default_factory=list)
    available: bool
    is_on_sale: bool = False
    source: str = "catalogue"


class PublicProductList(BaseModel):
    items: List[PublicProduct]
    total: int
    limit: int
    offset: int
    has_more: bool


class CatalogueFacets(BaseModel):
    departments: List[str]
    categories: List[str]
    colors: List[str]
    price_min: float
    price_max: float
    total_products: int


class StyledEditResponse(BaseModel):
    items: List[PublicProduct]

