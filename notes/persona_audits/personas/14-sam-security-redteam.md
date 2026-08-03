# Sam (passive security/info-exposure audit)

Task ID: `oc_mrr90lje_eb6756f7`
Model: `opencode/deepseek-v4-flash-free`
New persona for this batch — not adversarial-destructive, a passive read-only audit of what the
app leaks to any visitor who has just the URL, ahead of sharing it more widely.

## Report

Walkthrough complete. Here's what I found as Sam:

### Information exposed to any visitor with the URL

- **Username + filesystem structure** on `/status.html`: `sweep dir:
  /home/jeremy/.local/state/clawmarks/expeditions/trent_v3_epoch4/freeform1`. Confirmed the
  known candidate — full absolute path, real username, project naming conventions all visible to
  anyone who clicks "session status" in the nav bar.
- **RunPod dollar balance** in `/api/searchrun/report`: `start_balance: 9.9087646347`. The
  account balance (accurate to 7 decimal places) from when this leg launched is returned
  unprotected and visible in network responses.
- **Server/Python version** in every response header: `server: SimpleHTTP/0.6 Python/3.14.6`.
  Version info that helps an attacker narrow their exploit surface.
- **Python module paths** visible in UI: `python -m clawmarks.search.preference_pairwise_model`
  appears on `/preference_status.html` as the command to run manually.
- **Internal project naming** fully exposed: three expeditions (`demo`, `trent_v3_epoch4`,
  `uncanny_frontier`) and all their legs, category names like `allnight`, `round2 exploit`,
  `negtrigger`, `truncated` — reveals the full experiment taxonomy.
- **Generation seeds**: every thumbnail filename in the scan page encodes the random seed
  (`gen1_explore_32_seed947694`). Exposing seeds for a generative model is a
  reproducibility/copyright-assertion concern if the model is identifiable.
- **All internal API endpoints** return JSON with no auth: `/api/expeditions`,
  `/api/active-leg`, `/api/searchrun/report`, `/api/favorites`, `/api/preference_status`,
  `/api/seeds`, `/api/cockpit/queue`, `/api/cockpit/target_cells`, `/scan_data.json`.

### What's already appropriately gated or hidden

- 404 page is clean — "Nothing here" with the route name, no stack trace, no filesystem paths,
  no debug info.
- No `.env`, `.git`, or config-file leakage — tried common paths, all return 404 or 403 cleanly.
- No console-log or network-response leakage of API keys, tokens, or credentials.
- Images themselves are served with descriptive alt text, not debug IDs.
- The "Spends money" labeling on billable controls is clear and visible, even though there's no
  auth gate preventing their use.

### What I'd fix before sharing the URL

Remove the filesystem path from `/status.html` — show just the relative path or hide it from
non-local viewers. Strip `start_balance` from the search-run report API (an unrelated visitor
doesn't need to know your RunPod wallet balance). Consider suppressing the `Server` header or
generalizing it past the Python micro-version. And the biggest one: add even a basic auth layer
(a shared secret, a cookie, or a Tailscale ACL) before putting this behind any URL a stranger
could find. The app is charming and the tools are powerful, but right now anyone who stumbles on
it can browse every expedition, read every seed, and press every "Spends money" button.

Status: DONE

## Notes

This corroborates and sharpens the filesystem-path leak on `/status.html` already flagged by
Priya's original report (see cross-cutting findings in [README.md](README.md)), and surfaces two
new findings no prior persona reported: the unauthenticated RunPod balance exposure in
`/api/searchrun/report`, and the complete absence of any auth layer on every API endpoint —
meaning any billable control ("Spends money" badge notwithstanding) is reachable and clickable by
anyone with the URL, not just anyone who navigates the UI.
