"""Retell web-call, lifecycle webhook, and synchronous function transport."""

import json
import hashlib
import logging
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from backend.app.api.routes_voice import voice_service
from backend.app.config import settings
from backend.app.db import get_db_connection
from backend.app.retell.client import RetellClient, RetellClientError
from backend.app.retell.timing import TimedConnection, begin as begin_timing, finish as finish_timing, mark, timed
from backend.app.voice.capabilities.local import LocalVoiceCapabilityBackend
from backend.app.voice.executor import VoiceCapabilityExecutor
from backend.app.voice.providers.retell import RetellProviderAdapter
from backend.app.voice.schemas import CreateVoiceSessionRequest, VoiceProvider
from backend.app.voice.session import VoiceSessionNotFound

logger = logging.getLogger("retell.transport")
router = APIRouter(prefix="/v1/retell", tags=["Retell Transport"])


class CreateWebCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: str | None = Field(default=None, max_length=120)


class CreateWebCallResponse(BaseModel):
    call_id: str
    access_token: str


class WebCallRateLimiter:
    """Small process-local guard for the anonymous call-creation boundary."""

    def __init__(self, limit: int = 10, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, client_key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts[client_key]
            while attempts and now - attempts[0] >= self.window_seconds:
                attempts.popleft()
            if len(attempts) >= self.limit:
                return False
            attempts.append(now)
            return True


web_call_rate_limiter = WebCallRateLimiter()


class RetellFunctionResultCache:
    """Deduplicate Retell retries without changing commerce-layer idempotency."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._responses: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        now = time.monotonic()
        with self._lock:
            expired = [item for item, (created, _) in self._responses.items()
                       if now - created >= self.ttl_seconds]
            for item in expired:
                self._responses.pop(item, None)
            cached = self._responses.get(key)
            return dict(cached[1]) if cached else None

    def put(self, key: str, response: dict[str, Any]) -> None:
        with self._lock:
            self._responses[key] = (time.monotonic(), dict(response))

    def clear(self) -> None:
        with self._lock:
            self._responses.clear()


retell_function_results = RetellFunctionResultCache()


class RetellFunctionContext:
    def __init__(self, connection):
        self.connection = connection


async def get_retell_function_context():
    """Start timing before database-pool acquisition so pool waits remain visible."""
    timing_token = begin_timing()
    started = time.perf_counter()
    try:
        with get_db_connection() as connection:
            timed("database_connection_acquired", started)
            yield RetellFunctionContext(TimedConnection(connection))
    finally:
        finish_timing(timing_token)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


@router.post(
    "/create-web-call",
    response_model=CreateWebCallResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_web_call(payload: CreateWebCallRequest, request: Request):
    """Create an anonymous-safe Retell room without browser-held secrets."""
    if not web_call_rate_limiter.allow(_client_key(request)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Too many web call requests. Please try again shortly.")
    if not settings.retell_agent_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Voice calling is not configured.")
    session = voice_service.create_session(CreateVoiceSessionRequest(
        provider=VoiceProvider.RETELL,
        customer_id=payload.customer_id,
    ))
    body: dict[str, Any] = {
        "agent_id": settings.retell_agent_id,
        "metadata": {"nexgen_session_id": session.session_id},
    }
    try:
        result = RetellClient(settings.retell_api_key).create_web_call(body)
    except RetellClientError as exc:
        voice_service.end_session(session.session_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None
    return CreateWebCallResponse(call_id=result["call_id"], access_token=result["access_token"])


def _verify_retell_request(adapter: RetellProviderAdapter, signature: str | None,
                           raw_body: bytes) -> None:
    if not adapter.verify_webhook({"X-Retell-Signature": signature or ""}, raw_body):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid Retell signature.")


def _decode_json(raw_body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid JSON payload.") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Retell payload must be an object.")
    return payload


@router.post("/webhook")
async def retell_webhook(
    request: Request,
    x_retell_signature: str | None = Header(default=None, alias="X-Retell-Signature"),
):
    """Verify and acknowledge lifecycle events; never execute conversation turns."""
    raw_body = await request.body()
    adapter = RetellProviderAdapter()
    _verify_retell_request(adapter, x_retell_signature, raw_body)
    event = _decode_json(raw_body)
    event_name = event.get("event")
    if event_name == "call_ended":
        session_id = ((event.get("call") or {}).get("metadata") or {}).get("nexgen_session_id")
        if session_id:
            try:
                voice_service.end_session(str(session_id))
            except VoiceSessionNotFound:
                pass
    return {"received": True, "event": event_name, "processed": False}


@router.post("/function")
async def retell_custom_function(
    request: Request,
    x_retell_signature: str | None = Header(default=None, alias="X-Retell-Signature"),
    timing_context: RetellFunctionContext = Depends(get_retell_function_context),
):
    """Execute one signed Retell custom function synchronously through VoiceService."""
    read_started = time.perf_counter()
    raw_body = await request.body()
    timed("request_body_read", read_started, bytes=len(raw_body))
    adapter = RetellProviderAdapter()
    verify_started = time.perf_counter()
    _verify_retell_request(adapter, x_retell_signature, raw_body)
    timed("signature_verification", verify_started)
    payload = _decode_json(raw_body)
    mark("request_decoded")
    if payload.get("name") != "nexgen_voice_turn":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Unsupported Retell function.")

    request_key = hashlib.sha256(raw_body).hexdigest()
    cached = retell_function_results.get(request_key)
    mark("idempotency_lookup", cached=bool(cached))
    if cached is not None:
        return cached

    try:
        normalize_started = time.perf_counter()
        voice_request = adapter.normalize_event(payload)
        timed("session_reference_normalized", normalize_started)
        executor = VoiceCapabilityExecutor(LocalVoiceCapabilityBackend(timing_context.connection))
        service_started = time.perf_counter()
        response = voice_service.process_voice_turn(voice_request, executor=executor)
        timed("voice_service_returned", service_started)
    except VoiceSessionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Retell event does not contain a valid voice turn.") from exc
    except Exception:
        logger.exception("Retell voice turn processing failed.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Retell function processing failed.") from None
    serialize_started = time.perf_counter()
    result = adapter.build_response(response)
    retell_function_results.put(request_key, result)
    timed("response_serialization", serialize_started)
    return result
