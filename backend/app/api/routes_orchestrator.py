"""Authenticated read-only endpoint for deterministic request routing."""

from fastapi import APIRouter, Depends

from backend.app.api.deps import verify_tool_secret
from backend.app.orchestrator.schemas import RouteDecision, RouteRequest
from backend.app.orchestrator.service import OrchestratorService

router = APIRouter(prefix="/v1/orchestrator", tags=["AI Orchestrator"],
                   dependencies=[Depends(verify_tool_secret)])


@router.post("/route", response_model=RouteDecision)
def route_request(payload: RouteRequest):
    return OrchestratorService().route(payload)
