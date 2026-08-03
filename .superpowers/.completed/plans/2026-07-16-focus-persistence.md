# Focus Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist expedition/leg-scoped Focus dossiers with durable writes, source-specific validation, revision conflicts, and explicit HTTP APIs.

**Architecture:** Add a small file-backed record layer above `atomic_io.py`, then implement Focus behavior in a dedicated `focus_store.py`. `curation_server.py` only parses HTTP and maps domain errors to status codes. Stable tags and metric ranges remain authoritative; projection coordinates remain display hints.

**Tech Stack:** Python 3.10+, POSIX `fcntl`, JSON, SHA-256, `http.server`, pytest.

## Global Constraints

- Store Foci only under `$CLAWMARKS_STATE_DIR/foci/<expedition>/<leg>/`.
- Never delete a good record before a replacement succeeds.
- Every replacement flushes and `fsync`s the file, calls `os.replace()`, then `fsync`s the parent directory.
- Create every missing record directory one level at a time and `fsync` each new directory and its parent before the first file write.
- Canonical JSON is UTF-8 from `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`.
- Record IDs use complete UUID hex strings and the `focus_` prefix.
- Every mutation uses `fcntl.flock` and revision checks. Python thread locks alone are insufficient.
- A corrupt record remains untouched and produces a readable integrity error.
- Tests use temporary directories only. Do not run mutation tests against production state.
- Run Python and tests through `uv run` only.

## File Structure

- Modify `src/clawmarks/atomic_io.py`: parent-directory durability.
- Create `src/clawmarks/durable_records.py`: canonical bytes, digests, IDs, timestamps, path validation, and reentrant cross-process locks.
- Create `src/clawmarks/focus_store.py`: Focus schema, validation, persistence, and domain errors.
- Modify `src/clawmarks/curation_server.py`: Focus routes and PATCH support.
- Modify `tests/test_atomic_io.py`: durability behavior.
- Create `tests/test_durable_records.py`: canonicalization and locking.
- Create `tests/test_focus_store.py`: domain behavior and corruption/concurrency cases.
- Create `tests/test_curation_server_focus_routes.py`: HTTP contract.

### Task 1: Make Directory Creation And Atomic Replacement Durable

**Files:**
- Modify: `src/clawmarks/atomic_io.py`
- Modify: `tests/test_atomic_io.py`

**Interfaces:**
- Preserves: `atomic_json_write(path, value) -> None` and `atomic_write(path, write_fn) -> None`.
- Produces: `fsync_directory(path: Path) -> None` and `durable_makedirs(path: Path) -> None`.

- [ ] **Step 1: Write the failing parent-fsync test**

```python
def test_atomic_json_write_fsyncs_parent_after_replace(tmp_path, monkeypatch):
    calls = []
    real_fsync = os.fsync

    def recording_fsync(fd):
        calls.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", recording_fsync)
    atomic_json_write(tmp_path / "record.json", {"ok": True})

    assert len(calls) == 2


def test_durable_makedirs_fsyncs_each_new_directory_and_parent(tmp_path, monkeypatch):
    synced = []
    monkeypatch.setattr(atomic_io, "fsync_directory", lambda path: synced.append(Path(path)))

    durable_makedirs(tmp_path / "records" / "demo")

    assert synced == [
        tmp_path / "records", tmp_path,
        tmp_path / "records" / "demo", tmp_path / "records",
    ]
```

Keep the existing tests proving serialization failure preserves the original and removes the temp file.

- [ ] **Step 2: Run the test and verify failure**

Run: `uv run pytest -q tests/test_atomic_io.py`

Expected: FAIL because only the temporary file is fsynced and no durable directory helper exists.

- [ ] **Step 3: Implement parent fsync**

```python
def fsync_directory(path):
    fd = os.open(Path(path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_makedirs(path):
    path = Path(path)
    missing = []
    cursor = path
    while not cursor.exists():
        missing.append(cursor)
        cursor = cursor.parent
    if not cursor.is_dir():
        raise NotADirectoryError(cursor)
    for directory in reversed(missing):
        try:
            directory.mkdir()
        except FileExistsError:
            if not directory.is_dir():
                raise
        fsync_directory(directory)
        fsync_directory(directory.parent)
```

Call `durable_makedirs(path.parent)` before creating the same-directory temporary file. Call
`fsync_directory(path.parent)` immediately after `os.replace()`. Do not replace a good file or skip
ancestor durability when several record-directory levels are new.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_atomic_io.py`

Expected: PASS.

```bash
git add src/clawmarks/atomic_io.py tests/test_atomic_io.py
git commit -m "fix(storage): fsync directories after atomic replace"
```

### Task 2: Add Canonical Digests And Reentrant File Locks

**Files:**
- Create: `src/clawmarks/durable_records.py`
- Create: `tests/test_durable_records.py`

**Interfaces:**
- Produces: `canonical_json_bytes(value: object) -> bytes`.
- Produces: `sha256_json(value: object) -> str` and `sha256_file(path: Path) -> str`.
- Produces: `utc_now() -> str` and `new_id(prefix: str) -> str`.
- Produces: `validate_component(value: str, kind: str) -> str`.
- Produces: `file_locks(paths: Iterable[Path]) -> ContextManager[None]`.
- Produces: `record_lock_path(state_dir: Path, identity: str) -> Path` and `leg_lock_path(state_dir: Path, expedition: str, leg: str) -> Path`.
- Produces: `record_locks(lock_root: Path, identities: Iterable[str]) -> ContextManager[None]`.
- Produces: `leg_write_lock(state_dir: Path, expedition: str, leg: str) -> ContextManager[None]`.
- Consumes: `durable_makedirs()` and `fsync_directory()` from Task 1 for first-time lock trees.

- [ ] **Step 1: Write failing canonicalization and lock tests**

```python
def test_canonical_json_digest_ignores_mapping_order():
    assert sha256_json({"b": 2, "a": 1}) == sha256_json({"a": 1, "b": 2})
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_record_locks_sort_paths_before_flock(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(durable_records.fcntl, "flock", lambda fd, mode: seen.append((fd, mode)))
    with record_locks(tmp_path, ["trial_b", "focus_a"]):
        assert (tmp_path / "focus_a.lock").exists()
        assert (tmp_path / "trial_b.lock").exists()
    assert len(seen) == 4


def test_file_locks_complete_when_processes_supply_opposite_orders(tmp_path):
    start = multiprocessing.Event()
    done_a = multiprocessing.Event()
    done_b = multiprocessing.Event()
    paths = [tmp_path / "focus.lock", tmp_path / "leg.lock"]
    a = multiprocessing.Process(target=lock_in_order, args=(paths, start, done_a))
    b = multiprocessing.Process(target=lock_in_order, args=(list(reversed(paths)), start, done_b))
    try:
        a.start()
        b.start()
        start.set()
        assert done_a.wait(2)
        assert done_b.wait(2)
        a.join(2)
        b.join(2)
        assert a.exitcode == b.exitcode == 0
    finally:
        for process in (a, b):
            if process.is_alive():
                process.terminate()
            process.join(2)


def lock_in_order(paths, start, done):
    if not start.wait(2):
        raise RuntimeError("start event timed out")
    with file_locks(paths):
        pass
    done.set()


def test_validate_component_rejects_path_escape():
    with pytest.raises(ValueError):
        validate_component("../other", "expedition")
```

Also keep a serialization test in which process B cannot enter the same lock until process A exits.
Use `multiprocessing.Event` and bound every wait so a regression cannot hang pytest.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_durable_records.py`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the record primitives**

Use one process-local `threading.RLock` per absolute lock path and a thread-local nesting count. Only the outer acquisition opens the lock file and calls `fcntl.flock(fd, LOCK_EX)`; only the outer release calls `LOCK_UN` and closes the descriptor. `file_locks()` resolves and sorts every absolute path before acquisition and releases in reverse order. The record and leg helpers only construct paths and delegate to this one ordering function, so a Focus-plus-leg snapshot cannot deadlock with another multi-lock transition.

Before opening a lock, call `durable_makedirs(lock_path.parent)`. Create a missing lock file with
`O_CREAT | O_EXCL`, `fsync` that descriptor, and `fsync_directory(lock_path.parent)` before taking
the flock. If another process won creation, reopen the existing regular file without truncation.
Reject symlinks and non-regular lock paths.

```python
def canonical_json_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


def leg_write_lock(state_dir, expedition, leg):
    return file_locks([leg_lock_path(state_dir, expedition, leg)])
```

Sanitize lock identities to `[A-Za-z0-9_.-]+` after validating scope components. Lock files persist after release; never unlink them as part of ordinary operation.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_durable_records.py`

Expected: PASS, including multiprocessing serialization.

```bash
git add src/clawmarks/durable_records.py tests/test_durable_records.py
git commit -m "feat(storage): add durable record primitives"
```

### Task 3: Implement Map-Member Focus Records

**Files:**
- Create: `src/clawmarks/focus_store.py`
- Create: `tests/test_focus_store.py`

**Interfaces:**
- Produces: `Scope(expedition: str, leg: str)` frozen dataclass.
- Produces: `FocusStore(state_dir: Path, real_dir: Path)`.
- Produces: `FocusStore.list(scope: Scope, status: str | None = None) -> list[dict]`.
- Produces: `FocusStore.get(scope: Scope, focus_id: str) -> dict`.
- Produces: `FocusStore.create(scope: Scope, payload: dict, manifest: list[dict], coverage_cells: list[dict] | None = None) -> dict`.
- Produces: `FocusStore.update(scope: Scope, focus_id: str, expected_revision: int, changes: dict) -> dict`.
- Produces: `FocusStore.archive(scope: Scope, focus_id: str, expected_revision: int) -> dict`.
- Produces errors: `FocusNotFound`, `FocusConflict(current)`, `FocusIntegrityError(path, detail)`, and `FocusValidationError`.

- [ ] **Step 1: Write failing map-Focus tests**

```python
def test_create_map_focus_preserves_text_and_deduplicates_tags(store, scope, manifest):
    focus = store.create(scope, {
        "label": "Ink anchor",
        "source": {
            "view": "map", "kind": "map_members",
            "member_tags": ["a", "a", "b"],
            "real_anchor_tags": ["real.jpg"],
            "projection_hint": {"projection_version": "sha256:abc", "polygon": [[0.1, 0.2]]},
        },
        "question": "  Keep these spaces  ",
        "observation": "Six clusters.",
        "hypothesis_text": "Marks survive.",
        "test_contract": None,
    }, manifest)
    assert focus["revision"] == 1
    assert focus["source"]["member_tags"] == ["a", "b"]
    assert focus["question"] == "  Keep these spaces  "


def test_create_rejects_cross_leg_or_duplicate_manifest_tag(store, scope):
    with pytest.raises(FocusValidationError, match="resolve exactly once"):
        store.create(scope, map_payload(["a"]), [{"tag": "a"}, {"tag": "a"}])


def test_stale_update_returns_current_record(store, scope, manifest):
    focus = store.create(scope, map_payload(["a"]), manifest)
    current = store.update(scope, focus["focus_id"], 1, {"label": "new"})
    with pytest.raises(FocusConflict) as exc:
        store.update(scope, focus["focus_id"], 1, {"label": "stale"})
    assert exc.value.current == current
```

Also test unknown real anchor, invalid ID, unsupported update key, archived update, status filtering, and malformed JSON preservation.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_focus_store.py`

Expected: FAIL because `focus_store.py` does not exist.

- [ ] **Step 3: Implement map validation and revision writes**

Permit update keys only from `label`, `question`, `observation`, `hypothesis_text`, and `test_contract`. Source membership is immutable after creation in version 1; a changed evidence selection creates another Focus. Preserve natural-language strings byte-for-byte after JSON decoding. Validate generated tags through a tag-to-records index and real anchors as direct files under `real_dir` after basename validation.

For each generated member, resolve its manifest `file` path and require it to remain under
`config.leg_dir(scope.expedition, scope.leg)` after `Path.resolve()`. A scoped manifest entry that
points outside its leg is an integrity error, not valid Focus evidence.

Each mutation acquires `record_locks(state_dir / "locks" / "records", [focus_id])`, reloads from disk inside the lock, checks the revision, sets whole-second UTC timestamps, and writes with `atomic_json_write()`.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_focus_store.py`

Expected: PASS.

```bash
git add src/clawmarks/focus_store.py tests/test_focus_store.py
git commit -m "feat(focus): persist map-member dossiers"
```

### Task 4: Add Coverage-Frontier Validation

**Files:**
- Modify: `src/clawmarks/focus_store.py`
- Modify: `tests/test_focus_store.py`

**Interfaces:**
- Extends: `FocusStore.create()` for `source.kind == "coverage_frontier"`.
- Consumes: caller-supplied current Coverage cells as `coverage_cells: list[dict]`.

- [ ] **Step 1: Write failing frontier tests**

```python
def test_create_frontier_focus_requires_empty_adjacent_cell(store, scope, manifest):
    focus = store.create(
        scope,
        frontier_payload(faith=[-0.2, 0.1], novelty=[0.8, 1.1], adjacent=["a"]),
        manifest,
        coverage_cells=[{
            "faith_lo": -0.2, "faith_hi": 0.1,
            "novelty_lo": 0.8, "novelty_hi": 1.1,
            "count": 0, "frontier": True,
        }],
    )
    assert focus["source"]["kind"] == "coverage_frontier"


@pytest.mark.parametrize("faith,novelty", [([0.2, 0.2], [0.1, 0.2]), ([-1.1, 0], [0.1, 0.2]), ([0, 1], [1.8, 2.1])])
def test_frontier_ranges_must_be_ordered_and_in_domain(store, scope, manifest, faith, novelty):
    with pytest.raises(FocusValidationError):
        store.create(scope, frontier_payload(faith, novelty, ["a"]), manifest, coverage_cells=[])
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_focus_store.py`

Expected: FAIL on coverage validation.

- [ ] **Step 3: Implement the discriminated branch**

Require finite two-value ranges with `min < max`, faithfulness within `[-1.0, 1.0]`, novelty within `[0.0, 2.0]`, at least one adjacent member resolving exactly once, and an exact current Coverage cell whose count is zero and `frontier` is true. Persist only the canonical range, adjacent tags, anchors, and optional hint.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_focus_store.py`

Expected: PASS.

```bash
git add src/clawmarks/focus_store.py tests/test_focus_store.py
git commit -m "feat(focus): validate Coverage frontier dossiers"
```

### Task 5: Expose Revision-Checked Focus APIs

**Files:**
- Modify: `src/clawmarks/curation_server.py:879-950,1317-1369,1617-1821`
- Create: `tests/test_curation_server_focus_routes.py`

**Interfaces:**
- Produces the five Focus endpoints from the design specification.
- Produces: `Handler.do_PATCH()` with the same JSON error boundary as POST.
- Returns: HTTP 400 validation, 404 unknown record, 409 revision conflict with `{"error": ..., "current": record}`, and 500 readable integrity errors without altering the corrupt file.

- [ ] **Step 1: Write failing route tests**

```python
def test_focus_create_get_update_archive_round_trip(running_server, focus_payload):
    status, created = post_json(running_server, "/api/foci", focus_payload)
    assert status == 201
    focus_id = created["focus_id"]

    status, fetched = get_json(
        running_server, f"/api/foci/{focus_id}?expedition=demo&leg=round1"
    )
    assert status == 200 and fetched == created

    status, updated = patch_json(
        running_server,
        f"/api/foci/{focus_id}?expedition=demo&leg=round1",
        {"expected_revision": 1, "changes": {"observation": "Changed"}},
    )
    assert status == 200 and updated["revision"] == 2


def test_focus_route_rejects_scope_mismatch_without_using_active_leg(running_server, focus_payload):
    _, created = post_json(running_server, "/api/foci", focus_payload)
    status, body = get_json(
        running_server,
        f"/api/foci/{created['focus_id']}?expedition=demo&leg=other",
    )
    assert status == 404
```

Also test list status filtering, stale PATCH/Archive, malformed JSON, missing query scope, and duplicate tag errors.

- [ ] **Step 2: Run route tests and verify failure**

Run: `uv run pytest -q tests/test_curation_server_focus_routes.py`

Expected: FAIL with unknown endpoints.

- [ ] **Step 3: Add request parsing and error mapping**

Instantiate `FocusStore(config.STATE_DIR, Path(REAL_DIR))` per request or through a helper that reads current monkeypatched config values. Do not cache `STATE_DIR` in a module-level store because tests and deployments override it. Load the scoped manifest directly from `config.leg_dir(expedition, leg) / "scored_manifest.json"`; never call `_require_out_dir()` for a Focus endpoint.

POST body carries `scope`, `source`, and text fields. PATCH and archive require `expected_revision`. Use `201` for creation and `200` for successful reads/mutations.

When `source.kind == "coverage_frontier"`, recompute Coverage from the explicit scoped manifest on
the server and pass those authoritative cells to `FocusStore.create()`. Do not trust a browser
`frontier`, `count`, adjacency, or bin-domain claim. Map-member creation likewise resolves every
posted tag against the server's scoped manifest.

- [ ] **Step 4: Run focused and regression tests**

Run: `uv run pytest -q tests/test_curation_server_focus_routes.py tests/test_curation_server_active_leg.py tests/test_curation_server_expedition_routes.py`

Expected: PASS, with active selection unchanged by all explicit-scope Focus calls.

- [ ] **Step 5: Run full verification and commit**

Run: `uv run pytest -q && uv run ruff check src tests && uv run mypy src && git diff --check`

Expected: PASS.

```bash
git add src/clawmarks/curation_server.py tests/test_curation_server_focus_routes.py
git commit -m "feat(focus): expose dossier APIs"
```

## Execution Order

Execute this plan before research-workspace navigation, Guide, and paid trial handoff. Those plans consume `Scope`, `FocusStore`, canonical digests, and cross-process locks exactly as defined here.
