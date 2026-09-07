"""Audit log repository for Tool Gateway executions."""

import json
from typing import Any, Dict, Optional
from backend.app.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    """Persistence for Tool Gateway execution logs."""

    def log_tool_execution(
        self,
        tool_name: str,
        request_id: str,
        request_summary: Dict[str, Any],
        result_status: str,
        duration_ms: int,
        customer_id: Optional[str] = None,
        order_id: Optional[str] = None,
        error_code: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> None:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tool_audit_log (
                    tool_name,
                    request_id,
                    customer_id,
                    order_id,
                    request_summary,
                    result_status,
                    error_code,
                    idempotency_key,
                    duration_ms
                ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s);
                """,
                (
                    tool_name,
                    request_id,
                    customer_id,
                    order_id,
                    json.dumps(request_summary),
                    result_status,
                    error_code,
                    idempotency_key,
                    duration_ms
                )
            )
