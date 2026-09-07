"""Pydantic schemas for catalogue tools (search, details, compare)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SearchProductsInput(BaseModel):
    query: Optional[str] = Field(None, description="Free-text search query (e.g. 'linen shirt', 'black dress')")
    department: Optional[str] = Field(None, description="Department filter: WOMAN, MAN, or KIDS")
    category_id: Optional[str] = Field(None, description="Zara category identifier")
    min_price: Optional[float] = Field(None, ge=0.0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0.0, description="Maximum price filter")
    color: Optional[str] = Field(None, description="Color name filter (e.g. 'Black', 'Ecru')")
    size: Optional[str] = Field(None, description="Size filter (e.g. 'M', 'L', 'S')")
    on_sale: Optional[bool] = Field(None, description="Filter for products on sale")
    limit: int = Field(20, ge=1, le=50, description="Number of results to return (max 50)")


class ProductCard(BaseModel):
    product_id: str
    name: str
    department: str
    price: float
    currency: str
    is_on_sale: bool
    original_price: Optional[float] = None
    colors: List[str] = Field(default_factory=list)
    sizes: List[str] = Field(default_factory=list)
    primary_image_url: Optional[str] = None


class SearchProductsOutput(BaseModel):
    total_matching: int
    returned_count: int
    products: List[ProductCard]


class GetProductDetailsInput(BaseModel):
    product_id: str = Field(..., description="Zara canonical product ID (e.g. 'zara-us:00029400')")


class VariantDetail(BaseModel):
    variant_id: str
    sku: Optional[str] = None
    size_name: Optional[str] = None
    color_name: Optional[str] = None
    in_stock: bool = True
    availability_state: str = "IN_STOCK"


class ColorDetail(BaseModel):
    color_id: str
    color_name: Optional[str] = None
    color_code: Optional[str] = None
    color_reference: Optional[str] = None
    color_specific_url: Optional[str] = None


class ImageDetail(BaseModel):
    image_id: str
    image_url: str
    image_role: Optional[str] = None
    alt_text: Optional[str] = None


class CategoryDetail(BaseModel):
    category_id: str
    name: str
    department: Optional[str] = None


class ProductDetailsOutput(BaseModel):
    product_id: str
    name: str
    description: Optional[str] = None
    materials_care: Optional[str] = None
    department: str
    price: float
    currency: str
    is_on_sale: bool
    original_price: Optional[float] = None
    variants: List[VariantDetail] = Field(default_factory=list)
    colors: List[ColorDetail] = Field(default_factory=list)
    images: List[ImageDetail] = Field(default_factory=list)
    categories: List[CategoryDetail] = Field(default_factory=list)


class CompareProductsInput(BaseModel):
    product_ids: List[str] = Field(..., min_length=2, max_length=4, description="List of 2 to 4 product IDs to compare")


class ProductComparisonItem(BaseModel):
    product_id: str
    name: str
    department: str
    price: float
    currency: str
    is_on_sale: bool
    colors: List[str] = Field(default_factory=list)
    sizes: List[str] = Field(default_factory=list)
    materials_care: Optional[str] = None
    primary_image_url: Optional[str] = None


class CompareProductsOutput(BaseModel):
    compared_count: int
    products: List[ProductComparisonItem]
