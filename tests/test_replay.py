"""Tests for replay.py pure logic — no pygame or window required."""

import pytest

import replay


@pytest.fixture
def data():
    return {
        "event_name": "Miami GP",
        "driver_tracks": {
            "VER": {"t": [0.0, 1.0, 2.0], "x": [0.0, 10.0, 20.0], "y": [0.0, 5.0, 10.0]},
            "LEC": {"t": [0.0, 1.0, 2.0], "x": [1.0, 11.0, 21.0], "y": [0.0, 5.0, 10.0]},
        },
        "track_outline": {"x": [0.0, 1.0, 2.0], "y": [0.0, 1.0, 0.0]},
        "driver_laps_info": {
            "VER": [
                {"lap_number": 1, "end_time": 1.0, "position": 2},
                {"lap_number": 2, "end_time": 2.0, "position": 1},
            ],
            "LEC": [
                {"lap_number": 1, "end_time": 1.0, "position": 1},
                {"lap_number": 2, "end_time": 2.0, "position": 2},
            ],
        },
        "grid_positions": {"VER": 3, "LEC": 1},
        "colors": {"VER": "#1E5BC6", "LEC": "#DA1111"},
        "x_range": (0.0, 21.0),
        "y_range": (0.0, 10.0),
        "weather": [
            {
                "t": 0.0,
                "track_temp": 40.0,
                "air_temp": 30.0,
                "humidity": 50.0,
                "wind_speed": 5.0,
                "rainfall": False,
            }
        ],
        "total_laps": 57,
        "max_time": 2.0,
    }


def test_hex_to_rgb_valid():
    assert replay._hex_to_rgb("#1E5BC6") == (0x1E, 0x5B, 0xC6)


def test_hex_to_rgb_invalid_falls_back():
    assert replay._hex_to_rgb("not-a-hex") == (255, 255, 255)


def test_format_time():
    assert replay._format_time(75.0) == "01:15"


def test_interp_before_start_returns_first(data):
    r = replay.RaceReplay(data)
    assert r._interp_position("VER", -5.0) == (0.0, 0.0)


def test_interp_after_end_returns_last(data):
    r = replay.RaceReplay(data)
    assert r._interp_position("VER", 99.0) == (20.0, 10.0)


def test_interp_midpoint(data):
    r = replay.RaceReplay(data)
    x, y = r._interp_position("VER", 1.5)
    assert x == pytest.approx(15.0)
    assert y == pytest.approx(7.5)


def test_interp_unknown_driver(data):
    r = replay.RaceReplay(data)
    assert r._interp_position("NOR", 1.0) is None


def test_current_lap_and_position_uses_grid_before_first_lap(data):
    r = replay.RaceReplay(data)
    lap, pos = r._current_lap_and_position("VER", 0.0)
    assert lap == 1
    assert pos == 3  # grid fallback


def test_current_lap_and_position_after_lap(data):
    r = replay.RaceReplay(data)
    lap, pos = r._current_lap_and_position("VER", 2.0)
    assert lap == 3  # completed lap 2 -> on lap 3
    assert pos == 1


def test_standings_sorted_by_position(data):
    r = replay.RaceReplay(data)
    rows, leader_lap = r._standings(2.0)
    positions = [row[0] for row in rows]
    assert positions == sorted(positions)
    assert leader_lap >= 1


def test_run_replay_rejects_empty_data():
    with pytest.raises(replay.ReplayError, match="No replay data"):
        replay.run_replay({}, initial_speed=1.0)


def test_run_replay_rejects_bad_speed(data):
    with pytest.raises(replay.ReplayError, match="Invalid playback speed"):
        replay.run_replay(data, initial_speed=0)


def test_run_replay_reports_missing_pygame(data, monkeypatch):
    # On an environment without pygame, run_replay must raise a clear
    # ReplayError rather than a bare ImportError.
    monkeypatch.setattr(replay, "pygame", None)
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *a, **k):
        if name == "pygame":
            raise ImportError("no pygame")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    with pytest.raises(replay.ReplayError, match="pygame"):
        replay.run_replay(data, initial_speed=1.0)
