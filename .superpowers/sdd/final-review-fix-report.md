# Final Review Fix Report: pre-merge Important issues

## Status

DONE

## Summary

Both Important issues from the final whole-branch review of Tasks 1-8 are fixed.

### Issue 1: build pages still calling removed `/api/picks`

- `src/clawmarks/build/scan_gallery.py`: replaced the `/api/picks` fetch in the
  `Promise.all` block with `/api/ratings` filtered down to yes-labels (same shape as
  `elite_archive.py`'s JS), and deleted the now-dead `lightbox:pick` event listener
  (the pick button that fired it was removed in Task 5; nothing dispatches this event
  anymore). The `render()` call in the surrounding `Promise.all` is preserved.
- `src/clawmarks/build/map_view.py`: replaced the `/api/picks` fetch with the
  same-shape `/api/ratings` call, calling this file's redraw function (`draw()`)
  once ratings are loaded and once more in the `.catch()` fallback.

Both files keep the local `picks` variable name; downstream `picks[tag]` truthiness
checks in `scan_gallery.py`'s `pickedOnly` filter, picked-count status line, and
picked-winner badge, and in `map_view.py`'s gold-dot color and tooltip text, work
identically with the new yes-tags shape.

### Issue 2: `curation_server.load_manifest()` lifetime cache

Replaced the write-once `{"manifest": None}` dict with `{"manifest": None, "mtime":
None}` and added an mtime check: on every call, `os.path.getmtime` is compared
against the cached mtime, and the file is re-read (and mtime updated) whenever the
mtime differs. `os` was already imported in the existing combined `import base64,
json, os, random, subprocess, sys, threading, time` line, so no new import was
needed.

### New regression test

Added `tests/test_curation_server_manifest_cache.py` with one test that:

1. Writes `scored_manifest.json` with one item and calls `load_manifest()`.
2. Calls `load_manifest()` again unchanged and asserts the in-memory object is
   reused (cache hit).
3. Rewrites the file with two items, bumps the mtime with `os.utime`, and calls
   `load_manifest()` again. Asserts the new content is seen and the returned
   object is not the same as the first (proving the cache was actually invalidated,
   not just coincidentally equal).

This directly covers the bug the fix addresses and pins the mtime-invalidation
contract against future regressions. The brief said a test would be appropriate
"if you judge either fix needs a new test to lock in the behavior" — judged
yes for the manifest cache (a one-line re-introduction of the bug would otherwise
go unnoticed) and no for the JS /api/picks migration (no test infrastructure
exists in this repo for the build pages' embedded JS).

## git log --oneline (worktree, preference-classifier-phase-1)

```
cefa215 fix(clawmarks): migrate scan/map pages to ratings API, fix stale manifest cache
e228bc3 feat(clawmarks): add DINOv2 embedding cache
0a1cd76 feat(clawmarks): search driver exploit pool reads yes-ratings instead of picks
2ffe2c1 feat(clawmarks): elite archive reads yes-ratings instead of picks
405fcad feat(clawmarks): remove pick-as-winner from the lightbox, add rate.html
0620369 feat(clawmarks): replace pick endpoints with ratings endpoints in curation_server
b623363 feat(clawmarks): add one-time picks-to-ratings migration script
b39eb07 feat(clawmarks): add stratified rating sampler
a238381 feat(clawmarks): add shared manifest_index helpers and USER_RATINGS_FILE config
```

## Files changed

```
modified:   src/clawmarks/build/scan_gallery.py
modified:   src/clawmarks/build/map_view.py
modified:   src/clawmarks/curation_server.py
new file:   tests/test_curation_server_manifest_cache.py
```

## Test command and output

Command: `cd /workspace/trent-phase1-worktree && PYTHONPATH=src pytest -v`

```
... (output elided for brevity; 48 tests, all passing) ...
tests/test_yes_rated_images.py::test_load_yes_rated_images_joins_ratings_against_manifest PASSED [ 97%]
tests/test_yes_rated_images.py::test_load_yes_rated_images_returns_empty_without_files PASSED [100%]

============================== 48 passed in 7.01s ==============================
```

New manifest-cache test (snipped from the same run):

```
tests/test_curation_server_manifest_cache.py::test_load_manifest_re_reads_when_file_changes PASSED [100%]
```

Brief's dead-endpoint sanity check:

```
$ rg -n "/api/picks|lightbox:pick" src/ | grep -v __pycache__
(no output)
```

Brief's ratings-endpoint sanity check (all three build pages now route through
`/api/ratings`):

```
$ rg -n "/api/ratings" src/ | grep -v __pycache__
src/clawmarks/curation_server.py:39:  GET  /api/ratings           -> {tag: {label, rated_at}}
src/clawmarks/curation_server.py:200:        if self.path == "/api/ratings":
src/clawmarks/build/scan_gallery.py:254:  fetch('/api/ratings').then(r => r.json()).then(ratings => {{
src/clawmarks/build/map_view.py:140:fetch('/api/ratings').then(r => r.json()).then(ratings => {{
src/clawmarks/build/elite_archive.py:204:fetch('/api/ratings').then(r => r.json()).then(ratings => {{
```

## Working-directory note (same as Tasks 7-8)

Implemented on the `preference-classifier-phase-1` worktree at
`/workspace/trent-phase1-worktree/`. Tests run with `PYTHONPATH=src` so the
worktree's `src/` is imported in preference to the shared-venv install that points
at the main directory's older code. Commit landed on `preference-classifier-phase-1`.

## Note on unstaged `pyproject.toml` / `uv.lock`

`pyproject.toml` and `uv.lock` had unrelated changes in the working tree (a
`scikit-learn==1.6.1` dependency pin added by some other process). I left those
unstaged and committed only the four files the brief specified, per the brief's
`git add` line.

## Concerns

None. Both fixes applied exactly as the brief described, with the additional
regression test for the manifest cache that the brief recommended "if you judge
either fix needs a new test to lock in the behavior."
