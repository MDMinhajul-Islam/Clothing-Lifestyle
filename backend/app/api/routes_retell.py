"""Authenticated Retell transport routes."""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.app.api.deps import get_db, verify_tool_secret
from backend.app.api.routes_voice import voice_service
from backend.app.config import settings
from backend.app.retell.client import RetellClient, RetellClientError
from backend.app.voice.capabilities.local import LocalVoiceCapabilityBackend
from backend.app.voice.executor import VoiceCapabilityExecutor
from backend.app.voice.providers.retell import RetellProviderAdapter
from backend.app.voice.schemas import CreateVoiceSessionRequest, VoiceProvider
from backend.app.voice.session import VoiceSessionNotFound

logger = logging.getLogger("retell.transport")
router = APIRouter(prefix="/v1/retell", tags=["Retell Transport"])


class CreateWebCallRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=120)
    customer_id: str | None = Field(default=None, max_length=120)


class CreateWebCallResponse(BaseModel):
    call_id: str
    access_token: str


@router.post(
    "/create-web-call",
    response_model=CreateWebCallResponse,
    dependencies=[Depends(verify_tool_secret)],
    status_code=status.HTTP_201_CREATED,
)
def create_web_call(payload: CreateWebCallRequest):
    """Create a Retell room without returning server credentials."""
    session = voice_service.create_session(CreateVoiceSessionRequest(
        provider=VoiceProvider.RETELL,
        customer_id=payload.customer_id,
    ))
    body: dict[str, Any] = {
        "agent_id": payload.agent_id,
        "metadata": {"nexgen_session_id": session.session_id},
    }
    try:
        result = RetellClient(settings.retell_api_key).create_web_call(body)
    except RetellClientError as exc:
        voice_service.end_session(session.session_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None
    return CreateWebCallResponse(call_id=result["call_id"], access_token=result["access_token"])


@router.post("/webhook")
async def retell_webhook(
    request: Request,
    x_retell_signature: str | None = Header(default=None, alias="X-Retell-Signature"),
    conn=Depends(get_db),
):
    """Verify, normalize, and execute Retell transcript/custom-function events."""
    raw_body = await request.body()
    adapter = RetellProviderAdapter()
    if not adapter.verify_webhook({"X-Retell-Signature": x_retell_signature or ""}, raw_body):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Retell signature.")
    try:
        event = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from None

    event_name = event.get("event")
    if event_name in {"call_started", "call_ended", "call_analyzed"}:
        return {"received": True}
    if event_name not in {None, "transcript_updated"}:
        return {"received": True}

    try:
        voice_request = adapter.normalize_event(event)
        executor = VoiceCapabilityExecutor(LocalVoiceCapabilityBackend(conn))
        response = voice_service.process_voice_turn(voice_request, executor=executor)
    except VoiceSessionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Retell event does not contain a valid voice turn.") from exc
    except Exception:
        logger.exception("Retell voice turn processing failed.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Retell voice turn processing failed.") from None
    return adapter.build_response(response)
