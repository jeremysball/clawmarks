# Paid Trial Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Snapshot one Focus revision into a trial and route every curation-server and overnight-search paid image job through a durable, backup-first, spend-bounded launch gate with recoverable provenance.

**Architecture:** Separate immutable trial records from generic paid-launch records. `PaidWorkGate` owns request idempotency, locks, complete backups, durable S3 preflight, account reservations, job slots, and terminal reconciliation. `RunPodAdapter` persists an intent before `/run`; because RunPod has no client idempotency key, any ambiguous initial submission stops in `needs_reconciliation` and is never auto-repeated. Known provider IDs recover through the frozen S3 bucket set even after RunPod expires its response.

**Tech Stack:** Python 3.10+, POSIX `fcntl`, JSON/SHA-256, `urllib`, boto3 path-style S3, RunPod queue API, background threads/processes, pytest.

## Global Constraints

- Data integrity outranks convenience. All tests and smoke checks use temporary fixture legs.
- Before any paid dispatch, mirror the complete leg into `$CLAWMARKS_STATE_DIR/backups/`, `fsync` it, and verify file count plus SHA-256 content.
- Before any paid dispatch, complete the object-store mirror, capacity, bucket-ownership, and public-canary preflight in `2026-07-16-s3-funnel-durable-results.md`.
- Never delete a good record or orphan image during invalidation or recovery.
- Every paid route uses the same gate: Focus trial, standalone Cockpit, counterfactual, overnight search, retry, and future routes.
- Standalone probe CLIs remain outside this curation-workspace change and retain their mandatory complete-backup workflow. Exposing one through the server later makes it a paid route that must use this gate.
- A `launch_request_id` is route-level idempotency. A stable internal job key identifies one provider slot.
- RunPod initial `/run` submission is `intent_once`: timeout, disconnect, malformed response, or crash after intent becomes `needs_reconciliation`; never auto-submit it again.
- `/retry/<job-id>` is allowed only for a durable ID already reported `FAILED` or `TIMED_OUT`.
- A retry consumes one reserved attempt before network I/O. An ambiguous retry response becomes reconciliation-only and is never repeated automatically.
- Derive the reservation namespace from authenticated RunPod `myself.id`; expedition config never supplies account identity or price.
- Verify live endpoint ownership, GPU pools/count, worker bounds, idle timeout, and execution timeout before every reservation.
- Convert RunPod `policy.executionTimeout` and `policy.ttl` to milliseconds.
- Use `Decimal(str(value))` for money calculations and canonical decimal strings in receipts.
- Parse only GraphQL `data.myself.clientBalance`; reject aliases, booleans, malformed numbers, negative values, NaN, and infinities before reservation arithmetic.
- Acquire simultaneous file locks through one absolute-path sort and release them in reverse. Do not nest account, paid-lease, leg, and record lock classes; persist a transition, release its lock, then enter the next phase so recovery can resume after any boundary.
- No UI or test verification may make a real paid request.
- Run Python and tests through `uv run` only.

## Dependencies

- Complete Focus persistence before this plan.
- Complete the shared shell and navigation plans before the Cockpit/result UI tasks.
- Complete S3 Funnel Durable Results Tasks 1 through 6 before this plan's first paid launch integration, then apply its Task 7 alongside Tasks 7 through 10 here.
- Consume `atomic_json_write()`, `atomic_write()`, `durable_makedirs()`, `fsync_directory()`, `file_locks()`, `record_lock_path()`, `leg_lock_path()`, `leg_write_lock()`, canonical digests, `Scope`, and `FocusStore` exactly as defined there.

## File Structure

- Create `src/clawmarks/trial_store.py`: immutable evidence snapshots, trial revisions, lifecycle, and evaluation.
- Create `src/clawmarks/paid_work.py`: profiles, provider snapshots, launch and campaign records, leases, backups, reservations, slots, and recovery.
- Create `src/clawmarks/runpod_jobs.py`: RunPod submit/status/retry/cancel adapter.
- Modify `src/clawmarks/curation_server.py`: trial routes and migration of paid endpoints.
- Modify `src/clawmarks/search/run_manager.py` and `src/clawmarks/search/driver.py`: overnight launch and per-job gate integration.
- Modify leg-writing modules to respect `leg_write_lock()`.
- Modify Cockpit, Runs, Scan, Archive, Map, Coverage, and Explore renderers for provenance/reconciliation.
- Create `tests/test_trial_store.py`, `tests/test_paid_work.py`, `tests/test_runpod_jobs.py`, and route/integration tests.
- Modify `src/clawmarks/runpod_client.py` and `tests/test_runpod_client.py`: exact finite balance parsing for provider snapshots.

### Task 1: Make Every Leg Writer Respect The Backup Lock

**Files:**
- Modify: `src/clawmarks/curation_server.py`
- Modify: `src/clawmarks/search/driver.py`
- Modify: `src/clawmarks/search/seed_pool.py`
- Modify: `src/clawmarks/search/preference_settings.py`
- Modify: `src/clawmarks/search/preference_pairwise_model.py`
- Modify: `src/clawmarks/search/embed_cache.py`
- Modify: `src/clawmarks/search/score_manifest.py`
- Modify: `src/clawmarks/search/migrate_picks_to_ratings.py`
- Modify: `src/clawmarks/build/thumbnails.py`
- Modify: `src/clawmarks/build/solution_map.py`
- Modify: `src/clawmarks/build/similarity_index.py`
- Create: `tests/test_leg_write_lock_integration.py`

**Interfaces:**
- Every application write beneath `config.leg_dir(expedition, leg)` executes inside `leg_write_lock()`.
- Functions that cannot infer scope accept `scope: Scope` or `lock_context` explicitly.

- [ ] **Step 1: Write a failing backup-vs-writer serialization test**

```python
def test_backup_blocks_manifest_writer_until_copy_finishes(tmp_state, events):
    backup_process = Process(target=hold_backup_lock, args=(tmp_state, events))
    writer_process = Process(target=write_manifest, args=(tmp_state, events))
    backup_process.start()
    assert events.backup_entered.wait(2)
    writer_process.start()
    assert not events.writer_finished.wait(0.2)
    events.release_backup.set()
    assert events.writer_finished.wait(2)
```

- [ ] **Step 2: Run the integration test and verify failure**

Run: `uv run pytest -q tests/test_leg_write_lock_integration.py`

Expected: FAIL because existing writers know only `_lock` or no lock.

- [ ] **Step 3: Wrap the enumerated writes**

Move repeated JSON writes to `atomic_json_write()`. Wrap image, thumbnail, cache, manifest, preferences, seed, model metadata, state, and gallery publication in the scoped leg lock. Keep expensive computation and provider polling outside the lock; hold it only while publishing files and related records. Never use a naked `os.remove()` to invalidate embedding caches.

For `solution_map.py` and `similarity_index.py`, overwrite a cache only after a complete new temporary cache exists. Preserve the existing final cache on mismatch or recomputation failure.

- [ ] **Step 4: Run targeted writer tests**

Run: `uv run pytest -q tests/test_leg_write_lock_integration.py tests/test_atomic_io.py tests/test_run_manager.py tests/test_driver_state.py tests/test_embed_cache.py tests/test_preference_pairwise_model.py tests/test_curation_server_counterfactual_route.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clawmarks/curation_server.py src/clawmarks/search/driver.py src/clawmarks/search/seed_pool.py src/clawmarks/search/preference_settings.py src/clawmarks/search/preference_pairwise_model.py src/clawmarks/search/embed_cache.py src/clawmarks/search/score_manifest.py src/clawmarks/search/migrate_picks_to_ratings.py src/clawmarks/build/thumbnails.py src/clawmarks/build/solution_map.py src/clawmarks/build/similarity_index.py tests/test_leg_write_lock_integration.py
git commit -m "fix(storage): serialize leg writes with backups"
```

### Task 2: Snapshot Focus Evidence Into Revisioned Trials

**Files:**
- Create: `src/clawmarks/trial_store.py`
- Create: `tests/test_trial_store.py`

**Interfaces:**
- Produces: `TrialStore(state_dir: Path, real_dir: Path, focus_store: FocusStore)`.
- Produces: `create(scope, focus_id, expected_focus_revision, payload, derived_records=()) -> dict`.
- Produces: `get(scope, trial_id) -> dict`, `list_for_focus(scope, focus_id) -> list[dict]`.
- Produces: `update_draft(scope, trial_id, expected_revision, changes) -> dict`.
- Produces: `confirm(scope, trial_id, expected_revision) -> dict`.
- Produces: `update_lifecycle(scope, trial_id, allowed_from, status, **fields) -> dict`.
- Produces: `evaluate(scope, trial_id, expected_revision, judgment, notes) -> dict`.

- [ ] **Step 1: Write failing snapshot tests**

```python
def test_create_trial_freezes_focus_manifest_image_and_judgment_digests(store, scope, focus):
    trial = store.create(
        scope, focus["focus_id"], expected_focus_revision=focus["revision"],
        payload={"prompt": "owl", "negative_prompt": "blur", "strength": 1.0,
                 "cfg": 7.5, "sampler": "ddim", "steps": 28, "seeds": [1, 2]},
        derived_records=[{"kind": "redundancy_summary", "inputs": {"threshold": 0.74},
                          "value": {"cluster_count": 6}, "calculator_version": "sha256:abc"}],
    )
    assert trial["focus_snapshot"] == focus
    member = trial["evidence_snapshot"]["generated_members"][0]
    assert member["file_sha256"].startswith("sha256:")
    assert member["manifest_record_sha256"] == sha256_json(member["manifest_record"])
    assert trial["payload_sha256"] == sha256_json(trial["payload"])


def test_trial_creation_rejects_stale_focus_without_writing(store, scope, focus):
    with pytest.raises(TrialConflict):
        store.create(scope, focus["focus_id"], expected_focus_revision=focus["revision"] - 1, payload=payload())
    assert store.list_for_focus(scope, focus["focus_id"]) == []
```

Also test missing generated image, duplicate manifest tag, real-anchor digest and bundle publication at confirmation, invalid six-part contract at confirm, stale draft PATCH, frozen-field edits after confirm, and evaluation enum/revision checks.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_trial_store.py`

Expected: FAIL because `trial_store.py` does not exist.

- [ ] **Step 3: Build evidence snapshots under the leg lock**

Acquire `record_lock_path(..., focus_id)` and `leg_lock_path(..., expedition, leg)` together through
`file_locks()`, reload the Focus through `FocusStore`, then reload the manifest and judgment files.
Resolve each Focus tag exactly once and hash each image and canonical manifest record. At
confirmation, copy each real anchor to:

```text
$CLAWMARKS_STATE_DIR/evidence_bundles/sha256/<lowercase-hex>
```

Create trial and evidence-bundle directories through `durable_makedirs()`. Write a missing bundle
object through `atomic_write()` and verify its digest before publishing the trial. Preserve paths
relative to the leg or bundle root. Compute `snapshot_sha256` from the snapshot without its own
digest field, then insert the digest.

- [ ] **Step 4: Implement lifecycle and revision rules**

Use `trial_<uuid>`, revision 1, and statuses from the specification. Confirmation requires all six test-contract fields and re-verifies payload/evidence digests. Later lifecycle writes may alter only status, paid-launch link, result tags, failure, completion timestamp, and evaluation.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_trial_store.py`

Expected: PASS.

```bash
git add src/clawmarks/trial_store.py tests/test_trial_store.py
git commit -m "feat(trials): freeze Focus evidence snapshots"
```

### Task 3: Expose Draft, Confirm, And Evaluation APIs

**Files:**
- Modify: `src/clawmarks/curation_server.py`
- Create: `tests/test_curation_server_trial_routes.py`

**Interfaces:**
- Produces the trial create/get/PATCH/confirm routes from the specification.
- Produces: `POST /api/trials/<trial-id>/evaluation?expedition=<name>&leg=<name>`.
- Does not implement paid launch yet; launch returns HTTP 503 “paid launch gate not configured” until Task 8.

- [ ] **Step 1: Write failing route lifecycle tests**

```python
def test_focus_trial_create_edit_confirm_round_trip(server, focus):
    status, trial = post_json(
        server,
        f"/api/foci/{focus['focus_id']}/trials?expedition=demo&leg=round1",
        {"expected_focus_revision": focus["revision"], "payload": payload()},
    )
    assert status == 201 and trial["status"] == "draft"
    status, edited = patch_json(
        server,
        f"/api/trials/{trial['trial_id']}?expedition=demo&leg=round1",
        {"expected_revision": 1, "changes": {"payload": changed_payload()}},
    )
    assert status == 200 and edited["revision"] == 2
    status, confirmed = post_json(
        server,
        f"/api/trials/{trial['trial_id']}/confirm?expedition=demo&leg=round1",
        {"expected_revision": 2},
    )
    assert status == 200 and confirmed["status"] == "confirmed"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_curation_server_trial_routes.py`

Expected: FAIL with unknown endpoints.

- [ ] **Step 3: Add thin HTTP handlers**

Resolve all scope from URL/body, use current Focus and trial stores, and map validation/not-found/conflict/integrity errors consistently with Focus routes. Never use `_active_selection` for these endpoints.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_curation_server_trial_routes.py tests/test_trial_store.py`

Expected: PASS.

```bash
git add src/clawmarks/curation_server.py tests/test_curation_server_trial_routes.py
git commit -m "feat(trials): expose revisioned trial APIs"
```

### Task 4: Validate Paid Profiles And Calculate Conservative Reservations

**Files:**
- Create: `src/clawmarks/paid_work.py`
- Create: `tests/test_paid_work.py`
- Modify: `src/clawmarks/runpod_client.py`
- Modify: `tests/test_runpod_client.py`
- Modify: `src/clawmarks/curation_server.py`
- Create: `tests/test_paid_profile_routes.py`

**Interfaces:**
- Produces: `PaidProfile.from_expedition(scope: Scope) -> PaidProfile`.
- Produces: `RunPodProviderSnapshot(account_id, balance_usd, endpoint_id, gpu_pool_ids, gpu_count, idle_timeout_seconds, workers_min, workers_max, endpoint_execution_timeout_seconds, active_workers, retrieved_at, graphql_raw, rest_raw, health_raw)` frozen dataclass.
- Produces: `fetch_runpod_provider_snapshot(api_key: str, endpoint_id: str, gql_fn, rest_fn) -> RunPodProviderSnapshot`.
- Produces: `PaidProfile.validate_snapshot(snapshot: RunPodProviderSnapshot) -> None` and `unit_cost_usd(snapshot) -> Decimal`.
- Produces: `LaunchRequest(route_kind, scope, launch_request_id, payload_sha256, output_path, maximum_job_count, maximum_attempts_per_job, spend_cap_usd, focus_id=None, focus_revision=None, trial_id=None)` frozen dataclass.
- `LaunchRequest` also accepts nullable `campaign_id`; request-ID resumption requires an exact campaign match.
- Produces: `PaidWorkGate(state_dir: Path, provider_snapshot_fn: Callable[[str, str], RunPodProviderSnapshot], today_fn=date.today)`.
- Produces: `create_or_resume(request: LaunchRequest, api_key: str) -> dict`.
- Produces: `request_index_path(state_dir: Path, launch_request_id: str) -> Path` under `paid_launches/request_index/<sha256>.json`.
- Produces: `parse_runpod_client_balance(value: object) -> Decimal`.
- Produces: `parse_runpod_graphql_balance(payload: object) -> Decimal`.
- Produces: `claim_paid_lease(launch_id, process_identity)`, `heartbeat_paid_lease(launch_id)`, and `reconcile_paid_lease(scope)`.
- Produces: `claim_worker_start(launch_id, process_identity) -> str | None` and `mark_worker_started(launch_id, raw_claim_token, worker_identity) -> dict`.

- [ ] **Step 1: Write failing profile and reservation tests**

```python
def test_profile_cost_bound_uses_rate_ttl_and_idle():
    profile = PaidProfile(
        endpoint_id="endpoint", allowed_gpu_pool_ids=("ADA_24",),
        maximum_gpu_count=1, maximum_idle_timeout_seconds=10,
        maximum_workers=4, job_ttl_seconds=600,
        execution_timeout_seconds=500, maximum_attempts_per_job=2,
        balance_floor_usd=Decimal("0.05"),
    )
    snapshot = provider_snapshot(
        account_id="user_real", gpu_pool_ids=("ADA_24",), gpu_count=1,
        idle_timeout_seconds=5, workers_min=0, workers_max=2,
        endpoint_execution_timeout_seconds=500,
    )
    assert profile.unit_cost_usd(snapshot) == Decimal("0.18755")


def test_reservation_fails_when_estimate_exceeds_cap(gate, request):
    request = replace(request, maximum_job_count=4, spend_cap_usd=Decimal("0.10"))
    with pytest.raises(PaidWorkBlocked, match="spend cap"):
        gate.create_or_resume(request, "fake-key")


@pytest.mark.parametrize("value", [True, False, "NaN", "Infinity", "-Infinity", -1, "-0.01", None, {}])
def test_client_balance_rejects_nonfinite_boolean_negative_and_wrong_types(value):
    with pytest.raises(PaidWorkBlocked, match="clientBalance"):
        parse_runpod_client_balance(value)


def test_client_balance_accepts_only_the_exact_graphql_field():
    assert parse_runpod_client_balance("12.50") == Decimal("12.50")
    with pytest.raises(PaidWorkBlocked, match="clientBalance"):
        parse_runpod_graphql_balance({"data": {"myself": {"balance": "12.50"}}})


def test_request_id_index_prevents_cross_scope_duplicates(gate, request):
    first = gate.create_or_resume(request, "fake-key")
    cross_scope = replace(request, scope=Scope("other", "round2"))
    with pytest.raises(PaidWorkConflict, match="launch_request_id"):
        gate.create_or_resume(cross_scope, "fake-key")
    index = json.loads(request_index_path(gate.state_dir, request.launch_request_id).read_text())
    assert index["launch_id"] == first["launch_id"]
    assert index["scope"] == {"expedition": request.scope.expedition, "leg": request.scope.leg}
```

Also test missing/invalid profile fields, TTL shorter than execution timeout, price-ceiling expiry,
endpoint absent from the authenticated account, GraphQL/REST endpoint-ID disagreement, unknown or
unapproved positive GPU pool, missing live field, `workersMin > 0`, zero or excessive `workersMax`,
excessive GPU count, idle timeout, endpoint execution timeout, nonzero workers in any of `idle`,
`ready`, `running`, or `initializing`, available balance after active reservations, two profiles
sharing one authenticated account ledger, authenticated account
separation, same request ID resume, different request conflict, concurrent same-request creation,
concurrent same-account reservations, and concurrent different-account reservations.
Also test exact integer, finite float, decimal string, and zero balances; reject a missing
`data.myself.clientBalance`, `balance` or `credit` aliases, booleans, surrounding junk, NaN,
infinities, and negatives. Test request-index repair after a crash between launch and index writes,
same-ID lookup across different scopes, a stale index target, and duplicate historical records as an
integrity error that remains untouched.
Run two concurrent same-request callers through `create_or_resume()` and `claim_worker_start()`;
assert they receive one launch ID, exactly one receives a raw worker token, and the launch stores
only its digest.
Test lease recovery separately: a dead process with `external_dispatch_started: false` releases its
lease and permits the next numbered attempt; a dead or PID-reused process with true or unknown
dispatch state moves the launch to `needs_reconciliation` and retains its lease and reservation.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_paid_work.py`

Expected: FAIL because `paid_work.py` does not exist.

- [ ] **Step 3: Implement profile validation and launch identity**

Read `paid_work` from the expedition's `expedition.json`. Require a non-empty endpoint ID and
GPU-pool allowlist; positive GPU count, worker maximum, TTL, execution, floor, and integer
`maximum_attempts_per_job`; execution at least 5 seconds, TTL at least 10 seconds and no smaller than
execution, idle at least zero, and attempts at least one. Digest the canonical profile. Do not accept
`provider_account_id` or a configured rate. Reserve
`unit_cost(snapshot) * maximum_job_count * maximum_attempts_per_job`, not one execution per slot.

Pin these reviewed constants in code:

```python
RUNPOD_GPU_POOL_RATE_CEILINGS = {
    "AMPERE_16": Decimal("0.00016"),
    "AMPERE_24": Decimal("0.00019"),
    "ADA_24": Decimal("0.00031"),
}
RUNPOD_UNIVERSAL_RATE_CEILING_USD_PER_GPU_SECOND = Decimal("0.00240")
RUNPOD_RATE_CEILING_SOURCE = "https://docs.runpod.io/serverless/endpoints/endpoint-configurations"
RUNPOD_RATE_CEILING_REVIEWED_ON = date(2026, 7, 16)
RUNPOD_RATE_CEILING_MAX_AGE_DAYS = 30
```

Block launch after the validity window until a reviewed code change refreshes the table. Use the
highest mapped rate among the live positive pools; use the universal ceiling for an explicitly
allowed but unmapped pool. Fetch
GraphQL `myself { id endpoints { id gpuIds idleTimeout workersMin workersMax } }`, REST
`/v1/endpoints/<id>` fields `id`, `executionTimeoutMs`, and `gpuCount`, and queue API
`/v2/<id>/health`. Parse only positive GraphQL GPU pools; preserve exclusions in the raw receipt.
Require endpoint ownership, matching API IDs, all profile bounds, and zero pre-existing `idle`,
`ready`, `running`, or `initializing` workers before calculating cost.

Acquire a globally unique `request_<uuid>.lock`, then resolve `launch_request_id` through the durable
global request index defined in Step 4. Resume the same immutable request and reject a payload,
scope, count, cap, campaign, or provenance mismatch. For Focus trials, acquire request and trial
record locks together through the shared absolute-path ordering before writing the launch and
linking it to the trial. Non-Focus routes use the same request lock and index, so two processes or
two scopes cannot both observe "missing" and create duplicate launches.

Store the cooperative lease at
`$CLAWMARKS_STATE_DIR/locks/paid_leases/<expedition>/<leg>.json`. Serialize lease transitions with a
separate `fcntl` lock. The record contains launch ID, PID, process start-time ticks, heartbeat,
attempt number, and external-dispatch state. A preflight retry with the same request ID appends a
numbered attempt and preserves every earlier error; it never erases an attempt or creates another
launch record.

Workers refresh the heartbeat at least every 10 seconds while polling. Process identity remains the
authority: a matching live PID is not stolen because of a stale heartbeat, and a dead/PID-reused
identity follows the dispatch-state reconciliation rule.

Initialize `worker_start.status` as `unclaimed`. Under the launch-record lock, change it once to
`claimed`, store `sha256(raw_token)` plus process identity and time, and return the raw token only to
that caller. `mark_worker_started()` requires the matching raw token and records the worker identity.
A second claimant returns `None`. A dead or PID-reused claim that never reached durable `started`
becomes `needs_reconciliation`; it never reopens automatically.

- [ ] **Step 4: Implement account reservations**

Fetch an initial authenticated snapshot only to derive `sha256(account_id)`. Under
`$STATE_DIR/locks/accounts/<account-id-sha256>.lock`, fetch a fresh snapshot and require the same
account ID, reload only that account's
`paid_launches/account_reservations/<account-id-sha256>.json`, sum its nonterminal reservation decimal
strings, enforce all three specification inequalities, and durably write the reservation. Record
the balance retrieval timestamp, profile digest, selected pool ceiling, universal fallback and expiry, verified live
endpoint snapshot, unit cost, estimate, cap, floor, and authenticated account ID. Never let
separately locked accounts replace one shared reservations file.

Parse the GraphQL response by requiring nested mapping keys `data`, `myself`, and the exact
`clientBalance` spelling. Convert only `int`, finite `float`, non-empty decimal `str`, or `Decimal`;
reject `bool` before the integer check. Use `Decimal(str(value))`, then require
`balance.is_finite()` and `balance >= 0`. Do not read `balance`, `credit`, or another alias when the
exact field is absent.

Persist a global request index at
`$CLAWMARKS_STATE_DIR/paid_launches/request_index/<sha256(launch_request_id)>.json`. Under the
existing globally sorted request lock, load the index first. Its record contains schema version,
full request ID, launch ID, scope, immutable request digest, relative launch-record path, and creation
time. Require all fields and the target launch to match before resuming.

When an index is absent, scan every scoped paid-launch record under `paid_launches/` once while still
holding the request lock. Zero matches permits launch creation; one match repairs the missing index;
more than one match raises an integrity error without changing any record. Write the launch first and
the index second. A crash between those writes is therefore repairable by the one-time scan, while a
durable index makes every later cross-scope lookup direct.

- [ ] **Step 5: Add explicit paid-profile configuration**

Expose `GET` and `PATCH /api/paid-profile?expedition=<name>`. PATCH requires
`expected_profile_sha256` (`null` when no profile exists), validates the complete profile, acquires
the expedition profile lock, rejects changes while that expedition has a nonterminal launch, and
atomically replaces only the `paid_work` field in `expedition.json`. Add a ruled form to
`/status.html` with every editable profile bound plus read-only authenticated account, live endpoint
snapshot, selected pool ceiling, universal fallback, source, review date, expiry, and computed
worst-case unit cost.
Existing expeditions without a profile remain readable and get a direct configuration link; paid
launch fails closed with that recovery action instead of a generic error.

- [ ] **Step 6: Run tests and commit**

Run: `uv run pytest -q tests/test_paid_work.py tests/test_paid_profile_routes.py tests/test_curation_server_expedition_routes.py`

Expected: PASS.

```bash
git add src/clawmarks/paid_work.py src/clawmarks/runpod_client.py src/clawmarks/curation_server.py tests/test_paid_work.py tests/test_runpod_client.py tests/test_paid_profile_routes.py tests/test_curation_server_expedition_routes.py
git commit -m "feat(paid): reserve bounded provider spend"
```

### Task 5: Take And Verify Complete Leg Backups

**Files:**
- Modify: `src/clawmarks/paid_work.py`
- Modify: `tests/test_paid_work.py`
- Modify: `src/clawmarks/search/run_manager.py`
- Modify: `tests/test_run_manager.py`

**Interfaces:**
- Produces: `PaidWorkGate.mirror_leg(scope, launch_id) -> BackupReceipt`.
- Produces: `verify_mirror(source: Path, destination: Path) -> {"file_count": int, "files": dict[str, str]}`.
- Deprecates: `run_manager.backup_out_dir()` sibling backups after all callers migrate.

- [ ] **Step 1: Write failing complete-mirror tests**

```python
def test_mirror_copies_hidden_ignored_and_nested_files(gate, leg_dir):
    (leg_dir / ".hidden").write_bytes(b"hidden")
    (leg_dir / "images" / "paid.png").parent.mkdir()
    (leg_dir / "images" / "paid.png").write_bytes(b"image")
    receipt = gate.mirror_leg(SCOPE, "launch_11111111111111111111111111111111")
    assert receipt.file_count == 2
    assert receipt.files[".hidden"] == sha256_file(leg_dir / ".hidden")
    assert receipt.files["images/paid.png"] == sha256_file(leg_dir / "images/paid.png")


def test_mirror_verification_detects_same_count_different_content(gate, leg_dir, monkeypatch):
    monkeypatch.setattr(paid_work, "copy_file", corrupting_copy)
    with pytest.raises(PaidWorkBlocked, match="content"):
        gate.mirror_leg(SCOPE, "launch_11111111111111111111111111111111")
```

Also assert destination is under `state_dir/backups`, nested backup directories are created through
`durable_makedirs()`, every copied file and directory is fsynced, and no launch success receipt is
written after a mismatch.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_paid_work.py tests/test_run_manager.py`

Expected: FAIL because current backup checks count only and writes beside output.

- [ ] **Step 3: Implement complete mirror under `leg_write_lock()`**

Create the complete backup path through `durable_makedirs()`. Enumerate with `Path.rglob("*")`,
including hidden files. Reject symlinks and non-regular files rather than following paths outside the
leg. Copy each file to the dedicated backup tree, flush/fsync it, copy mode and timestamps, then
fsync directories from deepest to backup root. Build source and destination
relative-path-to-digest maps and require exact equality.

Do not delete a failed backup automatically; mark it incomplete for inspection. Never restore during preflight.

- [ ] **Step 4: Route run-manager backup calls through the gate helper**

Keep compatibility wrappers only until Task 10 migrates overnight launch. Make their destination and content verification match the shared implementation now so no route retains the unsafe sibling/count-only behavior.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_paid_work.py tests/test_run_manager.py`

Expected: PASS.

```bash
git add src/clawmarks/paid_work.py src/clawmarks/search/run_manager.py tests/test_paid_work.py tests/test_run_manager.py
git commit -m "feat(paid): verify complete leg mirrors"
```

### Task 6: Persist RunPod Intent Before Submission

**Files:**
- Create: `src/clawmarks/runpod_jobs.py`
- Create: `tests/test_runpod_jobs.py`
- Modify: `src/clawmarks/paid_work.py`
- Modify: `tests/test_paid_work.py`

**Interfaces:**
- Produces: `PaidWorkGate.claim_job_slot(launch_id, intended_tag, relative_path, payload) -> JobClaim`.
- Produces: `RunPodAdapter(api_key: str, request_fn=urlopen)`.
- Produces: `RunPodAdapter.submit_once(claim: JobClaim, profile: PaidProfile, workflow: dict) -> str`.
- Produces: `status(job_id) -> dict`, `retry_known(claim: JobClaim, current_status: str) -> dict`, and `cancel(job_id) -> dict`.

- [ ] **Step 1: Write failing intent-once tests**

```python
def test_submission_intent_is_durable_before_network_call(gate, adapter, request_spy):
    claim = gate.claim_job_slot(
        "launch_11111111111111111111111111111111", "tag_1", "tag_1.png", {"prompt": "owl"}
    )
    request_spy.assert_not_called()
    assert claim.receipt_path.exists()
    adapter.submit_once(claim, PROFILE, {"input": {"workflow": {}}})
    assert request_spy.call_count == 1


def test_ambiguous_submit_is_never_repeated(gate, timing_out_adapter):
    claim = gate.claim_job_slot(
        "launch_11111111111111111111111111111111", "tag_1", "tag_1.png", {"prompt": "owl"}
    )
    with pytest.raises(NeedsReconciliation):
        timing_out_adapter.submit_once(claim, PROFILE, WORKFLOW)
    with pytest.raises(NeedsReconciliation):
        timing_out_adapter.submit_once(claim, PROFILE, WORKFLOW)
    assert timing_out_adapter.calls == 1


def test_ambiguous_retry_consumes_attempt_and_is_never_repeated(gate, timing_out_adapter):
    claim = failed_known_claim(gate, provider_id="job_1", attempts_consumed=1)
    with pytest.raises(NeedsReconciliation):
        timing_out_adapter.retry_known(claim, current_status="FAILED")
    with pytest.raises(NeedsReconciliation):
        timing_out_adapter.retry_known(claim, current_status="FAILED")
    assert timing_out_adapter.retry_calls == 1
    assert load_receipt(claim)["attempts_consumed"] == 2
```

Also test stable deterministic key, slot cap under concurrent processes, provider ID durability
before polling, milliseconds in policy, retry rejection without known failed/timed-out ID, retry
rejection when its reserved attempt count is exhausted, durable attempt consumption before retry
network I/O, provider account or endpoint drift immediately before initial and retry calls, and 404
status becoming reconciliation rather than a new submission.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_runpod_jobs.py tests/test_paid_work.py`

Expected: FAIL because the adapter and slots do not exist.

- [ ] **Step 3: Implement slot and receipt state**

Derive `job_key = sha256_json({"launch_id": launch_id, "slot": slot_number, "payload_sha256": digest})`. Claim under the launch lock, append the slot to the launch, and write the result receipt before returning. Enforce `claimed <= maximum_job_count` and `accepted_job_count <= maximum_job_count` on every transition.

- [ ] **Step 4: Implement RunPod queue calls**

POST to `https://api.runpod.ai/v2/<endpoint-id>/run` with the Authorization header and:

```python
body = {
    **workflow,
    "policy": {
        "executionTimeout": profile.execution_timeout_seconds * 1000,
        "ttl": profile.job_ttl_seconds * 1000,
    },
}
```

Any exception or response without a non-empty string `id` marks the receipt and launch
`needs_reconciliation` and raises. A known ID is written durably before return. `/retry/<id>` reuses
that ID, only accepts recorded `FAILED` or `TIMED_OUT`, and durably consumes one of the profile's
reserved attempts plus a retry intent before calling RunPod. Exhausted attempts fail closed. A
timeout, disconnect, malformed response, or crash after that intent marks the retry ambiguous and
the launch `needs_reconciliation`. Polling the known ID may continue, but another call cannot send
the same retry intent again.

Immediately before writing request bytes, durably set the launch attempt's
`external_dispatch_started` to true. This transition occurs after the intent receipt and before the
network call; a crash on either side therefore fails toward reconciliation rather than a duplicate
submission.

Before that transition, fetch a fresh provider snapshot and require its account ID, endpoint ID,
positive GPU pools, GPU count, worker limits, idle timeout, and endpoint execution timeout to equal
the frozen safety receipt. Ignore current health counts after the preflight health-zero gate because
earlier slots in this same launch may have started workers. Any settings drift blocks the call and
moves the launch to `needs_reconciliation`; the worker cannot replace its safety receipt with a
larger live bound.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_runpod_jobs.py tests/test_paid_work.py`

Expected: PASS.

```bash
git add src/clawmarks/runpod_jobs.py src/clawmarks/paid_work.py tests/test_runpod_jobs.py tests/test_paid_work.py
git commit -m "feat(paid): persist RunPod submission intents"
```

### Task 7: Publish Results Through Recovery Receipts

**Files:**
- Modify: `src/clawmarks/atomic_io.py`
- Modify: `tests/test_atomic_io.py`
- Modify: `src/clawmarks/paid_work.py`
- Modify: `src/clawmarks/runpod_jobs.py`
- Modify: `tests/test_paid_work.py`
- Create: `tests/test_paid_result_recovery.py`

**Interfaces:**
- Produces: `publish_result(claim, stored_objects, manifest_record) -> dict`.
- Produces: `repair_provenance(launch_id) -> {"repaired": list[str], "conflicts": list[dict]}`.
- Produces: `reconcile_launch(launch_id) -> dict`.
- Produces: `resume_known_jobs() -> list[str]`.
- Produces: `atomic_write_new(path, write_fn) -> None`, an atomic no-clobber publication helper.

- [ ] **Step 1: Write failing crash-recovery tests**

```python
def test_image_receipt_is_durable_before_manifest_update(worker, fake_s3, monkeypatch):
    fake_s3.add("07-26", "job-123/abcd1234.png", b"png-bytes")
    claim = replace(CLAIM, provider_id="job-123", candidate_buckets=("07-26", "08-26"))
    monkeypatch.setattr(worker, "append_manifest", lambda *args: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        worker.publish_result(claim, worker.list_stored_objects(claim), MANIFEST_RECORD)
    assert output_image.read_bytes() == b"png-bytes"
    receipt = json.loads(claim.receipt_path.read_text())
    assert receipt["image_sha256"] == sha256_file(output_image)
    assert receipt["storage"]["key"] == "job-123/abcd1234.png"
    assert receipt["manifest_recorded_at"] is None


def test_repair_adds_only_missing_matching_provenance(worker):
    result = worker.repair_provenance("launch_11111111111111111111111111111111")
    assert result["repaired"] == ["tag_1"]
    assert result["conflicts"] == []
```

Also test conflict reporting without overwrite, preservation of incoming conflicting bytes under the
receipt recovery directory, Focus/trial nullable rules, thumbnail failure preserving image,
startup collection of every known nonterminal provider ID, recovery after RunPod's transient result
has expired, partial S3 upload, and reservation release only after terminal reconciliation.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_paid_result_recovery.py tests/test_paid_work.py`

Expected: FAIL on missing publication/recovery methods.

- [ ] **Step 3: Implement ordered publication**

Add `atomic_write_new()` to `atomic_io.py`: create a missing parent through `durable_makedirs()`,
write and fsync a same-directory temporary file, publish it with `os.link(temp, target)` so an
existing target raises instead of being replaced, fsync the parent, then unlink the temporary name.
Use `list_job_objects()` and `import_job_objects()` from the S3 plan to stream the known provider
ID's frozen bucket objects under `leg_write_lock()`. If the target already exists, adopt it only when
its digest matches. For different content, preserve the incoming paid bytes in the unique result
receipt recovery directory, mark a conflict, and leave the target untouched. Extend the receipt
with endpoint, bucket, key, ETag, byte count, SHA-256, and timestamps before appending provenance to
the manifest atomically. Add result tags to the trial only after the manifest record is durable.
Generate thumbnails last; thumbnail failure is recoverable and never removes the full image.

Every manifest record includes `launch_id` and `route_kind`; Focus-derived records also require `focus_id`, `focus_revision`, and `trial_id`.

- [ ] **Step 4: Implement idempotent repair and terminal release**

Repair reads receipts, verifies checksums, inserts only absent exact records, and reports any same-tag/different-content conflict. Terminal reconciliation releases the account reservation and paid-work lease under their locks. `needs_reconciliation` retains both.

`resume_known_jobs()` scans every nonterminal receipt with a durable provider ID at server startup
and worker restart, then immediately starts S3 result collection without another `/run`. A RunPod
404 or expired transient result does not block collection from the frozen buckets. Missing, partial,
excess, conflicting, or checksum-invalid S3 objects mark reconciliation. A receipt with intent but
no provider ID remains ambiguous, records manual unclaimed-prefix candidates, and is never submitted
again.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_paid_result_recovery.py tests/test_paid_work.py`

Expected: PASS.

```bash
git add src/clawmarks/atomic_io.py src/clawmarks/paid_work.py src/clawmarks/runpod_jobs.py tests/test_atomic_io.py tests/test_paid_result_recovery.py tests/test_paid_work.py
git commit -m "feat(paid): recover paid result provenance"
```

### Task 8: Launch Focus Trials From Cockpit

**Files:**
- Modify: `src/clawmarks/curation_server.py`
- Modify: `src/clawmarks/build/cockpit.py`
- Modify: `src/clawmarks/build/explore_hub.py`
- Modify: `src/clawmarks/build/runs_page.py`
- Modify: `tests/test_curation_server_trial_routes.py`
- Create: `tests/test_focus_trial_launch.py`

**Interfaces:**
- Produces: `POST /api/trials/<trial-id>/launch?expedition=<name>&leg=<name>`.
- Requires body: `{"expected_revision": int, "launch_request_id": "request_<uuid>", "spend_cap_usd": "decimal"}`.
- Returns HTTP 202 with launch ID after durable preflight and worker start; returns 409 for linked active/unreconciled launch and 402 for spend/balance failure.

- [ ] **Step 1: Write failing preflight sequence tests**

```python
def test_trial_launch_links_launch_before_external_dispatch(server, confirmed_trial, fake_gate):
    status, body = post_json(
        server,
        launch_url(confirmed_trial),
        {"expected_revision": confirmed_trial["revision"],
         "launch_request_id": "request_11111111111111111111111111111111",
         "spend_cap_usd": "4.00"},
    )
    assert status == 202
    trial = load_trial(confirmed_trial["trial_id"])
    launch = load_launch(body["launch_id"])
    assert trial["paid_launch_id"] == launch["launch_id"]
    assert launch["safety_receipt"]["backup"]["verified"] is True
    assert fake_gate.dispatch_observed_durable_links is True


def test_concurrent_same_request_starts_one_worker_and_one_provider_job(
    server, confirmed_trial, blocking_worker, fake_adapter
):
    body = {
        "expected_revision": confirmed_trial["revision"],
        "launch_request_id": "request_11111111111111111111111111111111",
        "spend_cap_usd": "4.00",
    }
    responses = post_concurrently(server, launch_url(confirmed_trial), body, count=2)
    assert {response.body["launch_id"] for response in responses} == {
        "launch_11111111111111111111111111111111"
    }
    assert blocking_worker.start_count == 1
    blocking_worker.release()
    assert fake_adapter.submit_count == 1
```

Add tests for same request resume, different request conflict, payload/evidence digest drift, failed preflight returning trial to confirmed, and crash repair of one-sided link.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_focus_trial_launch.py tests/test_curation_server_trial_routes.py`

Expected: FAIL because launch is disabled.

- [ ] **Step 3: Implement the exact preflight order**

Create/resume launch, link trial, verify frozen digests, reserve account spend, mirror/verify the
complete leg, mirror/verify the complete object store, verify current/next bucket ownership and
capacity, run the public write/read canary, bind evidence to both backup receipts, and persist the
frozen safety receipt. Then call
`claim_worker_start()` under the launch lock. Only the handler receiving the raw claim token starts
the worker and passes it as immutable input; same-request handlers return the existing launch. The
worker calls `mark_worker_started()` with that token before claiming a provider slot. It receives
the verified provider snapshot and uses `RunPodAdapter` plus result receipts without re-reading
mutable endpoint config.

During curation-server startup, call `resume_known_jobs()` before accepting another launch. This
restarts collection for durable provider IDs without repeating `/run`; ambiguous intent-only slots
remain blocked for human reconciliation.

- [ ] **Step 4: Update Cockpit and Explore**

Cockpit shows the complete Focus brief, evidence, exact payload, output path, job count, estimate, cap, profile source, balance floor, and backup state. Confirmation and Launch remain separate buttons. Store `launch_request_id` in `sessionStorage` by trial until a terminal HTTP response so a browser retry reuses it.

Explore and Runs display trial/launch state, reconciliation warnings, result links, and human evaluation controls. They never offer automatic retry for an ambiguous RunPod submission.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_focus_trial_launch.py tests/test_curation_server_trial_routes.py tests/test_explore_hub.py tests/test_runs_page.py`

Expected: PASS.

```bash
git add src/clawmarks/curation_server.py src/clawmarks/build/cockpit.py src/clawmarks/build/explore_hub.py src/clawmarks/build/runs_page.py tests/test_focus_trial_launch.py tests/test_curation_server_trial_routes.py tests/test_explore_hub.py tests/test_runs_page.py
git commit -m "feat(trials): launch Focus-scoped paid work"
```

### Task 9: Migrate Standalone Cockpit And Counterfactual Routes

**Files:**
- Modify: `src/clawmarks/curation_server.py:676-742,1879-2039`
- Modify: `src/clawmarks/shared_ui.py`
- Modify: `src/clawmarks/build/cockpit.py`
- Modify: `tests/test_curation_server_cockpit_scoring.py`
- Modify: `tests/test_curation_server_counterfactual_route.py`
- Modify: `tests/test_shared_ui.py`
- Create: `tests/test_cockpit.py`
- Create: `tests/test_paid_route_gate.py`

**Interfaces:**
- Legacy standalone Cockpit and counterfactual records gain `launch_id` and `route_kind`.
- Both handlers require a client-supplied route-level `launch_request_id` and call `PaidWorkGate`; neither calls `runpod_balance()`, `comfy_post()`, or `comfy_get()` directly.

- [ ] **Step 1: Write failing direct-dispatch guard tests**

```python
@pytest.mark.parametrize("path,payload", [
    ("/api/counterfactual", {"origin_tag": "a", "prompt": "cat", "spend_cap_usd": "4.00",
                              "launch_request_id": "request_11111111111111111111111111111111"}),
    ("/api/cockpit/queue/trial_11111111111111111111111111111111/run", {"spend_cap_usd": "4.00",
                                        "launch_request_id": "request_22222222222222222222222222222222"}),
])
def test_paid_routes_use_gate_and_return_launch_id(server, path, payload, fake_gate, monkeypatch):
    monkeypatch.setattr(cs, "comfy_post", lambda *args: pytest.fail("direct dispatch"))
    status, body = post_json(server, path, payload)
    assert status in {200, 202}
    assert body["launch_id"].startswith("launch_")
    assert fake_gate.calls == 1
```

Update old counterfactual tests so partial batches assert durable receipts and no submission after the first ambiguous slot.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_paid_route_gate.py tests/test_curation_server_counterfactual_route.py tests/test_curation_server_cockpit_scoring.py`

Expected: FAIL because both routes dispatch directly.

- [ ] **Step 3: Migrate handlers and workers**

Build immutable standalone launch requests with nullable Focus/trial fields. Require explicit
expedition and leg in each payload rather than resolving `_active_selection` after the request
starts. Keep pinned-seed single-job behavior. Replace direct image writes and record updates with
`publish_result()`. Use the same `claim_worker_start()` token handoff as Focus trials so concurrent
same-request handlers start one worker. Preserve old UI response fields while adding launch ID and
status URL where external compatibility requires them.

Update Cockpit and `_LIGHTBOX_JS` clients to generate a full `request_<uuid>` once with
`crypto.randomUUID().replaceAll('-', '')`, keep it in `sessionStorage` until a terminal HTTP
response, include explicit expedition/leg, and display the conservative estimate plus an editable
spend cap before POST. A network retry reuses the stored request ID.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_paid_route_gate.py tests/test_curation_server_counterfactual_route.py tests/test_curation_server_cockpit_scoring.py`

Expected: PASS.

```bash
git add src/clawmarks/curation_server.py src/clawmarks/shared_ui.py src/clawmarks/build/cockpit.py tests/test_paid_route_gate.py tests/test_curation_server_counterfactual_route.py tests/test_curation_server_cockpit_scoring.py tests/test_shared_ui.py tests/test_cockpit.py
git commit -m "refactor(paid): route interactive generation through gate"
```

### Task 10: Migrate Overnight Search To Bounded Job Slots

**Files:**
- Modify: `src/clawmarks/paid_work.py`
- Modify: `src/clawmarks/search/run_manager.py`
- Modify: `src/clawmarks/search/driver.py`
- Modify: `src/clawmarks/compute/comfyui.py`
- Modify: `src/clawmarks/curation_server.py:1823-1858`
- Modify: `src/clawmarks/build/runs_page.py`
- Modify: `tests/test_run_manager.py`
- Modify: `tests/test_paid_work.py`
- Modify: `tests/test_driver_state.py`
- Create: `tests/test_driver_paid_slots.py`
- Modify: `tests/test_curation_server_searchrun_routes.py`
- Modify: `tests/test_runs_page.py`

**Interfaces:**
- `run_manager.launch_run(..., launch_id: str, campaign_id: str, worker_claim_token: str)` starts only after shared preflight.
- Driver CLI requires `--launch-id`, `--campaign-id`, and `--worker-claim-token` for UI-paid runs.
- `submit_and_collect(..., launch_id, gate, adapter)` claims one slot per job and stops when no slots remain.
- Produces: `SearchCampaignStore(state_dir).create_or_resume(scope, config) -> dict`, `reserve_remaining(campaign_id, launch_id, unit_cost, maximum_attempts) -> dict`, and `reconcile_launch(campaign_id, launch_id) -> dict`.
- `PaidWorkGate.adopt_paid_lease(launch_id, worker_claim_token, process_identity)` verifies the generic worker-start claim and transfers the preflight lease to the driver before any provider call.
- `PaidWorkGate.cancel_launch(launch_id) -> dict` cancels every known nonterminal provider ID and preserves ambiguous slots.

- [ ] **Step 1: Write failing bounded-search tests**

```python
def test_driver_never_submits_more_than_launch_slots(fake_gate, fake_adapter):
    fake_gate.remaining = 2
    result = submit_and_collect(
        CFG, three_jobs(), OUT, "gen1",
        launch_id="launch_11111111111111111111111111111111",
        gate=fake_gate, adapter=fake_adapter,
    )
    assert fake_adapter.submit_count == 2
    assert len(result) == 2


def test_search_launch_count_uses_remaining_campaign_budget(profile, snapshot, config):
    unit_cost = profile.unit_cost_usd(snapshot)
    campaign = {
        "campaign_id": "campaign_11111111111111111111111111111111",
        "hard_budget_usd": "8.00",
        "maximum_generations": config.max_generations,
        "generation_batch_size": config.gen_batch_size,
        "completed_generations": 1,
        "accepted_slot_count": 20,
        "committed_cost_usd": str(unit_cost * 20),
        "active_reservations": {},
    }
    request = build_search_launch_request(
        config, profile, snapshot, campaign,
        "request_11111111111111111111111111111111"
    )
    hard_budget = (
        Decimal(str(config.budget_usd_cap))
        - Decimal(str(config.budget_safety_margin))
    )
    remaining_budget = hard_budget - Decimal(campaign["committed_cost_usd"])
    budget_slots = int(
        remaining_budget
        // (unit_cost * profile.maximum_attempts_per_job)
    )
    remaining_slots = config.max_generations * config.gen_batch_size - 20
    assert request.maximum_job_count == min(remaining_slots, budget_slots)


def test_terminal_restart_cannot_receive_full_campaign_budget_again(
    campaign_store, completed_launch, config, profile, snapshot
):
    campaign = campaign_store.reconcile_launch(
        completed_launch["campaign_id"], completed_launch["launch_id"]
    )
    resumed = campaign_store.reserve_remaining(
        campaign["campaign_id"], "launch_22222222222222222222222222222222",
        profile.unit_cost_usd(snapshot), profile.maximum_attempts_per_job,
    )
    assert resumed["reserved_cost_usd"] <= (
        Decimal(campaign["hard_budget_usd"])
        - Decimal(campaign["committed_cost_usd"])
    )
    assert resumed["maximum_job_count"] < config.max_generations * config.gen_batch_size
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_driver_paid_slots.py tests/test_paid_work.py tests/test_run_manager.py tests/test_curation_server_searchrun_routes.py`

Expected: FAIL because the driver has no launch identity or slot cap.

- [ ] **Step 3: Build one generic launch before spawning**

The first search route creates `campaign_<uuid>` under
`$STATE_DIR/search_campaigns/<expedition>/<leg>/` and freezes decimal-string hard budget, safety
margin, maximum generations, and batch size. It records that ID in server-owned search state. A
later request must resume that campaign until it is explicitly closed; the browser cannot mint a
new campaign by losing session storage.

Persist this shape through `atomic_json_write()` after `durable_makedirs()` creates its record tree:

```json
{
  "schema_version": 1,
  "campaign_id": "campaign_11111111111111111111111111111111",
  "scope": {"expedition": "demo", "leg": "round1"},
  "status": "active",
  "budget_usd_cap": "8.50",
  "budget_safety_margin": "0.50",
  "hard_budget_usd": "8.00",
  "maximum_generations": 10,
  "generation_batch_size": 20,
  "launch_ids": [],
  "completed_generations": 0,
  "accepted_slot_count": 0,
  "consumed_attempt_count": 0,
  "committed_cost_usd": "0",
  "active_reservations": {},
  "created_at": "2026-07-16T00:00:00Z",
  "updated_at": "2026-07-16T00:00:00Z"
}
```

Allowed statuses are `active`, `completed`, `cancelled`, and `needs_reconciliation`. Freeze the
scope and four configured bounds after creation. A config mismatch conflicts instead of silently
expanding an existing campaign.

Under the campaign lock, derive remaining generations, accepted slots, committed attempt cost, and
active reservations from every linked launch and receipt. Build the new launch from the minimum of
those remaining capacities. Construct the hard budget with
`Decimal(str(cap)) - Decimal(str(margin))`, never `Decimal(str(cap - margin))`. Block a replacement
while an earlier launch is active or ambiguous. Terminal reconciliation commits consumed attempt
ceilings and releases only unused campaign reservation.

Perform the shared reservation/backup preflight, then use `claim_worker_start()` to obtain the one
raw token. Start the driver with `--launch-id`, `--campaign-id`, and that token, then wait up to five
seconds for the driver to verify it through `adopt_paid_lease()` and replace the preflight PID/start
ticks with its own. Adoption failure kills and reaps the pre-dispatch driver, records a failed
attempt, and releases the safe account and campaign reservations. Remove the old
balance/count-only backup checks after migration. Keep the process identity lock for stop/status,
now keyed to launch ID.

- [ ] **Step 4: Replace direct driver submissions**

Move RunPod URL/key globals out of import time. The driver claims slots, writes intents, submits
once, refreshes its paid-lease heartbeat every 10 seconds, polls known IDs, publishes through
receipts, and stops cleanly when no slots remain. Keep its live balance telemetry as informational
only; the durable reservation and slot count authorize spend.

The Runs client generates and retains a full launch request ID exactly like Cockpit and displays the
server-owned campaign ID, remaining slot count, committed conservative cost, and remaining hard
budget. Stop first
calls `cancel_launch()` for every durable provider ID, then signals the driver process group. It
releases the reservation only after cancellation/status reconciliation proves no known job remains
billable. A slot with an ambiguous initial submission or failed cancellation moves the launch to
`needs_reconciliation` and retains the lease/reservation.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_driver_paid_slots.py tests/test_paid_work.py tests/test_driver_state.py tests/test_run_manager.py tests/test_curation_server_searchrun_routes.py`

Expected: PASS.

```bash
git add src/clawmarks/paid_work.py src/clawmarks/search/run_manager.py src/clawmarks/search/driver.py src/clawmarks/compute/comfyui.py src/clawmarks/curation_server.py src/clawmarks/build/runs_page.py tests/test_paid_work.py tests/test_driver_paid_slots.py tests/test_driver_state.py tests/test_run_manager.py tests/test_curation_server_searchrun_routes.py tests/test_runs_page.py
git commit -m "refactor(search): enforce paid launch job slots"
```

### Task 11: Surface Provenance And Recovery Across Evidence Tools

**Files:**
- Modify: `src/clawmarks/build/scan_gallery.py`
- Modify: `src/clawmarks/build/elite_archive.py`
- Modify: `src/clawmarks/build/map_view.py`
- Modify: `src/clawmarks/build/coverage_map.py`
- Modify: `src/clawmarks/build/runs_page.py`
- Modify: `src/clawmarks/build/explore_hub.py`
- Modify: `src/clawmarks/curation_server.py`
- Create: `tests/test_paid_provenance_ui.py`

**Interfaces:**
- Produces: `GET /api/paid-launches/<launch-id>?expedition=<name>&leg=<name>`.
- Produces: `POST /api/paid-launches/<launch-id>/repair` with no dispatch capability.
- Every paid result links to launch; Focus results also link to trial and source Focus.

- [ ] **Step 1: Write failing provenance UI tests**

```python
def test_focus_result_links_to_focus_trial_and_launch(render_result):
    html = render_result({
        "tag": "result_1", "launch_id": "launch_11111111111111111111111111111111",
        "route_kind": "focus_trial",
        "focus_id": "focus_11111111111111111111111111111111", "focus_revision": 3,
        "trial_id": "trial_11111111111111111111111111111111",
    })
    assert "launch_11111111111111111111111111111111" in html
    assert "focus_11111111111111111111111111111111" in html
    assert "trial_11111111111111111111111111111111" in html


def test_reconciliation_state_offers_repair_not_resubmit(runs_html):
    assert "Repair provenance" in runs_html
    assert "Submit again" not in runs_html
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_paid_provenance_ui.py`

Expected: FAIL because manifests have no universal launch link.

- [ ] **Step 3: Add read/repair routes and links**

Validate explicit scope before returning launch records. Repair invokes only receipt reconciliation. Render text/pattern provenance markers on images and exact links back to explicit Focus URLs. Keep archived Foci readable.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_paid_provenance_ui.py tests/test_scan_gallery.py tests/test_elite_archive.py tests/test_map_view.py tests/test_coverage_map.py tests/test_runs_page.py tests/test_explore_hub.py`

Expected: PASS.

```bash
git add src/clawmarks/build/scan_gallery.py src/clawmarks/build/elite_archive.py src/clawmarks/build/map_view.py src/clawmarks/build/coverage_map.py src/clawmarks/build/runs_page.py src/clawmarks/build/explore_hub.py src/clawmarks/curation_server.py tests/test_paid_provenance_ui.py
git commit -m "feat(paid): expose result provenance and repair"
```

### Task 12: Verify Failure Safety End To End

**Files:**
- Modify: `src/clawmarks/trial_store.py`
- Modify: `src/clawmarks/paid_work.py`
- Modify: `src/clawmarks/runpod_jobs.py`
- Modify: `src/clawmarks/curation_server.py`
- Modify: `src/clawmarks/search/run_manager.py`
- Modify: `src/clawmarks/search/driver.py`
- Modify: `tests/test_trial_store.py`
- Modify: `tests/test_paid_work.py`
- Modify: `tests/test_runpod_jobs.py`
- Modify: `tests/test_paid_result_recovery.py`
- Modify: `tests/test_focus_trial_launch.py`
- Modify: `tests/test_paid_route_gate.py`
- Modify: `tests/test_driver_paid_slots.py`
- Modify: `tests/test_paid_provenance_ui.py`

**Interfaces:**
- Verifies every crash boundary with fake provider and temporary state.

- [ ] **Step 1: Add a parameterized crash-boundary integration test**

Inject failure after each durable step: launch creation, trial link, account reservation, campaign
reservation, leg backup copy, leg backup verification, object-store backup copy, object-store backup
verification, capacity receipt, public canary, safety receipt, worker-start claim, worker-start
acknowledgment, initial intent, retry intent, provider response, provider-ID receipt, S3 download,
image write, storage receipt, manifest write, trial result link, campaign reconciliation, and
account-reservation release. For every case assert the last good JSON parses, no image is deleted, one request starts at
most one worker, accepted jobs never exceed slots, campaign capacity never increases after consumed
attempts, and retry behavior matches `external_dispatch_started`.

- [ ] **Step 2: Run all paid and trial tests**

Run: `uv run pytest -q tests/test_trial_store.py tests/test_paid_work.py tests/test_runpod_jobs.py tests/test_paid_result_recovery.py tests/test_focus_trial_launch.py tests/test_paid_route_gate.py tests/test_driver_paid_slots.py tests/test_paid_provenance_ui.py`

Expected: PASS with zero network calls outside fakes.

- [ ] **Step 3: Verify live UI with Playwright MCP**

Serve disposable state and a fake provider. At desktop and 390px, create/confirm/launch a Focus trial, inspect preflight values, observe completion, open provenance from Scan and Runs, submit evaluation, and simulate `needs_reconciliation`. Confirm the UI offers inspection/repair and never automatic resubmission.

- [ ] **Step 4: Run final repository verification**

Run: `uv run pytest -q && uv run ruff check src tests && uv run mypy src && git diff --check`

Expected: PASS.

- [ ] **Step 5: Commit verification fixes**

```bash
git add src/clawmarks/trial_store.py src/clawmarks/paid_work.py src/clawmarks/runpod_jobs.py src/clawmarks/curation_server.py src/clawmarks/search/run_manager.py src/clawmarks/search/driver.py tests/test_trial_store.py tests/test_paid_work.py tests/test_runpod_jobs.py tests/test_paid_result_recovery.py tests/test_focus_trial_launch.py tests/test_paid_route_gate.py tests/test_driver_paid_slots.py tests/test_paid_provenance_ui.py
git commit -m "fix(paid): close launch recovery boundaries"
```
