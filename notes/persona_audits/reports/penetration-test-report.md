# Penetration Test Report: CLAWMARKS Curation App
**Tester:** Nadia Reyes (Application Security Tester)  
**Target:** http://100.73.69.126:8420/ (CLAWMARKS curation app for LoRA hyperparameter search)  
**Scope:** Authorized read-only-outcome testing; no GPU job triggers, no destructive writes  
**Date:** 2026-07-19  

---

## Executive Summary

Tested the CLAWMARKS curation application for input validation, access control, and security header gaps. The app runs on Python's `SimpleHTTP/0.6` with no authentication layer (confirmed by prior audit). This assessment focused on active probing of API endpoints with malformed/boundary inputs, IDOR checks, CSRF exposure, and error handling.

**Key findings:** 1 P0 (critical), 3 P1 (high), 3 P2 (medium), plus several defense-in-depth observations.

---

## Findings Table

| Sev | Finding | Endpoint / Parameter | How Found | Suggested Fix |
|-----|---------|---------------------|-----------|---------------|
| **P0** | **Unauthenticated state-changing POST endpoints (CSRF + no auth)** | `POST /api/cockpit/queue` — creates queued GPU trials<br>`POST /api/compare` — records preference comparisons | Both accept JSON POSTs with no CSRF token, no auth check, no confirmation. `curl -X POST -H 'Content-Type: application/json' -d '{"expedition":"trent_v3_epoch4","leg":"freeform1",...}' http://100.73.69.126:8420/api/cockpit/queue` returns `{"ok":true,"id":"trial_..."}` and the trial appears in `/api/cockpit/queue`. `/api/compare` similarly accepts `winner`/`loser` and increments comparison count. | Add per-session CSRF tokens to all mutating endpoints. Require authentication/authorization before any state change. For `/api/cockpit/queue`, keep the "review and run" confirmation gate but also protect the *queue* operation itself. |
| **P1** | **IDOR — cross-expedition data access via guessable `expedition`/`leg` params** | All `/api/*` endpoints accepting `expedition` and `leg` query params (e.g., `/api/searchrun/report`, `/api/cockpit/target_cells`, `/api/preference_status`, `/api/cockpit/queue`, `/api/compare/next`) | Enumerated valid expeditions via `GET /api/expeditions` → `["demo","trent_v3_epoch4","uncanny_frontier"]`. Accessed `uncanny_frontier/round1` and `round2` data without ever navigating there via UI. `/api/searchrun/report?expedition=uncanny_frontier&leg=round1` returns valid JSON. | Treat `expedition`/`leg` as authorization boundaries, not just filters. Require session-scoped context or validate that the requesting user has access to the requested expedition. |
| **P1** | **Filesystem path disclosure in error messages** | `/api/cockpit/target_cells`, `/api/compare`, `/api/searchrun/report` | Injecting `expedition=trent_v3_epoch4'OR'1'='1` into `/api/cockpit/target_cells` returns 500 with body: `{"error":"FileNotFoundError: [Errno 2] No such file or directory: \"/home/jeremy/.local/state/clawmarks/expeditions/trent_v3_epoch4'OR'1'='1/freeform1/scored_manifest.json\"","no_manifest":true}`. Same pattern leaks `/home/jeremy/...` paths on other endpoints. | Catch filesystem errors and return generic messages (e.g., "expedition not found"). Never reflect user input in error paths. Log full details server-side only. |
| **P1** | **Missing security headers across all responses** | All endpoints (`/`, `/scan.html`, `/api/*`, etc.) | Response headers show only `Content-Type`, `Content-Length`, `Date`, `Server: SimpleHTTP/0.6 Python/3.14.6`. No `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`. | Add a middleware/handler wrapper that injects: `CSP: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:;`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`. |
| **P2** | **Stored XSS via `prompt` field in `/api/cockpit/queue`** | `POST /api/cockpit/queue` → `prompt` field | Submitted `prompt: "<script>alert(1)</script>"`; persisted and returned in `/api/cockpit/queue` JSON. The cockpit UI renders queue items via `escapeHtml()` in `renderQueue()`, so currently mitigated in-browser, but the API stores raw HTML. If any future consumer renders unsafed, XSS fires. | Sanitize or reject HTML in `prompt` at ingestion. Keep `escapeHtml()` at render time as defense in depth. |
| **P2** | **Reflected XSS vector in `/api/compare` `winner`/`loser` fields** | `POST /api/compare` → `winner`, `loser` fields | Submitted `winner: "<script>alert(1)</script>"` — accepted and stored (returns `{"ok":true,"count":9}`). Not currently reflected in any HTML response, but stored in comparison log. | Validate `winner`/`loser` against known image tag format (`gen\d+_\w+_\d+`). Reject non-matching values. |
| **P2** | **Inconsistent input validation — path traversal blocked in some endpoints, not others** | `/api/searchrun/status` vs `/api/searchrun/report`, `/api/cockpit/*` | `/api/searchrun/report` and `/api/cockpit/*` reject `../` and `..` in `expedition`/`leg` with 400. `/api/searchrun/status` silently ignores invalid values and returns `{"running":false}`. | Centralize expedition/leg validation in one helper used by all endpoints. Reject unknown expeditions uniformly. |
| **P2** | **Verbose server header leaks Python version** | All responses | `Server: SimpleHTTP/0.6 Python/3.14.6` | Suppress or genericize the `Server` header (e.g., `Server: clawmarks`). |
| **Info** | **No rate limiting on any endpoint** | All `/api/*` | Can POST `/api/cockpit/queue` or `/api/compare` repeatedly without delay. | Add per-IP/per-session rate limits on mutating endpoints. |
| **Info** | **`/api/seeds` returns empty object for valid expedition; no error for invalid** | `GET /api/seeds?expedition=trent_v3_epoch4&leg=freeform1` → `{}` | Returns `{}` for valid context; also `{}` for invalid expedition. No signal to caller. | Return 404 or structured error for unknown expedition/leg. |

---

## Endpoints Enumerated & Tested

| Endpoint | Method | Params Tested | Auth? | CSRF? | Notes |
|----------|--------|---------------|-------|-------|-------|
| `/api/searchrun/report` | GET | `expedition`, `leg` (path traversal, SQLi, XSS, null byte) | ❌ | N/A | Leaks RunPod balance (known); validates `expedition`/`leg` strictly |
| `/api/searchrun/status` | GET | `expedition`, `leg` (path traversal, SQLi) | ❌ | N/A | **No validation** — returns `{"running":false}` for any input |
| `/api/expeditions` | GET | — | ❌ | N/A | Lists all expeditions — enables IDOR reconnaissance |
| `/api/cockpit/target_cells` | GET | `expedition`, `leg` (path traversal, SQLi, XSS) | ❌ | N/A | **500 + path leak** on `expedition=...'OR'1'='1` |
| `/api/cockpit/queue` | GET | `expedition`, `leg` | ❌ | N/A | Returns trial queue |
| `/api/cockpit/queue` | POST | `expedition`, `leg`, `prompt`, `mission`, `n`, `strength`, `sampler`, `steps`, `cfg`, `negative`, `seed_strategy`, `hypothesis`, `target`, `target_cell`, `focus_id` | ❌ | ❌ | **Creates queued trials** — no auth, no CSRF, stores XSS payloads |
| `/api/cockpit/queue/{id}/run` | POST | `expedition`, `leg` | ❌ | ❌ | **Triggers GPU job** — **NOT TESTED** (billable) |
| `/api/cockpit/evidence` | GET | `prompt`, `cell` (SQLi, XSS, path traversal) | ❌ | N/A | Treats all as search terms; no injection |
| `/api/cockpit/autopilot` | POST | `expedition`, `leg`, `focus_id` | ❌ | ❌ | Times out (likely calls LLM) — **NOT FULLY TESTED** |
| `/api/compare/next` | GET | `expedition`, `leg` | ❌ | N/A | Returns next image pair for comparison |
| `/api/compare` | POST | `winner`, `loser`, `expedition`, `leg` | ❌ | ❌ | **Records comparison** — no auth, no CSRF, accepts XSS payloads |
| `/api/preference_status` | GET | `expedition`, `leg` | ❌ | N/A | Returns model status |
| `/api/favorites` | GET/POST | `expedition`, `leg`, `tag` | ❌ | ❌ | POST returns `{"error":"unknown endpoint"}` |
| `/api/seeds` | GET | `expedition`, `leg` | ❌ | N/A | Returns `{}` |
| `/scan_data.json` | GET | — | ❌ | N/A | Static JSON manifest (50 images) |
| `/thumbs/...` | GET | — | ❌ | N/A | Static thumbnails |

---

## Deliberately Not Tested (Billable / Destructive)

| Endpoint / Action | Reason |
|-------------------|--------|
| `POST /api/cockpit/queue/{id}/run` | Label says "Review and run" with cost badge "Spends money" — triggers RunPod GPU job |
| "Launch search" / "Run or monitor a search" (`/runs.html`) | Starts hyperparameter search rounds — bills GPU time |
| "Retrain now" / preference model training | Triggers model training on RunPod |
| `POST /api/cockpit/autopilot` (full test) | Timed out; may invoke LLM API with cost |
| Any `DELETE` / destructive write | No `DELETE` handlers found (501 on `/api/cockpit/queue/{id}`), but not probed further |

All were identified via UI labels ("Spends money", "billable-action" CSS class, "Launch search") and skipped per rules of engagement.

---

## Usability / Design Observations (Secondary)

- **Broken "session status" link on root page** when no query params present — `href="/status.html?expedition=&leg="` leads to empty context page.
- **Inconsistent error formats** — some endpoints return `{"error":"..."}`, others return HTML error pages (`<h1>Invalid workspace context</h1>`), others return empty objects `{}`.
- **No loading/error states** on `/api/cockpit/autopilot` — UI shows "this can take a minute" but no timeout handling visible.
- **Keyboard navigation** on compare page is solid (ArrowLeft/Right, Enter/Space) — good accessibility baseline.

---

## Recommended Priority Order

1. **P0** — Add CSRF tokens + auth gate to `/api/cockpit/queue` (POST) and `/api/compare` (POST)
2. **P1** — Centralize expedition/leg validation; enforce authorization checks
3. **P1** — Sanitize error responses; strip filesystem paths
4. **P1** — Deploy security headers middleware
5. **P2** — Input sanitization on `prompt`, `winner`, `loser` fields
6. **P2** — Rate limiting on mutating endpoints
7. **Info** — Genericize `Server` header; standardize error envelope

---

## Closing Note

This test covered active input validation, IDOR, CSRF, and header hygiene against a live research tool with real GPU billing behind certain buttons. The most impactful findings are the **unauthenticated state-changing endpoints** (P0) and **cross-expedition data access** (P1), both of which stem from the absence of any authentication/authorization layer — a known baseline gap from the prior audit. The path-disclosure errors and missing security headers are straightforward hardening steps.

**Status: DONE**