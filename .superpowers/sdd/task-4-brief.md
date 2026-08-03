### Task 4: `build/preference_status.py` (compute_data + render_html)

**Files:**
- Create: `src/clawmarks/build/preference_status.py`
- Test: `tests/test_preference_status.py`

**Interfaces:**
- Consumes: `clawmarks.config.SWEEP_DIR`/`PREFERENCE_SETTINGS_FILE`,
  `clawmarks.search.preference_settings.load`, `clawmarks.search.preference_model` (`MODEL_FILE`,
  `MODEL_META_FILE`, `MIN_LABELS`, `class_balance_error`), `clawmarks.shared_ui`
  (`nav_bar_html`, `TOPNAV_CSS`, `MOBILE_BASE_CSS`, `INFOTIP_CSS`, `info_btn`).
- Produces: `compute_data(sweep_dir) -> dict`, `render_html(data) -> str`. Task 5's
  `curation_server.py` route calls both.

**`compute_data` return shape** (all keys always present):

```python
{
    "n_yes": int, "n_no": int, "n_total": int,      # from user_ratings.json
    "min_labels": int,                               # preference_model.MIN_LABELS, for display
    "labels_gate_message": str,                       # "" if training could proceed right now
    "has_model": bool,                                 # MODEL_FILE exists
    "model_meta": dict | None,                        # MODEL_META_FILE contents, or None
    "use_predicted_preference": bool,                  # current persisted toggle value
}
```

`labels_gate_message` covers two failure modes with distinct text: below `MIN_LABELS` entirely
("only N labels (need 50); rate more images via rate.html.") and `class_balance_error`'s message
when at or above `MIN_LABELS` but imbalanced. Below `MIN_LABELS`, skip the balance check
entirely (matching `preference_model.main`'s own order: it checks `len(y) < MIN_LABELS` before
`class_balance_error`), since balance is irrelevant until the count gate is cleared.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_preference_status.py
import json

from clawmarks.build import preference_status


def _write_ratings(tmp_path, n_yes, n_no):
    ratings = {}
    for i in range(n_yes):
        ratings[f"y{i}"] = {"label": "yes", "rated_at": "t"}
    for i in range(n_no):
        ratings[f"n{i}"] = {"label": "no", "rated_at": "t"}
    (tmp_path / "user_ratings.json").write_text(json.dumps(ratings))


def test_compute_data_with_no_ratings_file_reports_zero_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(preference_status.preference_model, "MODEL_FILE", tmp_path / "preference_model.joblib")
    data = preference_status.compute_data(tmp_path)
    assert data["n_yes"] == 0 and data["n_no"] == 0 and data["n_total"] == 0
    assert data["has_model"] is False
    assert data["model_meta"] is None
    assert data["use_predicted_preference"] is False
    assert "50" in data["labels_gate_message"]


def test_compute_data_below_min_labels_reports_count_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(preference_status.preference_model, "MODEL_FILE", tmp_path / "preference_model.joblib")
    _write_ratings(tmp_path, n_yes=10, n_no=5)
    data = preference_status.compute_data(tmp_path)
    assert data["n_yes"] == 10 and data["n_no"] == 5 and data["n_total"] == 15
    assert "15" in data["labels_gate_message"] and "50" in data["labels_gate_message"]


def test_compute_data_at_min_labels_but_imbalanced_reports_balance_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(preference_status.preference_model, "MODEL_FILE", tmp_path / "preference_model.joblib")
    _write_ratings(tmp_path, n_yes=58, n_no=2)
    data = preference_status.compute_data(tmp_path)
    assert "5-fold" in data["labels_gate_message"]


def test_compute_data_well_balanced_above_min_labels_has_no_gate_message(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(preference_status.preference_model, "MODEL_FILE", tmp_path / "preference_model.joblib")
    _write_ratings(tmp_path, n_yes=30, n_no=30)
    data = preference_status.compute_data(tmp_path)
    assert data["labels_gate_message"] == ""


def test_compute_data_reads_model_meta_and_toggle_when_model_exists(tmp_path, monkeypatch):
    settings_path = tmp_path / "preference_settings.json"
    model_path = tmp_path / "preference_model.joblib"
    meta_path = tmp_path / "preference_model_meta.json"
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", settings_path)
    monkeypatch.setattr(preference_status.preference_model, "MODEL_FILE", model_path)
    monkeypatch.setattr(preference_status.preference_model, "MODEL_META_FILE", meta_path)
    model_path.write_text("fake model bytes")
    meta = {"trained_at": "2026-07-10T00:00:00+00:00", "n_labels": 60, "n_yes": 30, "n_no": 30, "cv_accuracy": 0.8}
    meta_path.write_text(json.dumps(meta))
    preference_status.preference_settings.save(True)

    data = preference_status.compute_data(tmp_path)
    assert data["has_model"] is True
    assert data["model_meta"] == meta
    assert data["use_predicted_preference"] is True


def test_render_html_disables_toggle_when_no_model():
    data = {"n_yes": 0, "n_no": 0, "n_total": 0, "min_labels": 50, "labels_gate_message": "not enough labels",
            "has_model": False, "model_meta": None, "use_predicted_preference": False}
    html = preference_status.render_html(data)
    assert "disabled" in html
    assert "/api/preference_toggle" in html


def test_render_html_enables_toggle_when_model_exists():
    meta = {"trained_at": "2026-07-10T00:00:00+00:00", "n_labels": 60, "n_yes": 30, "n_no": 30, "cv_accuracy": 0.8}
    data = {"n_yes": 30, "n_no": 30, "n_total": 60, "min_labels": 50, "labels_gate_message": "",
            "has_model": True, "model_meta": meta, "use_predicted_preference": True}
    html = preference_status.render_html(data)
    assert "disabled" not in html
    assert "checked" in html
    assert "0.8" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /workspace/trent-with-smart-prompts && PYTHONPATH=src uv run pytest tests/test_preference_status.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'clawmarks.build.preference_status'`)

- [ ] **Step 3: Implement**

```python
# src/clawmarks/build/preference_status.py
"""
Shows whether the preference classifier (search/preference_model.py) is trained and ready, and
exposes the single persisted toggle (search/preference_settings.py) that both archive.html and
`clawmarks run allnight` read to decide whether to use its predictions. See
docs/superpowers/specs/2026-07-10-preference-toggle-design.md.

Served live at /preference_status.html by curation_server.py.
"""
import json
import os

from clawmarks.search import preference_model, preference_settings
from clawmarks.shared_ui import INFOTIP_CSS, MOBILE_BASE_CSS, TOPNAV_CSS, info_btn, nav_bar_html


def compute_data(sweep_dir):
    ratings_path = f"{sweep_dir}/user_ratings.json"
    if os.path.exists(ratings_path):
        with open(ratings_path) as f:
            ratings = json.load(f)
    else:
        ratings = {}
    n_yes = sum(1 for r in ratings.values() if r.get("label") == "yes")
    n_no = sum(1 for r in ratings.values() if r.get("label") == "no")
    n_total = n_yes + n_no

    if n_total < preference_model.MIN_LABELS:
        gate_message = (f"only {n_total} labels (need {preference_model.MIN_LABELS}); "
                         f"rate more images via rate.html.")
    else:
        import numpy as np
        y = np.array([1] * n_yes + [0] * n_no, dtype=np.int64)
        gate_message = preference_model.class_balance_error(y)

    has_model = os.path.exists(preference_model.MODEL_FILE)
    model_meta = None
    if has_model and os.path.exists(preference_model.MODEL_META_FILE):
        with open(preference_model.MODEL_META_FILE) as f:
            model_meta = json.load(f)

    return {
        "n_yes": n_yes, "n_no": n_no, "n_total": n_total,
        "min_labels": preference_model.MIN_LABELS,
        "labels_gate_message": gate_message,
        "has_model": has_model,
        "model_meta": model_meta,
        "use_predicted_preference": preference_settings.load()["use_predicted_preference"],
    }


def render_html(data):
    gate_html = (f'<p class="gate">{data["labels_gate_message"]}</p>'
                 if data["labels_gate_message"] else '<p class="gate ok">ready to train.</p>')

    if data["model_meta"]:
        m = data["model_meta"]
        meta_html = (f'<table class="meta"><tr><td>trained</td><td>{m["trained_at"]}</td></tr>'
                     f'<tr><td>labels used</td><td>{m["n_labels"]} ({m["n_yes"]} yes / {m["n_no"]} no)</td></tr>'
                     f'<tr><td>cross-validated accuracy</td><td>{m["cv_accuracy"]}</td></tr></table>')
    else:
        meta_html = (f'<p class="meta-empty">no model trained yet. Once enough labels exist, run '
                     f'<code>python -m clawmarks.search.preference_model</code>.</p>')

    disabled_attr = "" if data["has_model"] else "disabled"
    checked_attr = "checked" if data["use_predicted_preference"] else ""

    toggle_tip = info_btn(
        "When on, archive.html's fallback champion per MAP-Elites cell and the next "
        "`clawmarks run allnight`'s exploit pool both use this trained model's predicted "
        "preference instead of raw novelty / yes-rated images. Off by default; only turn this "
        "on after eyeballing preference_rank.html against your own taste."
    )

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>CLAWMARKS preference status</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ color-scheme: dark; --bg:#0b0b0d; --panel:#16161a; --border:#2a2a30; --text:#eaeaee; --text-dim:#9a9aa4; }}
body {{ background:var(--bg); color:var(--text); font-family:-apple-system,sans-serif; margin:0; padding:24px; }}
{TOPNAV_CSS}
{MOBILE_BASE_CSS}
h1 {{ font-size:18px; margin:0 0 4px; }}
p.sub {{ color:var(--text-dim); max-width:760px; font-size:13px; line-height:1.6; }}
.panel {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:16px; margin-top:16px; max-width:520px; }}
p.gate {{ color:#e0a030; }}
p.gate.ok {{ color:#5fbf6f; }}
table.meta {{ font-size:13px; border-collapse:collapse; }}
table.meta td {{ padding:3px 10px 3px 0; color:var(--text-dim); }}
table.meta td:first-child {{ color:var(--text); }}
.toggle-row {{ margin-top:14px; display:flex; align-items:center; gap:8px; }}
#toggle-status {{ font-size:12px; color:var(--text-dim); margin-left:8px; }}
{INFOTIP_CSS}
</style></head><body>

{nav_bar_html('preference_status.html')}
<h1>Preference classifier status</h1>
<p class="sub">Labels: {data["n_yes"]} yes / {data["n_no"]} no ({data["n_total"]} total, needs {data["min_labels"]}).</p>
<div class="panel">
{gate_html}
{meta_html}
<div class="toggle-row">
<label><input type="checkbox" id="toggle" {checked_attr} {disabled_attr} onchange="toggle(this.checked)"> use predicted preference{toggle_tip}</label>
<span id="toggle-status"></span>
</div>
</div>
<script>
function toggle(enabled) {{
  const status = document.getElementById('toggle-status');
  status.textContent = 'saving...';
  fetch('/api/preference_toggle', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{enabled: enabled}}),
  }}).then(r => r.json()).then(data => {{
    if (data.error) {{
      status.textContent = data.error;
      document.getElementById('toggle').checked = !enabled;
    }} else {{
      status.textContent = 'saved.';
    }}
  }});
}}
</script>
<script src="scrollnav.js"></script>
<script src="infotip.js"></script>
</body></html>"""
    return html
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /workspace/trent-with-smart-prompts && PYTHONPATH=src uv run pytest tests/test_preference_status.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/clawmarks/build/preference_status.py tests/test_preference_status.py
git commit -m "feat(clawmarks): add preference classifier status view module"
```

---

