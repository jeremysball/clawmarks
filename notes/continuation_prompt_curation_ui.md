# Continuation prompt: CLAWMARKS curation web UI (2026-07-12)

Resume work on the live curation web server. Read `notes/lab_notebook.md` first (project source of
truth), especially the three 2026-07-12 entries. Read `CLAUDE.md` for the standing rules; the ones
that bite hardest below are data integrity, the fd/rg gitignore blind spot, RunPod idle billing, and
no em dashes.

## Current state (verified this session)

- Branch **`fix/curation-pages-and-sampler`** holds 8 committed changes (compare-page progress bar and
  per-pane captions, elite-archive bin labels, explore-hub sync, coverage-balanced comparison sampler,
  data-driven redundancy slider, corrected server docstring, CLAUDE.md fd/rg gotcha, notebook). Not yet
  merged to `main` or pushed. Full suite passes (192).
- **Rendering model, now documented in `curation_server.py`'s docstring:** every `.html` route renders
  in-process at request time via `view.render_html(view.compute_data(...))`. There are NO static HTML
  files and no per-page data JSON. `/scan_data.json` is the one client-fetched companion (scan.html
  only). A blank-looking page is empty-for-this-dataset or a client-side filter, never a missing file.
  Do not re-diagnose "missing static files"; that was a mistake this session, corrected.
- **Live server:** `CLAWMARKS_SWEEP_DIR=notes/uncanny_seedrun1 python3 -m clawmarks.curation_server 8420`,
  reachable at `http://100.73.69.126:8420/`. seedrun1 is 100 real 1024x1024 PNGs, a single-generation
  seed run (all `parent_tag: None`), holding **52 real user votes in `user_comparisons.json`** that must
  be preserved. Kill the server by PID from `ss -tlnp | rg ':8420'`, never `pkill` by pattern (it matches
  its own command line and kills the shell).

## Outstanding work (each item's real state confirmed by rendering the page, not assumed)

1. **Remove the binned atlas (gallery.html), "binned atlas (original)".** It renders fine (102 images),
   but the user wants it gone. Delete its route in `curation_server.py`, its view module, its entry in
   `shared_ui.NAV_OPTIONS` and the jump-to dropdown, its hub card in `explore_hub.py` (currently last),
   and any test. `rg -n 'gallery.html' src tests` to find every reference. Mechanical; do first.

2. **novelty_decay.html reads as broken but is almost certainly empty-by-design.** Like lineage, it needs
   multiple generations to show novelty falling off over rounds; seedrun1 has one generation, so there is
   nothing to plot. Confirm by reading `novelty_decay.compute_data`, then give it an explicit placeholder
   like lineage's ("nothing to show until round 2+") so it stops looking like a bug.

3. **seeds.html shows nothing.** `/api/seeds` returns 200 but seedrun1 has no `candidate_seeds.json`, so
   the list is empty; the browser 404 is just favicon. The "generate seeds" button posts to
   `/api/seeds/generate` (calls opencode/GPT-5.5, costs API time, no RunPod spend). Decide: seed a
   `candidate_seeds.json` so the page has content, or add a clear empty state and verify the generate
   button end to end. Not a code bug, an empty-data + unclear-empty-state issue.

4. **Map (UMAP) should show the nearest real training image on hover.** The map already works (100 points
   on a canvas). Each `POINTS` entry already carries `nearest_real` (a filename) and `nearest_real_sim`.
   The real images live in `REAL_DIR = {ROOT}/corrected_dataset_extract` (see
   `search/score_manifest.py:23`), which the server does NOT serve (it serves only `SWEEP_DIR`). Add a
   read-only, path-sanitized route (e.g. `/real/<name>`) that serves from `REAL_DIR`, then wire the map's
   hover tooltip to show that nearest real image and its similarity beside the hovered star, so the user
   can see how close a generation sits to an actual training image.

5. **Unified image-detail UI + generate-around (the big one, from an earlier unaddressed request).** Two
   linked asks: (a) clicking any image anywhere opens one unified detail view with its metadata (prompt,
   faithfulness, novelty, seed, nearest-real) and controls; (b) "generate images surrounding it," i.e.
   spawn variations near an image's seed/prompt. The counterfactual plumbing already exists
   (`POST /api/counterfactual`, single on-demand generation through the RunPod ComfyUI endpoint, with a
   pre-submission balance check). Extend it to N-variation generation and reuse one detail modal across
   scan, map, archive, and compare. Plan this before coding.

6. **Launch an overnight search run from the web UI (largest, plan separately).** Start/stop
   `search/driver.py` from the browser with live progress. Gate hard on the two standing risks: RunPod
   idle billing (invoke `runpod-status`, the pod must be up, pause when idle, never leave it running after
   the batch) and DATA INTEGRITY (a long unattended run writing irreplaceable generation output is exactly
   the CLAUDE.md Section 1 scenario; back up and verify before any step that writes/deletes/overwrites,
   and never let the driver clobber existing output). Design the safety rails first.

## Suggested order

Mechanical first (1), then the small empty-state clarity fixes (2, 3), then the map hover (4, medium),
then plan and build the unified detail + generate-around (5), and finally design the overnight-run
control (6, gated on the data-safety design). Append to the lab notebook after each item. Verify every
page change with headless Playwright against the live server before claiming it works; screenshot it.
