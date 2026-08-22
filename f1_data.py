"""
f1_data.py — data-access layer.

Every function here talks to FastF1 / Ergast and returns plain Python
data structures (lists of dicts). No printing, no formatting, no
export logic lives here — that keeps this module easy to test and
reuse regardless of how the data is presented.
"""

import logging

import fastf1
import pandas as pd
from fastf1.ergast import Ergast

logger = logging.getLogger(__name__)

_ergast = Ergast()


class F1DataError(Exception):
    """Raised when requested F1 data can't be retrieved or doesn't exist."""


def _is_na(value) -> bool:
    """Single, consistent NaN/None check used everywhere in this module."""
    return value is None or pd.isna(value)


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
        except Exception as e:
            logger.warning(
                "Could not fetch winner for %s round %s (%s): %s",
                year, round_num, event["event_name"], e,
            )
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
            "position": None if _is_na(pos) else int(pos),
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


def get_driver_lap_telemetry(year: int, round_num: int, driver_code: str) -> dict:
    """Return fastest-lap telemetry (distance, speed, throttle, brake) for one driver.

    For more than one driver in the same race, prefer
    `get_multiple_drivers_lap_telemetry` — it loads the session once
    instead of once per driver.
    """
    return get_multiple_drivers_lap_telemetry(year, round_num, [driver_code])[0]


def get_multiple_drivers_lap_telemetry(
    year: int, round_num: int, driver_codes: list[str]
) -> list[dict]:
    """Return fastest-lap telemetry for one or more drivers, loading the
    session only once regardless of how many drivers are requested.
    """
    try:
        session = fastf1.get_session(year, round_num, "R")
        session.load(telemetry=True, weather=False)
    except Exception as e:
        raise F1DataError(f"Could not load race {year} round {round_num}: {e}") from e

    results = []
    for code in driver_codes:
        driver_laps = session.laps.pick_drivers(code)
        if driver_laps.empty:
            raise F1DataError(f"No laps found for driver '{code}' in {year} round {round_num}.")

        fastest_lap = driver_laps.pick_fastest()
        if fastest_lap is None or fastest_lap.empty:
            raise F1DataError(f"No fastest lap found for driver '{code}' in {year} round {round_num}.")

        telemetry = fastest_lap.get_car_data().add_distance()
        results.append({
            "driver_code": code,
            "lap_time": str(fastest_lap["LapTime"]),
            "event_name": session.event["EventName"],
            "distance": telemetry["Distance"].tolist(),
            "speed": telemetry["Speed"].tolist(),
            "throttle": telemetry["Throttle"].tolist(),
            "brake": telemetry["Brake"].tolist(),
        })
    return results


def get_race_replay_data(year: int, round_num: int) -> dict:
    """
    Fetch and prepare everything needed for an animated race replay:
    per-driver position traces over time, lap/position history for a
    leaderboard, and weather samples over the race.
    """
    try:
        session = fastf1.get_session(year, round_num, "R")
        session.load(telemetry=True, weather=True)
    except Exception as e:
        raise F1DataError(f"Could not load race {year} round {round_num}: {e}") from e

    if not session.drivers:
        raise F1DataError(f"No driver data available for {year} round {round_num}.")

    driver_tracks = {}
    colors = {}
    all_x, all_y = [], []

    for drv in session.drivers:
        try:
            info = session.get_driver(drv)
            code = info["Abbreviation"]
            team_color = info.get("TeamColor")
            colors[code] = f"#{team_color}" if team_color else "#FFFFFF"
            pos = session.pos_data[drv]
        except Exception as e:
            logger.warning("Skipping driver %s (no position data): %s", drv, e)
            continue

        if pos is None or pos.empty:
            continue

        times = pos["Time"].dt.total_seconds().tolist()
        xs = pos["X"].tolist()
        ys = pos["Y"].tolist()
        driver_tracks[code] = {"t": times, "x": xs, "y": ys}
        all_x.extend(xs)
        all_y.extend(ys)

    if not driver_tracks:
        raise F1DataError(f"No position telemetry available for {year} round {round_num}.")

    # Build a clean track outline from a single "normal" lap (no pit
    # entry/exit) rather than a driver's full-session trace, which
    # would otherwise draw a stray loop through the pit lane every
    # time that driver pitted.
    outline_x, outline_y = [], []
    for drv in session.drivers:
        try:
            laps = session.laps.pick_drivers(drv)
            clean_laps = laps[laps["PitOutTime"].isna() & laps["PitInTime"].isna()]
            if clean_laps.empty:
                continue
            reference_lap = clean_laps.iloc[len(clean_laps) // 2]
            outline_pos = reference_lap.get_pos_data()
            if outline_pos is None or outline_pos.empty:
                continue
            outline_x = outline_pos["X"].tolist()
            outline_y = outline_pos["Y"].tolist()
            break
        except Exception as e:
            logger.warning("Skipping driver %s while building track outline: %s", drv, e)
            continue

    if not outline_x:
        # Fallback: any driver's full trace is better than no outline at all.
        first_track = next(iter(driver_tracks.values()))
        outline_x, outline_y = first_track["x"], first_track["y"]

    # Grid (starting) positions, used as a fallback until each driver
    # completes their first lap.
    grid_positions = {}
    try:
        for _, row in session.results.iterrows():
            code = row["Abbreviation"]
            gp = row.get("GridPosition")
            grid_positions[code] = None if _is_na(gp) else int(gp)
    except Exception as e:
        logger.warning("Could not build grid positions for %s round %s: %s", year, round_num, e)
        grid_positions = {}

    # Lap boundaries, keyed off 'Time' (session time when the lap was
    # completed) rather than 'LapStartTime' — the latter is frequently
    # missing/NaT in practice and left every lap unusable.
    driver_laps_info = {}
    for drv in session.drivers:
        try:
            info = session.get_driver(drv)
            code = info["Abbreviation"]
        except Exception as e:
            logger.warning("Skipping driver %s while building lap info: %s", drv, e)
            continue

        laps = session.laps.pick_drivers(drv).sort_values("LapNumber")
        entries = []
        for _, lap in laps.iterrows():
            lap_num = lap.get("LapNumber")
            end_time = lap.get("Time")
            if _is_na(lap_num) or _is_na(end_time):
                continue
            pos_val = lap.get("Position")
            entries.append({
                "lap_number": int(lap_num),
                "end_time": end_time.total_seconds(),
                "position": None if _is_na(pos_val) else int(pos_val),
            })
        driver_laps_info[code] = entries

    weather = []
    try:
        if session.weather_data is not None and not session.weather_data.empty:
            for _, row in session.weather_data.iterrows():
                weather.append({
                    "t": row["Time"].total_seconds(),
                    "track_temp": float(row["TrackTemp"]),
                    "air_temp": float(row["AirTemp"]),
                    "humidity": float(row["Humidity"]),
                    "wind_speed": float(row["WindSpeed"]),
                    "rainfall": bool(row["Rainfall"]),
                })
    except Exception as e:
        # Weather data isn't always available for every session; the
        # replay can still run without it (weather panel just won't show).
        logger.info("No weather data available for %s round %s: %s", year, round_num, e)
        weather = []

    total_laps = max(
        (e["lap_number"] for entries in driver_laps_info.values() for e in entries),
        default=0,
    )

    non_empty_times = [t["t"] for t in driver_tracks.values() if t["t"]]
    max_time = max((max(t) for t in non_empty_times), default=0.0)

    return {
        "event_name": session.event["EventName"],
        "driver_tracks": driver_tracks,
        "track_outline": {"x": outline_x, "y": outline_y},
        "driver_laps_info": driver_laps_info,
        "grid_positions": grid_positions,
        "colors": colors,
        "x_range": (min(all_x), max(all_x)),
        "y_range": (min(all_y), max(all_y)),
        "weather": weather,
        "total_laps": total_laps,
        "max_time": max_time,
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