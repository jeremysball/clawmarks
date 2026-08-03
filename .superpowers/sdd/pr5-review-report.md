# Code review: PR #5 — Transition CLAWMARKS tooling into an installable package

Range reviewed: `main..HEAD` (`b2ebe9d..5b87be4`, 19 commits), via the pre-generated diff
`.superpowers/sdd/review-b2ebe9d..5b87be4.diff` plus read-only verification against the worktree.
Test suite run: `uv run pytest -q` → **19 passed**.

## Strengths

- **Path resolution is genuinely centralized where it was adopted.** `src/clawmarks/config.py`
  exposes `repo_root()` with the `CLAWMARKS_ROOT` env override plus a walk-up to `pyproject.toml`,
  and derives `SWEEP_DIR`, `SWEEP2_DIR`, `PROBE_DIR`, `PROBE_STRENGTH_DIR`, `SEEDS_FILE`,
  `USER_PICKS_FILE` from it at import time (`config.py:20-27`). `tests/test_config.py` covers the
  override and derived-path cases. The build modules that adopted it resolve through `config.ROOT`,
  e.g. `uncanny_gallery.py:23` builds `REAL_DIR = f"{ROOT}/corrected_dataset_extract"` from the
  imported `ROOT`.

- **The two extractions called out as newly tested are real, not relocations.**
  `search/scoring.py` (`bin_edges`/`bin_of`/`novelty_from_similarity`) is covered by 4 tests in
  `tests/test_scoring.py`; `search/seed_pool.py` (`load`/`save`/`merge` with case-insensitive
  dedup, including intra-batch dedup) is covered by 5 tests in `tests/test_seed_pool.py`. Both
  are pure functions over their inputs, the right shape to unit test.

- **The allnight merge is parameterized cleanly.** `search/driver.py` replaces two ~90%-identical
  scripts with a `RoundConfig` dataclass and `ROUND_CONFIGS` table, and gates the round-specific
  behavior behind flags: prior-round exclusion embeddings behind `cfg.exclude_prev_round`
  (`driver.py:486`), seed-from-start behind `cfg.seed_from_start` (`driver.py:500`), and round 1's
  staged-escalation plateau logic preserved verbatim in the `else` branch (`driver.py:577-598`).
  `build_generation_jobs` takes `explore_fraction` and `style_subject_count` as parameters, and
  `tests/test_generation_jobs.py` asserts the 0.5 split reproduces round 1's 10/10 behavior and the
  0.85 split yields 17/3, so the merge's "same output, less duplication" claim is pinned by tests.

- **The CLI keeps the parse path light.** `build_parser()` (`cli.py:30`) builds argparse without
  importing the build modules; `_build_targets()` is only called inside `main()`, so
  `tests/test_cli.py` can exercise parsing without torch/transformers installed. The `thumbnails`
  argv fix (`build/thumbnails.py:21-26`, `sweep_dir` defaults to `SWEEP_DIR`) addressed the path
  bug that bit during implementation.

- **Dependency versions are explicitly pinned** (`pyproject.toml:5-11`): `numpy==2.0.0`,
  `pillow==11.0.0`, `torch==2.12.0`, `transformers==4.56.0`. A `uv.lock` is present.

## Issues

### Critical (Must Fix)

1. **Three of six `pod` subcommands silently no-op.** `cli.py:57-60` registers
   `bring-up`, `pause`, `terminate`, `ssh`, `get`, `put` in the parser, but `cli.py:90-99` only
   puts `bring-up`/`pause`/`terminate` in `action_map`. For `ssh`/`get`/`put`,
   `args.pod_action in action_map` is `False`, so control falls to `return 0` with no action and no
   error. The underlying functions exist (`runpod.py:210` `ssh`, `:231` `get`, `:245` `put`) but
   are never invoked. The spec's CLI shape documents all six
   (`docs/.../2026-07-09-software-transition-design.md:98`). A user running `clawmarks pod ssh`
   gets exit 0 and nothing happens, which is worse than a clear error. Wire these branches (prompting
   for `pod_id` plus command/paths) or raise explicitly.

2. **`clawmarks probe train` cannot launch a training run.** The `probe train` subparser is built
   with no arguments (`cli.py:55`), but `probe/train.py:134-135` requires `--name` and
   `--max-train-steps` (`required=True`). Two failure modes follow:
   `clawmarks probe train --name x --max-train-steps 260` fails at the top-level parser, because
   the `train` subparser accepts no flags ("unrecognized arguments"); bare `clawmarks probe train`
   calls `train_main()` (`cli.py:87`) with `argv=None`, so `ap.parse_args(None)` reads `sys.argv` and
   errors on the missing required args. The spec's `clawmarks probe train ...` passthrough is
   therefore unreachable. Forward the trailing args (e.g. parse-known-args at the top level and
   pass `sys.argv` tail to `train_main`) or add the train args to the subparser and forward `argv`.

3. **The old scripts the spec required to be deleted in this PR are still present.** Task 13 (delete
   the superseded `notes/*.py` and root `rp_*.py`) never ran. Verified on disk: 14
   `notes/build_*.py`, `notes/run_uncanny_allnight.py`, `notes/curation_server.py`, `rp_bring_up.py`,
   `rp_bring_up2.py` all still exist; the diff is 9987 insertions / 3 deletions. The spec is
   explicit that deletion must happen in the same PR once identical output is confirmed, "since
   keeping both around risks someone editing the wrong copy"
   (`docs/.../2026-07-09-software-transition-design.md:131-135`). Merging as-is leaves the repo in
   the parallel-old-and-new state the spec said to avoid, and the migration is not actually
   finished.

### Important (Should Fix)

1. **Hardcoded `/workspace/trent-with-smart-prompts/...` paths survive in `compute/runpod.py`.**
   `runpod.py:23-24, 30-32` define `KEY_PATH`, `PUBLIC_KEY`, `DEFAULT_DATASET_ZIP`,
   `DEFAULT_DATASET_DIR`, `DEFAULT_REMOTE_SETUP_SCRIPT` against the sibling checkout's absolute
   path instead of `config.ROOT`. This is precisely the straggler-path class the brief flagged from
   the preference-classifier phase. It also defeats the PR's central goal ("Path config is actually
   centralized, not partially"). Two amplifying problems:
   - `PUBLIC_KEY = open(...).read().strip()` (`runpod.py:24`) runs at import time, so importing
     `clawmarks.compute.runpod` reads a file from disk the moment the module loads. It works today
     only because the literal points at the sibling checkout where the keys live; it would break any
     checkout that lacks `runpod-ssh/` (this worktree has none at its own root).
   - `API_KEY = os.environ["RUNPOD_API_KEY"]` and `CIVITAI_TOKEN = os.environ["CIVITAI_TOKEN"]`
     (`runpod.py:19-20`) also run at import time, so the module is un-importable without `.envrc`
     sourced. The env reads were inherited from the originals, but the import-time file read is new
     brittleness introduced by the merge.
   Fix: derive all five paths from `config.ROOT`, and move the public-key read into `bring_up()`
   rather than the module body. (The `/workspace/...` strings at `runpod.py:99, 161, 168, 172` are
   the remote pod's filesystem, not the local checkout, and are correct.)

2. **The byte-identical smoke check that gates the whole migration never passed.** The spec and
   plan make Task 12 (run the old scripts, run `clawmarks build all`, diff `.html`/`.js` for zero
   differences) the gate for deleting old files and opening the PR. The notebook
   (`notes/lab_notebook.md:1143+`) records that Task 12 instead caused a data-loss incident across
   three attempts, the last destroying every full-resolution PNG, and that "Task 13 never ran and
   no PR was opened." The "package produces identical output" claim is therefore unverified, not
   confirmed. Before deleting the old scripts (Issue Critical #3) or merging, re-run the smoke check
   in full isolation per the patched Task 12: back up both sweep dirs as complete mirrors, run the
   old scripts, restore, run the new package, diff, then restore again.

3. **`pytest` is a runtime dependency.** `pyproject.toml:5-11` lists `pytest==9.1.0` under
   `dependencies`, so every install pulls pytest into the runtime environment. The commit message
   says "add numpy, pillow, torch, transformers as pinned runtime deps"; pytest was not supposed
   to be runtime. Move it to `[project.optional-dependencies]` (a `dev` extra) or a separate dev
   requirement.

4. **`clawmarks build <single>` eagerly imports every build module, including the heavy ones.**
   `_build_targets()` (`cli.py:4-27`) imports all 14 build modules up front on any `build`
   invocation, so a lightweight target like `clawmarks build thumbnails` (needs only PIL) still
   imports `uncanny_gallery`, which pulls `torch`, `numpy`, and `transformers` at module top
   (`uncanny_gallery.py:15-18`). Import only the requested target lazily (e.g. a name-to-module
   map resolved inside the chosen branch), so the heavy ML stack is not a prerequisite for building
   HTML.

### Minor (Nice to Have)

1. **`build all` order is not the historical order and is not demonstrably a dependency order.**
   `cli.py:75-77` iterates `BUILD_TARGETS.values()` in insertion order (scan first, thumbnails
   10th). The pre-transition scripts ran in `notes/build_*.py` glob (alphabetical) order, and the
   spec calls for "every generator in dependency order." No dependency analysis is in evidence; for
   example `scan_gallery` precedes `thumbnails` though `scan.html` references `thumbs/`. This is
   likely harmless (the HTML encodes paths whether or not the files exist yet), but it is unverified
   because the smoke check never ran (see Important #2). Drive the order from an explicit list, or
   at minimum confirm it matches the order that passed a real smoke diff.

2. **The `build` choices list duplicates the `BUILD_TARGETS` keys.** `cli.py:42-44` hardcodes the
   target names, and `cli.py:13-26` defines them again as dict keys. Adding a target needs two
   edits; risk of drift. Derive the `choices` from the same source.

3. **`probe/sweep.py` functions are CLI-orphans.** `run_probe_uncanny`, `run_strength_sweep`, and
   `gen_samples` were moved into `probe/sweep.py` but the CLI exposes only `probe train`. This is
   consistent with the spec (which only documents `probe train`), but those functions are now
   unreachable from the entry point; if they are meant to stay ad-hoc, a one-line note in the module
   would save the next reader from hunting for a subcommand that isn't there.

4. **Generated artifacts under `src/`.** `src/clawmarks.egg-info/` and `__pycache__/` directories
   exist under `src/` from the editable install. They are not in the diff, so they are not staged,
   but confirm `.gitignore` covers `*.egg-info` and `__pycache__` so a future `git add` does not
   sweep them in.

## Recommendations

1. **Wire the missing `pod ssh/get/put` branches** (Critical #1). At minimum, error explicitly
   rather than returning 0.
2. **Fix `probe train` arg forwarding** (Critical #2) so `clawmarks probe train --name X
   --max-train-steps N` works.
3. **Re-run the Task 12 smoke check in full isolation** (Important #2) and confirm zero diffs
   before merging. Use complete-mirror backups; do not narrow backup scope.
4. **Once the smoke check passes, delete the old scripts** (Critical #3) in this same PR, as the
   spec requires.
5. **Replace the five hardcoded paths in `compute/runpod.py`** with `config.ROOT`-derived values
   and move the `PUBLIC_KEY` file read out of module import time (Important #1).
6. **Move `pytest` out of runtime `dependencies`** into a dev extra (Important #3).
7. **Make per-target build imports lazy** so `clawmarks build thumbnails` does not require
   torch/transformers (Important #4).
8. **Resolve the `build all` ordering and the duplicated choices list** (Minor #1, #2).

## Assessment

With fixes. The genuinely substantive work is sound: `scoring` and `seed_pool` are real pure-logic
extractions with tests, the allnight merge is parameterized correctly with behavior pinned by
`test_generation_jobs.py`, and `config` centralizes path resolution for every module that adopted
it. But two subcommands are dead or unusable (`pod ssh/get/put` silently no-op; `probe train` cannot
forward its required args), centralization is incomplete (five surviving hardcoded paths plus an
import-time file read in `runpod.py`), `pytest` is a runtime dep, and most importantly the
migration's defining verification never actually ran: the byte-identical smoke check caused a
data-loss incident instead of passing, so the "identical output" claim is unverified, and the old
scripts the spec mandated for same-PR deletion are still on disk. Fix the broken subcommands and
the `runpod.py` stragglers, re-run an isolated smoke check to a zero-diff result, then delete the
old scripts before merging.