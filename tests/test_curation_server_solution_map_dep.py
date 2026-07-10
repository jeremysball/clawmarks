from clawmarks import curation_server as cs


def test_get_solution_map_data_uses_live_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "SWEEP_DIR", tmp_path)
    monkeypatch.setattr(cs, "_live_cache", cs.LiveCache())
    (tmp_path / "scored_manifest.json").write_text("[]")

    sentinel = {"solution_map_data": {"points": [], "real_points": []}, "similarity_scored": {}}
    monkeypatch.setattr(cs.solution_map, "compute_data", lambda sweep_dir: sentinel)

    assert cs._get_solution_map_data() is sentinel
