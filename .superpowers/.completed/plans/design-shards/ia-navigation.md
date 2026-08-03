# Information Architecture and Navigation Review

## Observations

The app has more navigation structure than the route list first suggests. `shared_ui.py` defines a sticky bar with an **all tools** link and a 14-item jump menu (`shared_ui.py:27-55`). Every main tool except `scan.html` and the hub uses it. `scan.html` has its own older **More tools** menu (`scan_gallery.py:186-198`), so no successful data page is truly stranded. The live `cockpit.html`, `compare.html`, `preference_status.html`, `explore.html`, `seeds.html`, and `runs.html` routes all returned HTTP 200 and confirmed these patterns.

There are two different homes:

- `/` is an expedition and leg context selector when the active leg lacks a readable manifest (`curation_server.py:959-977`, `1004-1067`). When data exists, it becomes a bare status readout followed by all 14 route links (`984-1002`).
- `/explore.html` is the real tool directory. It gives each route a task-oriented name and useful description (`explore_hub.py:13-27`, `49-79`). Every shared top bar returns here.

The flat tool list roughly follows likely frequency: cockpit, runs, compare, scan, broad diagnostics, preference tools, specialist diagnostics, seeds. That suits a solo researcher who learns a compact instrument through repeated use. The problem is not the number of routes. It is that the list does not express the relationships among them.

`cockpit.html` is a focused action workspace, not a global shell. It asks Jeremy to choose a generation mission and build a trial (`cockpit.py:24-53`, `362`). Opening it also silently switches the globally active leg to `cockpit` (`curation_server.py:1340-1350`). That side effect makes it a poor primary hub for pages that inspect another leg.

## Problems

1. **The root page conflates context setup, health status, and navigation.** In the live state it said “No expedition/leg selected” while the preceding error named `uncanny_frontier/cockpit/scored_manifest.json`. The active context existed; it simply lacked a manifest. Because that condition selects the empty body, every tool link disappears. The result reads as lost state rather than “cockpit selected; this leg has no scored images.”

2. **The app has competing notions of home.** Error pages return to `/` as the “status page” (`curation_server.py:907-949`), tool pages return to `explore.html`, and `explore.html` itself offers no route to the expedition and leg selector. Jeremy must remember which home changes context and which home finds tools.

3. **The shared menu is comprehensive but semantically flat.** “Coverage / void map” and “generation cockpit” have a direct workflow relationship, as do compare, preference status, preference ranking, and archive. The menu presents all as peers. Only `compare.html` links onward to preference status (`compare_page.py:173-191`). Most pages rely on the generic dropdown instead of offering the next likely action.

4. **A few exceptions weaken trust in the shared navigation.** `scan.html` omits cockpit, runs, compare, and both preference pages from its local menu (`scan_gallery.py:188-198`). `preference_rank.html` returns a plain unstyled sentence with no navigation when no model exists (`preference_rank.py:54-57`). Cockpit's no-data message links to `/` with “Launch a search round,” although launching happens on `runs.html` (`cockpit.py:472`; `runs_page.py:57-89`).

## Recommendations, Ranked by Impact

1. **Make `explore.html` the stable tool home and `/` the explicit context page.** Keep both routes, but name them consistently: **Tools** and **Expedition / leg**. Add the context link to the shared bar and the tools link to both root states. Do not make cockpit the home; its automatic leg switch would turn navigation into a state-changing action.

2. **Show the active expedition and leg in the shared bar.** A compact label such as `uncanny_frontier / round2` would prevent cross-leg mistakes during long sessions. On `/`, distinguish “no selection” from “selected leg has no scored manifest,” and keep tool navigation visible in either state.

3. **Group, but do not hide, the flat list.** Use four labeled groups in `explore.html` and the jump menu: **Generate** (cockpit, runs, seeds), **Curate** (compare, scan, archive), **Understand search** (map, coverage, redundancy, novelty decay, lineage), and **Preference model** (status, ranking). Preserve one-click access and the current route names.

4. **Add small contextual next-step links on high-traffic pages.** Coverage should offer “Target this gap in cockpit”; compare should link to status and ranking; status should link back to compare and forward to ranking; completed runs should link to scan, coverage, and novelty decay; lineage should offer “Continue this lineage in cockpit.” These links encode the research loop without forcing a linear wizard.

5. **Bring exceptions onto the shared contract.** Replace scan's hand-maintained subset with the shared options, render the standard shell in preference ranking's no-model state, and point cockpit's no-data action to `runs.html`.
