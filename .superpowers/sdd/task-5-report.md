# Task 5 Report: Remove "pick as winner" from the lightbox; add `rate.html`

## Status

DONE

## Summary

Created `src/clawmarks/build/rate_page.py` (generates `rate.html`, the keyboard-driven
yes/no rating page that fetches `/api/rate/next` and POSTs `/api/rate` from the browser
at runtime). Wired `rate_page` into `clawmarks build rate` in `src/clawmarks/cli.py` and
appended `"rate"` to the `build target` argparse choices. Added `("rate.html", "rate
images (yes/no)")` to `NAV_OPTIONS` in `src/clawmarks/shared_ui.py`. Removed every trace
of pick-as-winner from the lightbox: the `.lb-pick` button + its tooltip in the DOM
template, the `#lb-overlay button.picked` CSS rule, the `let picks = {}` state, the
`loadPicks()` fetch, the `el.querySelector('.lb-pick').onclick = togglePick;` wiring, the
spacebar shortcut, the `togglePick()` function, the `isPicked` render block, and the
`/api/picks` call in the `Promise.all` of `open()`. Created `tests/test_rate_page.py`
covering the page generator and added `test_build_rate_subcommand_parses` to
`tests/test_cli.py`.

Pre-implementation run confirmed the expected `ModuleNotFoundError: cannot import name
'rate_page' from 'clawmarks.build'` and an argparse `invalid choice: 'rate'` rejection.
Post-implementation run passes all 5 tests; full suite (38 tests across the repo) also
still passes with no regressions.

The brief's sanity check `grep -rn "lb-pick\|togglePick\|loadPicks" src/` returns nothing.

## git log --oneline

```
405fcad feat(clawmarks): remove pick-as-winner from the lightbox, add rate.html
0620369 feat(clawmarks): replace pick endpoints with ratings endpoints in curation_server
b623363 feat(clawmarks): add one-time picks-to-ratings migration script
b39eb07 feat(clawmarks): add stratified rating sampler
a238381 feat(clawmarks): add shared manifest_index helpers and USER_RATINGS_FILE config
```

## Files changed

```
new file:   src/clawmarks/build/rate_page.py
modified:   src/clawmarks/cli.py
modified:   src/clawmarks/shared_ui.py
modified:   tests/test_cli.py
new file:   tests/test_rate_page.py
```

## Test command and output

Command: `pytest tests/test_rate_page.py tests/test_cli.py -v`

```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0 -- /workspace/trent-with-smart-prompts/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/trent-with-smart-prompts
configfile: pyproject.toml
collecting ... collected 5 items

tests/test_rate_page.py::test_main_writes_rate_html PASSED                 [ 20%]
tests/test_cli.py::test_build_all_subcommand_parses PASSED                 [ 40%]
tests/test_cli.py::test_run_allnight_round_argument_parses PASSED          [ 60%]
tests/test_cli.py::test_serve_subcommand_parses PASSED                     [ 80%]
tests/test_cli.py::test_build_rate_subcommand_parses PASSED                [100%]

============================== 5 passed in 0.08s ===============================
```

Pre-implementation run (snipped to relevant lines):

```
ImportError: cannot import name 'rate_page' from 'clawmarks.build'
ERROR collecting tests/test_rate_page.py
... (in test_cli.py)
argparse: error: argument target: invalid choice: 'rate' (choose from 'all', 'scan', ...)
```

Full-suite sanity check: `pytest` -> 38 passed, no regressions.

Brief's pick-identifier check:

```
$ grep -rn "lb-pick\|togglePick\|loadPicks" src/ | grep -v __pycache__
(no output)
```

## Concerns

None. Implementation is verbatim from the brief. No new dependencies, no edits to files
outside the listed set. `toggleFavorite`, the `.lb-favorite` button, and the favorite
keyboard shortcut are all preserved untouched, per the brief. Stage-5b opt-in flag and
favoriting paths untouched.
