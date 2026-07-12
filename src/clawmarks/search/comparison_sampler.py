"""
Pair sampler for the compare UI (compare.html / GET /api/compare/next): picks two images to
show side by side next. Replaces search/rating_sampler.py's role for head-to-head comparisons.

Below MIN_COMPARISONS, picks a stratified-random pair: two bins chosen independently at random
from the existing faithfulness x novelty grid (also used by build/elite_archive.py), one random
image from each, so an early comparison session doesn't over-sample whichever region happens to
dominate the pool. At or above the floor, switches to model-uncertainty-guided selection: a
random candidate set of images is scored by the current model, and the two whose scores are
closest together are returned, since that pair is the model's best approximation of "least sure
which one wins" without enumerating every possible pair across a pool of thousands of images.
See docs/superpowers/specs/2026-07-11-head-to-head-preference-design.md.
"""
import random

from clawmarks.search.scoring import bin_edges, bin_of

N_BINS = 4  # matches build/elite_archive.py's grid
MIN_COMPARISONS = 50
RETRAIN_EVERY = 10
CANDIDATE_POOL_SIZE = 200


def bin_manifest(manifest):
    faith_vals = sorted(m["centroid_sim"] for m in manifest)
    novelty_vals = sorted(m["novelty"] for m in manifest)
    faith_edges = bin_edges(faith_vals, N_BINS)
    novelty_edges = bin_edges(novelty_vals, N_BINS)
    grid = {}
    for m in manifest:
        fb = bin_of(m["centroid_sim"], faith_edges)
        nb = bin_of(m["novelty"], novelty_edges)
        grid.setdefault((fb, nb), []).append(m)
    return grid


def stratified_random_pair(manifest, rng=random):
    """Returns two distinct manifest items from randomly chosen bins (can be the same bin), or
    None if the manifest has fewer than 2 images."""
    if len(manifest) < 2:
        return None
    grid = bin_manifest(manifest)
    nonempty = [items for items in grid.values() if items]
    if not nonempty:
        return None
    bin_a = rng.choice(nonempty)
    item_a = rng.choice(bin_a)
    for _ in range(20):
        bin_b = rng.choice(nonempty)
        item_b = rng.choice(bin_b)
        if item_b["tag"] != item_a["tag"]:
            return (item_a, item_b)
    # Every random draw collided with item_a (bad luck, or every other bin happens to be
    # empty of anything but item_a's own bin with item_a as its only member) - fall back to a
    # linear scan for any other image, which always succeeds given len(manifest) >= 2.
    for m in manifest:
        if m["tag"] != item_a["tag"]:
            return (item_a, m)
    return None


def most_uncertain_pair(manifest, model, score_fn, embeddings_for, rng=random):
    """Returns the two manifest items whose model scores are closest together, out of a random
    candidate set of up to CANDIDATE_POOL_SIZE images. `score_fn(model, embeddings) -> sequence`
    and `embeddings_for(items) -> sequence` let callers plug in
    preference_pairwise_model.score and an embedding lookup without this module importing the
    embedding cache directly. Returns None if fewer than 2 candidates are available."""
    if len(manifest) < 2:
        return None
    candidates = rng.sample(manifest, min(CANDIDATE_POOL_SIZE, len(manifest)))
    scores = score_fn(model, embeddings_for(candidates))
    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1])
    best_gap, best_pair = None, None
    for i in range(len(ranked) - 1):
        gap = abs(ranked[i][1] - ranked[i + 1][1])
        if best_gap is None or gap < best_gap:
            best_gap, best_pair = gap, (ranked[i][0], ranked[i + 1][0])
    return best_pair


def pick_next_pair(manifest, n_comparisons, model=None, score_fn=None, embeddings_for=None, rng=random):
    """Top-level entry point used by curation_server.py. Below MIN_COMPARISONS, or when no model
    is available yet, falls back to stratified_random_pair. At/above the floor with a model
    available, uses most_uncertain_pair."""
    if n_comparisons < MIN_COMPARISONS or model is None:
        return stratified_random_pair(manifest, rng=rng)
    return most_uncertain_pair(manifest, model, score_fn, embeddings_for, rng=rng)
