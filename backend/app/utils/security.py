"""Security, HMAC confirmation tokens, and request hashing."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict
from backend.app.config import settings


def hash_request_payload(payload: Dict[str, Any] | str) -> str:
    """Calculate deterministic SHA-256 hash of a request payload."""
    if isinstance(payload, dict):
        # Exclude volatile fields like request_id and confirmation_token from idempotency hashing
        filtered = {k: v for k, v in payload.items() if k not in ("request_id", "confirmation_token", "confirmed", "idempotency_key")}
        serialized = json.dumps(filtered, sort_keys=True, default=str)
    else:
        serialized = str(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def generate_confirmation_token(action: str, entity_id: str) -> str:
    """Generate a time-bound HMAC-signed confirmation token.
    
    Format: base64(action:entity_id:timestamp):signature
    """
    ts = int(time.time())
    payload = f"{action}:{entity_id}:{ts}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
    
    secret = settings.confirmation_secret.encode("utf-8")
    sig = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_confirmation_token(
    token: str,
    expected_action: str,
    expected_entity_id: str,
    max_age_seconds: int = 900
) -> bool:
    """Verify an HMAC confirmation token for action, entity_id, and expiration."""
    if not token or "." not in token:
        return False
    
    payload_b64, sig = token.split(".", 1)
    secret = settings.confirmation_secret.encode("utf-8")
    expected_sig = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(sig, expected_sig):
        return False
    
    try:
        payload = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        parts = payload.split(":", 2)
        if len(parts) != 3:
            return False
        action, entity_id, ts_str = parts
        ts = int(ts_str)
        
        # Check action & entity match
        if action != expected_action or entity_id != expected_entity_id:
            return False
        
        # Check expiration (default 15 minutes)
        if time.time() - ts > max_age_seconds:
            return False
        
        return True
    except Exception:
        return False

