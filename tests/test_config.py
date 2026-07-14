# tests/test_config.py
import os
import subprocess
import sys

from clawmarks import config


def test_repo_root_finds_pyproject():
    root = config.repo_root()
    assert (root / "pyproject.toml").exists()


def test_repo_root_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWMARKS_ROOT", str(tmp_path))
    assert config.repo_root() == tmp_path


def test_derived_paths_under_state_dir():
    assert config.SWEEP_DIR == config.STATE_DIR / "uncanny_round1"
    assert config.SWEEP2_DIR == config.STATE_DIR / "uncanny_round2"
    assert config.PROBE_DIR == config.STATE_DIR / "probe_uncanny"
    assert config.PROBE_STRENGTH_DIR == config.STATE_DIR / "probe_strength"


def test_state_dir_defaults_to_xdg_state_home(tmp_path):
    env = dict(os.environ, XDG_STATE_HOME=str(tmp_path), PYTHONPATH="src")
    env.pop("CLAWMARKS_STATE_DIR", None)
    env.pop("CLAWMARKS_SWEEP_DIR", None)
    result = subprocess.run(
        [sys.executable, "-c", "from clawmarks.config import STATE_DIR; print(STATE_DIR)"],
        env=env, capture_output=True, text=True, cwd=str(config.ROOT), check=True,
    )
    assert result.stdout.strip() == str(tmp_path / "clawmarks")


def test_state_dir_env_override(tmp_path):
    env = dict(os.environ, CLAWMARKS_STATE_DIR=str(tmp_path), PYTHONPATH="src")
    env.pop("CLAWMARKS_SWEEP_DIR", None)
    result = subprocess.run(
        [sys.executable, "-c", "from clawmarks.config import SWEEP_DIR; print(SWEEP_DIR)"],
        env=env, capture_output=True, text=True, cwd=str(config.ROOT), check=True,
    )
    assert result.stdout.strip() == str(tmp_path / "uncanny_round1")


def test_user_ratings_file_path():
    assert config.USER_RATINGS_FILE == config.SWEEP_DIR / "user_ratings.json"


def test_sweep_dir_env_override(tmp_path):
    # SWEEP_DIR is a module-level constant computed at import time, so the override has to be
    # exercised in a fresh subprocess rather than monkeypatched onto the already-imported module.
    env = dict(os.environ, CLAWMARKS_SWEEP_DIR=str(tmp_path), PYTHONPATH="src")
    result = subprocess.run(
        [sys.executable, "-c", "from clawmarks.config import SWEEP_DIR; print(SWEEP_DIR)"],
        env=env, capture_output=True, text=True, cwd=str(config.ROOT), check=True,
    )
    assert result.stdout.strip() == str(tmp_path)
