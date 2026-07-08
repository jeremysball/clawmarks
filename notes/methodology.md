# CLAWMARKS LoRA: hyperparameter search methodology (for external review)

## Context

Training an SDXL LoRA (Illustrious base checkpoint, trigger word `trentbuckle`) to reproduce a
personal illustration style called CLAWMARKS: sketchbook-style animal portraits in marker, ink,
colored pencil, and mixed media. The full training set is 31 real images. A first retrain (after
fixing a caption/image mismatch bug in 9 of 31 captions) produced a working checkpoint, picked by
a human-reviewed validation grid (10 prompts x 3 seeds x candidate epochs). That checkpoint,
epoch 4, is the current baseline.

The underlying goal is not just fidelity for its own sake: the plan is to use a checkpoint that
has faithfully learned the style's rules (not just its most common subject, cats) to generate
genuinely novel subject matter, unfamiliar to the training set, while still reading as
unmistakably in-style. The hyperparameter search below is meant to produce a more trustworthy
instrument for that later step, not an end in itself.

## The scoring metric

DINOv2 (facebook/dinov2-base), a self-supervised vision model with no text-alignment objective,
chosen over CLIP because CLIP's embeddings skew toward semantic content (what object is in the
image) while DINOv2 captures visual style more directly (texture, brushwork, composition),
independent of subject.

Method: embed all 31 real training images with DINOv2, average and renormalize into one
centroid vector, then score any generated image by cosine similarity to that centroid. The 31
real images score a mean self-similarity of 0.61 against their own centroid (min 0.22, max
0.84), which serves as the reference range for "looks like it belongs to this style."

Known limitation already found: this metric disagrees substantially with both CLIP scoring and
human aesthetic preference. Scoring an existing batch of 250 generations, CLIP and DINOv2 shared
only 6 of their top 30 picks, and several images a human reviewer preferred (photorealistic
graphite/watercolor renders) scored near the bottom of the DINOv2 ranking, because the real
CLAWMARKS set is dominated by flat graphic marker/ink work, not painterly realism.

## The search problem

Goal: find a training hyperparameter configuration producing generations closer to the real
style (by the DINOv2 centroid metric) than the current epoch-4 baseline.

Constraints:
- 31 training images total.
- A full training run is 780 steps (10 epochs, ~78 steps/epoch), about 35 minutes of GPU time on
  a rented RTX 3090.
- Budget: 5 full retrain "rounds," not a full grid search across every hyperparameter worth
  testing (dozens of full runs).

Hyperparameters in play, current baseline in parentheses: network dim/alpha (32/16), unet
learning rate (1e-4), text-encoder learning rate (5e-5), min_snr_gamma (5), learning-rate
schedule (cosine, 3 cycles), epoch/repeat count (10 epochs).

## Method, revised after external review

This document went to two outside models as expert reviewers (GPT-5.5 and GLM-5.2, independently
prompted; full reviews in `whitepaper/reviews/`). Both converged on the same core problems with
the plan below in its original form. The method here is the revised version; the resolution
section afterward maps each finding to the change it produced.

For each of 5 rounds (plus one calibration check, done once, and a step 0 done before round 1):

0. **Resolve the data-side outlier before any hyperparameter probing.** One training image scores
   only 0.22 self-similarity against the centroid (vs. mean 0.61). Both reviewers independently
   flagged this as the first thing to fix, since it distorts every centroid comparison that
   follows. Decide whether it's a caption error or a genuine stylistic outlier, and whether to
   down-weight or fix it, before round 1 starts.
1. **Calibration check (once).** Run 2-3 candidate directions at both probe length (~156 steps,
   ~2 epochs) and full length (780 steps), and check whether the two lengths rank the directions
   the same way. The learning-rate schedule runs 3 cosine cycles over 780 steps, so a 156-step
   probe completes under a single cycle, a different part of training dynamics, not a scaled-down
   copy of the full run. If rankings agree, probes are trustworthy for screening; if not, probes
   can only be trusted to catch catastrophic directions, not to pick winners.
2. **Noise floor**, pooled across rounds: 2-3 control probes (current-best config, seed only) per
   round, accumulated into a running pool rather than re-measured from scratch, since the pooled
   estimate only gets better with more data.
3. **Directional probes**: 3-4 replicates per candidate direction (not 2), same reduced length.
   Scored on the same fixed prompt/seed slots as the pooled controls, so replicate and control
   scores form paired comparisons.
4. **Selection rule**: a permutation test or bootstrap confidence interval over the paired deltas
   (direction replicates vs. pooled controls), requiring both statistical signal (most of the
   bootstrap mass positive) and a practically meaningful effect size (roughly >0.02 DINOv2
   cosine). With ~10 directions probed per round, apply a multiple-comparisons correction
   (Benjamini-Hochberg), or the simpler equivalent: rank every direction and commit only the
   single best, rather than the first to clear a loose bar.
5. **Commit**: the top-ranked direction gets a full 780-step retrain, scored at multiple
   checkpoints (epochs 2, 4, 6, 8, final) to see the trajectory shape, not just the endpoint, on
   two validation sets: the original 10-prompt set (continuity with epoch 4) and a holdout set of
   prompts never used to pick epoch 4, weighted toward subjects the original grid found weak
   (owl, tiger, and eventually human face/cyborg/liminal). The holdout exists because the
   original set already favors whatever epoch 4 happens to be good at, biasing the search toward
   "epoch-4 lookalikes" over configs that actually generalize.
6. **Data-side check**: kept to its own round, never combined with a hyperparameter change in the
   same round, so any improvement stays attributable to one cause.
7. Repeat for 5 rounds, keeping a ledger of probed-but-not-committed directions in case later
   data changes make one worth revisiting.

Alongside centroid similarity, also compute nearest-neighbor similarity (max similarity to any
single real image) as a cheap companion score. A Frechet-style distance or MMD (comparing full
distributions, not single means) was also considered, since centroid similarity can reward a
"safe," mean-hugging checkpoint as much as one that reproduces the real style's range, but both
need a reliable covariance estimate in DINOv2's 768-dimensional space, which 31 real images can't
support. Deferred until dimensionality reduction or a larger real/validated-synthetic pool exists.

After 5 rounds: rank all full-run checkpoints by score, then have a **human panel review the top
2-3** before naming a winner, since DINOv2 has already been shown (Known limitation, above) to
disagree with human preference on this dataset.

## Resolution: how the review findings map to the changes above

1. *Noise floor/replication insufficient* (both reviewers) → step 3-4: 3-4 replicates instead of
   2, paired-delta permutation/bootstrap test instead of "beats the floor," pooled controls
   accumulated across rounds.
2. *Multiple comparisons unaddressed* (GLM) → step 4: Benjamini-Hochberg correction, or rank-and-
   commit-only-the-best as the practical equivalent.
3. *Probe length may not predict full-run behavior* (both) → step 1: one-time calibration check
   comparing probe-length and full-length rankings before trusting probes at all.
4. *Centroid metric rewards collapse, dragged by the outlier* (both) → step 0 (resolve the
   outlier first) plus nearest-neighbor as a companion score; Frechet/MMD noted as a real upgrade
   but impractical at n=31 without dimensionality reduction.
5. *Local-optimum risk in greedy commit* (both) → step 4 (rank and commit the best, not the
   first) plus a ledger of untried/rejected directions to revisit later.
6. *Validation-set circularity* (both, independently) → step 5: a holdout prompt set never used
   to pick epoch 4, weighted toward the subjects that matter for the actual novel-subject goal.
7. *Checkpoint-selection multiplies comparisons within a commit* (GLM) → step 5: pre-specify
   scoring at fixed epochs (2/4/6/8/final) rather than scanning all sub-checkpoints and taking
   the best.
8. *Data and hyperparameter changes interleaved, breaking attribution* (GLM) → step 6: kept to
   separate rounds.
9. *Final ranking by a metric known to disagree with human preference* (GLM) → human panel review
   of the top few, not DINOv2 alone, at the end.
10. *Test whether DINOv2 rewards subject/composition rather than style* (GPT) → already tested
    empirically via a zero-LoRA-strength control in a follow-up probe (see lab notebook lab log):
    confirmed a real confound exists for prompts sharing vocabulary with training captions, folded
    into probe-design practice (strip shared vocabulary, or always run a zero-strength control).
