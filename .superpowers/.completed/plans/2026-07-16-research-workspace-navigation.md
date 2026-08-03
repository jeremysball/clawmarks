# Research Workspace Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Explore the active research desk, preserve explicit Focus scope across every tool, and connect Solution Map and Coverage selections to Cockpit without mutating global selection on read.

**Architecture:** Resolve an immutable `WorkspaceContext` from each page URL. Refactor live-cache and manifest helpers to accept explicit expedition/leg values, then pass one Focus summary through every page renderer and shared link. Explore derives its evidence wall, activity, workflow stage, and next decision from persisted records rather than browser-global state.

**Tech Stack:** Python 3.10+, server-rendered HTML/CSS/JavaScript, Canvas 2D, pytest, Playwright MCP.

## Global Constraints

- Focus-capable URLs use exactly `expedition`, `leg`, and `focus_id`.
- A partial Focus query is invalid. A bare tool URL remains leg-wide with no active Focus.
- Reading a page never writes `active_leg.json` or creates a leg.
- Saved member tags and score ranges are authoritative. Canvas coordinates and grid coordinates are hints.
- Missing Focus evidence stays visibly missing; the server never substitutes current nearest neighbors.
- The workflow stage is derived from records. Clicking another stage only changes its explanation.
- Keep the active scope, Focus, and Guide trigger understandable at 390px.
- Run Python and tests through `uv run` only.

## Dependencies

- Complete `2026-07-16-sulfur-proof-shared-shell.md` first.
- Complete `2026-07-16-focus-persistence.md` first.
- The paid-trial plan later supplies trial, launch, result, and evaluation rows to Explore's existing aggregation interface.

## File Structure

- Create `src/clawmarks/workspace_context.py`: URL parsing, scoped URLs, and immutable page context.
- Modify `src/clawmarks/curation_server.py`: explicit-scope data helpers and root/status/page routing.
- Replace `src/clawmarks/build/explore_hub.py`: active-desk renderer and derived readiness.
- Modify `src/clawmarks/build/map_view.py`: lasso, accessible selection list, and Focus creation.
- Modify `src/clawmarks/build/coverage_map.py`: exact frontier ranges, accessible table, and Focus creation.
- Modify every Focus-capable `src/clawmarks/build/*.py`: preserve query context in links and header.
- Modify route and render tests; create dedicated workspace-context and navigation tests.

### Task 1: Resolve Explicit Workspace Context

**Files:**
- Create: `src/clawmarks/workspace_context.py`
- Create: `tests/test_workspace_context.py`

**Interfaces:**
- Produces: `WorkspaceContext(expedition: str | None, leg: str | None, focus: dict | None)` frozen dataclass.
- Produces: `resolve_workspace_context(raw_url: str, active_selection: dict, focus_store: FocusStore) -> WorkspaceContext`.
- Produces: `context_url(path: str, context: WorkspaceContext, include_focus: bool = True) -> str`.
- Produces: `ContextQueryError` for partial or mismatched explicit scope.

- [ ] **Step 1: Write failing context tests**

```python
def test_bare_url_uses_browsing_scope_without_focus(store):
    context = resolve_workspace_context(
        "/map.html", {"expedition": "demo", "leg": "round1"}, store
    )
    assert context.expedition == "demo"
    assert context.leg == "round1"
    assert context.focus is None


def test_explicit_focus_scope_wins_without_mutating_active_selection(store, saved_focus):
    active = {"expedition": "other", "leg": "current"}
    context = resolve_workspace_context(
        f"/map.html?expedition=demo&leg=round1&focus_id={saved_focus['focus_id']}",
        active,
        store,
    )
    assert context.focus == saved_focus
    assert active == {"expedition": "other", "leg": "current"}


def test_partial_focus_query_is_rejected(store):
    with pytest.raises(ContextQueryError, match="all three"):
        resolve_workspace_context(
            "/map.html?focus_id=focus_11111111111111111111111111111111", {}, store
        )
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_workspace_context.py`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement parsing and URL construction**

Use `urllib.parse.urlparse`, `parse_qs`, and `urlencode`. Reject repeated values for any context key. An explicit `expedition` and `leg` without `focus_id` is a valid scoped leg-wide URL. If `focus_id` appears, require all three and load through `FocusStore.get(Scope(expedition, leg), focus_id)`.

`context_url()` preserves unrelated query parameters only when passed explicitly by its caller; it never copies an arbitrary source URL. It emits absolute-path links such as:

```text
/redundancy.html?expedition=demo&leg=round1&focus_id=focus_abcd
```

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_workspace_context.py`

Expected: PASS.

```bash
git add src/clawmarks/workspace_context.py tests/test_workspace_context.py
git commit -m "feat(workspace): resolve explicit Focus context"
```

### Task 2: Make Live Data Helpers Scope-Explicit

**Files:**
- Modify: `src/clawmarks/curation_server.py:142-390,1317-1615`
- Modify: `tests/test_curation_server_manifest_cache.py`
- Modify: `tests/test_curation_server_manifest_only_routes_cache.py`
- Create: `tests/test_curation_server_workspace_scope.py`

**Interfaces:**
- Changes: `_manifest_path(expedition, leg) -> Path`.
- Changes: `_get_scan_items(expedition, leg)`, `_get_solution_map_data(expedition, leg)`, `_get_map_data(expedition, leg)`, `_get_redundancy_data(expedition, leg)`, and `_get_manifest_cached(target_name, compute_fn, expedition, leg)`.
- Cache keys include `expedition` and `leg` so two tabs cannot share computed data accidentally.
- Produces: `GET /generated/<tag>?expedition=<name>&leg=<name>` and scoped `/thumbs/<tag>.jpg` resolution.
- Produces: `generated_image_url(tag, context, thumbnail=False) -> str` in `workspace_context.py`.

- [ ] **Step 1: Write a failing two-scope route test**

```python
def test_explicit_focus_page_reads_its_leg_without_switching_global_selection(server, focus):
    cs._active_selection.update(expedition="other", leg="current")
    before = config.ACTIVE_LEG_FILE.read_bytes()
    url = (
        f"/map.html?expedition=demo&leg=round1&focus_id={focus['focus_id']}"
    )
    status, body = get_html(server, url)
    assert status == 200
    assert "demo/round1" in body
    assert config.ACTIVE_LEG_FILE.read_bytes() == before
    assert cs._active_selection == {"expedition": "other", "leg": "current"}
```

Add a cache test with different manifests under two legs and assert each page contains only its own tags.
Add image-route tests proving an explicit Focus tab serves the requested leg's full image and
thumbnail even while the global active leg points elsewhere, and rejects a manifest path outside
that leg.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_curation_server_workspace_scope.py tests/test_curation_server_manifest_cache.py tests/test_curation_server_manifest_only_routes_cache.py`

Expected: FAIL because helpers use `_active_out_dir()`.

- [ ] **Step 3: Thread explicit scope through read helpers**

Resolve `WorkspaceContext` once at the top of each page route. Derive `out_dir = config.leg_dir(context.expedition, context.leg)` and pass it through cache calls. Use cache keys such as `f"map:{expedition}:{leg}"`. Do not assign to `_active_selection` in a GET handler.

Serve Focus-scoped generated images by resolving the tag exactly once in that scope's manifest,
requiring the resolved file beneath its leg directory, and streaming that file directly. Parse the
query before matching `/thumbs/`; generate and serve the thumbnail beneath the same explicit leg.
Use these routes in new Focus-aware pages instead of `SimpleHTTPRequestHandler`'s connection-time
active directory.

Keep mutating legacy APIs on their existing active-leg contract in this task. Later tasks add explicit scope where Focus-aware actions need it.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_curation_server_workspace_scope.py tests/test_curation_server_manifest_cache.py tests/test_curation_server_manifest_only_routes_cache.py`

Expected: PASS.

```bash
git add src/clawmarks/curation_server.py tests/test_curation_server_workspace_scope.py tests/test_curation_server_manifest_cache.py tests/test_curation_server_manifest_only_routes_cache.py
git commit -m "refactor(server): scope page data by URL context"
```

### Task 3: Split Explore Root From Session Status

**Files:**
- Modify: `src/clawmarks/curation_server.py:1021-1315,1373-1375,1508-1515`
- Modify: `src/clawmarks/build/explore_hub.py`
- Modify: `tests/test_explore_hub.py`
- Modify: `tests/test_curation_server_startup.py`
- Modify: `tests/test_curation_server_expedition_routes.py`

**Interfaces:**
- Produces: `GET /` and `GET /explore.html` as the same Explore renderer.
- Produces: `GET /status.html` as the existing status/picker renderer.
- Produces: `build_explore_data(context, foci, trials=(), guide_threads=(), launches=()) -> dict`.
- Produces: `derive_next_decision(focus, trials=()) -> {"stage": str, "label": str, "href": str}`.

- [ ] **Step 1: Write failing route and readiness tests**

```python
def test_root_and_explore_are_active_desk_while_status_keeps_picker(running_server):
    root = get_text(running_server, "/")
    explore = get_text(running_server, "/explore.html")
    status = get_text(running_server, "/status.html")
    assert 'id="workflowStepper"' in root
    assert 'id="workflowStepper"' in explore
    assert 'id="active-leg-form"' in status
    assert 'id="active-leg-form"' not in root


def test_next_decision_prefers_incomplete_contract_before_trials():
    decision = explore_hub.derive_next_decision(
        {"focus_id": "focus_11111111111111111111111111111111", "test_contract": None},
        trials=[],
    )
    assert decision["stage"] == "Explain"
    assert decision["label"] == "Edit Focus"
```

Add cases for no Focus, ready without a trial, active trial, unevaluated terminal trial, and evaluated trial.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_explore_hub.py tests/test_curation_server_startup.py tests/test_curation_server_expedition_routes.py`

Expected: FAIL because `/` still serves status and Explore is a card hub.

- [ ] **Step 3: Implement data derivation**

`build_explore_data()` must:

- list open Foci without selecting one when no `focus_id` exists;
- expose Saved Observations from the same Focus records;
- choose up to four stored generated members and then the first real anchor, filling with a fifth generated member only when no anchor exists;
- retain missing evidence as `{tag, role, missing: true}`;
- merge Focus timestamps and optional Guide/trial/launch records by `(timestamp, record_id)`;
- return the exact readiness facts used by `derive_next_decision()`.

- [ ] **Step 4: Render the approved active desk**

Replace tool cards with the connected five-button stepper, Focus/Saved Observations tabs, shallow question readout, mounted evidence wall, light activity detents, raised Next Decision plate, and a compact ruled full-tool index. Use native buttons and `aria-current="step"`; update one `aria-live="polite"` explanation region.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_explore_hub.py tests/test_curation_server_startup.py tests/test_curation_server_expedition_routes.py`

Expected: PASS.

```bash
git add src/clawmarks/curation_server.py src/clawmarks/build/explore_hub.py tests/test_explore_hub.py tests/test_curation_server_startup.py tests/test_curation_server_expedition_routes.py
git commit -m "feat(explore): make the research desk the root"
```

### Task 4: Create Map-Member Foci From A Lasso

**Files:**
- Modify: `src/clawmarks/build/map_view.py`
- Modify: `src/clawmarks/build/solution_map.py`
- Modify: `tests/test_map_view.py`
- Modify: `tests/test_solution_map.py`
- Create: `tests/test_map_focus_ui.py`

**Interfaces:**
- Produces browser function: `selectedTagsFromPolygon(points, polygon) -> string[]`.
- Produces browser function: `createMapFocus()` posting to `/api/foci`.
- Consumes: renderer arguments `context=None` and `focus=None`.
- Produces: `projection_version` as `sha256_json({"points": points, "real_points": real_points})`.

- [ ] **Step 1: Write failing render-contract tests**

```python
def test_map_renders_lasso_label_accessible_list_and_create_action(map_data):
    page = map_view.render_html(map_data, active_expedition="demo", active_leg="round1")
    assert 'id="selectionLabel"' in page
    assert "SELECTED REGION" in page
    assert 'aria-label="Solution map evidence list"' in page
    assert 'id="createMapFocus"' in page
    assert "selectedTagsFromPolygon" in page
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_map_view.py tests/test_map_focus_ui.py`

Expected: FAIL because the map only supports point clicks.

- [ ] **Step 3: Implement pointer and keyboard selection**

On `pointerdown`, capture the pointer and start a polygon. Add points on `pointermove` only after total movement reaches 6px. On `pointerup`, keep the old point inspection for shorter movement; otherwise close the polygon and use ray casting against generated points. Normalize stored polygon coordinates to `[0,1]` by canvas width and height.

Render a synchronized checkbox list of selected generated points. Checkbox changes update the same `Set` used by the canvas. The create button stays disabled while the set is empty.

- [ ] **Step 4: Post the authoritative source shape**

```javascript
const payload = {
  scope: {expedition: CONTEXT.expedition, leg: CONTEXT.leg},
  label: document.getElementById('focusLabel').value,
  source: {
    view: 'map', kind: 'map_members',
    member_tags: Array.from(selectedTags),
    real_anchor_tags: selectedRealAnchor ? [selectedRealAnchor] : [],
    projection_hint: {projection_version: DATA.projection_version, polygon: normalizedPolygon},
  },
  question: document.getElementById('focusQuestion').value,
  observation: '', hypothesis_text: '', test_contract: null,
};
```

After HTTP 201, navigate through `context_url('/explore.html', created_context)`.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_map_view.py tests/test_map_focus_ui.py tests/test_curation_server_focus_routes.py`

Expected: PASS.

```bash
git add src/clawmarks/build/map_view.py src/clawmarks/build/solution_map.py tests/test_map_view.py tests/test_solution_map.py tests/test_map_focus_ui.py
git commit -m "feat(map): create Focus dossiers from lasso selections"
```

### Task 5: Create Frontier Foci From Coverage

**Files:**
- Modify: `src/clawmarks/build/coverage_map.py`
- Modify: `tests/test_coverage_map.py`
- Create: `tests/test_coverage_focus_ui.py`

**Interfaces:**
- Changes: Coverage cells always contain finite `faith_lo`, `faith_hi`, `novelty_lo`, and `novelty_hi` using domains `[-1,1]` and `[0,2]` at outer edges.
- Changes: repeated quantile edges produce non-actionable cells; only finite, strictly increasing ranges may set `frontier: true`.
- Produces: native frontier buttons, equivalent table rows, and `createCoverageFocus()`.
- Produces: `binning_version = sha256_json({"cells": canonical_cell_ranges, "domains": metric_domains})` in computed data.

- [ ] **Step 1: Write failing domain and UI tests**

```python
def test_outer_bins_use_declared_metric_domains(tmp_path):
    (tmp_path / "scored_manifest.json").write_text(json.dumps([
        {"tag": "a", "centroid_sim": 0.2, "novelty": 0.7,
         "prompt_name": "p", "file": str(tmp_path / "a.png")}
    ]))
    data = coverage_map.compute_data(str(tmp_path))
    assert min(c["faith_lo"] for c in data["cells"]) == -1.0
    assert max(c["faith_hi"] for c in data["cells"]) == 1.0
    assert min(c["novelty_lo"] for c in data["cells"]) == 0.0
    assert max(c["novelty_hi"] for c in data["cells"]) == 2.0


def test_frontier_is_labeled_and_has_accessible_equivalent(data):
    page = coverage_map.render_html(data, active_expedition="demo", active_leg="round1")
    assert 'aria-label="Coverage frontier"' in page
    assert 'aria-label="Coverage values"' in page
    assert "Create Focus" in page
    assert "promising" not in page.lower()


def test_repeated_quantile_edges_never_expose_zero_width_frontier(tmp_path):
    write_manifest(tmp_path, [record("a", faith=0.2, novelty=0.7)])
    data = coverage_map.compute_data(str(tmp_path))
    assert not [cell for cell in data["cells"] if cell["frontier"]]


def test_every_frontier_has_finite_strict_ranges(nondegenerate_coverage_data):
    frontiers = [cell for cell in nondegenerate_coverage_data["cells"] if cell["frontier"]]
    assert frontiers
    for cell in frontiers:
        assert math.isfinite(cell["faith_lo"])
        assert math.isfinite(cell["faith_hi"])
        assert math.isfinite(cell["novelty_lo"])
        assert math.isfinite(cell["novelty_hi"])
        assert cell["faith_lo"] < cell["faith_hi"]
        assert cell["novelty_lo"] < cell["novelty_hi"]
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_coverage_map.py tests/test_coverage_focus_ui.py`

Expected: FAIL because outer bounds are null/display defaults and cells are divs.

- [ ] **Step 3: Implement exact ranges and native controls**

Set each cell's lower/upper range from bin edges with explicit domain endpoints. Calculate
`actionable = all_finite and faith_lo < faith_hi and novelty_lo < novelty_hi`, and include a cell in
the frontier set only when it is actionable. Render a native `<button>` for every actionable
frontier, with visible `F`, sulfur hatching, exact ranges, and adjacent count. Render zero-width cells
as inert density cells without Create Focus. Mirror the grid as a screen-reader table. Selecting
either actionable surface updates the same detail panel.

- [ ] **Step 4: Post a `coverage_frontier` source**

The POST body must include exact score ranges, all adjacent generated tags from `neighbor_tags()`, selected real anchor tags, and a `coverage_hint` with row, column, domains, and a digest of canonical cell definitions. Add an HTTP round-trip test with a sparse but nondegenerate manifest: choose one rendered actionable frontier, POST its exact payload to `/api/foci`, and assert HTTP 201. The one-record repeated-edge fixture must render no actionable frontier. On success, navigate to explicit Explore context.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_coverage_map.py tests/test_coverage_focus_ui.py tests/test_curation_server_focus_routes.py`

Expected: PASS.

```bash
git add src/clawmarks/build/coverage_map.py tests/test_coverage_map.py tests/test_coverage_focus_ui.py
git commit -m "feat(coverage): create Focus dossiers from frontiers"
```

### Task 6: Preserve Focus Across Every Tool And Fix Cockpit GET

**Files:**
- Modify: all `src/clawmarks/build/*.py` files that call `nav_bar_html()`.
- Modify: `src/clawmarks/build/cockpit.py`
- Modify: `src/clawmarks/curation_server.py:1395-1567`
- Modify: `tests/test_shared_ui.py`
- Modify: `tests/test_curation_server_cockpit_scoring.py`
- Create: `tests/test_focus_navigation.py`

**Interfaces:**
- Every renderer accepts `focus=None` and passes it to `nav_bar_html()`.
- Every workflow, evidence, Guide, and return link uses `context_url()`.
- Focus-scoped Cockpit consumes the source expedition/leg and never calls `_set_active_selection()`.
- Scan data, favorites, comparison, preference-flag, full-image, and thumbnail requests carry explicit scope when a Focus is active.

- [ ] **Step 1: Write failing link and side-effect tests**

```python
def test_all_focus_tool_links_preserve_complete_context(rendered_pages, focus):
    suffix = f"expedition=demo&amp;leg=round1&amp;focus_id={focus['focus_id']}"
    for page in rendered_pages:
        assert suffix in page


def test_focus_scoped_cockpit_get_does_not_write_active_leg(server, focus):
    before = config.ACTIVE_LEG_FILE.read_bytes()
    get_text(
        server,
        f"/cockpit.html?expedition=demo&leg=round1&focus_id={focus['focus_id']}",
    )
    assert config.ACTIVE_LEG_FILE.read_bytes() == before
    assert cs._active_selection["leg"] != "cockpit"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_focus_navigation.py tests/test_curation_server_cockpit_scoring.py tests/test_shared_ui.py`

Expected: FAIL because links are bare and Cockpit changes the global leg.

- [ ] **Step 3: Thread context through renderers**

Add `focus=None` at the end of renderer signatures to preserve current positional callers. Generate links through one escaped helper; do not concatenate query strings in each page. Mark Focus members and trial-result placeholders by text/pattern in Scan, Archive, Compare, Redundancy, Novelty Decay, Lineage, Coverage, and Map.

Update `_LIGHTBOX_JS` to read the three context query keys, add expedition/leg to
`/scan_data.json`, `/api/favorites`, `/api/favorite`, and `/api/unfavorite`, and use the scoped
generated-image URLs. Update Compare's next-pair GET and comparison POST, plus preference flags, to
carry explicit expedition/leg. Server handlers validate the named scope and write that leg directly;
they do not require it to equal `_active_selection`.

Delete Cockpit's GET-time `_set_active_selection(..., "cockpit")` block and expedition-switch script. Bare Cockpit uses the browsing scope; Focus Cockpit uses explicit source scope. Keep standalone generation available and label it “No Focus provenance.”

- [ ] **Step 4: Run focused and full tests**

Run: `uv run pytest -q tests/test_focus_navigation.py tests/test_curation_server_cockpit_scoring.py tests/test_shared_ui.py && uv run pytest -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clawmarks/shared_ui.py src/clawmarks/curation_server.py src/clawmarks/build/lineage_view.py src/clawmarks/build/redundancy_view.py src/clawmarks/build/novelty_decay.py src/clawmarks/build/runs_page.py src/clawmarks/build/map_view.py src/clawmarks/build/compare_page.py src/clawmarks/build/preference_rank.py src/clawmarks/build/seed_browser.py src/clawmarks/build/cockpit.py src/clawmarks/build/elite_archive.py src/clawmarks/build/coverage_map.py src/clawmarks/build/scan_gallery.py src/clawmarks/build/preference_status.py tests/test_focus_navigation.py tests/test_curation_server_cockpit_scoring.py tests/test_shared_ui.py
git commit -m "feat(workspace): preserve Focus across research tools"
```

### Task 7: Verify Desktop And Mobile Research Flow

**Files:**
- Modify: `src/clawmarks/workspace_context.py`
- Modify: `src/clawmarks/curation_server.py`
- Modify: `src/clawmarks/build/explore_hub.py`
- Modify: `src/clawmarks/build/map_view.py`
- Modify: `src/clawmarks/build/coverage_map.py`
- Test: `tests/test_workspace_context.py`
- Test: `tests/test_curation_server_workspace_scope.py`
- Test: `tests/test_explore_hub.py`
- Test: `tests/test_map_focus_ui.py`
- Test: `tests/test_coverage_focus_ui.py`

**Interfaces:**
- Verifies: Create Focus from Map and Coverage, cross-tool links, workflow controls, status route, and Cockpit read-only behavior.

- [ ] **Step 1: Start disposable live state**

Use a temporary `CLAWMARKS_STATE_DIR` populated with small generated and real-image fixtures. Never run this check against billed production output.

- [ ] **Step 2: Exercise the complete flow with Playwright MCP**

At desktop and 390px: open `/`, switch to `/status.html`, select a disposable leg, create a map lasso Focus, inspect it in Redundancy, return to Explore, open Cockpit, and verify `active_leg.json` is byte-identical. Repeat Focus creation from a Coverage frontier. Exercise the keyboard checkbox alternatives without pointer input.

- [ ] **Step 3: Check browser errors and accessibility**

Verify no console errors, no page-level overflow, visible horizontal-stepper continuation cue, `aria-current`, live explanation updates, labeled selection/frontier, and Focus context in every header.

- [ ] **Step 4: Run final verification and commit fixes**

Run: `uv run pytest -q && uv run ruff check src tests && uv run mypy src && git diff --check`

Expected: PASS.

```bash
git add src/clawmarks/workspace_context.py src/clawmarks/curation_server.py src/clawmarks/build/explore_hub.py src/clawmarks/build/map_view.py src/clawmarks/build/coverage_map.py tests/test_workspace_context.py tests/test_curation_server_workspace_scope.py tests/test_explore_hub.py tests/test_map_focus_ui.py tests/test_coverage_focus_ui.py
git commit -m "fix(workspace): close navigation verification gaps"
```
