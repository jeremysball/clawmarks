# Code review: PR #6, Tasks 9-13 (preference model training through end-to-end verification)

Range reviewed: `cefa215..ef8db3b` (5 commits). This is the first review of Tasks 9-13, which
were completed by an unattended process after Tasks 1-8 had already gone through a full review
cycle plus an independent GLM whole-branch review.

I read the full pre-generated diff, the five task specs in
`docs/superpowers/plans/2026-07-09-preference-classifier.md`, the four test files, the changed
source modules, ran the suite (`PYTHONPATH=src uv run pytest -q` → 66 passed), and verified
specific claims with read-only shell commands. I did not modify any file, and I did not touch
`notes/uncanny_sweep*` or the other worktrees.

---

## Strengths

- **The opt-in contract is honored at every gate I checked.** The Stage 5b flag defaults to
  `False` in all three places it appears: `driver.py:485` (`action="store_true", default=False`),
  `elite_archive.py:239`, and `cli.py:49`. Each code path that loads or uses the predicted
  preference (the `_predicted_preference_pool` block at `driver.py:598`, the predicted-score
  block at `elite_archive.py:269`) is guarded by both the flag *and* an `os.path.exists` check on
  the model file, so a missing model is a no-op, not a crash. When the flag is off the code is
  byte-for-byte the prior Stage 5a behavior. The fallback messages (`driver.py:605`) print when
  the flag is set but no model exists, rather than silently doing nothing. This is the single
  most important contract in this range and it holds.

- **The data-leakage concern in the accuracy metric is handled correctly.** `cross_validate`
  (`preference_model.py:42`) reports mean cross-validated accuracy: LeaveOneOut below
  `MIN_LABELS`, 5-fold `StratifiedKFold` at or above it. The reported number is therefore an
  honest held-out estimate, not in-sample fit. The model is a linear `LogisticRegression` on
  frozen DINOv2 embeddings (`preference_model.py:73`), not a high-capacity head, so the classic
  "tiny label set, huge head" overfit failure mode is structurally avoided; the `MIN_LABELS=50`
  floor adds a second guardrail. This matches the spec's intent.

- **DINOv2 is genuinely frozen.** `preference_model.py` consumes `embed_cache.load_cache`
  (precomputed `.npz`) and never backprops into or reloads the DINOv2 weights. `train()` fits a
  linear classifier on top of a fixed feature array. No fine-tuning occurs, per the plan.

- **Task 13 avoided the live-data hazard entirely.** Given the project's documented data-loss
  history, the right call was made: Task 13 committed a 100-image *fixture* under
  `tests/fixtures/sample_sweep/` and a thumbnail fallback in `embed_cache.py:111-116` rather than
  re-running the pipeline destructively against `notes/uncanny_sweep/`. The commit (`ef8db3b`)
  adds no destructive writes to any live data directory. The thumbnail fallback is also a
  thoughtful permanent fix for the lost-full-res situation.

- **Pure functions are genuinely pure and well-tested.** `elite_sort_key` and
  `build_item_summary` (Task 12) and `build_ranked_items` (Task 10) are unit-tested in isolation
  with synthetic inputs, not just imported. `test_elite_archive_predicted_preference.py` covers
  the neutral-fallback edge case (a tag missing its own score while others have scores) that the
  docstring calls out, and `test_build_ranked_items_skips_tags_missing_from_manifest` covers the
  ghost-tag case. These are behavior tests, not smoke tests.

---

## Issues

### Critical (Must Fix)

None. Nothing in this range breaks on merge, silently flips a default, loses functionality, or
risks live data. The opt-in contract (the critical contract for this range) holds, and the
suite passes.

### Important (Should Fix)

1. **The `--use-predicted-preference` flag is not wired through the `clawmarks run allnight`
   CLI path.** Task 11's interface (plan line 1947) promises "a new `--use-predicted-preference`
   CLI flag on `clawmarks run allnight`." The flag was added to `driver.main`'s own argparse
   (`driver.py:485`), but `cli.py:92` dispatches the run command as
   `driver_main(["--round", str(args.round)])` with no forwarding, and the `run allnight`
   subparser (`cli.py:56-58`) defines only `--round`. So `--use-predicted-preference` is
   reachable only via `python -m clawmarks.search.driver ...`, never via the documented
   `clawmarks run allnight` invocation. This is not a safety problem (the default stays off), but
   it means Stage 5b in the *live search* driver is effectively inaccessible from the project's
   own CLI, which defeats the point of the flag. Wire it through: add the argument to the
   `allnight` subparser and forward it in the `run` branch.

2. **`build <non-archive-target> --use-predicted-preference` forwards the flag to targets that
   do not accept it.** `cli.py:82-87` builds `extra_argv = ["--use-predicted-preference"]` and
   passes it to whichever target is invoked, not just `archive`. Most build targets
   (`rate_page`, `scan_gallery`, `coverage_map`, `preference_rank`) ignore `argv` entirely, so
   they are unaffected; but `thumbnails.main` (`thumbnails.py:22-25`) parses `argv` with
   `ArgumentParser`, and a future target that does likewise would raise
   `unrecognized arguments`. The help text says "archive target only," but nothing enforces that.
   Only forward `extra_argv` when `args.target == "archive"`; for everything else pass `[]`.

3. **No guard against single-class (or class-count-below-fold-count) training data.** Both
   `cross_validate` and `train` assume both `yes` and `no` labels are present in usable counts.
   `StratifiedKFold(n_splits=5)` raises if any class has fewer than `n_splits` members, and
   `LogisticRegression.fit` fails on a single-class `y`. The `MIN_LABELS=50` floor counts total
   labels, not per-class, so a dataset of 50+ ratings that are all `yes` (the natural state
   right after the picks-to-ratings migration, which produces *only* yes-labels, per Task 13
   Step 7) passes the floor and then crashes inside sklearn. The current plan dodges this only
   because the post-migration count is ~40 (below the floor) and the task explicitly says "do
   not train yet." The moment the owner rates 50+ images without enough `no` labels, `main()`
   will throw an uncaught sklearn exception instead of a friendly message. Add a check that both
   classes are present (and that the minority class has at least `n_splits` for the chosen CV) and
   print a clear "need both yes and no labels" refusal otherwise.

4. **Hardcoded absolute paths in the committed fixture manifest.**
   `tests/fixtures/sample_sweep/notes/uncanny_sweep/scored_manifest.json` contains 100 entries
   whose `"file"` field is a hardcoded absolute path rooted at
   `/workspace/trent-with-smart-prompts/...` (the *other* worktree, which this review was
   explicitly told not to touch). This is exactly the straggler-hardcoded-path class that two
   prior review passes caught. These are fixture-data paths, not source-code paths, and no test
   currently imports the fixture (see Issue 5), so it is inert today; but if a future test does
   load it through `embed_cache.main`'s `SWEEP_DIR / by_tag[tag]["file"]`, the absolute RHS wins
   the `Path` join and silently points at the main checkout's (partially destroyed)
   `notes/uncanny_sweep`, not the fixture. Rewriting the fixture paths to be relative, or
   generating them from `SWEEP_DIR` in a test fixture, removes the landmine. This also bears on
   focus area 6 (all paths from `clawmarks.config`), which the fixture currently violates in
   spirit.

### Minor (Nice to Have)

5. **The Task 13 fixture is checked in but unreferenced by any test.** `rg "sample_sweep|fixtures"`
   in `tests/` and `src/` returns no hits outside the fixture directory itself. Task 13's
   "verification" was a manual run documented in the commit message; the fixture exists so the
   run can be reproduced, but nothing automates it. An end-to-end test that points `SWEEP_DIR`
   at the fixture (via monkeypatch) and runs the migration → embed → archive → rate path would
   make Task 13's claim verifiable rather than asserted. Given the project's history of a
   smoke-check that caused a real data-loss incident, a real integration test here would be worth
   more than the 100 binary thumbnails currently committed.

6. **The `Unknown solver options: iprint` warning is harmless.** It comes from
   `sklearn/linear_model/_logistic.py:451` calling `scipy.optimize.minimize` with an `iprint`
   key that the installed scipy rejects; this PR's code never sets `solver`, `iprint`, or any
   optimizer option (only `max_iter=1000`), so the default `lbfgs` solver runs normally and
   `max_iter` does take effect. It is a sklearn-1.6.1 ↔ scipy version interaction, not a sign
   that the intended config is being ignored. Suppressing it (or pinning a compatible scipy) would
   quiet the 11-warning test output but is cosmetic.

7. **In-sample predictions appear in the ranking view.** `train()` fits on all labeled images,
   then `preference_rank.main` and `elite_archive` score the *entire* cache, including the
   images the model was trained on. For a "does the top of this list look like things I like"
   sanity gate that is acceptable, but the scores on training images are in-sample and will tend
   to be overconfident. The whitepaper should distinguish the cross-validated accuracy (honest)
   from the ranking-view scores (partly in-sample), or the gate could exclude training images
   from the ranked view. Not a code bug; a methodology clarity point.

8. **Enabling Stage 5b fully replaces the human-pick pool, not a blend.** `driver.py:598-603`
   sets `user_picks = predicted_pool`, discarding `_load_yes_rated_images()` entirely when both a
   model and the flag exist. That matches the spec ("instead of yes-rated images"), but it means
   the owner's actual human ratings stop contributing to the exploit pool the moment the model is
   turned on. Worth a sentence in the notebook/paper noting this is a deliberate substitution,
   and worth considering whether a union (predicted pool plus any yes-ratings not already in it)
   would better preserve the human signal. Not a defect.

---

## Recommendations (ordered by priority)

1. Fix Issue 1: wire `--use-predicted-preference` through the `clawmarks run allnight` subparser
   and forward it in the `run` branch of `cli.py`, so Stage 5b is reachable from the project CLI.
2. Fix Issue 2: only pass `extra_argv` to the `archive` target; pass `[]` to all others.
3. Fix Issue 3: check for both classes before CV/training and refuse with a clear message when
   the minority class is absent or below the fold count.
4. Fix Issue 4: replace the hardcoded absolute paths in the fixture manifest with relative paths
   or a generated fixture.
5. (Optional) Add Issue 5's integration test so Task 13's end-to-end claim is automated, not just
   documented in a commit message.
6. (Optional) Suppress or document the harmless `iprint` warning (Issue 6) and clarify the
   in-sample nature of the ranking scores in the whitepaper (Issue 7).

---

## Assessment

**Ready to merge: with fixes.** The critical contract (Stage 5b opt-in, flag-off-by-default) is
intact and the suite passes, so merging would not break anything or silently change behavior. But
the range ships an incomplete feature: the headline `clawmarks run allnight
--use-predicted-preference` flag the plan promises is not reachable from the CLI (Issue 1), which
makes the live-search half of Stage 5b a dead path despite being implemented and tested at the
module level. Combined with the latent single-class crash (Issue 3, which the project's
yes-only-after-migration state makes plausible the moment the label count clears 50), these are
worth resolving before merge rather than after. Issues 2 and 4 are smaller hygiene fixes that
clean up the same "flag/forwarding not fully wired" theme. None of this touches the live
`notes/uncanny_sweep*` data; Task 13 correctly used a committed fixture and a thumbnail fallback.