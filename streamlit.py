"""
streamlit_app.py — F1 season data dashboard.

Reuses the existing f1_data.py data-access layer untouched (it returns
plain dicts/lists, so it slots straight into Streamlit without any
changes). Run with:

    streamlit run streamlit_app.py

Cache directory and log level are configurable the same way as the
CLI: F1_CACHE_DIR and F1_LOG_LEVEL environment variables.
"""

import logging
import os

import fastf1
import pandas as pd
import plotly.express as px
import streamlit as st

from f1_data import (
    F1DataError,
    compare_seasons,
    get_constructor_standings,
    get_driver_standings,
    get_multiple_drivers_lap_telemetry,
    get_race_results,
    get_race_winners,
    get_schedule,
)

logging.basicConfig(level=os.environ.get("F1_LOG_LEVEL", "WARNING"))

CACHE_DIR = os.environ.get("F1_CACHE_DIR", "f1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

st.set_page_config(page_title="F1 Season Dashboard", page_icon="🏎️", layout="wide")

CURRENT_YEAR = 2026
YEAR_OPTIONS = list(range(CURRENT_YEAR, 1949, -1))


# ---------------------------------------------------------------------------
# Cached wrappers around f1_data.py — Streamlit re-runs the whole script on
# every interaction, so these stop that from re-hitting FastF1/Ergast each
# time a widget changes. FastF1's own on-disk cache still backs all of this.
# ---------------------------------------------------------------------------

@st.cache_data(ttl="1h", show_spinner=False)
def cached_schedule(year: int):
    return get_schedule(year)


@st.cache_data(ttl="1h", show_spinner=False)
def cached_race_winners(year: int):
    return get_race_winners(year)


@st.cache_data(ttl="1h", show_spinner=False)
def cached_driver_standings(year: int):
    return get_driver_standings(year)


@st.cache_data(ttl="1h", show_spinner=False)
def cached_constructor_standings(year: int):
    return get_constructor_standings(year)


@st.cache_data(ttl="1h", show_spinner=False)
def cached_race_results(year: int, round_num: int):
    return get_race_results(year, round_num)


@st.cache_data(ttl="1h", show_spinner=False)
def cached_compare_seasons(year1: int, year2: int):
    return compare_seasons(year1, year2)


@st.cache_data(ttl="1h", show_spinner=False)
def cached_telemetry(year: int, round_num: int, driver_codes: tuple[str, ...]):
    return get_multiple_drivers_lap_telemetry(year, round_num, list(driver_codes))


def show_error(e: F1DataError):
    st.error(str(e))


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def page_standings(year: int):
    st.subheader(f"Driver Standings — {year}")
    try:
        drivers = cached_driver_standings(year)
    except F1DataError as e:
        show_error(e)
        return
    df = pd.DataFrame(drivers)
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        st.bar_chart(df.set_index("driver")["points"])


def page_constructors(year: int):
    st.subheader(f"Constructor Standings — {year}")
    try:
        constructors = cached_constructor_standings(year)
    except F1DataError as e:
        show_error(e)
        return
    df = pd.DataFrame(constructors)
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        st.bar_chart(df.set_index("constructor")["points"])


def page_winners(year: int):
    st.subheader(f"Race Winners — {year}")
    try:
        winners = cached_race_winners(year)
    except F1DataError as e:
        show_error(e)
        return
    st.dataframe(pd.DataFrame(winners), use_container_width=True, hide_index=True)


def page_schedule(year: int):
    st.subheader(f"Season Schedule — {year}")
    try:
        schedule = cached_schedule(year)
    except F1DataError as e:
        show_error(e)
        return
    st.dataframe(pd.DataFrame(schedule), use_container_width=True, hide_index=True)


def page_race_results(year: int):
    st.subheader(f"Race Results — {year}")
    try:
        schedule = cached_schedule(year)
    except F1DataError as e:
        show_error(e)
        return

    round_labels = {f"R{ev['round']} — {ev['event_name']}": ev["round"] for ev in schedule}
    if not round_labels:
        st.info("No rounds available for this season yet.")
        return

    label = st.selectbox("Round", list(round_labels.keys()))
    round_num = round_labels[label]

    try:
        with st.spinner(f"Loading round {round_num} results..."):
            race = cached_race_results(year, round_num)
    except F1DataError as e:
        show_error(e)
        return

    st.caption(race["event_name"])
    st.dataframe(pd.DataFrame(race["results"]), use_container_width=True, hide_index=True)


def page_compare(year1: int, year2: int):
    st.subheader(f"Compare Seasons — {year1} vs {year2}")
    if year1 == year2:
        st.warning("Pick two different seasons to compare.")
        return

    with st.spinner("Loading both seasons..."):
        comparison = cached_compare_seasons(year1, year2)

    for year, message in comparison["errors"].items():
        st.warning(f"{year}: {message}")

    rows = []
    for year, season in comparison["data"].items():
        rows.append({"year": year, **season["summary"]})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def page_telemetry(year: int):
    st.subheader(f"Fastest-Lap Speed Comparison — {year}")
    try:
        schedule = cached_schedule(year)
    except F1DataError as e:
        show_error(e)
        return

    round_labels = {f"R{ev['round']} — {ev['event_name']}": ev["round"] for ev in schedule}
    if not round_labels:
        st.info("No rounds available for this season yet.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        label = st.selectbox("Round", list(round_labels.keys()), key="tel_round")
        round_num = round_labels[label]
    with col2:
        drivers_input = st.text_input(
            "Driver codes (space-separated)", value="VER LEC HAM",
            help="Three-letter FIA driver codes, e.g. VER LEC HAM NOR",
        )

    driver_codes = tuple(d.strip().upper() for d in drivers_input.split() if d.strip())
    if not driver_codes:
        st.info("Enter at least one driver code.")
        return

    if st.button("Load telemetry", type="primary"):
        try:
            with st.spinner("Loading session telemetry (first load can take a minute)..."):
                telemetry_list = cached_telemetry(year, round_num, driver_codes)
        except F1DataError as e:
            show_error(e)
            return

        frames = []
        for tel in telemetry_list:
            frames.append(pd.DataFrame({
                "distance": tel["distance"],
                "speed": tel["speed"],
                "driver": tel["driver_code"],
            }))
            st.caption(f"{tel['driver_code']}: fastest lap {tel['lap_time']}")

        combined = pd.concat(frames, ignore_index=True)
        fig = px.line(
            combined, x="distance", y="speed", color="driver",
            labels={"distance": "Distance (m)", "speed": "Speed (km/h)"},
            title=telemetry_list[0]["event_name"],
        )
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def main():
    st.title("🏎️ F1 Season Dashboard")
    st.caption("Powered by FastF1 + Ergast — same data layer as the fast-f1 CLI.")

    page = st.sidebar.radio(
        "View",
        [
            "Driver Standings",
            "Constructor Standings",
            "Race Winners",
            "Race Results",
            "Schedule",
            "Compare Seasons",
            "Telemetry Compare",
        ],
    )

    if page == "Compare Seasons":
        year1 = st.sidebar.selectbox("Year 1", YEAR_OPTIONS, index=1)
        year2 = st.sidebar.selectbox("Year 2", YEAR_OPTIONS, index=0)
        page_compare(year1, year2)
        return

    year = st.sidebar.selectbox("Season", YEAR_OPTIONS, index=1)

    if page == "Driver Standings":
        page_standings(year)
    elif page == "Constructor Standings":
        page_constructors(year)
    elif page == "Race Winners":
        page_winners(year)
    elif page == "Race Results":
        page_race_results(year)
    elif page == "Schedule":
        page_schedule(year)
    elif page == "Telemetry Compare":
        page_telemetry(year)


if __name__ == "__main__":
    main()