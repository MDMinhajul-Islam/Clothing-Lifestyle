"""Offline Phase 2G conversation demo. No database or mutation is used."""

from backend.app.voice.executor import VoiceCapabilityExecutor
from backend.app.voice.schemas import CapabilityResult, CreateVoiceSessionRequest, VoiceTurnRequest
from backend.app.voice.service import VoiceService


class DemoBackend:
    def execute(self, decision):
        if decision.route.value == "POLICY_RAG":
            return CapabilityResult(execution_status="STUBBED_OFFICIAL_RAG",
                spoken_text="Demo stub: the official Zara US policy handler would provide grounded evidence here.")
        if decision.tool_name == "track_order":
            return CapabilityResult(execution_status="STUBBED_TOOL_GATEWAY",
                spoken_text="Demo stub: the Tool Gateway would return the current shipment status here.")
        return CapabilityResult(execution_status="STUBBED_CAPABILITY",
                                spoken_text="Demo stub: the capability would respond here.")

    def prepare_write(self, tool_name, arguments):
        return CapabilityResult(execution_status="STUBBED_GATEWAY_PREFLIGHT",
            confirmation_token="demo-token-never-submitted",
            confirmation_prompt="Demo only: should I ask the Tool Gateway to proceed?")

    def confirm_write(self, tool_name, arguments, confirmation_token):
        raise RuntimeError("The offline demo never executes write confirmations.")


def main():
    service = VoiceService(executor=VoiceCapabilityExecutor(DemoBackend()))
    session_id = service.create_session(CreateVoiceSessionRequest()).session_id
    turns = ["Hello", "What's Zara's return policy?", "Where is my order?",
             "ORD-123", "Cancel my order", "No"]
    for transcript in turns:
        response = service.process_voice_turn(VoiceTurnRequest(
            session_id=session_id, transcript=transcript))
        print(f"User: {transcript}")
        print(f"Assistant: {response.spoken_text}")
    service.end_session(session_id)


if __name__ == "__main__":
    main()
