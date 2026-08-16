# fast-f1

A command-line tool to fetch Formula 1 season data — race winners, championship
standings, full race results, and season schedules — powered by
[FastF1](https://github.com/theOehrly/Fast-F1) and the Ergast API.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
mkdir f1_cache
```

## Usage

```bash
# List every race winner for a season
python main.py winners 2023

# Show final driver championship standings
python main.py standings 2023

# Show full results for a specific race (year, round number)
python main.py race 2023 5

# Show the full season calendar
python main.py schedule 2023
```

## Roadmap

- [ ] Constructor/team standings
- [ ] CSV/JSON export flags
- [ ] Compare two seasons side by side
- [ ] Colorized terminal output (`rich`)
- [ ] Fastest lap + pit stop data per race

## Credits

Built on top of [FastF1](https://github.com/theOehrly/Fast-F1), which wraps
official F1 timing data and the Ergast Developer API.