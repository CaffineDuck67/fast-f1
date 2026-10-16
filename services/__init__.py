"""Service layer: reusable analytics/business logic for the API.

These functions wrap the ``f1_data`` access layer and shape results for
HTTP consumption (downsampling, summaries) without duplicating any
fetching logic. They raise the same specific exceptions as ``f1_data``
(``InvalidQueryError`` / ``DataSourceError`` / ``DataUnavailableError``),
which the API layer maps to status codes.
"""

from __future__ import annotations

from typing import Any

import f1_data
from f1_data import (
    compare_seasons,
    get_constructor_standings,
    get_driver_standings,
    get_multiple_drivers_lap_telemetry,
    get_race_results,
    get_race_winners,
    get_schedule,
)

__all__ = [
    "DataSourceError",
    "DataUnavailableError",
    "F1DataError",
    "InvalidQueryError",
    "constructor_standings",
    "driver_standings",
    "driver_telemetry",
    "list_race_winners",
    "list_schedule",
    "race_results",
    "season_comparison",
]

# Re-exported so the API can import error types from one place.
F1DataError = f1_data.F1DataError
InvalidQueryError = f1_data.InvalidQueryError
DataSourceError = f1_data.DataSourceError
DataUnavailableError = f1_data.DataUnavailableError

# Default cap on telemetry samples returned per driver, to keep
# responses bounded (FastF1 fastest-laps can carry thousands of points).
DEFAULT_MAX_POINTS = 2000


def _downsample(values: list, max_points: int) -> list:
    """Return at most ``max_points`` evenly spaced samples from a list."""
    if max_points is None or max_points <= 0 or len(values) <= max_points:
        return values
    step = len(values) / max_points
    return [values[int(i * step)] for i in range(max_points)]


def list_schedule(year: int) -> list[dict]:
    return get_schedule(year)


def list_race_winners(year: int) -> list[dict]:
    return get_race_winners(year)


def driver_standings(year: int) -> list[dict]:
    return get_driver_standings(year)


def constructor_standings(year: int) -> list[dict]:
    return get_constructor_standings(year)


def race_results(year: int, round_num: int) -> dict:
    return get_race_results(year, round_num)


def season_comparison(year1: int, year2: int) -> dict:
    return compare_seasons(year1, year2)


def driver_telemetry(
    year: int,
    round_num: int,
    driver_codes: list[str],
    max_points: int = DEFAULT_MAX_POINTS,
) -> dict:
    """Fastest-lap telemetry for several drivers, downsampled for the API.

    Returns a compact per-driver summary (lap time + downsampled series)
    so responses stay a sane size even though the raw data has one point
    per ~300 ms per lap.
    """
    raw = get_multiple_drivers_lap_telemetry(year, round_num, driver_codes)
    event_name = raw[0]["event_name"] if raw else None

    drivers: list[dict[str, Any]] = []
    for tel in raw:
        distance = _downsample(tel["distance"], max_points)
        speed = _downsample(tel["speed"], max_points)
        drivers.append(
            {
                "driver_code": tel["driver_code"],
                "lap_time": tel["lap_time"],
                "n_samples": len(tel["distance"]),
                "returned_samples": len(distance),
                "distance": distance,
                "speed": speed,
            }
        )

    return {
        "year": year,
        "round": round_num,
        "event_name": event_name,
        "max_points": max_points,
        "drivers": drivers,
    }
