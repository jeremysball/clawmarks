# CLAWMARKS complete issue list

Consolidated from all 24 persona audits (`.personas/README.md`) plus the 2026-07-19 second wave:
Nadia (active security probing), Oren (structural/error-state audit), Femi (reproducibility
audit), Grace (blind art-judgment), and Diego (mobile-viewport sweep, compiled from captured
screenshots after the worker crashed four times in a row — see "Diego's sweep" note below).

**Deployment context that changes severity**: this app has no auth layer by design — it runs
locally or over a private VPN/tailnet, not on the open internet. Findings that assume a public,
untrusted-user threat model (CSRF tokens, rate limiting, generic auth-required-here findings) are
downgraded from "must fix" to "optional hardening." Findings that are true regardless of the
network boundary — anyone who reaches the tailnet URL can already see them — are NOT downgraded:
filesystem path leaks, the RunPod balance leak, stored XSS, and inconsistent input validation all
stand on their own.

## P0 — fix regardless of deployment model

| Issue | Found by | Fix |
|---|---|---|
| Invalid `expedition`/`leg` params return a raw HTTP 500 with a Python traceback and the real filesystem path (`/home/jeremy/.local/state/clawmarks/expeditions/...`) | Oren, corroborated by Nadia's injection testing on `/api/cockpit/target_cells` | Catch the filesystem error, return 404 with a plain "expedition not found" message, log the real path server-side only |
| `/api/searchrun/report` leaks the live RunPod dollar balance; `status.html` leaks the real filesystem path and username | Sam (original security audit), corroborated by Priyanka and Femi | Strip the balance field from the API response; stop rendering absolute paths in user-facing HTML |
| Search-run records capture none of: random seed, sampler, step count, CFG scale, strength schedule, prompt pool, or search bounds — a result cannot be reproduced from the UI alone | Femi (reproducibility audit) | Persist and display the full search configuration with each run |
| No LoRA/checkpoint identity recorded per run — only the informal expedition name hints at which model produced it | Femi | Add a `Model checkpoint` field (base model, epoch, training recipe ID) to the run report |
| No timestamp or code/git-commit version recorded per run | Femi | Record `started_at`, `finished_at`, driver git commit, dependency versions |
| Stored XSS: `POST /api/cockpit/queue`'s `prompt` field and `POST /api/compare`'s `winner`/`loser` fields accept and persist raw `<script>` payloads unsanitized at ingestion (currently mitigated only by `escapeHtml()` at render time — a future unescaped consumer would be vulnerable) | Nadia | Sanitize/reject HTML at ingestion; keep the render-time escaping as defense in depth |
| "Guide" button has `aria-controls="guidePanel"` but no such element exists — it's not just visually inert, it's structurally broken (dead ARIA reference) | Oren, corroborated by Priyanka | Implement the guide dialog or remove the button and its ARIA attributes |

## P1 — fix, but not urgent given local/VPN deployment

| Issue | Found by | Fix |
|---|---|---|
| No auth or CSRF token on any state-mutating endpoint (`/api/cockpit/queue`, `/api/compare`) | Nadia (active probing), Sam (original passive audit) | Downgraded per deployment context — add a shared-secret or tailnet ACL gate only if the app is ever exposed beyond the current VPN boundary |
| IDOR: any `expedition`/`leg` value is reachable by direct URL/param guess, not scoped to what a user navigated to through the UI | Nadia | Same as above — a network-boundary control (tailnet ACL), not an app-layer fix, given the deployment model |
| Missing security headers (CSP, X-Frame-Options, X-Content-Type-Options, etc.) on all responses | Nadia | Low-cost to add regardless; do if convenient |
| "Elite"/"Best" labels mean highest-novelty-per-cell, not aesthetic quality | Viktor (both rounds), Dr. Vasquez, Rae, Priya | Relabel to "most novel in cell" or similar |
| Several billable buttons ("Send draft to queue," "Retrain now," "generate counterfactual") carry no cost warning, unlike "Launch search" and "Generate" | Walt, Dana, Jordan, Priya, Priyanka | Apply the existing "Spends money" badge pattern to every billable control |
| Gallery thumbnails are keyboard-unreachable and have no alt text | Dana, Jordan | Make thumbnails focusable buttons; add alt text |
| Image lightbox omits full generation recipe (full prompt, negative prompt, sampler, steps, dimensions, checkpoint) even though the underlying page JS already has this data | Femi | Surface the full recipe in the lightbox UI |
| No training-dataset version surfaced anywhere (solution map names 31 real training images but no dataset ID/hash) | Femi | Add a `Training dataset` field to the run report and context picker |
| No DINOv2 model/checkpoint version documented anywhere in the UI | Femi | Record the exact checkpoint (e.g. `facebook/dinov2-large`) used for scoring, so future scorer updates don't silently break score comparability |
| No image lineage/parent_tag recorded for exploit images | Femi | Store `parent_tag` and mutation params per image |
| Spinbutton filter inputs (faithfulness min/max) silently accept out-of-range or inverted (min > max) values, producing "0 / 50 images" with no explanation | Oren | Clamp to valid range client-side; show an inline error on min > max |
| Empty search/filter results show only a bare count, no explanation of why | Oren | Add contextual empty-state text: "No images match your filters. Try widening the range or clearing your search term." |

## P2 — polish

| Issue | Found by | Fix |
|---|---|---|
| Orange/green used as the only signal for type/category (the most common red-green colorblindness collision) | Ines | Add a redundant icon or text label |
| Duplicate "Choose between two images" entry in the nav dropdown | Priyanka, Oren | Delete the duplicate `<option>` |
| Nav dropdown label, top-bar label, and on-page `<h1>` use three different names for the same page | Priyanka | Pick one name per page |
| Metric definitions (faithfulness/novelty formulas) live only in transient tooltips, no linked methods doc, no warning that a scorer-version change would break score comparability | Femi | Add a "Methods" page defining both metrics and the versioning risk |
| Console error "Transition was skipped" fires on multiple page loads (main browse, scan gallery) | Oren | Investigate View Transitions API race condition |
| "session status" banner link is hard-coded to `trent_v3_epoch4/freeform1` regardless of which expedition/leg is actually being viewed | Oren | Make the link relative to current context |
| Inconsistent input validation: `/api/searchrun/report` and `/api/cockpit/*` reject path traversal, `/api/searchrun/status` silently ignores bad input | Nadia | Centralize expedition/leg validation in one helper used by all endpoints |
| Inconsistent error response formats across endpoints — some JSON `{"error": ...}`, some raw HTML `<h1>`, some silent `{}` | Nadia, Oren | Standardize on one error envelope |
| Server header leaks Python version (`SimpleHTTP/0.6 Python/3.14.6`) | Nadia | Genericize the `Server` header |
| No rate limiting on any mutating endpoint | Nadia | Optional given deployment model; add if ever exposed more broadly |

## Resolved / false alarm

- **Marcus's "all 14 info popovers stuck on 'loading expeditions...' forever" claim** — checked
  directly against `shared_ui.py`. That string belongs to the unrelated "switch research context"
  dialog, not the `.infobtn` popovers, which build content synchronously from an already-present
  `data-tip` attribute with no fetch call at all. No fix needed; other personas' popover-content
  claims stand.

## Research finding, not a bug

**Grace's blind art-judgment exercise is the second independent data point (after Viktor's vision
redo) that `faithfulness` and `novelty` don't track perceived art quality.** Picking blind, her top
5 favorites were scattered across both sorts — her two strongest picks ranked near the bottom on
faithfulness, and her weakest novelty pick ranked highest on faithfulness. What her picks actually
shared was "emotional specificity," something neither metric measures. This corroborates Viktor's
earlier finding (his top pick scored novelty 0.6002 / faithfulness 0.4206, both mid-rank) and
strengthens the paper's core claim: these metrics measure real properties (distributional distance,
resemblance to real art) but neither is a quality score, and the app's "Elite"/"Best" labeling
(see P1 above) currently implies otherwise.

## Diego's mobile-viewport sweep (375x667)

Diego's worker (`opencode/mimo-v2.5-free`) crashed four times in a row across this one persona
(two API-level crashes from context bloat after repeated screenshots, two silent watchdog kills
with no error logged) and never produced a written final report. Its fourth and last attempt
logged zero bytes before dying — by that point the shared `taskferry` CLI itself had gone down
workspace-wide (see note below), so a fifth attempt wasn't possible. The findings below are
compiled directly from the ~30 screenshots the worker actually captured across its four attempts,
reviewed by hand, rather than from a worker-written report.

| Severity | Page | Problem | Fix |
|---|---|---|---|
| P1 | Generation cockpit (workbench) | "Choose a target coverage cell" renders as a horizontal row of fixed-width cards; the second and later cards are cut off at the right edge with no scroll affordance visible, so cells beyond the first are effectively hidden at this width | Switch to a horizontally-scrollable carousel with a visible scroll hint, or stack cards vertically below ~480px |
| P1 | Generation cockpit (workbench) | The "What are you testing?" / "Target coverage cell" two-column form and its follow-up "Seed strategy" / "Batch size" / "LoRA strength" row don't collapse to one column on mobile — input values are clipped mid-word (e.g. "Test whether t", "Faithfulness 0") | Stack form fields to a single column below a mobile breakpoint |
| P2 | Generation cockpit (workbench) | Bottom tab bar ("Trial record / Queue 2 / Results / Autopilot / show queue") is cramped into 5 items at this width; "Queue 2" and "show queue" wrap awkwardly and touch targets look tight | Reduce to icons + labels, or move to a scrollable tab strip |
| — (corroborates existing P0) | Predicted preference page, session status page | Both surface the raw filesystem path (`/home/jeremy/.local/state/clawmarks/expeditions/...`) directly in the page body, same leak as the P0 path-leak finding above — confirmed this isn't desktop-only, it's the same server-rendered text at any viewport | Same fix as the existing P0 entry |

Pages confirmed well-adapted to mobile, no fix needed: main browse (grid collapses cleanly to two
columns), lightbox (image, metadata, and similar-images strip all readable, though the prev/next
nav arrows are borderline for a 44px touch target and worth a follow-up measurement), compare
(stacks the two images vertically with a clear "OR" divider), search runs (report table collapses
to clean key-value rows), solution map (UMAP scatterplot and its legend both fit and stay
tappable), coverage/void map (grid cells scale down and stay legible), redundancy clusters,
novelty decay watchlist, lineage tree, candidate seeds, and elite archive (image grid, no
overflow).

Nothing billable or destructive was triggered while capturing these screenshots (no "Generate,"
"Launch search," "Send draft to queue," or similar buttons were clicked).

**Why the report is worker-assembled rather than persona-written**: this is the one persona in
the whole round where the underlying `taskferry` tooling itself failed, not just the worker model.
The CLI broke workspace-wide (`error: Unexpected token '<<'` on every command, including
`--version`) because of an unresolved `git stash` conflict left in `/workspace/taskferry/src/client.js`
by an unrelated concurrent session on a different branch (`chore/dry-cleanup-redteam-findings`) —
not something to fix from this worktree. Diego's fourth dispatch died before that CLI outage was
even diagnosed, so redispatching wasn't an option; the findings above were pulled straight from
the screenshot files on disk instead.
