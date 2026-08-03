# Task 6: `build/elite_archive.py` reads ratings, not picks

Context: earlier tasks in this plan added `user_ratings.json` (via `curation_server.py`'s
`/api/ratings`, `/api/rate/next`, `/api/rate` endpoints, and `rate.html`) as the replacement
for the old pick/unpick workflow, which Task 5 already removed from the lightbox UI. This task
switches `elite_archive.py` (the "elite archive" build page) from reading the old
`user_picks.json` to reading `user_ratings.json`'s yes-labels, and from its own inline
`item_summary` helper to the shared `clawmarks.search.manifest_index.item_summary(m, SWEEP_DIR)`
(added in an earlier task in this plan).

## Files

- Modify: `src/clawmarks/build/elite_archive.py`
- Create: `tests/test_elite_archive.py`

## Interfaces

- Consumes: `manifest_index.item_summary(m, SWEEP_DIR)` (already implemented in
  `src/clawmarks/search/manifest_index.py` by an earlier task) — replaces this file's own
  inline `item_summary` definition.

## Step 1: Write the failing test

```python
# tests/test_elite_archive.py
import json
import re

from clawmarks.build import elite_archive


def test_main_uses_yes_rated_images_not_user_picks(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(elite_archive, "SWEEP_DIR", tmp_path)
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
    # "a" has lower novelty than "b" but is yes-rated: it should win the cell despite that,
    # exactly the behavior user_picks.json used to provide.
    (tmp_path / "user_ratings.json").write_text(json.dumps({"a": {"label": "yes", "rated_at": "t0"}}))
    # a stale user_picks.json should be ignored entirely
    (tmp_path / "user_picks.json").write_text(json.dumps({"b": {"picked_at": "t0"}}))

    elite_archive.main([])

    captured = capsys.readouterr()
    assert "1 occupied cells, 1 human-picked elites" in captured.out

    html = (tmp_path / "archive.html").read_text()
    match = re.search(r"const CELLS = (\[.+?\]);\nlet picks", html)
    assert match is not None, "could not find 'const CELLS = [...]; let picks' in archive.html"
    cells = json.loads(match.group(1))
    assert len(cells) == 1
    tags_in_cell = {item["tag"] for item in cells[0]["items"]}
    assert tags_in_cell == {"a", "b"}
```

## Step 2: Run test to verify it fails

Run: `pytest tests/test_elite_archive.py -v`
Expected: FAIL — the current code reads `user_picks.json`, so `picks = {"b": ...}` (not `{"a":
...}`), and the printed line reads `1 occupied cells, 1 human-picked elites` for the wrong tag
(`b`, not `a`); the test's own `tags_in_cell` assertion still passes (both tags are in the one
forced cell either way) but a manual check confirms `n_human` is counted against `b`'s pick, not
`a`'s rating, before the fix. The test as written will start passing only once Step 3's change
makes `picks` come from `user_ratings.json`'s yes-labels instead of `user_picks.json` — until
then, it fails because `elite_archive.py` still has the inline `item_summary` function and the
`picks_path`/`user_picks.json` loading block Step 3 removes, which the test doesn't yet
reference but which govern `n_human`'s count in a way not yet driven by ratings.

## Step 3: Modify `elite_archive.py`

Change the import block:

```python
from clawmarks.config import SWEEP_DIR
from clawmarks.search.manifest_index import item_summary
from clawmarks.shared_ui import (
    nav_bar_html, TOPNAV_CSS, MOBILE_BASE_CSS, write_lightbox_asset, write_scrollnav_asset,
    write_infotip_asset, INFOTIP_CSS, info_btn,
)
```

Update the module docstring's second paragraph to say:

```
Elite selection per cell: a yes-rated image (notes/uncanny_sweep/user_ratings.json) wins if one
exists in that cell, since a person's judgment substitutes for the coherence/quality scorer this
project doesn't have (lab_notebook.md Section 3b). Otherwise falls back to highest novelty in
the cell, matching the ranking the search itself uses to build its automated "elites" list.
```

Replace the picks-loading block:

```python
    picks = {}
    picks_path = f"{SWEEP_DIR}/user_picks.json"
    if os.path.exists(picks_path):
        with open(picks_path) as f:
            picks = json.load(f)
```

with:

```python
    ratings = {}
    ratings_path = f"{SWEEP_DIR}/user_ratings.json"
    if os.path.exists(ratings_path):
        with open(ratings_path) as f:
            ratings = json.load(f)
    picks = {tag: r for tag, r in ratings.items() if r.get("label") == "yes"}
```

(Everything downstream — `n_human`, `picked_here`, `.human` CSS class — keeps working unchanged
since `picks` still ends up as "the set of tags that won their cell.")

Delete the inline `item_summary` function:

```python
    def item_summary(m):
        return {
            "tag": m["tag"], "prompt_name": m["prompt_name"], "prompt_type": m["prompt_type"],
            "faith": round(m["centroid_sim"], 4), "novelty": round(m["novelty"], 4),
            "strength": m["strength"], "cfg": m["cfg"],
            "thumb": (f"thumbs/{m['tag']}.jpg" if os.path.exists(f"{SWEEP_DIR}/thumbs/{m['tag']}.jpg")
                      else os.path.basename(m["file"])),
            "file": os.path.basename(m["file"]),
        }
```

and update its call site:

```python
                "items": [item_summary(m) for m in sorted(items, key=lambda m: -m["novelty"])],
```

to:

```python
                "items": [item_summary(m, SWEEP_DIR) for m in sorted(items, key=lambda m: -m["novelty"])],
```

In the JS template, rename the source label so it matches reality. Change:

```javascript
function eliteFor(c) {{
  const pickedHere = c.items.filter(it => picks[it.tag]);
  if (pickedHere.length) return {{ item: pickedHere[0], source: 'human pick' }};
  return {{ item: c.items[0], source: 'highest novelty' }};  // items pre-sorted by -novelty
}}
```

to:

```javascript
function eliteFor(c) {{
  const pickedHere = c.items.filter(it => picks[it.tag]);
  if (pickedHere.length) return {{ item: pickedHere[0], source: 'yes-rated' }};
  return {{ item: c.items[0], source: 'highest novelty' }};  // items pre-sorted by -novelty
}}
```

Update the one place that compares against the old string:

```javascript
  const human = source === 'human pick';
```

to:

```javascript
  const human = source === 'yes-rated';
```

Replace the picks-fetch-plus-live-update block at the bottom of the script (the pick button that
fired `lightbox:pick` no longer exists after Task 5, so this listener never fires):

```javascript
document.addEventListener('lightbox:pick', e => {{
  if (e.detail.picked) picks[e.detail.tag] = true; else delete picks[e.detail.tag];
  render();
  if (document.getElementById('modal').classList.contains('open')) {{
    document.querySelectorAll('#modalGrid .item').forEach(el => {{
      el.classList.toggle('human', !!picks[el.title]);
    }});
  }}
}});

fetch('/api/picks').then(r => r.json()).then(p => {{ picks = p; render(); }}).catch(() => {{ render(); }});
```

with:

```javascript
fetch('/api/ratings').then(r => r.json()).then(ratings => {{
  picks = {{}};
  Object.entries(ratings).forEach(([tag, r]) => {{ if (r.label === 'yes') picks[tag] = true; }});
  render();
}}).catch(() => {{ render(); }});
```

Update the page's descriptive copy: change `"Gold-bordered cells are human-picked winners;"` to
`"Gold-bordered cells are yes-rated winners;"`.

## Step 4: Run tests to verify they pass

Run: `pytest tests/test_elite_archive.py -v`
Expected: PASS

Run the full suite: `pytest -v`
Expected: all PASS.

## Step 5: Commit

```bash
git add src/clawmarks/build/elite_archive.py tests/test_elite_archive.py
git commit -m "feat(clawmarks): elite archive reads yes-ratings instead of picks"
```

## Global Constraints

- Conventional Commits format for the commit message.
- No changes to files outside the listed set.
- Don't touch Stage-5b opt-in flag or favoriting paths.
