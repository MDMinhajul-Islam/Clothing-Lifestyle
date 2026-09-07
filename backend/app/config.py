"""Application Configuration and Environment Settings."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

# Locate root directory and .env
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"


def _load_env_file(path: Path):
    """Load key-value pairs from .env into os.environ if not already present."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k not in os.environ:
                    os.environ[k] = v


_load_env_file(ENV_PATH)


class Settings(BaseModel):
    """Application Settings validated by Pydantic."""

    app_name: str = "Zara AI Tool Gateway"
    app_version: str = "1.0.0"
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    
    # Supabase / Database Settings
    supabase_db_url: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_DB_URL", "")
    )
    supabase_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("SUPABASE_URL", None)
    )
    supabase_service_role_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", None)
    )

    # Tool Gateway Authentication
    tool_gateway_secret: str = Field(
        default_factory=lambda: os.getenv("TOOL_GATEWAY_SECRET", "default-dev-tool-secret-change-in-prod")
    )
    confirmation_secret: str = Field(
        default_factory=lambda: os.getenv("CONFIRMATION_SECRET", os.getenv("TOOL_GATEWAY_SECRET", "confirm-secret-seed"))
    )

    # Database Pool Settings
    db_pool_min_conns: int = 2
    db_pool_max_conns: int = 10

    # Rate Limiting & Safety Limits
    rate_limit_max_requests: int = 120
    rate_limit_window_seconds: int = 60
    max_search_limit: int = 50
    default_search_limit: int = 20

    class Config:
        arbitrary_types_allowed = True


# Global cached settings instance
settings = Settings()
