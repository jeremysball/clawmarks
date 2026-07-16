# Error and Empty-State Legibility

_Design shard: error/empty-state UX in `src/clawmarks/curation_server.py`._

## What I Observed

**The live server** currently has the active leg (`uncanny_frontier`/`cockpit`) pointing at a
nonexistent `scored_manifest.json`. The `/` status page shows good structure but unhelpful
wording (see below). Every tool page (`/scan.html`, `/map.html`, `/redundancy.html`,
`/coverage.html`, `/novelty_decay.html`, `/lineage.html`, `/archive.html`,
`/preference_rank.html`) returns HTTP 500 with the same error page, which contains a misleading
hint. `/api/compare/next` returns clean JSON with `"no_manifest": true`.
`/api/scan_data.json` returns a bare Python `http.server` 404 page with no app styling.

All references are to `src/clawmarks/curation_server.py` at commit `f2bb89d` unless noted.

## Concrete Problems

### 1. `_send_error_page` gives the wrong diagnosis for a missing manifest file (line 933)

The hint on line 933-938 fires on **any** `FileNotFoundError` at all and says:

> This usually means `scored_manifest.json` still points at an old absolute path [...] and the image no longer lives there. Re-pointing or regenerating the manifest's `file` paths should fix it.

But when the manifest **file itself** is missing (the `FileNotFoundError` thrown by
`live_cache.py:25` doing `os.path.getmtime` on a path that resolves to a nonexistent file), this
hint is wrong. The manifest doesn't exist to be re-pointed. The user is told to fix contents of
a file that isn't on disk. The actual fix is either selecting a leg that has run, or launching a
round for this leg.

### 2. Startup validation prints a silent warning and keeps going (line 1969-1976)

`_check_manifest_images()` at server startup distinguishes two cases:

- **Manifest exists but images are missing** (line 1983-1993): fatal `sys.exit(1)` with a clear
  stderr message naming an example path and suggesting a leg switch.
- **Manifest doesn't exist at all** (line 1974-1976): prints a one-line stdout warning and
  continues. No stderr, no suggestion to pick another leg, no exit.

The result: the server starts up in a state where every tool page crashes, and the only clue in
the process output is a single `warning:` line to stdout that might scroll off screen during a
busy start. The two failure modes should be equally treated or at minimum named on stderr with
actionable advice.

### 3. Raw Python exceptions shown as user-facing status text (line 970-971 → line 1040)

When `load_manifest()` fails inside `_send_status_page()`, the exception string goes straight
into the page body:

```
could not read manifest: [Errno 2] No such file or directory: '/home/jeremy/.local/state/clawmarks/expeditions/uncanny_frontier/cockpit/scored_manifest.json'
```

This is a Python `FileNotFoundError` string, not a human-readable explanation. The page
*correctly* shows the expedition/leg picker right below it as the remedy, but the text reads
like a crash dump, not a status message. A user who skims past it to the picker might still
think the server is broken rather than understanding the active leg just needs changing.

### 4. Error pages omit route context

Every 500 is identical regardless of which tool page was requested. If a user opens
`/scan.html`, `/map.html`, and `/archive.html` in separate tabs, all three show the same page
with the same stack trace. There's no indication in the error body of which route triggered the
failure, which makes it harder to understand the scope (every page is down, not just
scan.html).

### 5. Inconsistent 404 styling (lines 1378, 1396, 1411, 1417)

`send_error(404, ...)` calls at the `/real/`, `/thumbs/`, and `/real_thumbs/` route guards, plus
the `super().do_GET()` fallthrough at line 1417 (which handles `/api/scan_data.json` 404s and
unmatched static files), all render Python's built-in `http.server` error page: a
light-background, unstyled HTML page that reads "Error response / Error code: 404 / Message:
File not found." This breaks visual consistency with the rest of the app's dark theme. The
`super().do_GET()` case never hits the app's error wrapper because
`SimpleHTTPRequestHandler.do_GET()` handles 404s inline without raising.

## Recommendations (Ranked by Impact)

### 1. Fix the `FileNotFoundError` hint to distinguish missing-file from stale-paths

In `_send_error_page` (line 930), split the `FileNotFoundError` hint into two cases:

- **File not found** (the path in the exception is the manifest itself, or the file in the
  exception string doesn't exist): tell the user the active leg has no scored manifest and point
  them to `/` to pick a leg that has completed a round, or to `/runs.html` to launch one.
- **Manifest exists but image files missing** (the path in the exception is an image under the
  out_dir): keep the current "re-point or regenerate" hint.

The check is a simple `os.path.exists` on the path from the exception string to determine which
branch to show. Without it, a missing-manifest failure presents advice about a file that isn't
there.

### 2. Make the empty-body status message human-readable

Replace the raw exception string at line 970-971 with a plain-sentence summary that names the
expedition and leg whose manifest couldn't be read:

```
uncanny_frontier/cockpit has no search data yet. Pick another leg that has completed a search
round, or launch a new round for this leg from /runs.html.
```

The exception text can go inside a `<details>` element (already the pattern from
`_send_error_page`) so the raw error is still available for debugging but doesn't dominate the
page.

### 3. Upgrade the missing-manifest startup check to match the stale-paths check

In `_check_manifest_images`, emit to stderr (not stdout) and include the same guidance: name the
affected leg and suggest switching to a leg with data or launching a round. Consider exiting
when no leg at all has a valid manifest (all legs are empty), but at least match the
`file=sys.stderr` severity of the stale-paths case.

### 4. Add the request path to the error page

One extra `<p>` in the error body template (line 940-949) with the route path costs nothing and
makes the page more informative when multiple tabs all show errors:

```
<p>Route: <code>/scan.html</code></p>
```

### 5. Route 404s through the app's styled error page

Override `send_error` in the Handler class (or replace the `send_error(...)` calls at lines
1378, 1396, 1411 with `_send_error_page` equivalents) and catch the `super().do_GET()`
fallthrough's 404 path. A 404 can use the same visual shell as the 500 page, just with a
different status code and a "nothing here" message instead of the stack trace.

---

*Reviewed: 2026-07-15 against live server at http://100.73.69.126:8420/ with active leg
uncanny_frontier/cockpit pointing at a nonexistent scored_manifest.json.*
