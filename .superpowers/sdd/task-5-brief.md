### Task 5: Remove "pick as winner" from the lightbox; add `rate.html`

**Files:**
- Modify: `src/clawmarks/shared_ui.py`
- Create: `src/clawmarks/build/rate_page.py`
- Modify: `src/clawmarks/cli.py`
- Create: `tests/test_rate_page.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Produces: `build.rate_page.main(argv=None)` writes `rate.html`, wired into
  `clawmarks build rate`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rate_page.py
from clawmarks.build import rate_page


def test_main_writes_rate_html(tmp_path, monkeypatch):
    monkeypatch.setattr(rate_page, "SWEEP_DIR", tmp_path)
    rate_page.main([])
    out = tmp_path / "rate.html"
    assert out.exists()
    content = out.read_text()
    assert "/api/rate/next" in content
    assert "/api/rate" in content
```

```python
# addition to tests/test_cli.py
def test_build_rate_subcommand_parses():
    parser = build_parser()
    args = parser.parse_args(["build", "rate"])
    assert args.command == "build"
    assert args.target == "rate"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rate_page.py tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clawmarks.build.rate_page'` and an
`argparse` error for the unrecognized `rate` choice.

- [ ] **Step 3: Modify `shared_ui.py`**

Add `"rate.html"` to `NAV_OPTIONS`, right after `"explore.html"`:

```python
NAV_OPTIONS = [
    ("explore.html", "all tools (hub)"),
    ("rate.html", "rate images (yes/no)"),
    ("scan.html", "scan gallery"),
```

Remove the pick button and its tooltip from `_LIGHTBOX_JS`'s `el.innerHTML` template. Change:

```javascript
    <button class="lb-back" style="display:none;">&#8592; back</button>
    <button class="lb-pick">&#9733; pick as winner</button>
    <span class="infobtn" data-id="lb-tip-pick" data-tip="Picking marks this image as a human-approved success. The next search generation uses picked images as starting points for new variations, ahead of the algorithm's own ranking: it's how your judgment steers where the search goes next.">?</span>
    <button class="lb-favorite">&#9825; favorite</button>
```

to:

```javascript
    <button class="lb-back" style="display:none;">&#8592; back</button>
    <button class="lb-favorite">&#9825; favorite</button>
```

Remove the now-unused CSS rule `#lb-overlay button.picked { ... }` from the style block.

Remove the `let picks = {};` declaration (search the file for `let favorites = {};` — the pick
variable sits right before it).

Remove the wiring line `el.querySelector('.lb-pick').onclick = togglePick;` from the DOM-setup
block (keep `el.querySelector('.lb-favorite').onclick = toggleFavorite;`).

Remove the pick keyboard shortcut from the `keydown` listener:

```javascript
      if (e.key === ' ') { e.preventDefault(); togglePick(); }
```

Remove `loadPicks()`:

```javascript
  function loadPicks(){
    return fetch('/api/picks').then(r => r.json()).then(p => { picks = p; }).catch(() => {});
  }
```

Change the `Promise.all` call in `open()` from:

```javascript
    Promise.all([loadData(), loadPicks(), loadFavorites(), loadCounterfactuals()]).then(() => {
```

to:

```javascript
    Promise.all([loadData(), loadFavorites(), loadCounterfactuals()]).then(() => {
```

Remove the pick-button rendering block from `render()`:

```javascript
    const isPicked = !!picks[d.tag];
    const pickBtn = el.querySelector('.lb-pick');
    pickBtn.textContent = isPicked ? '★ picked (click to unpick)' : '☆ pick as winner';
    pickBtn.classList.toggle('picked', isPicked);
```

Remove the `togglePick()` function entirely:

```javascript
  function togglePick(){
    const d = order[idx];
    const isPicked = !!picks[d.tag];
    const endpoint = isPicked ? '/api/unpick' : '/api/pick';
    const body = isPicked ? {tag: d.tag} : Object.assign({}, d);
    fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
      .then(r => r.json())
      .then(() => {
        if (isPicked) delete picks[d.tag]; else picks[d.tag] = body;
        render();
        document.dispatchEvent(new CustomEvent('lightbox:pick', {detail: {tag: d.tag, picked: !isPicked}}));
      });
  }
```

(Keep `toggleFavorite()` exactly as-is.)

- [ ] **Step 4: Create `build/rate_page.py`**

```python
# src/clawmarks/build/rate_page.py
"""
Generates rate.html: a full-screen, keyboard-driven yes/no rating page. Unlike every other
build/*.py generator, this page bakes in no per-image data at build time — it fetches
GET /api/rate/next itself and POSTs to /api/rate, both served by curation_server.py, so the page
never goes stale between rebuilds. Rebuilding only matters if this file itself changes.

Run with: python3 -m clawmarks.build.rate_page (or `clawmarks build rate`)
"""
from clawmarks.config import SWEEP_DIR
from clawmarks.shared_ui import (
    nav_bar_html, TOPNAV_CSS, MOBILE_BASE_CSS, write_scrollnav_asset, write_infotip_asset,
    INFOTIP_CSS, info_btn,
)


def main(argv=None):
    write_scrollnav_asset(SWEEP_DIR)
    write_infotip_asset(SWEEP_DIR)

    rate_tip = info_btn(
        "Rating trains the preference classifier: yes/no on as many images as you can stand "
        "to look at. Yes-rated images immediately take over the search's exploit pool (the same "
        "role picking used to play); once enough ratings exist, a model trained on them takes "
        "over ranking automatically."
    )

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>CLAWMARKS rate</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ color-scheme: dark; --bg:#0b0b0d; --panel:#16161a; --border:#2a2a30; --text:#eaeaee;
  --text-dim:#9a9aa4; --yes:#5ec98a; --no:#e0605e; }}
body {{ background:var(--bg); color:var(--text); font-family:-apple-system,sans-serif; margin:0; padding:24px;
  display:flex; flex-direction:column; align-items:center; }}
{TOPNAV_CSS}
{MOBILE_BASE_CSS}
h1 {{ font-size:18px; margin:0 0 4px; align-self:flex-start; }}
p.sub {{ color:var(--text-dim); max-width:640px; font-size:13px; line-height:1.6; align-self:flex-start; }}
#stage {{ margin-top:20px; width:100%; max-width:640px; display:flex; flex-direction:column; align-items:center; }}
#img {{ max-width:100%; max-height:60vh; border-radius:10px; box-shadow:0 20px 60px rgba(0,0,0,0.6); }}
#meta {{ color:var(--text-dim); font-size:12.5px; margin-top:10px; text-align:center; }}
#buttons {{ display:flex; gap:16px; margin-top:18px; }}
#buttons button {{ font-size:16px; padding:14px 34px; border-radius:10px; cursor:pointer; border:1px solid var(--border); background:var(--panel); color:var(--text); }}
#buttons .no {{ border-color:var(--no); color:var(--no); }}
#buttons .yes {{ border-color:var(--yes); color:var(--yes); }}
#count {{ color:var(--text-dim); font-size:12px; margin-top:14px; }}
#done {{ color:var(--text-dim); font-size:14px; margin-top:40px; text-align:center; }}
{INFOTIP_CSS}
</style></head><body>

{nav_bar_html('rate.html')}
<h1>Rate{rate_tip}</h1>
<p class="sub">Yes or no, as fast as you can go. Keyboard: &larr; or n = no, &rarr; or y = yes.</p>

<div id="stage">
  <img id="img" style="display:none;">
  <div id="meta"></div>
  <div id="buttons" style="display:none;">
    <button class="no" onclick="rate('no')">&larr; no</button>
    <button class="yes" onclick="rate('yes')">yes &rarr;</button>
  </div>
  <div id="done" style="display:none;">Nothing left to rate right now &mdash; every image in the pool has been rated or favorited.</div>
</div>
<div id="count"></div>

<script>
let current = null;
let ratedThisSession = 0;

function loadNext() {{
  document.getElementById('buttons').style.display = 'none';
  fetch('/api/rate/next').then(r => r.json()).then(d => {{
    if (d.done) {{
      current = null;
      document.getElementById('img').style.display = 'none';
      document.getElementById('done').style.display = 'block';
      return;
    }}
    current = d;
    const img = document.getElementById('img');
    img.src = d.thumb;
    img.style.display = 'block';
    document.getElementById('meta').textContent =
      `${{d.prompt_name}} | faith=${{d.faith}} novelty=${{d.novelty}}`;
    document.getElementById('buttons').style.display = 'flex';
  }});
}}

function rate(label) {{
  if (!current) return;
  const tag = current.tag;
  fetch('/api/rate', {{method:'POST', headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{tag, label}})}})
    .then(r => r.json())
    .then(() => {{
      ratedThisSession++;
      document.getElementById('count').textContent = `${{ratedThisSession}} rated this session`;
      loadNext();
    }});
}}

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowLeft' || e.key === 'n' || e.key === 'N') rate('no');
  if (e.key === 'ArrowRight' || e.key === 'y' || e.key === 'Y') rate('yes');
}});

loadNext();
</script>
<script src="scrollnav.js"></script>
<script src="infotip.js"></script>
</body></html>"""

    with open(f"{SWEEP_DIR}/rate.html", "w") as f:
        f.write(html)

    print(f"wrote {SWEEP_DIR}/rate.html", flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Wire `rate` into `cli.py`**

In `_build_targets()`, add `rate_page` to the import and the returned dict:

```python
    from clawmarks.build import (
        scan_gallery, elite_archive, coverage_map, map_view, redundancy_view,
        novelty_decay, lineage_view, solution_map, similarity_index, thumbnails,
        explore_hub, seed_browser, probe_report, uncanny_gallery, rate_page,
    )
    return {
        "scan": scan_gallery.main,
        "archive": elite_archive.main,
        "coverage": coverage_map.main,
        "map": map_view.main,
        "redundancy": redundancy_view.main,
        "novelty-decay": novelty_decay.main,
        "lineage": lineage_view.main,
        "solution-map": solution_map.main,
        "similarity": similarity_index.main,
        "thumbnails": thumbnails.main,
        "explore-hub": explore_hub.main,
        "seeds": seed_browser.main,
        "probe-report": probe_report.main,
        "uncanny-gallery": uncanny_gallery.main,
        "rate": rate_page.main,
    }
```

Add `"rate"` to the `build_p.add_argument("target", choices=[...])` list.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_rate_page.py tests/test_cli.py -v`
Expected: PASS (2 new tests, plus existing `test_cli.py` tests still pass)

Run the full suite: `pytest -v`
Expected: all PASS. `grep -rn "lb-pick\|togglePick\|loadPicks" src/` should return nothing.

- [ ] **Step 7: Commit**

```bash
git add src/clawmarks/shared_ui.py src/clawmarks/build/rate_page.py src/clawmarks/cli.py tests/test_rate_page.py tests/test_cli.py
git commit -m "feat(clawmarks): remove pick-as-winner from the lightbox, add rate.html"
```

---


## Global Constraints (apply to every task in this plan)

- Follow `docs/superpowers/specs/2026-07-09-preference-classifier-design.md` exactly; it is the
  source of truth for behavior this plan doesn't repeat verbatim.
- Pin every new dependency version exactly (project convention — see `pyproject.toml`'s existing
  `==` pins). Install with `uv add <package>==<version>`, never bare `pip install`.
- All file paths in code come from `clawmarks.config` (`ROOT`, `SWEEP_DIR`, etc.), never a
  hardcoded `/workspace/trent-with-smart-prompts` string.
- Every new pure-logic module gets unit tests under `tests/`, following this repo's existing
  pattern of testing pure functions directly rather than booting a real HTTP server (see
  `tests/test_seed_pool.py`, `tests/test_scoring.py`, `tests/test_generation_jobs.py`).
- Run `pytest` after every task's implementation step, not just at the end.
- Favoriting (`user_favorites.json`, the star/bookmark button, `/api/favorite`,
  `/api/unfavorite`) is never touched by this plan.
- Stage 5b (the trained model steering the live search) ships behind an opt-in flag that
  defaults off. Do not flip it on as part of this plan.
