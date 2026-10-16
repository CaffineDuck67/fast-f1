"""Season-level endpoints: schedule, winners, standings, comparison."""

from __future__ import annotations

from fastapi import APIRouter, Query

from api.schemas import (
    ConstructorStanding,
    DriverStanding,
    RaceWinner,
    ScheduleEntry,
    SeasonComparisonResponse,
    SeasonSummary,
)
from services import (
    constructor_standings,
    driver_standings,
    list_race_winners,
    list_schedule,
    season_comparison,
)

router = APIRouter(tags=["seasons"])

# Bounds mirror f1_data's validation so bad input is rejected at the edge.
YearQuery = Query(..., ge=1950, le=2100, description="Season year")


@router.get("/seasons/{year}/schedule", response_model=list[ScheduleEntry])
def schedule(year: int):
    return list_schedule(year)


@router.get("/seasons/{year}/winners", response_model=list[RaceWinner])
def winners(year: int):
    return list_race_winners(year)


@router.get("/seasons/{year}/standings/drivers", response_model=list[DriverStanding])
def standings_drivers(year: int):
    return driver_standings(year)


@router.get(
    "/seasons/{year}/standings/constructors",
    response_model=list[ConstructorStanding],
)
def standings_constructors(year: int):
    return constructor_standings(year)


@router.get("/seasons/compare", response_model=SeasonComparisonResponse)
def compare(
    year1: int = YearQuery,
    year2: int = YearQuery,
):
    result = season_comparison(year1, year2)
    summaries = {
        str(year): SeasonSummary(**season["summary"]) for year, season in result["data"].items()
    }
    return SeasonComparisonResponse(
        year1=result["year1"],
        year2=result["year2"],
        data=summaries,
        errors={str(y): msg for y, msg in result["errors"].items()},
    )
