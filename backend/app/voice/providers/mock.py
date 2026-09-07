from typing import Any

from backend.app.voice.schemas import VoiceTurnRequest, VoiceTurnResponse


class MockVoiceProviderAdapter:
    """Local transcript-only adapter; it performs no STT, TTS, or network calls."""

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        return True

    def normalize_event(self, event: dict[str, Any]) -> VoiceTurnRequest:
        return VoiceTurnRequest.model_validate(event)

    def build_response(self, response: VoiceTurnResponse) -> dict[str, Any]:
        return response.model_dump(mode="json")
