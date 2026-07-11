# scan.html grid: smooth reflow on filter/sort/favorite changes

## Problem

`scan.html`'s grid rebuilds instantly on every filter change, sort change, or favorite toggle:
`render()` clears `#grid` and re-inserts the surviving thumbnails with no transition. Cards
snap into their new positions with no visual continuity, which reads as static and makes it
hard to track where a given image went when the result set changes.

## Approach

Use the browser's View Transitions API (`document.startViewTransition`). Each thumbnail gets a
stable `view-transition-name` derived from its image tag. Wrapping a DOM update in
`document.startViewTransition(() => { ...update... })` makes the browser automatically animate
every element whose `view-transition-name` exists in both the old and new DOM state sliding
from its old position to its new one; elements that disappear fade out, elements that appear
fade in. No manual bounding-box math.

Feature-detect: if `document.startViewTransition` doesn't exist (an older browser), fall back to
calling the update function directly, which reproduces today's instant-snap behavior exactly.
This is a personal internal tool, so a Chromium/Safari-only enhancement with a plain fallback is
an acceptable trade for the much smaller implementation.

## Scope

Only the two call sites that fully rebuild the grid get wrapped:

- `applyFilters()`'s call to `render()` (fires on every filter/sort control change).
- The `lightbox:favorite` listener's call to `render()` (fires when a favorite is toggled from
  the lightbox while scan.html is open behind it).

The scroll-triggered incremental append (`renderMore()`, called by the `IntersectionObserver`
sentinel as the user scrolls near the bottom) is explicitly NOT wrapped. Animating up to 150
newly-appended cards at once as the user scrolls would look like a jarring cascade, not a smooth
reflow, and risks visible jank on the transition capture. Plain instant append (today's
behavior) stays for that path. Thumbnails created during a scroll append still get a
`view-transition-name`, so if a later filter change removes/reorders them, they participate
correctly in that transition.

## Implementation sketch

```js
function withViewTransition(fn) {
  if (document.startViewTransition) document.startViewTransition(fn);
  else fn();
}
```

`thumbHtml(d, i)` sets `style="view-transition-name: vt-${d.tag}"` on the `.thumb` div (image
tags are filename-derived, already safe as CSS identifiers after replacing any character outside
`[a-zA-Z0-9_-]` with `_`, matching the sanitization pattern used elsewhere for DOM ids).

`applyFilters()`'s last line changes from `render();` to `withViewTransition(render);`. The
`lightbox:favorite` listener's `render();` call changes the same way.

## Out of scope

- No change to `renderMore()`'s behavior.
- No change to any other tool page (archive.html, coverage.html, etc.). This is scoped to
  `scan.html`'s grid specifically, per the reported issue.
- No custom transition duration/easing CSS; the browser's default `::view-transition-group(*)`
  timing (250ms ease) is used as-is unless it looks wrong in verification, in which case a short
  `::view-transition-group(*) { animation-duration: 0.2s; }` rule can be added to match the
  rest of the page's existing `.12s`/`.15s` transition speeds.

## Testing

This is a pure client-side visual behavior with no server-side surface, so there's no meaningful
unit test to write. Verification is a live Playwright check: open scan.html, change a filter
that removes some cards, and confirm (a) the page doesn't error, (b) `document.startViewTransition`
was actually invoked (spy/monkeypatch it during the check), and (c) the resulting DOM after the
transition matches what `render()` would have produced directly.
