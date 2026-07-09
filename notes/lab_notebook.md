# CLAWMARKS LoRA: Lab Notebook

Running notes for a whitepaper on training a style-transfer SDXL LoRA and finding the
hyperparameter configuration that best reproduces the source art's style. Written for a
non-academic reader: every technical term gets defined in plain language the first time it
appears, since this notebook doubles as the first draft of the paper's methods section, and as
the single project ledger (infra, datasets, checkpoints, gotchas).

Author's assistant: Claude. This notebook is the shared record between us. Update it after
every meaningful step, not just at the end.

---

## 1. Background and motivation

The subject is a small, personal art style called CLAWMARKS: sketchbook-style animal portraits
(mostly cats, plus wolves, foxes, horses, owls) in marker, ink, colored pencil, and mixed media.
31 real images make up the full training set. The goal is an SDXL LoRA (a small add-on model
that teaches a big pretrained image model, here an SDXL checkpoint called Illustrious, a new
style without retraining the whole thing) that reproduces this style under the trigger word
`trentbuckle`.

**A data bug forced a full restart before anything else could work.** The first training attempt
used a dataset folder that looked correct by its name but wasn't. A caption/image consistency
check (does the text description attached to each training image actually describe that image)
found that 9 of 31 captions described the wrong image. This is a data-quality bug, not a model
bug, and it left no trace in the training loss curve. Loss looked normal throughout. Only
generating sample images at different training checkpoints and inspecting them by eye revealed
the problem. The lesson carries through everything below: an automated score is a filter, not a
verdict. Confirm the top candidates with human eyes before trusting a number.

**Epoch 4 became the current-best checkpoint this way:** after retraining on the corrected
dataset, a validation grid (the same 10 prompts × 3 random seeds × several candidate epochs) was
generated and reviewed against a rubric: style consistency, no broken or garbled compositions,
faithfulness to the training subjects. Epoch 4 won. It is the baseline this whitepaper's search
starts from.

---

## 2. An objective style-similarity metric

Epoch 4 generated 250 new images through a RunPod serverless endpoint. That raised a question:
which of those 250 images actually looks closest to the real training art, not just "which looks
best at a glance"? Two candidate tools:

- **CLIP** (2021) learns to match images with text descriptions. Its embeddings (a list of
  numbers representing an image's content in a form that supports mathematical comparison) skew
  toward semantic content: what object is in the picture. That's what its training objective
  rewards.
- **DINOv2** (Meta, self-supervised, trained on images alone with no text) captures visual style:
  texture, brushwork, composition, directly, since no text signal pulls it toward "what is this a
  picture of."

The real question is style match, not subject match, so DINOv2 is the better tool. It became the
primary metric.

**Method:** embed all 31 real training images with DINOv2, average them into one vector (the
centroid: the geometric center of the real art's style in embedding space), then score any
generated image by its cosine similarity (a number from -1 to 1 measuring how aligned two vectors
are; 1 means identical direction) to that centroid. Higher means closer to the real style.

**A surprising early finding:** scoring the existing 250 generated images, and a "curated 25"
picked earlier by eye, showed CLIP and DINOv2 disagree sharply. They shared only 6 of their top
30 picks. Several hand-picked "best" images, photorealistic graphite cat portraits, watercolor
horse paintings, scored near the bottom of all 250 by DINOv2 (ranks 200-246 of 250). The real
CLAWMARKS set is dominated by flat graphic marker and ink work, not painterly realism, so those
appealing realistic renders are stylistic outliers. DINOv2 confirmed this numerically instead of
leaving it as a hunch. The curated-25 selection was redone using the DINOv2 ranking.

**A second finding, still open (see Section 4):** scoring the 31 real training images against
their own centroid gives a mean self-similarity of 0.61, but a minimum of 0.22. At least one real
training image is a serious style outlier from the rest of the set. If the LoRA has to reproduce
a genuine outlier alongside 30 consistent images, that could dilute how sharply it learns the
dominant style. Whether this is a captioning error (like the original bug) or a legitimate
stylistic one-off worth down-weighting is round 1's first job.

---

## 3. Experiment design: the hyperparameter search

**Goal:** find the LoRA training configuration that produces generations closest to the real art
by DINOv2 similarity, past what the single epoch-4 checkpoint already achieves, in a way that
actually generalizes rather than just re-matching the prompts already used to pick epoch 4.

**Why not a full grid?** A full grid across every hyperparameter worth testing means dozens of
full retrains, each about 35 minutes of GPU time. That's affordable in dollars (rented cloud GPUs
run well under $1/hour), but most of that grid would test directions that don't help. A
sequential search spends the compute where the evidence points instead.

**External review.** Before running this for real, the design below went to two outside models
acting as ML-expert reviewers (GPT-5.5 and GLM-5.2, prompted independently, see
`notes/reviews/`). Both converged on the same core problems with the original plan, and
their fixes are folded into the method below rather than kept as a separate critique. Where a
step exists because of that review, it says so.

**Method: probe-then-commit sequential search, revised.**

0. **Resolve the data-side outlier first, before round 1's hyperparameter probes.** One real
   training image scores 0.22 against the centroid of the other 30 (mean 0.61). Both external
   reviewers independently flagged this as the first thing to resolve, since it distorts the
   centroid every later score gets compared against. Determine whether it's a caption error or a
   genuine stylistic one-off, and decide whether to down-weight or fix it, before any
   hyperparameter probe runs. This is its own step, not folded into a later round, so its effect
   is never tangled up with a hyperparameter change (see step 6).

1. **Calibration check, once, before trusting probes at all.** Take 2-3 candidate directions and
   run each at both probe length (~156 steps) and full length (780 steps), then check whether
   the two lengths rank the directions the same way. The learning-rate schedule runs 3 cosine
   cycles over the full 780 steps, so a 156-step probe finishes under a single cycle, a different
   part of the training dynamics, not just a shorter version of the same run. If probe-length and
   full-length rankings agree, probes are trustworthy for screening. If they don't, probes can
   only be trusted to catch catastrophically bad directions, not to pick a winner.

2. **Probe phase.** Short probes, about 2 epochs (~156 steps, 6-10 minutes), each testing one
   hyperparameter change from the current-best config. Each direction gets **8 replicates**
   (different seeds) -- not the earlier 3-4 guess, see the derivation below -- since fewer
   can't reliably separate a real effect from noise at the effect size actually worth acting on.
   Control probes (current-best config, seeds only) get pooled across rounds rather than
   re-measured each time, since the pooled estimate only improves as more accumulate.

3. **Selection rule: a real statistical test, not "beats the floor."** Score every probe on the
   same fixed prompt/seed slots so each direction's replicates and the pooled controls can be
   compared as paired deltas. Run a permutation test (or bootstrap a confidence interval over
   the paired deltas) rather than just checking "average beats the noise floor." Require both a
   real effect (most of the bootstrap mass positive) and a practically meaningful size (roughly
   >0.02 DINOv2 cosine, not just statistically nonzero). With ~10 probes tested per round, apply
   a multiple-comparisons correction (Benjamini-Hochberg) or the equivalent discipline of
   ranking every direction and only ever advancing the single best one, not the first to clear a
   bar. Taking the first direction that clears a loose bar, with this many tested per round,
   guarantees some spurious wins by chance alone.

   **Note on step 3 in practice: the noise floor has to be measured before it can be used.**
   "Beats the noise floor" only means something once the floor itself is a real number, not an
   assumption. The floor comes from the pooled control-only probes: score each one, take
   pairwise deltas between them (same fixed prompt/seed slots as everything else), and the
   spread of those deltas, which should average to zero since they're all the same config, is
   the noise floor's empirical standard deviation. Every direction's delta against control has
   to clear this floor, both statistically (permutation test or bootstrap CI, above) and in
   practical size (>0.02 cosine).

   This same number also decides how many replicates (n) round 1 actually needs, which the
   "3-4 replicates" starting assumption above was a guess at, not a derived figure. Once the
   noise floor's spread is measured from real control probes, simulate: generate synthetic
   paired deltas with that measured spread plus an injected effect, run the same permutation
   test at a few candidate n values (3, 4, 6, 8), and see which n detects the injected effect
   at least 80% of the time. That n, not the guess, is what round 1 should use.

   **Done, 2026-07-09** (see the lab log entry below for the full numbers): the noise floor
   measured from 3 control_156 replicates turned out bigger than the original 0.02-cosine
   effect floor could ever clear -- at n=8 replicates, a true 0.02 effect is only detected 24%
   of the time, no matter how many more replicates get added within a practical budget. The
   effect-size floor that step 3 actually enforces is revised to **0.05 cosine, not 0.02**,
   and round 1's replicate count is set to **n=8** (84% power at 0.05, 98%+ at 0.08 -- the
   scale of gaps actually seen in the calibration table, e.g. dim64's ~0.06 gap from the other
   three directions, constlr's ~0.10 probe-to-full swing).

4. **Commit phase.** The single best-ranked direction from step 3 gets one full 780-step
   retrain.

5. **Score the full run at multiple checkpoints, not one.** Score epochs 2, 4, 6, 8, and final,
   not just the endpoint, and look at the trajectory shape. A direction that only wins because it
   learns fastest early (and might overfit later) should not automatically win over one that
   catches up by epoch 10. Score against **two validation sets**: the original 10-prompt set (for
   continuity with epoch 4's history) and a **holdout set** of prompts never used to pick epoch 4,
   weighted toward the subjects the original validation grid found weak (owl, tiger; later,
   human face / cyborg / liminal once those are established prompts). The holdout set exists
   because the original set already favors whatever epoch 4 happens to be good at, so it's
   structurally biased toward rewarding "epoch-4 lookalikes" over configs that generalize better.
   This is a holdout of *generation prompts*, not of real training images or synthetic training
   images, a different axis from any dataset-augmentation work.
   Alongside the centroid score, also compute nearest-neighbor similarity (max similarity to any
   single real image, not the average) as a companion number: our own strength-sweep probe
   (Section 5, gotcha log) showed switching from centroid to nearest-neighbor doesn't flip which
   generations look good or bad, so it's a cheap secondary check rather than a replacement.
   A win becomes the new current-best config for the next round.

6. **Data-side check, kept to its own round.** Reconsider the training data itself between
   rounds, e.g. a caption fix or a repeat-count change, but never in the same round as a
   hyperparameter change, so any improvement stays attributable to one cause or the other, not
   both at once.

7. Repeat for 5 rounds. Keep a running ledger of directions that were probed but not committed,
   in case a later round's data changes make a previously-rejected direction worth revisiting
   (guards against the search settling into a local optimum simply by never looking back).

**Hyperparameters in play**, starting from the epoch-4 config (network dim 32 / alpha 16, unet
learning rate 1e-4, text-encoder learning rate 5e-5, min_snr_gamma 5, cosine learning-rate
schedule, 10 epochs):
- Network dim/alpha: how much capacity the LoRA has to learn new detail
- Learning rates: how large a step the model takes per batch
- min_snr_gamma: a loss-weighting trick that can stabilize training on noisy or varied data
- Learning-rate schedule shape: cosine vs. constant (the calibration check in step 1 matters
  especially here, since a 156-step probe can't complete even one full cosine cycle)
- Epoch/repeat count

**Metric upgrade, considered but not adopted for round 1.** Both reviewers, independently,
suggested a distributional metric (Frechet-style distance, the same idea behind FID, or MMD)
in place of centroid cosine similarity, since centroid similarity rewards a checkpoint that
produces safe, repetitive, mean-hugging images as much as one that reproduces the style's real
range. That's a real critique, but a Frechet-style distance needs a reliable covariance estimate
in DINOv2's 768-dimensional embedding space, and 31 real images can't support that (badly
underdetermined). Revisit this once more real or validated-synthetic images exist, or after
reducing embedding dimensionality (e.g. PCA to ~15-20 components); not before round 1.

**After all 5 rounds:** rank every full-run checkpoint, and their own epoch sub-checkpoints, by
DINOv2 score. Then, per Section 1's lesson (and per both external reviews), have a **human
panel review the top few**, not DINOv2 alone. The metric has already been shown to disagree with
human preference (Section 2), so the final call belongs to human eyes.

**Budget, revised 2026-07-09 after the noise-floor derivation:** with n=8 replicates (up from
the earlier 3-4 guess) across roughly 10 directions per round, that's ~80 probes per round at
6-10 minutes each, 8-13 hours of probing alone, plus one 34-minute commit run scored at 5
checkpoints. Call it **9-14 hours per round**, not 2.2-2.5. Five rounds plus the one-time
calibration check: **45-70 hours of GPU time**, a large jump from the original 11-13 hour
estimate, and worth running two pods in parallel (as calibration already did) rather than
serially. This is the direct, unavoidable cost of the effect-size floor moving from 0.02 to
0.05 cosine: a smaller detectable effect needs proportionally more replicates to see reliably,
and 0.02 was never achievable at any practical n given the measured noise (see step 3's note
above and the 2026-07-09 log entry).

---

## 4. Open questions for round 1

- Which real training image scores 0.22 against the centroid, and is that a caption bug or a
  genuine stylistic outlier? (Now step 0 of Section 3, resolved before probing starts.)
- Does the probe-length calibration check (step 1) confirm 156-step probes rank directions the
  same way as full 780-step runs? If not, probes can only screen out bad directions, not pick
  winners, and the whole budget estimate above needs revisiting.
- Does a hyperparameter direction that wins before a data change still win after one? If the data
  changes substantially, the pooled noise floor likely needs a fresh control-probe batch too.

---

## 4a. Whitepaper framing notes (deliberately unresolved)

Decided so far:

- The paper is a **technically rigorous accounting of what's been learned**, not a tutorial and
  not a claim of novel research. It won't oversell a 31-image, 5-round sweep as generalizable
  science.
- Center of gravity: a blend of **the search methodology** (probe-then-commit, the noise floor,
  double-replicated probes) and **the metric-disagreement finding** (CLIP vs. DINOv2, "pretty"
  images scoring near the bottom of the real style match). Neither is a mere setup for the
  other.
- Real mistakes belong in the paper as content, not as sanitized background: the dataset-caption
  bug, the duplicate-job incident, the torchvision workaround. These are part of what was
  actually learned.

Still open, on purpose, until more of the sweep exists to write about:

- Exact section structure and where the paper's scope ends (does it cover the serverless
  deployment/curation pipeline as a main section, or stay narrowly on the metric + search?).
- Whether the outlier training image (Section 4) turns into its own discussed finding or a
  footnote.
- Final framing of the limitations section: how bluntly to state the small-sample caveat, and
  whether to include what a larger-scale version of this study would need.

Revisit this section once round 1 (or a few rounds) of the sweep produces real numbers. Deciding
the paper's final shape now, before the data exists, would be guessing.

---

## 5. Project reference

Everything below is quick-reference state carried over from the project ledger: what's valid,
what's stale, and how to reach the infrastructure. Consult this before reusing any file in this
directory.

### Datasets: which one is correct

| File/dir | Images | Status |
|---|---|---|
| `art/`, `art.zip`, `full-dataset.zip` | 31 | Original, pre-fix. 9 captions describe the wrong image (see `caption_check_result.log`). Don't train on these. |
| `lora-dataset/` | ? | v1 training dataset, pre-caption-fix. Historical only. |
| `lora-dataset-v2/` | ? | v2 training dataset. Historical only. |
| `lora-dataset-v3/` | 24 | Stale: an incomplete subset (7 images missing) that still carries 9 wrong captions. The invalid v3 run below trained on this by mistake. |
| `clawmarks-illustrious-dataset-v2.zip` | 31 | The actually corrected dataset, despite the confusing "v2" name. Produced after `caption_check_result.log` flagged the 9 mismatches; every caption verified against its image. |
| `clawmarks-illustrious-dataset-corrected.zip` | 31 | Same content as the v2 zip, re-zipped under a clearer name and uploaded to the current retrain pod. **Use this one.** |

`caption_check_prompt.txt` / `caption_check_result.log` hold the GPT-5.5-via-opencode
caption/image consistency check that found the 9 mismatches. The log's `MISMATCH:` lines give
the correct description for each.

### Checkpoints

| Dir | Trained on | Status |
|---|---|---|
| `checkpoints/` | v1 dataset, original captions | Historical baseline. |
| `checkpoints_v2/` | v2 dataset, first caption-fix pass | Historical. |
| `checkpoints_v3/` | `lora-dataset-v3` (stale) | Invalid. Don't use for generation. Kept for reference. |
| `checkpoints_v3_fixed/` | `clawmarks-illustrious-dataset-corrected.zip` (31 verified images) | **The valid run.** unet_lr 1e-4, text_encoder_lr 5e-5, min_snr_gamma 5, final loss 0.106. Epoch 4 is current-best (see Section 1). |

Each checkpoint directory holds epoch snapshots `-000002` / `-000004` / `-000006` / `-000008` /
`-final`.

### Comparison sheets already built

- `train_compare_sheet_3way.png`: v1 vs. v2 vs. v3 (invalid) side by side.
- `v3_epoch_compare_sheet.png`: epoch 2/4/6/8/final grid for the invalid v3 run. Useful only as
  a reference for what overfitting or undertraining looks like, not for picking a real
  checkpoint.
- `epoch_sheet_full.png`, `epoch_sheet_full_res.png`: supporting full-resolution crops for the
  above.
- Raw per-checkpoint batches backing these sheets live in `gen/`, `gen_train/` (v1),
  `gen_train_v2/`, `gen_train_v3/` (invalid), plus kohya's own in-training sample dumps in
  `samples/` (v1) and `training_samples_v3/` (invalid run).

`gpt55_prompt.md` / `gpt55_review.log`: an independent overfitting assessment on the invalid v3
run. It recommended epoch 4 as generally safest and proposed the validation-grid method (8-12
prompts × 3-4 seeds across epoch 2/4/final) that the real retrain later used.

### Infra and access

- SSH key: `runpod-ssh/id_ed25519(.pub)`, reused across every pod recreation via the `PUBLIC_KEY`
  env var.
- Helper scripts `rpssh.py` / `rpget.py` / `rpsftp.py`: edit the `HOST`/`PORT` constants at the
  top of each whenever a new pod exists:
  `sed -i 's/HOST = ".*"/HOST = "x.x.x.x"/; s/PORT = .*/PORT = NNNN/'`.
- Base checkpoint: Illustrious SDXL v0.1. Civitai model ID in `clawmarks_model.json`, downloaded
  via `https://civitai.com/api/download/models/889818?token=...`.
- Dependency gotcha, hit twice already: pin `torch==2.4.1` and
  `xformers==0.0.28.post1 --no-deps`, both from `--index-url https://download.pytorch.org/whl/cu124`,
  installed with `uv`. An unpinned `xformers` install lets the resolver silently upgrade torch to
  an incompatible version.
- kohya dataset convention: `--train_data_dir` takes the *parent* of a repeat-count-prefixed
  subfolder (e.g. `img/10_trentbuckle/`), not the image folder itself.
- v3 hyperparameters: `network_dim 32`, `network_alpha 16`, `unet_lr 1e-4`, `text_encoder_lr 5e-5`,
  `lr_scheduler cosine` (3 cycles), `min_snr_gamma 5`, `clip_skip 2`, AdamW8bit, bf16,
  `max_train_epochs 10`, `train_batch_size 4`, 1024² bucketed, `seed 42`.
- Serverless endpoint `uix4vdb2cec7sb` (RunPod, EU-RO-1) runs `runpod/worker-comfyui:5.8.6-base`
  (template `u45jy611b1`) with network volume `pwkmq2gjhw` (20GB) holding
  `illustrious_v0.1.safetensors` (base) and `clawmarks-illustrious-v3-epoch4.safetensors` (LoRA)
  under `/models/checkpoints` and `/models/loras`. ComfyUI auto-detects these at
  `/runpod-volume/models/...` on serverless workers. Submit jobs via
  `POST https://api.runpod.ai/v2/uix4vdb2cec7sb/run` with a ComfyUI API-format workflow JSON (see
  `gen_batch.py`). The endpoint scales to zero and costs little to leave idle, so nothing forces
  its teardown; terminate it only when no more generation is planned.
- RunPod API key: not stored in any durable config file. It has lived only in session
  transcripts; grep prior `.jsonl` transcripts to recover it if lost.

### Gotcha log

- **Duplicate job submission (~500 jobs instead of 250).** Killing a backgrounded Python script
  because its log looked empty (stdout buffering, not an actual stall) let it finish posting most
  of its 250 jobs before it died. Relaunching then double-submitted, leaving roughly 500 total
  jobs queued. RunPod bills GPU-seconds actually run, not queue depth, so the cost impact stayed
  small (about $1-3 wasted), but draining the duplicate backlog before the tracked batch could
  start cost real wall-clock time. Lesson: launch background Python with `-u` (or otherwise force
  unbuffered output) before treating "no log output yet" as a stall.
- **`transformers.CLIPModel.get_image_features()` returns `BaseModelOutputWithPooling`**, not a
  raw tensor, on `transformers` 5.12.0. Fix: append `.pooler_output` before normalizing.
- **`AutoImageProcessor.from_pretrained("facebook/dinov2-base")` raises
  `ImportError: requires Torchvision`.** Rather than install torchvision and risk an unpinned
  package silently touching the pinned CPU-only `torch==2.12.0+cu130` build, fetch the model's
  `preprocessor_config.json` via `huggingface_hub.hf_hub_download` and reimplement the
  resize/crop/normalize pipeline by hand with PIL, numpy, and torch. This avoids the dependency
  entirely.
- **Dataset folder names lie.** A folder named `-v3` held a stale, incomplete (24 of 31 images)
  pre-fix snapshot, while the real corrected captions ended up in a zip confusingly named
  `clawmarks-illustrious-dataset-v2.zip`. Always diff a dataset's actual caption content against
  `caption_check_result.log`'s `MISMATCH:` entries, or rerun the consistency check, before reusing
  a cached dataset folder for training. Never trust the folder name alone.
- **`api.runpod.io/graphql` 403s bare `urllib` requests.** Python's `urllib.request` with no
  explicit `User-Agent` gets a Cloudflare block (`403`, body `error code: 1010`) on this host, even
  though the identical query succeeds via `curl`. The serverless REST host (`api.runpod.ai`)
  hasn't shown this. Fix: always set `User-Agent` (e.g. `"curl/8.0"`) on GraphQL requests.
- **`runpod/pytorch` dropped its old version-numbered image tags.** `2.4.1-py3.11-cuda12.4.1-...`
  (used in `rp_bring_up.py`'s first draft) no longer resolves; Docker Hub now serves mostly
  `1.0.7-rc.*` tags, though some old-style tags (e.g. `2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`)
  still exist. Check `https://hub.docker.com/v2/repositories/runpod/pytorch/tags/<tag>` for a 200
  before trusting an image tag in a pod-creation script; the base image's preinstalled torch
  version doesn't matter anyway since `remote_setup.sh` installs its own pinned venv.
- **kohya's default `caption_extension` is `.caption`, not `.txt`.** This dataset's captions are
  `.txt` files; without `--caption_extension .txt` explicitly, training would silently run with
  empty captions (no error, just an unconditioned LoRA) rather than failing loudly.
- **kohya_ss (`sd-scripts`) imports `torchvision` at module load time**
  (`library/utils.py` -> `library/original_unet.py`), even though this project's own DINOv2
  scoring scripts deliberately avoid it. `remote_setup.sh`'s pinned venv step only installed
  `torch`/`xformers`, so the first real training run failed immediately with
  `ModuleNotFoundError: No module named 'torchvision'`. Fixed by pinning
  `torchvision==0.19.1` (the release matched to `torch==2.4.1`) alongside the other two.
- **`rpssh.py` runs a non-login, non-interactive shell**, so `~/.local/bin` (where `uv` installs)
  isn't on `PATH` even though it's in `.bashrc`. Any one-off remote command that calls `uv`
  directly (outside `remote_setup.sh`, which exports `PATH` itself) needs
  `export PATH=$HOME/.local/bin:$PATH` prepended explicitly.
- **The RunPod `runpod/pytorch` base image has no `unzip`, and `remote_setup.sh`'s dataset step
  ran without `set -e`.** The `unzip` call failed silently, every subsequent `mv`/`rmdir` in that
  step failed too, but the script still reached `touch dataset.done` at the end, marking a failed
  extraction as complete. Fixed by installing `unzip` first and wrapping the extraction step in
  `set -e`/`set +e` so a real failure stops the script before the marker is written, rather than
  silently leaving `/workspace/training/img/` empty on a "successfully" set-up pod.
- **The 780-step full-length figure assumes `train_batch_size 4`, not 1.** 31 images x 10 repeats
  / batch 4 = ceil(310/4) = 78 steps/epoch x 10 epochs = 780. With the outlier now down-weighted
  (30 images x10 repeats + 1 x3 repeats = 303 image-repeats), that's ~76 steps/epoch, close enough
  that probe/calibration runs pass `--max_train_steps` explicitly rather than deriving it from
  epoch count.
- **`train_probe.py`'s remote command redirects all training output to a log file on the pod**
  (`> train.log 2>&1`), so the SSH channel carries zero bytes for the entire ~20-minute training
  run. With no keepalive configured, `dim64_780`'s launch hit a paramiko `socket.timeout` on the
  read side well before the training itself finished, even though the remote process kept running
  unaffected (it was writing to a local file on the pod, not blocked on the client reading
  anything) and completed successfully. The wrapper script's crash meant its checkpoints sat
  un-downloaded until recovered manually. This isn't the `timeout=3600` parameter's intended
  meaning kicking in (the run finished in ~20 min, well under that); it looks like an idle
  network path (a NAT or proxy somewhere between here and the pod) dropping a connection with no
  traffic on it. Fixed by calling `client.get_transport().set_keepalive(30)` in `ssh_client()` so
  the connection sends periodic traffic and doesn't look idle, even while the actual command
  output is silent on the channel.

### Unrelated material in this directory

- `fal-workflow.md`, `fal-workflow-review/`: an unrelated fal.ai workflow-skill review, no part of
  the CLAWMARKS LoRA work.
- `art-style-prompts.md`, `clawmarks-evolve/` (brief.md plus per-model variants and contact
  sheets): an earlier brainstorming round on hand-written per-image captions across multiple LLMs
  (GPT, Opus, Fable, DeepSeek), upstream of the current caption set.
- `clawmarks.safetensors`, `clawmarks_model.json`: an early prototype LoRA and its Civitai listing
  metadata, predating the v1/v2/v3 runs above. Superseded.

---

## 6. Lab log

*(Dated entries go here as rounds run: status, decisions, numbers, surprises.)*

### 2026-07-08: Notebook started, ledger merged in
Design finalized: probe-then-commit search, 5 rounds, directional probes double-replicated
against a measured noise floor, data-side adjustments allowed between rounds, DINOv2 centroid
similarity as the metric throughout. The separate `LEDGER.md` file folded into this notebook's
Section 5 so the project has one running record instead of two. Round 1's noise-floor probes
have not started.

### 2026-07-08: External methodology review drafted
Wrote `reviews/glm_review.md` critiquing `methodology.md` per `reviews/review_prompt.md`. Main
findings to weigh before round 1 runs: the n=2 replicate / n=3 control design cannot estimate
within-direction variance, so the selection rule should become a real two-sample test (Welch's t
or permutation) with controls pooled across rounds; ~10 probes per round at a loose bar needs a
BH correction to avoid spurious wins; 156-step probes finish under one cosine cycle and likely
misrepresent 780-step behavior, so one calibration round checking probe-vs-commit rank
correlation is worth running first; centroid cosine is dragged by the 0.22 outlier and rewards
style collapse, with nearest-neighbor or MMD in DINOv2 space as cheaper fixes; the validation
set used to pick epoch 4 is now being reused to score new configs (double-dipping), and seed
variance likely exceeds prompt variance so the 30-image grid should favor more seeds. Also
flagged: data changes and hyperparameter changes should stay on separate rounds so improvement
stays attributable, and the final human review should rank by a small panel, not the DINOv2
ranking known to disagree with human preference. Review kept under 600 words, no em dashes, ends
with `=== DONE ===`.

### 2026-07-08: External methodology review drafted
Created `reviews/gpt_review.md`, a concise ML-methodology critique of `methodology.md` using the
instructions in `reviews/review_prompt.md`. The review flags weak uncertainty estimates from only
2 replicates, possible 2-epoch to 10-epoch reversal, centroid-metric compression, early commit
risk in sequential search, and the need for holdout prompts plus immediate inspection of the
0.22-similarity training-image outlier.

### 2026-07-08: Probe-length calibration check underway, real training pipeline validated
Brought up the RTX 4090 training pod (`rp_bring_up.py`) and ran the four 156-step probes for
step 1's calibration check: `control` (baseline config), `dim64` (network dim 64 / alpha 32),
`lr2e4` (unet_lr 2e-4), and `constlr` (constant schedule instead of cosine, chosen because a
156-step probe finishes under one of the full run's 780-step / 3-cycle cosine schedule, the
gap this calibration check exists to catch). `control_156`'s final loss (0.109) closely matched
the historical epoch-4 winning run's final loss (0.106), which is real confidence the pipeline
(dataset, checkpoint, hyperparameters) is faithfully reproducing the known-good baseline before
trusting any of the three candidate directions' results. Generated 4 sample images per probe
checkpoint (same 4 prompts, same seed 42, same 28-step DDIM settings) with kohya's own
`sdxl_gen_img.py` directly on the pod, as a visual sanity check before scoring; contact sheet at
`notes/probe_samples/index.html`. No DINOv2/MMD scoring run yet on any checkpoint.

Brought up a second pod (`rp_bring_up2.py`, helper scripts `rpssh2.py`/`rpget2.py`/`rpsftp2.py`,
kept separate from the first pod's `rpssh.py` etc. so both stay independently reachable) to run
the three remaining 780-step full-length runs two at a time instead of serially. `dim64_780`
finished on pod 1 (final loss 0.110). `control_780` (so the baseline has a full-length twin too,
not just the three candidates) and `lr2e4_780` are running now, one per pod; `constlr_780` queued
next on whichever pod frees first.

Clarified the actual plan for step 3's statistical test before running it for real: the noise
floor isn't an assumption, it has to be measured from the pooled control probes' pairwise score
deltas (same fixed prompt/seed slots as every other comparison), and that measured spread is
also what determines how many replicates round 1 needs, via simulating the permutation test at
a few candidate n and checking which one reliably detects a 0.02-cosine injected effect. Neither
has been computed yet; both need the first batch of scored control probes as input. See the
methodology note added to Section 3, step 3, above.

### 2026-07-09: Calibration check (step 1) result: probe-length rankings disagree with full-length rankings

All four directions now have both a 156-step and a 780-step checkpoint. Generated 4 sample
images per checkpoint (fixed prompts, seed 42) with kohya's `sdxl_gen_img.py` and scored every
one against the DINOv2 centroid (`notes/score_probe_samples.py`, scores in
`notes/probe_samples/scores.json`; contact sheet `notes/probe_samples/index.html`).

Centroid-similarity means (n=4 images each):

| direction | 156-step | 780-step |
|---|---|---|
| control | 0.4634 | 0.5159 |
| dim64   | 0.3996 | 0.4164 |
| lr2e4   | 0.4973 | 0.4844 |
| constlr | 0.4995 | 0.3993 |

156-step ranking (best to worst): constlr, lr2e4, control, dim64.
780-step ranking (best to worst): control, lr2e4, dim64, constlr.

Two disagreements, one small and one large. `control` and `lr2e4` swap the #1 spot between
lengths, a ~0.03 gap each way, plausibly inside ordinary noise, though no noise floor has been
measured yet to confirm that. `constlr` swings from **best at 156 steps to worst at 780
steps**, a ~0.10 reversal, the largest gap in the whole table and far larger than any plausible
noise floor given the range these numbers occupy. This is the exact failure mode the calibration
check exists to catch: a constant learning rate looks strong early (still training at full
strength), but never decays the way the cosine schedule does, and by 780 steps that lack of
decay has cost it real quality rather than helped it. `dim64` stayed in last place at both
lengths, the one point of full agreement, and the gap to the other three is large enough (0.06+)
to trust regardless of noise floor.

Verdict, per the methodology's own decision rule (Section 3, step 1): **rankings do not agree,
so 156-step probes cannot be trusted to pick a winner for round 1.** They can still be trusted
to rule out a catastrophically bad direction, the way `dim64` was correctly identified as worst
at both lengths. Practical consequence for round 1's real probe phase (step 2): treat probe
results as a coarse screen, not a ranking to hand to step 3's significance test directly. Any
direction that clears the screen still needs a full 780-step run before being trusted as a
genuine improvement over control, which raises the real GPU-hour cost of round 1 versus the
original plan.

Caveat: this comparison itself is not yet statistically tested. Each checkpoint has one seed
and 4 fixed prompts, no replicate seeds, so there is no measured noise floor to compare the
observed gaps against, only a judgment call that a ~0.03 gap is small and a ~0.10 reversal is
large relative to the score range in this table. Measuring the real noise floor (task in
progress, needs pooled control-only replicates) would let the control/lr2e4 swap specifically be
called noise or real, rather than shrugged at.

### 2026-07-09: Noise floor measured, replicate count (n) derived -- effect-size floor revised from 0.02 to 0.05

Trained two more `control_156` replicates (`controlB_156`, `controlC_156`), identical config to
`control_156`, different random seed only (`train_probe.py` never pins a training seed, so
re-running the same config naturally gives an independent replicate). Generated the same 4
fixed-prompt samples for both (`notes/gen_samples.py`, a new reusable script -- reconstructs the
exact `sdxl_gen_img.py` invocation used for every other checkpoint this round: seed 42, 28-step
DDIM, scale 7.5, 1024x1024, same 4 prompt lines from `/tmp/art_prompts_base_v2.txt`) and scored
all three against the centroid.

Per-image centroid similarity, same config, 3 independent seeds:

| prompt | control | controlB | controlC | range | stdev |
|---|---|---|---|---|---|
| cat | 0.4995 | 0.3797 | 0.4310 | 0.1197 | 0.0601 |
| horse | 0.3023 | 0.2243 | 0.0982 | 0.2041 | 0.1030 |
| tiger | 0.5370 | 0.5264 | 0.6141 | 0.0877 | 0.0479 |
| wolf-cat | 0.5146 | 0.4817 | 0.4615 | 0.0531 | 0.0268 |

Checkpoint-mean spread across the 3 replicates: 0.4634, 0.4030, 0.4012 (stdev 0.0354, max
pairwise diff 0.0621).

Two things stand out. First, the **horse prompt is dramatically noisier than the other three**
(stdev 0.103, more than double cat's 0.060 and nearly 4x wolf-cat's 0.027) -- likely because
"galloping horse" is further from the training distribution (all 31 real images are cats) than
the other three prompts, so its generations land less predictably seed to seed. Second, and
more consequential: **the checkpoint-mean noise floor (stdev ~0.035, max observed swing 0.062)
is bigger than the 0.02-cosine effect-size floor the methodology had assumed** -- meaning that
threshold was never something a real probe-phase comparison could reliably clear, at any
practical replicate count.

Derived the actual replicate count via simulation (sign-flip permutation test, 4000 simulated
trials x 2000 permutations each, per-prompt noise variance from the table above, delta variance
= 2x single-run variance since a direction-vs-control delta carries noise from both sides):

| true effect (cosine) | n=3 | n=4 | n=6 | n=8 |
|---|---|---|---|---|
| 0.02 | 11% | 15% | 19% | 24% |
| 0.05 | 44% | 54% | 74% | 84% |
| 0.08 | 78% | 89% | 98% | 100% |

0.02 is undetectable at any practical n (24% power even at n=8 -- adding more replicates helps
only slowly). **Decision: raise the effect-size floor from 0.02 to 0.05 cosine, and set round
1's replicate count to n=8** (84% power at 0.05, 98%+ at the scale of gaps actually seen in the
calibration table -- dim64's ~0.06 gap, constlr's ~0.10 swing). Updated Section 3 steps 2-3 and
the budget estimate accordingly: n=8 x ~10 directions per round raises probing alone to 8-13
GPU-hours per round, not the earlier 80-110 minutes, so total budget across 5 rounds plus
calibration moves from an estimated 11-13 hours to **45-70 hours**, worth running on two pods in
parallel as calibration already did.

Also worth flagging for later interpretation: this noise-floor estimate itself comes from only
3 replicates (2 degrees of freedom), so it is a rough estimate with real uncertainty of its
own, not a precise population parameter. Revisit it once round 1's pooled control probes (8 more
replicates) accumulate -- the true floor could turn out somewhat higher or lower once more data
exists.

Terminated pod 2 (`9e64aw56psou89`) once `constlr_780` finished downloading; only pod 1
(`cn0zudkxb89or6`) is running now.
