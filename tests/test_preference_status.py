# tests/test_preference_status.py
import json

from clawmarks.build import preference_status


def _write_comparisons(tmp_path, n):
    comparisons = [{"winner": f"w{i}", "loser": f"l{i}", "compared_at": "t"} for i in range(n)]
    (tmp_path / "user_comparisons.json").write_text(json.dumps(comparisons))


def test_compute_data_with_no_comparisons_file_reports_zero_count(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(preference_status.preference_pairwise_model, "MODEL_FILE", tmp_path / "preference_pairwise_model.joblib")
    data = preference_status.compute_data(tmp_path)
    assert data["n_comparisons"] == 0
    assert data["has_model"] is False
    assert data["model_meta"] is None
    assert data["use_predicted_preference"] is False
    assert "50" in data["comparisons_gate_message"]


def test_compute_data_below_min_comparisons_reports_count_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(preference_status.preference_pairwise_model, "MODEL_FILE", tmp_path / "preference_pairwise_model.joblib")
    _write_comparisons(tmp_path, 15)
    data = preference_status.compute_data(tmp_path)
    assert data["n_comparisons"] == 15
    assert "15" in data["comparisons_gate_message"] and "50" in data["comparisons_gate_message"]


def test_compute_data_at_min_comparisons_has_no_gate_message(tmp_path, monkeypatch):
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", tmp_path / "preference_settings.json")
    monkeypatch.setattr(preference_status.preference_pairwise_model, "MODEL_FILE", tmp_path / "preference_pairwise_model.joblib")
    _write_comparisons(tmp_path, 50)
    data = preference_status.compute_data(tmp_path)
    assert data["comparisons_gate_message"] == ""


def test_compute_data_reads_model_meta_and_toggle_when_model_exists(tmp_path, monkeypatch):
    settings_path = tmp_path / "preference_settings.json"
    model_path = tmp_path / "preference_pairwise_model.joblib"
    meta_path = tmp_path / "preference_pairwise_model_meta.json"
    monkeypatch.setattr(preference_status.preference_settings, "PREFERENCE_SETTINGS_FILE", settings_path)
    monkeypatch.setattr(preference_status.preference_pairwise_model, "MODEL_FILE", model_path)
    monkeypatch.setattr(preference_status.preference_pairwise_model, "MODEL_META_FILE", meta_path)
    model_path.write_text("fake model bytes")
    meta = {"trained_at": "2026-07-11T00:00:00+00:00", "n_comparisons": 60, "cv_accuracy": 0.8}
    meta_path.write_text(json.dumps(meta))
    preference_status.preference_settings.save(True)

    data = preference_status.compute_data(tmp_path)
    assert data["has_model"] is True
    assert data["model_meta"] == meta
    assert data["use_predicted_preference"] is True


def test_render_html_disables_toggle_when_no_model():
    data = {"n_comparisons": 0, "min_comparisons": 50, "comparisons_gate_message": "not enough comparisons",
            "has_model": False, "model_meta": None, "use_predicted_preference": False}
    html = preference_status.render_html(data)
    assert "disabled" in html
    assert "/api/preference_toggle" in html


def test_render_html_enables_toggle_when_model_exists():
    meta = {"trained_at": "2026-07-11T00:00:00+00:00", "n_comparisons": 60, "cv_accuracy": 0.8}
    data = {"n_comparisons": 60, "min_comparisons": 50, "comparisons_gate_message": "",
            "has_model": True, "model_meta": meta, "use_predicted_preference": True}
    html = preference_status.render_html(data)
    assert "disabled" not in html
    assert "checked" in html
    assert "0.8" in html
