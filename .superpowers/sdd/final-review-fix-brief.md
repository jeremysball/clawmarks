# Fix brief: final whole-branch review findings (preference-classifier Phase 1)

The final review of Phase 1 (Tasks 1-8, commits `ecefb65..e228bc3` on
`preference-classifier-phase-1`) found no Critical issues but two Important ones that must be
fixed before merge. Fix both in one pass.

## Issue 1: `scan_gallery.py` and `map_view.py` still call the removed `/api/picks` endpoint

Task 4 removed `GET /api/picks`, `POST /api/pick`, `POST /api/unpick` from
`src/clawmarks/curation_server.py`. Task 5 migrated the lightbox and Task 6 migrated
`elite_archive.py` to the new ratings API, but two more build pages were never touched and
still fetch the dead endpoint:

- `src/clawmarks/build/scan_gallery.py:254` — `fetch('/api/picks').then(...).catch(() => {})`
- `src/clawmarks/build/scan_gallery.py:369` — `document.addEventListener('lightbox:pick', ...)`
  (dead listener — the pick button that fired this event no longer exists after Task 5)
- `src/clawmarks/build/map_view.py:140` — `fetch('/api/picks').then(...).catch(() => {})`

After merge, both fetches 404 (silently, since both have `.catch(() => {})`), so `picks` stays
`{}` forever. This breaks: `scan.html`'s star "picked winner" badge, its `pickedOnly` filter
(now matches zero images), and its "N picked" status count; and `map.html`'s gold winner dots
and enlarged pick markers.

### Fix

In `scan_gallery.py`, replace the `/api/picks` fetch (around line 254) with the same pattern
`elite_archive.py`'s JS already uses:

```javascript
fetch('/api/ratings').then(r => r.json()).then(ratings => {
  picks = {};
  Object.entries(ratings).forEach(([tag, r]) => { if (r.label === 'yes') picks[tag] = true; });
  render();
}).catch(() => { render(); });
```

(Use whatever the surrounding code's actual re-render function is called — check the file for
the correct call, it may not be exactly `render()`.)

Delete the dead `lightbox:pick` event listener block at `scan_gallery.py:369` entirely (the
button that fired it was removed in Task 5; nothing dispatches this event anymore).

In `map_view.py`, replace the `/api/picks` fetch (around line 140) with the equivalent, calling
whatever this file's redraw function is (likely `draw()`):

```javascript
fetch('/api/ratings').then(r => r.json()).then(ratings => {
  picks = {};
  Object.entries(ratings).forEach(([tag, r]) => { if (r.label === 'yes') picks[tag] = true; });
  draw();
}).catch(() => { draw(); });
```

Keep the existing local variable name `picks` in both files — it's referenced elsewhere in each
file's rendering logic (badges, filters, markers) and those call sites don't need to change,
since `picks[tag]` truthiness checks work identically whether `picks` came from the old
`/api/picks` shape or this new yes-rated-tags shape.

## Issue 2: `curation_server.load_manifest()` caches `scored_manifest.json` for the server's lifetime

`src/clawmarks/curation_server.py` around lines 164-171:

```python
_manifest_cache = {"manifest": None}

def load_manifest():
    if _manifest_cache["manifest"] is None:
        with open(f"{SWEEP_DIR}/scored_manifest.json") as f:
            _manifest_cache["manifest"] = json.load(f)
    return _manifest_cache["manifest"]
```

If `search/driver.py` appends new images to `scored_manifest.json` while the curation server is
already running, this cache never picks them up: `next_rating_response` computes "reviewed"
against the stale in-memory manifest, so once the stale set is fully rated, `/api/rate/next`
returns `{"done": true}` even though new images exist on disk. This silently defeats the whole
point of the rating UI (labeling against the current pool) until the server is restarted.

### Fix

Replace it with an mtime-invalidated cache:

```python
import os

_manifest_cache = {"manifest": None, "mtime": None}

def load_manifest():
    path = f"{SWEEP_DIR}/scored_manifest.json"
    mtime = os.path.getmtime(path)
    if _manifest_cache["manifest"] is None or _manifest_cache["mtime"] != mtime:
        with open(path) as f:
            _manifest_cache["manifest"] = json.load(f)
        _manifest_cache["mtime"] = mtime
    return _manifest_cache["manifest"]
```

(`import os` — check whether `curation_server.py` already imports `os` at the top before adding
a duplicate import.)

## Verify

Run the full suite after both fixes:

```bash
PYTHONPATH=/workspace/trent-phase1-worktree/src pytest -v
```

Expected: all tests still pass (no test currently covers these two files' JS or the manifest
cache directly, so this is a regression check, not a red-to-green cycle). If you judge either
fix needs a new test to lock in the behavior, add one — for `load_manifest`, a test that writes
`scored_manifest.json`, calls `load_manifest()`, rewrites the file with new content and a forced
mtime bump, calls `load_manifest()` again, and asserts the second call sees the new content
would directly cover the bug this fix addresses.

## Commit

```bash
git add src/clawmarks/build/scan_gallery.py src/clawmarks/build/map_view.py src/clawmarks/curation_server.py
git commit -m "fix(clawmarks): migrate scan/map pages to ratings API, fix stale manifest cache"
```

(If you added a test file for the manifest-cache fix, include it in the `git add` too.)

## Global Constraints (same as the rest of this plan)

- All file paths in code come from `clawmarks.config` (`ROOT`, `SWEEP_DIR`, etc.), never a
  hardcoded `/workspace/trent-with-smart-prompts` string.
- Favoriting (`user_favorites.json`, the star/bookmark button, `/api/favorite`,
  `/api/unfavorite`) is never touched by this fix.
- Don't touch anything outside these two issues — the rest of the review's findings (Minor
  category) are being handled separately, not as part of this fix.
