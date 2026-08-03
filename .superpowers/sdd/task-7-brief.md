# Task 7: `search/driver.py` exploit pool reads yes-ratings (Stage 5a)

Context: Task 6 (just completed) switched the elite-archive build page from
`user_picks.json` to `user_ratings.json`'s yes-labels. This task makes the same switch in
the search driver itself: the exploit step's seed pool (previously "human picks") now comes
from yes-rated images instead.

## Files

- Modify: `src/clawmarks/search/driver.py`
- Modify: `tests/test_generation_jobs.py` (no changes expected — confirms `build_generation_jobs`
  itself is untouched; this task only changes what feeds it)
- Create: `tests/test_yes_rated_images.py`

## Interfaces

- Consumes: `manifest_index.index_by_tag` (already implemented in
  `src/clawmarks/search/manifest_index.py` by an earlier task in this plan).
- Produces: `driver._load_yes_rated_images() -> list[dict]`, replacing `_load_user_picks()`
  everywhere it was called.

## Step 1: Write the failing test

```python
# tests/test_yes_rated_images.py
import json

from clawmarks.search import driver


def test_load_yes_rated_images_joins_ratings_against_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "SWEEP_DIR", tmp_path)
    manifest = [
        {"tag": "a", "prompt_name": "p", "prompt": "trentbuckle style, a", "strength": 1.0,
         "cfg": 7.0, "centroid_sim": 0.5, "novelty": 0.5, "file": "a.png"},
        {"tag": "b", "prompt_name": "p", "prompt": "trentbuckle style, b", "strength": 1.0,
         "cfg": 7.0, "centroid_sim": 0.5, "novelty": 0.5, "file": "b.png"},
    ]
    (tmp_path / "scored_manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "user_ratings.json").write_text(json.dumps({
        "a": {"label": "yes", "rated_at": "t0"},
        "b": {"label": "no", "rated_at": "t0"},
    }))
    result = driver._load_yes_rated_images()
    assert [m["tag"] for m in result] == ["a"]


def test_load_yes_rated_images_returns_empty_without_files(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "SWEEP_DIR", tmp_path)
    assert driver._load_yes_rated_images() == []
```

## Step 2: Run test to verify it fails

Run: `pytest tests/test_yes_rated_images.py -v`
Expected: FAIL with `AttributeError: module 'clawmarks.search.driver' has no attribute '_load_yes_rated_images'`

## Step 3: Modify `driver.py`

Add to the imports near the top of the file:

```python
from clawmarks.search.manifest_index import index_by_tag
```

Replace `_load_user_picks()`:

```python
def _load_user_picks():
    """Human-in-the-loop MAP-Elites: this project has no automated coherence/quality scorer,
    so per lab_notebook.md Section 3b there's no way for an image to automatically 'win' a
    bin. A person reviewing notes/uncanny_sweep/scan.html (served by
    notes/curation_server.py, which is what actually persists picks) can mark specific images
    as winners instead. When present, those picks anchor the exploit step's mutations in
    place of the raw novelty ranking, which is only ever a proxy for 'interesting,' not a
    verdict on it."""
    if SWEEP_DIR.joinpath("user_picks.json").exists():
        with open(SWEEP_DIR / "user_picks.json") as f:
            picks = json.load(f)
        return list(picks.values())
    return []
```

with:

```python
def _load_yes_rated_images():
    """Ratings supersede picks: a human's yes/no judgment on an image, not raw novelty, decides
    what the exploit step mutates near. user_ratings.json stores only {label, rated_at} per tag
    (the image metadata already lives in scored_manifest.json), so yes-rated tags are joined
    against that manifest to recover prompt/strength/cfg for mutation."""
    ratings_path = SWEEP_DIR / "user_ratings.json"
    manifest_path = SWEEP_DIR / "scored_manifest.json"
    if not ratings_path.exists() or not manifest_path.exists():
        return []
    with open(ratings_path) as f:
        ratings = json.load(f)
    yes_tags = {tag for tag, r in ratings.items() if r.get("label") == "yes"}
    if not yes_tags:
        return []
    with open(manifest_path) as f:
        manifest = json.load(f)
    by_tag = index_by_tag(manifest)
    return [by_tag[t] for t in yes_tags if t in by_tag]
```

Update the call site in `main()`:

```python
        user_picks = _load_user_picks() if cfg.seed_from_start else []
```

to:

```python
        user_picks = _load_yes_rated_images() if cfg.seed_from_start else []
```

(`build_generation_jobs`'s parameter stays named `user_picks` — it's an internal name meaning
"the exploit seed pool," and `tests/test_generation_jobs.py` already exercises it directly by
keyword; renaming it is out of scope for this task and would touch tests that don't need to
change.)

## Step 4: Run tests to verify they pass

Run: `pytest tests/test_yes_rated_images.py tests/test_generation_jobs.py -v`
Expected: PASS (2 new tests, 4 existing tests untouched and still passing)

Run the full suite: `pytest -v`
Expected: all PASS. `rg -n "_load_user_picks|user_picks.json" src/` should return nothing
under `src/clawmarks/search/driver.py` (a hit in `migrate_picks_to_ratings.py` and `config.py` is
expected and correct — those still read the historical file on purpose).

## Step 5: Commit

```bash
git add src/clawmarks/search/driver.py tests/test_yes_rated_images.py
git commit -m "feat(clawmarks): search driver exploit pool reads yes-ratings instead of picks"
```

## Global Constraints

- Conventional Commits format for the commit message.
- No changes to files outside the listed set.
- Don't rename `build_generation_jobs`'s `user_picks` parameter — out of scope.
