# fast-f1

Formula 1 analytics in three surfaces that share one data layer:

- a **CLI** for season standings, results, schedules and comparisons,
- an interactive **Streamlit dashboard**,
- a read-only **FastAPI** analytics API.

All three are powered by [FastF1](https://github.com/theOehrly/Fast-F1)
(official F1 timing data) and the [Ergast/Jolpica](https://ergast.com/mrd/)
results API. Nothing here invents data: if a value can't be retrieved,
you get an honest error, never a fabricated number.

## Architecture

```
f1_data.py       Data-access layer: all FastF1 / Ergast fetching. Returns
                 plain Python dicts/lists. Raises specific exceptions
                 (see "Error model" below). No printing/export logic.
config.py        Centralized setup: cache dir + logging (F1_CACHE_DIR,
                 F1_LOG_LEVEL). Shared by CLI, dashboard and API.
display.py       Terminal presentation (rich tables/panels/colors).
export.py        CSV / JSON export (validated, atomic writes).
visualize.py     Matplotlib telemetry plots (with input validation).
replay.py        Pygame animated race replay (pygame imported lazily).

services/        Reusable analytics for the API (wraps f1_data, adds
                 telemetry downsampling / response shaping).
api/             FastAPI app: main.py (factory + error mapping),
                 schemas.py (Pydantic models), routes/ (endpoints).

streamlit_app.py Streamlit dashboard.
predict_gp.py    Optional ML experiment (see "Machine learning").
tests/           Offline pytest suite (FastF1/Ergast are mocked).
```

Data fetching, business logic, and presentation are kept separate, so the
same `f1_data` functions back the CLI, the dashboard, and the API without
duplication.

## Requirements

- Python **3.10 – 3.12** recommended (3.13/3.14 work, but `pygame` has no
  prebuilt wheels for very new Pythons — see Replay below).

## Installation

```bash
python -m venv .venv
# Windows:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt        # CLI + dashboard + API
pip install -r requirements-dev.txt    # adds pytest, ruff, httpx
```

`requirements.txt` installs everything needed for the default surfaces.
Optional extras are declared in `pyproject.toml` and can be installed as:

```bash
pip install ".[replay]"    # pygame race replay
pip install ".[ml]"        # scikit-learn (predict_gp.py)
pip install ".[dev]"       # test + lint tooling
```

## Configuration

Both the CLI and dashboard read these environment variables (via
`config.py`):

| Variable       | Default      | Purpose                                   |
|----------------|--------------|-------------------------------------------|
| `F1_CACHE_DIR` | `./f1_cache` | FastF1 on-disk cache (created if missing) |
| `F1_LOG_LEVEL` | `WARNING`    | Root log level (DEBUG/INFO/WARNING/...)   |

The cache makes repeat calls fast and offline-friendly; it is large and
regenerable, so it is git-ignored. First-run commands hit the network.

## CLI usage

Run any command with `python main.py <command> ...`.

```bash
python main.py winners 2023          # every race winner in a season
python main.py standings 2023        # driver championship table
python main.py constructors 2023     # constructor championship table
python main.py race 2023 5           # full results for round 5
python main.py schedule 2023         # season calendar
python main.py compare 2022 2023     # side-by-side season comparison
```

Export any of the above to a file:

```bash
python main.py standings 2023 --csv standings.csv
python main.py race 2023 5 --json race5.json
python main.py compare 2022 2023 --csv c.csv --json c.json
```

Telemetry visualisation (matplotlib) for one or more drivers' fastest laps:

```bash
python main.py visualize 2023 5 VER LEC
python main.py visualize 2023 5 VER LEC HAM --full --output miami.png
python main.py visualize 2023 5 VER LEC --full --no-delta
```

Race replay (needs the optional `pygame` extra):

```bash
python main.py replay 2023 5
python main.py replay 2023 9 --speed 4
```

In the replay window: `SPACE` pause/resume, `←`/`→` rewind/fast-forward,
`↑`/`↓` speed, `R` restart, `ESC` close. If `pygame` isn't installed, the
`replay` command exits with a clear message instead of crashing the rest
of the CLI.

## Dashboard

```bash
streamlit run streamlit_app.py
```

Pages: driver/constructor standings, race winners, race results, schedule,
season comparison, and fastest-lap telemetry comparison. Expensive fetches
are cached with `st.cache_data` (1h TTL) on top of FastF1's disk cache.

## API

```bash
uvicorn api.main:app --reload
# Interactive docs: http://127.0.0.1:8000/docs
```

| Method | Path                                              | Description                    |
|--------|---------------------------------------------------|--------------------------------|
| GET    | `/health`                                         | App status (no upstream calls) |
| GET    | `/seasons/{year}/schedule`                        | Season calendar              |
| GET    | `/seasons/{year}/winners`                         | Race winners                 |
| GET    | `/seasons/{year}/standings/drivers`               | Driver standings             |
| GET    | `/seasons/{year}/standings/constructors`          | Constructor standings        |
| GET    | `/seasons/compare?year1=&year2=`                  | Season comparison            |
| GET    | `/races/{year}/{round}/results`                   | Full race results            |
| GET    | `/races/{year}/{round}/telemetry?drivers=&max_points=` | Fastest-lap telemetry (downsampled) |

Examples:

```bash
curl "http://127.0.0.1:8000/seasons/2023/standings/drivers"
curl "http://127.0.0.1:8000/races/2023/5/telemetry?drivers=VER&drivers=LEC&max_points=500"
```

Telemetry responses are bounded by `max_points` (default 2000, max 10000)
and evenly downsampled, so responses stay a sane size.

### Error model

`f1_data` raises specific exceptions, which the API maps to honest HTTP
statuses (and the CLI/dashboard surface as readable messages):

| Exception              | Meaning                          | HTTP |
|------------------------|----------------------------------|------|
| `InvalidQueryError`    | Bad year/round/driver input      | 400  |
| `DataUnavailableError` | Valid request, data absent/empty | 404  |
| `DataSourceError`      | Upstream provider/network failed | 502  |

## Testing and linting

```bash
pytest              # offline; FastF1/Ergast are mocked
ruff check .        # lint
ruff format --check .   # formatting
```

The suite (in `tests/`) covers data validation, error classification,
CSV/JSON round-trips, telemetry validation, replay logic, CLI dispatch,
service downsampling, and every API endpoint — all without live network.

## Export formats

- **CSV**: header is the union of all row keys; missing values are empty
  cells. Empty datasets are rejected with a clear error.
- **JSON**: any JSON-serializable result.

Both writes are **atomic** (temp file + rename), so a failed write never
leaves a corrupted file.

## Data sources & limitations

- Standings/winners/calendars come from Ergast/Jolpica; live timing and
  telemetry come from FastF1. Both have provider-side delays and rate
  limits, and only cover the official World Championship era (1950+).
- In-progress seasons return partial standings; future seasons may have a
  schedule but no results.
- Weather data is not available for every session (replay degrades
  gracefully without it).
- Test suite never depends on live F1 services; only real runs hit the API.

## Machine learning

`predict_gp.py` is an **optional, standalone experiment** that predicts
win/podium probabilities from grid/quali position and prior-race form,
with chronological grouping to avoid target leakage. It is intentionally
**not** wired into the API (training stays separate from ordinary
requests) and requires `pip install ".[ml]"`. Treat its output as an
indication, not a guarantee — small samples and the many real-world factors
in an F1 race limit accuracy.

## Troubleshooting

- **`ReplayError: ... pygame ... isn't installed`** — run
  `pip install ".[replay]"` (may fail on Python ≥ 3.13 where pygame has no
  wheels; everything else still works).
- **Slow first command** — FastF1 is downloading/caching; subsequent calls
  reuse `F1_CACHE_DIR`.
- **`DataSourceError` / 502** — the F1/Ergast provider is unreachable or
  rate-limited; retry later.
- **`404` / "No ... available"** — the season/round exists but has no data
  yet (e.g. a future or in-progress event).

## Credits

Built on [FastF1](https://github.com/theOehrly/Fast-F1) and the
[Ergast Developer API](https://ergast.com/mrd/). Terminal output via
[rich](https://github.com/Textualize/rich).
