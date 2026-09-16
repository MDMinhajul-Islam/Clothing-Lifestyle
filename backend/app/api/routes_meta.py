"""Health check and metadata routes."""

from fastapi import APIRouter, Depends
import psycopg2.extensions
from backend.app.config import settings
from backend.app.api.deps import get_db
from backend.app.tools.registry import export_tool_definitions

router = APIRouter(tags=["Metadata"])


@router.get("/livez")
async def liveness_check():
    """Process liveness after ASGI startup; no database or external service calls."""
    return {"status": "alive"}


@router.get("/health")
def health_check(conn: psycopg2.extensions.connection = Depends(get_db)):
    """Readiness check; retain the existing database-aware API contract."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1;")
        cur.fetchone()

    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "connected"
    }


@router.get("/v1/tools/definitions")
def get_definitions():
    """Retrieve machine-readable tool catalog definitions."""
    return export_tool_definitions()
