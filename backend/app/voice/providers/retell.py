"""Retell transport adapter; commerce decisions stay in VoiceService."""

import hashlib
import hmac
import re
import time
from typing import Any

from backend.app.config import settings
from backend.app.voice.schemas import VoiceTurnRequest, VoiceTurnResponse


_SIGNATURE = re.compile(r"^v=(\d+),d=([0-9a-fA-F]+)$")


class RetellProviderAdapter:
    """Verify and translate Retell events at the provider boundary."""

    def __init__(self, *, webhook_secret: str | None = None, max_age_seconds: int = 300):
        self.webhook_secret = webhook_secret or settings.retell_webhook_secret
        self.max_age_seconds = max_age_seconds

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        signature = next(
            (value for key, value in headers.items() if key.casefold() == "x-retell-signature"),
            "",
        )
        match = _SIGNATURE.fullmatch(signature.strip())
        if not self.webhook_secret or not match:
            return False
        timestamp, supplied = match.groups()
        if abs(int(time.time() * 1000) - int(timestamp)) > self.max_age_seconds * 1000:
            return False
        try:
            raw_text = body.decode("utf-8")
        except UnicodeDecodeError:
            return False
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            (raw_text + timestamp).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, supplied.casefold())

    def normalize_event(self, event: dict[str, Any]) -> VoiceTurnRequest:
        call = event.get("call") or {}
        metadata = call.get("metadata") or {}
        args = event.get("args") or {}
        session_id = (
            args.get("session_id")
            or metadata.get("nexgen_session_id")
            or event.get("session_id")
        )
        transcript = args.get("transcript") or args.get("message")
        if not transcript:
            transcript = self._latest_user_utterance(call)
        context = args.get("context") or {}
        return VoiceTurnRequest(
            session_id=session_id,
            transcript=transcript,
            context=context,
        )

    def build_response(self, response: VoiceTurnResponse) -> dict[str, Any]:
        return {
            "result": response.spoken_text,
            "spoken_text": response.spoken_text,
            "execution_status": response.execution_status,
            "needs_user_input": response.needs_user_input,
            "requires_confirmation": response.requires_confirmation,
        }

    @staticmethod
    def _latest_user_utterance(call: dict[str, Any]) -> str | None:
        transcript = call.get("transcript_object") or call.get("transcript_with_tool_calls") or []
        for item in reversed(transcript):
            if item.get("role") in {"user", "customer"} and item.get("content"):
                return str(item["content"])
        return None
