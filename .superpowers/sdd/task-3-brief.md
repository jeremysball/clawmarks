### Task 3: `shared_ui.py` nav entry for the new page

**Files:**
- Modify: `src/clawmarks/shared_ui.py`
- Test: `tests/test_shared_ui.py` (create if it doesn't exist; check first with
  `fd -a test_shared_ui tests` since it may already exist for other nav assertions)

**Interfaces:**
- Consumes: nothing.
- Produces: `"preference_status.html"` present in `shared_ui.NAV_OPTIONS`, so every existing
  page's nav dropdown (rendered via `nav_bar_html`) picks it up automatically. Task 4's
  `render_html` calls `nav_bar_html('preference_status.html')`.

- [ ] **Step 1: Check whether a nav test already exists**

Run: `fd -a test_shared_ui tests`

If it exists, read it and add a test in the same style as Step 2 below instead of creating a
new file. If it doesn't exist, create `tests/test_shared_ui.py` with the content in Step 2.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_shared_ui.py (or appended to the existing file)
from clawmarks.shared_ui import NAV_OPTIONS, nav_bar_html


def test_nav_options_includes_preference_status_page():
    hrefs = [href for href, _label in NAV_OPTIONS]
    assert "preference_status.html" in hrefs


def test_nav_bar_html_marks_preference_status_selected_when_current():
    html = nav_bar_html("preference_status.html")
    assert 'value="preference_status.html" selected' in html
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /workspace/trent-with-smart-prompts && PYTHONPATH=src uv run pytest tests/test_shared_ui.py -v`
Expected: FAIL (`assert "preference_status.html" in hrefs`)

- [ ] **Step 4: Add the nav entry**

In `src/clawmarks/shared_ui.py`, add a new tuple to `NAV_OPTIONS`, right after the existing
`("preference_rank.html", "predicted preference")` entry:

```python
    ("preference_status.html", "preference status"),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /workspace/trent-with-smart-prompts && PYTHONPATH=src uv run pytest tests/test_shared_ui.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/clawmarks/shared_ui.py tests/test_shared_ui.py
git commit -m "feat(clawmarks): add preference status page to the shared nav bar"
```

---

