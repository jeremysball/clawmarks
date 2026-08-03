# P0 Persona-Audit Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 7 P0 bugs filed from the 2026-07-19 persona audit (GitHub issues #58-#64, see `notes/persona_audits/personas/ISSUES.md`): two data-leak bugs (filesystem paths/traceback, RunPod balance), three reproducibility gaps in search-run records (config/seed data, checkpoint identity, timestamps/commit), one stored-XSS ingestion gap, and one dead ARIA reference.

**Architecture:** No new subsystems. Every fix is a targeted change to existing request handlers (`src/clawmarks/curation_server.py`), the search-run report builder (`src/clawmarks/search/run_manager.py`), the driver's persisted state (`src/clawmarks/search/driver.py`), the shared nav header (`src/clawmarks/shared_ui.py`), and a small `escape`/sanitize helper reused at ingestion. New state fields are added as optional (not required) so already-running or previously-persisted legs keep resuming without a migration step.

**Tech Stack:** Python 3, stdlib `http.server`-based HTTP handler, `pytest` for tests, no new third-party dependencies.

## Global Constraints

- Never hardcode a real filesystem path, username, or dollar balance into any HTTP response body (JSON or HTML) — this is the exact class of bug being fixed; a fix that reintroduces a leak elsewhere fails review.
- New fields added to `allnight_state.json` must be optional at read time (`_validate_state` must not add them to its `required` set) — a currently in-progress real run's persisted state predates this change and must keep resuming without a migration.
- Every new/changed handler that returns JSON on error must return `{"error": <plain message>}` with no embedded stack trace or absolute path, matching the existing `_send_json_error` / `_json_response(4xx, ...)` convention already used throughout `curation_server.py`.
- Run `uv run pytest -q tests/test_curation_server_error_page.py tests/test_curation_server_searchrun_routes.py tests/test_curation_server_compare_routes.py tests/test_run_manager.py tests/test_driver_state.py tests/test_shared_ui.py tests/test_cockpit.py` after each task; run the full `uv run pytest -q` once before the plan is considered done, per the project's CLAUDE.md testing convention.
- Commit messages use Conventional Commits (`fix(scope): ...`), imperative mood, per the project's CLAUDE.md.

---

## File Structure

| File | Responsibility | Tasks touching it |
|---|---|---|
| `src/clawmarks/curation_server.py` | HTTP handlers, `_page_context`/`_request_scope` validation, error dispatch, `status.html` render, `/api/compare` and `/api/cockpit/queue` POST handlers | 1, 2, 6 |
| `src/clawmarks/search/run_manager.py` | `build_report` — the dict served by `/api/searchrun/report` | 2, 3, 4, 5 |
| `src/clawmarks/search/driver.py` | `_new_state`, `_validate_state`, `load_state`, persisted `allnight_state.json` shape | 3, 4, 5 |
| `src/clawmarks/config.py` | Shared checkpoint/LoRA identity constants | 4 |
| `src/clawmarks/compute/comfyui.py` | Real search-path workflow builder (reads the new shared constants) | 4 |
| `src/clawmarks/shared_ui.py` | Shared nav header, `nav_bar_html`, Guide button markup, `SHARED_UI_JS` | 7 |
| `tests/test_curation_server_error_page.py` | Path/traceback-leak regression tests | 1 |
| `tests/test_curation_server_searchrun_routes.py` | Balance-leak and status.html-leak regression tests | 2 |
| `tests/test_run_manager.py` | `build_report` field tests for search-config/checkpoint/timestamp/commit | 3, 4, 5 |
| `tests/test_driver_state.py` | `_new_state`/`_validate_state`/`load_state` backward-compat tests | 3, 4, 5 |
| `tests/test_curation_server_compare_routes.py` | XSS-sanitization tests for `/api/compare` | 6 |
| `tests/test_cockpit.py` | XSS-sanitization tests for `/api/cockpit/queue` | 6 |
| `tests/test_shared_ui.py` | Guide-button/ARIA regression tests | 7 |

---

## Task 1: Stop leaking filesystem paths and tracebacks on invalid expedition/leg

GitHub issue #58. Invalid `expedition`/`leg` params currently pass `_validate_expedition_or_leg_name`'s format-only check (`curation_server.py:226-238`), then hit a `FileNotFoundError` deep in `_get_manifest_cached` whose message contains the real absolute path (e.g. `/home/jeremy/.local/state/clawmarks/expeditions/...`). That exception is caught by the generic `do_GET`/`do_POST` wrappers (`curation_server.py:1099-1110`, `1986-1991`) and surfaced verbatim: `_send_json_error` (`1149-1157`) puts `f"{type(exc).__name__}: {exc}"` straight into the JSON body, and `_send_error_page` (`1159-1220`) renders the full `traceback.format_exc()` text inside a `<details><pre class="stack">` block with no redaction.

**Files:**
- Modify: `src/clawmarks/curation_server.py:226-238` (`_validate_expedition_or_leg_name` — add existence check)
- Modify: `src/clawmarks/curation_server.py:1149-1157` (`_send_json_error`)
- Modify: `src/clawmarks/curation_server.py:1159-1220` (`_send_error_page`)
- Test: `tests/test_curation_server_error_page.py`
- Test: `tests/test_curation_server_expedition_routes.py`

**Interfaces:**
- Consumes: `config.EXPEDITIONS_DIR` (existing, `config.py:32`), `config.leg_dir(expedition, leg)` (existing, `config.py:40`).
- Produces: `ExpeditionNotFoundError(ValueError)` — a new exception class raised by `_validate_expedition_or_leg_name` when the expedition or leg does not exist on disk. Later tasks do not depend on this name, but keep it exact for anyone extending scope validation.

- [ ] **Step 1: Write the failing test for path redaction on a nonexistent expedition/leg**

```python
# tests/test_curation_server_expedition_routes.py — add to the existing file
def test_target_cells_on_nonexistent_expedition_returns_404_without_leaking_path(running_server):
    server = running_server
    port = server.server_address[1]

    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/cockpit/target_cells?expedition=totally_bogus&leg=also_bogus"
        )

    assert exc_info.value.code == 404
    body = json.loads(exc_info.value.read().decode())
    assert body["error"] == "expedition not found"
    assert "/home/" not in json.dumps(body)
    assert "Traceback" not in json.dumps(body)
```

Check the top of `tests/test_curation_server_expedition_routes.py` for its existing `running_server` fixture and `import json`, `urllib.error`, `urllib.request`, `pytest` — reuse them, don't redeclare.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/test_curation_server_expedition_routes.py::test_target_cells_on_nonexistent_expedition_returns_404_without_leaking_path -v`
Expected: FAIL (currently returns 500 with a path-containing body, not 404 with `{"error": "expedition not found"}`)

- [ ] **Step 3: Add the existence check and a dedicated exception**

In `src/clawmarks/curation_server.py`, near the existing exception classes (search for `class ContextQueryError` to find the right spot — add immediately after it):

```python
class ExpeditionNotFoundError(ValueError):
    """Raised when a syntactically valid expedition/leg name does not exist on disk. Caught
    separately from ContextQueryError so it always maps to 404, not the generic path-separator
    400."""
```

Modify `_validate_expedition_or_leg_name` (`curation_server.py:226-238`) to also check existence, but only for the expedition (leg existence varies legitimately — a not-yet-launched leg is valid to reference from the picker UI, so only the expedition directory is required to exist):

```python
def _validate_expedition_or_leg_name(name, kind, reserved=()):
    if not isinstance(name, str) or not name:
        raise ValueError(f"{kind} name must be a non-empty string")
    if "\x00" in name:
        raise ValueError(f"{kind} name {name!r} may not contain NUL")
    if os.sep in name or (os.altsep and os.altsep in name) or "/" in name or "\\" in name or ".." in name:
        raise ValueError(f"{kind} name {name!r} may not contain a path separator or '..'")
    if name in reserved:
        raise ValueError(f"{kind} name {name!r} is reserved")
```

Find `_request_scope` (`curation_server.py:304-320`, the function that both `_page_context` and every POST handler already call after format validation) and add the existence check there, once, so every caller gets it:

```python
def _request_scope(expedition, leg):
    if not expedition or not leg:
        raise ValueError("'expedition' and 'leg' query params are required")
    _validate_scope_names(expedition, leg)
    if not (config.EXPEDITIONS_DIR / expedition / "expedition.json").exists():
        raise ExpeditionNotFoundError(f"expedition {expedition!r} not found")
    return expedition, leg
```

(Match this against the real current body of `_request_scope` before editing — insert the existence check as the last step before `return`, keeping whatever parameter validation already precedes it.)

`_page_context` (`curation_server.py:1366-1398`) calls `_validate_scope_names` directly today, not `_request_scope` — change it to call `_request_scope` instead so GET routes get the same existence check as POST routes:

```python
def _page_context(self):
    query = urllib.parse.parse_qs(
        urllib.parse.urlparse(self.path).query, keep_blank_values=True
    )
    if "expedition" in query and "leg" in query:
        try:
            _request_scope(query["expedition"][0], query["leg"][0])
        except (IndexError, ValueError) as e:
            raise ContextQueryError(str(e)) from e
    return resolve_workspace_context(
        self.path, _active_selection, self._focus_store()
    )
```

- [ ] **Step 4: Make the error dispatch return 404 with a plain message for this exception, and redact tracebacks generally**

In `do_GET` (`curation_server.py:1099-1110`), add a branch for `ExpeditionNotFoundError` before the generic `except Exception`:

```python
def do_GET(self):
    try:
        self._do_GET()
    except ContextQueryError as e:
        self._send_context_error(e)
    except ExpeditionNotFoundError as e:
        self._send_not_found_error(e)
    except NoActiveLegError as e:
        self._send_no_active_leg_error(e)
    except Exception as e:
        if self._wants_json():
            self._send_json_error(e)
        else:
            self._send_error_page(e, traceback.format_exc())
```

Add the same branch to `do_POST` (`curation_server.py:1986-1991`) immediately above its existing `except Exception as e:`.

Add `_send_not_found_error` next to the existing `_send_context_error`/`_send_no_active_leg_error` helpers:

```python
def _send_not_found_error(self, exc):
    self._json_response(404, {"error": "expedition not found"})
```

Redact the traceback path segments in both leak sites. `_send_json_error` (`curation_server.py:1149-1157`) currently exposes `str(exc)` verbatim, which for a `FileNotFoundError` includes the absolute path — log it server-side instead of returning it:

```python
def _send_json_error(self, exc):
    no_manifest = isinstance(exc, FileNotFoundError) and "scored_manifest.json" in str(exc)
    print(f"500 error: {type(exc).__name__}: {exc}", flush=True)  # server-side only
    try:
        self._json_response(500, {
            "error": f"{type(exc).__name__}: internal error",
            "no_manifest": no_manifest,
        })
    except Exception:
        pass
```

`_send_error_page` (`curation_server.py:1159-1220`) renders `detail` (the full traceback, which is `html.escape`d but not redacted) inside the `<details>` block. Keep the stack trace available for local debugging but strip the real state-dir prefix out of the rendered text before escaping, since `config.STATE_DIR` is exactly the leaked prefix:

```python
def _send_error_page(self, exc, detail):
    redacted_detail = detail.replace(str(config.STATE_DIR), "<state-dir>")
    print(f"500 error at {self.path}: {detail}", flush=True)  # full detail server-side only
    # ... existing page-building code, but pass redacted_detail to html.escape(...) instead of detail
```

(Find the exact existing body of `_send_error_page` before editing — it already builds a styled HTML page; the only change is computing `redacted_detail` at the top and using it wherever `detail` was previously interpolated into the `<pre class="stack">` block, and adding the `print(...)` line so the real path is still visible in server logs for debugging.)

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest -q tests/test_curation_server_expedition_routes.py::test_target_cells_on_nonexistent_expedition_returns_404_without_leaking_path -v`
Expected: PASS

- [ ] **Step 6: Run the full existing error-page and expedition-route suites to check for regressions**

Run: `uv run pytest -q tests/test_curation_server_error_page.py tests/test_curation_server_expedition_routes.py tests/test_curation_server_searchrun_routes.py -v`
Expected: all PASS. `test_report_rejects_unsafe_scope_names` (in `test_curation_server_searchrun_routes.py`) must still pass unchanged — it tests the `..`-in-name 400 path, which this task does not touch.

- [ ] **Step 7: Commit**

```bash
git add src/clawmarks/curation_server.py tests/test_curation_server_expedition_routes.py
git commit -m "fix(server): return 404 instead of a path-leaking 500 for unknown expeditions"
```

---

## Task 2: Strip the RunPod balance from `/api/searchrun/report`; stop rendering the absolute path/username on `status.html`

GitHub issue #59. `run_manager.build_report` (`src/clawmarks/search/run_manager.py:177-220`) unconditionally includes `state.get("start_balance")` as `report["start_balance"]`, a real dollar figure, with no auth gate. Separately, `status.html` (built in `curation_server.py` around line 1404-1425) renders `str(_active_out_dir())`, an absolute filesystem path that includes the real username, directly into the page.

**Files:**
- Modify: `src/clawmarks/search/run_manager.py:177-220` (`build_report`)
- Modify: `src/clawmarks/curation_server.py` (status.html render — the block containing `sweep dir: <code>{html.escape(str(_active_out_dir() ...`)
- Test: `tests/test_run_manager.py`
- Test: `tests/test_curation_server_searchrun_routes.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `build_report(...)` no longer includes a `start_balance` key in its returned dict (it still accepts `current_balance` and still returns `spend` when given one — only the raw balance figure itself is removed). Task 3/4/5 add new keys to this same dict; they must not reintroduce `start_balance`.

- [ ] **Step 1: Write the failing test for balance removal**

```python
# tests/test_run_manager.py — add near test_build_report_computes_spend_when_current_balance_given
def test_build_report_never_includes_the_raw_start_balance(tmp_path):
    out_dir = tmp_path / "sweep"
    out_dir.mkdir()
    state = {
        "generation": 1, "stage": 0, "plateau_count": 0,
        "novelty_history": [0.1], "gpt55_subjects": [],
        "start_balance": 42.17, "start_time": 1.0,
    }
    (out_dir / "allnight_state.json").write_text(json.dumps(state))

    report = run_manager.build_report(out_dir, current_balance=40.0)

    assert "start_balance" not in report
    assert report["spend"] == pytest.approx(2.17)
```

- [ ] **Step 2: Write the failing test for status.html path/username redaction**

```python
# tests/test_curation_server_searchrun_routes.py — add near the other status-page tests, or
# create a new test file tests/test_curation_server_status_route.py if none of the existing
# fixtures fit; reuse the running_server fixture already defined in this file.
def test_status_page_does_not_render_the_absolute_state_dir(running_server):
    server, out_dir = running_server
    port = server.server_address[1]

    with urllib.request.urlopen(f"http://127.0.0.1:{port}/status.html") as resp:
        body = resp.read().decode()

    assert str(out_dir) not in body
    assert "/home/" not in body
```

- [ ] **Step 3: Run both tests to verify they fail**

Run: `uv run pytest -q tests/test_run_manager.py::test_build_report_never_includes_the_raw_start_balance tests/test_curation_server_searchrun_routes.py::test_status_page_does_not_render_the_absolute_state_dir -v`
Expected: FAIL on both — `start_balance` is currently present in the report dict, and the real path currently renders in `status.html`.

- [ ] **Step 4: Remove the balance field from `build_report`**

In `src/clawmarks/search/run_manager.py`, change `build_report` (lines 177-220) so `start_balance` is read internally (still needed to compute `spend`) but never placed in the returned dict:

```python
def build_report(out_dir, favorites=None, current_balance=None):
    ...
    report = {
        "novelty_trajectory": state.get("novelty_history", []),
        "plateau_count": state.get("plateau_count", 0),
        "generation": state.get("generation", 0),
        "total_images": len(manifest),
        "explore_exploit_split": {cat: v["count"] for cat, v in by_category.items()},
        "pick_rate_by_category": {
            cat: (v["picked"] / v["count"] if v["count"] else 0.0)
            for cat, v in by_category.items()
        },
    }
    if current_balance is not None and state.get("start_balance") is not None:
        report["spend"] = state["start_balance"] - current_balance
    return report
```

(This is the existing function body from the earlier research read, minus the `"start_balance": state.get("start_balance"),` line — every other line stays exactly as-is including whatever computes `manifest`/`by_category` above this snippet; do not touch those.)

- [ ] **Step 5: Redact the absolute path from `status.html`**

In `src/clawmarks/curation_server.py`, find the line (around 1424, inside the status-page template):

```python
<p>sweep dir: <code>{html.escape(str(_active_out_dir() or 'none selected'))}</code></p>
```

Replace with a relative, non-identifying display — the expedition/leg names already convey the same information without the filesystem prefix or username:

```python
<p>sweep dir: <code>{html.escape(f"{_active_selection['expedition']}/{_active_selection['leg']}" if _active_out_dir() else 'none selected')}</code></p>
```

- [ ] **Step 6: Run both tests to verify they pass**

Run: `uv run pytest -q tests/test_run_manager.py::test_build_report_never_includes_the_raw_start_balance tests/test_curation_server_searchrun_routes.py::test_status_page_does_not_render_the_absolute_state_dir -v`
Expected: PASS

- [ ] **Step 7: Run the full report/status/run_manager suites to check for regressions**

Run: `uv run pytest -q tests/test_run_manager.py tests/test_curation_server_searchrun_routes.py -v`
Expected: all PASS, including `test_report_reflects_state_and_manifest_on_disk` and `test_build_report_reads_novelty_trajectory_and_plateau_count_from_state`, neither of which asserted on `start_balance` being present.

- [ ] **Step 8: Commit**

```bash
git add src/clawmarks/search/run_manager.py src/clawmarks/curation_server.py tests/test_run_manager.py tests/test_curation_server_searchrun_routes.py
git commit -m "fix(server): stop leaking RunPod balance and absolute state-dir path"
```

---

## Task 3: Persist the full search configuration on each run's state, and surface it in the report

GitHub issue #60. `allnight_state.json` (built by `_new_state()`, `driver.py:201-206`) records only progress fields (`generation`, `stage`, `plateau_count`, `novelty_history`, `gpt55_subjects`, `start_balance`, `start_time`) — none of the actual search configuration (`explore_fraction`, `gen_batch_size`, `wall_clock_cap_hours`, `budget_usd_cap`, `budget_safety_margin`, `max_generations`, `textures`, `fallback_subjects`, `seed_from_start`) that `load_leg_config` (`driver.py:69-93`) already loads into a `LegConfig` at run start. Per-image seed/sampler/steps/cfg/strength/prompt are already persisted in `scored_manifest.json` (confirmed: `driver.py:121-146`) — nothing to change there.

**Files:**
- Modify: `src/clawmarks/search/driver.py:201-252` (`_new_state`, `_validate_state`, `save_state`)
- Modify: `src/clawmarks/search/run_manager.py:177-220` (`build_report`)
- Test: `tests/test_driver_state.py`
- Test: `tests/test_run_manager.py`

**Interfaces:**
- Consumes: `LegConfig` (existing dataclass, `driver.py:49-66`) — its fields are the source of the new `search_config` dict.
- Produces: `state["search_config"]` — an optional dict key (absent on state files written before this change, present going forward), with keys `explore_fraction`, `gen_batch_size`, `wall_clock_cap_hours`, `budget_usd_cap`, `budget_safety_margin`, `max_generations`, `textures`, `fallback_subjects`, `seed_from_start`. `build_report(...)` copies this dict (or `None` if absent) into `report["search_config"]`. Task 4 and Task 5 add sibling optional keys the same way — follow this exact pattern (add to `_new_state()`'s return dict, do NOT add to `_validate_state`'s `required` set, backfill with `.setdefault()` in `load_state`).

- [ ] **Step 1: Write the failing test for state creation carrying search_config**

```python
# tests/test_driver_state.py — add near test_state_file_uses_the_shared_filename_regardless_of_leg
def test_new_state_includes_search_config_placeholder(tmp_path):
    state = driver._new_state()
    assert state["search_config"] is None


def test_save_state_persists_search_config_from_leg_config(tmp_path):
    cfg = driver.LegConfig(
        expedition="demo", leg="leg1", dir=tmp_path,
        wall_clock_cap_hours=7.5, budget_usd_cap=10.0, budget_safety_margin=1.5,
        gen_batch_size=60, explore_fraction=0.5, max_generations=400,
        textures=["tex-a"], fallback_subjects=["subj-a"], seed_from_start=False,
    )
    state = driver._new_state()
    state["search_config"] = driver._search_config_from_leg_config(cfg)
    driver.save_state(cfg, state)

    reloaded = driver.load_state(cfg)
    assert reloaded["search_config"] == {
        "explore_fraction": 0.5, "gen_batch_size": 60, "wall_clock_cap_hours": 7.5,
        "budget_usd_cap": 10.0, "budget_safety_margin": 1.5, "max_generations": 400,
        "textures": ["tex-a"], "fallback_subjects": ["subj-a"], "seed_from_start": False,
    }


def test_load_state_backfills_search_config_for_legacy_state_files(tmp_path):
    """A state file written before this change has no search_config key at all. Loading it
    must not raise (per the project's data-integrity rule: never fail-close on an in-progress
    real run just because it predates a new optional field) -- it must backfill None."""
    cfg = driver.LegConfig(
        expedition="demo", leg="leg1", dir=tmp_path,
        wall_clock_cap_hours=7.5, budget_usd_cap=10.0, budget_safety_margin=1.5,
        gen_batch_size=60, explore_fraction=0.5, max_generations=400,
        textures=[], fallback_subjects=[], seed_from_start=False,
    )
    (tmp_path / "allnight_state.json").write_text(json.dumps({
        "generation": 5, "stage": 0, "plateau_count": 0, "novelty_history": [0.1] * 5,
        "gpt55_subjects": [], "start_balance": 5.0, "start_time": 1.0,
    }))

    state = driver.load_state(cfg)

    assert state["search_config"] is None
    assert state["generation"] == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest -q tests/test_driver_state.py::test_new_state_includes_search_config_placeholder tests/test_driver_state.py::test_save_state_persists_search_config_from_leg_config tests/test_driver_state.py::test_load_state_backfills_search_config_for_legacy_state_files -v`
Expected: FAIL — `state["search_config"]` raises `KeyError` (key doesn't exist yet), `_search_config_from_leg_config` doesn't exist yet.

- [ ] **Step 3: Add `search_config` to `_new_state`, a builder helper, backward-compatible validation, and backfill on load**

In `src/clawmarks/search/driver.py`, modify `_new_state` (lines 201-206):

```python
def _new_state():
    return {
        "generation": 0, "stage": 0, "plateau_count": 0,
        "novelty_history": [], "gpt55_subjects": [], "start_balance": None,
        "start_time": time.time(), "search_config": None,
    }
```

Add a new helper right after `_new_state`:

```python
def _search_config_from_leg_config(cfg):
    """Snapshots the reproducibility-relevant fields of a LegConfig for persistence in
    allnight_state.json (issue #60: search-run records must be reproducible from the UI
    alone, without needing the original expedition.json/leg.json files)."""
    return {
        "explore_fraction": cfg.explore_fraction,
        "gen_batch_size": cfg.gen_batch_size,
        "wall_clock_cap_hours": cfg.wall_clock_cap_hours,
        "budget_usd_cap": cfg.budget_usd_cap,
        "budget_safety_margin": cfg.budget_safety_margin,
        "max_generations": cfg.max_generations,
        "textures": list(cfg.textures),
        "fallback_subjects": list(cfg.fallback_subjects),
        "seed_from_start": cfg.seed_from_start,
    }
```

Modify `_validate_state` (lines 209-246): do **not** add `search_config` to the `required` set (adding it there would make every currently-persisted real run's state file fail to resume — see the Global Constraints note). Add a type check only when the key is present:

```python
def _validate_state(state, state_file):
    required = {
        "generation", "stage", "plateau_count", "novelty_history", "gpt55_subjects",
        "start_balance", "start_time",
    }
    if not isinstance(state, dict) or not required.issubset(state):
        raise RuntimeError(
            f"cannot resume: persisted state {state_file} is malformed or missing required fields"
        )
    # ... existing validation body for generation/stage/plateau_count/novelty_history/
    # gpt55_subjects/start_balance/start_time stays exactly as-is, unchanged ...
    search_config = state.get("search_config")
    if search_config is not None and not isinstance(search_config, dict):
        raise RuntimeError(f"cannot resume: persisted state {state_file} has invalid search_config")
```

Modify `load_state` (lines 188-198) to backfill the key for legacy files, right after the existing `_validate_state(state, state_file)` call and before `return state`:

```python
def load_state(cfg):
    state_file = _state_file(cfg)
    if not state_file.exists():
        return _new_state()
    try:
        with open(state_file) as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"cannot resume: persisted state {state_file} is unreadable: {e}") from e
    _validate_state(state, state_file)
    state.setdefault("search_config", None)
    return state
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q tests/test_driver_state.py::test_new_state_includes_search_config_placeholder tests/test_driver_state.py::test_save_state_persists_search_config_from_leg_config tests/test_driver_state.py::test_load_state_backfills_search_config_for_legacy_state_files -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for `build_report` surfacing search_config**

```python
# tests/test_run_manager.py
def test_build_report_surfaces_search_config_when_present(tmp_path):
    out_dir = tmp_path / "sweep"
    out_dir.mkdir()
    state = {
        "generation": 1, "stage": 0, "plateau_count": 0,
        "novelty_history": [0.1], "gpt55_subjects": [],
        "start_balance": 5.0, "start_time": 1.0,
        "search_config": {"explore_fraction": 0.5, "gen_batch_size": 60, "wall_clock_cap_hours": 7.5,
                           "budget_usd_cap": 10.0, "budget_safety_margin": 1.5, "max_generations": 400,
                           "textures": ["tex-a"], "fallback_subjects": ["subj-a"], "seed_from_start": False},
    }
    (out_dir / "allnight_state.json").write_text(json.dumps(state))

    report = run_manager.build_report(out_dir)

    assert report["search_config"]["explore_fraction"] == 0.5
    assert report["search_config"]["textures"] == ["tex-a"]


def test_build_report_search_config_is_none_for_legacy_runs(tmp_path):
    out_dir = tmp_path / "sweep"
    out_dir.mkdir()
    state = {
        "generation": 1, "stage": 0, "plateau_count": 0,
        "novelty_history": [0.1], "gpt55_subjects": [],
        "start_balance": 5.0, "start_time": 1.0,
    }
    (out_dir / "allnight_state.json").write_text(json.dumps(state))

    report = run_manager.build_report(out_dir)

    assert report["search_config"] is None
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `uv run pytest -q tests/test_run_manager.py::test_build_report_surfaces_search_config_when_present tests/test_run_manager.py::test_build_report_search_config_is_none_for_legacy_runs -v`
Expected: FAIL — `report["search_config"]` raises `KeyError`.

- [ ] **Step 7: Add `search_config` to the report dict**

In `src/clawmarks/search/run_manager.py`, `build_report` (as already edited in Task 2 Step 4), add one line to the `report` dict literal:

```python
    report = {
        "novelty_trajectory": state.get("novelty_history", []),
        "plateau_count": state.get("plateau_count", 0),
        "generation": state.get("generation", 0),
        "total_images": len(manifest),
        "explore_exploit_split": {cat: v["count"] for cat, v in by_category.items()},
        "pick_rate_by_category": {
            cat: (v["picked"] / v["count"] if v["count"] else 0.0)
            for cat, v in by_category.items()
        },
        "search_config": state.get("search_config"),
    }
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest -q tests/test_run_manager.py -v`
Expected: all PASS.

- [ ] **Step 9: Wire `_search_config_from_leg_config` into the real run-launch path**

Search `driver.py` for where `_new_state()` is called at the start of a real run (in the main driver loop, typically near the top of the function that calls `load_leg_config` and then `load_state`/`_new_state`). Find that call site and set `state["search_config"]` right after obtaining `cfg` and before the first `save_state(cfg, state)`:

```python
state = load_state(cfg)
if state.get("search_config") is None:
    state["search_config"] = _search_config_from_leg_config(cfg)
    save_state(cfg, state)
```

(Locate the exact existing surrounding code — this snippet's job is to backfill `search_config` once per run at startup, for both a brand-new state and a resumed legacy one that predates this field, without overwriting a `search_config` an earlier run of this same task already wrote.)

- [ ] **Step 10: Run the full driver test suite to check for regressions**

Run: `uv run pytest -q tests/test_driver_state.py tests/test_run_manager.py -v`
Expected: all PASS.

- [ ] **Step 11: Commit**

```bash
git add src/clawmarks/search/driver.py src/clawmarks/search/run_manager.py tests/test_driver_state.py tests/test_run_manager.py
git commit -m "feat(search): persist and report the full search configuration per run"
```

---

## Task 4: Record model checkpoint/LoRA identity per run

GitHub issue #61. Neither `allnight_state.json` nor the run report records which checkpoint/LoRA produced a run's images. The values are hardcoded string literals duplicated in two places: `src/clawmarks/compute/comfyui.py:23-25` (the real search path) and `src/clawmarks/curation_server.py:528-530` (the cockpit counterfactual builder) — both currently read `"illustrious_v0.1.safetensors"` and `"clawmarks-illustrious-v3-epoch4.safetensors"`.

**Files:**
- Modify: `src/clawmarks/config.py` (add shared constants)
- Modify: `src/clawmarks/compute/comfyui.py:11-25` (reference the shared constants instead of inline literals)
- Modify: `src/clawmarks/curation_server.py:524-544` (reference the shared constants instead of inline literals)
- Modify: `src/clawmarks/search/driver.py` (`_new_state`, run-launch backfill from Task 3 Step 9)
- Modify: `src/clawmarks/search/run_manager.py:177-220` (`build_report`)
- Test: `tests/test_comfyui.py`
- Test: `tests/test_driver_state.py`
- Test: `tests/test_run_manager.py`

**Interfaces:**
- Consumes: `driver._search_config_from_leg_config` and the run-launch backfill site from Task 3 Step 9.
- Produces: `config.CHECKPOINT_NAME` (`"illustrious_v0.1.safetensors"`), `config.LORA_NAME` (`"clawmarks-illustrious-v3-epoch4.safetensors"`) — importable string constants. `state["checkpoint_lora"]` — optional dict key `{"checkpoint": config.CHECKPOINT_NAME, "lora": config.LORA_NAME}`. `report["checkpoint_lora"]` mirrors it (or `None`).

- [ ] **Step 1: Write the failing test for shared constants**

```python
# tests/test_comfyui.py — add near the top-level tests
def test_build_workflow_uses_the_shared_checkpoint_and_lora_constants():
    from clawmarks import config
    wf = comfyui.build_workflow("a prompt", seed=1)
    ckpt_node = wf["input"]["workflow"]["1"]["inputs"]["ckpt_name"]
    lora_node = wf["input"]["workflow"]["2"]["inputs"]["lora_name"]
    assert ckpt_node == config.CHECKPOINT_NAME
    assert lora_node == config.LORA_NAME
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/test_comfyui.py::test_build_workflow_uses_the_shared_checkpoint_and_lora_constants -v`
Expected: FAIL — `config.CHECKPOINT_NAME` does not exist yet.

- [ ] **Step 3: Add the shared constants to config.py**

In `src/clawmarks/config.py`, add near the top-level constants (after `EXPEDITIONS_DIR`/`STATE_DIR` definitions):

```python
# The checkpoint/LoRA identity used for every generation job. A single source of truth so a
# run's persisted record (search/driver.py's allnight_state.json, surfaced via
# search/run_manager.py's build_report) always matches what compute/comfyui.py and
# curation_server.py's counterfactual builder actually submit (issue #61).
CHECKPOINT_NAME = "illustrious_v0.1.safetensors"
LORA_NAME = "clawmarks-illustrious-v3-epoch4.safetensors"
```

- [ ] **Step 4: Point `comfyui.py` and `curation_server.py` at the shared constants**

In `src/clawmarks/compute/comfyui.py`, add `from clawmarks import config` to the imports, then change lines 23-25:

```python
                "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": config.CHECKPOINT_NAME}},
                "2": {"class_type": "LoraLoader", "inputs": {
                    "lora_name": config.LORA_NAME,
                    "strength_model": strength, "strength_clip": strength,
                    "model": ["1", 0], "clip": ["1", 1]}},
```

In `src/clawmarks/curation_server.py`, `config` is already imported (used throughout the file) — change the equivalent lines at 528-530 the same way:

```python
                "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": config.CHECKPOINT_NAME}},
                "2": {"class_type": "LoraLoader", "inputs": {
                    "lora_name": config.LORA_NAME,
                    "strength_model": strength, "strength_clip": strength,
                    "model": ["1", 0], "clip": ["1", 1]}},
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest -q tests/test_comfyui.py -v`
Expected: all PASS.

- [ ] **Step 6: Write the failing tests for `checkpoint_lora` on state and report**

```python
# tests/test_driver_state.py
def test_new_state_includes_checkpoint_lora_placeholder(tmp_path):
    state = driver._new_state()
    assert state["checkpoint_lora"] is None


def test_load_state_backfills_checkpoint_lora_for_legacy_state_files(tmp_path):
    cfg = driver.LegConfig(
        expedition="demo", leg="leg1", dir=tmp_path,
        wall_clock_cap_hours=7.5, budget_usd_cap=10.0, budget_safety_margin=1.5,
        gen_batch_size=60, explore_fraction=0.5, max_generations=400,
        textures=[], fallback_subjects=[], seed_from_start=False,
    )
    (tmp_path / "allnight_state.json").write_text(json.dumps({
        "generation": 5, "stage": 0, "plateau_count": 0, "novelty_history": [0.1] * 5,
        "gpt55_subjects": [], "start_balance": 5.0, "start_time": 1.0,
    }))

    state = driver.load_state(cfg)

    assert state["checkpoint_lora"] is None
```

```python
# tests/test_run_manager.py
def test_build_report_surfaces_checkpoint_lora_when_present(tmp_path):
    out_dir = tmp_path / "sweep"
    out_dir.mkdir()
    state = {
        "generation": 1, "stage": 0, "plateau_count": 0,
        "novelty_history": [0.1], "gpt55_subjects": [],
        "start_balance": 5.0, "start_time": 1.0,
        "checkpoint_lora": {"checkpoint": "illustrious_v0.1.safetensors",
                             "lora": "clawmarks-illustrious-v3-epoch4.safetensors"},
    }
    (out_dir / "allnight_state.json").write_text(json.dumps(state))

    report = run_manager.build_report(out_dir)

    assert report["checkpoint_lora"]["checkpoint"] == "illustrious_v0.1.safetensors"
```

- [ ] **Step 7: Run tests to verify they fail**

Run: `uv run pytest -q tests/test_driver_state.py::test_new_state_includes_checkpoint_lora_placeholder tests/test_driver_state.py::test_load_state_backfills_checkpoint_lora_for_legacy_state_files tests/test_run_manager.py::test_build_report_surfaces_checkpoint_lora_when_present -v`
Expected: FAIL — `KeyError` on `checkpoint_lora`.

- [ ] **Step 8: Add `checkpoint_lora` following the exact `search_config` pattern from Task 3**

In `src/clawmarks/search/driver.py`, extend `_new_state`:

```python
def _new_state():
    return {
        "generation": 0, "stage": 0, "plateau_count": 0,
        "novelty_history": [], "gpt55_subjects": [], "start_balance": None,
        "start_time": time.time(), "search_config": None, "checkpoint_lora": None,
    }
```

Extend `load_state`'s backfill (added in Task 3 Step 3):

```python
    _validate_state(state, state_file)
    state.setdefault("search_config", None)
    state.setdefault("checkpoint_lora", None)
    return state
```

Extend `_validate_state`'s optional-field type check (added in Task 3 Step 3):

```python
    checkpoint_lora = state.get("checkpoint_lora")
    if checkpoint_lora is not None and not isinstance(checkpoint_lora, dict):
        raise RuntimeError(f"cannot resume: persisted state {state_file} has invalid checkpoint_lora")
```

Extend the run-launch backfill site added in Task 3 Step 9:

```python
state = load_state(cfg)
if state.get("search_config") is None:
    state["search_config"] = _search_config_from_leg_config(cfg)
if state.get("checkpoint_lora") is None:
    state["checkpoint_lora"] = {
        "checkpoint": clawmarks_config.CHECKPOINT_NAME, "lora": clawmarks_config.LORA_NAME,
    }
save_state(cfg, state)
```

(`clawmarks_config` is `driver.py`'s existing import alias for `clawmarks.config`, per `driver.py:27` — use that alias, not a bare `config`, to match the file's existing convention.)

In `src/clawmarks/search/run_manager.py`, extend the `report` dict from Task 3 Step 7:

```python
        "search_config": state.get("search_config"),
        "checkpoint_lora": state.get("checkpoint_lora"),
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `uv run pytest -q tests/test_driver_state.py tests/test_run_manager.py tests/test_comfyui.py -v`
Expected: all PASS.

- [ ] **Step 10: Commit**

```bash
git add src/clawmarks/config.py src/clawmarks/compute/comfyui.py src/clawmarks/curation_server.py src/clawmarks/search/driver.py src/clawmarks/search/run_manager.py tests/test_comfyui.py tests/test_driver_state.py tests/test_run_manager.py
git commit -m "feat(search): record checkpoint/LoRA identity per run from a single shared constant"
```

---

## Task 5: Record `finished_at` and the driver's git commit per run

GitHub issue #62. `allnight_state.json` already has `start_time` (set once in `_new_state`) but nothing marks when a run ended — `driver.py:784` only prints a final line, it never writes a `finished_at` field. No git-commit-reading helper exists anywhere in the codebase (confirmed via grep in the earlier research pass).

**Files:**
- Modify: `src/clawmarks/search/driver.py` (`_new_state`, `_validate_state`, `load_state`, a new `_git_commit()` helper, and the main loop's end-of-run write)
- Modify: `src/clawmarks/search/run_manager.py:177-220` (`build_report`)
- Test: `tests/test_driver_state.py`
- Test: `tests/test_run_manager.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `driver._git_commit()` — returns the current `HEAD` commit hash as a string, or `None` if `git` is unavailable or the working tree isn't a git repo (must not raise). `state["finished_at"]` — optional float (unix timestamp) or `None` while a run is in progress. `state["git_commit"]` — optional string or `None`. `report["started_at"]`, `report["finished_at"]`, `report["git_commit"]` mirror the state fields (`started_at` is `state["start_time"]` renamed for the report's external-facing name — the state key itself stays `start_time` for backward compatibility with every already-persisted file).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_driver_state.py
def test_git_commit_returns_a_real_hash_in_this_repo():
    commit = driver._git_commit()
    assert commit is None or (isinstance(commit, str) and len(commit) == 40)


def test_git_commit_returns_none_when_git_is_unavailable(monkeypatch):
    def _raise(*a, **k):
        raise FileNotFoundError("git not found")
    monkeypatch.setattr(driver.subprocess, "run", _raise)
    assert driver._git_commit() is None


def test_new_state_includes_finished_at_and_git_commit_placeholders(tmp_path):
    state = driver._new_state()
    assert state["finished_at"] is None
    assert state["git_commit"] is None


def test_load_state_backfills_finished_at_and_git_commit_for_legacy_state_files(tmp_path):
    cfg = driver.LegConfig(
        expedition="demo", leg="leg1", dir=tmp_path,
        wall_clock_cap_hours=7.5, budget_usd_cap=10.0, budget_safety_margin=1.5,
        gen_batch_size=60, explore_fraction=0.5, max_generations=400,
        textures=[], fallback_subjects=[], seed_from_start=False,
    )
    (tmp_path / "allnight_state.json").write_text(json.dumps({
        "generation": 5, "stage": 0, "plateau_count": 0, "novelty_history": [0.1] * 5,
        "gpt55_subjects": [], "start_balance": 5.0, "start_time": 1.0,
    }))

    state = driver.load_state(cfg)

    assert state["finished_at"] is None
    assert state["git_commit"] is None
```

```python
# tests/test_run_manager.py
def test_build_report_surfaces_timestamps_and_commit(tmp_path):
    out_dir = tmp_path / "sweep"
    out_dir.mkdir()
    state = {
        "generation": 1, "stage": 0, "plateau_count": 0,
        "novelty_history": [0.1], "gpt55_subjects": [],
        "start_balance": 5.0, "start_time": 1000.0,
        "finished_at": 2000.0, "git_commit": "a" * 40,
    }
    (out_dir / "allnight_state.json").write_text(json.dumps(state))

    report = run_manager.build_report(out_dir)

    assert report["started_at"] == 1000.0
    assert report["finished_at"] == 2000.0
    assert report["git_commit"] == "a" * 40
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest -q tests/test_driver_state.py::test_git_commit_returns_a_real_hash_in_this_repo tests/test_driver_state.py::test_git_commit_returns_none_when_git_is_unavailable tests/test_driver_state.py::test_new_state_includes_finished_at_and_git_commit_placeholders tests/test_driver_state.py::test_load_state_backfills_finished_at_and_git_commit_for_legacy_state_files tests/test_run_manager.py::test_build_report_surfaces_timestamps_and_commit -v`
Expected: FAIL — `_git_commit` doesn't exist, `KeyError` on the new state keys, `KeyError`/missing keys in the report.

- [ ] **Step 3: Add `_git_commit`, the new state fields, and end-of-run write**

In `src/clawmarks/search/driver.py`, add a new helper near `get_balance`/`_spent_or_none` (around line 164-177):

```python
def _git_commit():
    """Returns the driver's current git commit hash for reproducibility (issue #62), or None
    if git is unavailable -- must never raise, since a missing git binary or a non-repo
    checkout must not block a real generation run from starting."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None
```

`subprocess` and `os` are already imported at the top of `driver.py` (lines 19, 22) — no new imports needed.

Extend `_new_state`:

```python
def _new_state():
    return {
        "generation": 0, "stage": 0, "plateau_count": 0,
        "novelty_history": [], "gpt55_subjects": [], "start_balance": None,
        "start_time": time.time(), "search_config": None, "checkpoint_lora": None,
        "finished_at": None, "git_commit": None,
    }
```

Extend `load_state`'s backfill:

```python
    _validate_state(state, state_file)
    state.setdefault("search_config", None)
    state.setdefault("checkpoint_lora", None)
    state.setdefault("finished_at", None)
    state.setdefault("git_commit", None)
    return state
```

Extend `_validate_state`'s optional-field checks:

```python
    finished_at = state.get("finished_at")
    if finished_at is not None and (
        isinstance(finished_at, bool) or not isinstance(finished_at, (int, float)) or not math.isfinite(finished_at)
    ):
        raise RuntimeError(f"cannot resume: persisted state {state_file} has invalid finished_at")
    git_commit = state.get("git_commit")
    if git_commit is not None and not isinstance(git_commit, str):
        raise RuntimeError(f"cannot resume: persisted state {state_file} has invalid git_commit")
```

Extend the run-launch backfill site (set `git_commit` once at run start, alongside `search_config`/`checkpoint_lora` from Tasks 3-4):

```python
state = load_state(cfg)
if state.get("search_config") is None:
    state["search_config"] = _search_config_from_leg_config(cfg)
if state.get("checkpoint_lora") is None:
    state["checkpoint_lora"] = {
        "checkpoint": clawmarks_config.CHECKPOINT_NAME, "lora": clawmarks_config.LORA_NAME,
    }
if state.get("git_commit") is None:
    state["git_commit"] = _git_commit()
save_state(cfg, state)
```

Find the run-ending print statement at `driver.py:784` (`print(f"\nLEG {cfg.expedition}/{cfg.leg} RUN ENDED at generation {state['generation']}, "`) and add a state write immediately before it:

```python
state["finished_at"] = time.time()
save_state(cfg, state)
print(f"\nLEG {cfg.expedition}/{cfg.leg} RUN ENDED at generation {state['generation']}, "
```

(`time` is already imported at the top of `driver.py`, line 23.)

In `src/clawmarks/search/run_manager.py`, extend the `report` dict:

```python
        "search_config": state.get("search_config"),
        "checkpoint_lora": state.get("checkpoint_lora"),
        "started_at": state.get("start_time"),
        "finished_at": state.get("finished_at"),
        "git_commit": state.get("git_commit"),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q tests/test_driver_state.py tests/test_run_manager.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full driver/run_manager/comfyui suites to check for regressions**

Run: `uv run pytest -q tests/test_driver_state.py tests/test_run_manager.py tests/test_comfyui.py tests/test_driver_sibling_exclusion.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/clawmarks/search/driver.py src/clawmarks/search/run_manager.py tests/test_driver_state.py tests/test_run_manager.py
git commit -m "feat(search): record run start/finish timestamps and git commit for reproducibility"
```

---

## Task 6: Sanitize `prompt`/`hypothesis`/`target` and `winner`/`loser` at ingestion

GitHub issue #63. `/api/cockpit/queue`'s `build_trial` (`curation_server.py:683-716`) only `.strip()`s `prompt`/`hypothesis`/`target` before persisting. `/api/compare`'s `record_comparison` (`curation_server.py:589-591`) persists `winner`/`loser` completely raw. Both are reachable directly as JSON POST routes. The only existing mitigation is a render-time `escapeHtml()` in `src/clawmarks/build/cockpit.py:436` (and an independent `escHtml` copy in `src/clawmarks/build/preference_rank.py:158-160`) — defense in depth only, not ingestion-time sanitization.

**Files:**
- Modify: `src/clawmarks/curation_server.py:589-591` (`record_comparison`)
- Modify: `src/clawmarks/curation_server.py:683-716` (`build_trial`)
- Test: `tests/test_curation_server_compare_routes.py`
- Test: `tests/test_cockpit.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_reject_html(value, field_name)` — a new module-level helper in `curation_server.py` that raises `ValueError(f"{field_name!r} may not contain HTML")` if `value` contains `<` or `>`. Reused by both `record_comparison` and `build_trial`. `winner`/`loser` in `/api/compare` and `prompt`/`hypothesis`/`target` in `/api/cockpit/queue` now return `400 {"error": "..."}` instead of persisting when they contain `<` or `>`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_curation_server_compare_routes.py — add near the existing compare-route tests;
# reuse whatever running_server fixture and _post_json helper the file already defines.
def test_compare_rejects_html_in_winner(running_server):
    server, out_dir = running_server
    port = server.server_address[1]

    status, data = _post_json(f"http://127.0.0.1:{port}/api/compare", {
        "expedition": "demo", "leg": "leg1",
        "winner": "<script>alert(1)</script>", "loser": "gen1_a",
    })

    assert status == 400
    assert "HTML" in data["error"]
```

```python
# tests/test_cockpit.py — add near the existing /api/cockpit/queue tests; reuse whatever
# running_server fixture and _post_json helper the file already defines.
def test_queue_rejects_html_in_prompt(running_server):
    server, out_dir = running_server
    port = server.server_address[1]

    status, data = _post_json(f"http://127.0.0.1:{port}/api/cockpit/queue", {
        "expedition": "demo", "leg": "leg1",
        "prompt": "<img src=x onerror=alert(1)>",
    })

    assert status == 400
    assert "HTML" in data["error"]


def test_queue_rejects_html_in_hypothesis(running_server):
    server, out_dir = running_server
    port = server.server_address[1]

    status, data = _post_json(f"http://127.0.0.1:{port}/api/cockpit/queue", {
        "expedition": "demo", "leg": "leg1",
        "prompt": "a safe prompt", "hypothesis": "<script>bad</script>",
    })

    assert status == 400
    assert "HTML" in data["error"]
```

(Check each test file's existing fixture setup first — the exact `_post_json` signature and `running_server` yield shape must match what's already declared at the top of that file, following the same pattern shown in `tests/test_curation_server_searchrun_routes.py` read during research.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest -q tests/test_curation_server_compare_routes.py::test_compare_rejects_html_in_winner tests/test_cockpit.py::test_queue_rejects_html_in_prompt tests/test_cockpit.py::test_queue_rejects_html_in_hypothesis -v`
Expected: FAIL — currently returns 200, the payload persists unsanitized.

- [ ] **Step 3: Add the shared rejection helper and wire it into both write paths**

In `src/clawmarks/curation_server.py`, add near the other small validation helpers (close to `_validate_expedition_or_leg_name`):

```python
def _reject_html(value, field_name):
    """Rejects raw HTML at ingestion (issue #63: /api/compare and /api/cockpit/queue
    previously persisted <script>/<img onerror=...> payloads verbatim, relying only on a
    render-time escapeHtml() that a future unescaped consumer could bypass). Rejecting instead
    of stripping keeps the fix simple and gives the caller an explicit, actionable error."""
    if isinstance(value, str) and ("<" in value or ">" in value):
        raise ValueError(f"{field_name!r} may not contain HTML")
```

Modify `record_comparison` (`curation_server.py:589-591`):

```python
def record_comparison(comparisons, winner, loser, now):
    _reject_html(winner, "winner")
    _reject_html(loser, "loser")
    updated = list(comparisons)
    updated.append({"winner": winner, "loser": loser, "compared_at": now})
    return updated
```

The `/api/compare` handler (`curation_server.py:2037-2062`) already calls `record_comparison` inside a block, but the `ValueError` it can now raise isn't currently caught there — find the handler's existing `try`/`except ValueError` (it already has one around `_request_scope`, per the earlier research read) and confirm `record_comparison`'s call is inside a matching `try`/`except ValueError as e: self._json_response(400, {"error": str(e)}); return` block. If `record_comparison` is called outside any such block in the real current code, wrap it:

```python
    with _lock:
        comparisons = load_comparisons(expedition, leg)
        try:
            comparisons = record_comparison(comparisons, winner, loser, datetime.now(timezone.utc).isoformat())
        except ValueError as e:
            self._json_response(400, {"error": str(e)})
            return
        save_comparisons(comparisons, expedition, leg)
```

Modify `build_trial` (`curation_server.py:683-716`):

```python
def build_trial(payload, now, trial_id):
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("missing 'prompt'")
    _reject_html(prompt, "prompt")
    hypothesis = (payload.get("hypothesis") or "").strip()
    _reject_html(hypothesis, "hypothesis")
    target = payload.get("target") or ""
    _reject_html(target, "target")
    # ... existing body continues unchanged (mission, queue_title, focus_id, seed_strategy, n,
    # strength, sampler, steps, cfg computation) ...
    return {
        "id": trial_id, "status": "draft", "mission": mission, "queue_title": queue_title,
        "prompt": prompt, "hypothesis": hypothesis,
        "target": target, "target_cell": payload.get("target_cell"),
        "focus_id": focus_id,
        "seed_strategy": seed_strategy, "n": n, "strength": strength,
        "sampler": sampler, "steps": steps, "cfg": cfg,
        "negative": payload.get("negative") or NEG_DEFAULT,
        "created_at": now, "result_tags": [], "error": None,
    }
```

(Match this against `build_trial`'s real current body — the shown edit only adds the three `_reject_html` calls and switches the two inline `(payload.get(...) or "").strip()`/`payload.get("target") or ""` expressions to the local `hypothesis`/`target` variables already being validated; every other line — `mission`, `queue_title`, `focus_id`, `seed_strategy`, `n`, `strength`, `sampler`, `steps`, `cfg` — is unchanged from whatever the real function currently computes.) The `/api/cockpit/queue` handler at `curation_server.py:2217-2241` already wraps its `build_trial(...)` call in `try: ... except ValueError as e: self._json_response(400, {"error": str(e)}); return` (confirmed in the earlier research read) — no handler-level change needed there.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q tests/test_curation_server_compare_routes.py::test_compare_rejects_html_in_winner tests/test_cockpit.py::test_queue_rejects_html_in_prompt tests/test_cockpit.py::test_queue_rejects_html_in_hypothesis -v`
Expected: PASS

- [ ] **Step 5: Run the full compare/cockpit suites to check for regressions**

Run: `uv run pytest -q tests/test_curation_server_compare_routes.py tests/test_cockpit.py tests/test_compare_page.py -v`
Expected: all PASS — in particular, any existing test that posts a normal (HTML-free) prompt/winner/loser must still succeed unchanged.

- [ ] **Step 6: Commit**

```bash
git add src/clawmarks/curation_server.py tests/test_curation_server_compare_routes.py tests/test_cockpit.py
git commit -m "fix(server): reject HTML in prompt/hypothesis/target/winner/loser at ingestion"
```

---

## Task 7: Fix the dead `guidePanel` ARIA reference

GitHub issue #64. `shared_ui.py:291-295`'s Guide button has `aria-controls="guidePanel"` but no element with `id="guidePanel"` exists anywhere in the codebase, and the button has no click handler at all (confirmed via grep: only the one `aria-controls` reference exists; `SHARED_UI_JS` has no `guideOpen`/`guidePanel` reference). Given there is no existing guide-content data source to source real content from, and the fix's two options per `ISSUES.md` are "implement the guide dialog or remove the button and its ARIA attributes," this task removes the button — implementing new guide content is out of scope for a P0 leak/breakage fix and would need its own design pass.

**Files:**
- Modify: `src/clawmarks/shared_ui.py:291-295` (remove `guide_button`)
- Modify: `src/clawmarks/shared_ui.py:344` (remove `guide_button` from the assembled nav bar string)
- Test: `tests/test_shared_ui.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `nav_bar_html(...)`'s returned HTML no longer contains `id="guideOpen"` or `aria-controls="guidePanel"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_shared_ui.py
def test_nav_bar_has_no_dead_guide_panel_reference():
    """Regression test for issue #64: aria-controls="guidePanel" pointed at an element that
    never existed anywhere in the codebase, and the button had no click handler either -- a
    dead, structurally broken ARIA reference, not just a visually inert button. Removed
    outright rather than given a stub dialog, since there is no existing guide-content source
    to build a real one from."""
    html = shared_ui.nav_bar_html("/status.html", active_expedition="demo", active_leg="leg1")
    assert "guidePanel" not in html
    assert "guideOpen" not in html
```

(Check the existing top of `tests/test_shared_ui.py` for its actual import statement and the real minimal-required-argument signature of `nav_bar_html` before writing this call — match whatever positional/keyword arguments its other tests already pass.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/test_shared_ui.py::test_nav_bar_has_no_dead_guide_panel_reference -v`
Expected: FAIL — `guidePanel` and `guideOpen` are both currently present.

- [ ] **Step 3: Remove the Guide button**

In `src/clawmarks/shared_ui.py`, delete the `guide_button` assignment (lines 291-295):

```python
guide_button = (
    '<button id="guideOpen" class="guide-button" type="button" '
    'aria-haspopup="dialog" aria-controls="guidePanel" '
    'title="open the OpenCode Guide for this page">Guide</button>'
)
```

And remove `{guide_button}` from the assembled string at line 344:

```python
f'{context_button}{focus_link}{running_label}{guide_button}{session_link}{dropdown}'
```

becomes:

```python
f'{context_button}{focus_link}{running_label}{session_link}{dropdown}'
```

Leave the now-unused `.guide-button` CSS rule (lines 371-375, 432) and `--guide-surface`/`--guide-ink` custom properties (lines 87-88) in place for now — removing unreferenced CSS is a separate cleanup, not part of this leak/breakage fix, and touching more than necessary here risks an unrelated visual regression in a P0 fix.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/test_shared_ui.py::test_nav_bar_has_no_dead_guide_panel_reference -v`
Expected: PASS

- [ ] **Step 5: Run the full shared_ui and static-asset suites to check for regressions**

Run: `uv run pytest -q tests/test_shared_ui.py tests/test_curation_server_static_assets.py -v`
Expected: all PASS — no other test currently asserts on the Guide button's presence (confirmed: the button had no click handler, so nothing downstream depends on it existing).

- [ ] **Step 6: Commit**

```bash
git add src/clawmarks/shared_ui.py tests/test_shared_ui.py
git commit -m "fix(ui): remove the Guide button's dead aria-controls reference"
```

---

## Final Verification

- [ ] Run the full suite once: `uv run pytest -q`
- [ ] Confirm all 7 GitHub issues (#58-#64) have a corresponding commit by title; close each issue referencing its commit.
- [ ] Grep the diff for any remaining literal `illustrious_v0.1.safetensors` or `clawmarks-illustrious-v3-epoch4.safetensors` outside `config.py` to confirm Task 4's dedup is complete: `git diff main --stat` then `rg -n "illustrious_v0.1.safetensors|clawmarks-illustrious-v3-epoch4" src/clawmarks/`.
- [ ] Manually hit `/status.html` and `/api/searchrun/report?expedition=<real>&leg=<real>` against a real local server instance and visually confirm no absolute path or dollar balance appears in either response, per this project's CLAUDE.md rule to verify a live-server change with a live check, not just passing tests.
