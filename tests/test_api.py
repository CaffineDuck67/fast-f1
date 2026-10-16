"""Tests for the FastAPI surface using mocked services (offline)."""

from unittest import mock

from fastapi.testclient import TestClient

import api.routes.races as races_routes
import api.routes.seasons as seasons_routes
from api.main import app
from services import DataSourceError, DataUnavailableError, InvalidQueryError

client = TestClient(app)


def test_health_does_not_touch_providers():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_schedule_ok():
    payload = [
        {
            "round": 1,
            "date": "2023-03-05",
            "event_name": "Bahrain",
            "location": "Sakhir",
            "country": "Bahrain",
        }
    ]
    with mock.patch.object(seasons_routes, "list_schedule", return_value=payload):
        r = client.get("/seasons/2023/schedule")
    assert r.status_code == 200
    assert r.json()[0]["event_name"] == "Bahrain"


def test_schedule_not_found_maps_404():
    with mock.patch.object(
        seasons_routes,
        "list_schedule",
        side_effect=DataUnavailableError("No schedule data available for 2050."),
    ):
        r = client.get("/seasons/2050/schedule")
    assert r.status_code == 404
    assert r.json()["error_type"] == "DataUnavailableError"


def test_schedule_upstream_failure_maps_502():
    with mock.patch.object(
        seasons_routes, "list_schedule", side_effect=DataSourceError("Could not load schedule")
    ):
        r = client.get("/seasons/2023/schedule")
    assert r.status_code == 502
    assert r.json()["error_type"] == "DataSourceError"


def test_invalid_query_maps_400():
    with mock.patch.object(
        seasons_routes, "list_schedule", side_effect=InvalidQueryError("Year out of range")
    ):
        r = client.get("/seasons/2023/schedule")
    assert r.status_code == 400


def test_driver_standings_ok():
    payload = [
        {
            "position": 1,
            "driver": "Max Verstappen",
            "constructor": "Red Bull",
            "points": 575.0,
            "wins": 19,
        }
    ]
    with mock.patch.object(seasons_routes, "driver_standings", return_value=payload):
        r = client.get("/seasons/2023/standings/drivers")
    assert r.status_code == 200
    assert r.json()[0]["points"] == 575.0


def test_compare_returns_summaries():
    fake = {
        "year1": 2022,
        "year2": 2023,
        "data": {
            2022: {
                "summary": {
                    "num_races": 22,
                    "champion_driver": "Verstappen",
                    "champion_driver_points": 454.0,
                    "champion_constructor": "Red Bull",
                    "champion_constructor_points": 759.0,
                    "top_driver_wins": 15,
                }
            },
            2023: {
                "summary": {
                    "num_races": 22,
                    "champion_driver": "Verstappen",
                    "champion_driver_points": 575.0,
                    "champion_constructor": "Red Bull",
                    "champion_constructor_points": 860.0,
                    "top_driver_wins": 19,
                }
            },
        },
        "errors": {},
    }
    with mock.patch.object(seasons_routes, "season_comparison", return_value=fake):
        r = client.get("/seasons/compare?year1=2022&year2=2023")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["2023"]["num_races"] == 22


def test_race_results_ok():
    payload = {
        "event_name": "Miami GP",
        "results": [
            {
                "position": 1,
                "driver_code": "VER",
                "driver": "Max Verstappen",
                "team": "Red Bull",
                "points": 25.0,
                "status": "Finished",
            }
        ],
    }
    with mock.patch.object(races_routes, "race_results", return_value=payload):
        r = client.get("/races/2023/5/results")
    assert r.status_code == 200
    assert r.json()["event_name"] == "Miami GP"


def test_race_results_empty_position_and_points_are_nullable():
    payload = {
        "event_name": "Miami GP",
        "results": [
            {
                "position": None,
                "driver_code": "LEC",
                "driver": "Charles Leclerc",
                "team": "Ferrari",
                "points": None,
                "status": "DNF",
            }
        ],
    }
    with mock.patch.object(races_routes, "race_results", return_value=payload):
        r = client.get("/races/2023/5/results")
    assert r.status_code == 200
    row = r.json()["results"][0]
    assert row["position"] is None
    assert row["points"] is None


def test_telemetry_ok_and_downsampled():
    payload = {
        "year": 2023,
        "round": 5,
        "event_name": "Miami GP",
        "max_points": 2,
        "drivers": [
            {
                "driver_code": "VER",
                "lap_time": "1:30.0",
                "n_samples": 50,
                "returned_samples": 2,
                "distance": [0.0, 25.0],
                "speed": [200.0, 210.0],
            }
        ],
    }
    with mock.patch.object(races_routes, "driver_telemetry", return_value=payload):
        r = client.get("/races/2023/5/telemetry?drivers=VER&max_points=2")
    assert r.status_code == 200
    assert r.json()["drivers"][0]["returned_samples"] == 2


def test_telemetry_requires_drivers():
    r = client.get("/races/2023/5/telemetry")
    assert r.status_code == 422  # missing required query param


def test_bad_year_type_rejected_at_edge():
    r = client.get("/seasons/abc/schedule")
    assert r.status_code == 422
