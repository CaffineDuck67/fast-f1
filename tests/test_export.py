"""Tests for export.py (CSV/JSON), which need no network access."""

import json

import pytest

import export


def test_csv_roundtrip(tmp_path):
    rows = [
        {"position": 1, "driver": "Max Verstappen", "points": 575.0},
        {"position": 2, "driver": "Sergio Perez", "points": 285.0},
    ]
    path = tmp_path / "out.csv"
    export.export_to_csv(rows, str(path))

    text = path.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "position,driver,points"
    assert "Max Verstappen" in text
    assert len(text.strip().splitlines()) == 3  # header + 2 rows


def test_csv_handles_uneven_keys(tmp_path):
    # Regression: rows with differing keys used to crash (extrasaction=raise,
    # fieldnames taken only from row[0]).
    rows = [
        {"round": 1, "event_name": "Bahrain", "driver": "VER"},
        {"round": 2, "event_name": "Saudi Arabia", "driver": None, "extra": "x"},
    ]
    path = tmp_path / "uneven.csv"
    export.export_to_csv(rows, str(path))

    parsed = list(csv_dictreader(path))
    assert set(parsed[0].keys()) == {"round", "event_name", "driver", "extra"}
    assert parsed[1]["extra"] == "x"


def test_csv_rejects_empty(tmp_path):
    with pytest.raises(export.ExportError):
        export.export_to_csv([], str(tmp_path / "empty.csv"))


def test_csv_rejects_non_dict_rows(tmp_path):
    with pytest.raises(export.ExportError):
        export.export_to_csv([1, 2, 3], str(tmp_path / "bad.csv"))


def test_wrong_extension_rejected(tmp_path):
    with pytest.raises(export.ExportError):
        export.export_to_csv([{"a": 1}], str(tmp_path / "out.txt"))


def test_missing_directory_rejected():
    with pytest.raises(export.ExportError):
        export.export_to_csv([{"a": 1}], "/no/such/dir/out.csv")


def test_empty_path_rejected():
    with pytest.raises(export.ExportError):
        export.export_to_json({"a": 1}, "")


def test_json_roundtrip(tmp_path):
    data = {"year": 2023, "champion": "Verstappen", "points": 575.0}
    path = tmp_path / "out.json"
    export.export_to_json(data, str(path))
    assert json.loads(path.read_text(encoding="utf-8")) == data


def test_json_non_serializable(tmp_path):
    class Custom:
        pass

    path = tmp_path / "bad.json"
    with pytest.raises(export.ExportError):
        export.export_to_json({"x": Custom()}, str(path))


def test_no_temp_file_left_behind_on_failure(tmp_path):
    # A failed JSON write must not leave a stray .tmp file in the dir.
    class Custom:
        pass

    with pytest.raises(export.ExportError):
        export.export_to_json({"x": Custom()}, str(tmp_path / "bad.json"))
    assert list(tmp_path.glob("*.tmp")) == []


def test_csv_leaves_no_temp_on_success(tmp_path):
    export.export_to_csv([{"a": 1}], str(tmp_path / "ok.csv"))
    assert list(tmp_path.glob("*.tmp")) == []


def csv_dictreader(path):
    import csv

    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
