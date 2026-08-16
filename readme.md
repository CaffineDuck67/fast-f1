# fast-f1

A command-line tool to fetch and analyze Formula 1 season data — race
winners, driver & constructor standings, full race results, season
comparisons, and calendars — with colorized terminal output and
CSV/JSON export. Powered by
[FastF1](https://github.com/theOehrly/Fast-F1) and the Ergast API.

## Project structure

```
main.py       CLI entry point (argparse only — no data or display logic)
f1_data.py    Data-access layer: all FastF1 / Ergast fetching
display.py    Terminal presentation (rich tables, panels, colors)
export.py     CSV / JSON export utilities
visualize.py  Matplotlib plotting (speed comparison charts)
replay.py     Pygame animated race replay (track map, leaderboard, weather)
```

Data fetching, presentation, and export are kept in separate modules
so each can be extended independently.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
mkdir f1_cache
```

## Commands

### Race winners
```bash
python main.py winners 2023
```
Lists every race in the season with its winning driver and constructor.

### Driver standings
```bash
python main.py standings 2023
```
Final (or current, for an in-progress season) driver championship table —
position, driver, constructor, points, wins. Top 3 are highlighted
gold/silver/bronze.

### Constructor standings
```bash
python main.py constructors 2023
```
Same idea, for the constructors' championship.

### Race results
```bash
python main.py race 2023 5
```
Full finishing order for a specific round, with points and status
(finished/retired/DNF), color-coded.

### Season schedule
```bash
python main.py schedule 2023
```
Full calendar — round, date, event name, location, country.

### Compare two seasons
```bash
python main.py compare 2022 2023
```
Side-by-side table of key stats between two seasons: races held,
champion (driver & constructor), champion points, and win counts —
with the year-over-year change highlighted in green/red.

### Visualize fastest lap speed
```bash
python main.py visualize 2023 5 VER LEC
python main.py visualize 2023 5 VER LEC HAM --output miami_speed.png
```
Plots speed-vs-distance for each driver's fastest lap in a race and
saves it as a PNG (default: `speed_comparison.png`). Pass any number
of driver codes to compare more than two at once.

### Race replay (animated track map)
```bash
python main.py replay 2023 5
python main.py replay 2023 9 --speed 4
```
Opens an interactive window animating the full race on a track map:
cars move in real time (or sped up), with a live leaderboard, weather
panel, and lap/time counter — similar to a race engineer's replay
tool.

**Controls (in the replay window):**
| Key | Action |
|---|---|
| `SPACE` | Pause / resume |
| `←` / `→` | Rewind / fast-forward 5s |
| `↑` / `↓` | Increase / decrease playback speed |
| `R` | Restart from the beginning |
| `ESC` | Close the window |

Position data for a full race is a larger download than the other
commands, so the first load can take a minute — it's cached
afterward like everything else.

## Exporting data

Every command above supports `--csv` and `--json` flags to save the
exact data shown in the terminal to a file:

```bash
python main.py standings 2023 --csv standings.csv
python main.py race 2023 5 --json race5.json
python main.py compare 2022 2023 --csv comparison.csv --json comparison.json
```

Both flags can be used together to export to both formats at once.
Export paths are validated (correct extension, existing directory)
and you'll get a clear success message or a specific error if
something's wrong.

## Error handling

The CLI handles gracefully:
- Invalid or out-of-range seasons/rounds
- Seasons with missing/partial data (e.g. a season still in progress)
- Network/API failures when fetching from FastF1 or Ergast
- Malformed CLI arguments (argparse validation)
- Invalid export paths (wrong extension, nonexistent directory, empty data)

## Roadmap

- [x] Constructor/team standings
- [x] CSV/JSON export flags
- [x] Compare two seasons side by side
- [x] Colorized terminal output (rich)
- [x] Fastest-lap speed comparison plot
- [x] Animated race replay with leaderboard and weather
- [ ] Pit stop data per race
- [ ] Driver-vs-driver season comparison
- [ ] Interactive mode / TUI

## Credits

Built on top of [FastF1](https://github.com/theOehrly/Fast-F1), which
wraps official F1 timing data and the Ergast Developer API. Terminal
output powered by [rich](https://github.com/Textualize/rich).