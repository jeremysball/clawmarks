# CLAWMARKS preference classifier: rate, learn, steer the search

## Motivation

The hyperparameter search (round 1 of the 5-round plan in `lab_notebook.md` Section 3) is
paused: the user wants to shift effort to the inference-time exploration side, which already
has a mature toolchain (`search/driver.py`'s adaptive MAP-Elites-style loop, `curation_server.py`
with picks/favorites/counterfactuals, 8 browsing tools). That toolchain optimizes for
faithfulness and novelty, both DINOv2-embedding distances with no aesthetic judgment. The lab
notebook already documents a real gap this causes: `build_elite_archive.py` falls back to
"highest novelty wins" whenever no human pick exists for a bin, which can select a worse-looking
image over a better one in the same bin, since novelty has no opinion about quality.

This project adds a preference classifier: a model that predicts how much the user will like an
image, trained on the user's own yes/no ratings. It closes the elite-selection gap above and,
longer term, lets the live search hunt for images the user will like, not just images that are
novel.

## Scope

In scope: a ratings-collection UI, an embedding cache, a preference model trained on frozen
DINOv2 embeddings, a pool re-ranking view to validate the model, and wiring the model into
`build_elite_archive.py`'s fallback and `search/driver.py`'s exploit selection.

Out of scope: resuming the hyperparameter search (paused, not abandoned; picks back up as its
own thread later). Any change to the DINOv2 centroid/novelty scoring itself. A pairwise-
comparison or active-learning labeling scheme (out of scope for v1; plain random-eligible
sampling, stratified by existing bins, is enough to start).

## Current state (grounding numbers)

- `scored_manifest.json`: 3672 images, each with `centroid_sim` (faithfulness) and `novelty`
  scores already computed, but no raw embedding vectors persisted.
- `user_picks.json`: 40 picks (all positive; feeds the search's exploit pool).
- `user_favorites.json`: 1 favorite (pure bookmark, no search effect).
- `user_counterfactuals.json`: 0 (feature built, unused so far).

40 labels, all positive, is not enough to train anything. The rating UI below exists to fix that
before any model training is attempted.

## Component 1: embedding cache

A one-time script (`src/clawmarks/search/embed_cache.py`) runs the DINOv2 model already used
by the scoring pipeline over every image referenced in `scored_manifest.json`, and writes the
resulting embeddings to `notes/uncanny_sweep/embeddings.npz` (or equivalent), keyed by image
tag. This runs locally (no RunPod cost). A second mode processes only tags missing from the
cache, so future search rounds can extend it incrementally rather than recomputing everything.

## Component 2: rating UI

A new page, `rate.html`, served by `src/clawmarks/curation_server.py`, shows one image at a time with a
binary yes/no control (mouse and keyboard, e.g. arrow keys or `y`/`n`). Two new endpoints:

- `GET /api/rate/next`: returns the next image to rate.
- `POST /api/rate`: records a label for a given tag.

Labels are stored in a new `notes/uncanny_sweep/user_ratings.json`,
`{tag: {label: "yes"|"no", rated_at}}`, parallel to the existing picks/favorites files.

**Sampling**: `GET /api/rate/next` excludes any tag already present in `user_picks.json`,
`user_favorites.json`, or `user_ratings.json`, so every rating adds a new label. From the
remaining eligible pool, it samples stratified across the existing faithfulness x novelty bins
(the same grid `build_elite_archive.py` already uses) rather than pure random, so an early
session doesn't over-sample whichever region happens to dominate the pool (e.g. late-generation
exploit-heavy images).

## Component 3: training

A script, `src/clawmarks/search/preference_model.py`, loads the embedding cache and
`user_ratings.json`, and trains a logistic regression (scikit-learn) on the embeddings alone
(no generation metadata as input — see "Feature set" below). It reports validation accuracy via
k-fold (or leave-one-out if fewer than ~50 labels exist) and saves the fitted model to disk
(`notes/uncanny_sweep/preference_model.joblib`).

Training is a manual, explicit step (rerun the script), not automatic on every new rating, so
results stay easy to reason about. The script refuses to train below a floor of 50 labels and
prints a clear message instead of producing a model on too little data.

**Feature set: embedding only.** Generation metadata (strength, cfg, prompt_type, category) is
deliberately excluded. Metadata features risk the model keying off generation settings rather
than actual visual content, and they're meaningless for any image from outside this pipeline.
Embedding-only keeps the model a pure "does this look like something the user likes" predictor.

## Component 4: pool re-ranking view (validation stage)

A new view, either a sort mode added to the existing scan gallery or a standalone page, lists
every embedded image sorted by the model's predicted preference probability, highest first.
This is the human validation gate: before the model touches anything live, the user browses this
ranking and confirms it actually tracks their taste.

Built-in sanity check: the model should score the existing 39 non-training picks (they predate
the rating UI, so they were never in its training set) highly. If it doesn't, that's a signal to
investigate before proceeding to Component 5, not a green light to plow ahead anyway.

## Component 5: steering the live search (gated on Component 4 passing)

Two integration points, both opt-in behind an explicit flag:

- `build_elite_archive.py`: replace the "highest novelty wins" per-bin fallback (used when no
  human pick exists) with "highest predicted preference wins."
- `search/driver.py`: add predicted preference as a factor in exploit-candidate selection,
  alongside the existing faithfulness/novelty criteria.

Because this changes what a paid, live search actually generates, it ships behind a flag and
gets a dry run first: run the driver for one generation with the new fallback active, diff which
images it would have selected against the old novelty-only logic, and eyeball the difference
before trusting it on a real budget-metered overnight run.

## Data flow

```
search driver generates images
  -> DINOv2 scoring (existing: centroid_sim, novelty)
  -> embedding cache (new, one-time + incremental)
  -> rating UI samples unreviewed images, stratified by bin
  -> user rates yes/no -> user_ratings.json
  -> preference_model.py trains on embeddings + ratings (manual, gated at 50+ labels)
  -> Component 4: re-rank pool, human validates
  -> Component 5 (only after validation passes): wired into elite_archive fallback
     and driver.py exploit selection, behind a flag, dry-run tested first
```

## Error handling

- Training below the 50-label floor: script exits with a clear message, no model produced.
- Rating UI sampler: must never re-serve a tag already in picks/favorites/ratings; a unit test
  covers this directly.
- Re-rating an already-rated tag overwrites the existing entry rather than duplicating it.
- Embedding cache: incremental mode must not silently skip tags that exist in the manifest but
  are missing an image file on disk; it should report a hard error listing which tags failed.

## Testing

- Unit tests: stratified sampler excludes reviewed tags; `POST /api/rate` overwrites, not
  duplicates; `preference_model.py` refuses to train under the label floor.
- Model-quality gate: Component 4's sanity check (existing 39 picks should score highly) is the
  primary go/no-go signal before Component 5 is attempted.
- Component 5 dry run: diff old vs. new elite-selection output for one generation before it's
  allowed to affect a real search budget.
