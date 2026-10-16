"""Health / status endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas import HealthResponse

router = APIRouter(tags=["status"])


@router.get("/health", response_model=HealthResponse, summary="Liveness/readiness")
def health() -> HealthResponse:
    """Return application status.

    Deliberately does NOT touch upstream providers, so it stays green even
    when FastF1/Ergast are unreachable — useful for load balancers/CI.
    """
    return HealthResponse()
