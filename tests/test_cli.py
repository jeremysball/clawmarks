# tests/test_cli.py
from clawmarks.cli import _ALL_TARGETS, _BUILD_MODULES, build_parser


def test_build_all_subcommand_parses():
    parser = build_parser()
    args = parser.parse_args(["build", "all"])
    assert args.command == "build"
    assert args.target == "all"


def test_solution_map_runs_before_its_dependents_in_build_all_order():
    # "map" reads solution_map_data.json and "redundancy" reads similarity_scored.json, both
    # written only by "solution-map". `build all` iterates _ALL_TARGETS in order, so on a sweep
    # directory with no leftover files from an earlier run, running these out of order crashes
    # with FileNotFoundError.
    order = list(_ALL_TARGETS)
    assert order.index("solution-map") < order.index("map")
    assert order.index("solution-map") < order.index("redundancy")


def test_probe_report_excluded_from_build_all():
    # probe-report is a fixed report over one specific historical probe-calibration run; it
    # never reads SWEEP_DIR, so it can't be built per sweep directory and must not be part of
    # the "all" loop. It's still a valid standalone target (build_parser accepts it).
    assert "probe-report" not in _ALL_TARGETS
    assert "probe-report" in _BUILD_MODULES


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


def test_build_archive_with_predicted_preference_flag_parses():
    parser = build_parser()
    args = parser.parse_args(["build", "archive", "--use-predicted-preference"])
    assert args.command == "build"
    assert args.target == "archive"
    assert args.use_predicted_preference is True


def test_build_archive_without_flag_defaults_false():
    parser = build_parser()
    args = parser.parse_args(["build", "archive"])
    assert args.use_predicted_preference is False
