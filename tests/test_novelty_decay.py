import json

from clawmarks.build import novelty_decay


def test_compute_data_builds_series_across_generations(tmp_path):
    manifest = [
        {"tag": "gen0_a", "prompt_name": "p", "novelty": 0.5},
        {"tag": "gen1_a", "prompt_name": "p", "novelty": 0.4},
    ]
    (tmp_path / "scored_manifest.json").write_text(json.dumps(manifest))
    data = novelty_decay.compute_data(str(tmp_path))
    assert len(data["series"]) == 1
    assert data["series"][0]["prompt_name"] == "p"

    html = novelty_decay.render_html(data)
    assert "<!doctype" in html.lower()


def test_render_html_placeholder_when_no_multi_generation_prompt(tmp_path):
    manifest = [{"tag": "gen0_a", "prompt_name": "p", "novelty": 0.5}]
    (tmp_path / "scored_manifest.json").write_text(json.dumps(manifest))
    data = novelty_decay.compute_data(str(tmp_path))
    assert data["series"] == []

    html = novelty_decay.render_html(data)
    assert "placeholder" in html.lower()
