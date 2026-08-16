

import fastf1
from fastf1.ergast import Ergast

_ergast = Ergast()


class F1DataError(Exception):
    """Raised when requested F1 data can't be retrieved or doesn't exist."""


def get_schedule(year: int) -> list[dict]:
    """Return the full race calendar for a season."""
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except Exception as e:
        raise F1DataError(f"Could not load schedule for {year}: {e}") from e

    if schedule.empty:
        raise F1DataError(f"No schedule data available for {year}.")

    return [
        {
            "round": int(row["RoundNumber"]),
            "date": str(row["EventDate"].date()),
            "event_name": row["EventName"],
            "location": row["Location"],
            "country": row["Country"],
        }
        for _, row in schedule.iterrows()
    ]


def get_race_winners(year: int) -> list[dict]:
    """Return the winner of every race in a season."""
    schedule = get_schedule(year)
    winners = []

    for event in schedule:
        round_num = event["round"]
        try:
            results = _ergast.get_race_results(season=year, round=round_num).content
            if not results:
                raise F1DataError("no results")
            winner = results[0].iloc[0]
            winners.append({
                "round": round_num,
                "event_name": event["event_name"],
                "driver": f"{winner['givenName']} {winner['familyName']}",
                "constructor": winner["constructorName"],
            })
        except Exception:
            winners.append({
                "round": round_num,
                "event_name": event["event_name"],
                "driver": None,
                "constructor": None,
            })

    return winners


def get_driver_standings(year: int) -> list[dict]:
    """Return final (or current) driver championship standings for a season."""
    try:
        standings = _ergast.get_driver_standings(season=year).content
    except Exception as e:
        raise F1DataError(f"Could not load driver standings for {year}: {e}") from e

    if not standings:
        raise F1DataError(f"No driver standings available for {year}.")

    df = standings[0]
    return [
        {
            "position": int(row["position"]),
            "driver": f"{row['givenName']} {row['familyName']}",
            "constructor": row["constructorNames"][0] if row["constructorNames"] else "N/A",
            "points": float(row["points"]),
            "wins": int(row["wins"]),
        }
        for _, row in df.iterrows()
    ]


def get_constructor_standings(year: int) -> list[dict]:
    """Return final (or current) constructor championship standings for a season."""
    try:
        standings = _ergast.get_constructor_standings(season=year).content
    except Exception as e:
        raise F1DataError(f"Could not load constructor standings for {year}: {e}") from e

    if not standings:
        raise F1DataError(f"No constructor standings available for {year}.")

    df = standings[0]
    return [
        {
            "position": int(row["position"]),
            "constructor": row["constructorName"],
            "points": float(row["points"]),
            "wins": int(row["wins"]),
        }
        for _, row in df.iterrows()
    ]


def get_race_results(year: int, round_num: int) -> dict:
    """Return full results for a specific race, plus the event name."""
    try:
        session = fastf1.get_session(year, round_num, "R")
        session.load(telemetry=False, weather=False)
    except Exception as e:
        raise F1DataError(f"Could not load race {year} round {round_num}: {e}") from e

    if session.results is None or session.results.empty:
        raise F1DataError(f"No results available for {year} round {round_num}.")

    results = []
    for _, row in session.results.iterrows():
        pos = row["Position"]
        results.append({
            "position": int(pos) if pos == pos else None,  # NaN check
            "driver_code": row["Abbreviation"],
            "driver": row["FullName"],
            "team": row["TeamName"],
            "points": float(row["Points"]),
            "status": row["Status"],
        })

    return {
        "event_name": session.event["EventName"],
        "results": results,
    }


def compare_seasons(year1: int, year2: int) -> dict:
    """Build a side-by-side comparison of two seasons' key stats."""
    errors = {}
    data = {}

    for year in (year1, year2):
        season_info = {}
        try:
            season_info["driver_standings"] = get_driver_standings(year)
        except F1DataError as e:
            errors[year] = str(e)
            season_info["driver_standings"] = []

        try:
            season_info["constructor_standings"] = get_constructor_standings(year)
        except F1DataError as e:
            errors.setdefault(year, str(e))
            season_info["constructor_standings"] = []

        try:
            season_info["schedule"] = get_schedule(year)
        except F1DataError as e:
            errors.setdefault(year, str(e))
            season_info["schedule"] = []

        drivers = season_info["driver_standings"]
        constructors = season_info["constructor_standings"]

        season_info["summary"] = {
            "num_races": len(season_info["schedule"]),
            "champion_driver": drivers[0]["driver"] if drivers else "N/A",
            "champion_driver_points": drivers[0]["points"] if drivers else None,
            "champion_constructor": constructors[0]["constructor"] if constructors else "N/A",
            "champion_constructor_points": constructors[0]["points"] if constructors else None,
            "top_driver_wins": drivers[0]["wins"] if drivers else None,
        }

        data[year] = season_info

    return {
        "year1": year1,
        "year2": year2,
        "data": data,
        "errors": errors,
    }