"""Public orchestrator service. Execution belongs to downstream capabilities."""

from .router import IntentRouter
from .schemas import RouteDecision, RouteRequest


class OrchestratorService:
    def __init__(self, router=None):
        self.router = router or IntentRouter()

    def route(self, request: RouteRequest) -> RouteDecision:
        return self.router.route(request)
