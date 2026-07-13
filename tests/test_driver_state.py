import json

from clawmarks.search import driver


def test_state_file_round_one_has_no_round_suffix(tmp_path, monkeypatch):
    """Regression test for issue #15: round 1's original script wrote allnight_state.json (no
    round-number suffix). The merged driver must keep reading/writing that same filename, or
    resuming round 1 silently starts over at generation 0 instead of finding its existing state."""
    monkeypatch.setattr(driver, "SWEEP_DIR", tmp_path)
    path = driver._state_file(driver.ROUND_CONFIGS[1])
    assert path == tmp_path / "allnight_state.json"


def test_state_file_round_two_keeps_its_round_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "SWEEP2_DIR", tmp_path)
    path = driver._state_file(driver.ROUND_CONFIGS[2])
    assert path == tmp_path / "allnight2_state.json"


def test_load_state_resumes_from_the_correctly_named_round_one_file(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "SWEEP_DIR", tmp_path)
    (tmp_path / "allnight_state.json").write_text(json.dumps({
        "generation": 7, "stage": 1, "plateau_count": 2, "novelty_history": [0.1],
        "gpt55_subjects": [], "start_balance": 5.0, "start_time": 100.0,
    }))
    state = driver.load_state(driver.ROUND_CONFIGS[1])
    assert state["generation"] == 7


def test_load_resumable_manifest_returns_empty_when_no_manifest_exists(tmp_path):
    assert driver._load_resumable_manifest(tmp_path) == []


def test_load_resumable_manifest_resumes_prior_persisted_images(tmp_path):
    """Regression test for issue #15: the main loop used to always start from manifest = [] and
    then overwrite scored_manifest.json with only the new run's images, so a restart permanently
    discarded every previously persisted record. Loading the existing file first prevents that."""
    prior = [{"tag": "a", "centroid_sim": 0.5, "novelty": 0.3}]
    (tmp_path / "scored_manifest.json").write_text(json.dumps(prior))
    assert driver._load_resumable_manifest(tmp_path) == prior
