# CLAWMARKS Curation App — Structural Design-Flaw Audit

**Date:** 2026-07-19  
**Auditor:** Oren Blake (QA)  
**Target:** http://100.73.69.126:8420/ (CLAWMARKS curation app, expedition `trent_v3_epoch4`, leg `freeform1`)  
**Scope:** Markup structure, DOM state, HTTP behavior, text content — no visual/layout judgment.  
**Constraint:** Read-only; no GPU job launches, no irreversible writes.

---

## Summary of Pages Tested

| Page | URL | Status | Console Errors |
|------|-----|--------|----------------|
| Browse all images (main) | `/?expedition=trent_v3_epoch4&leg=freeform1` | 200 OK | 1 ("Transition was skipped") |
| Session status | `/status.html?...` | 200 OK | 0 |
| Solution map | `/map.html?...` | 200 OK | 0 |
| Generation cockpit | `/cockpit.html?...` | 200 OK | 0 |
| Compare (head-to-head) | `/compare.html?...` | 200 OK | 0 |
| Preference status | `/preference_status.html?...` | 200 OK | 0 |
| Predicted preference | `/preference_rank.html?...` | 200 OK | 0 |
| Research desk (explore) | `/explore.html?...` | 200 OK | 0 |
| Candidate seeds | `/seeds.html?...` | 200 OK | 0 |
| Search runs | `/runs.html?...` | 200 OK | 0 |
| Scan gallery | `/scan.html?...` | 200 OK | 1 ("Transition was skipped") |
| Coverage / void map | `/coverage.html?...` | 200 OK | 0 |
| Redundancy clusters | `/redundancy.html?...` | 200 OK | 0 |
| Novelty decay watchlist | `/novelty_decay.html?...` | 200 OK | 0 |
| Lineage tree | `/lineage.html?...` | 200 OK | 0 |
| Elite archive | `/archive.html?...` | 200 OK | 0 |
| Invalid expedition/leg | `/?expedition=nonexistent&leg=freeform1` | **500** | 1 |
| Nonexistent route | `/nonexistent.html` | **404** | 1 |

---

## Findings Table

| Sev | Finding | How Found | Suggested Fix |
|-----|---------|-----------|---------------|
| **P0** | **Invalid expedition/leg returns HTTP 500 with raw stack trace & filesystem path** | Navigated to `/?expedition=nonexistent&leg=freeform1` and `/?expedition=nonexistent&leg=nonexistent` | Return **404** (or 400) with a friendly "Expedition not found" page. Never expose server filesystem paths (`/home/jeremy/.local/state/...`) or Python tracebacks to the client. |
| **P0** | **"Guide" button is dead — references non-existent dialog** | Clicked "Guide" button in banner; inspected DOM for `id="guidePanel"` | The button has `aria-controls="guidePanel"` and `aria-haspopup="dialog"` but no element with `id="guidePanel"` exists. Either implement the guide dialog or remove the button / its ARIA attributes. |
| **P1** | **Spinbutton inputs accept out-of-range & inverted values silently** | Entered `faithMin=2.0` (valid range 0–1), then `faithMax=0.5` (min > max) via URL params | Page shows "0 / 50 images" with **no warning**. Add client-side validation: clamp to 0–1, show inline error when min > max, disable filter application until valid. |
| **P1** | **Empty search / filter results show only a count, no explanatory text** | Searched for `"nonexistentprompt"`; applied `faithMin=2.0` | UI reads "0 / 50 images" — a user cannot tell *why* results are empty. Show a brief message: "No images match your filters. Try widening the similarity range or clearing the search term." |
| **P1** | **Invalid expedition shows server filesystem path in error message** | Same as P0 above | The 500 page renders `FileNotFoundError: [Errno 2] No such file or directory: '/home/jeremy/.local/state/clawmarks/expeditions/nonexistent/...'`. Sanitize error messages; show generic "Expedition not found" instead. |
| **P2** | **Console error "Transition was skipped" on multiple pages** | Observed on main browse page, scan page, and others on load | Likely a View Transitions API race condition. Not user-visible but indicates fragile navigation code. Investigate and suppress or fix. |
| **P2** | **"Jump to another page" dropdown lists "Choose between two images" twice** | Opened dropdown in banner; counted options | Duplicate entry at positions 3 and 13. Remove the duplicate. |
| **P2** | **Inconsistent empty-state quality** | Compared `novelty_decay.html` (excellent: explains *why* empty, *what will populate it*) vs. main browse with filters (bare count) | Apply the `novelty_decay.html` pattern everywhere: state *what data is missing*, *why*, and *what action will fill it*. |
| **P2** | **Session status link in banner uses hard-coded expedition/leg** | Inspected "session status" link href on pages with different params | Link always points to `trent_v3_epoch4/freeform1` even when viewing a different expedition. Make it relative to current context. |
| **P2** | **No visible focus outline on some interactive elements (keyboard nav)** | Tabbed through banner buttons/links | The "Guide" button and expedition selector show `:focus-visible` but some custom buttons (e.g., cell buttons in coverage map) may lack it. Audit `:focus-visible` styles globally. |

---

## What Was Deliberately Skipped (Billable / Destructive)

- **Generate / Launch search / Send draft to queue / Retrain now buttons** — all labeled "Spends money" or imply GPU job starts. Not clicked.
- **Cockpit "Send draft to queue"** — would enqueue a generation batch.
- **Runs page "Back up and launch"** — would start an overnight search round.
- **Seeds page "Generate" button** — calls GPT-5.5 API (billable).
- **Preference pages "Retrain now"** — triggers model training.
- **Any form submission that POSTs to a write endpoint** — only GET navigation and safe input interactions were tested.

---

## Closing Notes

The app is structurally sound for its happy path: all legitimate pages load (200), navigation works, and several empty-state pages (`novelty_decay.html`, `lineage.html`, `preference_rank.html`) are models of good UX writing — they tell the user *what's missing, why, and what will change it*.

The critical flaws are **error handling** (500 instead of 404, stack traces leaked) and **one dead primary navigation control** (Guide button). The validation gaps on numeric filters are silent-failure UX bugs that will confuse users who mistype or misunderstand the 0–1 scale.

Fix the P0s first — they make the app look broken and leak internal paths. Then harden the numeric inputs and propagate the excellent empty-state pattern to the main browse page.

Status: DONE