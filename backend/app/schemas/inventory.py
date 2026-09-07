"""Pydantic schemas for inventory check and store search tools."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CheckInventoryInput(BaseModel):
    product_id: Optional[str] = Field(None, description="Zara product ID (e.g. 'zara-us:00029400')")
    variant_id: Optional[str] = Field(None, description="Specific Zara variant SKU ID")
    store_id: Optional[str] = Field(None, description="Filter for a specific store ID")
    size: Optional[str] = Field(None, description="Filter variant by size (e.g. 'M', 'L')")
    color: Optional[str] = Field(None, description="Filter variant by color name")


class StoreStockItem(BaseModel):
    store_id: str
    store_name: str
    city: str
    state: str
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    availability_status: str


class VariantInventoryResult(BaseModel):
    variant_id: str
    size_name: str
    color_name: str
    total_available_in_network: int
    stores: List[StoreStockItem]


class CheckInventoryOutput(BaseModel):
    product_id: Optional[str] = None
    total_network_available: int
    overall_status: str
    matching_variants: List[VariantInventoryResult]


class FindStoresInput(BaseModel):
    city: Optional[str] = Field(None, description="City name filter")
    state: Optional[str] = Field(None, description="US State filter (e.g. 'CA', 'NY', 'IL')")
    postal_code: Optional[str] = Field(None, description="ZIP code filter")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude for distance calculation")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude for distance calculation")
    limit: int = Field(10, ge=1, le=30, description="Max stores to return")


class StoreItem(BaseModel):
    store_id: str
    store_code: str
    store_name: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    phone: Optional[str] = None
    distance_miles: Optional[float] = None
    status: str
    is_synthetic: bool = True


class FindStoresOutput(BaseModel):
    total_matching: int
    stores: List[StoreItem]

