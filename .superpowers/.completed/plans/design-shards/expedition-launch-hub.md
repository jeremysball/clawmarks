# Expedition And Launch-Hub Design Review

## What I observed

The new model has a sound conceptual definition. The design defines an expedition as a themed line of work with shared defaults and a pooled history, while a leg is one run within it whose output contributes to that pool (`docs/superpowers/specs/2026-07-14-expedition-leg-generation-design.md:18-22, 65-80`). The live status hub, however, renders that relationship as a bold raw expedition name followed by a flat row of identically styled leg buttons (`curation_server.py:1004-1015`). It exposes the names but gives no indication of the expedition's purpose, a leg's purpose, its inherited defaults, or whether it has usable data.

The live server made the separation problem concrete. `GET /api/active-leg` reports `uncanny_frontier/cockpit`; `GET /api/searchrun/status` reports a live process for `trent_v3_epoch4/freeform1`. The hub then says "No expedition/leg selected" because the active cockpit lacks a manifest, even though a selection exists and a real run is spending money. This follows the hub's binary `has_data` branch (`curation_server.py:959-977`), which treats an unreadable or empty selected leg as the same empty state as no selection.

`/runs.html` uses separate expedition and leg dropdowns, but initially chooses the first alphabetically listed expedition and first leg (`runs_page.py:104-116`). It does not fetch or display the active selection. Its report updates for whichever dropdown values happen to be selected, while its status line reports the globally running leg (`runs_page.py:133-164`). Thus the page can show a running `trent_v3_epoch4/freeform1` status beside a report for `trent_v3_epoch4/cockpit`, with no explicit mismatch warning.

The cockpit has an expedition-only selector and silently sets the active leg to `cockpit` on switch (`build/cockpit.py:56-76`). That is appropriate for manual trials, but it reinforces that "active leg" is a global working context, not the currently running overnight search. The distinction is nowhere named for a returning researcher.

## Problems

1. **Critical: the launch page defaults to an arbitrary target, not the active or running target.** On a return visit, a researcher can see a live run for one leg, then read or launch against the first dropdown pair. The backend blocks a simultaneous process (`curation_server.py:1612-1624`), but after the current process ends, the stale default makes a wrong-leg launch plausible.

2. **High: the hierarchy communicates storage names, not research intent.** `trent_v3_epoch4`, `freeform1`, `round1`, and `cockpit` require remembered context. The config already carries descriptions, including that `freeform1` is a single unguided 50-image batch and that `uncanny_frontier` is reference-only, but `/api/expeditions` returns only names and leg arrays (`curation_server.py:169-179`). A researcher returning days later cannot tell why each leg exists or whether it is safe to reuse.

3. **High: launch and stop actions lack a last-moment identity check.** "Back up and launch" correctly signals a safety operation and the server validates the named expedition and leg (`curation_server.py:1590-1625`). Still, the action does not restate the exact `expedition / leg`, budget cap, generation cap, or that its shared pool includes sibling legs. Stop has no confirmation and its target is only implicit in the small status sentence.

4. **Medium: the hub hides active context when it lacks scored images.** The active `uncanny_frontier/cockpit` state appears as "No expedition/leg selected." This is factually false in the observed session and obscures the active versus running distinction precisely when a new leg has no manifest yet.

## Recommendations, Ranked By Impact

1. **Make the Runs page run-centric.** On load, fetch both `/api/active-leg` and `/api/searchrun/status`. If running, pin a prominent "RUNNING: trent_v3_epoch4 / freeform1" card above controls, populate the report from that pair, and label dropdown changes as "Inspect another leg." Disable launch while running as today. When idle, initialize dropdowns from the active selection, not alphabetical order.

2. **Add a compact preflight confirmation before launch and stop.** Launch confirmation should name the exact expedition and leg, describe the leg from its config, show effective budget cap, batch size, and generation cap, and state that a verified backup will be made. Stop confirmation should name the currently running pair and say it sends a stop request to that process. This is a small client-side addition with a large reduction in costly slips.

3. **Return and display metadata, not just raw names.** Extend the expedition listing with each expedition and leg description plus simple state such as `reference only`, `empty`, `has scored images`, and `running`. Present expedition cards with indented leg rows on the hub. Mark `cockpit` as the manual-trial leg and visually distinguish it from launchable overnight legs.

4. **Always show both contexts in a persistent header.** Replace the hub's binary empty-state wording with `Active workspace: expedition / leg` and a separate `Search process: running pair` or `none`. If the selected leg lacks a manifest, say "selected, no scored manifest yet," not "no selection." Carry the same two labels into cockpit and runs.

5. **Validate active-leg selection against an existing leg.** `_set_active_selection` validates only the expedition (`curation_server.py:160-166`). Rejecting an unknown leg would prevent an invalid persisted workspace from producing a misleading empty state.
