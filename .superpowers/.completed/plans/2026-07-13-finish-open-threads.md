# Finish the open threads (supersedes 2026-07-13-close-open-threads.md)

Written 2026-07-13, against `main` at `add745c` (the merge that reconciled the diverged
fix and cockpit lines).

## Why this plan replaces the last one

The previous plan (`4ea765b`, on `feat/close-open-threads`) was written while `main` and
`origin/main` had **diverged**, so its task statuses were judged against a tree that was
missing half the work. Re-audited against the merged `main`, with file-level evidence:

- **Tasks 1 and 2 are DONE.** The CV-leakage split, pair-judgment consolidation, paramiko
  dependency, and the `torch.maximum` fix all landed in the merge.
  (`preference_pairwise_model.py:50-71,123-153`, `pyproject.toml:5-12`, `driver.py:441-445`)
- **Four open tasks are already implemented on branches nobody merged.** Merging them is
  cheaper than rewriting them, and it is the whole of Phase 1 below.
- **`feat/preference-retrain-ui` is already in main** by content. Delete the branch; do not
  merge it.

Net: 2 tasks done, 4 tasks one merge away, 5 tasks genuinely unwritten.

## Phase 1: merge what already exists (unblocks 4 of 9 open tasks)

Each branch below is complete work sitting unmerged. `main` is protected, so each needs a
PR. Merge in this order; the first two touch `driver.py` and will conflict with each other
if reversed.

| # | Branch | Closes | Evidence it is real work |
|---|--------|--------|--------------------------|
| 1.1 | `feat/close-open-task3` | Task 3 | atomic writes + state validation, `driver.py:301-404,699-816` |
| 1.2 | `feat/close-open-task7` | Task 7 | corrected MMD p-value + power analysis |
| 1.3 | `fix/xss-json-in-script` | Task 4 | `json_script` escaping, `shared_ui.py:18`, `scan_gallery.py:67` |
| 1.4 | `origin/docs/tailscale-bind-recommendation` | Task 5 | `CLAWMARKS_HOST` binding, `curation_server.py:828-829` |

For each: rebase onto current `main`, run the suite **with secrets stripped**
(`env -u RUNPOD_API_KEY -u CIVITAI_TOKEN uv run pytest -q`, which is what CI sees), open a
PR, merge on green.

Then: `git branch -D feat/preference-retrain-ui feat/close-open-task1 feat/close-open-task4`.
The first is already in main by content; the last two are empty branches that were never
started, and they read as in-flight work until deleted.

**Verification for Phase 1:** re-run the audit. Tasks 3, 4, 5, and 7 must show DONE with
file-level evidence in `main`, not "merged the branch".

## Phase 2: the five tasks that are genuinely unwritten

Ordered by "what breaks if it stays open", worst first. Each is a separate branch and PR.

### Task 6: transactional writes in the recovery scripts (data-integrity)

Highest priority: this is the class of bug that already destroyed a full sweep of
RunPod-billed output once. `score_manifest.py:110-124` **drops manifest entries whose files
are missing** and overwrites the manifest in place; `merge_round2.py:60-99` writes the
manifest and cache non-transactionally. A crash mid-write leaves the only copy truncated.

- Write to a temp file in the same directory, then `os.replace` (atomic on POSIX).
- Never drop an entry to "clean" a manifest. Missing file means quarantine the entry and
  report it, not delete it.
- Test: kill the write partway (monkeypatch `os.replace` to raise) and assert the original
  manifest is intact and parseable.

### Task 8: move the retrain off the request lock

`curation_server.py:975-991` retrains synchronously while holding `_lock`, so every other
request blocks for the duration of a model fit. Move the fit to a worker, keep the lock only
for the state swap. Also reconcile the two gates the plan already flagged: the status page
counts raw comparisons while the retrain gate counts *usable* ones, so the UI can promise a
retrain that never fires.

### Task 9: counterfactual `n` and progressive images

`/api/counterfactual` is single-result (`curation_server.py:1127-1187`). Accept `n` (default
1, cap 6), turn the result panel into a small clickable grid, add `mountProgressive()` in
`shared_ui.py`, and add a `/real_thumbs/<name>` route mirroring the existing `/thumbs/`
on-demand cache. **Cache to a scratch dir under `SWEEP_DIR`, never into
`corrected_dataset_extract/`, which is read-only reference data.**

Note: the generation-cockpit spec depends on this `n` extension. It is the unblocker for
that whole thread.

### Task 10: launch and monitor a search run from the UI

No `run_manager.py`, no `run_status.py`, no run routes (`curation_server.py:937`); the cockpit
still starts an ad-hoc thread at `curation_server.py:1101`. Build: pre-launch backup+verify,
balance floor, a one-run-at-a-time lock file, detached subprocess, pollable status, stop
button. The 2026-07-12 overnight-search-launch spec has the design; its one unresolved
question (does `driver.py` run from this sandbox or on a RunPod pod over SSH?) must be
answered before coding, not during.

Also add the per-run report the notebook keeps asking for: novelty trajectory, plateau count,
spend, pick rate by category, explore-vs-exploit split.

### Task 11: repo hygiene

Delete the two rejected specs (`2026-07-11-toml-config-design.md`,
`2026-07-11-ui-redesign-design.md`). Add `*.backup_candidate_seeds_*` to `.gitignore:44`;
two such directories (196 MB each) were left untracked in the tree and had to be deleted by
hand. Reconcile `TODO.txt` with reality: it is gitignored, has no history, and was 35 commits
stale when last read. Fold anything permanent into the lab notebook.

## Phase 3: the gates that need a human, not a commit

These are not coding tasks and should stop being listed alongside them.

- **Preference validation.** Browse `preference_rank.html` against the 61-rating model and
  confirm it matches taste before flipping either Stage 5b flag. Blocking: `cv_accuracy`
  0.6691 against a ~0.54-0.58 chance baseline is only modestly better than a coin. Decide
  whether that is trustworthy or whether more labels are needed first.
- **Round-1 sign-off.** The 8-direction slate (alpha32, dim16, snr1, snr20, clipskip1,
  telr_match, telr_freeze, cycles1) needs approval before any paid run. `cycles1` still needs
  its own probe length; its 1-cycle schedule spans 780 steps, not 260.
- **Round 2 review.** All 280 images from the explore-heavy run are unreviewed. Every one of
  the 39 elite picks came from round 1, so the round1-vs-round2 comparison the run was built
  to test has never been made.
- **Reference photo.** Resolve whether one of the artist exists; the near-term reveal branch
  is blocked on it.

## Verification for the whole plan

Nothing counts as done on a green workflow file alone.

1. `env -u RUNPOD_API_KEY -u CIVITAI_TOKEN uv run pytest -q` passes (CI's real condition; the
   suite could not even be *collected* without secrets until `tests/conftest.py` seeded
   placeholders).
2. `uv run ruff check src tests` and `uv run mypy src` pass (CI's exact scope).
3. Any UI change gets a live Playwright check against a restarted `curation_server.py`, per
   CLAUDE.md. A passing suite says nothing about whether a page renders.
4. Re-run the task audit against `main` and require file-level evidence per task.
