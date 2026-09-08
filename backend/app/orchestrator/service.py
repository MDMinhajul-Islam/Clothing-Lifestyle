"""Public orchestrator service. Execution belongs to downstream capabilities."""

import time

from backend.app.retell.timing import timed
from .router import IntentRouter
from .schemas import RouteDecision, RouteRequest


class OrchestratorService:
    def __init__(self, router=None):
        self.router = router or IntentRouter()

    def route(self, request: RouteRequest) -> RouteDecision:
        started = time.perf_counter()
        try:
            return self.router.route(request)
        finally:
            timed("intent_router", started)
