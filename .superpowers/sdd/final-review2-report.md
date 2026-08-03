# Final Review: `feat/preference-toggle` branch (9da9ad1..6c3056c)

## Overall Verdict

**Ready to merge as-is.** Both features match their specs and plans, Tasks 1 through 5 are
fully present (Task 6 intentionally dropped per project owner), all 137 tests pass, the
rate.html scrollback feature was already independently designed, implemented, verified with
live Playwright browser testing, and code-reviewed before being merged into this branch. The
findings below are all Minor/nitpick; none block merge. The server-side gate on the toggle
endpoint is present and tested, the atomic write pattern is consistent with the rest of the
codebase, and the LiveCache integration invalidates correctly on settings file changes.

## Findings

### Minor / nitpick

1. **`POST /api/preference_toggle` doesn't guard `preference_settings.save()` with `_lock`**
   `src/clawmarks/curation_server.py:512`. Every other POST route that writes a JSON store
   (`/api/rate`, `/api/favorite`, `/api/unfavorite`) wraps its read-modify-write in
   `with _lock`. The toggle route skips it, relying on `preference_settings.save()`'s atomic
   tmp-then-`os.replace`. That's safe against corruption (replace is atomic), and the only
   consequence of a concurrent toggles race is "last writer holds the boolean," which is
   harmless for a single-user toggle. The omission is defensible, but inconsistent with the
   file's own pattern. If a future reader applies Cargo-cult consistency and adds the lock,
   keep `preference_settings.save()` atomic either way; the lock alone doesn't make replace
   non-atomic, it just serializes. Optional to add.

2. **No test for toggling `enabled: false` or for non-boolean `enabled`**
   `tests/test_curation_server_preference_status_route.py`. The suite covers the two most
   meaningful paths (enable with no model -> 400, enable with model -> 200 + persists), but
   skips the disable path and the `isinstance(enabled, bool)` validation branch. Both are
   one-liner code paths and low risk. The disable path matters slightly because it's the
   normal way a user turns the feature back off after experimenting; a passing test on it
   would lock in that the response still carries `use_predicted_preference: false`. Optional
   gap, not a merge blocker.

3. **`compute_data` synthesizes a `y` numpy array just to feed `class_balance_error`**
   `src/clawmarks/build/preference_status.py:31-33`. The balance check only reads `y.sum()`
   and `len(y)`, so constructing `np.array([1]*n_yes + [0]*n_no)` does more work than needed.
   The plan spec'd this exact shape, and it's read-only status code so the cost is trivial.
   Noting it only because a lighter-weight helper (`class_balance_error(n_yes, n_no)` taking
   integers) would avoid importing numpy into a status-page module at all, which is the
   reason the `import numpy as np` is deferred inline rather than at module top. The
   defer-inline-import is a mild code smell that the array construction itself creates.

4. **`compute_data`'s label counts can differ from `preference_model.main`'s training set**
   `src/clawmarks/build/preference_status.py:23-25` counts every `"yes"`/`"no"` entry in
   `user_ratings.json`, while `preference_model.build_training_set` filters to tags present in
   the embedding cache. The status page's counts are therefore an upper bound on what train
   actually uses. This is by design (the plan notes it: the page shows readiness, the gate
   uses the same `MIN_LABELS` constant), and in practice the embedding cache covers the whole
   manifest, so the two counts agree. Worth knowing if `user_ratings.json` ever holds tags
   not in the cache, but not a defect.

5. **rate.html pre-existing em dash removed, no new em dashes introduced**
   The diff replaces `bakes in no per-image data at build time — it fetches` (with a real `—`)
   with the period-separated form, which is the only content-level em dash change in the
   range. The `// --- zoom ---` comment dividers and unified-diff `---` file headers picked up
   by an em-dash grep are not prose. Writing-style rule satisfied.

## What was verified

- All 137 tests pass (`PYTHONPATH=src uv run pytest tests/ -v`), including 10 new tests for
  the preference-toggle feature (4 settings, 2 shared_ui nav, 7 preference_status compute/render,
  5 curation_server route) and the pre-existing 35 test_preference_model suite with the new
  sidecar test.
- Server-side gate: `POST /api/preference_toggle` returns 400 when `enabled: true` and
  `MODEL_FILE` doesn't exist, tested at `test_curation_server_preference_status_route.py:47`.
- `archive.html` no longer parses the query string; the test at line 74 explicitly asserts
  `?use_predicted_preference=1` is ignored (`calls == [False]`) and the persisted setting
  drives the render (`calls == [False, True]`).
- Atomic write: `preference_settings.save` uses `f"{path}.tmp"` + `os.replace`, matching
  `embed_cache.save_cache` and `save_store`. Test for no leftover tmp at line 19.
- LiveCache integration: `_preference_status_watched_files` conditionally includes each file
  only if it exists (same pattern as `_solution_map_watched_files`), so a settings file
  appearing for the first time (on first toggle) changes the watched-file set and correctly
  invalidates the cache on the next `_get_preference_status_data()` call.
- Task 6 (clI default resolution) is absent as stated; its scope (cli.py, driver default) is
  not partially landed or half-wired.

REVIEW_COMPLETE