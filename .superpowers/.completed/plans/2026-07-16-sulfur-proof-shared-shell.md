# Sulfur Proof Shared Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved Sulfur Proof typography, tokens, tactile controls, context header, and responsive accessibility rules across every live curation page.

**Architecture:** Keep the existing server-rendered Python pages, but move the visual foundation and shared header behavior into `shared_ui.py`. Serve bundled fonts and shared browser code from package resources. Page modules retain their evidence-specific layouts while consuming one shell instead of defining competing themes.

**Tech Stack:** Python 3.10+, `http.server`, server-rendered HTML/CSS/JavaScript, pytest, Playwright MCP.

## Global Constraints

- Preserve the approved palette exactly: paper `#C3C5BA`, paper-deep `#B3B5A9`, ink `#11120F`, soft `#4D5048`, rule `#898D81`, sulfur `#CBD63F`, Guide surface `#20251B`, Guide ink `#ECEFDF`.
- Bundle Barlow Condensed, IBM Plex Sans, and IBM Plex Mono. Production pages make no runtime font request.
- Keep normal body text at least 14px desktop and 15px mobile; controls have 44px touch targets at 700px and below.
- Use hard unblurred depth only. Ordinary prose and data rows remain flat.
- Preserve every current route and interaction while changing presentation.
- Run Python and tests through `uv run` only.
- Do not touch generation-output directories during visual verification.

## File Structure

- Create `src/clawmarks/static/fonts/`: bundled OFL font files and licenses.
- Modify `pyproject.toml`: package the static assets.
- Modify `src/clawmarks/shared_ui.py`: visual tokens, typography, common controls, context header, dialog, and browser behavior.
- Modify `src/clawmarks/curation_server.py`: serve package assets and shared shell JavaScript.
- Modify every `src/clawmarks/build/*.py` page that calls `nav_bar_html()`: consume the shared shell and remove conflicting theme roots.
- Modify status/error rendering in `src/clawmarks/curation_server.py`: use the same shell.
- Modify `tests/test_shared_ui.py` and `tests/test_curation_server_static_assets.py`: shared contract coverage.
- Modify page-specific render tests under `tests/`: reject old theme roots and assert required evidence treatments.

### Task 1: Bundle Fonts And Serve Package Assets

**Files:**
- Create: `src/clawmarks/static/fonts/BarlowCondensed-SemiBold.ttf`
- Create: `src/clawmarks/static/fonts/BarlowCondensed-ExtraBold.ttf`
- Create: `src/clawmarks/static/fonts/IBMPlexSans-Variable.ttf`
- Create: `src/clawmarks/static/fonts/IBMPlexMono-Regular.ttf`
- Create: `src/clawmarks/static/fonts/IBMPlexMono-SemiBold.ttf`
- Create: `src/clawmarks/static/fonts/LICENSE-Barlow.txt`
- Create: `src/clawmarks/static/fonts/LICENSE-IBM-Plex.txt`
- Create: `src/clawmarks/static/fonts/SHA256SUMS`
- Modify: `pyproject.toml`
- Modify: `src/clawmarks/curation_server.py:122-123,1377-1393`
- Test: `tests/test_curation_server_static_assets.py`

**Interfaces:**
- Produces: `GET /assets/fonts/<allowlisted-name>` with the correct font MIME type and immutable cache header.
- Produces: package data available from both a source checkout and an installed wheel.

- [ ] **Step 1: Write failing asset-route tests**

```python
def test_bundled_font_is_served(running_server):
    port = running_server.server_address[1]
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}/assets/fonts/IBMPlexSans-Variable.ttf"
    ) as response:
        assert response.headers["Content-Type"] == "font/ttf"
        assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        assert response.read()[:4] in {b"\x00\x01\x00\x00", b"OTTO"}


def test_asset_route_rejects_path_traversal(running_server):
    port = running_server.server_address[1]
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(
            f"http://127.0.0.1:{port}/assets/fonts/..%2F..%2Fconfig.py"
        )
    assert exc.value.code == 404
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `uv run pytest -q tests/test_curation_server_static_assets.py`

Expected: FAIL because `/assets/fonts/IBMPlexSans-Variable.ttf` is not served.

- [ ] **Step 3: Add the pinned font assets and licenses**

Run these exact commands from the repository root:

```bash
ls src/clawmarks/static
mkdir -p src/clawmarks/static/fonts
curl -fL https://raw.githubusercontent.com/google/fonts/89f5431ff0db41bd2fe3f7ba21a723a01622428b/ofl/barlowcondensed/BarlowCondensed-SemiBold.ttf -o src/clawmarks/static/fonts/BarlowCondensed-SemiBold.ttf
curl -fL https://raw.githubusercontent.com/google/fonts/89f5431ff0db41bd2fe3f7ba21a723a01622428b/ofl/barlowcondensed/BarlowCondensed-ExtraBold.ttf -o src/clawmarks/static/fonts/BarlowCondensed-ExtraBold.ttf
curl -fL https://raw.githubusercontent.com/google/fonts/89f5431ff0db41bd2fe3f7ba21a723a01622428b/ofl/barlowcondensed/OFL.txt -o src/clawmarks/static/fonts/LICENSE-Barlow.txt
curl -fL "https://raw.githubusercontent.com/google/fonts/8409f033cd7dee08914990602f0df5f5e70e0c14/ofl/ibmplexsans/IBMPlexSans%5Bwdth%2Cwght%5D.ttf" -o src/clawmarks/static/fonts/IBMPlexSans-Variable.ttf
curl -fL https://raw.githubusercontent.com/google/fonts/633f3200539c52ee0aba2dfd7f46921417a81877/ofl/ibmplexmono/IBMPlexMono-Regular.ttf -o src/clawmarks/static/fonts/IBMPlexMono-Regular.ttf
curl -fL https://raw.githubusercontent.com/google/fonts/633f3200539c52ee0aba2dfd7f46921417a81877/ofl/ibmplexmono/IBMPlexMono-SemiBold.ttf -o src/clawmarks/static/fonts/IBMPlexMono-SemiBold.ttf
curl -fL https://raw.githubusercontent.com/google/fonts/8409f033cd7dee08914990602f0df5f5e70e0c14/ofl/ibmplexsans/OFL.txt -o src/clawmarks/static/fonts/LICENSE-IBM-Plex.txt
```

Verify each downloaded file is non-empty and recognized as TrueType: `file src/clawmarks/static/fonts/*.ttf`.
Create `src/clawmarks/static/fonts/SHA256SUMS` with these exact contents:

```text
7b619d14bc2327509a9ef32b0890f709626f7ecc9ff61191c2a4314c5499d2d9  src/clawmarks/static/fonts/BarlowCondensed-SemiBold.ttf
724c9c25952d5f4a2d87185d9767aa006144c5f0d944dc05bf7d5d603551c260  src/clawmarks/static/fonts/BarlowCondensed-ExtraBold.ttf
3b031aa4216174205bd8471f88a49b91f093169e9e87bd5262242bc5967fe2e3  src/clawmarks/static/fonts/IBMPlexSans-Variable.ttf
6a3412f058c7d8dfd9170c41e85ade48e5156ecb89356110ca57a0a27734af46  src/clawmarks/static/fonts/IBMPlexMono-Regular.ttf
d3c38e55c78f5b0f28009fddba4834ec503278936a5986032424c9bd2d23aa46  src/clawmarks/static/fonts/IBMPlexMono-SemiBold.ttf
186d750eb496a4c17a76385f82be6aea2ac1cf2de074a811d63786cf374ea73f  src/clawmarks/static/fonts/LICENSE-Barlow.txt
7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da  src/clawmarks/static/fonts/LICENSE-IBM-Plex.txt
```

Run: `sha256sum -c src/clawmarks/static/fonts/SHA256SUMS`

Expected: all seven lines report `OK`.

- [ ] **Step 4: Package and serve only allowlisted assets**

Add to `pyproject.toml`:

```toml
[tool.setuptools.package-data]
clawmarks = ["static/**/*"]
```

Use `importlib.resources.files("clawmarks").joinpath("static", "fonts", name).read_bytes()` in `curation_server.py`. Accept only names in a constant `FONT_ASSETS`; do not map arbitrary URL text to the filesystem.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_curation_server_static_assets.py`

Expected: PASS.

```bash
git add pyproject.toml src/clawmarks/static/fonts src/clawmarks/curation_server.py tests/test_curation_server_static_assets.py
git commit -m "feat(ui): bundle Sulfur Proof fonts"
```

### Task 2: Define The Sulfur Proof Foundation

**Files:**
- Modify: `src/clawmarks/shared_ui.py:46-106,129-196`
- Test: `tests/test_shared_ui.py`

**Interfaces:**
- Produces: `SULFUR_CSS`, `SULFUR_FONT_CSS`, `CONTROL_CSS`, `TOPNAV_CSS`, and `MOBILE_BASE_CSS`.
- Preserves: temporary legacy aliases (`--bg`, `--panel`, `--panel-2`, `--border`, `--text`, `--text-dim`, `--accent`) so page migration can proceed without a flag day.

- [ ] **Step 1: Write failing token and depth tests**

```python
def test_sulfur_tokens_and_fonts_are_exact():
    assert "--paper:#C3C5BA" in shared_ui.SULFUR_CSS
    assert "--text-soft:#4D5048" in shared_ui.SULFUR_CSS
    assert "Barlow Condensed" in shared_ui.SULFUR_FONT_CSS
    assert "url('/assets/fonts/" in shared_ui.SULFUR_FONT_CSS
    assert "https://" not in shared_ui.SULFUR_FONT_CSS


def test_depth_uses_hard_shadows_and_reduced_motion():
    assert "box-shadow:4px 4px 0" in shared_ui.CONTROL_CSS
    assert "@media (prefers-reduced-motion: reduce)" in shared_ui.SULFUR_CSS
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `uv run pytest -q tests/test_shared_ui.py`

Expected: FAIL because the Sulfur constants do not exist.

- [ ] **Step 3: Add exact shared CSS constants**

Define the foundation with this shape:

```python
SULFUR_FONT_CSS = """
@font-face { font-family:"Barlow Condensed"; src:url('/assets/fonts/BarlowCondensed-SemiBold.ttf') format('truetype'); font-weight:600; font-display:swap; }
@font-face { font-family:"Barlow Condensed"; src:url('/assets/fonts/BarlowCondensed-ExtraBold.ttf') format('truetype'); font-weight:800; font-display:swap; }
@font-face { font-family:"IBM Plex Sans"; src:url('/assets/fonts/IBMPlexSans-Variable.ttf') format('truetype'); font-weight:100 700; font-stretch:75% 100%; font-display:swap; }
@font-face { font-family:"IBM Plex Mono"; src:url('/assets/fonts/IBMPlexMono-Regular.ttf') format('truetype'); font-weight:400; font-display:swap; }
@font-face { font-family:"IBM Plex Mono"; src:url('/assets/fonts/IBMPlexMono-SemiBold.ttf') format('truetype'); font-weight:600; font-display:swap; }
"""

SULFUR_CSS = """
:root { color-scheme:light; --paper:#C3C5BA; --paper-deep:#B3B5A9; --ink:#11120F;
  --text-soft:#4D5048; --rule:#898D81; --sulfur:#CBD63F; --guide-surface:#20251B;
  --guide-ink:#ECEFDF; --font-display:"Barlow Condensed","Arial Narrow",sans-serif;
  --font-body:"IBM Plex Sans",Arial,sans-serif; --font-mono:"IBM Plex Mono","SFMono-Regular",Consolas,monospace;
  --bg:var(--paper); --panel:var(--paper); --panel-2:var(--paper-deep); --border:var(--rule);
  --text:var(--ink); --text-dim:var(--text-soft); --accent:var(--ink); --pick:var(--sulfur); }
* { box-sizing:border-box; }
body { background-color:var(--paper); color:var(--ink); font:14px/1.5 var(--font-body);
  background-image:repeating-linear-gradient(0deg,rgba(17,18,15,.045) 0 1px,transparent 1px 8px),
    repeating-linear-gradient(90deg,rgba(255,255,255,.025) 0 1px,transparent 1px 13px),
    radial-gradient(circle at 18% 22%,rgba(255,255,255,.08),transparent 38%); }
h1,h2,h3 { font-family:var(--font-display); }
code,.mono,.receipt { font-family:var(--font-mono); }
:focus-visible { outline:3px solid var(--sulfur); outline-offset:3px; }
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { scroll-behavior:auto!important; transition:none!important; animation:none!important; } }
"""
```

`CONTROL_CSS` must define `.raised-control`, `.raised-readout`, `.mounted-evidence`, `.light-detent`, and `.recessed-readout` using the three approved strengths. Pressed controls translate by their shadow offset and remove the outer shadow.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_shared_ui.py`

Expected: PASS.

```bash
git add src/clawmarks/shared_ui.py tests/test_shared_ui.py
git commit -m "feat(ui): define Sulfur Proof foundation"
```

### Task 3: Replace The Shared Header And Context Picker

**Files:**
- Modify: `src/clawmarks/shared_ui.py:28-106,198-213`
- Modify: `src/clawmarks/curation_server.py:1385-1393`
- Test: `tests/test_shared_ui.py`
- Test: `tests/test_curation_server_expedition_routes.py`

**Interfaces:**
- Changes: `nav_bar_html(current, active_expedition=None, active_leg=None, running=None, focus=None) -> str`.
- Produces: `/shared-ui.js` from `SHARED_UI_JS`.
- `focus` shape: `None` or `{"focus_id": str, "label": str, "revision": int}`.

- [ ] **Step 1: Write failing semantic-header tests**

```python
def test_header_names_page_scope_focus_and_guide():
    markup = nav_bar_html(
        "map.html", "demo", "round1",
        focus={"focus_id": "focus_11111111111111111111111111111111", "label": "Ink anchor", "revision": 3},
    )
    assert "CLAWMARKS" in markup
    assert "Solution map" in markup
    assert "demo/round1" in markup
    assert "Ink anchor" in markup and "r3" in markup
    assert 'id="contextPicker"' in markup
    assert 'id="guideOpen"' in markup
    assert '<dialog' in markup


def test_narrow_header_keeps_context_and_guide_labels():
    assert "@media (max-width:700px)" in shared_ui.TOPNAV_CSS
    assert ".context-label" in shared_ui.TOPNAV_CSS
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_shared_ui.py tests/test_curation_server_expedition_routes.py`

Expected: FAIL against the old link/select header.

- [ ] **Step 3: Implement semantic header markup**

Use one `<header class="topnav">` containing wordmark, page name, context button, optional Focus link, running state, Guide button, and tool `<select>`. The context button opens a native `<dialog id="contextDialog">`; the dialog fetches `/api/expeditions`, renders expedition/leg buttons, POSTs `/api/active-leg`, then reloads the current pathname without stale Focus parameters. Include a `session status` link to `/status.html`.

Define `NAV_GROUPS` with a leading `Explore` group containing `/`, `/status.html`, and the five-stage destinations. Keep `NAV_OPTIONS` derived from those groups so tests cannot drift.

- [ ] **Step 4: Serve `SHARED_UI_JS` and run tests**

Run: `uv run pytest -q tests/test_shared_ui.py tests/test_curation_server_expedition_routes.py tests/test_curation_server_static_assets.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clawmarks/shared_ui.py src/clawmarks/curation_server.py tests/test_shared_ui.py tests/test_curation_server_expedition_routes.py tests/test_curation_server_static_assets.py
git commit -m "feat(ui): add shared research context header"
```

### Task 4: Migrate Evidence And Curation Pages

**Files:**
- Modify: `src/clawmarks/build/map_view.py`
- Modify: `src/clawmarks/build/coverage_map.py`
- Modify: `src/clawmarks/build/redundancy_view.py`
- Modify: `src/clawmarks/build/novelty_decay.py`
- Modify: `src/clawmarks/build/lineage_view.py`
- Modify: `src/clawmarks/build/scan_gallery.py`
- Modify: `src/clawmarks/build/elite_archive.py`
- Modify: `src/clawmarks/build/compare_page.py`
- Modify: `src/clawmarks/build/preference_status.py`
- Modify: `src/clawmarks/build/preference_rank.py`
- Test: `tests/test_map_view.py`
- Test: `tests/test_coverage_map.py`
- Test: `tests/test_redundancy_view.py`
- Test: `tests/test_novelty_decay.py`
- Test: `tests/test_lineage_view.py`
- Test: `tests/test_scan_gallery.py`
- Test: `tests/test_elite_archive.py`
- Test: `tests/test_compare_page.py`
- Test: `tests/test_preference_status.py`
- Test: `tests/test_preference_rank_live.py`

**Interfaces:**
- Consumes: `SULFUR_FONT_CSS`, `SULFUR_CSS`, `CONTROL_CSS`, `TOPNAV_CSS`, `MOBILE_BASE_CSS`, `nav_bar_html()`.
- Produces: unchanged page-specific JavaScript and API behavior under the new shell.

- [ ] **Step 1: Add failing render-contract assertions**

For each page test, assert the rendered page contains `--paper:#C3C5BA`, `shared-ui.js`, a `<header`, and no `prefers-color-scheme: dark`. Add page-specific assertions:

```python
assert "mounted-evidence" in archive_html
assert 'class="or-axis"' in compare_html
assert 'aria-label="Coverage frontier"' in coverage_html
assert 'aria-label="Solution map evidence list"' in map_html
```

- [ ] **Step 2: Run the page-render tests and verify failure**

Run: `uv run pytest -q tests/test_map_view.py tests/test_coverage_map.py tests/test_redundancy_view.py tests/test_novelty_decay.py tests/test_lineage_view.py tests/test_scan_gallery.py tests/test_elite_archive.py tests/test_compare_page.py tests/test_preference_status.py tests/test_preference_rank_live.py`

Expected: FAIL because pages still emit dark local roots and rounded cards.

- [ ] **Step 3: Migrate page foundations without changing data behavior**

Import the shared Sulfur constants in every file, place them after any remaining local CSS so they win, then remove each local `:root` and dark-mode override. Apply these exact structural rules:

- Map: dark reversed canvas, flat interpretation column, accessible evidence list.
- Coverage: hatched frontier buttons with visible `F`, ruled explanation rows, accessible table.
- Compare: two dominant mounted images and one text `OR` axis.
- Scan and Archive: mounted evidence grids, square corners, full-image access preserved.
- Redundancy, Novelty Decay, and Lineage: ruled evidence rows, no statistic-card grid.
- Preference pages: one thin readiness row and ruled model evidence.

Keep existing IDs, data attributes, endpoint names, and event handlers unchanged.

- [ ] **Step 4: Run page tests and commit**

Run: `uv run pytest -q tests/test_map_view.py tests/test_coverage_map.py tests/test_redundancy_view.py tests/test_novelty_decay.py tests/test_lineage_view.py tests/test_scan_gallery.py tests/test_elite_archive.py tests/test_compare_page.py tests/test_preference_status.py tests/test_preference_rank_live.py`

Expected: PASS.

```bash
git add src/clawmarks/build/map_view.py src/clawmarks/build/coverage_map.py src/clawmarks/build/redundancy_view.py src/clawmarks/build/novelty_decay.py src/clawmarks/build/lineage_view.py src/clawmarks/build/scan_gallery.py src/clawmarks/build/elite_archive.py src/clawmarks/build/compare_page.py src/clawmarks/build/preference_status.py src/clawmarks/build/preference_rank.py tests/test_map_view.py tests/test_coverage_map.py tests/test_redundancy_view.py tests/test_novelty_decay.py tests/test_lineage_view.py tests/test_scan_gallery.py tests/test_elite_archive.py tests/test_compare_page.py tests/test_preference_status.py tests/test_preference_rank_live.py
git commit -m "feat(ui): migrate evidence pages to Sulfur Proof"
```

### Task 5: Migrate Action, Status, Error, And Empty Surfaces

**Files:**
- Modify: `src/clawmarks/build/cockpit.py`
- Modify: `src/clawmarks/build/runs_page.py`
- Modify: `src/clawmarks/build/seed_browser.py`
- Modify: `src/clawmarks/build/explore_hub.py`
- Modify: `src/clawmarks/curation_server.py:1021-1315`
- Test: `tests/test_curation_server_expedition_routes.py`
- Test: `tests/test_curation_server_error_page.py`
- Test: `tests/test_curation_server_startup.py`
- Test: `tests/test_curation_server_cockpit_scoring.py`
- Test: `tests/test_runs_page.py`
- Test: `tests/test_seed_browser.py`
- Test: `tests/test_explore_hub.py`

**Interfaces:**
- Consumes: shared shell constants and header.
- Preserves: all existing generation, launch, stop, status, and error behavior.

- [ ] **Step 1: Write failing shell and accessibility assertions**

```python
assert "--paper:#C3C5BA" in cockpit.render_html()
assert "prefers-color-scheme: dark" not in cockpit.render_html()
assert 'role="alert"' in integrity_error_html
assert 'href="/status.html"' in empty_state_html
assert "min-height:44px" in shared_ui.MOBILE_BASE_CSS
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run pytest -q tests/test_curation_server_expedition_routes.py tests/test_curation_server_error_page.py tests/test_curation_server_startup.py tests/test_curation_server_cockpit_scoring.py tests/test_runs_page.py tests/test_seed_browser.py tests/test_explore_hub.py`

Expected: FAIL against the remaining local themes.

- [ ] **Step 3: Apply the shared shell**

Cockpit becomes one ruled recipe with a recessed settings area and one full-width mounted payload-review strip. Runs leads with outcome and inline statistics. Status and error pages retain their exact diagnostics but use the shared header and paper system. Explore receives only the shell here; the active-desk composition belongs to the navigation plan.

- [ ] **Step 4: Run focused and full tests**

Run: `uv run pytest -q tests/test_curation_server_expedition_routes.py tests/test_curation_server_error_page.py tests/test_curation_server_startup.py tests/test_curation_server_cockpit_scoring.py tests/test_runs_page.py tests/test_seed_browser.py tests/test_explore_hub.py`, then `uv run pytest -q`.

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clawmarks/build/cockpit.py src/clawmarks/build/runs_page.py src/clawmarks/build/seed_browser.py src/clawmarks/build/explore_hub.py src/clawmarks/curation_server.py tests/test_curation_server_expedition_routes.py tests/test_curation_server_error_page.py tests/test_curation_server_startup.py tests/test_curation_server_cockpit_scoring.py tests/test_runs_page.py tests/test_seed_browser.py tests/test_explore_hub.py
git commit -m "feat(ui): complete Sulfur Proof page migration"
```

### Task 6: Verify The Live Visual Contract

**Files:**
- Verify only; this task has no planned file edits. A failure returns to the owning task, which adds a focused regression test before editing its listed source file.

**Interfaces:**
- Verifies: desktop, 390px mobile, 200% zoom, keyboard navigation, and reduced motion.

- [ ] **Step 1: Start the server against disposable fixture state**

Create a temporary state tree through test fixtures or a copied non-production sample. Do not point this check at irreplaceable RunPod output. Set `CLAWMARKS_STATE_DIR` to that temporary tree and start the default port with `uv run clawmarks serve`; the CLI rejects a positional port.

- [ ] **Step 2: Exercise every advertised route with Playwright MCP**

Inspect Explore, Map, Coverage, Compare, Cockpit, Runs, one empty state, and one integrity error at 1440px desktop and 390px mobile. Open the context dialog, switch a disposable leg, close it with Escape, tab through the header, open image detail, and verify visible focus restoration.

- [ ] **Step 3: Check objective browser signals**

Confirm `document.documentElement.scrollWidth === document.documentElement.clientWidth` except inside intentional map/grid/stepper scrollers. Check console errors, external font requests, computed body font, 44px mobile targets, and `prefers-reduced-motion` behavior.

- [ ] **Step 4: Run final verification**

Run: `uv run pytest -q && uv run ruff check src tests && uv run mypy src && git diff --check`

Expected: PASS with no diff whitespace errors.

## Execution Order

Execute this plan before the navigation and Guide plans. Later plans extend `nav_bar_html()` and the shared browser assets but must preserve these tokens, static routes, and responsive contracts.
