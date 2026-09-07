"""Capability boundary used by voice; implementations call existing capability APIs."""

from typing import Protocol

from backend.app.orchestrator.schemas import Route, RouteDecision
from backend.app.rag.service import retrieve_policy_knowledge
from .schemas import CapabilityResult


class VoiceCapabilityBackend(Protocol):
    def execute(self, decision: RouteDecision) -> CapabilityResult: ...
    def prepare_write(self, tool_name: str, arguments: dict) -> CapabilityResult: ...
    def confirm_write(self, tool_name: str, arguments: dict,
                      confirmation_token: str) -> CapabilityResult: ...


class LocalCapabilityBackend:
    """Runs public policy RAG; defers capabilities that require a gateway adapter."""

    def execute(self, decision: RouteDecision):
        if decision.route == Route.POLICY_RAG:
            result = retrieve_policy_knowledge(**decision.tool_arguments)
            return CapabilityResult(execution_status=result.status,
                                    data=result.model_dump(mode="json"))
        return CapabilityResult(execution_status="CAPABILITY_ADAPTER_NOT_CONFIGURED")

    def prepare_write(self, tool_name, arguments):
        return CapabilityResult(execution_status="GATEWAY_PREFLIGHT_NOT_CONFIGURED")

    def confirm_write(self, tool_name, arguments, confirmation_token):
        return CapabilityResult(execution_status="GATEWAY_CONFIRMATION_NOT_CONFIGURED")


class VoiceCapabilityExecutor:
    def __init__(self, backend=None):
        self.backend = backend or LocalCapabilityBackend()

    def execute(self, decision):
        return self.backend.execute(decision)

    def prepare_write(self, decision):
        return self.backend.prepare_write(decision.tool_name, dict(decision.tool_arguments))

    def confirm_write(self, tool_name, arguments, confirmation_token):
        if not confirmation_token:
            return CapabilityResult(execution_status="GATEWAY_CONFIRMATION_TOKEN_UNAVAILABLE",
                spoken_text="I can't safely complete that action until the confirmation service is available.")
        return self.backend.confirm_write(tool_name, dict(arguments), confirmation_token)
