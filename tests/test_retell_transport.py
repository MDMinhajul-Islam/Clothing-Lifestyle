import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import patch

from backend.app.api.routes_retell import CreateWebCallRequest, create_web_call, router
from backend.app.voice.providers.retell import RetellProviderAdapter
from backend.app.voice.schemas import VoiceTurnResponse
from backend.app.orchestrator.schemas import Route


class RetellTransportTests(unittest.TestCase):
    def test_retell_routes_are_registered(self):
        paths = {route.path for route in router.routes}
        self.assertIn("/v1/retell/create-web-call", paths)
        self.assertIn("/v1/retell/webhook", paths)

    def test_signature_verification_uses_raw_body_and_rejects_tampering(self):
        body = b'{"event":"transcript_updated"}'
        timestamp = str(int(time.time() * 1000))
        digest = hmac.new(b"secret", body + timestamp.encode(), hashlib.sha256).hexdigest()
        adapter = RetellProviderAdapter(webhook_secret="secret")
        headers = {"x-retell-signature": f"v={timestamp},d={digest}"}
        self.assertTrue(adapter.verify_webhook(headers, body))
        self.assertFalse(adapter.verify_webhook(headers, body + b" "))

    def test_signature_rejects_stale_timestamp(self):
        body = b"{}"
        timestamp = str(int((time.time() - 301) * 1000))
        digest = hmac.new(b"secret", body + timestamp.encode(), hashlib.sha256).hexdigest()
        self.assertFalse(RetellProviderAdapter(webhook_secret="secret").verify_webhook(
            {"X-Retell-Signature": f"v={timestamp},d={digest}"}, body))

    def test_transcript_event_normalizes_to_existing_voice_contract(self):
        request = RetellProviderAdapter(webhook_secret="secret").normalize_event({
            "event": "transcript_updated",
            "call": {
                "metadata": {"nexgen_session_id": "voice-123"},
                "transcript_object": [
                    {"role": "agent", "content": "How can I help?"},
                    {"role": "user", "content": "Show me black dresses"},
                ],
            },
        })
        self.assertEqual(request.session_id, "voice-123")
        self.assertEqual(request.transcript, "Show me black dresses")

    def test_build_response_returns_retell_spoken_result(self):
        response = VoiceTurnResponse(session_id="voice-123", status="READY",
            route=Route.GENERAL_CHAT, intent="GENERAL_CONVERSATION",
            execution_status="SUCCESS", spoken_text="Hello.")
        built = RetellProviderAdapter(webhook_secret="secret").build_response(response)
        self.assertEqual(built["result"], "Hello.")
        self.assertNotIn("metadata", built)

    @patch("backend.app.api.routes_retell.RetellClient.create_web_call")
    def test_create_web_call_returns_only_public_call_credentials(self, create_call):
        create_call.return_value = {
            "call_id": "call-123", "access_token": "public-token", "agent_id": "agent-1"
        }
        response = create_web_call(CreateWebCallRequest(agent_id="agent-1"))
        self.assertEqual(response.model_dump(), {
            "call_id": "call-123", "access_token": "public-token"
        })
        sent = create_call.call_args.args[0]
        self.assertEqual(sent["agent_id"], "agent-1")
        self.assertIn("nexgen_session_id", sent["metadata"])


if __name__ == "__main__":
    unittest.main()
