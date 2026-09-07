"""Thread-safe in-memory voice session storage for local Phase 2G use."""

from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .schemas import VoiceProvider


class VoiceSession(BaseModel):
    session_id: str
    provider: VoiceProvider
    customer_id: str | None = None
    customer_type: str | None = None
    auth_level: str = "PUBLIC"
    access_token: str | None = None
    current_order_id: str | None = None
    current_product_id: str | None = None
    reference_product_id: str | None = None
    current_store_id: str | None = None
    last_intent: str | None = None
    last_route: str | None = None
    pending_tool_name: str | None = None
    pending_arguments: dict[str, Any] = Field(default_factory=dict)
    pending_missing_fields: list[str] = Field(default_factory=list)
    pending_confirmation: bool = False
    pending_confirmation_token: str | None = None
    conversation_turn: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class VoiceSessionNotFound(LookupError):
    pass


class InMemoryVoiceSessionStore:
    def __init__(self):
        self._sessions: dict[str, VoiceSession] = {}
        self._lock = RLock()

    def create_session(self, provider=VoiceProvider.MOCK, customer_id=None):
        session = VoiceSession(session_id=f"voice-{uuid4().hex}", provider=provider,
                               customer_id=customer_id)
        with self._lock:
            self._sessions[session.session_id] = session
        return session.model_copy(deep=True)

    def get_session(self, session_id):
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise VoiceSessionNotFound("Voice session was not found.")
            return session.model_copy(deep=True)

    def update_session(self, session):
        with self._lock:
            if session.session_id not in self._sessions:
                raise VoiceSessionNotFound("Voice session was not found.")
            self._sessions[session.session_id] = session.model_copy(deep=True)
        return session.model_copy(deep=True)

    def end_session(self, session_id):
        with self._lock:
            if session_id not in self._sessions:
                raise VoiceSessionNotFound("Voice session was not found.")
            del self._sessions[session_id]
