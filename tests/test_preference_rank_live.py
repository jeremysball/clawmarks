import json

from clawmarks.build import preference_rank


def test_compute_data_returns_no_model_state_when_model_missing(tmp_path):
    manifest = [{"file": "/x/a.png", "tag": "a", "prompt_name": "p", "centroid_sim": 0.5, "novelty": 0.5}]
    (tmp_path / "scored_manifest.json").write_text(json.dumps(manifest))

    data = preference_rank.compute_data(str(tmp_path))
    assert data["has_model"] is False

    html = preference_rank.render_html(data)
    assert "no trained model" in html.lower() or "not enough" in html.lower()
    assert "topnav" in html


def test_rank_page_has_bounded_review_mode_and_rank_ordinals():
    data = {"has_model": True, "items": [
        {"tag": "a", "thumb": "a.jpg", "faith": 0.5, "novelty": 0.4,
         "predicted_preference": 0.8},
    ]}

    html = preference_rank.render_html(data)

    assert "Review top, middle, and bottom" in html
    assert "Rank #" in html
    assert "/api/preference_rank/flag" in html


def test_rank_page_renders_persisted_flag_objects_as_selected_buttons():
    data = {"has_model": True, "items": [
        {"tag": "model-controlled<tag>", "thumb": "a.jpg", "faith": 0.5, "novelty": 0.4,
         "predicted_preference": 0.8},
    ]}

    html = preference_rank.render_html(data)

    assert "flags[tag]?.flag === flag" in html
    assert "aria-pressed=\"${flags[it.tag]?.flag === 'matches'}\"" in html
    assert "class=\"flag-button ${flagSelected(it.tag, 'matches')}\"" in html
    assert "flags[tag] = flag" not in html


def test_rank_page_reports_flag_save_failures_without_mutating_state():
    data = {"has_model": True, "items": [
        {"tag": "a", "thumb": "a.jpg", "faith": 0.5, "novelty": 0.4,
         "predicted_preference": 0.8},
    ]}

    html = preference_rank.render_html(data)

    assert "if (!r.ok) throw new Error('flag save failed')" in html
    assert "flags[tag] = {flag: flag, flagged_at: flags[tag]?.flagged_at ?? null}" in html
    assert "Could not save this flag." in html
    assert "id=\"flagError\"" in html
