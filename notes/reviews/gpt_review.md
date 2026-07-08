# Methodology Review

This is a thoughtful plan for a tiny-data LoRA search, but the current design treats probe scores as more decisive than they will be. With 31 training images, 30 validation generations, and short 156-step probes, variance will come from training seed, prompt seed, checkpoint epoch, sampler behavior, and the metric itself. The plan should treat probes as cheap triage, not proof.

## Answers to the Five Questions

1. **The noise-floor design is useful but too weak as a decision rule.** Two replicates per direction and 2-3 controls can catch gross noise, but they cannot estimate uncertainty well. I would keep the design but score each generated image separately, then compare paired prompt-seed cells against the baseline. For each direction, compute the mean delta over the same 30 prompt-seed slots and bootstrap a confidence interval over those 30 deltas. Advance a direction only if most of the bootstrap mass is positive and the effect size is practically meaningful, for example >0.02 DINOv2 cosine. This costs no extra GPU time.

2. **Two-epoch probes may not predict epoch-10 behavior.** LoRA training often changes character over time: higher learning rates can look strong early and overfit later; lower learning rates can lag early and win later. To reduce reversal risk, save and score intermediate checkpoints inside each probe, for example after epochs 1 and 2, and look for trajectory shape rather than a single endpoint. For commit runs, score epoch 2, 4, 6, 8, and 10. A direction that wins only because it learns fastest should not automatically win.

3. **Centroid cosine is a reasonable first metric, but it is too compressed for a heterogeneous art set.** A single centroid rewards the dominant mode and penalizes legitimate outliers. Add two cheap companion metrics: nearest-neighbor similarity to the real images, and distance to the distribution of real-image scores. For example, report each generation's centroid score, its max similarity to any training image, and whether it falls inside the real-image score range. High centroid plus very high nearest-neighbor similarity may indicate memorization; moderate centroid plus plausible nearest-neighbor spread may indicate broader style learning. Keep human review as the final gate.

4. **Sequential search can get stuck, but the bigger risk is committing too early.** Given five full retrains, I would not spend budget on a broad grid. Instead, probe several directions per round, rank all of them by paired delta, and commit only after seeing the whole round's results. If two directions both clear the bar, prefer the one with the larger paired effect and cleaner trajectory, not the first one noticed. Reserve one final full run for a combination test of the two best compatible changes, such as learning rate plus schedule.

5. **Main blind spots:** first, the validation prompts may leak the original epoch-4 selection bias. Add a small holdout prompt set with unfamiliar subjects, since the stated goal is novel subject matter in style. Second, DINOv2 may reward subject and composition more than expected; test this by scoring generated outputs from the base model with the same prompts and no LoRA. Third, inspect the 0.22 real-image outlier before any hyperparameter search. If it is a caption bug or a different medium, it will distort both training and the centroid.

## Practical Revision

Keep the probe-then-commit structure, but make three changes: use paired per-image deltas with bootstrap intervals, score checkpoint trajectories instead of only 2-epoch endpoints, and add nearest-neighbor plus holdout-subject reporting beside the centroid score. These changes fit the compute budget and make the results easier to defend.

=== DONE ===
