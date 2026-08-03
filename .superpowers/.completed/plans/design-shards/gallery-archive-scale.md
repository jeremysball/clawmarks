# Design shard: gallery/archive browsing at scale

Read-only UX shard of the 10-shard design pass. Scope `/scan.html` and
`/archive.html`, the two pages meant to browse hundreds of full-resolution generated
images. Both currently 500 in this environment (stale absolute path in
`scored_manifest.json` for the active leg, unrelated to this review), so the analysis
below is from the HTML-generating code: `src/clawmarks/build/scan_gallery.py`,
`src/clawmarks/build/elite_archive.py`, `src/clawmarks/build/thumbnails.py`,
`src/clawmarks/shared_ui.py` (the lightbox), and the `/thumbs/` route in
`curation_server.py:1390`.

## What I observed

**Thumbnailing** is shared and is the right shape. `generate_thumbnail`
(`build/thumbnails.py:18`) makes 220px JPEG q78, written atomically via
`os.replace`. `/thumbs/<tag>.jpg` is generated lazily on first request
(`curation_server.py:1390-1399`): missing file -> look up manifest entry -> generate
-> fall through to `SimpleHTTPRequestHandler`. The docstring at `thumbnails.py:3`
correctly notes a thumbnail never goes stale, so no invalidation problem.

**scan.html** (`scan_gallery.py`) already does the hard scale work:
- `renderMore()` (`scan_gallery.py:356`) chunks the grid at `PAGE_SIZE = 150`
  with a sentinel `IntersectionObserver` (`rootMargin: '600px'`) growing the grid
  as the user approaches the bottom, so a filter change repaints one page, not
  thousands. The inline comment at `:302-306` records that this *was* a real
  observed lag source ("up to 3672 `<img>` tags parsed/laid out at once"), so the
  fix is battle-tested, not theoretical.
- Each thumb carries `loading="lazy" decoding="async"` (`:349`), so off-grid
  thumbs the browser hasn't reached are not fetched.
- Filter/sort is generous for a solo tool: sort by novelty / faithfulness(asc|desc)
  / generation(newest|oldest) / prompt(A-Z|Z-A); filter by type (style/conflict),
  category (grid, negtrigger, truncated, allnight exploit/explore, r2
  exploit/explore), prompt name (populated from data), faithfulness numeric
  min/max, free-text prompt search, picked-only and favorited-only checkboxes.
  Numeric/text inputs are debounced 250ms (`:382`); others apply immediately.
- View Transitions API (`:314`) animates reordering on filter change.

**archive.html** (`elite_archive.py`) is the lighter touch: a fixed 4x4 grid of
the one elite per occupied cell, plus a per-cell "view all $n in this cell" button
(`:271`) that opens a modal listing every image in that cell (`:276-285`).

**lightbox.js** (in `shared_ui.py`, served at `/lightbox.js`) is shared by every
tool page. Its `wireThumbPrefetch()` (`shared_ui.py:621`) observes every
`img[data-tag]` on the page through a `MutationObserver` and, for any thumb inside
a 150px viewport margin, eagerly starts fetching the **full-resolution** 1-2.5MB
PNG; scrolling off-screen aborts. It runs unconditionally on every page that
includes the script.

## Concrete problems

1. **archive.html's "view all" modal renders the whole cell in one
   `innerHTML` write** (`elite_archive.py:279`). No chunking, no sentinel, no
   `IntersectionObserver`. scan.html's own comment says a few thousand imgs in
   one parse is "unusably slow"; the modal has the same shape with none of the
   mitigation. MAP-Elites by construction concentrates images in a few hot cells
   (exploit jobs push toward high-faithfulness/high-novelty bins), so a single
   cell quietly holding a few hundred images is the expected outcome, not an
   edge case. This is the page most likely to degrade first.

2. **No `Cache-Control` on `/thumbs/` or source-image responses.**
   `curation_server.py:1390-1417` falls through to `SimpleHTTPRequestHandler`,
   which sends no caching headers. On a reload mid-search (Jeremy's normal pattern
   during an overnight run), the browser re-issues conditional requests for every
   cached thumbnail and every full PNG the lightbox pre-fetched. Thumbnails literally
   never change (`thumbnails.py:4`), so these revalidations are pure overhead, and
   for a few thousand thumbs over a tailnet link they add up.

3. **`wireThumbPrefetch` eagerly fetches full PNGs for every visible thumb on
   every page**, not just scan.html. On a dense grid (scan.html growing toward
   thousands, or the unpaginated archive modal), `IntersectionObserver` firing
   for rows scrolling into a 150px margin means dozens of concurrent 1-2.5MB
   fetches starting and aborting as the user scrolls. The thumbnail is already a
   220px JPEG that conveys the image fine at grid scale; the full PNG only
   matters once a thumbnail is actually clicked. The lightbox already has
   `prefetchNeighbors()` (`shared_ui.py:419`) for the in-lightbox next/prev case,
   so `wireThumbPrefetch` is purely anticipatory, and its cost scales with the
   grid, not with intent.

4. **Filter/sort state is not in the URL.** scan.html rebuilds `view` from
   `DATA` purely from in-DOM control state on every reload, so a carefully-set
   filter combo (faith 0.6-0.8, r2_explore only, novelty-desc) is lost the moment
   Jeremy reloads during a long session or closes the tab overnight. For a tool
   explicitly used "across long/overnight sessions," that is a recurring cost with
   a cheap fix.

5. **"Generation (newest first)" sort conflates rounds.** `generation_of`
   (`scan_gallery.py:23`) parses `gen<N>_` off the tag and ignores the
   `r2_` prefix, so `r2_gen3_` and `gen3_` sort as equal. As the search accrues
   expedition/leg rounds, "newest first" stops meaning newest.

## Recommendations, ranked by impact

1. **Paginate the archive "view all" modal the same way scan.html does**, or cap
   it. Cheapest version: in `openModal` (`elite_archive.py:276`), render only the
   first ~150 items and add the same sentinel + `IntersectionObserver` pattern
   to append more. Slightly more work but higher payoff: cap at, say, 200 and
   surface a "showing 200 of $n, load all" button, since a cell with 600 images
   is reviewable as a scan but rarely as a one-shot wall. Highest-impact, since
   this is the failing-shape page and the fix already exists to copy.

2. **Send `Cache-Control: public, max-age=31536000, immutable` on `/thumbs/`
   and `/real_thumbs/` responses** in `curation_server.py` before the fall-through
   to `super().do_GET()`, and the same for any served `.png`/`.jpg` under the
   active leg dir. Thumbnails are immutable by design; full-res generation
   outputs are never overwritten. One route block, effect on every reload.

3. **Gate `wireThumbPrefetch` behind a narrower trigger.** Two cheap options:
   (a) only prefetch full PNGs for thumbs that have been *hovered* ~150ms (desktop)
   or *focused* (keyboard), keeping the immediate-click benefit without the
   scroll-storm; (b) rise the `rootMargin` from 150px to something tiny like
   0px so only thumbs actually in the viewport prefetch. Either keeps the
   "lightbox opens instantly when you click" win from `shared_ui.py:612-620`
   while cutting the bandwidth on dense grids to near-zero.

4. **Persist scan.html filter/sort/edit state in `URLSearchParams` and restore
   on load.** The page already has `applyFilters()` as a single chokepoint; route
   each control's change through a `history.replaceState` and a `popstate`
   handler. This is the single biggest usability win for the overnight-session
   workflow and touches one file.

5. **Add a sort key that respects round before generation**, e.g.
   `generation_of` returning a tuple `(round, gen)`. One regex change in
   `scan_gallery.py:23-25`; makes "newest first" mean newest again as expeditions
   accrue.

6. **Optional, low priority: surface per-category counts** in the `<select>`
   option labels (`<option value="r2_explore">round2 explore (412)</option>`).
   Helps Jeremy decide where the next search run should focus, which is the
   page's actual purpose, and costs a one-time `DATA.reduce` at populate time.

No framework migration or redesign recommended: the per-route build-and-inject
model is fine for a solo user, scan.html's chunked-`IntersectionObserver` pattern
is the right scaling primitive, and all six recommendations above are local
edits to two files (`elite_archive.py`, `scan_gallery.py`) plus one route block
in `curation_server.py`. The current approach is not broken; it is one modal
and one cache header away from holding at several thousand images per leg.