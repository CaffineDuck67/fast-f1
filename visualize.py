"""
visualize.py — matplotlib plotting for race telemetry.

Kept separate from display.py (terminal/rich output) since this
produces image files rather than terminal output. No data-fetching
happens here — functions take telemetry dicts as returned by
f1_data.get_driver_lap_telemetry().
"""

import matplotlib.pyplot as plt


class VisualizeError(Exception):
    """Raised when a plot can't be generated or saved."""


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
    """
    if not telemetry_list:
        raise VisualizeError("No telemetry data to plot.")

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