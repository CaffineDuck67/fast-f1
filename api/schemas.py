"""Pydantic request/response models for the fast-f1 analytics API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str = "fast-f1"
    version: str = "0.1.0"


class ScheduleEntry(BaseModel):
    round: int
    date: str
    event_name: str
    location: str
    country: str


class RaceWinner(BaseModel):
    round: int
    event_name: str
    driver: str | None = None
    constructor: str | None = None


class DriverStanding(BaseModel):
    position: int
    driver: str
    constructor: str
    points: float
    wins: int


class ConstructorStanding(BaseModel):
    position: int
    constructor: str
    points: float
    wins: int


class RaceResultRow(BaseModel):
    position: int | None = None
    driver_code: str
    driver: str
    team: str
    points: float | None = None
    status: str | None = None


class RaceResultsResponse(BaseModel):
    event_name: str
    results: list[RaceResultRow]


class SeasonSummary(BaseModel):
    num_races: int
    champion_driver: str
    champion_driver_points: float | None = None
    champion_constructor: str
    champion_constructor_points: float | None = None
    top_driver_wins: int | None = None


class SeasonComparisonResponse(BaseModel):
    year1: int
    year2: int
    data: dict[str, SeasonSummary]
    errors: dict[str, str] = Field(default_factory=dict)


class TelemetryDriver(BaseModel):
    driver_code: str
    lap_time: str
    n_samples: int
    returned_samples: int
    distance: list[float]
    speed: list[float]


class TelemetryResponse(BaseModel):
    year: int
    round: int
    event_name: str | None = None
    max_points: int
    drivers: list[TelemetryDriver]


class ErrorResponse(BaseModel):
    detail: str
    error_type: str
