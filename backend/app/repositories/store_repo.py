"""Store repository for Zara demo retail locations."""

from typing import Any, Dict, List, Optional
from backend.app.repositories.base import BaseRepository


class StoreRepository(BaseRepository):
    """Data access methods for demo store locations."""

    def find_stores(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        where_clauses = ["1=1"]
        params: List[Any] = []

        if city and city.strip():
            where_clauses.append("city ILIKE %s")
            params.append(f"%{city.strip()}%")

        if state and state.strip():
            where_clauses.append("state ILIKE %s")
            params.append(state.strip())

        if postal_code and postal_code.strip():
            where_clauses.append("postal_code ILIKE %s")
            params.append(f"{postal_code.strip()}%")

        sql = f"""
            SELECT
                store_id,
                store_code,
                store_name,
                address_line_1,
                city,
                state,
                postal_code,
                phone,
                latitude,
                longitude,
                status,
                is_synthetic
            FROM stores
            WHERE {" AND ".join(where_clauses)}
            ORDER BY state ASC, city ASC
            LIMIT %s;
        """
        params.append(limit)
        with self.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                r["latitude"] = float(r["latitude"]) if r.get("latitude") else None
                r["longitude"] = float(r["longitude"]) if r.get("longitude") else None
            return rows

    def get_all_stores(self) -> List[Dict[str, Any]]:
        """Fetch all stores for geospatial distance calculation."""
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT
                    store_id,
                    store_code,
                    store_name,
                    address_line_1,
                    city,
                    state,
                    postal_code,
                    phone,
                    latitude,
                    longitude,
                    status,
                    is_synthetic
                FROM stores
                WHERE status = 'OPEN';
                """
            )
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                r["latitude"] = float(r["latitude"]) if r.get("latitude") else None
                r["longitude"] = float(r["longitude"]) if r.get("longitude") else None
            return rows
