"""FastAPI Dependencies for Authentication, Database Connections, and Audit Logging."""

import logging
import time
import uuid
from typing import Any, Dict, Generator, Optional
from fastapi import Header, HTTPException, Request, Security, status
import psycopg2.extensions

from backend.app.config import settings
from backend.app.db import get_db_connection
from backend.app.repositories.audit_repo import AuditRepository

logger = logging.getLogger("tool_gateway.api")


def verify_tool_secret(
    x_tool_secret: Optional[str] = Header(None, alias="X-Tool-Secret")
) -> str:
    """Enforce authentication via X-Tool-Secret header."""
    expected = settings.tool_gateway_secret
    if not expected or x_tool_secret != expected:
        logger.warning("Unauthorized tool invocation attempted.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Missing or invalid X-Tool-Secret header."
            }
        )
    return x_tool_secret


def get_db() -> Generator[psycopg2.extensions.connection, None, None]:
    """Provide a database connection from the pool."""
    with get_db_connection() as conn:
        yield conn


def log_tool_audit(
    conn: psycopg2.extensions.connection,
    tool_name: str,
    request_id: str,
    request_summary: Dict[str, Any],
    result_status: str,
    duration_ms: int,
    customer_id: Optional[str] = None,
    order_id: Optional[str] = None,
    error_code: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> None:
    """Persist audit log entry safely."""
    try:
        audit_repo = AuditRepository(conn)
        audit_repo.log_tool_execution(
            tool_name=tool_name,
            request_id=request_id,
            request_summary=request_summary,
            result_status=result_status,
            duration_ms=duration_ms,
            customer_id=customer_id,
            order_id=order_id,
            error_code=error_code,
            idempotency_key=idempotency_key,
        )
        conn.commit()
    except Exception as e:
        logger.error("Failed to write tool audit log: %s", e)

