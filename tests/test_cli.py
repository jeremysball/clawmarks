# tests/test_cli.py
from clawmarks.cli import build_parser


def test_build_all_subcommand_parses():
    parser = build_parser()
    args = parser.parse_args(["build", "all"])
    assert args.command == "build"
    assert args.target == "all"


def test_run_allnight_round_argument_parses():
    parser = build_parser()
    args = parser.parse_args(["run", "allnight", "--round", "2"])
    assert args.command == "run"
    assert args.round == 2


def test_serve_subcommand_parses():
    parser = build_parser()
    args = parser.parse_args(["serve"])
    assert args.command == "serve"


def test_build_rate_subcommand_parses():
    parser = build_parser()
    args = parser.parse_args(["build", "rate"])
    assert args.command == "build"
    assert args.target == "rate"


def test_build_preference_rank_subcommand_parses():
    parser = build_parser()
    args = parser.parse_args(["build", "preference-rank"])
    assert args.command == "build"
    assert args.target == "preference-rank"
