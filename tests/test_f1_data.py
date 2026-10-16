"""Tests for f1_data.py with mocked FastF1/Ergast (fully offline)."""

from unittest import mock

import pandas as pd
import pytest

import f1_data
from f1_data import (
    DataSourceError,
    DataUnavailableError,
    InvalidQueryError,
)


def _schedule_df(with_nat=False):
    dates = [pd.Timestamp("2023-03-05"), pd.NaT if with_nat else pd.Timestamp("2023-03-19")]
    return pd.DataFrame(
        {
            "RoundNumber": [1, 2],
            "EventDate": dates,
            "EventName": ["Bahrain", "Saudi Arabia"],
            "Location": ["Sakhir", "Jeddah"],
            "Country": ["Bahrain", "Saudi Arabia"],
        }
    )


# --- validation (no I/O) ------------------------------------------------


def test_year_too_low():
    with pytest.raises(InvalidQueryError):
        f1_data.get_schedule(1800)


def test_year_not_int():
    with pytest.raises(InvalidQueryError):
        f1_data.get_schedule("2023")


def test_round_zero():
    with pytest.raises(InvalidQueryError):
        f1_data.get_race_results(2023, 0)


def test_empty_driver_codes():
    with pytest.raises(InvalidQueryError):
        f1_data.get_multiple_drivers_lap_telemetry(2023, 5, [])


# --- schedule -----------------------------------------------------------


def test_get_schedule_ok():
    with mock.patch.object(f1_data.fastf1, "get_event_schedule", return_value=_schedule_df()):
        events = f1_data.get_schedule(2023)
    assert events[0]["round"] == 1
    assert events[0]["date"] == "2023-03-05"
    assert events[0]["event_name"] == "Bahrain"


def test_get_schedule_handles_nat_date():
    with mock.patch.object(
        f1_data.fastf1, "get_event_schedule", return_value=_schedule_df(with_nat=True)
    ):
        events = f1_data.get_schedule(2023)
    assert events[1]["date"] == ""  # no crash on NaT


def test_get_schedule_empty():
    with mock.patch.object(f1_data.fastf1, "get_event_schedule", return_value=pd.DataFrame()):
        with pytest.raises(DataUnavailableError):
            f1_data.get_schedule(2050)


def test_get_schedule_source_error():
    with mock.patch.object(f1_data.fastf1, "get_event_schedule", side_effect=RuntimeError("boom")):
        with pytest.raises(DataSourceError):
            f1_data.get_schedule(2023)


# --- standings ----------------------------------------------------------


def test_driver_standings_ok():
    df = pd.DataFrame(
        [
            {
                "position": 1,
                "givenName": "Max",
                "familyName": "Verstappen",
                "constructorNames": ["Red Bull"],
                "points": 575,
                "wins": 19,
            }
        ]
    )
    ergast = mock.MagicMock()
    ergast.get_driver_standings.return_value.content = [df]
    with mock.patch.object(f1_data, "_ergast", ergast):
        out = f1_data.get_driver_standings(2023)
    assert out[0]["driver"] == "Max Verstappen"
    assert out[0]["points"] == 575.0
    assert out[0]["constructor"] == "Red Bull"


def test_driver_standings_empty():
    ergast = mock.MagicMock()
    ergast.get_driver_standings.return_value.content = []
    with mock.patch.object(f1_data, "_ergast", ergast):
        with pytest.raises(DataUnavailableError):
            f1_data.get_driver_standings(2023)


def test_driver_standings_source_error():
    ergast = mock.MagicMock()
    ergast.get_driver_standings.side_effect = ConnectionError("down")
    with mock.patch.object(f1_data, "_ergast", ergast):
        with pytest.raises(DataSourceError):
            f1_data.get_driver_standings(2023)


def test_constructor_standings_ok():
    df = pd.DataFrame(
        [
            {
                "position": 1,
                "constructorName": "Red Bull",
                "points": 860,
                "wins": 21,
            }
        ]
    )
    ergast = mock.MagicMock()
    ergast.get_constructor_standings.return_value.content = [df]
    with mock.patch.object(f1_data, "_ergast", ergast):
        out = f1_data.get_constructor_standings(2023)
    assert out[0]["constructor"] == "Red Bull"


# --- race results -------------------------------------------------------


def test_race_results_ok_and_nan_points():
    results = pd.DataFrame(
        [
            {
                "Position": 1,
                "Abbreviation": "VER",
                "FullName": "Max Verstappen",
                "TeamName": "Red Bull",
                "Points": 25.0,
                "Status": "Finished",
            },
            {
                "Position": float("nan"),
                "Abbreviation": "LEC",
                "FullName": "Charles Leclerc",
                "TeamName": "Ferrari",
                "Points": float("nan"),
                "Status": "DNF",
            },
        ]
    )
    session = mock.MagicMock()
    session.results = results
    session.event = {"EventName": "Miami GP"}
    with mock.patch.object(f1_data.fastf1, "get_session", return_value=session):
        out = f1_data.get_race_results(2023, 5)
    rows = out["results"]
    assert rows[0]["position"] == 1
    assert rows[0]["points"] == 25.0
    assert rows[1]["position"] is None  # NaN -> None
    assert rows[1]["points"] is None  # NaN -> None (regression)
    assert out["event_name"] == "Miami GP"


def test_race_results_empty():
    session = mock.MagicMock()
    session.results = pd.DataFrame()
    with mock.patch.object(f1_data.fastf1, "get_session", return_value=session):
        with pytest.raises(DataUnavailableError):
            f1_data.get_race_results(2023, 5)


# --- compare ------------------------------------------------------------


def test_compare_seasons_handles_partial_data():
    with (
        mock.patch.object(
            f1_data, "get_driver_standings", side_effect=DataUnavailableError("no data")
        ),
        mock.patch.object(f1_data, "get_constructor_standings", return_value=[]),
        mock.patch.object(f1_data, "get_schedule", return_value=[]),
    ):
        result = f1_data.compare_seasons(2022, 2023)
    assert 2022 in result["errors"]
    assert result["data"][2023]["summary"]["num_races"] == 0
    assert result["data"][2023]["summary"]["champion_driver"] == "N/A"
