

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

GOLD = "bold yellow"
SILVER = "bold white"
BRONZE = "bold rgb(205,127,50)"


def _position_style(position: int) -> str:
    if position == 1:
        return GOLD
    if position == 2:
        return SILVER
    if position == 3:
        return BRONZE
    return ""


def print_error(message: str):
    console.print(Panel(Text(message, style="bold red"), title="Error", border_style="red"))


def print_warning(message: str):
    console.print(Panel(Text(message, style="bold yellow"), title="Warning", border_style="yellow"))


def print_success(message: str):
    console.print(f"[bold green]✓[/bold green] {message}")


def print_schedule(year: int, schedule: list[dict]):
    table = Table(title=f"{year} Season Schedule", header_style="bold cyan")
    table.add_column("Round", justify="right")
    table.add_column("Date")
    table.add_column("Event")
    table.add_column("Location")
    table.add_column("Country")

    for e in schedule:
        table.add_row(str(e["round"]), e["date"], e["event_name"], e["location"], e["country"])

    console.print(table)


def print_winners(year: int, winners: list[dict]):
    table = Table(title=f"{year} Race Winners", header_style="bold cyan")
    table.add_column("Round", justify="right")
    table.add_column("Event")
    table.add_column("Winner")
    table.add_column("Constructor")

    for w in winners:
        driver = w["driver"] or "[dim]— no data —[/dim]"
        constructor = w["constructor"] or ""
        table.add_row(str(w["round"]), w["event_name"], driver, constructor)

    console.print(table)


def print_driver_standings(year: int, standings: list[dict]):
    table = Table(title=f"{year} Driver Championship Standings", header_style="bold cyan")
    table.add_column("Pos", justify="right")
    table.add_column("Driver")
    table.add_column("Constructor")
    table.add_column("Points", justify="right")
    table.add_column("Wins", justify="right")

    for row in standings:
        style = _position_style(row["position"])
        table.add_row(
            str(row["position"]),
            row["driver"],
            row["constructor"],
            f"{row['points']:g}",
            str(row["wins"]),
            style=style,
        )

    console.print(table)


def print_constructor_standings(year: int, standings: list[dict]):
    table = Table(title=f"{year} Constructor Championship Standings", header_style="bold cyan")
    table.add_column("Pos", justify="right")
    table.add_column("Constructor")
    table.add_column("Points", justify="right")
    table.add_column("Wins", justify="right")

    for row in standings:
        style = _position_style(row["position"])
        table.add_row(
            str(row["position"]),
            row["constructor"],
            f"{row['points']:g}",
            str(row["wins"]),
            style=style,
        )

    console.print(table)


def print_race_results(year: int, round_num: int, event_name: str, results: list[dict]):
    table = Table(title=f"{year} Round {round_num} — {event_name}", header_style="bold cyan")
    table.add_column("Pos", justify="right")
    table.add_column("Driver")
    table.add_column("Team")
    table.add_column("Points", justify="right")
    table.add_column("Status")

    for row in results:
        pos = row["position"]
        pos_str = str(pos) if pos is not None else "DNF"
        style = _position_style(pos) if pos else ("bold red" if "DNF" in pos_str else "")
        status_style = "green" if row["status"] == "Finished" else "red"
        table.add_row(
            pos_str,
            f"{row['driver']} ({row['driver_code']})",
            row["team"],
            f"{row['points']:g}",
            f"[{status_style}]{row['status']}[/{status_style}]",
            style=style,
        )

    console.print(table)


def print_comparison(comparison: dict):
    year1, year2 = comparison["year1"], comparison["year2"]
    data = comparison["data"]
    errors = comparison["errors"]

    for year in (year1, year2):
        if year in errors:
            print_warning(f"{year}: {errors[year]}")

    s1, s2 = data[year1]["summary"], data[year2]["summary"]

    table = Table(title=f"Season Comparison: {year1} vs {year2}", header_style="bold cyan")
    table.add_column("Metric")
    table.add_column(str(year1), justify="right")
    table.add_column(str(year2), justify="right")
    table.add_column("Change", justify="right")

    def diff_str(v1, v2):
        if v1 is None or v2 is None:
            return "—"
        d = v2 - v1
        if d > 0:
            return f"[green]+{d:g}[/green]"
        if d < 0:
            return f"[red]{d:g}[/red]"
        return "0"

    table.add_row("Races held", str(s1["num_races"]), str(s2["num_races"]), diff_str(s1["num_races"], s2["num_races"]))
    table.add_row("Champion (driver)", s1["champion_driver"], s2["champion_driver"], "")
    table.add_row(
        "Champion points",
        f"{s1['champion_driver_points']:g}" if s1["champion_driver_points"] is not None else "N/A",
        f"{s2['champion_driver_points']:g}" if s2["champion_driver_points"] is not None else "N/A",
        diff_str(s1["champion_driver_points"], s2["champion_driver_points"]),
    )
    table.add_row("Champion (constructor)", s1["champion_constructor"], s2["champion_constructor"], "")
    table.add_row(
        "Constructor points",
        f"{s1['champion_constructor_points']:g}" if s1["champion_constructor_points"] is not None else "N/A",
        f"{s2['champion_constructor_points']:g}" if s2["champion_constructor_points"] is not None else "N/A",
        diff_str(s1["champion_constructor_points"], s2["champion_constructor_points"]),
    )
    table.add_row(
        "Champion's wins",
        str(s1["top_driver_wins"]) if s1["top_driver_wins"] is not None else "N/A",
        str(s2["top_driver_wins"]) if s2["top_driver_wins"] is not None else "N/A",
        diff_str(s1["top_driver_wins"], s2["top_driver_wins"]),
    )

    console.print(table)