"""Authenticated local voice-session simulation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import get_db, verify_tool_secret
from backend.app.voice.capabilities.local import LocalVoiceCapabilityBackend
from backend.app.voice.executor import VoiceCapabilityExecutor
from backend.app.voice.schemas import (
    CreateVoiceSessionRequest, EndVoiceSessionResponse, VoiceSessionView,
    VoiceTurnRequest, VoiceTurnResponse,
)
from backend.app.voice.service import VoiceService
from backend.app.voice.session import VoiceSessionNotFound
from backend.app.notifications.customer_communication import CustomerCommunicationService

router = APIRouter(prefix="/v1/voice", tags=["Voice Agent"],
                   dependencies=[Depends(verify_tool_secret)])
voice_service = VoiceService()


@router.post("/session", response_model=VoiceSessionView)
def create_voice_session(payload: CreateVoiceSessionRequest):
    return voice_service.create_session(payload)


@router.post("/turn", response_model=VoiceTurnResponse)
def process_voice_turn(payload: VoiceTurnRequest, conn=Depends(get_db)):
    try:
        executor = VoiceCapabilityExecutor(LocalVoiceCapabilityBackend(conn))
        return voice_service.process_voice_turn(
            payload, executor=executor, communicator=CustomerCommunicationService(conn))
    except VoiceSessionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Voice turn processing failed.") from None


@router.get("/session/{session_id}", response_model=VoiceSessionView)
def get_voice_session(session_id: str):
    try:
        return VoiceSessionView(**voice_service.get_session(session_id).model_dump())
    except VoiceSessionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None


@router.delete("/session/{session_id}", response_model=EndVoiceSessionResponse)
def end_voice_session(session_id: str):
    try:
        return voice_service.end_session(session_id)
    except VoiceSessionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
