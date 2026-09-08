"""Minimal server-side client for the Retell REST API."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RetellClientError(RuntimeError):
    pass


class RetellClient:
    CREATE_WEB_CALL_URL = "https://api.retellai.com/v2/create-web-call"

    def __init__(self, api_key: str, *, timeout_seconds: float = 10.0):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def create_web_call(self, payload: dict) -> dict:
        if not self.api_key:
            raise RetellClientError("Retell is not configured.")
        request = Request(
            self.CREATE_WEB_CALL_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RetellClientError(f"Retell rejected the web call request ({exc.code}).") from None
        except (URLError, TimeoutError, json.JSONDecodeError):
            raise RetellClientError("Retell web call creation is temporarily unavailable.") from None
        if not result.get("call_id") or not result.get("access_token"):
            raise RetellClientError("Retell returned an incomplete web call response.")
        return result
