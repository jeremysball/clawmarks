import pytest

from clawmarks import config
from clawmarks.focus_store import FocusStore, Scope
from clawmarks.workspace_context import (
    ContextQueryError,
    resolve_workspace_context,
)


@pytest.fixture
def state_dir(tmp_path):
    return tmp_path / "state"


@pytest.fixture
def real_dir(tmp_path):
    path = tmp_path / "real"
    path.mkdir()
    (path / "real.jpg").write_bytes(b"real")
    return path


@pytest.fixture
def scope():
    return Scope("demo", "round1")


@pytest.fixture
def leg_dir(tmp_path, monkeypatch, scope):
    expeditions_dir = tmp_path / "state" / "expeditions"
    monkeypatch.setattr(config, "EXPEDITIONS_DIR", expeditions_dir)
    path = config.leg_dir(scope.expedition, scope.leg)
    path.mkdir(parents=True)
    return path


@pytest.fixture
def store(state_dir, real_dir):
    return FocusStore(state_dir, real_dir)


@pytest.fixture
def manifest(leg_dir):
    records = []
    for tag in ("a", "b"):
        image = leg_dir / f"{tag}.png"
        image.write_bytes(tag.encode())
        records.append({"tag": tag, "file": str(image)})
    return records


@pytest.fixture
def saved_focus(store, scope, manifest):
    payload = {
        "label": "Ink anchor",
        "source": {
            "view": "map",
            "kind": "map_members",
            "member_tags": ["a"],
            "real_anchor_tags": ["real.jpg"],
            "projection_hint": {
                "projection_version": "sha256:abc",
                "polygon": [[0.1, 0.2]],
            },
        },
        "question": "Keep these spaces",
        "observation": "Six clusters.",
        "hypothesis_text": "Marks survive.",
        "test_contract": None,
    }
    return store.create(scope, payload, manifest)


def test_bare_url_uses_browsing_scope_without_focus(store):
    context = resolve_workspace_context(
        "/map.html", {"expedition": "demo", "leg": "round1"}, store
    )
    assert context.expedition == "demo"
    assert context.leg == "round1"
    assert context.focus is None


def test_explicit_focus_scope_wins_without_mutating_active_selection(store, saved_focus):
    active = {"expedition": "other", "leg": "current"}
    context = resolve_workspace_context(
        f"/map.html?expedition=demo&leg=round1&focus_id={saved_focus['focus_id']}",
        active,
        store,
    )
    assert context.focus == saved_focus
    assert active == {"expedition": "other", "leg": "current"}


def test_partial_focus_query_is_rejected(store):
    with pytest.raises(ContextQueryError, match="all three"):
        resolve_workspace_context(
            "/map.html?focus_id=focus_11111111111111111111111111111111", {}, store
        )
