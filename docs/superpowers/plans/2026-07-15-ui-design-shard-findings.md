# Curation-Server Design-Shard Findings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every finding from the 2026-07-15 ten-shard UX review of the curation server
(`docs/superpowers/plans/design-shards/*.md`) with small, local, mechanical fixes — no framework
migration or redesign, matching every shard's own conclusion.

**Architecture:** The server is a stdlib `http.server` app: `curation_server.py` routes requests
to per-page `render_html()` functions under `src/clawmarks/build/*.py`, all sharing chrome
(nav bar, lightbox, tooltips) from `src/clawmarks/shared_ui.py`. Every fix here edits one of
these existing files in place; no new architecture, no new dependency.

**Tech Stack:** Python 3 stdlib `http.server`, hand-written HTML/CSS/JS strings (no template
engine, no frontend framework), pytest for tests, Playwright MCP for live UI verification.

## Global Constraints

- No framework migration, no template engine, no rewrite — every shard explicitly ruled this out
  and scoped its own fixes as local edits to one or two files.
- Every state-changing/paid/destructive action must show its destination (`expedition/leg`) and,
  for paid or irreversible actions, a restated payload before it fires — this is the project's
  standing data-integrity rule (`CLAUDE.md`).
- Never delete a file to invalidate a cache or "clean" a manifest; quarantine and report instead
  (`CLAUDE.md`).
- Run `env -u RUNPOD_API_KEY -u CIVITAI_TOKEN uv run pytest -q` before calling any phase done —
  this is what CI actually runs.
- Any UI-visible change gets a live Playwright check against a restarted `curation_server.py`
  before being called done — a passing test suite does not verify a page renders correctly.
- Apply the `writing-clearly-and-concisely` style to all new user-facing copy: active voice, no
  em dashes, no throat-clearing.

---

## Before starting: working-tree note

`git status` currently shows uncommitted changes already in `curation_server.py` and
`search/run_manager.py` (an in-progress "create expedition/leg" UI and a zombie-process reap
fix) plus a dirty `.gitignore` and lab-notebook edit. None of that overlaps this plan's tasks —
it touches the empty-state picker panel and `run_manager.current_run()`, neither of which any
task below rewrites wholesale — but every task's diff should be checked against `git diff` before
committing to make sure it doesn't collide with those lines. Commit or stash that unrelated work
first if it would otherwise get swept into this plan's commits.

## Task ordering and phases

Ordered by the cross-cutting synthesis from the shard review: structural gaps that make the tool
misleading or unsafe first (Phases 1-2), then correctness bugs with a real failure mode (Phase 3),
then legibility/consistency/scale work (Phases 4-8). Each phase is independently shippable and
independently revertable. Tasks within a phase touch disjoint files where possible so they can be
reordered or dropped without blocking siblings.

---

# Phase 1: Active expedition/leg is invisible (5 shards converged on this)

Every one of ia-navigation, cockpit-autopilot, expedition-launch-hub, data-integrity-affordances,
and solo-researcher-continuity independently found the same root defect: the server tracks and
persists the active expedition/leg and whether a search is running, but no page ever shows it, so
a returning researcher can act against the wrong target. This phase makes the active context and
running-search state visible everywhere.

### Task 1.1: Inject active expedition/leg into the shared nav bar

**Files:**
- Modify: `src/clawmarks/shared_ui.py:45-55` (`nav_bar_html`)
- Modify: every call site of `nav_bar_html(...)` across `src/clawmarks/build/*.py` and
  `src/clawmarks/curation_server.py` (grep for `nav_bar_html(` — currently one call per page,
  passing only the current route string)
- Test: `tests/test_shared_ui.py` (create if it doesn't exist)

**Interfaces:**
- Produces: `nav_bar_html(current, active_expedition=None, active_leg=None)` — every later task
  that touches a page's nav bar call site uses this signature.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_shared_ui.py
from clawmarks.shared_ui import nav_bar_html


def test_nav_bar_shows_active_leg():
    html = nav_bar_html("compare.html", active_expedition="uncanny_frontier", active_leg="round2")
    assert "uncanny_frontier" in html
    assert "round2" in html


def test_nav_bar_omits_label_when_no_selection():
    html = nav_bar_html("compare.html")
    assert "nav-activeleg" not in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_shared_ui.py -v`
Expected: FAIL — `nav_bar_html() got an unexpected keyword argument 'active_expedition'`

- [ ] **Step 3: Implement**

```python
# src/clawmarks/shared_ui.py, replace lines 45-55
def nav_bar_html(current, active_expedition=None, active_leg=None):
    opts = "".join(
        f'<option value="{href}"{" selected" if href == current else ""}>{label}</option>'
        for href, label in NAV_OPTIONS
    )
    active_label = ""
    if active_expedition and active_leg:
        active_label = (
            f'<span id="nav-activeleg" class="nav-activeleg" '
            f'title="active workspace">{active_expedition}/{active_leg}</span>'
        )
    return (
        '<div id="topnav" class="topnav" data-autohide>'
        '<a class="navlink" href="explore.html">&larr; all tools</a>'
        f'{active_label}'
        '<select onchange="if(this.value) location.href=this.value;">'
        f'<option value="">jump to...</option>{opts}</select></div>'
    )
```

Add to `TOPNAV_CSS` (same file, right after the existing block):

```css
.topnav .nav-activeleg { color:var(--text-dim,#9a9aa4); font-size:12px; font-family:monospace;
  padding:2px 8px; background:rgba(154,154,164,0.12); border-radius:5px; white-space:nowrap; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_shared_ui.py -v`
Expected: PASS

- [ ] **Step 5: Thread the active leg into every call site**

`curation_server.py` already tracks the active selection in a module global (loaded from
`ACTIVE_LEG_FILE` at startup — see `curation_server.py:130-137`). Find the accessor used
elsewhere in the file (it backs `/api/active-leg`) and use the same one here. Every
`render_html()` function in `src/clawmarks/build/*.py` that currently does
`nav_bar_html('some_page.html')` needs the active expedition/leg passed through as an argument to
`render_html()` itself, sourced from `curation_server.py`'s existing active-selection state at
the request handler. Concretely: each `render_html()` gains an `active_expedition=None,
active_leg=None` parameter (default `None` keeps every existing unit test that calls
`render_html()` directly working unchanged), and each call site in `curation_server.py` that
currently does `build.compare_page.render_html()` (etc.) becomes
`build.compare_page.render_html(active_expedition=exp, active_leg=leg)` using whatever the
handler already resolves via `_active_selection`/`_active_out_dir()`. Grep for `render_html()`
across `curation_server.py` to enumerate every call site — there are ~14, one per route.

- [ ] **Step 6: Run the full suite**

Run: `env -u RUNPOD_API_KEY -u CIVITAI_TOKEN uv run pytest -q`
Expected: PASS, no regressions

- [ ] **Step 7: Live-check with Playwright**

Restart `curation_server.py`, open any tool page, confirm the nav bar shows
`expedition/leg` next to the "all tools" link, and that it's absent (not a blank span) when no
leg is selected.

- [ ] **Step 8: Commit**

```bash
git add src/clawmarks/shared_ui.py src/clawmarks/build/*.py src/clawmarks/curation_server.py tests/test_shared_ui.py
git commit -m "feat(ui): show active expedition/leg in the shared nav bar"
```

### Task 1.2: Add a "running search" indicator alongside it

**Files:**
- Modify: `src/clawmarks/shared_ui.py` (`nav_bar_html`, extend from Task 1.1)
- Modify: `src/clawmarks/curation_server.py` (wherever `render_html()` call sites were updated in
  Task 1.1 — add a `run_manager.current_run()` check, already imported per `run_manager.py`)
- Test: extend `tests/test_shared_ui.py`

**Interfaces:**
- Consumes: `run_manager.current_run()` (existing; returns `None` or a dict with
  `expedition`/`leg`/`pid` — see `search/run_manager.py:70-90`).
- Produces: `nav_bar_html(current, active_expedition=None, active_leg=None, running=None)` where
  `running` is `None` or `(expedition, leg)`.

- [ ] **Step 1: Write the failing test**

```python
def test_nav_bar_shows_running_indicator():
    html = nav_bar_html("runs.html", running=("trent_v3_epoch4", "freeform1"))
    assert "RUNNING" in html
    assert "trent_v3_epoch4/freeform1" in html
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `uv run pytest tests/test_shared_ui.py -v`
Expected: FAIL — unexpected keyword `running`

- [ ] **Step 3: Implement**

```python
# nav_bar_html, extend the signature and body from Task 1.1
def nav_bar_html(current, active_expedition=None, active_leg=None, running=None):
    ...
    running_label = ""
    if running:
        r_exp, r_leg = running
        running_label = f'<span class="nav-running">RUNNING: {r_exp}/{r_leg}</span>'
    return (
        '<div id="topnav" class="topnav" data-autohide>'
        '<a class="navlink" href="explore.html">&larr; all tools</a>'
        f'{active_label}{running_label}'
        ...
    )
```

```css
.topnav .nav-running { color:#0b0b0d; font-size:11.5px; font-weight:700; padding:2px 8px;
  background:var(--up,#5ec98a); border-radius:5px; white-space:nowrap; letter-spacing:0.02em; }
```

- [ ] **Step 4: Run test to verify it passes.**
- [ ] **Step 5: Wire the call sites** from Task 1.1 to also pass
  `running=(_run["expedition"], _run["leg"]) if (_run := run_manager.current_run()) else None`.
- [ ] **Step 6: Run full suite, live-check, commit** (same pattern as Task 1.1, message:
  `feat(ui): surface an active search run in the nav bar`).

### Task 1.3: Fix the root page's three-branch status (not two)

The root page (`_send_status_page` / `_status_page_data_body` / `_status_page_empty_body` in
`curation_server.py:959-1067`, read in full above) currently branches only on `has_data`
(whether `scored_manifest.json` exists and is non-empty). A leg that is selected but has never
run shows literally the same "no expedition/leg selected" text as no selection at all
(ia-navigation problem 1, solo-researcher-continuity P1/P2, expedition-launch-hub problem 4).

**Files:**
- Modify: `src/clawmarks/curation_server.py:959-1067`
- Test: `tests/test_curation_server_expedition_routes.py` (existing file, already has coverage
  for expedition/leg routes per the file's current diff — add cases here)

**Interfaces:**
- Consumes: `_active_selection` (existing global/accessor), `_active_out_dir()` (existing),
  `run_manager.current_run()` (existing).
- Produces: `_send_status_page` renders one of three states, not two: **no selection**,
  **selected, no scored data yet**, **selected, has data**.

- [ ] **Step 1: Write the failing test**

```python
def test_status_page_shows_selected_leg_with_no_data(tmp_path, monkeypatch):
    # Set an active selection whose out_dir has no scored_manifest.json, then assert the
    # rendered page says the leg is selected (not "no expedition/leg selected").
    ...  # follow this file's existing fixture pattern for setting the active selection
    body = fetch_status_page()  # existing helper in this test file, or add one
    assert b"no expedition/leg selected" not in body.lower()
    assert b"uncanny_frontier" in body
    assert b"cockpit" in body
    assert b"no scored" in body.lower() or b"no search data" in body.lower()
```

Read `tests/test_curation_server_expedition_routes.py` in full first to match its existing
fixture/helper conventions (how it stands up a server instance, sets active selection, and reads
response bodies) rather than inventing a parallel pattern.

- [ ] **Step 2: Run test to verify it fails.**

Run: `uv run pytest tests/test_curation_server_expedition_routes.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the third branch**

```python
# curation_server.py, replace the body of _send_status_page (lines 959-977)
def _send_status_page(self):
    selection = _active_selection()  # existing accessor; returns None or {"expedition":..,"leg":..}
    if selection is None:
        body = self._status_page_no_selection_body()
    else:
        try:
            manifest = load_manifest()
            n_entries = len(manifest)
            n_present = sum(1 for m in manifest if os.path.exists(m["file"]))
            manifest_summary = f"{n_present}/{n_entries} manifest images present on disk"
            has_data = n_present > 0
        except FileNotFoundError:
            manifest_summary = f"{selection['expedition']}/{selection['leg']} has no scored manifest yet"
            has_data = False
        if has_data:
            body = self._status_page_data_body(manifest_summary)
        else:
            body = self._status_page_selected_empty_body(selection, manifest_summary)
    self.send_response(200)
    self.send_header("Content-Type", "text/html")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)
```

Rename the current `_status_page_empty_body` to `_status_page_no_selection_body` (used only when
`selection is None`), and add `_status_page_selected_empty_body(self, selection,
manifest_summary)`: reuse the same picker/create-expedition/create-leg panel markup from the
current empty body (`curation_server.py:1004-1067`, unchanged — the picker is still useful even
with a selection, e.g. to switch legs), but change the summary text at the top from
`{manifest_summary}` (which was the raw exception string before Task 1.3, per Phase 6 below) to a
plain sentence:

```python
f'<p>Active: <code>{html.escape(selection["expedition"])}/{html.escape(selection["leg"])}</code>, '
f'{html.escape(manifest_summary)}. Launch a round from <a href="/runs.html">runs.html</a> '
f'or pick a different leg below.</p>'
```

- [ ] **Step 4: Run test to verify it passes.**
- [ ] **Step 5: Run full suite.**
- [ ] **Step 6: Live-check** — with a leg selected that has no manifest, confirm the root page
  says "Active: X/Y — no scored manifest yet", not "no expedition/leg selected".
- [ ] **Step 7: Commit**

```bash
git add src/clawmarks/curation_server.py tests/test_curation_server_expedition_routes.py
git commit -m "fix(server): distinguish 'no leg selected' from 'leg selected, no data yet' on the root page"
```

### Task 1.4: Root-page resume + comparison-count summary

**Files:**
- Modify: `src/clawmarks/curation_server.py` (`_status_page_data_body`, from Task 1.3)
- Test: extend `tests/test_curation_server_expedition_routes.py`

Add to `_status_page_data_body` (the "has data" branch) a one-liner inline script that calls the
existing `/api/preference_status` endpoint and renders the comparison count, matching
solo-researcher-continuity R1:

```html
<p id="cmpStat" class="sub">&nbsp;</p>
<script>
fetch('/api/preference_status').then(r => r.json()).then(d => {
  const el = document.getElementById('cmpStat');
  if (typeof d.n_comparisons === 'number') {
    const acc = (d.model_meta && typeof d.model_meta.cv_accuracy === 'number')
      ? `, model at ${(d.model_meta.cv_accuracy * 100).toFixed(0)}%` : '';
    el.textContent = `${d.n_comparisons} comparisons${acc}`;
  }
}).catch(() => {});
</script>
```

- [ ] Write a test asserting `cmpStat` and the fetch call appear in the rendered body.
- [ ] Implement as above.
- [ ] Run full suite, live-check, commit (`feat(ui): show comparison progress on the root status page`).

---

# Phase 2: Paid/destructive actions fire without confirming their target

cockpit-autopilot, expedition-launch-hub, and data-integrity-affordances each flagged this
independently and ranked it their #1 recommendation. Given the project's own history of losing a
full sweep of RunPod-billed output to an unattended destructive action (`CLAUDE.md`), this is the
highest-stakes phase in the whole plan.

### Task 2.1: Cockpit "Run queued trial" gets a payload-summary confirmation

**Files:**
- Modify: `src/clawmarks/build/cockpit.py:591-626` (queue row rendering + `runTrial`, read above)
- Test: add a Playwright-driven check (this is pure client JS; no server-side test applies) —
  document the manual verification steps in Step 5 below instead of a pytest test.

Currently `runTrial(id)` (cockpit.py:617-626) posts to `/api/cockpit/queue/${id}/run` on one
click with no intermediate state. Each row (cockpit.py:594-599) shows only title, image count,
seed strategy, strength, sampler, steps, CFG — not prompt, hypothesis, target cell, negative
prompt, or expedition (cockpit-autopilot problem 2).

- [ ] **Step 1: Expand each draft row with full payload details.**

In `renderQueue()` (cockpit.py:591-599), change the per-row template so drafts show the first
line of the prompt and the target cell, matching cockpit-autopilot recommendation 3:

```js
$('queuePane').innerHTML = draftsAndRunning.length ? draftsAndRunning.map(t=>`
  <div class="trial-row"><div><b>${{escapeHtml(t.queue_title||t.mission)}}</b><br>
  <span class="small">${{escapeHtml((t.prompt||'').split('\\n')[0].slice(0,80))}}</span><br>
  <span class="small">${{t.n}} images &middot; ${{escapeHtml(t.seed_strategy)}} seeds &middot; ${{t.strength.toFixed(2)}} strength &middot; ${{escapeHtml(t.sampler)}} / ${{t.steps}} / ${{t.cfg}}</span></div>
  <span class="status ${{t.status}}">${{t.status}}${{t.error?': '+escapeHtml(t.error):''}}</span>
  ${{t.status==='draft'?`<button data-run="${{t.id}}" type="button">Review and run</button>`:''}}</div>`).join('')
  : '<div class="empty-note">No trials queued yet.</div>';
```

- [ ] **Step 2: Replace the direct `runTrial` call with a confirmation step.**

```js
function reviewTrial(id){{
  const trial = queue.find(t=>t.id===id);
  if(!trial) return;
  const summary = `Expedition: ${{trial.expedition||'(current)'}}\n`+
    `Prompt: ${{trial.prompt}}\n`+
    `Target: ${{trial.target_cell ? JSON.stringify(trial.target_cell) : '(none)'}}\n`+
    `This submits ${{trial.n}} paid RunPod job(s).`;
  if(!confirm(summary + '\n\nConfirm and run?')) return;
  runTrial(id);
}}
```

Wire `queuePane`'s `[data-run]` buttons to `reviewTrial` instead of `runTrial` directly
(`cockpit.py:600`: `button.onclick=()=>reviewTrial(button.dataset.run)`). Keep `runTrial` itself
unchanged as the actual POST.

A native `confirm()` is the minimum viable version and matches the project's existing
`"nothing fancier than necessary"` scoping in every shard; if a nicer modal already exists
elsewhere in `cockpit.py`'s CSS (check for `.modal` classes before adding a new one), reuse it
instead of introducing a second dialog pattern.

- [ ] **Step 3: Run full suite** (this task touches only client JS in an f-string; confirm no
  Python syntax errors: `uv run python -c "from clawmarks.build import cockpit; cockpit.render_html()"`
  or the equivalent existing smoke test if one exists).
- [ ] **Step 4: Live-check with Playwright.** Load `/cockpit.html`, queue a draft, click
  "Review and run", confirm the browser's native confirm dialog shows prompt/target/job-count,
  cancel it and confirm nothing was submitted, then accept and confirm the trial starts.
- [ ] **Step 5: Commit**

```bash
git add src/clawmarks/build/cockpit.py
git commit -m "feat(cockpit): require a payload-summary confirmation before running a paid trial"
```

### Task 2.2: Runs page — confirm launch and stop with the exact target

**Files:**
- Modify: `src/clawmarks/build/runs_page.py:167-194` (`launchBtn`/`stopBtn` handlers, read above)

- [ ] **Step 1: Add a confirmation to the launch handler.**

```js
launchBtn.addEventListener('click', () => {
  launchError.textContent = '';
  if (!expeditionSel.value || !legSel.value) {
    launchError.textContent = 'pick an expedition and leg first';
    return;
  }
  const msg = `Launch a search round for ${expeditionSel.value}/${legSel.value}?\n\n` +
    `This backs up and file-count-verifies the leg's out_dir first, then starts search.driver.`;
  if (!confirm(msg)) return;
  launchBtn.disabled = true;
  launchBtn.textContent = 'Backing up and launching...';
  ... // unchanged fetch call below
});
```

- [ ] **Step 2: Add a confirmation to the stop handler, naming the running pair.**

```js
stopBtn.addEventListener('click', () => {
  const msg = statusLine.textContent.startsWith('Running')
    ? `Stop this search run?\n\n${statusLine.textContent}\n\nAlready-written files are preserved; ` +
      `the driver process is sent SIGTERM, then SIGKILL if it doesn't exit.`
    : 'Stop the running search?';
  if (!confirm(msg)) return;
  stopBtn.disabled = true;
  fetch('/api/searchrun/stop', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'})
    .then(() => refreshStatus());
});
```

- [ ] **Step 3: Live-check.** Confirm both dialogs show the exact expedition/leg, and cancelling
  either leaves state unchanged (button not disabled, no network request — check via Playwright's
  network-request inspection).
- [ ] **Step 4: Commit**

```bash
git add src/clawmarks/build/runs_page.py
git commit -m "feat(runs): confirm launch and stop with the exact expedition/leg before firing"
```

### Task 2.3: Runs page defaults to the active/running leg, not alphabetical

expedition-launch-hub's highest-severity finding: `populateLegs()`/`loadExpeditions()`
(`runs_page.py:104-117`) picks whichever expedition/leg sorts first alphabetically, so a
returning researcher can launch against the wrong target once the current run ends.

**Files:**
- Modify: `src/clawmarks/build/runs_page.py:96-165`
- Modify: `src/clawmarks/curation_server.py` — confirm `/api/active-leg` GET already exists
  (it's used by the root page's picker; if there's no GET handler, only POST, add one that
  returns the current `_active_selection()`)

- [ ] **Step 1: Check for a GET `/api/active-leg` route.**

Run: `grep -n "active-leg" src/clawmarks/curation_server.py`

If only a POST handler exists, add a GET branch returning
`{"expedition": ..., "leg": ...}` or `{"expedition": None, "leg": None}` from the same
`_active_selection()` accessor Task 1.1 already uses.

- [ ] **Step 2: On load, fetch both active-leg and running status, and prefer them over
  alphabetical defaults.**

```js
function loadExpeditions() {
  return Promise.all([
    fetch('/api/expeditions').then(r => r.json()),
    fetch('/api/active-leg').then(r => r.ok ? r.json() : {}),
    fetch('/api/searchrun/status').then(r => r.json()),
  ]).then(([expeditionsResp, active, status]) => {
    expeditionsData = expeditionsResp.expeditions || [];
    expeditionSel.innerHTML = expeditionsData.map(e =>
      `<option value="${escHtml(e.name)}">${escHtml(e.name)}</option>`).join('');
    const preferExp = status.running ? status.expedition : active.expedition;
    const preferLeg = status.running ? status.leg : active.leg;
    if (preferExp && expeditionsData.some(e => e.name === preferExp)) {
      expeditionSel.value = preferExp;
    }
    populateLegs();
    if (preferLeg && Array.from(legSel.options).some(o => o.value === preferLeg)) {
      legSel.value = preferLeg;
    }
  });
}
```

- [ ] **Step 3: Live-check.** With an active leg set and no run in progress, confirm the
  dropdowns pre-select it, not the alphabetically-first pair. With a run in progress, confirm
  they pre-select the running pair instead.
- [ ] **Step 4: Commit**

```bash
git add src/clawmarks/build/runs_page.py src/clawmarks/curation_server.py
git commit -m "fix(runs): default the launch dropdowns to the active or running leg, not alphabetical order"
```

### Task 2.4: Stop control explains its consequence; favorite/unfavorite gets an undo

**Files:**
- Modify: `src/clawmarks/build/runs_page.py` (status line copy, covered by Task 2.2's confirm
  text above — no separate change needed beyond that)
- Modify: `src/clawmarks/shared_ui.py:581-593` (`toggleFavorite` in the lightbox JS, read above)

data-integrity-affordances problem 2: unfavoriting has no undo, even though favorites feed the
next search's exploit pool when predicted preference is disabled.

- [ ] **Step 1: Add a transient undo after unfavorite.**

```js
// shared_ui.py, in the lightbox JS's toggleFavorite() (currently lines 581-593)
function toggleFavorite(){
  const d = order[idx];
  const isFav = !!favorites[d.tag];
  const endpoint = isFav ? '/api/unfavorite' : '/api/favorite';
  const body = isFav ? {tag: d.tag} : Object.assign({}, d);
  const removedRecord = isFav ? favorites[d.tag] : null;
  fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
    .then(r => r.json())
    .then(() => {
      if (isFav) delete favorites[d.tag]; else favorites[d.tag] = body;
      render();
      document.dispatchEvent(new CustomEvent('lightbox:favorite', {detail: {tag: d.tag, favorited: !isFav}}));
      if (isFav && removedRecord) showUndoFavorite(d.tag, removedRecord);
    });
}

let undoTimer = null;
function showUndoFavorite(tag, record){
  clearTimeout(undoTimer);
  const status = el.querySelector('.lb-info');
  const original = status.textContent;
  status.textContent = 'Removed favorite. Undo?';
  const undoBtn = document.createElement('button');
  undoBtn.textContent = 'Undo';
  undoBtn.onclick = () => {
    fetch('/api/favorite', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(record)})
      .then(r => r.json()).then(() => { favorites[tag] = record; render(); });
  };
  el.querySelector('.lb-actions').appendChild(undoBtn);
  undoTimer = setTimeout(() => { undoBtn.remove(); }, 10000);
}
```

Requires no server changes: `/api/favorite` already accepts the full record to re-create it
(confirm by reading the existing `_favorite`/`_unfavorite` handlers in `curation_server.py`
before assuming the shape — grep for `def _favorite` and `def _unfavorite`).

- [ ] **Step 2: Live-check.** Unfavorite an image, confirm an "Undo" button appears for ~10s and
  restores the favorite when clicked, and disappears after the timeout.
- [ ] **Step 3: Commit**

```bash
git add src/clawmarks/shared_ui.py
git commit -m "feat(lightbox): add a 10-second undo after removing a favorite"
```

---

# Phase 3: Judgment-workflow correctness (compare.html)

judgment-workflow's #1 finding is a real bug, not a UX nit: `choose()` (`compare_page.py:235-264`,
read above) never disables the pane or the arrow handler while its POST is in flight, so a held
key or a double-click can fire multiple POSTs for a single displayed pair before `loadNext()`
swaps images in. The server appends every POST immediately (no dedup), so a double-vote silently
inflates the comparison count without adding real preference-model evidence.

### Task 3.1: Make each vote an explicit, single-flight transaction

**Files:**
- Modify: `src/clawmarks/build/compare_page.py:235-272` (`choose`, pane/keydown listeners)
- Test: this is client JS with no direct pytest coverage today (`compare_page.py`'s existing
  tests, if any, only check `render_html()` output — confirm with
  `grep -n "def test" tests/test_compare_page.py` if that file exists). Add the manual
  Playwright check in Step 3; add a pytest assertion only for the rendered guard flag if
  `tests/test_compare_page.py` exists and already asserts on script content.

- [ ] **Step 1: Add a `submitting` guard.**

```js
// compare_page.py, replace choose() (currently lines 235-264)
let submitting = false;

function choose(side) {
  if (!current || submitting) return;
  submitting = true;
  document.getElementById('pane1').classList.add('submitting');
  document.getElementById('pane2').classList.add('submitting');
  const winner = side === 1 ? current.img1.tag : current.img2.tag;
  const loser = side === 1 ? current.img2.tag : current.img1.tag;
  fetch('/api/compare', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({winner, loser})})
    .then(r => {
      if (!r.ok) throw new Error('Could not save the comparison');
      return r.json();
    })
    .then((res) => {
      comparedThisSession++;
      document.getElementById('count').textContent = `${comparedThisSession} compared this session`;
      if (res && typeof res.count === 'number') totalCount = res.count;
      const crossedRetrain = totalCount >= MIN_COMPARISONS && totalCount % RETRAIN_EVERY === 0;
      if (crossedRetrain) {
        fetchStatus(bumpBar);
      } else {
        renderProgress();
        if (totalCount < MIN_COMPARISONS) bumpBar();
      }
      loadNext();
      submitting = false;
      document.getElementById('pane1').classList.remove('submitting');
      document.getElementById('pane2').classList.remove('submitting');
    }).catch(() => {
      submitting = false;
      document.getElementById('pane1').classList.remove('submitting');
      document.getElementById('pane2').classList.remove('submitting');
      document.getElementById('done').textContent =
        "Couldn't reach the server. Check your connection and try again.";
      document.getElementById('done').style.display = 'block';
    });
}

document.getElementById('pane1').addEventListener('click', () => choose(1));
document.getElementById('pane2').addEventListener('click', () => choose(2));

document.addEventListener('keydown', e => {
  if (e.key === 'ArrowLeft') { e.preventDefault(); choose(1); }
  if (e.key === 'ArrowRight') { e.preventDefault(); choose(2); }
});
```

Add CSS for the guard state (near the existing `.pane` rules in this file's `<style>` block):

```css
.pane.submitting { pointer-events:none; opacity:0.6; }
```

Note the added `e.preventDefault()` on the arrow keys: judgment-workflow problem 3 flagged that
without it, arrow-key voting can also scroll the page.

- [ ] **Step 2: Run full suite.**

Run: `env -u RUNPOD_API_KEY -u CIVITAI_TOKEN uv run pytest -q`

- [ ] **Step 3: Live-check with Playwright.** Load `/compare.html`, rapidly click one pane twice
  (or hold an arrow key), and confirm only one `/api/compare` POST fires (inspect via
  `mcp__playwright__browser_network_requests`) and the comparison count advances by exactly one.

- [ ] **Step 4: Commit**

```bash
git add src/clawmarks/build/compare_page.py
git commit -m "fix(compare): make each vote a single-flight transaction, disable panes while a POST is pending"
```

### Task 3.2: Progress bar shows usable comparisons, not raw submissions

judgment-workflow problem 4: the compare page's progress bar promises an unlock at 50 raw
`n_comparisons`, but the retrain gate actually requires 50 *usable* (distinct, embedded,
consolidated) pairs. `preference_status.py:25-39` (per the memo) already computes both — this
page just needs to consume the usable count instead of the raw one.

**Files:**
- Modify: `src/clawmarks/build/compare_page.py:194-205` (`fetchStatus`)
- Modify: `src/clawmarks/build/preference_status.py` only if it does not already expose a
  `n_usable` field on `/api/preference_status` — check first with
  `grep -n "n_usable\|usable" src/clawmarks/build/preference_status.py
  src/clawmarks/curation_server.py`

- [ ] **Step 1: Confirm the field name.** If `/api/preference_status` doesn't already return
  `n_usable`, that's a prerequisite change in whichever module builds that response
  (`curation_server.py` or `preference_status.py` — grep for `preference_status` route handler)
  before this task's client change makes sense. Add it there first, following whatever field the
  memo's `preference_status.py:25-39` describes computing.

- [ ] **Step 2: Use the usable count for the bar, keep raw as secondary.**

```js
function fetchStatus(after) {
  fetch('/api/preference_status').then(r => r.ok ? r.json() : null).then(d => {
    if (d) {
      if (typeof d.n_usable === 'number') totalCount = d.n_usable;
      else if (typeof d.n_comparisons === 'number') totalCount = d.n_comparisons;
      rawCount = typeof d.n_comparisons === 'number' ? d.n_comparisons : totalCount;
      if (d.model_meta && typeof d.model_meta.cv_accuracy === 'number') {
        lastAccuracy = d.model_meta.cv_accuracy;
        modelMeta = d.model_meta;
      }
    }
    renderProgress();
    if (after) after();
  }).catch(() => { renderProgress(); if (after) after(); });
}
```

Add a `let rawCount = 0;` near the existing `let totalCount = 0;` declaration, and surface it in
`renderProgress()`'s sub-label when it differs from `totalCount`:

```js
sub.textContent = rawCount !== totalCount
  ? `${totalCount} / ${MIN_COMPARISONS} usable comparisons (${rawCount} submitted)`
  : `${totalCount} / ${MIN_COMPARISONS} comparisons`;
```

- [ ] **Step 3: Run full suite, live-check** (compare a session with some rejected/duplicate
  comparisons and confirm the two counts differ correctly), **commit**
  (`fix(compare): unlock progress tracks usable comparisons, not raw submissions`).

---

# Phase 4: Visual design-system consolidation

visual-design-system found the CSS is already ~95% consistent across 14 pages (copy-pasted, not
divergent) with two real traps: `--pick` means opposite colors on scan vs. compare, and cockpit
is the only bright page in an allnight tool. Both shards it flagged are mechanical.

### Task 4.1: Add a shared `DARK_TOKENS` block + `.btn` classes to `shared_ui.py`

**Files:**
- Modify: `src/clawmarks/shared_ui.py` (add new constants)
- Modify: all 14 `build/*.py` files listed in the memo (`map_view.py:63`, `coverage_map.py:172`,
  `elite_archive.py:142`, `preference_rank.py:73`, `preference_status.py:122`,
  `redundancy_view.py:83`, `runs_page.py:26`, `compare_page.py:36`, `scan_gallery.py:112`,
  `seed_browser.py:35`, `explore_hub.py:59`, `novelty_decay.py:89`, plus
  `curation_server.py:990` and `:1020`) to consume the shared block instead of re-declaring it
- Test: `tests/test_shared_ui.py` (extend)

**Interfaces:**
- Produces: `shared_ui.DARK_TOKENS` (a CSS string, `:root{...}` block) and `shared_ui.BTN_CSS`
  (`.btn`/`.btn--primary`/`.btn--secondary` classes) — every page's `render_html()` interpolates
  both into its `<style>` block in place of its own hand-rolled `:root` and button rules.

- [ ] **Step 1: Write the failing test**

```python
def test_dark_tokens_defines_pick_as_gold():
    from clawmarks import shared_ui
    assert "--pick:#f5c542" in shared_ui.DARK_TOKENS
```

- [ ] **Step 2: Run test to verify it fails.**
- [ ] **Step 3: Implement**

```python
# src/clawmarks/shared_ui.py — add near the top, after NAV_OPTIONS
DARK_TOKENS = """
:root { color-scheme:dark; --bg:#0b0b0d; --panel:#16161a; --panel-2:#1d1d22; --border:#2a2a30;
  --text:#eaeaee; --text-dim:#9a9aa4; --text-faint:#6a6a74; --accent:#7c9eff; --pick:#f5c542;
  --up:#5ec98a; --down:#e0605e; }
"""

BTN_CSS = """
.btn { font-size:13px; padding:6px 12px; border-radius:6px; border:1px solid var(--border);
  background:var(--panel-2); color:var(--text); cursor:pointer; }
.btn--primary { background:var(--accent); color:#0b0b0d; font-weight:600; border-color:var(--accent); }
.btn--secondary { background:var(--panel-2); color:var(--text); border:1px solid var(--border); }
.btn:disabled { opacity:0.4; cursor:not-allowed; }
"""
```

Values are copied verbatim from the existing 14-site duplication the memo documents (identical
across all but `compare_page.py`'s inverted `--pick`, fixed in Task 4.2), so this step changes no
rendered pixel by itself — it just gives one edit point going forward.

- [ ] **Step 4: Run test to verify it passes.**
- [ ] **Step 5: Swap each of the 14 files** to interpolate `{DARK_TOKENS}` in place of its own
  `:root{...}` block, and use `.btn`/`.btn--primary`/`.btn--secondary` in place of its hand-rolled
  primary/secondary button rules where those rules are pure copies (do not touch a page's
  layout-specific button variants, e.g. cockpit's mission-bar buttons, which are not in scope
  here). Do this one file at a time; after each file, run
  `uv run python -c "from clawmarks.build import <module>; <module>.render_html()"` (adjust per
  file's actual entry point/args) to confirm the f-string still renders without a `KeyError` or
  `NameError` before moving to the next file.
- [ ] **Step 6: Run full suite.**
- [ ] **Step 7: Live-check** two or three of the touched pages side by side with the pre-change
  screenshots (or just visually confirm no color/spacing change) to verify this was truly a
  no-visual-diff refactor.
- [ ] **Step 8: Commit** (one commit per file, or one combined commit if the diff review is
  easier that way — this project has no stated preference either way for pure-refactor commits,
  so keep them together): `refactor(ui): consolidate the 14 duplicated dark-mode token blocks into shared_ui.DARK_TOKENS`.

### Task 4.2: Fix `--pick`'s semantic inversion in `compare_page.py`

**Files:**
- Modify: `src/clawmarks/build/compare_page.py:37` (or wherever `--pick` now lives post-Task 4.1)

`compare_page.py` currently declares `--pick:#7c9eff` (blue, the accent color) while every other
page uses `--pick:#f5c542` (gold, meaning "human picked"). Since Task 4.1 already fixed the
canonical value to gold, check whether `compare_page.py` has any CSS rule relying on `--pick`
resolving to blue (grep `var(--pick)` in this file); if such a rule exists, rename that specific
usage to `var(--accent)` (which is what it actually means there) rather than fighting the shared
token.

- [ ] **Step 1:** `grep -n "pick" src/clawmarks/build/compare_page.py` and inspect every hit.
- [ ] **Step 2:** Rename any accent-colored-but-labeled-`--pick` usage to `--accent`.
- [ ] **Step 3:** Run full suite, live-check `/compare.html` renders unchanged visually, commit
  (`fix(compare): stop reusing --pick to mean accent-blue; use --accent`).

### Task 4.3: Give cockpit a dark-mode variant for allnight sessions

**Files:**
- Modify: `src/clawmarks/build/cockpit.py` (near line 102, and the `.cockpit-topnav` override —
  read the file's `<style>` block in full before editing, since this plan only saw lines
  580-697; read 1-350 before starting this task)
- Reference: `src/clawmarks/build/probe_report.py:167-175` — already does dual-theme via
  `@media (prefers-color-scheme: dark)`; copy that pattern rather than inventing a new one.

- [ ] **Step 1: Read `cockpit.py` lines 1-350 and `probe_report.py` lines 150-200** to see the
  exact current `--paper`/`--ink` declarations and the precedent dual-theme block.
- [ ] **Step 2: Add a `@media (prefers-color-scheme: dark)` block below the existing `:root`**
  that swaps `--paper`/`--ink` for dark equivalents (e.g. `--paper: var(--bg)`,
  `--ink: var(--text)`), following `probe_report.py`'s exact structure.
- [ ] **Step 3: Drop the `.cockpit-topnav` background override** once the nav bar's dark
  variables apply correctly in both color schemes (it exists only because the light cockpit page
  clashed with the dark-only nav bar).
- [ ] **Step 4: Live-check** cockpit in both a light-scheme and dark-scheme browser/OS setting
  (Playwright can emulate `color-scheme` via `browser_resize`/CDP or by toggling OS-level
  `prefers-color-scheme` — use whatever mechanism this repo's other dual-theme pages are already
  tested with, e.g. check `probe_report.py`'s own test file for the pattern).
- [ ] **Step 5: Commit** (`feat(cockpit): add a dark-mode variant for low-light overnight sessions`).

### Task 4.4: Collapse the three near-duplicate surface greys

**Files:**
- Modify: `runs_page.py:38,45`, `preference_status.py:137`, and wherever `--panel-2` /
  `#1d1d22` / `#24242a` / `#1f1f24` are used for the same "secondary surface" role — grep each
  literal across `src/clawmarks/build/*.py` first to get the exact current call sites (line
  numbers in the shard memo are for the state at commit `f2bb89d`; re-grep them now since
  Task 4.1 may have already touched some of these files).
- [ ] Replace each literal with `var(--panel-2)` from the now-shared `DARK_TOKENS`.
- [ ] Run full suite, live-check, commit (`refactor(ui): collapse three duplicate secondary-surface greys into --panel-2`).

---

# Phase 5: Gallery/archive at scale

gallery-archive-scale found `scan.html` already solved the hard scaling problems (chunked
rendering, lazy thumbnails, debounced filters); `archive.html`'s "view all" modal has none of
that and is the page most likely to degrade first, since MAP-Elites search concentrates images
into a few hot cells.

### Task 5.1: Paginate the archive "view all" modal

**Files:**
- Modify: `src/clawmarks/build/elite_archive.py:271-285` (`openModal`, per the memo — read the
  full file before editing since this plan hasn't read it directly; cite exact current line
  numbers from your own read, they may have shifted)
- Reference implementation: `src/clawmarks/build/scan_gallery.py:302-382` (`renderMore()`,
  `PAGE_SIZE`, the `IntersectionObserver` sentinel pattern) — copy this pattern, don't invent a
  new one.

- [ ] **Step 1: Read `elite_archive.py` in full** and confirm the exact current `openModal`
  implementation and its cell-image-list source.
- [ ] **Step 2: Read `scan_gallery.py:290-390`** to copy its chunking pattern verbatim (same
  `PAGE_SIZE`-style constant, same sentinel div + `IntersectionObserver` with `rootMargin: '600px'`).
- [ ] **Step 3: Apply the same pattern to the modal's image list**, capping the initial render at
  a fixed page size (150, matching `scan_gallery.py`'s constant) with a "load more" sentinel, and
  add a "showing N of M, load all" affordance per the memo's recommendation.
- [ ] **Step 4: Run full suite.**
- [ ] **Step 5: Live-check** by opening a cell with many images (or a synthetic fixture with
  200+ entries) and confirming the modal no longer does one giant `innerHTML` write.
- [ ] **Step 6: Commit** (`fix(archive): paginate the 'view all' modal instead of rendering the whole cell at once`).

### Task 5.2: Add `Cache-Control` headers to `/thumbs/`, `/real_thumbs/`, and served images

**Files:**
- Modify: `src/clawmarks/curation_server.py:1390-1417` (the `/thumbs/` route and fallthrough to
  `super().do_GET()`, read above)

- [ ] **Step 1: Read `curation_server.py:1370-1420` in full** to see the exact current
  route-guard structure before editing (the memo's line numbers are from commit `f2bb89d`).
- [ ] **Step 2: Add a header** before the fallthrough:

```python
self.send_header("Cache-Control", "public, max-age=31536000, immutable")
```

on the response path(s) serving `/thumbs/<tag>.jpg` and `/real_thumbs/<name>` (both routes
already exist — `curation_server.py:1316` — no dependency on any other task in this plan), and
any served `.png`/`.jpg` under the active leg's `out_dir` (full-res generation output is never
overwritten in place, per the memo).

- [ ] **Step 3: Run full suite, live-check** (inspect response headers via
  `mcp__playwright__browser_network_requests` on a reload), **commit**
  (`perf(server): send long-lived Cache-Control on immutable thumbnail/image responses`).

### Task 5.3: Gate `wireThumbPrefetch` behind hover/focus, not raw viewport proximity

**Files:**
- Modify: `src/clawmarks/shared_ui.py:621-646` (`wireThumbPrefetch`, read above)

Current behavior: any thumb within a 150px scroll margin eagerly fetches its full-resolution
1-2.5MB PNG. On a dense grid this means dozens of concurrent large fetches purely from scrolling.

- [ ] **Step 1: Narrow the trigger to hover (desktop) or focus (keyboard), per the memo's option
  (a).**

```js
function wireThumbPrefetch(){
  const observed = new WeakSet();
  function wireOne(img){
    if (observed.has(img)) return;
    observed.add(img);
    let hoverTimer = null;
    img.addEventListener('mouseenter', () => {
      hoverTimer = setTimeout(() => {
        const tag = img.dataset.tag;
        if (tag) loadData().then(() => prefetchImage(byTag[tag])).catch(() => {});
      }, 150);
    });
    img.addEventListener('mouseleave', () => {
      clearTimeout(hoverTimer);
      const tag = img.dataset.tag;
      if (tag) abortPrefetch(tag);
    });
    img.addEventListener('focus', () => {
      const tag = img.dataset.tag;
      if (tag) loadData().then(() => prefetchImage(byTag[tag])).catch(() => {});
    });
  }
  function scan(){ document.querySelectorAll('img[data-tag]').forEach(wireOne); }
  scan();
  new MutationObserver(scan).observe(document.body, {childList: true, subtree: true});
}
```

This removes the `IntersectionObserver`-based eager viewport prefetch entirely in favor of
intent-based triggers, keeping the lightbox's own `prefetchNeighbors()` (next/prev inside an open
lightbox, unaffected — that's a separate function) as the fast-open mechanism once a click
happens.

- [ ] **Step 2: Run full suite, live-check** — confirm hovering a thumb ~150ms starts a fetch
  (network tab), moving away aborts it, and scrolling past many thumbs without hovering causes no
  large fetches.
- [ ] **Step 3: Commit** (`perf(lightbox): prefetch full-res images on hover/focus intent, not raw scroll proximity`).

### Task 5.4: Persist scan.html filter/sort state in the URL

**Files:**
- Modify: `src/clawmarks/build/scan_gallery.py` (`applyFilters()` chokepoint — read the file in
  full first; the memo cites this as the single biggest usability win for overnight sessions)

- [ ] **Step 1: Read `scan_gallery.py` in full**, locate `applyFilters()` and every control whose
  change should round-trip through the URL (sort, type/category/prompt filters, faithfulness
  min/max, free-text search, picked-only, favorited-only).
- [ ] **Step 2: Route each control change through `history.replaceState` writing a
  `URLSearchParams`**, and add a `popstate` handler (and an on-load read) that restores control
  values from the URL before the first `applyFilters()` call.
- [ ] **Step 3: Run full suite, live-check** — set a filter combo, reload the page, confirm it's
  restored; use the back button after changing filters and confirm it steps back correctly.
- [ ] **Step 4: Commit** (`feat(scan): persist filter/sort state in the URL so a reload doesn't lose it`).

### Task 5.5: Fix "newest first" to respect round, not just generation number

**Files:**
- Modify: `src/clawmarks/build/scan_gallery.py:23-25` (`generation_of`, per the memo)

- [ ] **Step 1:** Read the current `generation_of` regex/parsing.
- [ ] **Step 2:** Change it to return a `(round, gen)` tuple, parsing the `r2_` (or similar)
  prefix into the round component instead of ignoring it, so `r2_gen3_...` sorts after
  `gen3_...` (round 1) rather than equal to it.
- [ ] **Step 3:** Update the sort comparator that consumes `generation_of` to compare tuples.
- [ ] **Step 4:** Run full suite (add a unit test for `generation_of` if none exists — feed it
  `"gen3_..."` and `"r2_gen3_..."` and assert the round-2 tag sorts later), live-check the
  "generation (newest first)" sort on a manifest spanning two rounds, commit
  (`fix(scan): make 'newest first' sort respect round number, not just generation`).

---

# Phase 6: Error and empty-state legibility

error-empty-states found the `FileNotFoundError` hint fires the same wrong advice ("re-point the
manifest paths") whether the manifest file itself is missing or an image file behind a valid
manifest is missing — two very different fixes.

### Task 6.1: Split the `FileNotFoundError` hint by which file is actually missing

**Files:**
- Modify: `src/clawmarks/curation_server.py:930-939` (`_send_error_page`, read above)

- [ ] **Step 1: Implement the branch**

```python
def _send_error_page(self, exc, detail):
    message = f"{type(exc).__name__}: {exc}"
    hint = ""
    if isinstance(exc, FileNotFoundError):
        missing_path = str(exc).split("'")[1] if "'" in str(exc) else ""
        if missing_path.endswith("scored_manifest.json"):
            hint = (
                "<p>The active leg has no scored manifest yet. "
                '<a href="/">Pick a leg that has completed a search round</a>, or '
                '<a href="/runs.html">launch a new round for this leg</a>.</p>'
            )
        else:
            hint = (
                "<p>This usually means <code>scored_manifest.json</code> still points at an "
                "old absolute path (e.g. after the project directory was renamed or moved) and "
                "the image no longer lives there. Re-pointing or regenerating the manifest's "
                "<code>file</code> paths should fix it.</p>"
            )
    ...  # rest of the function unchanged
```

- [ ] **Step 2: Write a test.**

```python
def test_error_page_missing_manifest_hint(monkeypatch):
    # Trigger a FileNotFoundError whose path ends in scored_manifest.json and assert the
    # rendered page tells the user to pick/launch a leg, not to re-point paths.
    ...
```

Follow this test file's existing conventions for triggering `_send_error_page` (check
`tests/test_curation_server_expedition_routes.py` or a dedicated error-page test file for the
pattern).

- [ ] **Step 3: Run test, run full suite, live-check** by selecting a leg with no manifest and
  opening any tool page directly, confirming the correct hint shows.
- [ ] **Step 4: Commit** (`fix(server): give the right diagnosis for a missing manifest vs. a stale image path`).

### Task 6.2: Human-readable status-page message instead of a raw exception string

Already covered by Task 1.3 above (the third-branch rewrite replaces the raw
`f"could not read manifest: {e}"` string with a plain sentence) — no separate task needed here,
but if Task 1.3 is skipped or reordered, this specific sub-change (`curation_server.py:970-971`)
must still land on its own.

### Task 6.3: Upgrade the missing-manifest startup warning to match the stale-paths check

**Files:**
- Modify: `src/clawmarks/curation_server.py` (`_check_manifest_images`, per the memo around
  lines 1969-1993 — re-grep for the current line numbers, since earlier tasks in this plan may
  shift them)

- [ ] **Step 1: Read the function in full.**
- [ ] **Step 2: Change the missing-manifest branch** from a stdout `print("warning: ...")` to
  `print(..., file=sys.stderr)` with the same actionable guidance as the stale-paths branch
  (name the affected expedition/leg, suggest switching legs or launching a round). Do not add a
  `sys.exit(1)` here unless *every* leg across *every* expedition has no manifest (that would be
  a legitimately fatal state); check with the existing `_list_expeditions()` helper before
  deciding whether to exit.
- [ ] **Step 3: Run full suite, commit** (`fix(server): emit missing-manifest startup warnings to stderr with actionable guidance`).

### Task 6.4: Show the request path on the error page

**Files:**
- Modify: `src/clawmarks/curation_server.py` (`_send_error_page`, body template around
  line 940-949)

- [ ] **Step 1:** Thread the request path (`self.path`, already available on the handler) into
  `_send_error_page`'s body template: add `<p>Route: <code>{html.escape(self.path)}</code></p>`
  right after the `<h1>`.
- [ ] **Step 2:** Run full suite, live-check with two tabs open on different failing routes,
  confirm each shows its own path, commit (`fix(server): show the request path on the error page`).

### Task 6.5: Route 404s through the app's styled error shell

**Files:**
- Modify: `src/clawmarks/curation_server.py:1378,1396,1411,1417` (per the memo — re-grep current
  line numbers)

- [ ] **Step 1:** Read the handler class and find every `self.send_error(404, ...)` call plus the
  `super().do_GET()` fallthrough.
- [ ] **Step 2:** Add a small `_send_404_page(self, path)` sharing the same visual shell as
  `_send_error_page` (dark background, consistent typography) with a "nothing here" message
  instead of a stack trace, and call it from each of the three explicit 404 sites.
- [ ] **Step 3:** For the `super().do_GET()` fallthrough 404s (which `SimpleHTTPRequestHandler`
  handles inline without raising), override `send_error` on the handler class to route status
  404 through `_send_404_page` instead of the base class's plain-text page.
- [ ] **Step 4:** Run full suite, live-check by requesting a nonexistent route and a nonexistent
  static file, confirm both render the app's dark theme, commit
  (`fix(server): style 404 pages consistently with the rest of the app`).

---

# Phase 7: DINOv2-similarity page explainability

scientific-visualization: none of `/map.html`, `/coverage.html`, `/redundancy.html`,
`/novelty_decay.html` define DINOv2 or distinguish the three different cosine-similarity metrics
they surface, despite the project's own `probe_report.py` already having solved score
calibration.

### Task 7.1: Add a shared DINOv2 explainer tooltip

**Files:**
- Modify: `src/clawmarks/shared_ui.py` (add a constant near `info_btn`)
- Modify: `src/clawmarks/build/map_view.py`, `coverage_map.py`, `redundancy_view.py`,
  `novelty_decay.py` (first mention of "DINOv2" on each page)

- [ ] **Step 1: Add the shared tip.**

```python
# shared_ui.py
DINO_TIP = (
    "DINOv2 is an open vision model that turns an image into about 768 numbers (an embedding) "
    "capturing style without human labels; similar style gives similar embeddings, so we measure "
    "style match without a human."
)
```

- [ ] **Step 2:** In each of the four pages, wrap the first literal occurrence of "DINOv2" with
  `{info_btn(DINO_TIP)}` (import `DINO_TIP` alongside the existing `info_btn` import).
- [ ] **Step 3:** Run full suite, live-check each page shows the tooltip on first mention, commit
  (`docs(ui): add a shared DINOv2 explainer tooltip to the four similarity pages`).

### Task 7.2: Name the three cosine similarities distinctly

**Files:**
- Modify: `src/clawmarks/build/map_view.py:241-244,252` (hover panel + nearest-real caption)
- Modify: `src/clawmarks/build/redundancy_view.py:114` (slider label)

- [ ] **Step 1: Read `map_view.py:230-260`** to see the exact current hover-panel template.
- [ ] **Step 2:** Change `faith` and `sim` labels to `"style match to your real art's average"`
  and `"closest single training photo"` respectively, per the memo's exact wording.
- [ ] **Step 3:** In `redundancy_view.py`, change the bare `"Similarity threshold"` label to
  `"image-to-image match threshold"`.
- [ ] **Step 4:** Run full suite, live-check both pages, commit
  (`docs(ui): distinguish centroid similarity, nearest-real similarity, and pairwise similarity by name`).

### Task 7.3: Port probe-report's score calibration to map/coverage

**Files:**
- Modify: `src/clawmarks/build/map_view.py` (hover panel), `coverage_map.py` (legend, around
  lines 342-345 per the memo)
- Reference: `src/clawmarks/build/probe_report.py:384-389` (existing calibrated-band pattern)

- [ ] **Step 1: Read `probe_report.py:370-400`** to copy its min/median/max calibration pattern
  exactly.
- [ ] **Step 2:** In `map_view.py`, pass `min`/`median`/`max` of `centroid_sim` into the hover
  panel and render e.g. `"faith 0.42 (median 0.39 this sweep)"`.
- [ ] **Step 3:** In `coverage_map.py`, add count ticks (`"1"`, `"median N"`, `"max M"`) to the
  legend.
- [ ] **Step 4:** Run full suite, live-check, commit
  (`feat(ui): calibrate faithfulness/similarity scores against this sweep's own range`).

### Task 7.4: Small remaining explainability fixes

- [ ] Add a 3-row on-canvas legend to `map_view.py` (star = real training photo, dot = generated,
  gold dot = picked winner) per the memo's CSS-only suggestion at its current lines 88-94.
- [ ] Append the quantile-bin and median-frontier-gate explanation to `coverage_map.py`'s
  `axes_tip`, exact wording from the memo's recommendation 5.
- [ ] Add scale context below the redundancy slider (`"default 0.93 (tightest 5% of pairs this
  sweep); your pairs span 0.71-0.98"`, using the already-computed `all_scores` data) and append
  `"(highest novelty)"` to the representative-image label.
- [ ] Add novelty's one-sentence definition to `novelty_decay.py`'s subtitle.
- [ ] Add a tooltip to the map's play control.
- Run full suite, live-check each, commit each as its own small commit (or one combined
  `docs(ui): finish the scientific-visualization explainability pass` commit — these are all
  independent one-line copy additions with no interface dependency between them).

---

# Phase 8: Remaining IA/navigation, solo-researcher, and hygiene items

Everything else from ia-navigation and solo-researcher-continuity not already covered by
Phase 1, plus judgment-workflow's keyboard-accessibility and metric-anchoring items, plus
repo hygiene.

### Task 8.1: Make `explore.html` the stable tool home, group the flat nav list

**Files:**
- Modify: `src/clawmarks/build/explore_hub.py`
- Modify: `src/clawmarks/shared_ui.py` (`NAV_OPTIONS`/`nav_bar_html`, extend grouping)

- [ ] **Step 1: Read `explore_hub.py` in full.**
- [ ] **Step 2:** Group the tool list into four labeled sections in both `explore_hub.py`'s
  layout and the shared jump-menu (`NAV_OPTIONS` consumer in `nav_bar_html`): **Generate**
  (cockpit, runs, seeds), **Curate** (compare, scan, archive), **Understand search** (map,
  coverage, redundancy, novelty decay, lineage), **Preference model** (status, ranking). Keep
  every route name and one-click access unchanged — this is presentation grouping only.
- [ ] **Step 3:** Add a "Tools" link (to `explore.html`) into both root-page branches (Task 1.3's
  new selected-empty body and the existing data body), and add an "Expedition / leg" context
  link into the shared nav bar next to the active-leg label from Task 1.1.
- [ ] **Step 4:** Run full suite, live-check, commit (`feat(ui): group the flat tool list into four labeled sections`).

### Task 8.2: Add contextual next-step links on high-traffic pages

- [ ] Coverage page: add a "Target this gap in cockpit" link per cell.
- [ ] Compare page: link to preference status and ranking.
- [ ] Status page: link back to compare and forward to ranking (may already partly exist via
  Task 1.4's `preference_status.html` link).
- [ ] Runs page (on a completed run): link to scan, coverage, novelty decay for that leg.
- [ ] Lineage page: "Continue this lineage in cockpit" link.
- Run full suite, live-check each, commit as one combined
  `feat(ui): add contextual next-step links between related tool pages` commit (these are
  independent one-link additions with no shared interface).

### Task 8.3: Bring nav exceptions onto the shared contract

**Files:**
- Modify: `src/clawmarks/build/scan_gallery.py:186-198` (its own hand-maintained "More tools" menu)
- Modify: `src/clawmarks/build/preference_rank.py:54-57` (unstyled no-model sentence)
- Modify: `src/clawmarks/build/cockpit.py:472` (no-data link pointing at `/` instead of `runs.html`)

- [ ] Replace `scan.html`'s local menu with the shared `nav_bar_html(...)` call (matching every
  other page), preserving its additional cockpit/runs/compare/preference links by confirming
  they're already in `NAV_OPTIONS`.
- [ ] Replace `preference_rank.html`'s bare no-model sentence with the standard page shell
  (nav bar + consistent styling) around the same message.
- [ ] Change cockpit's no-data "Launch a search round" link from `/` to `/runs.html`, where
  launching actually happens.
- Run full suite, live-check all three, commit
  (`fix(ui): bring scan.html, preference_rank.html, and cockpit's no-data link onto the shared nav contract`).

### Task 8.4: Judgment-workflow keyboard/screen-reader accessibility

**Files:**
- Modify: `src/clawmarks/build/compare_page.py:105-114,266-345` (panes, magnifier, zoom overlay)

- [ ] **Step 1:** Give each `.pane` `role="button"`, `tabindex="0"`, an accessible label (e.g.
  `aria-label="Choose this image"`), and a `:focus-visible` outline in CSS.
- [ ] **Step 2:** Add `Enter`/`Space` keydown handling on each pane equivalent to a click.
- [ ] **Step 3:** Give the zoom-icon magnifier the same treatment (`tabindex`, keyboard-open),
  and add an `Escape` handler on the zoom overlay that closes it and returns focus to the
  magnifier that opened it (extend the existing `keydown` handler this file already has for
  arrow-key voting).
- [ ] **Step 4:** Run full suite, live-check by tabbing through `/compare.html` with a keyboard
  only (no mouse) and confirming both panes and the magnifier are reachable and operable, commit
  (`feat(compare): make the judgment task fully keyboard and screen-reader operable`).

### Task 8.5: Hide compare metrics until after choice

**Files:**
- Modify: `src/clawmarks/build/compare_page.py:134-137` (`caption`, its render call sites)

- [ ] **Step 1:** Change captions to show only a neutral label ("Image A" / "Image B") while
  `current` is unanswered.
- [ ] **Step 2:** After `choose()` resolves (before `loadNext()` swaps to the next pair), briefly
  reveal the full `caption()` text (prompt name, faithfulness, novelty) for ~1s, or move it behind
  a "show sampling details" `<details>` disclosure the memo suggests as the alternative — pick
  whichever is simpler given the existing DOM structure once Step 1 is implemented; both satisfy
  the finding.
- [ ] **Step 3:** Run full suite, live-check, commit
  (`fix(compare): hide faithfulness/novelty metrics until after a choice, to reduce anchoring`).

### Task 8.6: Bounded review mode for `preference_rank.html`

**Files:**
- Modify: `src/clawmarks/build/preference_rank.py` (read in full first — the memo cites lines
  23-33, 79-111 for the current unbounded 500-thumbnail grid)

- [ ] **Step 1:** Read the file in full.
- [ ] **Step 2:** Add rank ordinals to each rendered cell.
- [ ] **Step 3:** Add a review-mode toggle presenting a bounded subset (top 20, middle 10,
  bottom 10 per the memo) with a per-item "matches my taste / questionable" mark, storing only
  the reviewer's flag/notes (not another training label) via a small new endpoint or extending an
  existing one — check `curation_server.py` for a natural place to add
  `/api/preference_rank/flag` before inventing a new route pattern.
- [ ] **Step 4:** Run full suite, live-check, commit
  (`feat(preference-rank): add a bounded top/middle/bottom review mode with a taste-check flag`).

### Task 8.7: Solo-researcher mobile-viewport fixes

**Files:**
- Modify: `src/clawmarks/build/preference_status.py:149` (toggle row wrapping)

- [ ] Add `flex-wrap:wrap` and a `gap` to the `.toggle-row` rule so the checkbox label and
  "Retrain now" button wrap onto separate lines below 400px, matching the memo's R4.
- [ ] Run full suite, live-check at a 390px viewport width via Playwright's mobile emulation,
  commit (`fix(preference-status): wrap the retrain toggle row instead of clipping on narrow viewports`).

### Task 8.8: Root-page "Resume" button for the persisted active leg

Already substantially covered by Task 1.3/1.4's status-page rewrite. If a one-click "Resume"
button (distinct from the picker buttons, pre-selecting the persisted `_active_selection()`
without requiring a click through the full picker) is still wanted on top of that, add it as a
single `<button>` above the expedition grid in `_status_page_no_selection_body`, POSTing the
already-known persisted selection to `/api/active-leg` and reloading. Optional — the memo itself
rates this "nice to have," lowest priority in its own list.

### Task 8.9: Repo hygiene

**Files:**
- Delete: `docs/superpowers/specs/2026-07-11-toml-config-design.md`,
  `docs/superpowers/specs/2026-07-11-ui-redesign-design.md` (rejected specs, per the memo)
- Modify: `.gitignore` (add `*.backup_candidate_seeds_*`)
- Modify: `TODO.txt` (reconcile with reality; not tracked by git, no commit needed for this file)

- [ ] Confirm both spec files are indeed superseded/rejected (check git log / the specs
  directory for a newer replacement) before deleting.
- [ ] Add `*.backup_candidate_seeds_*` to `.gitignore` (check the file's current state first —
  `git status` shows `.gitignore` already has uncommitted changes from unrelated work; add this
  line without reverting that other work).
- [ ] Fold anything from `TODO.txt` worth a permanent record into `notes/lab_notebook.md`'s lab
  log, then let `TODO.txt` itself go back to reflecting only current work (it's gitignored, no
  commit needed).
- [ ] Commit the spec deletion and `.gitignore` addition:
  `git commit -m "chore: remove rejected specs, ignore stray backup-seed directories"`.

---

## Verification for the whole plan

Nothing counts as done on a passing test suite alone.

1. `env -u RUNPOD_API_KEY -u CIVITAI_TOKEN uv run pytest -q` passes after every phase (CI's real
   condition).
2. `uv run ruff check src tests` and `uv run mypy src` pass (CI's exact scope).
3. Every task that touches a page gets a live Playwright check against a restarted
   `curation_server.py`, per `CLAUDE.md` — a passing suite says nothing about whether a page
   renders or an interaction actually works.
4. Re-open each of the 10 shard memos after its corresponding phase lands and confirm every
   numbered problem it raised now has a corresponding shipped fix or an explicit, recorded reason
   it was skipped (fold that reasoning into `notes/lab_notebook.md`, not just this plan file).
