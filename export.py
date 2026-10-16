import csv
import json
import os
import tempfile


class ExportError(Exception):
    """Raised when data can't be exported to the requested path."""


def _validate_path(path: str, expected_ext: str):
    if not path or not isinstance(path, str):
        raise ExportError("An export path must be provided.")

    ext = os.path.splitext(path)[1].lower()
    if ext != expected_ext:
        raise ExportError(
            f"Expected a '{expected_ext}' file extension for this export, got '{ext or '(none)'}' "
            f"in '{path}'."
        )

    directory = os.path.dirname(path) or "."
    if not os.path.isdir(directory):
        raise ExportError(f"Directory '{directory}' does not exist.")


def _atomic_write(path: str, write_fn):
    """Write to a temp file in the same directory, then atomically replace.

    Avoids leaving a partially written / corrupted file if the write
    fails midway.
    """
    directory = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    completed = False
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            write_fn(f)
        os.replace(tmp_path, path)
        completed = True
    except OSError as e:
        raise ExportError(f"Failed to write to '{path}': {e}") from e
    finally:
        if not completed:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def export_to_csv(rows: list[dict], path: str):
    """Export a list of dicts to a CSV file.

    Rows need not share an identical key set: the union of all keys
    (first-seen order preserved) becomes the header, and missing values
    are written as empty cells.
    """
    _validate_path(path, ".csv")

    if not rows:
        raise ExportError("No data to export.")

    if not all(isinstance(r, dict) for r in rows):
        raise ExportError("CSV export expects a list of dict rows.")

    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    def _write(f):
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    _atomic_write(path, _write)


def export_to_json(data, path: str):
    """Export any JSON-serializable data (list or dict) to a JSON file."""
    _validate_path(path, ".json")

    def _write(f):
        json.dump(data, f, indent=2, ensure_ascii=False)

    try:
        _atomic_write(path, _write)
    except ExportError:
        raise
    except TypeError as e:
        raise ExportError(f"Data is not JSON-serializable: {e}") from e
