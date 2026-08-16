

import csv
import json
import os


class ExportError(Exception):
    """Raised when data can't be exported to the requested path."""


def _validate_path(path: str, expected_ext: str):
    ext = os.path.splitext(path)[1].lower()
    if ext != expected_ext:
        raise ExportError(
            f"Expected a '{expected_ext}' file extension for this export, got '{ext or '(none)'}' "
            f"in '{path}'."
        )

    directory = os.path.dirname(path) or "."
    if not os.path.isdir(directory):
        raise ExportError(f"Directory '{directory}' does not exist.")


def export_to_csv(rows: list[dict], path: str):
    """Export a list of flat dicts to a CSV file. All rows must share keys."""
    _validate_path(path, ".csv")

    if not rows:
        raise ExportError("No data to export.")

    fieldnames = list(rows[0].keys())

    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    except OSError as e:
        raise ExportError(f"Failed to write CSV to '{path}': {e}") from e


def export_to_json(data, path: str):
    """Export any JSON-serializable data (list or dict) to a JSON file."""
    _validate_path(path, ".json")

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise ExportError(f"Failed to write JSON to '{path}': {e}") from e
    except TypeError as e:
        raise ExportError(f"Data is not JSON-serializable: {e}") from e