"""Refund repository for querying processed refunds."""

from typing import Any, Dict, List, Optional
from backend.app.repositories.base import BaseRepository


class RefundRepository(BaseRepository):
    """Data access methods for refund records."""

    def get_refunds(
        self,
        order_number: Optional[str] = None,
        return_id: Optional[str] = None,
        refund_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        where_clauses = []
        params: List[Any] = []

        if refund_id:
            where_clauses.append("r.refund_id = %s")
            params.append(refund_id.strip())
        elif return_id:
            where_clauses.append("r.return_id = %s")
            params.append(return_id.strip())
        elif order_number:
            where_clauses.append("o.order_number = %s")
            params.append(order_number.strip())
        else:
            return []

        sql = f"""
            SELECT
                r.refund_id,
                r.order_id,
                r.return_id,
                r.refund_status,
                r.refund_method,
                r.amount,
                r.currency,
                r.requested_at,
                r.processed_at,
                r.provider_reference
            FROM refunds r
            JOIN orders o ON r.order_id = o.order_id
            WHERE {" AND ".join(where_clauses)}
            ORDER BY r.requested_at DESC;
        """
        with self.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = [dict(row) for row in cur.fetchall()]
            for r in rows:
                r["amount"] = float(r["amount"])
                r["requested_at"] = r["requested_at"].isoformat() if r.get("requested_at") else None
                r["processed_at"] = r["processed_at"].isoformat() if r.get("processed_at") else None
            return rows
