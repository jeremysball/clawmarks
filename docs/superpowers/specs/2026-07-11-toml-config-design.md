# TOML Configuration File Design

## Problem

`clawmarks/config.py` currently reads two path settings from environment variables:
`CLAWMARKS_ROOT` (repo root override, for installs outside the source checkout) and
`CLAWMARKS_SWEEP_DIR` (points the whole toolchain at a one-off batch directory instead of the
default `notes/uncanny_sweep`). Both are exported as bare module-level constants
(`config.ROOT`, `config.SWEEP_DIR`) that around 20 other modules import once, at their own
import time.

Environment variables work but don't scale as a settings surface: they're invisible unless you
already know to look, they can't be hot-reloaded (a constant bound at import time never sees a
later `export`), and there's no single place to see or edit the toolchain's path configuration.

Secrets (`RUNPOD_API_KEY`, `CIVITAI_TOKEN`, `CIVITAI_MODEL_ID`) are explicitly out of scope for
this change and stay in `.envrc` as they are today.

## Design

### File

A new, optional file: `clawmarks.toml` at the repo root. Gitignored, like `.envrc` and
`TODO.txt`: it's a local override, not project state. If the file doesn't exist, every setting
falls back to its current default (repo-root-relative `notes/uncanny_sweep`, and `ROOT` found by
walking up from `config.py` to the nearest `pyproject.toml`).

```toml
[paths]
sweep_dir = "/workspace/trent-with-smart-prompts/notes/uncanny_seedrun1"
# root = "..."   # only needed if clawmarks is installed outside its source checkout
```

Parsed with `tomllib` (Python 3.11+ stdlib; this project already runs 3.14), so no new
dependency.

### Accessors replace module-level constants

`config.SWEEP_DIR` and `config.ROOT` (bare constants, bound once at import time) are replaced by
accessor functions:

```python
def sweep_dir() -> Path: ...
def root() -> Path: ...
```

Each call checks the config file's mtime (a single cheap `os.stat`) and reloads the parsed TOML
if it changed since the last check. No background thread or filesystem watcher: for a low-
traffic local dev tool, a stat-on-every-call is both simpler and cheap enough.

Every current call site that does `from clawmarks.config import SWEEP_DIR` at module import time
is changed to `from clawmarks import config` and `config.sweep_dir()` at the point of use, so a
config change is visible on the next call rather than frozen at the process's own startup. This
is a mechanical rename across roughly 20 files; no call site's logic changes, only how it obtains
the path.

`SWEEP2_DIR`, `PROBE_DIR`, `PROBE_STRENGTH_DIR`, `SEEDS_FILE`, `USER_PICKS_FILE`,
`USER_RATINGS_FILE`, and `PREFERENCE_SETTINGS_FILE` are all derived from `SWEEP_DIR`/`NOTES_DIR`
today as module-level constants computed once; they become small functions too
(`seeds_file()`, `user_picks_file()`, etc.), each calling `sweep_dir()` internally, so they stay
correct when the sweep directory changes.

### Server-side cache invalidation

`curation_server.py` already has a live-cache mechanism (`_live_cache.get(name, compute_fn,
watched_files=[...])`) that invalidates a cached rendered page when any file in `watched_files`
changes mtime. `clawmarks.toml` becomes one more watched file for every cached page whose
rendering depends on `sweep_dir()` (which is effectively all of them), so:

- A config edit changes which directory `sweep_dir()` returns on the very next call (no server
  restart needed).
- Any page cached against the old directory is correctly thrown away and recomputed against the
  new one, instead of serving stale data until its underlying manifest happens to change.

### What's explicitly not changing

- Secrets (`RUNPOD_API_KEY`, `CIVITAI_TOKEN`, `CIVITAI_MODEL_ID`) stay in `.envrc`, loaded via
  `os.environ`, exactly as today.
- No filesystem watcher / inotify: stat-on-access is enough at this traffic level.
- No config validation framework or schema library: two path keys don't need one.

## Testing

- Unit tests for `config.sweep_dir()`/`config.root()`: no file present → default; file present →
  overridden value; file changes between two calls → second call picks up the new value without
  re-importing the module.
- A `curation_server.py` test confirming a cached page invalidates when `clawmarks.toml`'s mtime
  changes, matching the existing pattern already tested for the model-file watched-files case.
