"""Customer Domain Service."""

from typing import Optional
import psycopg2.extensions
from backend.app.schemas.customer import (
    GetCustomerInput,
    CustomerProfileOutput,
    CustomerAddressItem,
)
from backend.app.repositories.customer_repo import CustomerRepository


class CustomerService:
    """Domain service managing shopper lookups and profile retrieval."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.repo = CustomerRepository(conn)

    def get_customer(self, input_data: GetCustomerInput) -> CustomerProfileOutput:
        if not (input_data.customer_id or input_data.email or input_data.phone):
            raise ValueError("Must provide customer_id, email, or phone for customer lookup.")

        cust = self.repo.get_customer(
            customer_id=input_data.customer_id,
            email=input_data.email,
            phone=input_data.phone
        )
        if not cust:
            raise ValueError("Customer not found matching the provided identifier.")

        addresses = [CustomerAddressItem(**a) for a in cust.get("addresses", [])]
        return CustomerProfileOutput(
            customer_id=cust["customer_id"],
            first_name=cust["first_name"],
            last_name=cust["last_name"],
            email=cust["email"],
            phone=cust.get("phone"),
            city=cust.get("city"),
            state=cust.get("state"),
            preferred_language=cust["preferred_language"],
            preferred_currency=cust["preferred_currency"],
            account_status=cust["account_status"],
            addresses=addresses
        )

