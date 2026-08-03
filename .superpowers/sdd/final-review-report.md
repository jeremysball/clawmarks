# Final Review: preference-classifier Phase 1 (Tasks 1-8)

Range: `ecefb65..e228bc3` on `preference-classifier-phase-1`. Diff read in full;
implementation cross-checked against the live worktree at `/workspace/trent-phase1-worktree`.

## Strengths

- **Clean separation of concerns, honestly tested.** Each new module splits pure logic from
  I/O and tests the pure part directly, matching the repo's existing pattern
  (`test_seed_pool.py`, `test_scoring.py`):
  `rating_sampler.pick_next`, `curation_server.record_rating` / `next_rating_response`,
  `migrate_picks_to_ratings.merge_picks_into_ratings`, and the `embed_cache` helpers
  (`missing_tags`, `sync`, `load_cache`, `save_cache`) are all unit-tested without booting an
  HTTP server or loading the real DINOv2 model. The `FakeModel` in `test_embed_cache.py`
  derives a deterministic embedding from pixel means, so the tests exercise the cache's own
  batching/ordering/caching logic rather than the network-fetched backbone.
- **TDD followed faithfully.** Tests were written first and the implementations match the plan
  snippets. The one documented deviation, `embed_cache.save_cache` wrapping `np.savez` in
  `with open(tmp, "wb") as f: np.savez(f, ...)`, is correct and worth confirming: `np.savez`
  called with a *path string* opens and closes its own temp file, and `os.replace` can race
  that close on some platforms, producing `FileNotFoundError`. Passing an already-open file
  handle makes the flush happen on the caller's `with` block, so `os.replace` sees a complete
  file. The reasoning holds; the fix is right.
- **Migration is safe and idempotent.** `merge_picks_into_ratings` skips any tag that already
  has a rating (whatever its label), so reruns are no-ops; `main` writes via `tmp` +
  `os.replace` (atomic), and leaves `user_picks.json` on disk per the spec. The "deliberate
  later rating beats old pick" ordering is documented in the docstring.
- **Stratification is genuine.** `pick_next` chooses a *bin* uniformly at random, then an item
  uniformly within it, so a sparse bin with one eligible image is exactly as likely to be
  sampled as a dense bin with hundreds. `test_pick_next_can_return_from_a_sparsely_populated_bin`
  proves this directly, the property the spec needs to keep an early session from
  over-sampling late-generation exploit-heavy images.
- **`record_rating` is immutable and validating.** It copies `dict(ratings)`, rejects labels
  outside `("yes", "no")` with `ValueError`, and overwrites (never duplicates) on re-rating,
  meeting the spec's "re-rating overwrites" requirement.
- **`embed_cache.sync` meets the spec's error contract.** It raises `FileNotFoundError`
  listing the offending tag when a manifest tag's image file is missing, rather than silently
  skipping it (spec, "Error handling"). It embeds only `missing_tags`, preserving tag/embedding
  row alignment through `list(tags) + to_add`.
- **`elite_archive.py` fallback correctly keyed off yes-ratings.** `picks = {tag: r for tag, r
  in ratings.items() if r.get("label") == "yes"}` keeps the downstream `n_human`,
  `picked_here`, and `.human` CSS working with no further churn, exactly as the plan argued.
- All file paths come from `clawmarks.config`; no hardcoded `/workspace/...` strings introduced.

## Issues

### Critical (Must Fix)

None.

### Important (Should Fix)

**1. `scan_gallery.py` and `map_view.py` still call the removed `/api/picks` endpoint,
silently breaking after this phase.**

- `src/clawmarks/build/scan_gallery.py:254` — `fetch('/api/picks').then(...).catch(() => {})`
- `src/clawmarks/build/scan_gallery.py:369` — `document.addEventListener('lightbox:pick', ...)`
- `src/clawmarks/build/map_view.py:140` — `fetch('/api/picks').then(...).catch(() => {})`

Task 4 removed `GET /api/picks`, `POST /api/pick`, `POST /api/unpick`. These two build pages
were not in the plan's file list, so they still ship the dead fetch and the dead
`lightbox:pick` listener. After this phase merges, both fetches 404; `.catch(() => {})`
swallows the error, so `picks` stays `{}`. User-visible regressions:

- `scan.html`: the star "picked winner" badge (`scan_gallery.py:330`), the `pickedOnly` filter
  (`:283`, now matches zero images), and the "N picked" count in the status bar
  (`:316`) all stop reflecting any human judgment.
- `map.html`: gold winner dots and enlarged pick markers (`map_view.py:186,190,226`) no longer
  render.

This is the "integrates cleanly with surrounding code" check the brief flags: the plan retired
picks globally but only migrated the lightbox and `elite_archive` to ratings, leaving two more
browsing pages calling a removed endpoint. The plan's own verification grep
(`grep -rn "lb-pick\|togglePick\|loadPicks" src/`) was too narrow: it checked the lightbox's
*internal* names but not the `/api/picks` URL or the `lightbox:pick` event name, so it missed
these.

Why it matters: these pages are the project owner's primary browsing surfaces, and the whole
point of the migration is to keep human-curation highlights visible through the new mechanism,
not to delete them.

Fix: migrate both pages the way `elite_archive.py`'s JS did, replacing the `/api/picks` fetch
with `/api/ratings` filtered to `label === 'yes'`:

```javascript
fetch('/api/ratings').then(r => r.json()).then(ratings => {
  picks = {};
  Object.entries(ratings).forEach(([tag, r]) => { if (r.label === 'yes') picks[tag] = true; });
  render();   // or draw() in map_view
}).catch(() => { render(); });
```

Also delete the dead `lightbox:pick` listener in `scan_gallery.py:369` (the pick button that
fired it no longer exists after Task 5). Renaming the local `picks` variable to `yesRated` (or
keeping the name and just changing semantics) is optional; the existing `picks[tag]` truthiness
checks keep working either way.

**2. `curation_server.load_manifest()` caches `scored_manifest.json` for the server's lifetime.**

`curation_server.py:164-171`:

```python
_manifest_cache = {"manifest": None}

def load_manifest():
    if _manifest_cache["manifest"] is None:
        with open(f"{SWEEP_DIR}/scored_manifest.json") as f:
            _manifest_cache["manifest"] = json.load(f)
    return _manifest_cache["manifest"]
```

The old `/api/picks` path loaded `user_picks.json` fresh on every request; the manifest was
never server-side state. This phase introduces an in-memory manifest cache, so images added to
`scored_manifest.json` by a later `search/driver.py` run while the curation server is up never
become eligible for rating. Worse, `next_rating_response` computes `reviewed` against the
*stale* manifest, so once the stale set is fully reviewed `/api/rate/next` returns
`{"done": true}` even though hundreds of new images exist on disk. The rating UI's entire
purpose is to grow labels against the current pool, so this silently defeats it until the server
is restarted.

Why it matters: a silent "nothing left to rate" with real work remaining is exactly the kind
of hidden failure the project's gotcha log exists to catch.

Fix (simplest): drop the cache and load on each request (the manifest is a few-MB JSON read
under `_lock` on each `/api/rate/next`; the old code did the equivalent for picks on every
page load and that was fine). If the read cost matters, invalidate on mtime:

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

### Minor (Nice to Have)

- **Terminal print wording is stale in `elite_archive.py`.** The page copy was updated to
  "yes-rated winners" but the final print still says `N human-picked elites`
  (`elite_archive.py`, last line of `main`). The new test pins the old wording, so fixing the
  string means updating the test assertion too. Cosmetic, but the terminal is part of the
  project's running record and the wording is now technically wrong.

- **`next_rating_response`'s `rng is not None` guard is a smell.**
  `curation_server.py:149-150` branches on `rng` because `rating_sampler.pick_next`'s default
  parameter is `rng=random` (the module), and passing `rng=None` explicitly would call
  `None.choice` and crash. Simpler:

  ```python
  def pick_next(manifest, reviewed_tags, rng=None):
      rng = rng or random
      ...
  ```

  Then `next_rating_response` can call `pick_next(manifest, reviewed_tags, rng=rng)` unconditionally.
  Not wrong as shipped; just awkward.

- **`rate.html` has no fetch error handling and can double-submit on rapid key presses.**
  `loadNext()` (`rate_page.py`, JS) has no `.catch` on the `/api/rate/next` fetch; a server or
  network error leaves the spinner-free stage hung with no message. `rate()` keeps `current`
  set until the POST's `.then` resolves and `loadNext` reassigns it, so two quick key presses
  on the same image POST the same tag twice. Setting `current = null` at the top of `rate()`
  (and re-enabling on the next `loadNext`) closes the double-submit; adding a `.catch` to
  both fetches with a visible error keeps the UI from hanging. UX robustness only.

- **`embed_paths` divides by `feats.norm` without a zero guard.**
  `embed_cache.py` `feats = feats / feats.norm(dim=-1, keepdim=True)`. A model output that is all
  zeros for a corrupt/blank image yields `0/0` -> `NaN`, which then silently flows into the
  cache and downstream training. Unlikely for real DINOv2 output, but a one-line
  `feats / feats.norm(...).clamp(min=1e-12)` would make it impossible. Nit.

- **`/api/rate` has no auth and the server binds `0.0.0.0` (pre-existing, not introduced here).**
  The brief asks about exposure beyond localhost: any client that can reach the port can write
  ratings. This is consistent with the existing `/api/favorite` / `/api/counterfactual` design
  (the counterfactual endpoint is strictly more dangerous because it spends RunPod budget), so
  this phase doesn't make things worse. If the server is ever reachable off the tailnet,
  `/api/rate` is externally writable, but the impact is limited to polluting the labels file.
  Worth a note as a Recommendation, not a blocker for this phase.

## Recommendations

1. Fix Issue 1 (scan_gallery / map_view) before merge. It's a direct, silent regression in two
   of the project owner's primary browsing surfaces, caused by the global endpoint removal, and
   the fix is a straightforward port of what `elite_archive.py`'s JS already does.
2. Fix Issue 2 (manifest cache) before the rating UI is relied on for a real labeling session.
   If you'd rather defer it, at minimum document the "restart server after a search run" caveat
   in the module docstring so the next session doesn't re-derive it from a hung UI.
3. Adopt the `rate()` `current = null` guard and the `.catch` handlers in `rate.html` in the
   same pass, since they're a few lines each and the page is new.
4. No new dependencies were added in Tasks 1-8 (scikit-learn is Task 9), so the
   `uv add ==<version>` pinning constraint is not exercised by this range. Confirmed: the diff
   touches only `src/` and `tests/`, not `pyproject.toml` / `uv.lock`.

## Assessment

**Ready to merge?** With fixes.

**Reasoning:** The pure-logic modules, migration, sampler, embedding cache, and test coverage
are solid and plan-aligned, including the documented `save_cache` deviation. Two integration
gaps ship broken client-side behavior: `scan_gallery.py` and `map_view.py` still fetch the
removed `/api/picks`, and `curation_server.load_manifest()`'s lifetime cache makes the rating
UI silently stop serving new images after any search run while the server is up. Issue 1 is the
merge blocker; Issue 2 should be fixed before real labeling but could ship documented if
pressed. Neither reflects a flaw in the plan itself; both are scope gaps the plan's narrow
verification grep missed.