"""Small real-backend NexGen voice demo; read flows and write preflight only."""

from backend.app.db import close_db_pool, get_db_connection
from backend.app.voice.capabilities.local import LocalVoiceCapabilityBackend
from backend.app.voice.executor import VoiceCapabilityExecutor
from backend.app.voice.schemas import CreateVoiceSessionRequest, VoiceTurnRequest
from backend.app.voice.service import VoiceService


def main():
    with get_db_connection() as conn:
        service = VoiceService(executor=VoiceCapabilityExecutor(LocalVoiceCapabilityBackend(conn)))
        session_id = service.create_session(CreateVoiceSessionRequest()).session_id
        for transcript in ("Hello", "What is the return policy?", "I need something for a wedding"):
            response = service.process_voice_turn(VoiceTurnRequest(
                session_id=session_id, transcript=transcript))
            print(f"User: {transcript}")
            print(f"Assistant: {response.spoken_text}")
        service.end_session(session_id)
    close_db_pool()


if __name__ == "__main__":
    main()
