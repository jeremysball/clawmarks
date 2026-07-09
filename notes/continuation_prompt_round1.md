# Continuation prompt: round 1 noise floor at 260 steps, paired-seed design

Use this to resume the "round 1 noise floor / probe phase" thread of the CLAWMARKS LoRA project.
Read `notes/lab_notebook.md` first (Section 3, step 2, and the 2026-07-09 lab log entries) for
full methodology and background; this file is a handoff for one specific in-flight thread, not a
replacement for the notebook. (There's a separate `notes/continuation_prompt.md` for the
unrelated "reveal branch" / counter-art thread; don't conflate the two.)

## Where things stand right now

**In flight:** 8 `control260A`..`control260H` replicates (260-step probes, same hyperparameters
as the current-best config, differing only by uncontrolled training seed) are training across
two pods, launched via `notes/run_control260_batch.sh`.

- Pod 1 (`cn0zudkxb89or6`, `rpssh.py`/`rpget.py`/`rpsftp.py`): running `control260A control260B
  control260C control260D`. As of last check, A/B/C are trained, sampled, and downloaded to
  `notes/probe_samples/control260{A,B,C}_260/`; D was mid-training.
- Pod 2 (`iv8iannf63g3cf` at `47.47.180.44:17882`, `rpssh2.py`/`rpget2.py`/`rpsftp2.py`): running
  `control260E control260F control260G control260H`. E/F/G done and downloaded; H was
  mid-training.

**First thing to do on resume:** check whether both batches have actually finished (they were
close, ~15-20 min out, when this thread got handed off). Don't rely on any background-task
notification carrying over from the prior conversation, since those don't persist across
sessions. Use the `runpod-status` skill or SSH directly (see `rpssh.py`/`rpssh2.py` for
host/port) and check `ls /workspace/output/control260*/` plus `ps aux | grep sdxl_train` on each
pod, or just check `ls notes/probe_samples/control260*_260/` locally against the full set of 8.

## Why these runs exist, and their key limitation

The 156-step noise floor (measured earlier from `control_156`/`controlB_156`../`controlH_156`)
doesn't transfer to 260-step probes: noise floor is a property of probe length. Probes were
extended from 156 to 260 steps because 156 cuts off 60% through the first of 3 cosine-schedule
cycles in the real 780-step run, before the learning rate decays back down. 260 completes one
full cycle, a much closer proxy. See notebook step 2 for the full reasoning.

**Important:** `control260A`-`H` use **unpinned, uncontrolled training seeds**. This batch was
launched before the paired-seed design (below) existed. Treat this batch as a raw/unpaired
260-step noise-floor reference, not the design round 1 will actually use going forward.

## The paired-seed methodology change (already implemented, not yet re-run)

Mid-thread, we confirmed (by reading kohya's actual source, not assuming) that `train_probe.py`
never pinned a training seed at all: kohya's `set_seed()` call is skipped whenever `--seed` is
omitted, so every probe run so far got an uncontrolled LoRA weight init and batch-shuffle order.
Both are controlled together by a single seed value: `set_seed()` sets `random`/`numpy`/
`torch.manual_seed`/`cuda.manual_seed_all`, and kohya's DataLoader uses `shuffle=True` with no
separate generator, so it draws from that same global torch RNG (and worker processes derive
their seeds from it too). Generation was already pinned (`gen_samples.py` always uses `--seed
42`), so all measured noise floor so far is pure training-seed variance.

Implemented this session:
- `train_probe.py` now accepts `--seed`, passed straight through to kohya's `--seed` flag.
- Added `CANONICAL_SEEDS` (8 fixed seeds: `20260709, 8675309, 271828, 141421, 314159, 161803,
  57721, 30103`) at module scope. **From here on, control and every candidate direction reuse
  this exact list** so replicate *i* of any direction shares its training seed with replicate
  *i* of control. This is a paired design: the delta at each seed index cancels the shared
  init/shuffle-order variance instead of just averaging over it, which should tighten the
  paired-delta variance and may let round 1 use a smaller n than the unpaired estimate implies.
- Explicitly rejected: pinning one single global seed for every run in the whole search. That
  would collapse replication to n=1 and risk mistaking one seed's lucky interaction with a
  hyperparameter for a real effect. Pairing is not the same thing as not-replicating.
- Documented in `lab_notebook.md` step 2 (the "Note added 2026-07-09: paired training seeds, not
  just pooled ones" paragraph) and in `TODO.txt`.

## control260A-H is done; this section is superseded (2026-07-09)

Both batches finished training, sampling, and downloading. **Do not go measure a fresh unpaired
260-step noise floor from this batch as a next step.** That plan (steps 1-6 that used to be
listed here) is superseded by a simpler realization, below.

## How probes get judged now: no separate noise-floor measurement required

A sign-flip permutation test builds its null distribution from the very deltas under test.
Given a direction's 8 paired deltas (`direction_score[seed_i] - control_score[seed_i]`, same
seed on both sides via `CANONICAL_SEEDS`), the test asks how often random sign-flips of those
same 8 numbers would produce a mean this large. It never needs an externally-measured floor
constant to run. That constant was only ever a stand-in for two side calculations:

- **Practical effect-size floor**: still worth a working number (0.05 cosine, carried over from
  the 156-step derivation), but it can be revised using round 1's own real paired deltas rather
  than a dedicated calibration batch.
- **Replicate count n**: n=8 was derived assuming unpaired noise. Pairing can only shrink
  variance, never grow it, so n=8 should be at least as safe under the paired design, likely
  more so.

Practical consequence: `control260A`-`H` (unpinned/unpaired seeds) is a useful descriptive
reference, not a gate. Round 1's real probe phase does not need to wait on measuring a fresh
unpaired floor first. Full reasoning: `lab_notebook.md` step 3, "Note added 2026-07-09: paired
seeds make a separately-measured noise floor optional, not required."

## Next steps, in order

1. **Open question, resolve with the user first:** round 1's ~10 candidate directions were only
   ever referenced as a placeholder count in the notebook (Section 3's budget math), never
   actually listed. The 3 tested in calibration (`dim64`, `lr2e4`, `constlr`) don't carry over
   as-is: `constlr` was disproven at full length (best at 156, worst at 780), `dim64` was worst
   at both lengths but never confirmed against a real floor, and `control`/`lr2e4` tied within
   noise. Candidates on the table but not yet decided: other `network_dim`/`network_alpha`
   values, `min_snr_gamma` variants, `clip_skip` variants, `text_encoder_lr` moved independently
   of `unet_lr`, `lr_scheduler_num_cycles` other than 3. Don't pick the final list unilaterally;
   confirm scope with the user, per this project's standing "keep options open" preference.
2. Train control at 260 steps using `CANONICAL_SEEDS` explicitly, 8 replicates, one per
   canonical seed. This is the real paired baseline every direction gets compared against going
   forward, not throwaway calibration. `control260A`-`H` cannot substitute for this: those runs
   never pinned a seed, so there's no way to know after the fact which seed each one used.
3. Once the candidate list is confirmed, run each direction as 8 replicates at 260 steps using
   `CANONICAL_SEEDS` (replicate *i* of a direction shares seed *i* with the control batch above).
4. Score everything, then per direction run a sign-flip permutation test directly on that
   direction's own 8 paired deltas (no external floor needed). Require both statistical
   significance and a practical effect size (working floor 0.05 cosine). Apply
   Benjamini-Hochberg correction across every direction tested this round, or the equivalent
   discipline of only ever advancing the single best-ranked direction.
5. Fold results into `lab_notebook.md`'s lab log as they land, not just at the end. Update
   `TODO.txt` to match.
6. Winner (if any) moves to the commit phase: full 780-step retrain, scored at multiple epochs
   against both the original and the broadened holdout prompt set.
7. Remember to terminate whichever pod(s) aren't needed once this phase wraps; both were still
   accruing cost (~$0.69/hr each) as of this writing.

## Full remaining TODO, dumped for reference (see `TODO.txt` for the live version)

```
## Round 1: noise floor probes (in progress)
[x] Resolve the 0.22-similarity outlier real image: confirmed genuine stylistic outlier,
    down-weighted via a separate low-repeat kohya subfolder.
[x] Build MMD scoring tool alongside centroid/nearest-neighbor; real-vs-generated gap is real
    signal, modest in size, no collapse signature.
[x] Decide GPU: RTX 4090.
[x] Write rp_bring_up.py + remote_setup.sh: idempotent pod bring-up.
[x] Step 1 calibration, 156-step and 780-step legs: all four directions (control, dim64,
    lr2e4, constlr) trained, sampled, scored.
[x] Step 1 verdict: 156-step and 780-step rankings disagree (constlr swings from best to
    worst); probes can screen out bad directions but not pick a winner outright.
[x] Noise floor measured from 3 then 8 control_156 replicates: checkpoint-mean stdev ~0.035,
    horse prompt ~4x noisier than wolf-cat.
[x] Derived round 1's replicate count via permutation-test power simulation: 0.02 cosine
    undetectable at any practical n; revised effect-size floor to 0.05 cosine, n=8.
[x] Probe length revised to 260 steps (one full cosine cycle), not 156.
[x] Added --seed to train_probe.py; CANONICAL_SEEDS defined for paired control/direction
    comparisons going forward.
[x] control260A-H (8 unpaired replicates) finished training/sampling/downloading.
[x] Realized a per-direction permutation test is self-calibrating; dropped the requirement to
    measure a fresh unpaired 260-step floor before round 1 can start.
[ ] OPEN QUESTION: confirm round 1's actual ~10 candidate directions with the user.
[ ] Train control at 260 steps using CANONICAL_SEEDS explicitly (the real paired baseline).
[ ] Step 2: run each confirmed direction as 8 replicates at 260 steps using CANONICAL_SEEDS.
[ ] Step 3: per-direction sign-flip permutation test + 0.05-cosine effect floor +
    Benjamini-Hochberg correction across directions tested, or rank-and-commit-only-the-best.
[ ] Step 4: commit phase, full 780-step retrain of the winning direction.
[ ] Step 5: score the committed run at epochs 2/4/6/8/final against the original and broadened
    holdout prompt sets.
[ ] Step 6: any data-side change stays in its own round, never mixed with a hyperparameter round.
[ ] Step 7: repeat for rounds 2-5, keeping a ledger of probed-but-not-committed directions.
[ ] Fold each round's results into lab_notebook.md as they happen.

## Near-term reveal branch (separate thread, few-days deadline)
[ ] Resolve whether a reference photo of the artist exists (see notes/continuation_prompt.md).
[ ] Once resolved: decide img2img/IP-Adapter vs. text-only, draft liminal-space prompts,
    generate, floor-check with DINOv2/MMD, curate, show the artist.
```

## Standing constraints, don't relitigate these

- **Never commit `.safetensors` checkpoints to git**, in any form, not even via LFS. Explicit,
  hard instruction from earlier in this project ("dont commit anything then"). `.gitignore`
  already has `*.safetensors`; keep it.
- **Always publish any Artifact locally too**, mirrored into `notes/probe_samples/` and served
  over the tailnet (`python3 -m http.server 8420 --bind 0.0.0.0`, tailnet IP `100.75.221.31`),
  in addition to the claude.ai Artifact tool. Shorten both links with the `chhoto` skill
  (`~/.claude/skills/chhoto/bin/shorten.sh`, self-hosted at `prometheus:4567`, needs
  `CHHOTO_API_KEY` from `.envrc`).
- Explain ML concepts in plain language as they come up (this is a non-academic researcher's
  project, per `CLAUDE.md`). Don't assume familiarity with things like noise floors,
  permutation tests, or cosine LR schedules without a plain-language gloss the first time.
  Recent examples already explained in this thread: what a 260-step probe vs. 780-step full run
  actually tests, what a paired seed design buys over pooling, why a global fixed seed would be
  worse not better.
- No em dashes anywhere in the notebook, TODO, or commits, and no `--` standing in for one
  either: `rg -n "—"` and check for ` -- ` before calling any writing done.
- `TODO.txt` is gitignored/ephemeral (working scratch list); `notes/lab_notebook.md` is the
  durable source of truth. Keep both current, but only the notebook needs to survive long-term.
