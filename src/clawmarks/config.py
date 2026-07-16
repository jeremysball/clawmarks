import os
from pathlib import Path


def repo_root() -> Path:
    env_override = os.environ.get("CLAWMARKS_ROOT")
    if env_override:
        return Path(env_override)
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(
        "Could not find pyproject.toml by walking up from clawmarks/config.py. "
        "If clawmarks is installed outside its source checkout, set CLAWMARKS_ROOT "
        "to the repo root explicitly."
    )


ROOT = repo_root()
NOTES_DIR = ROOT / "notes"
# Runtime state (generated images, manifests, checkpoints, and expedition/leg config) lives
# outside the repo per the XDG Base Directory spec, not under notes/, so it survives a repo
# re-clone and doesn't tempt anyone into committing gitignored generation output.
# CLAWMARKS_STATE_DIR overrides the XDG default entirely; XDG_STATE_HOME overrides only the
# ~/.local/state root. See ADR 0001: expedition/leg config used to live in a git-tracked
# ROOT/expeditions/ tree; it moved here so an expedition can be created or edited without a
# git commit, and so config never has to be reconciled against generation output that was
# already state-dir-only.
STATE_DIR = Path(os.environ["CLAWMARKS_STATE_DIR"]) if os.environ.get("CLAWMARKS_STATE_DIR") \
    else Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "clawmarks"
EXPEDITIONS_DIR = STATE_DIR / "expeditions"
PROBE_DIR = STATE_DIR / "probe_uncanny"
PROBE_STRENGTH_DIR = STATE_DIR / "probe_strength"
# The curation server's currently-selected expedition/leg, persisted so a server restart
# doesn't forget it and fall back to the empty-state hub while real data still exists.
ACTIVE_LEG_FILE = STATE_DIR / "active_leg.json"


def leg_dir(expedition: str, leg: str) -> Path:
    """Runtime output directory for one leg: allnight_state.json, scored_manifest.json,
    thumbs/, real_thumbs/, seed_pool.json, and every curation artifact (favorites,
    comparisons, cockpit queue, ...) stored for that expedition leg. Lives alongside that
    expedition's config (EXPEDITIONS_DIR / expedition / "expedition.json" and
    "legs/<leg>.json") under the same STATE_DIR/expeditions/<expedition>/ directory, one
    level up, distinguished by the "legs/" config subdir versus the bare "<leg>/" output
    subdir."""
    return EXPEDITIONS_DIR / expedition / leg
