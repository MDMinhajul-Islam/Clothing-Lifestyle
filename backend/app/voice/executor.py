"""Capability boundary used by voice; implementations call existing capability APIs."""

import time

from backend.app.orchestrator.schemas import RouteDecision
from backend.app.retell.timing import timed
from backend.app.voice.capabilities.base import VoiceCapabilityBackend
from .schemas import CapabilityResult


class VoiceCapabilityExecutor:
    def __init__(self, backend=None):
        self.backend = backend

    def execute(self, decision):
        if self.backend is None:return CapabilityResult(execution_status="CAPABILITY_ADAPTER_NOT_CONFIGURED")
        started=time.perf_counter()
        try:return self.backend.execute(decision)
        finally:timed("voice_capability_executor",started,tool=decision.tool_name)

    def prepare_write(self, decision):
        if self.backend is None:return CapabilityResult(execution_status="CAPABILITY_ADAPTER_NOT_CONFIGURED")
        started=time.perf_counter()
        try:return self.backend.prepare_write(decision.tool_name, dict(decision.tool_arguments))
        finally:timed("voice_capability_executor_prepare",started,tool=decision.tool_name)

    def confirm_write(self, tool_name, arguments, confirmation_token):
        if not confirmation_token:
            return CapabilityResult(execution_status="GATEWAY_CONFIRMATION_TOKEN_UNAVAILABLE",
                spoken_text="I can't safely complete that action until the confirmation service is available.")
        if self.backend is None:return CapabilityResult(execution_status="CAPABILITY_ADAPTER_NOT_CONFIGURED")
        started=time.perf_counter()
        try:return self.backend.confirm_write(tool_name, dict(arguments), confirmation_token)
        finally:timed("voice_capability_executor_confirm",started,tool=tool_name)
