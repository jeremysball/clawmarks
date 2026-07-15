import json

from clawmarks.build import preference_rank


def test_compute_data_returns_no_model_state_when_model_missing(tmp_path):
    manifest = [{"file": "/x/a.png", "tag": "a", "prompt_name": "p", "centroid_sim": 0.5, "novelty": 0.5}]
    (tmp_path / "scored_manifest.json").write_text(json.dumps(manifest))

    data = preference_rank.compute_data(str(tmp_path))
    assert data["has_model"] is False

    html = preference_rank.render_html(data)
    assert "no trained model" in html.lower() or "not enough" in html.lower()


def test_render_html_never_emits_a_literal_closing_script_tag():
    """A literal "</script>" substring anywhere before the real closing tag truncates the
    browser's HTML parse of the whole <script> block early -- everything after it is dropped
    silently, with no console error. This bit six pages via a copy-pasted comment; guard
    against it coming back."""
    data = {"has_model": True, "items": [
        {"tag": "a", "prompt_name": "p", "prompt_type": "style", "faith": 0.5, "novelty": 0.5,
         "strength": 1.0, "cfg": 7.0, "thumb": "a.png", "file": "a.png", "predicted_preference": 0.9},
    ]}
    html = preference_rank.render_html(data)
    script_start = html.index("<script>")
    script_end = html.index("</script>", script_start + len("<script>"))
    body = html[script_start + len("<script>"):script_end]
    assert "</script" not in body
