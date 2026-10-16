"""Tests for the CLI entry point: argument parsing and command dispatch."""

import argparse
from unittest import mock

import pytest

import main


def test_parser_standings():
    args = main.build_parser().parse_args(["standings", "2023"])
    assert args.command == "standings"
    assert args.year == 2023
    assert args.func is main.cmd_standings


def test_parser_visualize_flags():
    args = main.build_parser().parse_args(
        ["visualize", "2023", "5", "VER", "LEC", "--full", "--no-delta", "-o", "out.png"]
    )
    assert args.drivers == ["VER", "LEC"]
    assert args.full is True
    assert args.no_delta is True
    assert args.output == "out.png"


def test_parser_requires_command():
    with pytest.raises(SystemExit):
        main.build_parser().parse_args([])


def test_cmd_standings_dispatches_to_display():
    args = argparse.Namespace(year=2023, csv=None, json=None)
    data = [
        {"position": 1, "driver": "Verstappen", "constructor": "RB", "points": 575.0, "wins": 19}
    ]
    with (
        mock.patch.object(main, "get_driver_standings", return_value=data) as getter,
        mock.patch.object(main.display, "print_driver_standings") as printer,
    ):
        main.cmd_standings(args)
    getter.assert_called_once_with(2023)
    printer.assert_called_once_with(2023, data)


def test_cmd_race_exports_csv(tmp_path):
    args = argparse.Namespace(year=2023, round=5, csv=str(tmp_path / "r.csv"), json=None)
    race = {
        "event_name": "Miami GP",
        "results": [
            {
                "position": 1,
                "driver_code": "VER",
                "driver": "Max",
                "team": "RB",
                "points": 25.0,
                "status": "Finished",
            }
        ],
    }
    with (
        mock.patch.object(main, "get_race_results", return_value=race),
        mock.patch.object(main.display, "print_race_results"),
    ):
        main.cmd_race(args)
    assert (tmp_path / "r.csv").exists()


def test_cmd_winners_export_json(tmp_path):
    args = argparse.Namespace(year=2023, csv=None, json=str(tmp_path / "w.json"))
    winners = [{"round": 1, "event_name": "Bahrain", "driver": "VER", "constructor": "RB"}]
    with (
        mock.patch.object(main, "get_race_winners", return_value=winners),
        mock.patch.object(main.display, "print_winners"),
    ):
        main.cmd_winners(args)
    assert (tmp_path / "w.json").exists()


def test_handle_export_reports_error():
    args = argparse.Namespace(csv="bad.txt", json=None)
    with (
        mock.patch.object(
            main.export, "export_to_csv", side_effect=main.export.ExportError("bad ext")
        ),
        mock.patch.object(main.display, "print_error") as err,
    ):
        main._handle_export([{"a": 1}], args, "test")
    err.assert_called_once()


def test_cmd_compare_flattens_for_export(tmp_path):
    args = argparse.Namespace(year1=2022, year2=2023, csv=str(tmp_path / "c.csv"), json=None)
    comparison = {
        "year1": 2022,
        "year2": 2023,
        "errors": {},
        "data": {
            2022: {
                "summary": {
                    "num_races": 22,
                    "champion_driver": "Verstappen",
                    "champion_driver_points": 454.0,
                    "champion_constructor": "RB",
                    "champion_constructor_points": 759.0,
                    "top_driver_wins": 15,
                }
            },
            2023: {
                "summary": {
                    "num_races": 22,
                    "champion_driver": "Verstappen",
                    "champion_driver_points": 575.0,
                    "champion_constructor": "RB",
                    "champion_constructor_points": 860.0,
                    "top_driver_wins": 19,
                }
            },
        },
    }
    with (
        mock.patch.object(main, "compare_seasons", return_value=comparison),
        mock.patch.object(main.display, "print_comparison"),
    ):
        main.cmd_compare(args)
    assert (tmp_path / "c.csv").exists()
