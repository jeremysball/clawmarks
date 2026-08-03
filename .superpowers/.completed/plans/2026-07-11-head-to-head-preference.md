# Head-to-Head Preference Comparisons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the yes/no `rate.html` preference system with head-to-head comparisons: show two images, the user picks a winner, and a pairwise (Bradley-Terry-style) model trained on those comparisons ranks the whole pool.

**Architecture:** A new pairwise model module (`search/preference_pairwise_model.py`) trains a logistic regression on embedding differences between winners and losers. A new pair sampler (`search/comparison_sampler.py`) picks stratified-random pairs below a comparison floor, then model-uncertainty-guided pairs above it. A new UI (`build/compare_page.py`, served as `compare.html`) replaces `rate.html`. `curation_server.py` swaps its rating endpoints for comparison endpoints and retrains the model periodically. Four downstream consumers (`elite_archive.py`, `driver.py`, `preference_rank.py`, `preference_status.py`) swap from the old yes/no model to the new pairwise one; the two that used "yes-rated image wins" as a manual-override signal switch to favorites instead, since yes/no ratings no longer exist.

**Tech Stack:** Python, `sklearn.linear_model.LogisticRegression`, `joblib`, `numpy`, vanilla JS/HTML (no framework), `pytest`.

## Global Constraints

- `MIN_COMPARISONS = 50` — training floor, mirrors the old `MIN_LABELS`.
- `RETRAIN_EVERY = 10` — retrain cadence once at/above the floor.
- `CANDIDATE_POOL_SIZE = 200` — sample size for uncertainty-guided pair selection.
- `user_ratings.json` and `preference_model.joblib` (old yes/no artifacts) are never deleted, migrated, or read by any code after this plan ships. They stay on disk, untouched, unused.
- New model files use new names (`preference_pairwise_model.joblib`, `preference_pairwise_model_meta.json`) so they never collide with the legacy files in the same directory.
- `elite_archive.py`'s and `driver.py`'s old "yes-rated image wins" manual-override tier becomes "favorited image wins," reading `user_favorites.json` (already exists, untouched by this plan) instead of `user_ratings.json`.
- Spec: `docs/superpowers/specs/2026-07-11-head-to-head-preference-design.md`.

---

### Task 1: Pairwise preference model

**Files:**
- Create: `src/clawmarks/search/preference_pairwise_model.py`
- Test: `tests/test_preference_pairwise_model.py`

**Interfaces:**
- Consumes: `clawmarks.config.SWEEP_DIR` (existing), `clawmarks.search.embed_cache.load_cache` / `embed_cache.EMBEDDINGS_FILE` (existing, unchanged signatures: `load_cache(path) -> (tags: list, embeddings: np.ndarray)`).
- Produces: `MIN_COMPARISONS: int`, `MODEL_FILE: Path`, `MODEL_META_FILE: Path`, `build_training_set(tags, embeddings, comparisons) -> (X: np.ndarray, y: np.ndarray)`, `cross_validate(X, y) -> float`, `train(X, y) -> LogisticRegression`, `score(model, embeddings) -> np.ndarray`, `train_and_save(comparisons) -> dict | None` (keys `model`, `cv_accuracy`, `n_comparisons`), `main(argv=None) -> int`. Tasks 4, 6, 7, 8, 9 import `MODEL_FILE`, `MODEL_META_FILE`, `score`, and (task 4 only) `train_and_save`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_preference_pairwise_model.py
import numpy as np

from clawmarks.search import preference_pairwise_model as ppm


def test_build_training_set_mirrors_each_comparison_into_two_rows():
    tags = ["a", "b", "c"]
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0], [2.0, 2.0]], dtype=np.float32)
    comparisons = [{"winner": "a", "loser": "b", "compared_at": "t0"}]
    X, y = ppm.build_training_set(tags, embeddings, comparisons)
    assert X.shape == (2, 2)
    assert list(y) == [1, 0]
    assert np.allclose(X[0], [1.0, -1.0])
    assert np.allclose(X[1], [-1.0, 1.0])


def test_build_training_set_skips_comparisons_with_unknown_tags():
    tags = ["a"]
    embeddings = np.array([[1.0, 0.0]], dtype=np.float32)
    comparisons = [{"winner": "a", "loser": "missing", "compared_at": "t0"}]
    X, y = ppm.build_training_set(tags, embeddings, comparisons)
    assert X.shape == (0, 0)
    assert len(y) == 0


def test_build_training_set_handles_multiple_comparisons():
    tags = ["a", "b", "c", "d"]
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0], [2.0, 0.0], [0.0, 2.0]], dtype=np.float32)
    comparisons = [
        {"winner": "a", "loser": "b", "compared_at": "t0"},
        {"winner": "c", "loser": "d", "compared_at": "t1"},
    ]
    X, y = ppm.build_training_set(tags, embeddings, comparisons)
    assert X.shape == (4, 2)
    assert list(y) == [1, 1, 0, 0]


def test_train_and_score_orders_a_clearly_preferred_cluster_above_another():
    rng = np.random.RandomState(0)
    winners = rng.normal(loc=5.0, scale=0.1, size=(20, 2))
    losers = rng.normal(loc=-5.0, scale=0.1, size=(20, 2))
    diffs = (winners - losers).astype(np.float32)
    X = np.concatenate([diffs, -diffs])
    y = np.concatenate([np.ones(20), np.zeros(20)])
    model = ppm.train(X, y)
    scores = ppm.score(model, np.array([[5.0, 0.0], [-5.0, 0.0]], dtype=np.float32))
    assert scores[0] > scores[1]


def test_cross_validate_returns_a_valid_accuracy_using_leave_one_out_below_min_comparisons():
    rng = np.random.RandomState(0)
    X = rng.normal(size=(10, 2)).astype(np.float32)
    y = np.array([0, 1] * 5)
    acc = ppm.cross_validate(X, y)
    assert 0.0 <= acc <= 1.0


def test_train_and_save_returns_none_below_min_comparisons(tmp_path, monkeypatch):
    monkeypatch.setattr(ppm, "SWEEP_DIR", tmp_path)
    monkeypatch.setattr(ppm.embed_cache, "EMBEDDINGS_FILE", tmp_path / "embeddings.npz")
    comparisons = [{"winner": "a", "loser": "b", "compared_at": "t0"}] * 10
    assert ppm.train_and_save(comparisons) is None


def test_train_and_save_writes_model_and_meta_on_success(tmp_path, monkeypatch):
    from clawmarks.search import embed_cache

    rng = np.random.RandomState(0)
    tags = [f"t{i}" for i in range(120)]
    embeddings = rng.normal(size=(120, 2)).astype(np.float32)
    embed_cache.save_cache(tmp_path / "embeddings.npz", tags, embeddings)

    comparisons = [
        {"winner": tags[i], "loser": tags[i + 1], "compared_at": "t"}
        for i in range(0, 100, 2)
    ]

    monkeypatch.setattr(ppm, "SWEEP_DIR", tmp_path)
    monkeypatch.setattr(ppm.embed_cache, "EMBEDDINGS_FILE", tmp_path / "embeddings.npz")
    monkeypatch.setattr(ppm, "MODEL_FILE", tmp_path / "preference_pairwise_model.joblib")
    monkeypatch.setattr(ppm, "MODEL_META_FILE", tmp_path / "preference_pairwise_model_meta.json")

    result = ppm.train_and_save(comparisons)
    assert result is not None
    assert 0.0 <= result["cv_accuracy"] <= 1.0
    assert result["n_comparisons"] == 50
    assert (tmp_path / "preference_pairwise_model.joblib").exists()

    import json
    meta = json.loads((tmp_path / "preference_pairwise_model_meta.json").read_text())
    assert meta["n_comparisons"] == 50
    assert "trained_at" in meta


def test_main_refuses_without_comparisons_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ppm, "SWEEP_DIR", tmp_path)
    rc = ppm.main([])
    assert rc == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_preference_pairwise_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clawmarks.search.preference_pairwise_model'`

- [ ] **Step 3: Write the implementation**

```python
# src/clawmarks/search/preference_pairwise_model.py
"""
Trains a pairwise preference model on frozen DINOv2 embeddings (search/embed_cache.py) and the
user's head-to-head comparisons (user_comparisons.json), so images can be ranked by predicted
preference. Replaces search/preference_model.py's role: yes/no ratings are gone, comparisons are
head-to-head instead. See docs/superpowers/specs/2026-07-11-head-to-head-preference-design.md.

Fits a Bradley-Terry-style pairwise model with plain logistic regression: for each comparison,
the training row is embedding[winner] - embedding[loser] labeled 1, mirrored as its negation
labeled 0. The model learns a direction in embedding space such that "more in that direction"
predicts winning, which is why score() can rank any image in the pool, including one that was
never directly compared: it only depends on the image's own embedding, not a per-image win/loss
tally. Mirroring every row also guarantees exact class balance automatically, unlike the old
yes/no labels, so there's no balance-gate check needed here.

Refuses to train below MIN_COMPARISONS: with only a handful of comparisons, any model would be
overfitting noise, not learning taste. Run compare.html (via `clawmarks serve`) until this floor
is cleared.

Run with: python -m clawmarks.search.preference_pairwise_model
"""
import json
import os
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut, StratifiedKFold, cross_val_score

from clawmarks.config import SWEEP_DIR
from clawmarks.search import embed_cache

MIN_COMPARISONS = 50
MODEL_FILE = SWEEP_DIR / "preference_pairwise_model.joblib"
MODEL_META_FILE = SWEEP_DIR / "preference_pairwise_model_meta.json"


def build_training_set(tags, embeddings, comparisons):
    """`tags`/`embeddings` come from embed_cache.load_cache; `comparisons` is the loaded
    user_comparisons.json list. Returns (X, y): a mirrored pair of rows per usable comparison
    (embedding[winner] - embedding[loser] labeled 1, its negation labeled 0), skipping any
    comparison whose winner or loser tag isn't in the embedding cache."""
    tag_to_row = {t: i for i, t in enumerate(tags)}
    diffs = []
    for c in comparisons:
        winner, loser = c.get("winner"), c.get("loser")
        if winner not in tag_to_row or loser not in tag_to_row:
            continue
        diffs.append(embeddings[tag_to_row[winner]] - embeddings[tag_to_row[loser]])
    if not diffs:
        return np.zeros((0, 0), dtype=np.float32), np.zeros((0,), dtype=np.int64)
    diffs = np.stack(diffs)
    X = np.concatenate([diffs, -diffs])
    y = np.concatenate([np.ones(len(diffs)), np.zeros(len(diffs))])
    return X.astype(np.float32), y.astype(np.int64)


def cross_validate(X, y):
    """Mean cross-validated accuracy at predicting which side of a mirrored pair is the winner.
    Leave-one-out below MIN_COMPARISONS rows, since every row matters at that scale; 5-fold
    StratifiedKFold at or above it."""
    cv = LeaveOneOut() if len(y) < MIN_COMPARISONS else StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    scores = cross_val_score(LogisticRegression(max_iter=1000), X, y, cv=cv)
    return float(scores.mean())


def train(X, y):
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    return model


def score(model, embeddings):
    """Returns a higher-is-more-preferred score for each row of `embeddings`. Uses
    decision_function rather than predict_proba: the model was trained on embedding
    *differences*, so there's no single well-defined "P(yes)" for a lone image, but
    decision_function is monotonic with the model's implied preference ranking, which is all
    every caller (elite_archive.py, driver.py, preference_rank.py) needs to sort by."""
    return model.decision_function(embeddings)


def train_and_save(comparisons):
    """Trains on `comparisons` (an already-loaded list) and persists MODEL_FILE/MODEL_META_FILE.
    Returns {"model", "cv_accuracy", "n_comparisons"}, or None if there aren't enough usable
    comparisons to train on (fewer than MIN_COMPARISONS, or none reference tags present in the
    embedding cache)."""
    if len(comparisons) < MIN_COMPARISONS:
        return None
    tags, embeddings = embed_cache.load_cache(embed_cache.EMBEDDINGS_FILE)
    X, y = build_training_set(tags, embeddings, comparisons)
    if X.shape[0] == 0:
        return None
    acc = cross_validate(X, y)
    model = train(X, y)
    joblib.dump(model, MODEL_FILE)
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_comparisons": len(comparisons),
        "cv_accuracy": round(acc, 4),
    }
    tmp = f"{MODEL_META_FILE}.tmp"
    with open(tmp, "w") as f:
        json.dump(meta, f)
    os.replace(tmp, MODEL_META_FILE)
    return {"model": model, "cv_accuracy": acc, "n_comparisons": len(comparisons)}


def main(argv=None):
    comparisons_path = SWEEP_DIR / "user_comparisons.json"
    if not comparisons_path.exists():
        print(f"no comparisons file at {comparisons_path}; nothing to train on", flush=True)
        return 1
    with open(comparisons_path) as f:
        comparisons = json.load(f)

    if len(comparisons) < MIN_COMPARISONS:
        print(f"only {len(comparisons)} comparisons (need {MIN_COMPARISONS}); not training. "
              f"Compare more images via compare.html first.", flush=True)
        return 1

    result = train_and_save(comparisons)
    if result is None:
        print("no comparisons reference tags present in the embedding cache; nothing to train "
              "on. Run `python -m clawmarks.search.embed_cache` first.", flush=True)
        return 1

    print(f"{result['n_comparisons']} comparisons, cross-validated accuracy: "
          f"{result['cv_accuracy']:.3f}", flush=True)
    print(f"wrote {MODEL_FILE} and {MODEL_META_FILE}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_preference_pairwise_model.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add src/clawmarks/search/preference_pairwise_model.py tests/test_preference_pairwise_model.py
git commit -m "feat(search): add pairwise preference model trained on head-to-head comparisons"
```

---

### Task 2: Comparison pair sampler

**Files:**
- Create: `src/clawmarks/search/comparison_sampler.py`
- Test: `tests/test_comparison_sampler.py`

**Interfaces:**
- Consumes: `clawmarks.search.scoring.bin_edges`, `clawmarks.search.scoring.bin_of` (existing, unchanged).
- Produces: `N_BINS: int`, `MIN_COMPARISONS: int`, `RETRAIN_EVERY: int`, `CANDIDATE_POOL_SIZE: int`, `bin_manifest(manifest) -> dict`, `stratified_random_pair(manifest, rng=random) -> tuple | None`, `most_uncertain_pair(manifest, model, score_fn, embeddings_for, rng=random) -> tuple | None`, `pick_next_pair(manifest, n_comparisons, model=None, score_fn=None, embeddings_for=None, rng=random) -> tuple | None`. Task 4 imports `MIN_COMPARISONS`, `RETRAIN_EVERY`, and calls `pick_next_pair`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_comparison_sampler.py
import random

from clawmarks.search import comparison_sampler as cs


def _manifest(n):
    return [{"tag": f"t{i}", "centroid_sim": i / n, "novelty": 1 - i / n} for i in range(n)]


def test_bin_manifest_splits_into_n_bins_by_bin_count():
    manifest = _manifest(16)
    grid = cs.bin_manifest(manifest)
    assert len(grid) <= cs.N_BINS * cs.N_BINS
    assert sum(len(v) for v in grid.values()) == 16


def test_stratified_random_pair_returns_two_distinct_items():
    manifest = _manifest(20)
    rng = random.Random(0)
    for _ in range(30):
        pair = cs.stratified_random_pair(manifest, rng=rng)
        assert pair is not None
        a, b = pair
        assert a["tag"] != b["tag"]


def test_stratified_random_pair_returns_none_with_fewer_than_two_images():
    assert cs.stratified_random_pair(_manifest(1)) is None
    assert cs.stratified_random_pair(_manifest(0)) is None


def test_most_uncertain_pair_picks_the_closest_scored_candidates():
    manifest = _manifest(10)
    scores_by_tag = {f"t{i}": float(i) for i in range(10)}
    # t4 and t5 are adjacent (gap 1.0); every other adjacent gap is also 1.0, so force a
    # tighter gap between two items to make the expected winner unambiguous.
    scores_by_tag["t4"] = 5.0
    scores_by_tag["t5"] = 5.05

    def score_fn(model, embeddings):
        return [scores_by_tag[tag] for tag in embeddings]

    def embeddings_for(items):
        return [it["tag"] for it in items]

    pair = cs.most_uncertain_pair(manifest, model=object(), score_fn=score_fn,
                                  embeddings_for=embeddings_for, rng=random.Random(0))
    assert pair is not None
    tags = {pair[0]["tag"], pair[1]["tag"]}
    assert tags == {"t4", "t5"}


def test_most_uncertain_pair_returns_none_with_fewer_than_two_images():
    assert cs.most_uncertain_pair(_manifest(1), object(), lambda m, e: [], lambda items: []) is None


def test_pick_next_pair_uses_stratified_below_min_comparisons():
    manifest = _manifest(20)
    calls = {"most_uncertain": 0}

    def score_fn(model, embeddings):
        calls["most_uncertain"] += 1
        return [0.0] * len(embeddings)

    pair = cs.pick_next_pair(manifest, n_comparisons=10, model=object(), score_fn=score_fn,
                              embeddings_for=lambda items: items, rng=random.Random(0))
    assert pair is not None
    assert calls["most_uncertain"] == 0


def test_pick_next_pair_uses_stratified_when_no_model_even_above_floor():
    manifest = _manifest(20)
    pair = cs.pick_next_pair(manifest, n_comparisons=60, model=None, rng=random.Random(0))
    assert pair is not None


def test_pick_next_pair_uses_most_uncertain_at_or_above_floor_with_a_model():
    manifest = _manifest(20)
    calls = {"n": 0}

    def score_fn(model, embeddings):
        calls["n"] += 1
        return list(range(len(embeddings)))

    pair = cs.pick_next_pair(manifest, n_comparisons=60, model=object(), score_fn=score_fn,
                              embeddings_for=lambda items: items, rng=random.Random(0))
    assert pair is not None
    assert calls["n"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_comparison_sampler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clawmarks.search.comparison_sampler'`

- [ ] **Step 3: Write the implementation**

```python
# src/clawmarks/search/comparison_sampler.py
"""
Pair sampler for the compare UI (compare.html / GET /api/compare/next): picks two images to
show side by side next. Replaces search/rating_sampler.py's role for head-to-head comparisons.

Below MIN_COMPARISONS, picks a stratified-random pair: two bins chosen independently at random
from the existing faithfulness x novelty grid (also used by build/elite_archive.py), one random
image from each, so an early comparison session doesn't over-sample whichever region happens to
dominate the pool. At or above the floor, switches to model-uncertainty-guided selection: a
random candidate set of images is scored by the current model, and the two whose scores are
closest together are returned, since that pair is the model's best approximation of "least sure
which one wins" without enumerating every possible pair across a pool of thousands of images.
See docs/superpowers/specs/2026-07-11-head-to-head-preference-design.md.
"""
import random

from clawmarks.search.scoring import bin_edges, bin_of

N_BINS = 4  # matches build/elite_archive.py's grid
MIN_COMPARISONS = 50
RETRAIN_EVERY = 10
CANDIDATE_POOL_SIZE = 200


def bin_manifest(manifest):
    faith_vals = sorted(m["centroid_sim"] for m in manifest)
    novelty_vals = sorted(m["novelty"] for m in manifest)
    faith_edges = bin_edges(faith_vals, N_BINS)
    novelty_edges = bin_edges(novelty_vals, N_BINS)
    grid = {}
    for m in manifest:
        fb = bin_of(m["centroid_sim"], faith_edges)
        nb = bin_of(m["novelty"], novelty_edges)
        grid.setdefault((fb, nb), []).append(m)
    return grid


def stratified_random_pair(manifest, rng=random):
    """Returns two distinct manifest items from randomly chosen bins (can be the same bin), or
    None if the manifest has fewer than 2 images."""
    if len(manifest) < 2:
        return None
    grid = bin_manifest(manifest)
    nonempty = [items for items in grid.values() if items]
    if not nonempty:
        return None
    bin_a = rng.choice(nonempty)
    item_a = rng.choice(bin_a)
    for _ in range(20):
        bin_b = rng.choice(nonempty)
        item_b = rng.choice(bin_b)
        if item_b["tag"] != item_a["tag"]:
            return (item_a, item_b)
    # Every random draw collided with item_a (bad luck, or every other bin happens to be
    # empty of anything but item_a's own bin with item_a as its only member) - fall back to a
    # linear scan for any other image, which always succeeds given len(manifest) >= 2.
    for m in manifest:
        if m["tag"] != item_a["tag"]:
            return (item_a, m)
    return None


def most_uncertain_pair(manifest, model, score_fn, embeddings_for, rng=random):
    """Returns the two manifest items whose model scores are closest together, out of a random
    candidate set of up to CANDIDATE_POOL_SIZE images. `score_fn(model, embeddings) -> sequence`
    and `embeddings_for(items) -> sequence` let callers plug in
    preference_pairwise_model.score and an embedding lookup without this module importing the
    embedding cache directly. Returns None if fewer than 2 candidates are available."""
    if len(manifest) < 2:
        return None
    candidates = rng.sample(manifest, min(CANDIDATE_POOL_SIZE, len(manifest)))
    scores = score_fn(model, embeddings_for(candidates))
    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1])
    best_gap, best_pair = None, None
    for i in range(len(ranked) - 1):
        gap = abs(ranked[i][1] - ranked[i + 1][1])
        if best_gap is None or gap < best_gap:
            best_gap, best_pair = gap, (ranked[i][0], ranked[i + 1][0])
    return best_pair


def pick_next_pair(manifest, n_comparisons, model=None, score_fn=None, embeddings_for=None, rng=random):
    """Top-level entry point used by curation_server.py. Below MIN_COMPARISONS, or when no model
    is available yet, falls back to stratified_random_pair. At/above the floor with a model
    available, uses most_uncertain_pair."""
    if n_comparisons < MIN_COMPARISONS or model is None:
        return stratified_random_pair(manifest, rng=rng)
    return most_uncertain_pair(manifest, model, score_fn, embeddings_for, rng=rng)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_comparison_sampler.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/clawmarks/search/comparison_sampler.py tests/test_comparison_sampler.py
git commit -m "feat(search): add stratified/uncertainty-guided pair sampler for head-to-head comparisons"
```

---

### Task 3: Compare page UI

**Files:**
- Create: `src/clawmarks/build/compare_page.py`
- Test: `tests/test_compare_page.py`
- Delete: `src/clawmarks/build/rate_page.py`, `tests/test_rate_page.py`

**Interfaces:**
- Consumes: `clawmarks.shared_ui.nav_bar_html`, `TOPNAV_CSS`, `MOBILE_BASE_CSS`, `INFOTIP_CSS`, `info_btn` (existing, unchanged).
- Produces: `render_html() -> str`. Task 4 imports this and calls it from the `/compare.html` route.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_compare_page.py
from clawmarks.build import compare_page


def test_render_html_includes_compare_api_calls():
    html = compare_page.render_html()
    assert "/api/compare/next" in html
    assert "/api/compare" in html


def test_render_html_has_two_panes():
    html = compare_page.render_html()
    assert 'id="pane1"' in html
    assert 'id="pane2"' in html
    assert 'id="img1"' in html
    assert 'id="img2"' in html


def test_render_html_has_no_button_elements():
    html = compare_page.render_html()
    assert "<button" not in html


def test_render_html_has_zoom_icons_and_overlay():
    html = compare_page.render_html()
    assert 'id="zoom1"' in html
    assert 'id="zoom2"' in html
    assert 'id="zoom-overlay"' in html
    assert "function openZoom(" in html
    assert "function closeZoom(" in html


def test_render_html_has_arrow_key_handling():
    html = compare_page.render_html()
    assert "ArrowLeft" in html
    assert "ArrowRight" in html


def test_render_html_has_session_count():
    html = compare_page.render_html()
    assert 'id="count"' in html
    assert "comparedThisSession" in html


def test_render_html_has_done_state():
    html = compare_page.render_html()
    assert 'id="done"' in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_compare_page.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clawmarks.build.compare_page'`

- [ ] **Step 3: Write the implementation**

```python
# src/clawmarks/build/compare_page.py
"""
Generates compare.html: a head-to-head comparison page. Shows two images side by side; tapping
or clicking one picks it as the winner, feeding search/preference_pairwise_model.py. Replaces
build/rate_page.py's role (yes/no rating is gone). Like rate_page.py, this page bakes in no
per-image data at build time: it fetches GET /api/compare/next itself and POSTs to
/api/compare, both served by curation_server.py, so the page never goes stale between rebuilds.

Served live at /compare.html by curation_server.py.
"""
from clawmarks.shared_ui import nav_bar_html, TOPNAV_CSS, MOBILE_BASE_CSS, INFOTIP_CSS, info_btn


def render_html():
    compare_tip = info_btn(
        "Trains the preference model by comparison: pick whichever of the two images you "
        "prefer, as many times as you can stand. Early comparisons are sampled to spread across "
        "the faithfulness/novelty grid; once 50+ comparisons exist, the model itself starts "
        "picking which pairs are most useful to compare next."
    )

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>CLAWMARKS compare</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ color-scheme: dark; --bg:#0b0b0d; --panel:#16161a; --border:#2a2a30; --text:#eaeaee;
  --text-dim:#9a9aa4; --pick:#7c9eff; }}
body {{ background:var(--bg); color:var(--text); font-family:-apple-system,sans-serif; margin:0; padding:24px;
  display:flex; flex-direction:column; align-items:center; }}
{TOPNAV_CSS}
{MOBILE_BASE_CSS}
h1 {{ font-size:18px; margin:0 0 4px; align-self:flex-start; }}
p.sub {{ color:var(--text-dim); max-width:640px; font-size:13px; line-height:1.6; align-self:flex-start; }}
#stage {{ margin-top:20px; width:100%; max-width:1100px; display:flex; flex-direction:column; align-items:center; }}
#pair {{ display:flex; gap:16px; width:100%; justify-content:center; flex-wrap:wrap; }}
.pane {{ position:relative; flex:1 1 420px; max-width:520px; cursor:pointer; border-radius:10px;
  border:2px solid transparent; transition:border-color .12s ease; }}
.pane:hover {{ border-color:var(--pick); }}
.pane img {{ display:block; width:100%; max-height:70vh; object-fit:contain; border-radius:8px;
  background:var(--panel); user-select:none; -webkit-user-drag:none; }}
.zoom-icon {{ position:absolute; top:8px; right:8px; width:30px; height:30px; border-radius:50%;
  background:rgba(20,20,24,0.7); border:1px solid rgba(255,255,255,0.2); color:#eaeaee;
  font-size:15px; display:flex; align-items:center; justify-content:center; cursor:zoom-in; z-index:2; }}
.zoom-icon:hover {{ background:rgba(124,158,255,0.35); }}
#meta {{ color:var(--text-dim); font-size:12.5px; margin-top:10px; text-align:center; display:flex; gap:24px; }}
#count {{ color:var(--text-dim); font-size:12px; margin-top:14px; }}
#done {{ color:var(--text-dim); font-size:14px; margin-top:40px; text-align:center; }}
#zoom-overlay {{ position:fixed; inset:0; background:rgba(8,8,10,0.94); backdrop-filter:blur(6px);
  display:none; align-items:center; justify-content:center; z-index:1000; cursor:grab; overflow:hidden; }}
#zoom-overlay.open {{ display:flex; }}
#zoom-overlay img {{ max-width:none; max-height:none; user-select:none; -webkit-user-drag:none; }}
{INFOTIP_CSS}
</style></head><body>

{nav_bar_html('compare.html')}
<h1>Compare{compare_tip}</h1>
<p class="sub">Tap or click the image you prefer (or press &larr;/&rarr;). Tap the magnifier in
a corner to inspect that image at full resolution; tap again to close.</p>

<div id="stage">
  <div id="pair">
    <div class="pane" id="pane1" data-side="1">
      <img id="img1" style="display:none;">
      <div class="zoom-icon" id="zoom1">&#128269;</div>
    </div>
    <div class="pane" id="pane2" data-side="2">
      <img id="img2" style="display:none;">
      <div class="zoom-icon" id="zoom2">&#128269;</div>
    </div>
  </div>
  <div id="meta"></div>
  <div id="done" style="display:none;">Nothing left to compare right now &mdash; the pool doesn't have enough images left to form a new pair.</div>
</div>
<div id="count"></div>

<div id="zoom-overlay">
  <img id="zoom-img">
</div>

<script>
let current = null;
let comparedThisSession = 0;

function loadNext() {{
  fetch('/api/compare/next').then(r => r.json()).then(d => {{
    if (d.done) {{
      current = null;
      document.getElementById('pair').style.display = 'none';
      document.getElementById('done').style.display = 'block';
      return;
    }}
    current = d;
    document.getElementById('pair').style.display = 'flex';
    document.getElementById('done').style.display = 'none';
    const img1 = document.getElementById('img1');
    const img2 = document.getElementById('img2');
    img1.src = d.img1.file; img1.style.display = 'block';
    img2.src = d.img2.file; img2.style.display = 'block';
    document.getElementById('meta').innerHTML =
      `<span>${{d.img1.prompt_name}} | faith=${{d.img1.faith}} novelty=${{d.img1.novelty}}</span>` +
      `<span>${{d.img2.prompt_name}} | faith=${{d.img2.faith}} novelty=${{d.img2.novelty}}</span>`;
  }});
}}

function choose(side) {{
  if (!current) return;
  const winner = side === 1 ? current.img1.tag : current.img2.tag;
  const loser = side === 1 ? current.img2.tag : current.img1.tag;
  fetch('/api/compare', {{method:'POST', headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{winner, loser}})}})
    .then(r => r.json())
    .then(() => {{
      comparedThisSession++;
      document.getElementById('count').textContent = `${{comparedThisSession}} compared this session`;
      loadNext();
    }});
}}

document.getElementById('pane1').addEventListener('click', () => choose(1));
document.getElementById('pane2').addEventListener('click', () => choose(2));

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowLeft') choose(1);
  if (e.key === 'ArrowRight') choose(2);
}});

// --- zoom overlay: opens on a zoom-icon tap, closes on any tap, drag to pan while open ---

let zoomOpen = false;
let panX = 0, panY = 0, dragging = false, dragMoved = false, dragStartX = 0, dragStartY = 0;

function clampOffset(offset, wrapSize, imgSize) {{
  if (imgSize <= wrapSize) return (wrapSize - imgSize) / 2;
  return Math.min(0, Math.max(wrapSize - imgSize, offset));
}}

function openZoom(side, e) {{
  e.stopPropagation();
  if (!current) return;
  const src = side === 1 ? current.img1.file : current.img2.file;
  const overlay = document.getElementById('zoom-overlay');
  const zimg = document.getElementById('zoom-img');
  zimg.src = src;
  panX = 0; panY = 0;
  zimg.style.transform = 'translate(0px, 0px)';
  overlay.classList.add('open');
  zoomOpen = true;
}}

function closeZoom() {{
  document.getElementById('zoom-overlay').classList.remove('open');
  zoomOpen = false;
}}

document.getElementById('zoom1').addEventListener('click', e => openZoom(1, e));
document.getElementById('zoom2').addEventListener('click', e => openZoom(2, e));

const overlayEl = document.getElementById('zoom-overlay');
overlayEl.addEventListener('mousedown', e => {{
  dragging = true; dragMoved = false;
  dragStartX = e.clientX - panX; dragStartY = e.clientY - panY;
}});
document.addEventListener('mousemove', e => {{
  if (!dragging) return;
  dragMoved = true;
  const zimg = document.getElementById('zoom-img');
  panX = clampOffset(e.clientX - dragStartX, overlayEl.clientWidth, zimg.naturalWidth);
  panY = clampOffset(e.clientY - dragStartY, overlayEl.clientHeight, zimg.naturalHeight);
  zimg.style.transform = `translate(${{panX}}px, ${{panY}}px)`;
}});
document.addEventListener('mouseup', () => {{
  if (dragging && !dragMoved) closeZoom();
  dragging = false;
}});

loadNext();
</script>
<script src="scrollnav.js"></script>
<script src="infotip.js"></script>
</body></html>"""

    return html
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_compare_page.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Delete the old rate page and its test**

```bash
git rm src/clawmarks/build/rate_page.py tests/test_rate_page.py
```

- [ ] **Step 6: Run the full test suite to confirm nothing else references the deleted module yet**

Run: `uv run pytest -v 2>&1 | tail -30`
Expected: Failures only in `curation_server`-related tests/imports (fixed in Task 4) — no other files import `rate_page` directly (confirm with `rg -l "rate_page" src tests`; only `curation_server.py` should appear).

- [ ] **Step 7: Commit**

```bash
git add src/clawmarks/build/compare_page.py tests/test_compare_page.py
git commit -m "feat(build): add compare_page.py, replacing the yes/no rate_page.py"
```

---

### Task 4: Server API — compare endpoints replace rate endpoints

**Files:**
- Modify: `src/clawmarks/curation_server.py`
- Test: `tests/test_curation_server_compare_routes.py` (new)
- Modify: `tests/test_curation_server_preference_status_route.py`

**Interfaces:**
- Consumes: Task 1's `preference_pairwise_model` (`MODEL_FILE`, `MODEL_META_FILE`, `score`, `train_and_save`), Task 2's `comparison_sampler` (`MIN_COMPARISONS`, `RETRAIN_EVERY`, `pick_next_pair`), Task 3's `compare_page.render_html()`.
- Produces: `GET /api/compare/next`, `POST /api/compare` routes; `COMPARISONS_FILE` constant; `load_comparisons()`, `save_comparisons()`, `record_comparison()`, `next_compare_response()` module-level functions (mirroring the old `load_store`/`save_store`/`record_rating`/`next_rating_response` shapes, but list-shaped instead of dict-shaped). Removes `GET /api/ratings`, `GET /api/rate/next`, `POST /api/rate`, and the `rating_sampler`/`preference_model`/`rate_page` imports.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_curation_server_compare_routes.py
import json
import threading
from http.server import HTTPServer
import urllib.request
import urllib.error

import pytest

from clawmarks import curation_server as cs
from clawmarks.search import comparison_sampler


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "SWEEP_DIR", tmp_path)
    monkeypatch.setattr(cs, "_live_cache", cs.LiveCache())
    monkeypatch.setattr(cs, "COMPARISONS_FILE", str(tmp_path / "user_comparisons.json"))
    monkeypatch.setattr(cs.preference_pairwise_model, "MODEL_FILE", tmp_path / "preference_pairwise_model.joblib")
    monkeypatch.setattr(cs.preference_pairwise_model, "MODEL_META_FILE", tmp_path / "preference_pairwise_model_meta.json")
    manifest = [
        {"tag": f"t{i}", "prompt_name": "p", "prompt_type": "style", "centroid_sim": i / 20,
         "novelty": 1 - i / 20, "strength": 1.0, "cfg": 7.0, "file": f"{i}.png"}
        for i in range(20)
    ]
    (tmp_path / "scored_manifest.json").write_text(json.dumps(manifest))
    server = HTTPServer(("127.0.0.1", 0), cs.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, tmp_path
    server.shutdown()
    thread.join(timeout=2)


def test_compare_next_returns_two_distinct_images(running_server):
    server, tmp_path = running_server
    port = server.server_address[1]
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/compare/next") as resp:
        data = json.loads(resp.read().decode())
    assert data["img1"]["tag"] != data["img2"]["tag"]
    assert "faith" in data["img1"] and "novelty" in data["img1"]


def test_compare_next_returns_done_with_fewer_than_two_images(running_server):
    server, tmp_path = running_server
    port = server.server_address[1]
    (tmp_path / "scored_manifest.json").write_text(json.dumps([
        {"tag": "only", "prompt_name": "p", "prompt_type": "style", "centroid_sim": 0.5,
         "novelty": 0.5, "strength": 1.0, "cfg": 7.0, "file": "only.png"},
    ]))
    monkeypatch_reload = cs.load_manifest  # force a fresh read past the mtime cache
    cs._manifest_cache["manifest"] = None
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/compare/next") as resp:
        data = json.loads(resp.read().decode())
    assert data == {"done": True}


def test_post_compare_appends_a_comparison_record(running_server):
    server, tmp_path = running_server
    port = server.server_address[1]
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/compare", method="POST",
        data=json.dumps({"winner": "t0", "loser": "t1"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    assert data["ok"] is True
    assert data["count"] == 1
    comparisons = json.loads((tmp_path / "user_comparisons.json").read_text())
    assert len(comparisons) == 1
    assert comparisons[0]["winner"] == "t0"
    assert comparisons[0]["loser"] == "t1"
    assert "compared_at" in comparisons[0]


def test_post_compare_rejects_missing_fields(running_server):
    server, tmp_path = running_server
    port = server.server_address[1]
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/compare", method="POST",
        data=json.dumps({"winner": "t0"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400


def test_compare_html_route_serves_page(running_server):
    server, tmp_path = running_server
    port = server.server_address[1]
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/compare.html") as resp:
        body = resp.read().decode()
    assert "CLAWMARKS compare" in body


def test_rate_routes_no_longer_exist(running_server):
    server, tmp_path = running_server
    port = server.server_address[1]
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/rate.html")
    assert exc_info.value.code == 404
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/rate/next")
    assert exc_info.value.code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_curation_server_compare_routes.py -v`
Expected: FAIL — `/api/compare/next` and `/api/compare` don't exist yet (404s / `preference_pairwise_model` attribute errors on `cs`).

- [ ] **Step 3: Modify `curation_server.py`**

Modify the module docstring's API list (around `src/clawmarks/curation_server.py:38-53`):

```python
API:
  GET  /api/ratings           -> {tag: {label, rated_at}}
  GET  /api/rate/next         -> item_summary dict for the next unreviewed image, or {"done": true}
  POST /api/rate               body: {"tag": "...", "label": "yes"|"no"} -> upserts, returns ok
```

becomes:

```python
API:
  GET  /api/compare/next       -> {"img1": item_summary, "img2": item_summary} for the next
                                   pair to compare, or {"done": true} if fewer than 2 images
                                   exist in the pool
  POST /api/compare             body: {"winner": tag, "loser": tag} -> appends a comparison
                                 record, returns {"ok": true, "count": n}
```

Modify the top-of-file explanatory docstring (`src/clawmarks/curation_server.py:1-18`), replacing the yes/no-rating paragraph with:

```python
"""
Static file server + tiny comparison API for the uncanny-frontier scan gallery. Replaces the
plain `python3 -m http.server` that was serving notes/uncanny_sweep/ read-only: a plain static
server can't accept writes, and the whole point of this is letting a human record head-to-head
preference comparisons from the browser, which needs somewhere to persist that choice.

Comparisons are stored in notes/uncanny_sweep/user_comparisons.json, a list of
{winner, loser, compared_at} records. search/preference_pairwise_model.py trains a Bradley-
Terry-style model on this data (see
docs/superpowers/specs/2026-07-11-head-to-head-preference-design.md). The selection of which
pair to compare next is stratified across the faithfulness x novelty grid below
comparison_sampler.MIN_COMPARISONS, then model-uncertainty-guided above it; this server retrains
the model every comparison_sampler.RETRAIN_EVERY comparisons once the floor is cleared.

Favorites (notes/uncanny_sweep/user_favorites.json) are a separate store: a plain bookmark
for images worth keeping (e.g. for the writeup) without steering where the search goes next,
for when "I like this" and "build more like this" are different judgments.

Counterfactuals (notes/uncanny_sweep/user_counterfactuals.json, images in
notes/uncanny_sweep/counterfactuals/) are on-demand single generations: pick an existing image,
change whichever of prompt/strength/cfg/seed you want, submit, and this server calls the same
serverless ComfyUI endpoint the search itself uses (uix4vdb2cec7sb), waits synchronously for the
one job to finish (a few seconds if a worker is already warm, up to several minutes if the
endpoint scaled to zero and needs to cold-start one), and saves the result. These are NOT scored against
the DINOv2 centroid/novelty metrics and are NOT fed back into the search; they're a quick "what
if" comparison tool, not part of the MAP-Elites archive. A RunPod balance check runs before every
submission and refuses below a safety floor rather than risk the silent-stall failure mode this
project hit once already with a negative balance.

Candidate seeds (notes/uncanny_sweep/candidate_seeds.json) are the pool of subject/texture
descriptions "explore" jobs draw from. The search driver (search/driver.py) escalates to
GPT-5.5 for fresh ones on plateau, via a subprocess call to `opencode run`; this server exposes
the same mechanism on demand so the pool can be reviewed and topped up between runs, not just
mid-run. Generation is synchronous (up to 5 minutes) and calls out to opencode/GPT-5.5, so it
costs real API time but no RunPod spend.
"""
```

Modify the imports block (`src/clawmarks/curation_server.py:63-74`):

```python
from clawmarks.config import ROOT, SEEDS_FILE, SWEEP_DIR
from clawmarks.search.seed_pool import merge as seed_pool_merge
from clawmarks.search import rating_sampler, preference_settings, preference_model
from clawmarks.search.manifest_index import item_summary
from clawmarks.shared_ui import _LIGHTBOX_JS, SCROLLNAV_JS, INFOTIP_JS
from clawmarks.live_cache import LiveCache
from clawmarks.build import (
    scan_gallery, similarity_index, solution_map, map_view, redundancy_view, coverage_map,
    novelty_decay, lineage_view, elite_archive, preference_rank, uncanny_gallery, explore_hub,
    seed_browser, rate_page, preference_status,
)
from clawmarks.build.thumbnails import generate_thumbnail
```

becomes:

```python
from clawmarks.config import ROOT, SEEDS_FILE, SWEEP_DIR
from clawmarks.search.seed_pool import merge as seed_pool_merge
from clawmarks.search import comparison_sampler, preference_settings, preference_pairwise_model
from clawmarks.search import embed_cache
from clawmarks.search.manifest_index import item_summary
from clawmarks.shared_ui import _LIGHTBOX_JS, SCROLLNAV_JS, INFOTIP_JS
from clawmarks.live_cache import LiveCache
from clawmarks.build import (
    scan_gallery, similarity_index, solution_map, map_view, redundancy_view, coverage_map,
    novelty_decay, lineage_view, elite_archive, preference_rank, uncanny_gallery, explore_hub,
    seed_browser, compare_page, preference_status,
)
from clawmarks.build.thumbnails import generate_thumbnail
```

Modify `_preference_status_watched_files` (`src/clawmarks/curation_server.py:132-138`):

```python
def _preference_status_watched_files():
    files = []
    for f in (f"{SWEEP_DIR}/user_ratings.json", preference_model.MODEL_FILE,
              preference_model.MODEL_META_FILE, preference_settings.PREFERENCE_SETTINGS_FILE):
        if os.path.exists(f):
            files.append(str(f))
    return files
```

becomes:

```python
def _preference_status_watched_files():
    files = []
    for f in (COMPARISONS_FILE, preference_pairwise_model.MODEL_FILE,
              preference_pairwise_model.MODEL_META_FILE, preference_settings.PREFERENCE_SETTINGS_FILE):
        if os.path.exists(f):
            files.append(str(f))
    return files
```

Modify the constants block (`src/clawmarks/curation_server.py:147-151`):

```python
FAVORITES_FILE = f"{SWEEP_DIR}/user_favorites.json"
RATINGS_FILE = f"{SWEEP_DIR}/user_ratings.json"
COUNTERFACTUALS_DIR = f"{SWEEP_DIR}/counterfactuals"
COUNTERFACTUALS_FILE = f"{SWEEP_DIR}/user_counterfactuals.json"
DEFAULT_PORT = 8420
```

becomes:

```python
FAVORITES_FILE = f"{SWEEP_DIR}/user_favorites.json"
COMPARISONS_FILE = f"{SWEEP_DIR}/user_comparisons.json"
COUNTERFACTUALS_DIR = f"{SWEEP_DIR}/counterfactuals"
COUNTERFACTUALS_FILE = f"{SWEEP_DIR}/user_counterfactuals.json"
DEFAULT_PORT = 8420
```

Replace `next_rating_response` and `record_rating` (`src/clawmarks/curation_server.py:225-240`):

```python
def next_rating_response(manifest, reviewed_tags, rng=None):
    """Returns an item_summary dict for the next image to rate, or {"done": True} if every
    image in `manifest` is already in `reviewed_tags`."""
    item = rating_sampler.pick_next(manifest, reviewed_tags, rng=rng) if rng is not None \
        else rating_sampler.pick_next(manifest, reviewed_tags)
    if item is None:
        return {"done": True}
    return item_summary(item, SWEEP_DIR)


def record_rating(ratings, tag, label, now):
    if label not in ("yes", "no"):
        raise ValueError(f"label must be 'yes' or 'no', got {label!r}")
    updated = dict(ratings)
    updated[tag] = {"label": label, "rated_at": now}
    return updated
```

becomes:

```python
def load_comparisons():
    if os.path.exists(COMPARISONS_FILE):
        with open(COMPARISONS_FILE) as f:
            return json.load(f)
    return []


def save_comparisons(comparisons):
    tmp = f"{COMPARISONS_FILE}.tmp"
    with open(tmp, "w") as f:
        json.dump(comparisons, f, indent=1)
    os.replace(tmp, COMPARISONS_FILE)


def record_comparison(comparisons, winner, loser, now):
    updated = list(comparisons)
    updated.append({"winner": winner, "loser": loser, "compared_at": now})
    return updated


_pairwise_model_cache = {"model": None}


def _embeddings_for(items):
    tags, embeddings = embed_cache.load_cache(embed_cache.EMBEDDINGS_FILE)
    tag_to_row = {t: i for i, t in enumerate(tags)}
    idx = [tag_to_row[m["tag"]] for m in items if m["tag"] in tag_to_row]
    return embeddings[idx]


def _maybe_retrain_pairwise_model(comparisons):
    """Called after every recorded comparison. Retrains and persists the model every
    comparison_sampler.RETRAIN_EVERY comparisons once comparison_sampler.MIN_COMPARISONS is
    cleared, and refreshes the in-memory cache used by pair selection so a freshly-trained model
    starts steering pair selection immediately, not just after the next server restart."""
    n = len(comparisons)
    if n < comparison_sampler.MIN_COMPARISONS or n % comparison_sampler.RETRAIN_EVERY != 0:
        return
    result = preference_pairwise_model.train_and_save(comparisons)
    if result is not None:
        _pairwise_model_cache["model"] = result["model"]


def next_compare_response(manifest, comparisons):
    """Returns {"img1": item_summary, "img2": item_summary} for the next pair to compare, or
    {"done": True} if the pool has fewer than 2 images to pick from."""
    model = _pairwise_model_cache["model"]
    candidate_manifest = manifest
    if model is not None:
        tags, _ = embed_cache.load_cache(embed_cache.EMBEDDINGS_FILE)
        embedded = set(tags)
        candidate_manifest = [m for m in manifest if m["tag"] in embedded] or manifest
    pair = comparison_sampler.pick_next_pair(
        candidate_manifest, len(comparisons), model=model,
        score_fn=preference_pairwise_model.score, embeddings_for=_embeddings_for,
    )
    if pair is None:
        return {"done": True}
    a, b = pair
    return {"img1": item_summary(a, SWEEP_DIR), "img2": item_summary(b, SWEEP_DIR)}
```

Modify `do_GET` (`src/clawmarks/curation_server.py:287-299`):

```python
    def do_GET(self):
        if self.path == "/api/ratings":
            with _lock:
                self._json_response(200, load_store(RATINGS_FILE))
            return
        if self.path == "/api/rate/next":
            with _lock:
                ratings = load_store(RATINGS_FILE)
                favorites = load_store(FAVORITES_FILE)
                reviewed = set(ratings) | set(favorites)
                response = next_rating_response(load_manifest(), reviewed)
            self._json_response(200, response)
            return
```

becomes:

```python
    def do_GET(self):
        if self.path == "/api/compare/next":
            with _lock:
                comparisons = load_comparisons()
                response = next_compare_response(load_manifest(), comparisons)
            self._json_response(200, response)
            return
```

Modify the `/rate.html` route (`src/clawmarks/curation_server.py:459-466`):

```python
        if self.path == "/rate.html":
            body = rate_page.render_html().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
```

becomes:

```python
        if self.path == "/compare.html":
            body = compare_page.render_html().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
```

Modify `do_POST` (`src/clawmarks/curation_server.py:491-502`):

```python
        if self.path == "/api/rate":
            tag = payload.get("tag")
            label = payload.get("label")
            if not tag or label not in ("yes", "no"):
                self._json_response(400, {"error": "missing 'tag' or invalid 'label' (must be 'yes' or 'no')"})
                return
            with _lock:
                ratings = load_store(RATINGS_FILE)
                ratings = record_rating(ratings, tag, label, datetime.now(timezone.utc).isoformat())
                save_store(RATINGS_FILE, ratings)
            self._json_response(200, {"ok": True, "count": len(ratings)})
            return
```

becomes:

```python
        if self.path == "/api/compare":
            winner = payload.get("winner")
            loser = payload.get("loser")
            if not winner or not loser:
                self._json_response(400, {"error": "missing 'winner' or 'loser'"})
                return
            with _lock:
                comparisons = load_comparisons()
                comparisons = record_comparison(comparisons, winner, loser, datetime.now(timezone.utc).isoformat())
                save_comparisons(comparisons)
                _maybe_retrain_pairwise_model(comparisons)
            self._json_response(200, {"ok": True, "count": len(comparisons)})
            return
```

Modify the `preference_toggle` handler's model-existence check (`src/clawmarks/curation_server.py:509`):

```python
            if enabled and not os.path.exists(preference_model.MODEL_FILE):
```

becomes:

```python
            if enabled and not os.path.exists(preference_pairwise_model.MODEL_FILE):
```

- [ ] **Step 4: Update the preference-status route test's monkeypatches**

In `tests/test_curation_server_preference_status_route.py`, the `running_server` fixture patches `cs.preference_model.MODEL_FILE` and seeds a `user_ratings.json`. Update it:

```python
@pytest.fixture
def running_server(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "SWEEP_DIR", tmp_path)
    monkeypatch.setattr(cs, "_live_cache", cs.LiveCache())
    monkeypatch.setattr(preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(cs.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(cs.preference_pairwise_model, "MODEL_FILE", tmp_path / "preference_pairwise_model.joblib")
    (tmp_path / "scored_manifest.json").write_text(json.dumps([]))
    server = HTTPServer(("127.0.0.1", 0), cs.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, tmp_path
    server.shutdown()
    thread.join(timeout=2)
```

And in `test_post_preference_toggle_accepts_enable_with_model_and_persists`, change:

```python
    (tmp_path / "preference_model.joblib").write_text("fake model")
```

to:

```python
    (tmp_path / "preference_pairwise_model.joblib").write_text("fake model")
```

Same substitution in `test_archive_html_uses_persisted_setting_not_query_param`.

- [ ] **Step 5: Run the compare-route and preference-status tests**

Run: `uv run pytest tests/test_curation_server_compare_routes.py tests/test_curation_server_preference_status_route.py -v`
Expected: PASS. If `test_compare_next_returns_done_with_fewer_than_two_images` fails because of the manifest mtime cache, remove the unused `monkeypatch_reload` line (it was a leftover — the important part is resetting `cs._manifest_cache["manifest"] = None` before the request, which is already present in the test).

- [ ] **Step 6: Run the full suite to check for any other stale reference to `preference_model`, `rating_sampler`, `rate_page`, `RATINGS_FILE`, or `next_rating_response` in curation_server.py's own test coverage**

Run: `rg -n "preference_model\.|rating_sampler|rate_page|RATINGS_FILE|next_rating_response|record_rating\b" src/clawmarks/curation_server.py tests/test_curation_server_compare_routes.py tests/test_curation_server_preference_status_route.py`
Expected: no matches (empty output). If anything remains, fix it before proceeding.

- [ ] **Step 7: Commit**

```bash
git add src/clawmarks/curation_server.py tests/test_curation_server_compare_routes.py tests/test_curation_server_preference_status_route.py
git commit -m "feat(server): replace yes/no rate endpoints with head-to-head compare endpoints"
```

---

### Task 5: Nav bar rename

**Files:**
- Modify: `src/clawmarks/shared_ui.py:16-30`

**Interfaces:**
- Consumes: nothing new.
- Produces: `NAV_OPTIONS` with `("compare.html", "compare images (head-to-head)")` in place of the old `rate.html` entry.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_shared_ui.py (create the file if it doesn't already exist; check first
# with `fd shared_ui tests` — if it exists, add this test to it instead of creating a new file)
from clawmarks.shared_ui import NAV_OPTIONS


def test_nav_options_has_compare_not_rate():
    hrefs = [href for href, _ in NAV_OPTIONS]
    assert "compare.html" in hrefs
    assert "rate.html" not in hrefs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_shared_ui.py -k nav_options -v`
Expected: FAIL — `rate.html` is still present.

- [ ] **Step 3: Modify `shared_ui.py`**

Change `src/clawmarks/shared_ui.py:16-30`:

```python
NAV_OPTIONS = [
    ("explore.html", "all tools (hub)"),
    ("rate.html", "rate images (yes/no)"),
    ("scan.html", "scan gallery"),
```

to:

```python
NAV_OPTIONS = [
    ("explore.html", "all tools (hub)"),
    ("compare.html", "compare images (head-to-head)"),
    ("scan.html", "scan gallery"),
```

(the rest of the list — `map.html` through `gallery.html` — is unchanged)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_shared_ui.py -k nav_options -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/clawmarks/shared_ui.py tests/test_shared_ui.py
git commit -m "feat(ui): rename nav bar entry from rate.html to compare.html"
```

---

### Task 6: Elite archive — favorites replace yes-ratings, model import swap

**Files:**
- Modify: `src/clawmarks/build/elite_archive.py`
- Modify: `tests/test_elite_archive.py`, `tests/test_elite_archive_live.py`

**Interfaces:**
- Consumes: Task 1's `preference_pairwise_model.MODEL_FILE`, `score`.
- Produces: `compute_data`'s manual-override tier now reads `user_favorites.json` instead of filtering `user_ratings.json` for `label == "yes"`. `elite_sort_key`, `build_item_summary` signatures unchanged (Task-6-untouched: `tests/test_elite_archive_predicted_preference.py` needs no changes).

- [ ] **Step 1: Update the failing tests first**

Replace `tests/test_elite_archive.py` in full:

```python
# tests/test_elite_archive.py
import json
import re

from clawmarks.build import elite_archive


def test_compute_data_uses_favorited_images_not_user_picks(tmp_path, monkeypatch):
    # Force every image into a single cell, regardless of its faith/novelty values, so the test
    # doesn't depend on how a 2-item manifest happens to quantile-split across N_BINS x N_BINS
    # cells (bin_edges(vals, 1) always returns [], so bin_of always returns 0).
    monkeypatch.setattr(elite_archive, "N_BINS", 1)
    manifest = [
        {"tag": "a", "prompt_name": "p", "prompt_type": "style", "centroid_sim": 0.9,
         "novelty": 0.1, "strength": 1.0, "cfg": 7.0, "file": "a.png"},
        {"tag": "b", "prompt_name": "p", "prompt_type": "style", "centroid_sim": 0.9,
         "novelty": 0.9, "strength": 1.0, "cfg": 7.0, "file": "b.png"},
    ]
    (tmp_path / "scored_manifest.json").write_text(json.dumps(manifest))
    # "a" has lower novelty than "b" but is favorited: it should win the cell despite that,
    # exactly the behavior user_picks.json used to provide before ratings existed.
    (tmp_path / "user_favorites.json").write_text(json.dumps({"a": {"tag": "a", "favorited_at": "t0"}}))
    # a stale user_picks.json should be ignored entirely
    (tmp_path / "user_picks.json").write_text(json.dumps({"b": {"picked_at": "t0"}}))

    data = elite_archive.compute_data(str(tmp_path))
    assert len(data["cells"]) == 1
    assert data["n_human"] == 1

    html = elite_archive.render_html(data)
    match = re.search(r"const CELLS = (\[.+?\]);\nlet picks", html)
    assert match is not None, "could not find 'const CELLS = [...]; let picks' in archive.html"
    cells = json.loads(match.group(1))
    assert len(cells) == 1
    tags_in_cell = {item["tag"] for item in cells[0]["items"]}
    assert tags_in_cell == {"a", "b"}
```

Replace `tests/test_elite_archive_live.py` in full:

```python
import json

from clawmarks.build import elite_archive


def test_compute_data_prefers_favorited_image_in_cell(tmp_path):
    manifest = [
        {"file": "/x/a.png", "tag": "a", "prompt_name": "p", "centroid_sim": 0.5, "novelty": 0.9,
         "prompt_type": "conflict", "strength": 1.0, "cfg": 5.0},
        {"file": "/x/b.png", "tag": "b", "prompt_name": "p", "centroid_sim": 0.5, "novelty": 0.1,
         "prompt_type": "conflict", "strength": 1.0, "cfg": 5.0},
    ]
    (tmp_path / "scored_manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "user_favorites.json").write_text(json.dumps({"b": {"tag": "b", "favorited_at": "x"}}))
    data = elite_archive.compute_data(str(tmp_path))
    html = elite_archive.render_html(data)
    assert '"tag": "b"' in html


def test_compute_data_falls_back_to_novelty_without_favorites(tmp_path):
    manifest = [
        {"file": "/x/a.png", "tag": "a", "prompt_name": "p", "centroid_sim": 0.5, "novelty": 0.9,
         "prompt_type": "conflict", "strength": 1.0, "cfg": 5.0},
    ]
    (tmp_path / "scored_manifest.json").write_text(json.dumps(manifest))
    data = elite_archive.compute_data(str(tmp_path))
    assert data["cells"][0]["items"][0]["tag"] == "a"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_elite_archive.py tests/test_elite_archive_live.py -v`
Expected: FAIL — `compute_data` still reads `user_ratings.json`.

- [ ] **Step 3: Modify `elite_archive.py`**

Modify the module docstring (`src/clawmarks/build/elite_archive.py:7-11`):

```python
Elite selection per cell: a yes-rated image (notes/uncanny_sweep/user_ratings.json) wins if one
exists in that cell, since a person's judgment substitutes for the coherence/quality scorer this
project doesn't have (lab_notebook.md Section 3b). Otherwise falls back to highest novelty in
the cell, matching the ranking the search itself uses to build its automated "elites" list.
```

becomes:

```python
Elite selection per cell: a favorited image (notes/uncanny_sweep/user_favorites.json) wins if
one exists in that cell, since a person's judgment substitutes for the coherence/quality scorer
this project doesn't have (lab_notebook.md Section 3b). This used to be driven by yes-rated
images, but yes/no ratings were replaced by head-to-head comparisons (see
docs/superpowers/specs/2026-07-11-head-to-head-preference-design.md), which have no per-image
manual-override signal of their own, so favoriting fills that role instead. Otherwise falls back
to highest novelty in the cell, matching the ranking the search itself uses to build its
automated "elites" list.
```

Modify the import (`src/clawmarks/build/elite_archive.py:18`):

```python
from clawmarks.search.preference_model import MODEL_FILE as PREFERENCE_MODEL_FILE
```

becomes:

```python
from clawmarks.search.preference_pairwise_model import MODEL_FILE as PREFERENCE_MODEL_FILE
```

Modify `compute_data`'s ratings-loading block (`src/clawmarks/build/elite_archive.py:46-63`):

```python
    ratings = {}
    ratings_path = f"{sweep_dir}/user_ratings.json"
    if os.path.exists(ratings_path):
        with open(ratings_path) as f:
            ratings = json.load(f)
    picks = {tag: r for tag, r in ratings.items() if r.get("label") == "yes"}

    predicted_scores = {}
    if use_predicted_preference and os.path.exists(PREFERENCE_MODEL_FILE):
        import joblib

        from clawmarks.search import embed_cache
        from clawmarks.search.preference_model import predict_proba

        tags, embeddings = embed_cache.load_cache(embed_cache.EMBEDDINGS_FILE)
        model = joblib.load(PREFERENCE_MODEL_FILE)
        scores = predict_proba(model, embeddings)
        predicted_scores = dict(zip(tags, scores))
```

becomes:

```python
    picks = {}
    favorites_path = f"{sweep_dir}/user_favorites.json"
    if os.path.exists(favorites_path):
        with open(favorites_path) as f:
            picks = json.load(f)

    predicted_scores = {}
    if use_predicted_preference and os.path.exists(PREFERENCE_MODEL_FILE):
        import joblib

        from clawmarks.search import embed_cache
        from clawmarks.search.preference_pairwise_model import score as pairwise_score

        tags, embeddings = embed_cache.load_cache(embed_cache.EMBEDDINGS_FILE)
        model = joblib.load(PREFERENCE_MODEL_FILE)
        scores = pairwise_score(model, embeddings)
        predicted_scores = dict(zip(tags, scores))
```

Modify the page description text (`src/clawmarks/build/elite_archive.py:170-176`):

```python
<p class="sub">One image per occupied cell of the faithfulness x novelty grid: the actual
MAP-Elites archive, not the full population. Gold-bordered cells are yes-rated winners;
blue-bordered cells (only when this page is built with --use-predicted-preference) are the
trained model's top pick for that cell; others fall back to the highest-novelty image the
automated search found. The DINOv2 scorer only ranks faithfulness and novelty, not aesthetic
quality, so it can't tell which image in a cell is the better picture: click "view all" to browse
every candidate in a cell and pick a different one by hand.</p>
```

becomes:

```python
<p class="sub">One image per occupied cell of the faithfulness x novelty grid: the actual
MAP-Elites archive, not the full population. Gold-bordered cells are favorited winners;
blue-bordered cells (only when this page is built with --use-predicted-preference) are the
trained model's top pick for that cell; others fall back to the highest-novelty image the
automated search found. The DINOv2 scorer only ranks faithfulness and novelty, not aesthetic
quality, so it can't tell which image in a cell is the better picture: click "view all" to browse
every candidate in a cell and pick a different one by hand.</p>
```

Modify the client-side JS `eliteFor` function and its trailing fetch (`src/clawmarks/build/elite_archive.py:195-200` and `:240-244`):

```python
function eliteFor(c) {{
  const pickedHere = c.items.filter(it => picks[it.tag]);
  if (pickedHere.length) return {{ item: pickedHere[0], source: 'yes-rated' }};
  if (c.items[0].predicted_preference !== undefined) return {{ item: c.items[0], source: 'predicted preference' }};
  return {{ item: c.items[0], source: 'highest novelty' }};  // items pre-sorted by elite_sort_key
}}
```

becomes:

```python
function eliteFor(c) {{
  const pickedHere = c.items.filter(it => picks[it.tag]);
  if (pickedHere.length) return {{ item: pickedHere[0], source: 'favorited' }};
  if (c.items[0].predicted_preference !== undefined) return {{ item: c.items[0], source: 'predicted preference' }};
  return {{ item: c.items[0], source: 'highest novelty' }};  // items pre-sorted by elite_sort_key
}}
```

and:

```python
fetch('/api/ratings').then(r => r.json()).then(ratings => {{
  picks = {{}};
  Object.entries(ratings).forEach(([tag, r]) => {{ if (r.label === 'yes') picks[tag] = true; }});
  render();
}}).catch(() => {{ render(); }});
```

becomes:

```python
fetch('/api/favorites').then(r => r.json()).then(favorites => {{
  picks = {{}};
  Object.keys(favorites).forEach(tag => {{ picks[tag] = true; }});
  render();
}}).catch(() => {{ render(); }});
```

Also update the `human`/`yes-rated` badge check in `render()` (`src/clawmarks/build/elite_archive.py:202-220`), where `const human = source === 'yes-rated';` becomes `const human = source === 'favorited';`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_elite_archive.py tests/test_elite_archive_live.py tests/test_elite_archive_predicted_preference.py -v`
Expected: PASS (the predicted-preference test file is untouched and should still pass since it doesn't exercise `compute_data`'s ratings/favorites path).

- [ ] **Step 5: Run a broader check for any remaining `user_ratings` or `yes-rated` reference in this file**

Run: `rg -n "user_ratings|yes-rated|yes_rated|preference_model\b" src/clawmarks/build/elite_archive.py`
Expected: no matches.

- [ ] **Step 6: Commit**

```bash
git add src/clawmarks/build/elite_archive.py tests/test_elite_archive.py tests/test_elite_archive_live.py
git commit -m "feat(build): elite_archive uses favorites instead of retired yes/no ratings"
```

---

### Task 7: Search driver — favorited images replace yes-rated images, Stage 5b model swap

**Files:**
- Modify: `src/clawmarks/search/driver.py`
- Delete: `tests/test_yes_rated_images.py`
- Create: `tests/test_favorited_images.py`

**Interfaces:**
- Consumes: Task 1's `preference_pairwise_model` (used only inside `_predicted_preference_pool`'s existing inline import, swapped to the new module).
- Produces: `driver._load_favorited_images() -> list[dict]` in place of `driver._load_yes_rated_images()`. `_predicted_preference_pool`'s signature is unchanged (still takes `manifest, model_path, embed_model, top_n=15`); only its inline import and the caller's hardcoded path change.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_favorited_images.py
import json

from clawmarks.search import driver


def test_load_favorited_images_returns_favorite_records(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "SWEEP_DIR", tmp_path)
    favorites = {
        "a": {"tag": "a", "prompt_name": "p", "prompt": "trentbuckle style, a", "strength": 1.0,
              "cfg": 7.0, "faith": 0.5, "novelty": 0.5, "favorited_at": "t0"},
    }
    (tmp_path / "user_favorites.json").write_text(json.dumps(favorites))
    result = driver._load_favorited_images()
    assert [m["tag"] for m in result] == ["a"]
    assert result[0]["prompt"] == "trentbuckle style, a"


def test_load_favorited_images_returns_empty_without_file(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "SWEEP_DIR", tmp_path)
    assert driver._load_favorited_images() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_favorited_images.py -v`
Expected: FAIL with `AttributeError: module 'clawmarks.search.driver' has no attribute '_load_favorited_images'`

- [ ] **Step 3: Modify `driver.py`**

Delete `_load_yes_rated_images` (`src/clawmarks/search/driver.py:268-284`):

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

replace it with:

```python
def _load_favorited_images():
    """Favorites supersede raw novelty for what the exploit step mutates near, the same role
    yes/no ratings used to play before they were replaced by head-to-head comparisons (see
    docs/superpowers/specs/2026-07-11-head-to-head-preference-design.md). Unlike the old
    ratings store, user_favorites.json already holds a full item object per tag (tag,
    prompt_name, prompt, strength, cfg, ...), so favorited items can be returned directly
    without joining against scored_manifest.json."""
    favorites_path = SWEEP_DIR / "user_favorites.json"
    if not favorites_path.exists():
        return []
    with open(favorites_path) as f:
        favorites = json.load(f)
    return list(favorites.values())
```

Modify the call site and the Stage 5b model path (`src/clawmarks/search/driver.py:597-605`):

```python
        user_picks = _load_yes_rated_images() if cfg.seed_from_start else []
        if args.use_predicted_preference:
            predicted_pool = _predicted_preference_pool(
                manifest, SWEEP_DIR / "preference_model.joblib", model,
            )
            if predicted_pool:
                user_picks = predicted_pool
            else:
                print("--use-predicted-preference set but no trained model found yet "
                      "(or nothing generated so far this round); using yes-rated images "
                      "instead", flush=True)
```

becomes:

```python
        user_picks = _load_favorited_images() if cfg.seed_from_start else []
        if args.use_predicted_preference:
            predicted_pool = _predicted_preference_pool(
                manifest, SWEEP_DIR / "preference_pairwise_model.joblib", model,
            )
            if predicted_pool:
                user_picks = predicted_pool
            else:
                print("--use-predicted-preference set but no trained model found yet "
                      "(or nothing generated so far this round); using favorited images "
                      "instead", flush=True)
```

Modify `_predicted_preference_pool`'s inline import (`src/clawmarks/search/driver.py:288-309`):

```python
    import joblib

    from clawmarks.search import embed_cache
    from clawmarks.search.preference_model import predict_proba

    by_tag = {m["tag"]: m for m in manifest}

    def image_path_for(tag):
        return by_tag[tag]["file"]

    tags, embeddings = embed_cache.sync(manifest, embed_cache.EMBEDDINGS_FILE, embed_model, image_path_for)
    model = joblib.load(model_path)
    scores = predict_proba(model, embeddings)
```

becomes:

```python
    import joblib

    from clawmarks.search import embed_cache
    from clawmarks.search.preference_pairwise_model import score as pairwise_score

    by_tag = {m["tag"]: m for m in manifest}

    def image_path_for(tag):
        return by_tag[tag]["file"]

    tags, embeddings = embed_cache.sync(manifest, embed_cache.EMBEDDINGS_FILE, embed_model, image_path_for)
    model = joblib.load(model_path)
    scores = pairwise_score(model, embeddings)
```

Modify the `--use-predicted-preference` argparse help text (`src/clawmarks/search/driver.py:486-489`):

```python
        help="Stage 5b (opt-in, requires notes/uncanny_sweep/preference_model.joblib and "
             "human validation via preference_rank.html first): rank the exploit pool by the "
             "trained model's predicted preference instead of yes-rated images. Defaults off; "
             "do not enable without having browsed preference_rank.html first.",
```

becomes:

```python
        help="Stage 5b (opt-in, requires notes/uncanny_sweep/preference_pairwise_model.joblib "
             "and human validation via preference_rank.html first): rank the exploit pool by "
             "the trained model's predicted preference instead of favorited images. Defaults "
             "off; do not enable without having browsed preference_rank.html first.",
```

- [ ] **Step 4: Delete the old test file**

```bash
git rm tests/test_yes_rated_images.py
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_favorited_images.py tests/test_predicted_preference_pool.py -v`
Expected: PASS

- [ ] **Step 6: Run a broader check for any remaining reference to the old names in this file**

Run: `rg -n "_load_yes_rated_images|preference_model\.joblib\"|predict_proba|yes-rated" src/clawmarks/search/driver.py`
Expected: no matches.

- [ ] **Step 7: Commit**

```bash
git add src/clawmarks/search/driver.py tests/test_favorited_images.py
git commit -m "feat(search): driver uses favorited images and the pairwise model for Stage 5b"
```

---

### Task 8: Preference rank page — model import swap

**Files:**
- Modify: `src/clawmarks/build/preference_rank.py`

**Interfaces:**
- Consumes: Task 1's `preference_pairwise_model.MODEL_FILE`, `score`.
- Produces: same `compute_data(sweep_dir) -> dict` / `render_html(data) -> str` / `build_ranked_items(...)` signatures as before (Task's own existing tests, `test_preference_rank.py` and `test_preference_rank_live.py`, need no changes — they only exercise `build_ranked_items` and the no-model-yet path, neither of which depends on which model module is imported).

- [ ] **Step 1: Confirm the existing tests still describe the desired behavior**

Run: `uv run pytest tests/test_preference_rank.py tests/test_preference_rank_live.py -v`
Expected: PASS already (these tests don't reference `preference_model` by name, only `MODEL_FILE` via monkeypatch on the `preference_rank` module itself, so they keep passing before and after this task — this step is a sanity check, not a red-green step).

- [ ] **Step 2: Modify `preference_rank.py`**

Modify the module docstring (`src/clawmarks/build/preference_rank.py:1-8`):

```python
"""
Component 4 of the preference-classifier design: ranks every embedded image by the trained
model's predicted P(yes), highest first, so the model's judgment can be eyeballed against the
user's own taste before Stage 5b lets it steer anything live. Requires
search/preference_model.py to have already produced notes/uncanny_sweep/preference_model.joblib
(needs 50+ ratings — see search/preference_model.py's MIN_LABELS).

Served live at /preference_rank.html by curation_server.py.
"""
```

becomes:

```python
"""
Ranks every embedded image by the trained pairwise model's predicted preference score, highest
first, so the model's judgment can be eyeballed against the user's own taste before Stage 5b
lets it steer anything live. Requires search/preference_pairwise_model.py to have already
produced notes/uncanny_sweep/preference_pairwise_model.joblib (needs 50+ comparisons — see
search/preference_pairwise_model.py's MIN_COMPARISONS). See
docs/superpowers/specs/2026-07-11-head-to-head-preference-design.md.

Served live at /preference_rank.html by curation_server.py.
"""
```

Modify the import (`src/clawmarks/build/preference_rank.py:17`):

```python
from clawmarks.search.preference_model import MODEL_FILE, predict_proba
```

becomes:

```python
from clawmarks.search.preference_pairwise_model import MODEL_FILE, score
```

Modify `compute_data` (`src/clawmarks/build/preference_rank.py:34-47`):

```python
    tags, embeddings = embed_cache.load_cache(embed_cache.EMBEDDINGS_FILE)
    model = joblib.load(MODEL_FILE)
    scores = predict_proba(model, embeddings)
```

becomes:

```python
    tags, embeddings = embed_cache.load_cache(embed_cache.EMBEDDINGS_FILE)
    model = joblib.load(MODEL_FILE)
    scores = score(model, embeddings)
```

Modify the no-model error message (`src/clawmarks/build/preference_rank.py:50-53`):

```python
    if not data["has_model"]:
        return (f"<!doctype html><html><body>no trained model at {MODEL_FILE}; run `python -m "
                f"clawmarks.search.preference_model` first (needs 50+ ratings)</body></html>")
```

becomes:

```python
    if not data["has_model"]:
        return (f"<!doctype html><html><body>no trained model at {MODEL_FILE}; run `python -m "
                f"clawmarks.search.preference_pairwise_model` first (needs 50+ comparisons)</body></html>")
```

Modify the page's descriptive tooltip (`src/clawmarks/build/preference_rank.py:57-62`):

```python
    rank_tip = info_btn(
        "Sorted by the trained preference model's predicted probability that you'd rate this "
        "image 'yes,' highest first. This view exists to sanity-check the model before it's "
        "allowed to steer the live search: does the top of this list actually look like things "
        "you like?"
    )
```

becomes:

```python
    rank_tip = info_btn(
        "Sorted by the trained preference model's predicted score, highest first: the model "
        "learned this ranking from your head-to-head comparisons, not a yes/no judgment. This "
        "view exists to sanity-check the model before it's allowed to steer the live search: "
        "does the top of this list actually look like things you like?"
    )
```

The page's `<p class="sub">` text (`src/clawmarks/build/preference_rank.py:84`) already reads `Top {len(items)} images by predicted P(yes), highest first.` — update it to `Top {len(items)} images by predicted preference score, highest first.` since the score is no longer a probability.

- [ ] **Step 3: Run tests to verify nothing broke**

Run: `uv run pytest tests/test_preference_rank.py tests/test_preference_rank_live.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/clawmarks/build/preference_rank.py
git commit -m "feat(build): preference_rank uses the pairwise comparison model"
```

---

### Task 9: Preference status page — comparisons replace labels

**Files:**
- Modify: `src/clawmarks/build/preference_status.py`
- Modify: `tests/test_preference_status.py`

**Interfaces:**
- Consumes: Task 1's `preference_pairwise_model` (`MIN_COMPARISONS`, `MODEL_FILE`, `MODEL_META_FILE`).
- Produces: `compute_data(sweep_dir) -> dict` with keys `n_comparisons`, `min_comparisons`, `comparisons_gate_message`, `has_model`, `model_meta`, `use_predicted_preference` (replacing `n_yes`/`n_no`/`n_total`/`min_labels`/`labels_gate_message`). `render_html(data)` updated to match. Task 4's `_preference_status_watched_files` already watches `COMPARISONS_FILE` and the new model files (done in Task 4), so no further curation_server.py change is needed here.

- [ ] **Step 1: Replace `tests/test_preference_status.py` in full**

```python
# tests/test_preference_status.py
import json

from clawmarks.build import preference_status


def _write_comparisons(tmp_path, n):
    comparisons = [{"winner": f"w{i}", "loser": f"l{i}", "compared_at": "t"} for i in range(n)]
    (tmp_path / "user_comparisons.json").write_text(json.dumps(comparisons))


def test_compute_data_with_no_comparisons_file_reports_zero_count(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(preference_status.preference_pairwise_model, "MODEL_FILE", tmp_path / "preference_pairwise_model.joblib")
    data = preference_status.compute_data(tmp_path)
    assert data["n_comparisons"] == 0
    assert data["has_model"] is False
    assert data["model_meta"] is None
    assert data["use_predicted_preference"] is False
    assert "50" in data["comparisons_gate_message"]


def test_compute_data_below_min_comparisons_reports_count_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(preference_status.preference_pairwise_model, "MODEL_FILE", tmp_path / "preference_pairwise_model.joblib")
    _write_comparisons(tmp_path, 15)
    data = preference_status.compute_data(tmp_path)
    assert data["n_comparisons"] == 15
    assert "15" in data["comparisons_gate_message"] and "50" in data["comparisons_gate_message"]


def test_compute_data_at_min_comparisons_has_no_gate_message(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(preference_status.preference_pairwise_model, "MODEL_FILE", tmp_path / "preference_pairwise_model.joblib")
    _write_comparisons(tmp_path, 50)
    data = preference_status.compute_data(tmp_path)
    assert data["comparisons_gate_message"] == ""


def test_compute_data_reads_model_meta_and_toggle_when_model_exists(tmp_path, monkeypatch):
    settings_path = tmp_path / "preference_settings.json"
    model_path = tmp_path / "preference_pairwise_model.joblib"
    meta_path = tmp_path / "preference_pairwise_model_meta.json"
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", settings_path)
    monkeypatch.setattr(preference_status.preference_pairwise_model, "MODEL_FILE", model_path)
    monkeypatch.setattr(preference_status.preference_pairwise_model, "MODEL_META_FILE", meta_path)
    model_path.write_text("fake model bytes")
    meta = {"trained_at": "2026-07-11T00:00:00+00:00", "n_comparisons": 60, "cv_accuracy": 0.8}
    meta_path.write_text(json.dumps(meta))
    preference_status.preference_settings.save(True)

    data = preference_status.compute_data(tmp_path)
    assert data["has_model"] is True
    assert data["model_meta"] == meta
    assert data["use_predicted_preference"] is True


def test_render_html_disables_toggle_when_no_model():
    data = {"n_comparisons": 0, "min_comparisons": 50, "comparisons_gate_message": "not enough comparisons",
            "has_model": False, "model_meta": None, "use_predicted_preference": False}
    html = preference_status.render_html(data)
    assert "disabled" in html
    assert "/api/preference_toggle" in html


def test_render_html_enables_toggle_when_model_exists():
    meta = {"trained_at": "2026-07-11T00:00:00+00:00", "n_comparisons": 60, "cv_accuracy": 0.8}
    data = {"n_comparisons": 60, "min_comparisons": 50, "comparisons_gate_message": "",
            "has_model": True, "model_meta": meta, "use_predicted_preference": True}
    html = preference_status.render_html(data)
    assert "disabled" not in html
    assert "checked" in html
    assert "0.8" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_preference_status.py -v`
Expected: FAIL — `preference_status.preference_pairwise_model` doesn't exist yet, and `compute_data` still returns `n_yes`/`n_no`/`n_total`/`labels_gate_message`.

- [ ] **Step 3: Rewrite `preference_status.py` in full**

```python
# src/clawmarks/build/preference_status.py
"""
Shows whether the preference classifier (search/preference_pairwise_model.py) is trained and
ready, and exposes the single persisted toggle (search/preference_settings.py) that both
archive.html and `clawmarks run allnight` read to decide whether to use its predictions. See
docs/superpowers/specs/2026-07-11-head-to-head-preference-design.md.

Served live at /preference_status.html by curation_server.py.
"""
import json
import os

from clawmarks.search import preference_pairwise_model, preference_settings
from clawmarks.shared_ui import INFOTIP_CSS, MOBILE_BASE_CSS, TOPNAV_CSS, info_btn, nav_bar_html


def compute_data(sweep_dir):
    comparisons_path = f"{sweep_dir}/user_comparisons.json"
    if os.path.exists(comparisons_path):
        with open(comparisons_path) as f:
            comparisons = json.load(f)
    else:
        comparisons = []
    n_comparisons = len(comparisons)

    if n_comparisons < preference_pairwise_model.MIN_COMPARISONS:
        gate_message = (f"only {n_comparisons} comparisons (need "
                         f"{preference_pairwise_model.MIN_COMPARISONS}); compare more images "
                         f"via compare.html.")
    else:
        gate_message = ""

    has_model = os.path.exists(preference_pairwise_model.MODEL_FILE)
    model_meta = None
    if has_model and os.path.exists(preference_pairwise_model.MODEL_META_FILE):
        with open(preference_pairwise_model.MODEL_META_FILE) as f:
            model_meta = json.load(f)

    return {
        "n_comparisons": n_comparisons,
        "min_comparisons": preference_pairwise_model.MIN_COMPARISONS,
        "comparisons_gate_message": gate_message,
        "has_model": has_model,
        "model_meta": model_meta,
        "use_predicted_preference": preference_settings.load()["use_predicted_preference"],
    }


def render_html(data):
    gate_html = (f'<p class="gate">{data["comparisons_gate_message"]}</p>'
                 if data["comparisons_gate_message"] else '<p class="gate ok">ready to train.</p>')

    if data["model_meta"]:
        m = data["model_meta"]
        meta_html = (f'<table class="meta"><tr><td>trained</td><td>{m["trained_at"]}</td></tr>'
                     f'<tr><td>comparisons used</td><td>{m["n_comparisons"]}</td></tr>'
                     f'<tr><td>cross-validated accuracy</td><td>{m["cv_accuracy"]}</td></tr></table>')
    else:
        meta_html = (f'<p class="meta-empty">no model trained yet. Once enough comparisons exist, run '
                     f'<code>python -m clawmarks.search.preference_pairwise_model</code>.</p>')

    disabled_attr = "" if data["has_model"] else "disabled"
    checked_attr = "checked" if data["use_predicted_preference"] else ""

    toggle_tip = info_btn(
        "When on, archive.html's fallback champion per MAP-Elites cell and the next "
        "`clawmarks run allnight`'s exploit pool both use this trained model's predicted "
        "preference instead of raw novelty / favorited images. Off by default; only turn this "
        "on after eyeballing preference_rank.html against your own taste."
    )

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>CLAWMARKS preference status</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ color-scheme: dark; --bg:#0b0b0d; --panel:#16161a; --border:#2a2a30; --text:#eaeaee; --text-dim:#9a9aa4; }}
body {{ background:var(--bg); color:var(--text); font-family:-apple-system,sans-serif; margin:0; padding:24px; }}
{TOPNAV_CSS}
{MOBILE_BASE_CSS}
h1 {{ font-size:18px; margin:0 0 4px; }}
p.sub {{ color:var(--text-dim); max-width:760px; font-size:13px; line-height:1.6; }}
.panel {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:16px; margin-top:16px; max-width:520px; }}
p.gate {{ color:#e0a030; }}
p.gate.ok {{ color:#5fbf6f; }}
table.meta {{ font-size:13px; border-collapse:collapse; }}
table.meta td {{ padding:3px 10px 3px 0; color:var(--text-dim); }}
table.meta td:first-child {{ color:var(--text); }}
.toggle-row {{ margin-top:14px; display:flex; align-items:center; gap:8px; }}
#toggle-status {{ font-size:12px; color:var(--text-dim); margin-left:8px; }}
{INFOTIP_CSS}
</style></head><body>

{nav_bar_html('preference_status.html')}
<h1>Preference classifier status</h1>
<p class="sub">Comparisons: {data["n_comparisons"]} total (needs {data["min_comparisons"]}).</p>
<div class="panel">
{gate_html}
{meta_html}
<div class="toggle-row">
<label><input type="checkbox" id="toggle" {checked_attr} {disabled_attr} onchange="toggle(this.checked)"> use predicted preference{toggle_tip}</label>
<span id="toggle-status"></span>
</div>
</div>
<script>
function toggle(enabled) {{
  const status = document.getElementById('toggle-status');
  status.textContent = 'saving...';
  fetch('/api/preference_toggle', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{enabled: enabled}}),
  }}).then(r => r.json()).then(data => {{
    if (data.error) {{
      status.textContent = data.error;
      document.getElementById('toggle').checked = !enabled;
    }} else {{
      status.textContent = 'saved.';
    }}
  }});
}}
</script>
<script src="scrollnav.js"></script>
<script src="infotip.js"></script>
</body></html>"""
    return html
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_preference_status.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Run the curation_server preference-status route tests again to confirm the cross-module rename didn't break the live route**

Run: `uv run pytest tests/test_curation_server_preference_status_route.py -v`
Expected: PASS (this route test asserts on the page title and JSON shape, not the removed `n_yes`/`n_no` fields, so it should already be fine from Task 4 — this is a regression check).

- [ ] **Step 6: Commit**

```bash
git add src/clawmarks/build/preference_status.py tests/test_preference_status.py
git commit -m "feat(build): preference_status reports comparisons instead of yes/no labels"
```

---

### Task 10: Full-suite verification and cleanup sweep

**Files:** none (verification only)

- [ ] **Step 1: Run the complete test suite**

Run: `uv run pytest -v 2>&1 | tail -60`
Expected: all tests pass. If any test outside this plan's scope fails, investigate whether it's a pre-existing failure (check `git stash` + rerun on a clean `main` to confirm) or a regression from this plan's changes before proceeding.

- [ ] **Step 2: Grep for any leftover reference to the retired yes/no system outside of the legacy migration script and the design docs**

Run: `rg -n "preference_model\b|rating_sampler|rate_page|rate\.html|predict_proba|/api/rate\b|/api/ratings\b" src/`

Expected matches: only `src/clawmarks/config.py` (the untouched `USER_RATINGS_FILE` constant, kept for the legacy migration script) and `src/clawmarks/search/migrate_picks_to_ratings.py` (the historical one-off migration script, intentionally untouched). If anything else matches, fix it — it's a missed call site from an earlier task.

- [ ] **Step 3: Confirm the legacy yes/no files are untouched, not deleted, if a `notes/uncanny_seedrun1` or `notes/uncanny_sweep` directory exists with them**

Run: `fd -a "user_ratings.json|preference_model.joblib" notes/ 2>/dev/null || true`
Expected: any matches found are left as-is; this step is a sanity check, not an action step. Do not delete or modify anything this command finds.

- [ ] **Step 4: Manually smoke-test the live server** (not automatable — requires the Playwright verification this project's CLAUDE.md requires for visual deliverables)

Start the server pointed at whichever sweep directory currently has embeddings and enough comparisons to be interesting (check `notes/*/embeddings.npz` and `notes/*/scored_manifest.json`), then use the Playwright MCP tools to open `/compare.html`, exercise a click-to-pick and a keyboard pick, open and close a zoom overlay, and confirm `/preference_status.html` and `/preference_rank.html` reflect the new comparison-based state without errors in the browser console.

- [ ] **Step 5: Update the lab notebook**

Per this project's CLAUDE.md, append a dated entry to `notes/lab_notebook.md`'s lab log noting that the yes/no rating system was replaced by head-to-head comparisons, linking the spec (`docs/superpowers/specs/2026-07-11-head-to-head-preference-design.md`) and this plan, and noting that the old `user_ratings.json`/`preference_model.joblib` files remain on disk unused. This is a manual documentation step, not a code change — do it by hand once the smoke test in Step 4 passes.

- [ ] **Step 6: Final commit if Steps 2-5 produced any fixes or notebook edits**

```bash
git add -A
git commit -m "chore: verify head-to-head preference migration end-to-end, update lab notebook"
```
