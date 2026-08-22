"""
F1 Winner & Podium Predictor
============================
Uses FastF1 to pull historical qualifying/race data, engineers form-based
features per driver/team, trains gradient-boosted classifiers, and predicts
win/podium probabilities for an upcoming Grand Prix.

SETUP
-----
    pip install fastf1 scikit-learn pandas numpy

USAGE
-----
    python predict_gp.py

Edit the CONFIG block below to point at the race you want to predict.
Run it AFTER qualifying for that race has finished so the script can pull
the real starting grid (most predictive single feature). If quali hasn't
happened yet, set QUALI_DONE = False and the script will fall back to
each driver's average grid position this season.


---------------
The first run downloads and caches session data via FastF1 (which hits
Formula1's live timing service and the Ergast/Jolpica results API), so it
needs normal internet access and will take a few minutes for a few
seasons of data. Subsequent runs reuse the local cache and are fast.
"""

import warnings
import numpy as np
import pandas as pd
import fastf1
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import log_loss

warnings.filterwarnings("ignore")

# ============================== CONFIG ===================================
CACHE_DIR = "./f1_cache"          # FastF1 cache folder (created if missing)
TRAIN_SEASONS = [2023, 2024, 2025, 2026]   # seasons to train on
TARGET_YEAR = 2026
TARGET_GP = "Netherlands"         # FastF1 event name / location, e.g. "Netherlands", "Monza"
QUALI_DONE = False                # True once qualifying results exist for TARGET_GP
FORM_WINDOW = 5                   # races of rolling form to use
# ===========================================================================

import os
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)


def get_season_events(year):
    """Return the ordered list of race-round names for a season, excluding testing."""
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return schedule[["RoundNumber", "EventName", "Location", "Country"]]


def load_race_and_quali(year, round_number):
    """Pull grid position, finishing position, points and team for one round."""
    try:
        race = fastf1.get_session(year, round_number, "R")
        race.load(laps=False, telemetry=False, weather=False, messages=False)
        quali = fastf1.get_session(year, round_number, "Q")
        quali.load(laps=False, telemetry=False, weather=False, messages=False)
    except Exception as e:
        print(f"  skip {year} round {round_number}: {e}")
        return None

    if race.results is None or len(race.results) == 0:
        return None

    res = race.results[["Abbreviation", "TeamName", "GridPosition", "Position", "Points"]].copy()
    res["Year"] = year
    res["Round"] = round_number

    if quali.results is not None and len(quali.results) > 0:
        q = quali.results[["Abbreviation", "Position"]].rename(columns={"Position": "QualiPosition"})
        res = res.merge(q, on="Abbreviation", how="left")
    else:
        res["QualiPosition"] = res["GridPosition"]

    return res


def build_historical_dataset(seasons):
    """Loop every completed round in every season and stack results."""
    frames = []
    for year in seasons:
        events = get_season_events(year)
        for _, ev in events.iterrows():
            print(f"Fetching {year} R{ev.RoundNumber} - {ev.EventName}")
            df = load_race_and_quali(year, int(ev.RoundNumber))
            if df is not None:
                df["EventName"] = ev.EventName
                frames.append(df)
    if not frames:
        raise RuntimeError("No historical data could be loaded — check network access.")
    return pd.concat(frames, ignore_index=True)


def engineer_features(df, form_window=FORM_WINDOW):
    """Add rolling driver/team form features computed strictly from PRIOR races."""
    df = df.sort_values(["Year", "Round"]).reset_index(drop=True)
    df["Position"] = pd.to_numeric(df["Position"], errors="coerce")
    df["GridPosition"] = pd.to_numeric(df["GridPosition"], errors="coerce")
    df["QualiPosition"] = pd.to_numeric(df["QualiPosition"], errors="coerce")
    df["Podium"] = (df["Position"] <= 3).astype(int)
    df["Win"] = (df["Position"] == 1).astype(int)

    df["DriverAvgFinish"] = np.nan
    df["DriverAvgPoints"] = np.nan
    df["TeamAvgPoints"] = np.nan

    for driver, grp in df.groupby("Abbreviation"):
        grp = grp.sort_values(["Year", "Round"])
        df.loc[grp.index, "DriverAvgFinish"] = (
            grp["Position"].shift(1).rolling(form_window, min_periods=1).mean()
        )
        df.loc[grp.index, "DriverAvgPoints"] = (
            grp["Points"].shift(1).rolling(form_window, min_periods=1).mean()
        )

    for team, grp in df.groupby("TeamName"):
        grp = grp.sort_values(["Year", "Round"])
        df.loc[grp.index, "TeamAvgPoints"] = (
            grp["Points"].shift(1).rolling(form_window, min_periods=1).mean()
        )

    df["DriverAvgFinish"] = df["DriverAvgFinish"].fillna(df["DriverAvgFinish"].median())
    df["DriverAvgPoints"] = df["DriverAvgPoints"].fillna(0)
    df["TeamAvgPoints"] = df["TeamAvgPoints"].fillna(0)
    return df


FEATURES = ["GridPosition", "QualiPosition", "DriverAvgFinish", "DriverAvgPoints", "TeamAvgPoints"]


def train_models(df):
    """Train separate calibrated classifiers for win and podium probability."""
    data = df.dropna(subset=FEATURES + ["Podium", "Win"]).copy()
    X = data[FEATURES]
    groups = data["Year"] * 100 + data["Round"]  # keep whole races together in CV

    gkf = GroupKFold(n_splits=5)
    for target in ["Podium", "Win"]:
        y = data[target]
        losses = []
        for tr_idx, te_idx in gkf.split(X, y, groups):
            m = GradientBoostingClassifier(random_state=42)
            m.fit(X.iloc[tr_idx], y.iloc[tr_idx])
            p = m.predict_proba(X.iloc[te_idx])[:, 1]
            losses.append(log_loss(y.iloc[te_idx], p, labels=[0, 1]))
        print(f"{target} model cross-val log-loss: {np.mean(losses):.3f}")

    podium_model = GradientBoostingClassifier(random_state=42).fit(X, data["Podium"])
    win_model = GradientBoostingClassifier(random_state=42).fit(X, data["Win"])
    return podium_model, win_model


def build_next_gp_frame(df, year, gp_name, quali_done):
    """Assemble the feature rows for the upcoming race's entry list."""
    latest = df.sort_values(["Year", "Round"]).groupby("Abbreviation").tail(1)
    entry = latest[["Abbreviation", "TeamName", "DriverAvgFinish", "DriverAvgPoints", "TeamAvgPoints"]].copy()

    if quali_done:
        events = get_season_events(year)
        match = events[events["EventName"].str.contains(gp_name, case=False, na=False)]
        if match.empty:
            raise ValueError(f"Could not find event matching '{gp_name}' in {year} schedule.")
        round_number = int(match.iloc[0]["RoundNumber"])
        quali = fastf1.get_session(year, round_number, "Q")
        quali.load(laps=False, telemetry=False, weather=False, messages=False)
        q = quali.results[["Abbreviation", "Position"]].rename(columns={"Position": "QualiPosition"})
        entry = entry.merge(q, on="Abbreviation", how="inner")
        entry["GridPosition"] = entry["QualiPosition"]
    else:
        # No quali yet: approximate grid with each driver's average grid this season
        avg_grid = df[df["Year"] == year].groupby("Abbreviation")["GridPosition"].mean()
        entry["GridPosition"] = entry["Abbreviation"].map(avg_grid).fillna(df["GridPosition"].median())
        entry["QualiPosition"] = entry["GridPosition"]
        print("QUALI_DONE=False -> using season-average grid position as a placeholder for grid.")

    return entry


def predict_next_gp():
    print("Building historical training set (this pulls real session data)...")
    raw = build_historical_dataset(TRAIN_SEASONS)
    raw = raw[raw["Position"].notna() | raw["Points"].notna()]
    feat = engineer_features(raw)

    print("\nTraining models...")
    podium_model, win_model = train_models(feat)

    print(f"\nBuilding entry list for {TARGET_YEAR} {TARGET_GP}...")
    entry = build_next_gp_frame(feat, TARGET_YEAR, TARGET_GP, QUALI_DONE)
    X_next = entry[FEATURES]

    entry["WinProb"] = win_model.predict_proba(X_next)[:, 1]
    entry["PodiumProb"] = podium_model.predict_proba(X_next)[:, 1]
    entry["WinProb"] = entry["WinProb"] / entry["WinProb"].sum()  # normalize to sum to 1

    result = entry.sort_values("WinProb", ascending=False)[
        ["Abbreviation", "TeamName", "GridPosition", "WinProb", "PodiumProb"]
    ].reset_index(drop=True)

    print(f"\n=== {TARGET_YEAR} {TARGET_GP} GP prediction ===")
    print(f"Predicted winner: {result.iloc[0]['Abbreviation']} ({result.iloc[0]['TeamName']})")
    print("Predicted podium (top 3 by podium probability):")
    print(result.sort_values("PodiumProb", ascending=False).head(3).to_string(index=False))
    print("\nFull grid, ranked by win probability:")
    print(result.to_string(index=False))
    return result


if __name__ == "__main__":

    predict_next_gp()
