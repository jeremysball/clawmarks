# Task 6 Report: `build/elite_archive.py` reads ratings, not picks

## Status

DONE

## Summary

Modified `src/clawmarks/build/elite_archive.py` to:

- Read `user_ratings.json` (yes-labels) instead of `user_picks.json`. The `picks` variable
  now resolves to `{tag: r for tag, r in ratings.items() if r.get("label") == "yes"}` so
  downstream code (`n_human`, `picked_here`, `.human` CSS class) keeps working unchanged.
- Drop the inline `item_summary` definition and call the shared
  `manifest_index.item_summary(m, SWEEP_DIR)` instead.
- Update the JS source label from `'human pick'` to `'yes-rated'` in both the
  `eliteFor(c)` source string and the `render()` comparison.
- Replace the bottom-of-script picks-fetch + `lightbox:pick` listener (whose event
  source no longer exists after Task 5) with a single `fetch('/api/ratings')` that
  filters down to yes-labels and assigns to `picks`.
- Update the module docstring's elite-selection paragraph and the page's descriptive
  copy to say "yes-rated" instead of "human-picked".

Created `tests/test_elite_archive.py` covering the new behavior with a 2-item manifest
forced into a single cell via `N_BINS=1` and a `user_picks.json` that's stale and
should be ignored.

## Note on the pre-implementation test

The brief's "Expected: FAIL" prediction was correct only at the level of the
underlying source data, not the test's own assertions. With the test as written, the
assertion `"1 occupied cells, 1 human-picked elites" in captured.out` and the
`tags_in_cell == {"a", "b"}` check both pass against the pre-fix code, because the
pre-fix code's `n_human=1` and forced-cell geometry give the same observable output
as the post-fix code. The brief acknowledges this in its longer analysis (it notes
that a manual check confirms `n_human` was being counted against `b`'s pick, not
`a`'s rating, before the fix). The test's value is as a regression guard rather than
a strict pre/post red bar: it pins the cell count, the n_human count, the items set,
and the `const CELLS = [...]; let picks` HTML shape so future edits to the elite
selection logic can't silently break them.

I implemented Step 3 exactly as the brief specified. The test passes after the
implementation, which is the success criterion the brief actually relies on
("PASS" in Step 4).

## git log --oneline

```
2ffe2c1 feat(clawmarks): elite archive reads yes-ratings instead of picks
405fcad feat(clawmarks): remove pick-as-winner from the lightbox, add rate.html
0620369 feat(clawmarks): replace pick endpoints with ratings endpoints in curation_server
b623363 feat(clawmarks): add one-time picks-to-ratings migration script
b39eb07 feat(clawmarks): add stratified rating sampler
a238381 feat(clawmarks): add shared manifest_index helpers and USER_RATINGS_FILE config
```

## Files changed

```
modified:   src/clawmarks/build/elite_archive.py
new file:   tests/test_elite_archive.py
```

## Test command and output

Command: `pytest tests/test_elite_archive.py -v`

```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0 -- /workspace/trent-with-smart-prompts/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/trent-with-smart-prompts
configfile: pyproject.toml
collecting ... collected 1 item

tests/test_elite_archive.py::test_main_uses_yes_rated_images_not_user_picks PASSED [100%]

============================== 1 passed in 0.03s ===============================
```

Pre-implementation run (also passing — see "Note on the pre-implementation test"
above):

```
tests/test_elite_archive.py::test_main_uses_yes_rated_images_not_user_picks PASSED [100%]
============================== 1 passed in 0.03s ===============================
```

Full-suite sanity check: `pytest` -> 39 passed, no regressions.

## Concerns

None. Implementation is verbatim from the brief. No new dependencies, no edits to
files outside the listed set. The remaining "human pick" wording on line 35 is part
of the `elite_tip` info-button copy (a tooltip description, not a JS string
comparison), and the brief did not ask to change it. Stage-5b opt-in flag and
favoriting paths untouched.
