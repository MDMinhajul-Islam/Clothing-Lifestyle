from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.app.orchestrator.schemas import OrchestratorContext, Route


class VoiceProvider(str, Enum):
    MOCK = "mock"


class CreateVoiceSessionRequest(BaseModel):
    provider: VoiceProvider = VoiceProvider.MOCK
    customer_id: str | None = None

    @field_validator("customer_id")
    @classmethod
    def strip_customer(cls, value):
        return value.strip() or None if value else None


class VoiceTurnRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    transcript: str = Field(min_length=1, max_length=1000)
    context: OrchestratorContext = Field(default_factory=OrchestratorContext)

    @field_validator("session_id", "transcript")
    @classmethod
    def strip_required(cls, value):
        if not value.strip():
            raise ValueError("value cannot be blank")
        return value.strip()


class VoiceSessionView(BaseModel):
    session_id: str
    provider: VoiceProvider
    customer_id: str | None = None
    conversation_turn: int
    created_at: str


class VoiceTurnResponse(BaseModel):
    session_id: str
    status: str
    route: Route | None = None
    intent: str | None = None
    execution_status: str
    spoken_text: str
    needs_user_input: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    tool_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EndVoiceSessionResponse(BaseModel):
    session_id: str
    ended: bool


class CapabilityResult(BaseModel):
    execution_status: str
    data: dict[str, Any] = Field(default_factory=dict)
    spoken_text: str | None = None
    confirmation_token: str | None = None
    confirmation_prompt: str | None = None
