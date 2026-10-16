"""Race-level endpoints: full results and fastest-lap telemetry."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query

from api.schemas import RaceResultsResponse, TelemetryResponse
from services import driver_telemetry, race_results

router = APIRouter(tags=["races"])

RoundPath = Path(..., ge=1, description="Race round")


@router.get("/races/{year}/{round}/results", response_model=RaceResultsResponse)
def results(year: int, round: int = RoundPath):
    return race_results(year, round)


@router.get("/races/{year}/{round}/telemetry", response_model=TelemetryResponse)
def telemetry(
    year: int,
    round: int = RoundPath,
    drivers: list[str] = Query(..., min_length=1, description="Driver codes, e.g. VER"),
    max_points: int = Query(
        2000,
        ge=1,
        le=10000,
        description="Max evenly-spaced samples returned per driver",
    ),
):
    codes = [d.strip().upper() for d in drivers if d and d.strip()]
    return driver_telemetry(year, round, codes, max_points=max_points)
