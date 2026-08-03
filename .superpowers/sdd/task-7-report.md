# Task 7 Report: `search/driver.py` exploit pool reads yes-ratings (Stage 5a)

## Status

DONE

## Summary

Modified `src/clawmarks/search/driver.py` to:

- Add `from clawmarks.search.manifest_index import index_by_tag` near the top of the
  imports.
- Replace `_load_user_picks()` with `_load_yes_rated_images()`. The new function reads
  `user_ratings.json`, filters down to tags whose `label == "yes"`, joins them against
  `scored_manifest.json` via `index_by_tag`, and returns the manifest entries for those
  tags (recovering the full prompt/strength/cfg metadata that the ratings file alone
  doesn't carry). Returns `[]` early if either file is missing or there are no yes tags.
- Update the call site in `main()` to invoke `_load_yes_rated_images()`. The local
  variable `user_picks` and `build_generation_jobs`'s `user_picks` parameter both keep
  their names (the parameter is an internal "exploit seed pool" name; renaming it is out
  of scope per the brief).

Created `tests/test_yes_rated_images.py` covering the join against the manifest (yes +
no mixed) and the empty-fallback case (no files on disk).

Pre-implementation run confirmed the expected `AttributeError: module
'clawmarks.search.driver' has no attribute '_load_yes_rated_images'` for both new
tests. Post-implementation run passes both; full suite (41 tests across the repo) also
still passes with no regressions.

The brief's sanity check `rg -n "_load_user_picks|user_picks.json" src/` returns only
the expected matches in `config.py` and `migrate_picks_to_ratings.py` — those still
read the historical file on purpose, and the brief explicitly says they're correct.

## Working-directory note

Tasks 1-6 were committed on the `preference-classifier-phase-1` worktree at
`/workspace/trent-phase1-worktree/`, while the main directory
`/workspace/trent-with-smart-prompts/` is on a different branch (`clawmarks-package-
transition`) that doesn't have those commits. The Python environment is shared via a
symlinked `.venv` and editable-installs `clawmarks` against the main directory's
`src/`. To run pytest against the worktree's Tasks 1-6 + 7 code, I exported
`PYTHONPATH=src` for each pytest invocation in this task, so the worktree's `src/` is
imported in preference to the main directory's. The commit was made on
`preference-classifier-phase-1` in the worktree as Task 7's brief requires.

## git log --oneline (worktree, preference-classifier-phase-1)

```
0a1cd76 feat(clawmarks): search driver exploit pool reads yes-ratings instead of picks
2ffe2c1 feat(clawmarks): elite archive reads yes-ratings instead of picks
405fcad feat(clawmarks): remove pick-as-winner from the lightbox, add rate.html
0620369 feat(clawmarks): replace pick endpoints with ratings endpoints in curation_server
b623363 feat(clawmarks): add one-time picks-to-ratings migration script
b39eb07 feat(clawmarks): add stratified rating sampler
a238381 feat(clawmarks): add shared manifest_index helpers and USER_RATINGS_FILE config
```

## Files changed

```
modified:   src/clawmarks/search/driver.py
new file:   tests/test_yes_rated_images.py
```

## Test command and output

Command: `cd /workspace/trent-phase1-worktree && PYTHONPATH=src pytest tests/test_yes_rated_images.py tests/test_generation_jobs.py -v`

```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0 -- /workspace/trent-with-smart-prompts/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/trent-phase1-worktree
configfile: pyproject.toml
collecting ... collected 6 items

tests/test_yes_rated_images.py::test_load_yes_rated_images_joins_ratings_against_manifest PASSED [ 16%]
tests/test_yes_rated_images.py::test_load_yes_rated_images_returns_empty_without_files PASSED [ 33%]
tests/test_generation_jobs.py::test_batch_splits_by_explore_fraction PASSED    [ 50%]
tests/test_generation_jobs.py::test_fifty_fifty_split_matches_round_one_behavior PASSED [ 66%]
tests/test_generation_jobs.py::test_exploit_jobs_prefer_user_picks_over_elites PASSED [ 83%]
tests/test_generation_jobs.py::test_no_elites_and_no_picks_produces_only_explore_jobs PASSED [100%]

============================== 6 passed in 0.05s ===============================
```

Pre-implementation run (both new tests fail with the expected AttributeError):

```
AttributeError: module 'clawmarks.search.driver' has no attribute '_load_yes_rated_images'
============================== 2 failed in 0.11s ===============================
```

Full-suite sanity check (`PYTHONPATH=src pytest`): 41 passed, no regressions.

Brief's pick-identifier check (`rg -n "_load_user_picks|user_picks.json" src/`):

```
src/clawmarks/config.py:27:USER_PICKS_FILE = SWEEP_DIR / "user_picks.json"
src/clawmarks/search/migrate_picks_to_ratings.py:1:"""One-time migration: user_picks.json entries become user_ratings.json entries with
```

(Only the historical-file reads remain, as the brief expects.)

## Concerns

None. Implementation is verbatim from the brief. No new dependencies, no edits to
files outside the listed set. `build_generation_jobs`'s `user_picks` parameter kept its
name, per the brief's "out of scope" call-out. Stage-5b opt-in flag and favoriting
paths untouched.
