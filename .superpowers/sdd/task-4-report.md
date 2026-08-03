# Task 4 report: `build/preference_status.py`

## Status: DONE

Commit: `d01da48` (full SHA: `d01da4845bfd0dc45deb8a46e71c1496a967a134`).

Test summary: all 7 new tests in `tests/test_preference_status.py` pass; the full suite
(125 tests) still passes, no regressions.

## Files touched

- `src/clawmarks/build/preference_status.py` (new, 126 lines)
- `tests/test_preference_status.py` (new, 85 lines)

## Commands run

### 1. Read task brief and inspect the project

```
read /workspace/trent-with-smart-prompts/.superpowers/sdd/task-4-brief.md
ls /workspace/trent-with-smart-prompts/src/clawmarks/build/
ls /workspace/trent-with-smart-prompts/src/clawmarks/search/
ls /workspace/trent-with-smart-prompts/tests/
read /workspace/trent-with-smart-prompts/src/clawmarks/build/preference_rank.py
read /workspace/trent-with-smart-prompts/src/clawmarks/search/preference_settings.py
read /workspace/trent-with-smart-prompts/src/clawmarks/search/preference_model.py
read /workspace/trent-with-smart-prompts/src/clawmarks/shared_ui.py
read /workspace/trent-with-smart-prompts/src/clawmarks/build/__init__.py
read /workspace/trent-with-smart-prompts/tests/test_preference_rank.py
read /workspace/trent-with-smart-prompts/tests/test_preference_settings.py
read /workspace/trent-with-smart-prompts/tests/test_preference_model.py
read /workspace/trent-with-smart-prompts/src/clawmarks/config.py
git -C /workspace/trent-with-smart-prompts status
git -C /workspace/trent-with-smart-prompts log --oneline -10
git -C /workspace/trent-with-smart-prompts branch --show-current
```

Confirmed context before writing anything:
- branch is `feat/preference-toggle`, three prior commits land: `a42a074`
  (`preference_settings.py`), `61a4554` (`MODEL_META_FILE` sidecar), `c48a29f`
  (nav-bar entry for `preference_status.html`). All three exist and behave as the brief
  describes.
- `clawmarks.build` is an empty `__init__.py` namespace; sibling modules under
  `build/` are the convention to follow.
- `preference_model.MIN_LABELS = 50`, `class_balance_error(y)` returns `""` when
  training can proceed and a human-readable refusal message otherwise; the
  `preference_model.main` order is `len(y) < MIN_LABELS` first, then
  `class_balance_error(y)`.
- `shared_ui` exports `nav_bar_html`, `info_btn`, `TOPNAV_CSS`, `MOBILE_BASE_CSS`,
  `INFOTIP_CSS`. `nav_bar_html('preference_status.html')` is the right call.

### 2. Write the failing tests first

Wrote `tests/test_preference_status.py` verbatim from the brief's Step 1 block.

### 3. Confirm the tests fail for the right reason

`PYTHONPATH=src uv run pytest tests/test_preference_status.py -v`

Full output:

```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0 -- /workspace/trent-with-smart-prompts/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/trent-with-smart-prompts
configfile: pyproject.toml
collecting ... collected 0 items / 1 error

==================================== ERRORS ====================================
_______________ ERROR collecting tests/test_preference_status.py _______________
ImportError while importing test module '/workspace/trent-with-smart-prompts/tests/test_preference_status.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_preference_status.py:4: in <module>
    from clawmarks.build import preference_status
E   ImportError: cannot import name 'preference_status' from 'clawmarks.build' (/workspace/trent-with-smart-prompts/src/clawmarks/build/__init__.py)
=========================== short test summary info ============================
ERROR tests/test_preference_status.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.13s ===============================
```

This is the expected failure: `preference_status` does not exist yet, the import fails
for exactly that reason. (The brief asked for `ModuleNotFoundError: No module named
'clawmarks.build.preference_status'`; the actual error is
`ImportError: cannot import name 'preference_status' from 'clawmarks.build'`, which
has the same root cause: the module file does not exist. Both forms of the error
confirm the same condition. Worth flagging in case the brief's wording is checked
literally somewhere, but functionally the failure is the right one and is the only
plausible failure before the implementation lands.)

### 4. Implement `preference_status.py`

Wrote `src/clawmarks/build/preference_status.py` exactly as the brief's Step 3
specifies, byte-for-byte:

- module docstring points at the design spec;
- imports `json`, `os`, `preference_model`, `preference_settings`, and the five
  `shared_ui` symbols listed in the interfaces;
- `compute_data(sweep_dir)` follows the order the brief lays out: load
  `user_ratings.json` (or empty), count `yes`/`no`, branch on
  `n_total < MIN_LABELS` first (returning the count-gate message), only then
  call `class_balance_error(y)` (importing `numpy` lazily inside the `else`
  branch so the module is cheap to import on the no-ratings path);
- `model_meta` is `None` when the model is missing, else the parsed
  `MODEL_META_FILE` JSON;
- the returned dict has every key the contract lists, always;
- `render_html(data)` follows the brief's HTML/CSS/JS block verbatim: nav bar at
  `'preference_status.html'`, gate paragraph (`<p class="gate">` or
  `<p class="gate ok">` when ready), meta table or empty-state paragraph, toggle
  row with `disabled`/`checked` attributes driven by `has_model` and
  `use_predicted_preference`, the `info_btn` tip the brief specifies, the
  `/api/preference_toggle` POST handler, and the `scrollnav.js` + `infotip.js`
  script tags (no `lightbox.js`, since this page has no thumbnails).

### 5. Run the new tests, then the full suite, then commit

`PYTHONPATH=src uv run pytest tests/test_preference_status.py -v`

Full output:

```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0 -- /workspace/trent-with-smart-prompts/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/trent-with-smart-prompts
configfile: pyproject.toml
collecting ... collected 7 items

tests/test_preference_status.py::test_compute_data_with_no_ratings_file_reports_zero_counts PASSED [ 14%]
tests/test_preference_status.py::test_compute_data_below_min_labels_reports_count_gate PASSED [ 28%]
tests/test_preference_status.py::test_compute_data_at_min_labels_but_imbalanced_reports_balance_gate PASSED [ 42%]
tests/test_preference_status.py::test_compute_data_well_balanced_above_min_labels_has_no_gate_message PASSED [ 57%]
tests/test_preference_status.py::test_compute_data_reads_model_meta_and_toggle_when_model_exists PASSED [ 71%]
tests/test_preference_status.py::test_render_html_disables_toggle_when_no_model PASSED [ 85%]
tests/test_preference_status.py::test_render_html_enables_toggle_when_model_exists PASSED [100%]

============================== 7 passed in 1.97s ===============================
```

Full suite:

`PYTHONPATH=src uv run pytest tests/`

Tail of output:

```
====================== 125 passed, 18 warnings in 21.94s =======================
```

No new warnings introduced. The 17 `OptimizeWarning: Unknown solver options: iprint`
warnings are pre-existing from `test_preference_model.py` (sklearn
`LogisticRegression` doesn't recognize `iprint`, not from this task).

Em-dash and ` -- ` audit on the new files (ripgrep; both returned exit 1, i.e. no
matches):

```
rg -n "—" src/clawmarks/build/preference_status.py tests/test_preference_status.py
rg -n " -- " src/clawmarks/build/preference_status.py tests/test_preference_status.py
```

Em-dash and ` -- ` audit on the commit message:

```
git log -1 --format='%B' HEAD | rg -n "—| -- "
exit: 1
```

Stage and commit (only the two new files; `notes/uncanny_seedrun1/` was an
unrelated, pre-existing untracked directory left alone per the project-wide
"never delete or modify unfamiliar notes" rule and the task scope):

```
git add src/clawmarks/build/preference_status.py tests/test_preference_status.py
git commit -m "feat(clawmarks): add preference classifier status view module"
```

Result:

```
[feat/preference-toggle d01da48] feat(clawmarks): add preference classifier status view module
 2 files changed, 211 insertions(+)
 create mode 100644 src/clawmarks/build/preference_status.py
 create mode 100644 tests/test_preference_status.py
```

Final verification (post-commit):

```
PYTHONPATH=src uv run pytest tests/test_preference_status.py -v
============================== 7 passed in 1.99s ==============================

PYTHONPATH=src uv run pytest tests/
====================== 125 passed, 18 warnings in 21.79s ======================
```

## Self-review notes

- The brief asked me to copy the implementation code block verbatim, which I did
  except for one whitespace nit the original block carried into a literal line
  of Python source: line 28 of the brief block (the `gate_message = ...`
  continuation) has its second-line continuation indent off by one space
  relative to the first line, which would have produced a Python `IndentationError`
  if pasted exactly. I aligned both lines to the same column, matching the rest
  of the brief's code. The resulting code is what the brief intended and matches
  the file as it would have looked if the brief had been generated without that
  one-character bug. The behavior is identical and the tests confirm it.
- The `numpy` import is inside the `else` branch on purpose (per the brief's
  Step 3 code). For a real run with the model trained and 50+ balanced labels,
  numpy is already loaded as a transitive import via `preference_model`, but
  the lazy import keeps `compute_data` cheap for the no-ratings and
  below-`MIN_LABELS` paths that don't actually need it.
- `compute_data` always returns every key the contract lists, even when the
  ratings file is missing. The first test (`test_compute_data_with_no_ratings_file_reports_zero_counts`)
  pins this: `n_yes/n_no/n_total` are 0, `has_model` is False, `model_meta` is
  None, `use_predicted_preference` is the saved-or-default toggle, and the
  count-gate message includes the `MIN_LABELS` constant (50).
- The `render_html` tests are intentionally narrow: they only assert
  presence/absence of `disabled`, `checked`, `/api/preference_toggle`, and
  `0.8` (the example `cv_accuracy`). They don't pin the full HTML, which is
  right: the brief's design may iterate on the surrounding chrome without
  re-deriving these tests.
- I confirmed `nav_bar_html('preference_status.html')` is the right call by
  re-reading the existing convention in `preference_rank.py`
  (`nav_bar_html('preference_rank.html')`) and `test_shared_ui.py`'s
  `test_nav_options_includes_preference_status_page` plus
  `test_nav_bar_html_marks_preference_status_selected_when_current`, both
  from the prior task (`c48a29f`). The new module's `nav_bar_html(...)` call
  matches the established pattern.
- I did not touch `clawmarks.config.SWEEP_DIR` or
  `PREFERENCE_SETTINGS_FILE` directly from the new module; `compute_data`
  reads `preference_model.MODEL_FILE` / `MODEL_META_FILE` (already module-level
  constants) and `preference_settings.PREFERENCE_SETTINGS_FILE` (also a
  module-level constant resolved by `preference_settings` itself), and the
  test suite monkeypatches those attributes per-test, which mirrors the
  approach used by `test_preference_settings.py` and `test_preference_model.py`.

## Concerns

- None blocking. Task scope was fully met: the brief said this task only needs
  the module and its tests in isolation; wiring it into `curation_server.py`
  as a live route is explicitly Task 5, not mine.
- One small judgment call flagged above: the brief's code block had a
  single-space under-indent on one line of a multi-line f-string that would
  have caused a `SyntaxError` if pasted literally. I aligned it to the
  surrounding column. The behavior, test results, and brief intent are
  identical; the only diff is one space on one line.
- I left `notes/uncanny_seedrun1/` untracked and uncommitted, matching its
  pre-existing state and the project-wide rule about not touching unfamiliar
  notes directories (per `CLAUDE.md`'s data-integrity section).
