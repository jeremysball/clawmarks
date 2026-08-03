# Design shard: solo-researcher session continuity

**Scope:** read-only UX review of `curation_server.py` and its build modules for
resumability across sessions and narrow-viewport usability. Screenshots captured
live at 390x844px against the running server.

## What I observed

The server persists the active leg to disk (`src/clawmarks/curation_server.py:130-137`)
and loads it at startup, but this information surfaces nowhere in the UI. The root
page (`/`) renders one of two branches based on whether a scored manifest exists
(`src/clawmarks/curation_server.py:974-977`), not on whether a leg is selected. When
a leg exists but has no data yet, the page shows "No expedition/leg selected" even
though `_set_active_selection` has already accepted the click and written
`ACTIVE_LEG_FILE` successfully. There is no third branch for "leg selected, no data
yet."

The compare page (`src/clawmarks/build/compare_page.py:127`) tracks
`comparedThisSession` in browser-side JS only: zero on every page load, lost on tab
close, no server-side mirror. Jeremy must remember or navigate to
`/preference_status.html` to find his total comparison count, a four-tap trip from
the hub that tells him the state but requires him to know to look there.

Every tool page uses the shared nav bar (`src/clawmarks/shared_ui.py:45-55`) with a
"jump to..." dropdown and a "all tools" backlink. No page shows the currently active
expedition/leg. Jeremy can land on any page by URL or bookmark and not know which
dataset he is working against without walking back to `/`.

The MOBILE_BASE_CSS (`src/clawmarks/shared_ui.py:144-153`) is minimal: font-size
reduction, padding reduction, tap-target min-height. It does not re-flow nav bar
elements for narrow viewports beyond `max-width:none` on the select. The cockpit
page has its own extensive mobile layout rules (`src/clawmarks/build/cockpit.py:302-351`),
well-developed but complex; the other pages rely on the shared base plus one or two
per-page media queries. In live testing at 390px, compare.html and explore.html
render legibly with no overflow. The preference_status page clips its toggle row at
very narrow widths (checkbox label runs against the "Retrain now" button with no
wrapping).

## Concrete problems

### P1: Root page says "No expedition/leg selected" after a valid selection succeeds

`curation_server.py:974` checks `has_data`, which depends on `scored_manifest.json`
existing and being readable. When a new leg is selected (one that has never had a
search run), the file does not exist, so `has_data` is false, and the empty-state
branch fires. But the user *did* select a leg. The page gives no feedback that the
selection was accepted; it looks identical to before the click. A user who picks a
fresh leg sees the same "No expedition/leg selected" text and can reasonably
conclude the click failed and click again.

### P2: No "where you left off" on the root page

The root page has access to:
- The persisted active leg (loaded at `curation_server.py:137`)
- The list of expeditions and their legs (`_list_expeditions()`)
- Whether a search run is active (`run_manager.status()`)

None of this is rendered. Jeremy opens the page the next day and sees a generic
"pick a leg" screen with an expedition picker: no indication that he was working on
`uncanny_frontier/round2` yesterday, no "resume where you left off" affordance, no
comparison count, no last-activity timestamp.

### P3: Comparison progress is invisible without navigation

`compare.html` fetches `/api/preference_status` on load and shows model-train
progress, but only on that page. The root page has no comparison count. The nav bar
has no badge. Jeremy must know to check `/preference_status.html` (or re-open
compare.html) to learn where he stands, which requires knowing the tool exists and
what it reports.

### P4: No active expedition/leg shown in the nav bar

Every tool page calls `nav_bar_html(current)` which produces a backlink and a
dropdown, but the active leg is never injected into that template. Landing on
`/compare.html` from a bookmark or a phone tab shows no indication of which leg is
active.

### P5: No last-session timestamp or activity summary

The server has no mechanism to record "last meaningful action" (selection of leg,
POST of comparison, launch of run) with a timestamp. All state is structural (files
on disk), not activity-level. Reconstructing "what was I doing" requires reading the
lab notebook or grepping file modification times.

## Recommendations

Ranked by impact for the solo researcher.

### R1 (high impact, ~20 lines): Show active leg + comparison count on root page

Add a third branch to `_send_status_page` for "leg selected but no manifest yet,"
and a fourth section to the data-body (`_status_page_data_body`) for "resume where
you left off." Concrete minimal implementation:

- Check `_active_selection` directly instead of routing through `has_data`.
- When a leg is active, show it prominently: "Active: `uncanny_frontier`/`round2`"
  even if no manifest exists.
- Call `/api/preference_status` from a one-liner inline `<script>` on the data-body
  page and render the comparison count and model accuracy as a second stat line
  ("1,234 comparisons, model at 73%" or "Model unlocks in 12 votes").
- Add a `last_selected` timestamp when writing `ACTIVE_LEG_FILE` (current code at
  `curation_server.py:166` writes only `expedition`/`leg`), and render it as human
  relative time ("active since 2026-07-14 22:31").

No new endpoints needed: `/api/preference_status` already exists, and
`/api/active-leg` already returns the selection. The root page just needs to consume
them.

### R2 (high impact, ~5 lines): Inject active leg into nav bar

Pass `current_expedition` and `current_leg` to `nav_bar_html` and render them as a
small label next to the backlink, e.g. "uncanny_frontier/round2." This is
`shared_ui.py:45-55` with one new `<span>` element. Every tool page already has the
active leg available through `_active_selection` (global in curation_server.py, or
passable as arguments to the render functions). This gives Jeremy at-a-glance
confirmation on every page, including pages opened from stale bookmarks.

### R3 (medium impact, ~15 lines): Add a comparison badge to the nav bar

Use the existing `/api/preference_status` endpoint from a small inline script on
every page (or just the root page and compare.html) to show a live comparison count
in the nav bar. A simple `<span id="nav-compare-badge">` that updates on load would
let Jeremy see at a glance "1,234" or "0/50" next to the compare link without
navigating. Low volume of API calls since the count changes slowly.

### R4 (lower impact, ~10 lines): Narrow-viewport wrapping on preference_status
toggle row

`preference_status.py:149` renders a single `<div class="toggle-row">` with checkbox
+ label + button inline. At 390px the "Retrain now" button sits against the label
text with no wrapping. Add `flex-wrap:wrap` and a `gap` that keeps the button on its
own visual line at narrow widths. Same treatment for the info button next to the
checkbox.

### R5 (nice to have): "Resume" button on root for the persisted active leg

The root page already knows `_active_selection` at startup. If a selection is
persisted, add a prominent "Resume" button at the top of the picker panel that
selects it immediately (POST `/api/active-leg` with the stored values) and reloads.
This is one `<button>` and one event listener, placed before the expedition grid.

## What not to touch

The cockpit's mobile layout (`cockpit.py:302-352`) is well-considered and dense; it
works. The explore.html grid and compare.html `<pair>` layout both re-flow correctly
on narrow viewports. The nav bar's autohide scroll behavior (`shared_ui.py:155-169`)
is effective and costs no session memory. The `ACTIVE_LEG_FILE` persistence
mechanism is sound and already reloaded at server startup: the gap is in
presentation, not in data.

No framework migration, no template engine, no multi-session auth. All five
recommendations are small additions to existing hand-written HTML strings in the
existing pattern, fitting comfortably under 60 lines total.
