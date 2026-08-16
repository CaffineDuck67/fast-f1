

import argparse
import sys

import fastf1
from fastf1.ergast import Ergast

fastf1.Cache.enable_cache("f1_cache")


def cmd_winners(year: int):
    """List every race winner for a given season."""
    ergast = Ergast()
    schedule = fastf1.get_event_schedule(year, include_testing=False)

    print(f"\n{year} Race Winners\n{'-' * 40}")
    for _, event in schedule.iterrows():
        round_num = event["RoundNumber"]
        gp_name = event["EventName"]
        try:
            results = ergast.get_race_results(season=year, round=round_num).content[0]
            winner = results.iloc[0]
            print(f"Round {round_num:>2} | {gp_name:<30} | {winner['givenName']} {winner['familyName']} ({winner['constructorName']})")
        except Exception:
            print(f"Round {round_num:>2} | {gp_name:<30} | (no data / not yet run)")


def cmd_standings(year: int):
    """Print final driver championship standings for a season."""
    ergast = Ergast()
    standings = ergast.get_driver_standings(season=year).content[0]

    print(f"\n{year} Driver Championship Standings\n{'-' * 50}")
    for _, row in standings.iterrows():
        print(f"{row['position']:>2}. {row['givenName']} {row['familyName']:<20} "
              f"{row['points']:>6} pts  ({row['constructorNames'][0]})")


def cmd_race(year: int, round_num: int):
    """Print full race results for a specific round."""
    session = fastf1.get_session(year, round_num, "R")
    session.load(telemetry=False, weather=False)

    print(f"\n{year} Round {round_num} — {session.event['EventName']} Results\n{'-' * 60}")
    results = session.results[["Position", "Abbreviation", "FullName", "TeamName", "Points", "Status"]]
    for _, row in results.iterrows():
        pos = row["Position"]
        pos_str = f"{int(pos)}" if pos == pos else "DNF"
        print(f"{pos_str:>3} | {row['Abbreviation']} | {row['FullName']:<20} | {row['TeamName']:<20} | {row['Points']:>4} pts | {row['Status']}")


def cmd_schedule(year: int):
    """Print the full race calendar for a season."""
    schedule = fastf1.get_event_schedule(year, include_testing=False)

    print(f"\n{year} Season Schedule\n{'-' * 50}")
    for _, event in schedule.iterrows():
        print(f"Round {event['RoundNumber']:>2} | {event['EventDate'].date()} | {event['EventName']} — {event['Location']}, {event['Country']}")


def main():
    parser = argparse.ArgumentParser(description="F1 season data CLI (powered by FastF1 + Ergast)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_winners = sub.add_parser("winners", help="List all race winners for a season")
    p_winners.add_argument("year", type=int)

    p_standings = sub.add_parser("standings", help="Show final driver standings for a season")
    p_standings.add_argument("year", type=int)

    p_race = sub.add_parser("race", help="Show full results for a specific race")
    p_race.add_argument("year", type=int)
    p_race.add_argument("round", type=int)

    p_schedule = sub.add_parser("schedule", help="Show the full calendar for a season")
    p_schedule.add_argument("year", type=int)

    args = parser.parse_args()

    if args.command == "winners":
        cmd_winners(args.year)
    elif args.command == "standings":
        cmd_standings(args.year)
    elif args.command == "race":
        cmd_race(args.year, args.round)
    elif args.command == "schedule":
        cmd_schedule(args.year)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)