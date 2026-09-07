"""Pydantic schemas for customer lookup tools."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GetCustomerInput(BaseModel):
    customer_id: Optional[str] = Field(None, description="Customer UUID")
    email: Optional[str] = Field(None, description="Customer email address")
    phone: Optional[str] = Field(None, description="Customer phone number")


class CustomerAddressItem(BaseModel):
    address_id: str
    address_type: str
    recipient_name: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    is_default_shipping: bool


class CustomerProfileOutput(BaseModel):
    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    preferred_language: str
    preferred_currency: str
    account_status: str
    addresses: List[CustomerAddressItem] = Field(default_factory=list)

