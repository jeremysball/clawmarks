# Review: CLAWMARKS LoRA hyperparameter search methodology

## Two cross-cutting issues

**Selection rule under-tests variance.** Two controls and two replicates make every mean an n=2 estimate, and the floor is itself an n=3 estimate. A lucky probe pair clears the bar. Treat this as a two-sample comparison between a direction's replicates and pooled controls; a Welch's t or permutation test gives a real p-value. Pool controls across rounds, since the baseline is cheap to re-run and the estimate only improves.

**Multiple comparisons unaddressed.** ~10 probes per round at a loose bar guarantees spurious wins. Apply BH correction within a round, or rank directions and commit only the top one after a stricter bar.

## Q1: Sufficient?

No. Two replicates cannot estimate within-direction variance; you cannot distinguish "helps by X" from "two seeds landed high." Use 3-4 replicates per direction and report each direction's standard deviation, not just its mean. "Both same sign" is satisfied by chance 25% of the time when the true effect is near zero, exactly the marginal regime you care about. Pre-register the threshold before running, or the bar drifts to whatever feels convincing.

## Q2: Probes representative of the full run?

Unverified. Three cosine cycles over 780 steps means a 156-step probe finishes under one cycle, sampling a different dynamical regime than the commit run lives in. Late effects (overfitting, network-dim capacity, min_snr_gamma) can reverse sign between probe and commit. Calibration round: take 2-3 directions to both 156 and 780 steps, check rank correlation. If they agree, probes are defensible; if not, probe longer or accept probes only screen for catastrophic directions, not winners.

## Q3: Right metric shape?

Probably not. The centroid is dragged by the 0.22 outlier, so it rewards matching the mean-plus-outlier, not the dominant style. Cosine-to-centroid also rewards collapse: a checkpoint producing only near-mean images scores high while failing to reproduce the real spread. Cheaper alternatives: nearest-neighbor distance to the 31 reals (use a non-minimum k to ignore the outlier), or MMD or a Frechet-style distance in DINOv2 space, which compares distributions and rewards matching the spread.

## Q4: Local-optimum risk?

Real. Greedy "first direction that clears the bar" locks you in a basin. Cheap mitigation: probe the top 2-3 directions by prior plausibility each round and commit the best of those, not the first to clear. Keep a ledger of tried-but-not-committed directions for later revisit. The data-side check is itself a basin escape; don't waste it by bundling it with a hyperparameter change the same round (Q5).

## Q5: Other blind spots

- **Double-dipping on the validation set.** Epoch 4 was picked on the 10-prompt set; the same set now scores new configs, biasing toward epoch-4 lookalikes. Hold out a separate set or rotate prompts across rounds.
- **Generation stochasticity may dominate.** 10 prompts x 3 seeds = 30 images. Seed variance in style match likely exceeds prompt variance; spend more on seeds, fewer on prompts.
- **Probe length cannot test schedule shape.** A 156-step probe completes under one cosine cycle, so lr_scheduler and cycle count are untestable at probe length. Drop them from probes, or accept they're un-optimized.
- **Epoch selection within a commit multiplies comparisons.** A 780-step run has 5 sub-checkpoints; scoring all and taking the best is uncontrolled selection. Pre-specify which epoch you score, or correct for 5 tests.
- **Data and hyperparameter changes interleaved.** Down-weighting the outlier in the same round as an LR change makes improvement unattributable. Keep them on separate rounds.
- **Final human review ranks by a metric known to disagree with human preference.** Rank finalists by a small human panel, not DINOv2, since you've shown it ranks human-preferred images near the bottom.

=== DONE ===