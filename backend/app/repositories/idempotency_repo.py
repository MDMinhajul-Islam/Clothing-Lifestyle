"""Idempotency repository for mutation tracking."""

import json
from typing import Any, Dict, Optional
from backend.app.repositories.base import BaseRepository


class IdempotencyRepository(BaseRepository):
    """Persistence for idempotency keys to prevent duplicate execution."""

    def get_idempotency_record(self, key: str) -> Optional[Dict[str, Any]]:
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT idempotency_key, tool_name, request_hash, response_json, status, created_at
                FROM tool_idempotency_keys
                WHERE idempotency_key = %s;
                """,
                (key,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def record_idempotency(
        self,
        key: str,
        tool_name: str,
        request_hash: str,
        response_json: Dict[str, Any],
        status: str = "SUCCEEDED"
    ) -> None:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tool_idempotency_keys (idempotency_key, tool_name, request_hash, response_json, status)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (idempotency_key) DO NOTHING;
                """,
                (key, tool_name, request_hash, json.dumps(response_json), status)
            )
