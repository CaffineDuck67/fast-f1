"""Tests for services/ — downsampling and telemetry shaping (mocked)."""

from unittest import mock

import services


def test_downsample_no_op_when_short():
    vals = [1, 2, 3]
    assert services._downsample(vals, 10) == vals


def test_downsample_bounded_and_evenly_spaced():
    vals = list(range(100))
    out = services._downsample(vals, 10)
    assert len(out) == 10
    assert out[0] == 0
    assert out[-1] <= 99


def test_downsample_unbounded():
    vals = list(range(50))
    assert services._downsample(vals, 0) == vals
    assert services._downsample(vals, None) == vals


def test_driver_telemetry_shapes_and_downsamples():
    raw = [
        {
            "driver_code": "VER",
            "lap_time": "1:30.000",
            "event_name": "Miami GP",
            "distance": [float(i) for i in range(50)],
            "speed": [200.0] * 50,
            "throttle": [50.0] * 50,
            "brake": [0.0] * 50,
            "time": [float(i) for i in range(50)],
        }
    ]
    with mock.patch.object(services, "get_multiple_drivers_lap_telemetry", return_value=raw):
        out = services.driver_telemetry(2023, 5, ["VER"], max_points=10)

    assert out["event_name"] == "Miami GP"
    d = out["drivers"][0]
    assert d["n_samples"] == 50
    assert d["returned_samples"] == 10
    assert len(d["distance"]) == 10
    assert len(d["speed"]) == 10


def test_reexports_error_types():
    import f1_data

    assert services.InvalidQueryError is f1_data.InvalidQueryError
    assert services.DataSourceError is f1_data.DataSourceError
    assert services.DataUnavailableError is f1_data.DataUnavailableError
    assert issubclass(services.InvalidQueryError, services.F1DataError)
