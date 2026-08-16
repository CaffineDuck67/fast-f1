"""
main.py — F1 CLI entry point.

Commands:
    winners <year>                      List every race winner for a season
    standings <year>                    Driver championship standings
    constructors <year>                 Constructor championship standings
    race <year> <round>                 Full results for a specific race
    schedule <year>                     Full season calendar
    compare <year1> <year2>             Side-by-side comparison of two seasons
    visualize <year> <round> <drivers>  Plot fastest-lap speed comparison
    replay <year> <round>               Animated race replay with leaderboard

Any of the above accept:
    --csv <path>    export result as CSV
    --json <path>   export result as JSON

Example:
    python main.py standings 2023 --csv standings.csv
    python main.py race 2023 5 --json race5.json
    python main.py compare 2022 2023
"""

import argparse
import sys

import fastf1

import display
import export
import visualize
import replay
from f1_data import (
    F1DataError,
    get_schedule,
    get_race_winners,
    get_driver_standings,
    get_constructor_standings,
    get_race_results,
    get_driver_lap_telemetry,
    get_race_replay_data,
    compare_seasons,
)

fastf1.Cache.enable_cache("f1_cache")


def _handle_export(data, args, label: str):
    """Shared export handling for --csv / --json flags."""
    try:
        if getattr(args, "csv", None):
            export.export_to_csv(data, args.csv)
            display.print_success(f"Exported {label} to '{args.csv}'")
        if getattr(args, "json", None):
            export.export_to_json(data, args.json)
            display.print_success(f"Exported {label} to '{args.json}'")
    except export.ExportError as e:
        display.print_error(str(e))


def cmd_winners(args):
    winners = get_race_winners(args.year)
    display.print_winners(args.year, winners)
    _handle_export(winners, args, "race winners")


def cmd_standings(args):
    standings = get_driver_standings(args.year)
    display.print_driver_standings(args.year, standings)
    _handle_export(standings, args, "driver standings")


def cmd_constructors(args):
    standings = get_constructor_standings(args.year)
    display.print_constructor_standings(args.year, standings)
    _handle_export(standings, args, "constructor standings")


def cmd_race(args):
    race = get_race_results(args.year, args.round)
    display.print_race_results(args.year, args.round, race["event_name"], race["results"])
    _handle_export(race["results"], args, "race results")


def cmd_schedule(args):
    schedule = get_schedule(args.year)
    display.print_schedule(args.year, schedule)
    _handle_export(schedule, args, "schedule")


def cmd_compare(args):
    comparison = compare_seasons(args.year1, args.year2)
    display.print_comparison(comparison)

    # Flatten for export: one row per year's summary
    export_rows = []
    for year, season in comparison["data"].items():
        row = {"year": year, **season["summary"]}
        export_rows.append(row)
    _handle_export(export_rows, args, "season comparison")


def cmd_visualize(args):
    telemetry_list = []
    for driver_code in args.drivers:
        telemetry_list.append(
            get_driver_lap_telemetry(args.year, args.round, driver_code.upper())
        )

    event_name = telemetry_list[0]["event_name"]

    try:
        visualize.plot_speed_comparison(
            args.year, args.round, event_name, telemetry_list, args.output
        )
    except visualize.VisualizeError as e:
        display.print_error(str(e))
        return

    display.print_success(f"Saved speed comparison plot to '{args.output}'")
    for tel in telemetry_list:
        console_line = f"  {tel['driver_code']}: fastest lap {tel['lap_time']}"
        display.console.print(console_line)


def cmd_replay(args):
    display.console.print(f"[dim]Loading position data for {args.year} round {args.round}... this can take a minute.[/dim]")
    data = get_race_replay_data(args.year, args.round)
    display.print_success(f"Loaded {data['event_name']} — launching replay window (close it or press ESC to exit)")
    replay.run_replay(data, initial_speed=args.speed)


def _add_export_flags(parser):
    parser.add_argument("--csv", metavar="PATH", help="Export result to a CSV file")
    parser.add_argument("--json", metavar="PATH", help="Export result to a JSON file")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="F1 season data CLI — powered by FastF1 + Ergast",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_winners = sub.add_parser("winners", help="List all race winners for a season")
    p_winners.add_argument("year", type=int)
    _add_export_flags(p_winners)
    p_winners.set_defaults(func=cmd_winners)

    p_standings = sub.add_parser("standings", help="Show driver championship standings")
    p_standings.add_argument("year", type=int)
    _add_export_flags(p_standings)
    p_standings.set_defaults(func=cmd_standings)

    p_constructors = sub.add_parser("constructors", help="Show constructor championship standings")
    p_constructors.add_argument("year", type=int)
    _add_export_flags(p_constructors)
    p_constructors.set_defaults(func=cmd_constructors)

    p_race = sub.add_parser("race", help="Show full results for a specific race")
    p_race.add_argument("year", type=int)
    p_race.add_argument("round", type=int)
    _add_export_flags(p_race)
    p_race.set_defaults(func=cmd_race)

    p_schedule = sub.add_parser("schedule", help="Show the full calendar for a season")
    p_schedule.add_argument("year", type=int)
    _add_export_flags(p_schedule)
    p_schedule.set_defaults(func=cmd_schedule)

    p_compare = sub.add_parser("compare", help="Compare two seasons side by side")
    p_compare.add_argument("year1", type=int)
    p_compare.add_argument("year2", type=int)
    _add_export_flags(p_compare)
    p_compare.set_defaults(func=cmd_compare)

    p_visualize = sub.add_parser(
        "visualize", help="Plot fastest-lap speed comparison for two or more drivers"
    )
    p_visualize.add_argument("year", type=int)
    p_visualize.add_argument("round", type=int)
    p_visualize.add_argument("drivers", nargs="+", help="Driver codes, e.g. VER LEC HAM")
    p_visualize.add_argument(
        "--output", "-o", default="speed_comparison.png", metavar="PATH",
        help="Output image path (default: speed_comparison.png)",
    )
    p_visualize.set_defaults(func=cmd_visualize)

    p_replay = sub.add_parser(
        "replay", help="Launch an animated race replay with live leaderboard and weather"
    )
    p_replay.add_argument("year", type=int)
    p_replay.add_argument("round", type=int)
    p_replay.add_argument(
        "--speed", type=float, default=1.0,
        help="Initial playback speed multiplier (default: 1.0)",
    )
    p_replay.set_defaults(func=cmd_replay)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
    except F1DataError as e:
        display.print_error(str(e))
        sys.exit(1)
    except Exception as e:
        display.print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()