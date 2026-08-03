# DINOv2-similarity visualization pages

Scope: `/map.html`, `/redundancy.html`, `/coverage.html`, `/novelty_decay.html`. Data: `build/solution_map.py` (UMAP + nearest-real + pairwise cosine), `build/similarity_index.py`, `build/coverage_map.py`, `build/novelty_decay.py`. Routes at `curation_server.py:1215-1253`.

## What I observed

`info_btn` tooltips (`shared_ui.py:74-83`) explain one or two concepts per page in plain English. The project already has an internal gold standard: `probe_report.py:384-389` shows a 0.00-0.90 score bar, shades the real training images' own self-similarity band, and tells the reader "a marker left of that band scored below the real set's worst-case." That page calibrates a score against a visible reference. None of the four in scope do.

`map_view.py`: good tooltips (`umap_tip` lines 39-46, `mode_collapse_tip` lines 47-52) plus subtitle prose stating stars = real photos. But the hover panel (lines 241-244) prints `faith`, `novelty`, and nearest-real `sim` with no definition or tooltip, and the nearest-real caption (line 252) repeats `sim 0.71` raw. No on-canvas legend distinguishes gold stars from blue dots, and the play control (lines 285-300) has no tooltip.

`coverage_map.py`: `axes_tip` (lines 159-166) defines both axes in plain English; the legend (lines 342-345) shows low / high / frontier swatches but no numeric ticks, so a blue cell could hold 3 or 300 images. Bins are quantile-cut (line 30: `vals[int(i*len(vals)/n)]`), equal image counts not equal score ranges; the page never says so, and a reader assuming "left half = low faith" in absolute terms will misread the grid. Frontier cells are gated on 4-adjacency to a cell at or above the median occupied count (lines 52-59), but the tooltip drops the median rule.

`redundancy_view.py`'s `cluster_tip` (lines 51-57) spells out that a connected component can be a chain of gradual drift, not a tight duplicate group. The slider pulls min, max, and default from the data's edge distribution (lines 64-71), but the label says only "Similarity threshold ≥ 0.93" with no scale context. The rep is chosen by highest novelty (line 172) but the head (line 174) just says "representative."

`novelty_decay.py`: sparklines and a "declining / flat / still rising" tag, plus `trend_tip` (lines 78-83) flagging its 0.01 cutoff as a rule of thumb. But novelty is never defined on the page; the subtitle (lines 117-120) expects it learned elsewhere. Sparklines are per-row auto-scaled (lines 137-139), so two "flat" prompts at different levels look identical.

Across all four, "DINOv2" is unanchored outside tooltips. (`scan_gallery.py:74` defines "DINOv2 embedding and the centroid", but the scope pages do not reuse it.)

## Concrete problems

1. **DINOv2 is never explained on any page.** "DINOv2 embedding space" in the map subtitle is the reader's first contact with the term.
2. **Three cosine similarities overlap in name.** `faith`/`centroid_sim` (to all real images' centroid), `nearest_real_sim` (to one nearest real photo), and the redundancy slider (pairwise image-to-image) all surface as "sim," and the map hover puts `faith` next to `nearest_real_sim` with no signal they reference different things.
3. **Scores lack calibration.** `faith=0.42` and `sim 0.71` float free of the dataset's range; the probe report already solves this, these pages do not.
4. **map_view has no on-canvas legend** (stars vs dots, picked vs not).
5. **coverage's quantile bins and frontier-median rule are invisible** on the page.
6. **redundancy slider has no scale context**, and the rep's selection rule is unstated.
7. **novelty_decay never defines novelty**, and per-row auto-scaling hides absolute level.

## Recommendations ranked by impact

1. **Anchor DINOv2 at first mention on each page, one tooltip.** "DINOv2 is an open vision model that turns an image into ~768 numbers (an embedding) capturing style without human labels; similar style gives similar embeddings, so we measure style match without a human." A shared `dino_tip` in `shared_ui.py` sourced into each page's first "DINOv2" occurrence. Highest impact; every other tooltip assumes this.
2. **Name the three similarities distinctly.** In `map_view.py:241-244`: "style match to your real art's average: 0.42" and "closest single training photo: 0.71". In `redundancy_view.py:114`: "image-to-image match threshold" instead of bare "Similarity threshold".
3. **Port the probe-report calibration.** For map_view, pass `min / median / max` of `centroid_sim` into the panel and render "faith 0.42 (median 0.39 this sweep)"; shade the real-self-similarity band on the nearest-real caption. For coverage, add count ticks ("1", "median N", "max M") to the legend at lines 342-345.
4. **Add a 3-row on-canvas key to map_view** (star = real training photo, dot = generated, gold dot = picked winner). Local CSS at lines 88-94.
5. **State quantile bins and the median frontier gate on coverage.** Append to `axes_tip` (lines 159-166): "Each column holds roughly equal image counts, so the leftmost faith column is the lowest eighth of this sweep, not 'low faith' in absolute terms. A frontier cell is empty but borders a cell at or above this sweep's median count."
6. **Scale-context the redundancy slider.** Below the slider at line 116, render "default 0.93 (tightest 5% of pairs this sweep); your pairs span 0.71-0.98." Data already lives in `all_scores` at lines 64-70. Append "(highest novelty)" to the rep label at line 174.
7. **Lift novelty's definition onto novelty_decay.** One sentence in the subtitle (lines 117-120): "Novelty measures how different an image is from everything already explored; 1 means nothing found so far looks like it." A direct nav landing then needs no bounce.
8. **Tooltip the play control on map_view.** One `info_btn` at line 115: "Slides the generation cutoff forward. Watch whether the cloud expands into new regions (still exploring) or only thickens existing clusters (re-treading)."

None needs a redesign; all are local to the `compute_data`/`render_html` pair.