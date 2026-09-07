"""Customer repository for secure shopper profile lookups."""

from typing import Any, Dict, List, Optional
from backend.app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository):
    """Data access methods for customer profiles and addresses."""

    def get_customer(
        self,
        customer_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Look up customer by exact identifier."""
        if not (customer_id or email or phone):
            return None

        where_clauses = []
        params: List[Any] = []

        if customer_id:
            where_clauses.append("customer_id = %s")
            params.append(customer_id.strip())
        elif email:
            where_clauses.append("LOWER(email) = LOWER(%s)")
            params.append(email.strip())
        elif phone:
            where_clauses.append("phone = %s")
            params.append(phone.strip())

        sql = f"""
            SELECT
                customer_id,
                first_name,
                last_name,
                email,
                phone,
                city,
                state,
                preferred_language,
                preferred_currency,
                account_status
            FROM customers
            WHERE {" OR ".join(where_clauses)}
            LIMIT 1;
        """
        with self.cursor() as cur:
            cur.execute(sql, tuple(params))
            customer = cur.fetchone()
            if not customer:
                return None

            customer = dict(customer)
            customer["customer_id"] = str(customer["customer_id"])

            # Fetch addresses
            cur.execute(
                """
                SELECT
                    address_id,
                    address_type,
                    recipient_name,
                    address_line_1,
                    city,
                    state,
                    postal_code,
                    is_default_shipping
                FROM customer_addresses
                WHERE customer_id = %s
                ORDER BY is_default_shipping DESC, created_at ASC;
                """,
                (customer["customer_id"],)
            )
            addresses = [dict(a) for a in cur.fetchall()]
            for a in addresses:
                a["address_id"] = str(a["address_id"])
            customer["addresses"] = addresses

            return customer

