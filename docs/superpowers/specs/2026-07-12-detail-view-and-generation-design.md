# Unified detail view, real-image viewing, and thumb-then-full-res loading

Design only, not an implementation plan. Covers three of the continuation prompt's outstanding
items together because they're one underlying UI investment, not three separate features:

- the original item 5, "plan a unified image-detail + generate-around UI"
- task 11, "UMAP map: view the full real reference image, not just the thumb-in-panel"
- task 12, "design a thumb-then-full-res image swap API generalized across the map/scan/archive
  tools"

## What already exists (verified in code, not assumed from memory)

A shared Lightbox component (`shared_ui.py`, served as `/lightbox.js`) already provides a linked
image-detail modal with a built-in generate-around panel. `Lightbox.open(tag)` is already wired
into seven of the eleven tool pages: `scan.html`, `map.html`, `archive.html`,
`preference_rank.html`, `redundancy.html`, `lineage.html`, `coverage.html`. Opening an image
shows it full-size, a similarity strip of nearby images (click to jump between them without
closing the modal), a favorite toggle, and a "generate counterfactual" panel that posts to
`POST /api/counterfactual` and appends the result to a small strip of past variations for that
image.

So the "unified detail + generate-around UI" item is mostly built already, not a blank-slate
design. What's actually missing is narrower:

1. **`compare.html` has no detail/generate-around access at all.** Its two panes are plain
   `<img>` tags with click-to-vote handlers; there's no way to inspect an image full-size or spin
   off a variation from a comparison pane the way every other tool page allows.
2. **`/api/counterfactual` generates exactly one variation per request.** Getting several
   requires clicking "Generate" repeatedly by hand, re-entering a new seed each time.
3. **No image anywhere loads thumb-first-then-swaps-to-full-res.** The Lightbox's main image
   (`shared_ui.py:373`, `mainImg.src = d.file`) sets the full-resolution `file` path directly and
   shows a CSS loading spinner until it arrives; there is no progressive thumb-then-full stage.
   The new `/real/<name>` route added this session for the map's nearest-real-image panel has the
   same gap in a sharper form: it serves the real training photo at full resolution on every
   hover, with no thumbnail variant at all, so task 11's "view the full real reference image"
   request is really asking for the enlarge step of a pattern that doesn't exist yet for real
   images in any size.

## Gap 1: bring compare.html into the shared Lightbox

Each pane already has a `data-tag`-bearing image and a "click side to vote" gesture (`.pane`
`onclick`, see `compare_page.py`). Making the whole pane open the Lightbox would collide with
that primary gesture, so the plan is a small expand affordance instead: a corner icon button per
pane (`.pane-expand`, positioned top-right like the existing favorite icon on other pages) that
calls `Lightbox.open(tag)` without triggering the pane's vote handler
(`event.stopPropagation()`). The Lightbox already knows how to render generate-around and
similarity-strip UI for any tag in `scan_data.json`, so no new modal code is needed on the
compare side, just the entry point.

Open question for whoever implements this: should generating a counterfactual from inside a
live comparison affect that comparison in any way (e.g., offer the new variation as a fresh pair
next round), or stay purely a side "what if" tool the way it already is everywhere else? Leaning
toward "stays a side tool, no special-casing" for consistency, but flagging it since compare.html
is the one page where an image on screen is mid-decision rather than already-scored.

## Gap 2: N-variation generation

Extend `POST /api/counterfactual` to accept an optional `n` (default 1, capped at 6 server-side
to bound RunPod spend from one click). The existing single-job loop in
`_handle_counterfactual` (`curation_server.py:705-780`) already does one balance check, builds
one workflow, submits, and polls to completion; for `n > 1` it repeats that submit-and-poll
sequence `n` times reusing the same balance check (checking once up front, not once per job,
since the floor is a "don't start a batch this account can't afford" guard, not a
per-job re-check), giving each job its own random seed unless the caller pinned one, and returns
a list of records instead of one:

```python
seeds = [seed] if payload.get("seed") else [random.randint(1, 999999) for _ in range(n)]
records = []
for s in seeds:
    wf = build_workflow(prompt, s, strength, cfg, steps, sampler, negative)
    # ...submit, poll, save, append to records...
self._json_response(200, {"ok": True, "results": records})
```

Client-side, the `lb-cf-panel` gets an `n=` stepper next to the existing fields, and
`lb-cf-result` becomes a small grid (reusing the existing `lb-cf-list` strip styling) instead of
a single image, with each result clickable to promote it into the main Lightbox view via the
existing `jump()` mechanism.

This makes each generate-around click slower in the single-request sense (`n` sequential jobs
instead of one), which is an acceptable tradeoff since the whole flow is already a synchronous,
wait-for-it interaction with its own timeout and balance-floor guard; it does not change the
worst-case latency character of the feature, only its total duration for `n > 1`.

## Gap 3: a real thumb-then-full-res loading pattern

This is the one genuinely new piece of shared infrastructure the batch calls for, matching the
user's framing directly: a caller says "put this image here," and a small helper manages a
synchronous thumb load followed by an asynchronous full-res swap, instead of every call site
either loading a heavy full-res image directly (Lightbox main image, the new `/real/` panel) or
being stuck on a thumb forever (grid views, which is correct there).

Proposed shared helper in `shared_ui.py`, exposed on `window` alongside `Lightbox` so any page's
generated JS can call it without a new import:

```js
function mountProgressive(imgEl, thumbSrc, fullSrc) {
  imgEl.src = thumbSrc;               // synchronous: whatever's already cached/fast
  imgEl.classList.add('progressive-loading');
  const full = new Image();
  full.onload = () => {
    imgEl.src = fullSrc;              // async swap once the full-res bytes are in
    imgEl.classList.remove('progressive-loading');
  };
  full.src = fullSrc;
}
```

`progressive-loading` gets a CSS blur/dim treatment matching the Lightbox's existing `.loading`
spinner state, so a caller opts in just by naming a thumb source and a full source, not by
wiring up load-event plumbing itself each time.

Two call sites change to use it:

- **Lightbox main image** (`shared_ui.py:373`): thumb source is `d.thumb` (already computed for
  the grid), full source is `d.file`. This makes opening any image from any of the seven
  Lightbox-enabled pages feel instant (grid thumb reused, no blank/spinner gap) while the full
  image loads behind it.
- **Map hover panel's real-image view** (`map_view.py`, added this session): needs a thumbnail
  variant of `/real/<name>` to exist first, since right now that route only serves full
  resolution. `thumbnails.py`'s `generate_thumbnail(src_path, dst_path)` already does exactly the
  on-demand-generate-and-cache job the `/thumbs/` route relies on for generated images
  (`curation_server.py:602-611`); the natural fix is a matching `/real_thumbs/<name>` route built
  the same way, caching into a `real_thumbs/` directory next to `/real/`'s source
  (`corrected_dataset_extract/`, read-only reference data, so cache writes go to a scratch
  location under `SWEEP_DIR` instead of the reference directory itself). Once that route exists,
  the map panel's `<img id="realImg">` switches from a plain `src=` assignment to
  `mountProgressive(realImg, '/real_thumbs/'+name, '/real/'+name)`, which is what actually
  answers task 11: clicking (or just viewing) the panel gets a fast thumb immediately and the
  full reference photo a moment later, rather than a slow direct full-res load on every hover.

Grid thumbnails (`scan.html`'s `<img loading="lazy">` tiles, etc.) are explicitly out of scope
for this helper: they're already thumb-only by design, and there's no full-res image to swap to
until a tile is actually opened.

## Explicitly not covered here

Tasks 13 (compare.html tooltip for the "Model reads your taste" stat) and 14 (prompt toward a
generation flow when compare.html's pairs exhaust) are small, independent, and don't depend on
any of the above; they're tracked separately in `TODO.txt` rather than folded into this design.
