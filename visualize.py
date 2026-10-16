"""
visualize.py — matplotlib plotting for race telemetry.

Kept separate from display.py (terminal/rich output) since this
produces image files rather than terminal output. No data-fetching
happens here — functions take telemetry dicts as returned by
f1_data.get_driver_lap_telemetry() / get_multiple_drivers_lap_telemetry().
"""

import matplotlib.pyplot as plt
import numpy as np


class VisualizeError(Exception):
    """Raised when a plot can't be generated or saved."""


def _validate_series(tel: dict, require_time: bool = False):
    """Validate one telemetry dict before plotting.

    Ensures the required keys exist, are non-empty, share a length, and
    that distance/numeric values are usable. Raises VisualizeError with
    an actionable message otherwise.
    """
    code = tel.get("driver_code", "?")
    keys = ["distance", "speed"]
    if require_time:
        keys.append("time")

    for key in ("distance", "speed", "throttle", "brake") + (("time",) if require_time else ()):
        if key not in tel or tel[key] is None:
            raise VisualizeError(f"Driver {code}: missing '{key}' telemetry.")

    distance = list(tel["distance"])
    if len(distance) == 0:
        raise VisualizeError(f"Driver {code}: empty telemetry.")

    for key in keys:
        if len(tel[key]) != len(distance):
            raise VisualizeError(
                f"Driver {code}: '{key}' length ({len(tel[key])}) does not "
                f"match 'distance' length ({len(distance)})."
            )

    try:
        dist_arr = np.asarray(distance, dtype=float)
    except (TypeError, ValueError) as e:
        raise VisualizeError(f"Driver {code}: non-numeric distance values ({e}).") from e

    if not np.all(np.diff(dist_arr) >= 0):
        raise VisualizeError(f"Driver {code}: distance values are not monotonically increasing.")


def _overlapping_mask(ref_distance, distance):
    """Return the reference mask limited to the shared distance range.

    Guards against interpolation over a range where one driver has no
    samples (which would silently clamp to endpoints and mislead).
    """
    common_max = min(float(ref_distance.max()), float(distance.max()))
    common_min = max(float(ref_distance.min()), float(distance.min()))
    if common_max <= common_min:
        return None
    return (ref_distance <= common_max) & (ref_distance >= common_min)


def plot_speed_comparison(
    year: int,
    round_num: int,
    event_name: str,
    telemetry_list: list[dict],
    output_path: str,
):
    """
    Plot speed-vs-distance for one or more drivers' fastest laps on the
    same axes and save to output_path.

    Kept as-is for a quick, single-panel view. For throttle/brake and
    a gap-over-distance trace, use plot_telemetry_comparison instead.
    """
    if not telemetry_list:
        raise VisualizeError("No telemetry data to plot.")

    for tel in telemetry_list:
        _validate_series(tel)

    try:
        plt.figure(figsize=(12, 6))

        for tel in telemetry_list:
            label = f"{tel['driver_code']} ({tel['lap_time']})"
            plt.plot(tel["distance"], tel["speed"], label=label, linewidth=1.8)

        plt.xlabel("Distance (m)")
        plt.ylabel("Speed (km/h)")
        plt.title(f"{year} Round {round_num} — {event_name}\nFastest Lap Speed Comparison")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
    except Exception as e:
        raise VisualizeError(f"Failed to generate/save plot: {e}") from e


def plot_telemetry_comparison(
    year: int,
    round_num: int,
    event_name: str,
    telemetry_list: list[dict],
    output_path: str,
    show_delta: bool = True,
):
    """
    Plot speed, throttle, and brake vs. distance for one or more
    drivers' fastest laps, stacked on shared axes. Optionally adds a
    time-delta panel (gap to the first driver in the list, in seconds,
    over distance) — the fastest way to see exactly where time is
    won or lost on track.

    telemetry_list entries must include 'distance', 'speed',
    'throttle', 'brake', and (if show_delta) 'time' — a list of
    per-sample elapsed lap time in seconds, same length as 'distance'.
    """
    if not telemetry_list:
        raise VisualizeError("No telemetry data to plot.")

    has_time = show_delta and all("time" in tel for tel in telemetry_list)
    if show_delta and not has_time:
        show_delta = False  # silently degrade rather than fail the whole plot

    for tel in telemetry_list:
        _validate_series(tel, require_time=has_time)

    n_panels = 4 if show_delta else 3
    try:
        height_ratios = [3, 1, 1, 1.5] if show_delta else [3, 1, 1]
        fig, axes = plt.subplots(
            n_panels,
            1,
            figsize=(12, 4 + 2.2 * n_panels),
            sharex=True,
            gridspec_kw={"height_ratios": height_ratios},
        )
        ax_speed, ax_throttle, ax_brake = axes[0], axes[1], axes[2]

        for tel in telemetry_list:
            label = f"{tel['driver_code']} ({tel['lap_time']})"
            ax_speed.plot(tel["distance"], tel["speed"], label=label, linewidth=1.8)
            ax_throttle.plot(tel["distance"], tel["throttle"], linewidth=1.2)
            ax_brake.plot(tel["distance"], tel["brake"], linewidth=1.2)

        ax_speed.set_ylabel("Speed (km/h)")
        ax_speed.legend(loc="lower right")
        ax_speed.grid(True, alpha=0.3)

        ax_throttle.set_ylabel("Throttle (%)")
        ax_throttle.set_ylim(-5, 105)
        ax_throttle.grid(True, alpha=0.3)

        ax_brake.set_ylabel("Brake")
        ax_brake.grid(True, alpha=0.3)

        if show_delta:
            ax_delta = axes[3]
            reference = telemetry_list[0]
            ref_distance = np.array(reference["distance"])
            ref_time = np.array(reference["time"])

            for tel in telemetry_list[1:]:
                distance = np.array(tel["distance"])
                time = np.array(tel["time"])
                # Interpolate this driver's time onto the reference's
                # distance grid so both traces can be subtracted directly.
                mask = _overlapping_mask(ref_distance, distance)
                if mask is None or not mask.any():
                    continue  # no shared distance range -> skip misleading delta
                interp_time = np.interp(ref_distance[mask], distance, time)
                delta = interp_time - ref_time[mask]
                ax_delta.plot(
                    ref_distance[mask],
                    delta,
                    label=f"{tel['driver_code']} vs {reference['driver_code']}",
                    linewidth=1.6,
                )

            ax_delta.axhline(0, color="grey", linewidth=0.8, linestyle="--")
            ax_delta.set_ylabel("Gap (s)\n(+ = behind ref)")
            ax_delta.legend(loc="best")
            ax_delta.grid(True, alpha=0.3)

        axes[-1].set_xlabel("Distance (m)")
        fig.suptitle(f"{year} Round {round_num} — {event_name}\nFastest Lap Telemetry Comparison")
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
    except Exception as e:
        raise VisualizeError(f"Failed to generate/save plot: {e}") from e
