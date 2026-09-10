import hashlib
import hmac
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.api.routes_retell import (
    CreateWebCallRequest, RetellFunctionContext, WebCallRateLimiter, create_web_call,
    get_retell_function_context, retell_function_results, router,
)
from backend.app.main import app
from backend.app.voice.providers.retell import RetellProviderAdapter
from backend.app.voice.schemas import VoiceTurnResponse
from backend.app.orchestrator.schemas import Route


class RetellTransportTests(unittest.TestCase):
    def test_retell_routes_are_registered(self):
        paths = {route.path for route in router.routes}
        self.assertIn("/v1/retell/create-web-call", paths)
        self.assertIn("/v1/retell/webhook", paths)
        self.assertIn("/v1/retell/function", paths)

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

    def test_webpage_context_is_restored_and_function_context_wins(self):
        request = RetellProviderAdapter(webhook_secret="secret").normalize_event({
            "name": "nexgen_voice_turn",
            "args": {"transcript": "Medium?", "context": {"size": "M"}},
            "call": {"metadata": {"nexgen_session_id": "voice-123", "webpage_context": {
                "product_id": "zara-us:00000001", "size": "S",
                "visible_products": [{"product_id": "zara-us:00000001", "name": "Dress"}],
            }}},
        })
        self.assertEqual(request.context.product_id, "zara-us:00000001")
        self.assertEqual(request.context.size, "M")
        self.assertEqual(request.context.visible_products[0]["name"], "Dress")

    def test_build_response_returns_retell_spoken_result(self):
        response = VoiceTurnResponse(session_id="voice-123", status="READY",
            route=Route.GENERAL_CHAT, intent="GENERAL_CONVERSATION",
            execution_status="SUCCESS", spoken_text="Hello.")
        built = RetellProviderAdapter(webhook_secret="secret").build_response(response)
        self.assertEqual(built["result"], "Hello.")
        self.assertNotIn("metadata", built)

    @patch("backend.app.api.routes_retell.RetellClient.create_web_call")
    @patch("backend.app.api.routes_retell.settings.retell_agent_id", "agent-configured")
    @patch("backend.app.api.routes_retell.web_call_rate_limiter.allow", return_value=True)
    def test_create_web_call_returns_only_public_call_credentials(self, _allow, create_call):
        create_call.return_value = {
            "call_id": "call-123", "access_token": "public-token", "agent_id": "agent-1"
        }
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
        response = create_web_call(CreateWebCallRequest(context={
            "product_id": "zara-us:00000001", "active_variant_id": "black-m",
            "color": "Black", "size": "M",
        }), request)
        self.assertEqual(response.model_dump(), {
            "call_id": "call-123", "access_token": "public-token"
        })
        sent = create_call.call_args.args[0]
        self.assertEqual(sent["agent_id"], "agent-configured")
        self.assertIn("nexgen_session_id", sent["metadata"])
        self.assertEqual(sent["metadata"]["webpage_context"]["product_id"], "zara-us:00000001")
        self.assertEqual(sent["metadata"]["webpage_context"]["active_variant_id"], "black-m")

    @patch("backend.app.api.routes_retell.RetellClient.create_web_call")
    @patch("backend.app.api.routes_retell.settings.retell_agent_id", "agent-configured")
    @patch("backend.app.api.routes_retell.web_call_rate_limiter.allow", return_value=True)
    def test_logged_in_portal_cookie_authorizes_voice_server_side(self, _allow, create_call):
        create_call.return_value = {"call_id": "call-portal", "access_token": "public-token"}
        connection = object()
        manager = MagicMock()
        manager.__enter__.return_value = connection
        request = SimpleNamespace(
            headers={}, cookies={"nexgen_customer_session": "portal-cookie"},
            client=SimpleNamespace(host="127.0.0.1"),
        )
        with patch("backend.app.api.routes_retell.get_db_connection", return_value=manager), \
                patch("backend.app.api.routes_retell.CustomerAuthService.profile", return_value={
                    "customer_id": "customer-1", "first_name": "Minhajul", "last_name": "Islam",
                    "email": "mdminhajul.islam1823@gmail.com", "addresses": [{
                        "address_id": "address-1", "is_default_shipping": True,
                    }],
                }), \
                patch("backend.app.api.routes_retell.RetailCapabilityService.issue_portal_voice_access",
                      return_value="server-side-voice-token"):
            create_web_call(CreateWebCallRequest(customer_id="untrusted-browser-id"), request)
        metadata = create_call.call_args.args[0]["metadata"]
        state = __import__("backend.app.api.routes_retell", fromlist=["voice_service"]).voice_service.get_session(
            metadata["nexgen_session_id"])
        self.assertEqual(state.customer_id, "customer-1")
        self.assertEqual(state.auth_level, "TRANSACTION_VERIFIED")
        self.assertEqual(state.access_token, "server-side-voice-token")
        self.assertEqual(state.confirmed_spoken_email, "mdminhajul.islam1823@gmail.com")
        self.assertEqual(state.customer_name, "Minhajul Islam")
        self.assertEqual(state.shipping_address_id, "address-1")
        self.assertTrue(state.shipping_profile_loaded)

    def test_create_web_call_schema_rejects_browser_agent_override(self):
        with self.assertRaises(ValidationError):
            CreateWebCallRequest.model_validate({"agent_id": "browser-selected"})

    def test_create_web_call_has_no_tool_secret_dependency(self):
        route = next(item for item in router.routes if item.path.endswith("/create-web-call"))
        header_names = {parameter.alias for parameter in route.dependant.header_params}
        self.assertNotIn("X-Tool-Secret", header_names)

    def test_anonymous_rate_limit_rejects_excess_calls(self):
        limiter = WebCallRateLimiter(limit=2, window_seconds=60)
        self.assertTrue(limiter.allow("guest"))
        self.assertTrue(limiter.allow("guest"))
        self.assertFalse(limiter.allow("guest"))

    @patch("backend.app.api.routes_retell.web_call_rate_limiter.allow", return_value=False)
    def test_create_web_call_returns_429_when_limited(self, _allow):
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
        with self.assertRaises(HTTPException) as raised:
            create_web_call(CreateWebCallRequest(), request)
        self.assertEqual(raised.exception.status_code, 429)

    @staticmethod
    def _signed_headers(body: bytes) -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        digest = hmac.new(b"secret", body + timestamp.encode(), hashlib.sha256).hexdigest()
        return {"X-Retell-Signature": f"v={timestamp},d={digest}",
                "Content-Type": "application/json"}

    @patch("backend.app.api.routes_retell.settings.retell_webhook_secret", "secret")
    @patch("backend.app.api.routes_retell.voice_service.process_voice_turn")
    def test_transcript_webhook_never_executes_conversation(self, process_turn):
        body = json.dumps({"event": "transcript_updated", "call": {}}).encode()
        response = TestClient(app).post("/v1/retell/webhook", content=body,
                                        headers=self._signed_headers(body))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["processed"])
        process_turn.assert_not_called()

    @patch("backend.app.api.routes_retell.settings.retell_webhook_secret", "secret")
    @patch("backend.app.api.routes_retell.voice_service.process_voice_turn")
    def test_custom_function_executes_once_and_returns_spoken_text(self, process_turn):
        process_turn.return_value = VoiceTurnResponse(
            session_id="voice-123", status="READY", route=Route.TOOL_GATEWAY,
            intent="SEARCH_PRODUCTS", execution_status="SUCCESS",
            spoken_text="I found three black dresses.")
        body = json.dumps({
            "name": "nexgen_voice_turn",
            "args": {"transcript": "Show me black dresses"},
            "call": {"call_id": "call-123",
                     "metadata": {"nexgen_session_id": "voice-123"}},
        }, separators=(",", ":")).encode()
        app.dependency_overrides[get_retell_function_context] = lambda: RetellFunctionContext(object())
        retell_function_results.clear()
        try:
            client = TestClient(app)
            first = client.post("/v1/retell/function", content=body,
                                headers=self._signed_headers(body))
            second = client.post("/v1/retell/function", content=body,
                                 headers=self._signed_headers(body))
        finally:
            app.dependency_overrides.pop(get_retell_function_context, None)
            retell_function_results.clear()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["result"], "I found three black dresses.")
        self.assertEqual(second.json(), first.json())
        process_turn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
