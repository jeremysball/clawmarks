# Task 8 Report: DINOv2 embedding cache

## Status

DONE_WITH_CONCERNS

## Summary

Created `src/clawmarks/search/embed_cache.py` with the DINOv2 embedding cache module —
`preprocess`, `embed_paths`, `load_cache`, `save_cache`, `missing_tags`, `sync`, and
`main`, plus the `EMBEDDINGS_FILE` constant and `MODEL_ID` constant. Created
`tests/test_embed_cache.py` covering the shape/normalization of `embed_paths` output
(via a deterministic `FakeModel` that derives embeddings from mean pixel value), the
save/load round-trip, the missing-file load fallback, `missing_tags`, `sync`'s
add-only-missing-and-persist behavior across two sync calls, and `sync`'s
`FileNotFoundError` on a manifest tag whose image file is missing.

Pre-implementation run confirmed the expected `ImportError: cannot import name
'embed_cache' from 'clawmarks.search'`. Post-implementation run passes all 6 tests;
full suite (`PYTHONPATH=src pytest`) -> 47 passed, no regressions.

## Concern: brief's `save_cache` had a `np.savez` lazy-write bug

The brief's exact `save_cache` body — `np.savez(tmp, ...); os.replace(tmp, path)` —
fails at runtime because `np.savez` doesn't flush the underlying file to disk before
returning (it returns a `np.lib.npyio.NpzFile` and the file is closed only on garbage
collection or explicit close). The very next line, `os.replace`, raises
`FileNotFoundError` because the `.tmp` file doesn't physically exist yet.

Reproduced outside the test:

```
$ python -c "import numpy as np, os; np.savez('/tmp/x.tmp', a=np.array([1])); print(os.path.exists('/tmp/x.tmp'))"
False
```

The brief's "transcribe it, don't redesign it" rule is about the high-level structure
of the module (interfaces, signatures, control flow, docstring). To get the test to
pass — which the brief itself requires in Step 4 — I made a one-line bug fix:
wrap `np.savez` in a `with open(tmp, "wb") as f:` block. This is the documented
file-object form of `np.savez` and has the side effect of closing (and thus flushing)
the file before `os.replace` runs. The atomic-write intent is preserved unchanged;
the only difference from the brief is that the file is now flushed at the right
moment.

```python
def save_cache(path, tags, embeddings):
    tmp = str(path) + ".tmp"
    with open(tmp, "wb") as f:
        np.savez(f, tags=np.array(tags), embeddings=np.asarray(embeddings, dtype=np.float32))
    os.replace(tmp, path)
```

I'd recommend the spec maintainer update the plan's snippet to this form so future
implementations of this task don't trip the same trap.

## Working-directory note (same as Task 7)

Implemented on the `preference-classifier-phase-1` worktree at
`/workspace/trent-phase1-worktree/`. Tests run with `PYTHONPATH=src` so the
worktree's `src/` is imported in preference to the shared-venv install that points at
the main directory's older code. Commit landed on `preference-classifier-phase-1`.

## git log --oneline (worktree, preference-classifier-phase-1)

```
e228bc3 feat(clawmarks): add DINOv2 embedding cache
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
new file:   src/clawmarks/search/embed_cache.py
new file:   tests/test_embed_cache.py
```

## Test command and output

Command: `cd /workspace/trent-phase1-worktree && PYTHONPATH=src pytest tests/test_embed_cache.py -v`

```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0 -- /workspace/trent-with-smart-prompts/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/trent-phase1-worktree
configfile: pyproject.toml
collecting ... collected 6 items

tests/test_embed_cache.py::test_embed_paths_returns_one_normalized_row_per_path PASSED [ 16%]
tests/test_embed_cache.py::test_save_and_load_cache_round_trips PASSED     [ 33%]
tests/test_embed_cache.py::test_load_cache_missing_file_returns_empty PASSED [ 50%]
tests/test_embed_cache.py::test_missing_tags_returns_manifest_tags_not_in_cache PASSED [ 66%]
tests/test_embed_cache.py::test_sync_adds_only_missing_tags_and_persists PASSED [ 83%]
tests/test_embed_cache.py::test_sync_raises_on_missing_image_file PASSED   [100%]

============================== 6 passed in 1.77s ===============================
```

Pre-implementation run (snipped):

```
ImportError: cannot import name 'embed_cache' from 'clawmarks.search'
(/workspace/trent-phase1-worktree/src/clawmarks/search/__init__.py)
ERROR collecting tests/test_embed_cache.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!!
```

First run after verbatim transcription (snipped) — these were the two failures that
motivated the one-line fix in `save_cache`:

```
src/clawmarks/search/embed_cache.py:99: in sync
    save_cache(cache_path, all_tags, all_embeddings)
...
>       os.replace(tmp, path)
E       FileNotFoundError: [Errno 2] No such file or directory:
            '.../embeddings.npz.tmp' -> '.../embeddings.npz'

FAILED tests/test_embed_cache.py::test_save_and_load_cache_round_trips
FAILED tests/test_embed_cache.py::test_sync_adds_only_missing_tags_and_persists
============================== 2 failed, 4 passed in 2.17s ===============================
```

Full-suite sanity check (`PYTHONPATH=src pytest`): 47 passed, no regressions.

## Concerns

1. The `save_cache` fix described above. Status is `DONE_WITH_CONCERNS` because of
   this single deviation from the brief's verbatim code, even though the deviation is
   the minimum change needed for the brief's own tests to pass.
