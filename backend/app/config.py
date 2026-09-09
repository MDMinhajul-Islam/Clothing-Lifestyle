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

    app_name: str = "NexGen AI Retail Voice Commerce Assistant"
    brand_name: str = Field(default_factory=lambda: os.getenv("BRAND_NAME", "NexGen"))
    agent_name: str = Field(default_factory=lambda: os.getenv("AGENT_NAME", "NexGen Assistant"))
    policy_reference_brand: str = "Zara"
    policy_reference_market: str = "US"
    policy_reference_locale: str = "en"
    policy_usage: str = "REFERENCE_DEMO"
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

    # Retell credentials remain server-side. The webhook secret may be the
    # Retell API key designated for webhook signing or a separately managed key.
    retell_api_key: str = Field(default_factory=lambda: os.getenv("RETELL_API_KEY", ""))
    retell_agent_id: str = Field(default_factory=lambda: os.getenv("RETELL_AGENT_ID", ""))
    retell_webhook_secret: str = Field(
        default_factory=lambda: os.getenv("RETELL_WEBHOOK_SECRET", "")
    )

    # Transactional email. Credentials remain server-side and are never logged.
    email_provider: str = Field(default_factory=lambda: os.getenv("EMAIL_PROVIDER", "smtp"))
    email_from_name: str = Field(default_factory=lambda: os.getenv("EMAIL_FROM_NAME", "NexGen AI Fashion & Voice Commerce"))
    email_from_address: str = Field(default_factory=lambda: os.getenv("EMAIL_FROM_ADDRESS", ""))
    smtp_host: str = Field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = Field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_username: str = Field(default_factory=lambda: os.getenv("SMTP_USERNAME", ""))
    smtp_password: str = Field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_use_tls: bool = Field(default_factory=lambda: os.getenv("SMTP_USE_TLS", "true").lower() == "true")
    payment_placeholder_url: str = Field(default_factory=lambda: os.getenv("PAYMENT_PLACEHOLDER_URL", "https://example.invalid/complete-payment"))
    admin_email: str = Field(default_factory=lambda: os.getenv("ADMIN_EMAIL", ""))
    admin_password_hash: str = Field(default_factory=lambda: os.getenv("ADMIN_PASSWORD_HASH", ""))
    customer_portal_url: str = Field(default_factory=lambda: os.getenv("CUSTOMER_PORTAL_URL", "http://localhost:5173"))
    customer_session_cookie: str = Field(default_factory=lambda: os.getenv("CUSTOMER_SESSION_COOKIE", "nexgen_customer_session"))
    customer_session_days: int = Field(default_factory=lambda: int(os.getenv("CUSTOMER_SESSION_DAYS", "7")))
    cors_origins: str = Field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*"))

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
