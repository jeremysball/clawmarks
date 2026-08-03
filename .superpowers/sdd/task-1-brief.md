### Task 1: `search/preference_settings.py` + `config.py` setting path

**Files:**
- Create: `src/clawmarks/search/preference_settings.py`
- Modify: `src/clawmarks/config.py`
- Test: `tests/test_preference_settings.py`

**Interfaces:**
- Consumes: `clawmarks.config.PREFERENCE_SETTINGS_FILE` (new).
- Produces: `load() -> {"use_predicted_preference": bool}`, `save(enabled: bool) -> None`. Later
  tasks (4, 5, 6) call both.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_preference_settings.py
import json

from clawmarks.search import preference_settings


def test_load_returns_false_default_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    assert preference_settings.load() == {"use_predicted_preference": False}


def test_save_then_load_round_trips_true(tmp_path, monkeypatch):
    path = tmp_path / "preference_settings.json"
    monkeypatch.setattr(preference_settings, "PREFERENCE_SETTINGS_FILE", path)
    preference_settings.save(True)
    assert preference_settings.load() == {"use_predicted_preference": True}


def test_save_writes_atomically_no_tmp_file_left_behind(tmp_path, monkeypatch):
    path = tmp_path / "preference_settings.json"
    monkeypatch.setattr(preference_settings, "PREFERENCE_SETTINGS_FILE", path)
    preference_settings.save(True)
    assert not (tmp_path / "preference_settings.json.tmp").exists()
    assert json.loads(path.read_text()) == {"use_predicted_preference": True}


def test_save_false_then_load_round_trips_false(tmp_path, monkeypatch):
    path = tmp_path / "preference_settings.json"
    monkeypatch.setattr(preference_settings, "PREFERENCE_SETTINGS_FILE", path)
    preference_settings.save(True)
    preference_settings.save(False)
    assert preference_settings.load() == {"use_predicted_preference": False}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /workspace/trent-with-smart-prompts && PYTHONPATH=src uv run pytest tests/test_preference_settings.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'clawmarks.search.preference_settings'`)

- [ ] **Step 3: Add the config path**

In `src/clawmarks/config.py`, immediately after the existing `USER_RATINGS_FILE = SWEEP_DIR / "user_ratings.json"` line, add:

```python
PREFERENCE_SETTINGS_FILE = SWEEP_DIR / "preference_settings.json"
```

- [ ] **Step 4: Write the module**

```python
# src/clawmarks/search/preference_settings.py
"""
Single persisted setting shared by archive.html's rendering and `clawmarks run allnight`'s
exploit-pool source, so flipping predicted-preference on or off happens in one place instead
of two independent controls (a query param and a CLI flag). See
docs/superpowers/specs/2026-07-10-preference-toggle-design.md.
"""
import json
import os

from clawmarks.config import PREFERENCE_SETTINGS_FILE


def load():
    """Returns {"use_predicted_preference": bool}. Missing file means the default, False."""
    if not os.path.exists(PREFERENCE_SETTINGS_FILE):
        return {"use_predicted_preference": False}
    with open(PREFERENCE_SETTINGS_FILE) as f:
        return json.load(f)


def save(enabled):
    tmp = f"{PREFERENCE_SETTINGS_FILE}.tmp"
    with open(tmp, "w") as f:
        json.dump({"use_predicted_preference": bool(enabled)}, f)
    os.replace(tmp, PREFERENCE_SETTINGS_FILE)
```

Note: `load()`/`save()` read the module-level `PREFERENCE_SETTINGS_FILE` name at call time (not
a captured default argument), so the tests above can `monkeypatch.setattr(preference_settings,
"PREFERENCE_SETTINGS_FILE", ...)` and have both functions pick it up.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /workspace/trent-with-smart-prompts && PYTHONPATH=src uv run pytest tests/test_preference_settings.py -v`
Expected: PASS (4/4)

- [ ] **Step 6: Commit**

```bash
git add src/clawmarks/search/preference_settings.py src/clawmarks/config.py tests/test_preference_settings.py
git commit -m "feat(clawmarks): add persisted preference-toggle setting"
```

---

