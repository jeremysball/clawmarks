# S3 Funnel Durable Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve every paid RunPod image in a self-hosted S3-compatible store before RunPod's transient result expires, then import it through CLAWMARKS' no-clobber recovery path.

**Architecture:** Run VersityGW and a dedicated Tailscale Funnel sidecar as an independent Compose project with ordinary host directories for objects and IAM state. A path-style boto3 client bootstraps monthly result buckets, verifies the public boundary, takes a complete mirror before paid dispatch, and imports objects by durable provider job ID. `PaidWorkGate` freezes storage evidence before `/run`; recovery never needs a second provider submission.

**Tech Stack:** Python 3.10+, boto3 1.43.50, botocore SigV4, VersityGW 1.7.0, Tailscale 1.98.9, Docker Compose, POSIX files, SHA-256, pytest.

## Global Constraints

- Data integrity outranks convenience. Never test backup, restore, deletion, or conflict handling against production object data.
- Before any paid operation can write to the object store, take and verify a complete mirror of object data and VersityGW IAM state.
- Object data defaults to `$XDG_DATA_HOME/clawmarks/object-store/objects`; `CLAWMARKS_OBJECT_DATA_DIR` overrides it.
- Object-store backups default to `$XDG_DATA_HOME/clawmarks/object-store-backups`; `CLAWMARKS_OBJECT_BACKUP_DIR` overrides it.
- IAM state defaults to `$XDG_STATE_HOME/clawmarks/object-store/iam`; `CLAWMARKS_OBJECT_IAM_DIR` overrides it.
- Tailscale identity defaults to `$XDG_STATE_HOME/clawmarks/object-store/tailscale`; `CLAWMARKS_OBJECT_TS_STATE_DIR` overrides it.
- Pin `tailscale/tailscale:v1.98.9@sha256:f15d5d3f4a68773a853180b72496f70ba614b64de0878c43fe3da39fe0afba47`.
- Pin `versity/versitygw:v1.7.0@sha256:c4cbd9d9cb8dedbb055ac788dbd02635651b9b1cebac95b095b3217231aa87ad`.
- Test the exact `runpod/worker-comfyui:5.8.6-base@sha256:52a6c9cb8cdd9398eac42485ac485d024873f66d69f1a10f9d008dd159cbd091` upload helper before any paid production job.
- S3 clients use SigV4 and `addressing_style="path"`; virtual-host bucket addressing is forbidden.
- Funnel exposes only HTTPS port 443 and proxies only `/` to `127.0.0.1:7070`.
- Root S3 credentials and the Tailscale OAuth secret remain on the Docker host. RunPod receives only restricted worker S3 credentials.
- Worker policy explicitly denies object deletion, bucket deletion, ACL mutation, and policy mutation.
- Remote objects have indefinite retention. CLAWMARKS contains no automatic S3 delete call.
- The current and next UTC `MM-YY` buckets cover the maximum seven-day RunPod TTL.
- Set `TZ=UTC` in the RunPod worker template and compatibility container so the upstream helper's local `time.strftime("%m-%y")` matches CLAWMARKS' UTC bucket calculation.
- A known provider job ID is the durable recovery key. An ambiguous request without a provider ID is never resubmitted or auto-adopted.
- Run Python and tests through `uv run` only. Install Python packages through `uv add` with exact versions.

## Dependencies

- Complete Focus Persistence Tasks 1 and 2 before using `durable_makedirs()`, `fsync_directory()`, `file_locks()`, and `atomic_write_new()`.
- Complete Paid Trial Handoff Tasks 4 through 7 before Tasks 6 and 7 of this plan.
- Keep `deploy/object-store/` independent of the root `docker-compose.yml`, its Watchtower scope, and its Tailscale identity.
- The live compatibility and RunPod probe steps require explicit user approval. Automated tests use disposable paths and fake clients.

## File Structure

- Create `src/clawmarks/object_store.py`: settings, path-style clients, month buckets, IAM/bootstrap, public verification, listing, download, and recovery candidates.
- Create `src/clawmarks/object_backup.py`: complete object/IAM mirrors, verification, capacity checks, and backup receipts.
- Create `src/clawmarks/storage_cli.py`: storage command handlers and Compose process boundary.
- Modify `src/clawmarks/config.py`: XDG object-store path resolution.
- Modify `src/clawmarks/cli.py`: `clawmarks storage` parser and dispatch.
- Create `deploy/object-store/compose.yaml`: pinned VersityGW and Tailscale services.
- Create `deploy/object-store/tailscale/serve.json`: one HTTPS Funnel proxy.
- Create `deploy/object-store/.env.example`: names and non-secret deployment settings only.
- Create `deploy/object-store/worker-path-style/Dockerfile`: conditional worker fallback that changes only botocore addressing.
- Create `deploy/object-store/worker-path-style/patch_rp_upload.py`: fail-closed source patch for the fallback image.
- Create `deploy/object-store/compat/verify_worker_upload.py`: exact upstream helper smoke program.
- Create `tests/test_object_store.py`, `tests/test_object_backup.py`, `tests/test_storage_cli.py`, and `tests/test_object_store_compose.py`.
- Create `tests/test_s3_result_recovery.py`: durable import and ambiguity tests.
- Modify `src/clawmarks/paid_work.py`, `src/clawmarks/runpod_jobs.py`, and their tests after those files exist.
- Modify `pyproject.toml` and `uv.lock`: pin boto3 and its resolved transitive dependencies.

---

### Task 1: Resolve Storage Paths And Add The CLI Boundary

**Files:**
- Modify: `src/clawmarks/config.py`
- Modify: `src/clawmarks/cli.py`
- Create: `src/clawmarks/storage_cli.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_cli.py`
- Create: `tests/test_storage_cli.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

**Interfaces:**
- Produces: `ObjectStorePaths(data_dir, backup_dir, iam_dir, tailscale_state_dir, lock_path, receipt_dir)` frozen dataclass.
- Produces: `object_store_paths(environ: Mapping[str, str] = os.environ, home: Path | None = None) -> ObjectStorePaths`.
- Produces: `storage_cli.main(action: str, args: argparse.Namespace) -> int`.
- Produces CLI actions `paths`, `init`, `compose-config`, `bootstrap`, `verify`, `backup`, and `status`.

- [ ] **Step 1: Add the pinned boto3 dependency**

Run:

```bash
uv add boto3==1.43.50
```

Expected: `pyproject.toml` contains `boto3==1.43.50`, `uv.lock` updates, and no existing direct dependency changes version.

- [ ] **Step 2: Write failing path and parser tests**

```python
def test_object_store_paths_follow_separate_xdg_data_and_state_roots(tmp_path):
    paths = config.object_store_paths(
        {"XDG_DATA_HOME": str(tmp_path / "data"), "XDG_STATE_HOME": str(tmp_path / "state")},
        home=tmp_path / "home",
    )
    assert paths.data_dir == tmp_path / "data/clawmarks/object-store/objects"
    assert paths.backup_dir == tmp_path / "data/clawmarks/object-store-backups"
    assert paths.iam_dir == tmp_path / "state/clawmarks/object-store/iam"
    assert paths.tailscale_state_dir == tmp_path / "state/clawmarks/object-store/tailscale"
    assert paths.lock_path == tmp_path / "state/clawmarks/locks/object-store.lock"


def test_storage_subcommands_parse_without_accepting_unknown_arguments():
    parser = build_parser()
    for action in ("paths", "init", "compose-config", "bootstrap", "verify", "backup", "status"):
        args = parser.parse_args(["storage", action])
        assert args.command == "storage"
        assert args.storage_action == action
```

Also test every explicit `CLAWMARKS_OBJECT_*_DIR` override, XDG fallback to `~/.local/share` and `~/.local/state`, and `storage init` creating only the four configured roots plus receipt and lock parents.

- [ ] **Step 3: Run tests and verify failure**

Run: `uv run pytest -q tests/test_config.py tests/test_cli.py tests/test_storage_cli.py`

Expected: FAIL because storage paths and commands do not exist.

- [ ] **Step 4: Implement pure path resolution**

Add this shape to `config.py`; do not add import-time object-store constants that make environment tests order-dependent:

```python
@dataclass(frozen=True)
class ObjectStorePaths:
    data_dir: Path
    backup_dir: Path
    iam_dir: Path
    tailscale_state_dir: Path
    lock_path: Path
    receipt_dir: Path


def object_store_paths(environ=os.environ, home=None):
    home = Path.home() if home is None else Path(home)
    data_home = Path(environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    state_home = Path(environ.get("XDG_STATE_HOME") or home / ".local" / "state")
    state_dir = Path(environ.get("CLAWMARKS_STATE_DIR") or state_home / "clawmarks")
    return ObjectStorePaths(
        data_dir=Path(environ.get("CLAWMARKS_OBJECT_DATA_DIR") or data_home / "clawmarks/object-store/objects"),
        backup_dir=Path(environ.get("CLAWMARKS_OBJECT_BACKUP_DIR") or data_home / "clawmarks/object-store-backups"),
        iam_dir=Path(environ.get("CLAWMARKS_OBJECT_IAM_DIR") or state_home / "clawmarks/object-store/iam"),
        tailscale_state_dir=Path(environ.get("CLAWMARKS_OBJECT_TS_STATE_DIR") or state_home / "clawmarks/object-store/tailscale"),
        lock_path=state_dir / "locks/object-store.lock",
        receipt_dir=state_dir / "object_store/receipts",
    )
```

Import `dataclass` and `Mapping` as needed. Preserve the existing `STATE_DIR` behavior for expedition state.

- [ ] **Step 5: Add thin CLI dispatch**

In `build_parser()`, create the storage parser and set `storage_action` as required. In `main()`, reject trailing arguments through the existing shared check, then call:

```python
if args.command == "storage":
    from clawmarks.storage_cli import main as storage_main
    return storage_main(args.storage_action, args)
```

Implement `paths` as JSON with absolute resolved values and `init` through `durable_makedirs()`. Define the remaining actions as imports of the exact functions introduced by later tasks; until those functions exist, raise a clear `StorageUnavailable` instead of silently succeeding.

- [ ] **Step 6: Run tests and commit**

Run: `uv run pytest -q tests/test_config.py tests/test_cli.py tests/test_storage_cli.py`

Expected: PASS.

```bash
git add pyproject.toml uv.lock src/clawmarks/config.py src/clawmarks/cli.py src/clawmarks/storage_cli.py tests/test_config.py tests/test_cli.py tests/test_storage_cli.py
git commit -m "feat(storage): add object-store paths and CLI"
```

### Task 2: Define The Independent Pinned Compose Stack

**Files:**
- Create: `deploy/object-store/compose.yaml`
- Create: `deploy/object-store/tailscale/serve.json`
- Create: `deploy/object-store/.env.example`
- Create: `tests/test_object_store_compose.py`
- Modify: `src/clawmarks/storage_cli.py`
- Modify: `tests/test_storage_cli.py`

**Interfaces:**
- Produces: `compose_environment(paths: ObjectStorePaths, environ: Mapping[str, str]) -> dict[str, str]`.
- Produces: `compose_command(*args: str) -> list[str]` rooted at `deploy/object-store/compose.yaml`.
- `storage compose-config` runs `docker compose config --quiet` with resolved absolute bind mounts.

- [ ] **Step 1: Write failing static deployment tests**

```python
def test_compose_uses_pinned_userspace_sidecar_without_host_ports(repo_root):
    text = (repo_root / "deploy/object-store/compose.yaml").read_text()
    assert "tailscale/tailscale:v1.98.9@sha256:f15d5d3f4a68773a853180b72496f70ba614b64de0878c43fe3da39fe0afba47" in text
    assert "versity/versitygw:v1.7.0@sha256:c4cbd9d9cb8dedbb055ac788dbd02635651b9b1cebac95b095b3217231aa87ad" in text
    assert "network_mode: service:storage-tailscale" in text
    assert "ports:" not in text
    assert "NET_ADMIN" not in text
    assert "/dev/net/tun" not in text
    assert ":latest" not in text


def test_serve_config_exposes_only_s3_over_funnel(repo_root):
    config = json.loads((repo_root / "deploy/object-store/tailscale/serve.json").read_text())
    assert config["TCP"] == {"443": {"HTTPS": True}}
    host = "${TS_CERT_DOMAIN}:443"
    assert config["Web"][host]["Handlers"] == {"/": {"Proxy": "http://127.0.0.1:7070"}}
    assert config["AllowFunnel"] == {host: True}
```

Also assert the Compose project has no Watchtower labels, the Tailscale state is a bind mount, every host bind uses one `CLAWMARKS_OBJECT_*` variable, admin port 7071 is not in Serve configuration, and `.env.example` contains no credential value.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_object_store_compose.py tests/test_storage_cli.py`

Expected: FAIL because the deployment files do not exist.

- [ ] **Step 3: Create the exact Tailscale Serve and Funnel configuration**

Write `deploy/object-store/tailscale/serve.json`:

```json
{
  "TCP": {"443": {"HTTPS": true}},
  "Web": {
    "${TS_CERT_DOMAIN}:443": {
      "Handlers": {"/": {"Proxy": "http://127.0.0.1:7070"}}
    }
  },
  "AllowFunnel": {"${TS_CERT_DOMAIN}:443": true}
}
```

- [ ] **Step 4: Create the Compose project**

Write `deploy/object-store/compose.yaml` with this service contract:

```yaml
name: clawmarks-object-store

services:
  storage-tailscale:
    image: tailscale/tailscale:v1.98.9@sha256:f15d5d3f4a68773a853180b72496f70ba614b64de0878c43fe3da39fe0afba47
    hostname: clawmarks-storage
    environment:
      TS_AUTHKEY: "${CLAWMARKS_OBJECT_TS_OAUTH_SECRET:?set CLAWMARKS_OBJECT_TS_OAUTH_SECRET}?ephemeral=false"
      TS_EXTRA_ARGS: "--advertise-tags=tag:clawmarks-storage"
      TS_AUTH_ONCE: "true"
      TS_STATE_DIR: /var/lib/tailscale
      TS_SERVE_CONFIG: /config/serve.json
      TS_USERSPACE: "true"
    volumes:
      - "${CLAWMARKS_OBJECT_TS_STATE_DIR:?set CLAWMARKS_OBJECT_TS_STATE_DIR}:/var/lib/tailscale"
      - ./tailscale:/config:ro
    restart: unless-stopped

  versitygw:
    image: versity/versitygw:v1.7.0@sha256:c4cbd9d9cb8dedbb055ac788dbd02635651b9b1cebac95b095b3217231aa87ad
    network_mode: service:storage-tailscale
    environment:
      ROOT_ACCESS_KEY_ID: "${CLAWMARKS_OBJECT_ROOT_ACCESS_KEY_ID:?set CLAWMARKS_OBJECT_ROOT_ACCESS_KEY_ID}"
      ROOT_SECRET_ACCESS_KEY: "${CLAWMARKS_OBJECT_ROOT_SECRET_ACCESS_KEY:?set CLAWMARKS_OBJECT_ROOT_SECRET_ACCESS_KEY}"
    command:
      - --port
      - 127.0.0.1:7070
      - --admin-port
      - 127.0.0.1:7071
      - --iam-dir
      - /var/lib/versitygw/iam
      - --health
      - /health
      - posix
      - /var/lib/versitygw/objects
    volumes:
      - "${CLAWMARKS_OBJECT_DATA_DIR:?set CLAWMARKS_OBJECT_DATA_DIR}:/var/lib/versitygw/objects"
      - "${CLAWMARKS_OBJECT_IAM_DIR:?set CLAWMARKS_OBJECT_IAM_DIR}:/var/lib/versitygw/iam"
    depends_on:
      - storage-tailscale
    restart: unless-stopped
```

Use a directory mount for `/config`, as Tailscale requires for live Serve configuration updates. Do not add a default bridge, host port, kernel capability, or named data volume.

- [ ] **Step 5: Validate environment and Compose rendering**

`compose_environment()` copies the caller environment, inserts the four resolved path variables, and requires these secret names without printing their values:

```text
CLAWMARKS_OBJECT_TS_OAUTH_SECRET
CLAWMARKS_OBJECT_ROOT_ACCESS_KEY_ID
CLAWMARKS_OBJECT_ROOT_SECRET_ACCESS_KEY
CLAWMARKS_OBJECT_WORKER_ACCESS_KEY_ID
CLAWMARKS_OBJECT_WORKER_SECRET_ACCESS_KEY
CLAWMARKS_OBJECT_ENDPOINT_URL
```

`compose-config` executes:

```python
[
    "docker", "compose", "--project-directory", str(deploy_dir),
    "-f", str(deploy_dir / "compose.yaml"), "config", "--quiet",
]
```

If Docker is absent, return a nonzero result with `Docker Compose is required for storage compose-config`; static tests still run locally.

- [ ] **Step 6: Run tests and commit**

Run: `uv run pytest -q tests/test_object_store_compose.py tests/test_storage_cli.py`

Expected: PASS.

```bash
git add deploy/object-store/compose.yaml deploy/object-store/tailscale/serve.json deploy/object-store/.env.example src/clawmarks/storage_cli.py tests/test_object_store_compose.py tests/test_storage_cli.py
git commit -m "feat(storage): define pinned Funnel stack"
```

### Task 3: Bootstrap Restricted Monthly Buckets Idempotently

**Files:**
- Create: `src/clawmarks/object_store.py`
- Create: `tests/test_object_store.py`
- Modify: `src/clawmarks/storage_cli.py`
- Modify: `tests/test_storage_cli.py`

**Interfaces:**
- Produces: `ObjectStoreConfig.from_environ(environ: Mapping[str, str]) -> ObjectStoreConfig`.
- Produces: `s3_client(config: ObjectStoreConfig, worker: bool = False)` with path-style SigV4.
- Produces: `utc_result_buckets(now: datetime) -> tuple[str, str]`.
- Produces: `worker_bucket_policy(bucket: str, worker_access_key: str) -> dict`.
- Produces: `bootstrap_storage(config, paths, now, backup_receipt=None, admin_run=subprocess.run) -> dict`.
- Produces: `verify_bucket_assignments(config, buckets, admin_run=subprocess.run) -> dict`.

- [ ] **Step 1: Write failing client, calendar, policy, and idempotency tests**

```python
def test_month_buckets_cross_december_in_utc():
    now = datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc)
    assert utc_result_buckets(now) == ("12-26", "01-27")


def test_worker_policy_denies_destructive_actions():
    policy = worker_bucket_policy("07-26", "worker-key")
    deny = next(s for s in policy["Statement"] if s["Effect"] == "Deny")
    assert deny["Principal"] == "worker-key"
    assert set(deny["Action"]) >= {
        "s3:DeleteObject", "s3:DeleteBucket", "s3:PutBucketPolicy",
        "s3:DeleteBucketPolicy", "s3:PutBucketAcl", "s3:PutObjectAcl",
    }


def test_bootstrap_rerun_does_not_replace_worker_credentials(fake_s3, fake_admin, settings):
    first = bootstrap_storage(settings, PATHS, NOW, admin_run=fake_admin)
    second = bootstrap_storage(settings, PATHS, NOW, admin_run=fake_admin)
    assert first["buckets"] == second["buckets"] == ["07-26", "08-26"]
    assert fake_admin.create_user_calls == 1
    assert fake_admin.change_owner_calls == 2
```

Also test missing/invalid endpoint URL, HTTPS requirement, secret redaction, worker credential verification, current/next ownership mismatch, exact bucket policy canonical equality, explicit delete denial, and rejection of naive datetimes.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_object_store.py tests/test_storage_cli.py`

Expected: FAIL because `object_store.py` does not exist.

- [ ] **Step 3: Build the path-style client and month calculation**

Construct every client through this exact botocore shape:

```python
Config(
    signature_version="s3v4",
    s3={"addressing_style": "path"},
    retries={"max_attempts": 3, "mode": "standard"},
)
```

Require an `https://` endpoint with no query, fragment, username, or password. Derive the next bucket by advancing to day 28, adding four days, and replacing the result's day with one. Format both UTC dates with `%m-%y`.

- [ ] **Step 4: Implement idempotent VersityGW account and bucket setup**

Use `docker compose exec -T versitygw versitygw admin` against `http://127.0.0.1:7071`. Pass root credentials through environment variables, not argv. The exact subcommands are:

```text
list-users
create-user --access "$CLAWMARKS_OBJECT_WORKER_ACCESS_KEY_ID" --secret "$CLAWMARKS_OBJECT_WORKER_SECRET_ACCESS_KEY" --role user
list-buckets
change-bucket-owner --bucket "$bucket" --owner "$CLAWMARKS_OBJECT_WORKER_ACCESS_KEY_ID"
```

Create a missing bucket with the root boto3 client, assign it to the worker, then attach the canonical policy with `put_bucket_policy`. On rerun, require the existing worker identity, ownership, and policy to match. Never rotate or delete an account from `bootstrap_storage()`.

Initial bootstrap may proceed without a mirror only when both roots contain zero files; record that
fact in its receipt. A read-only rerun that finds the expected user, buckets, owners, and policies
also needs no new mirror. If an established root needs any mutation, require a verified
`backup_receipt` whose source map exactly matches the current object and IAM roots. Until Task 4
wires that receipt into the CLI, block with `run clawmarks storage backup before bootstrap`.

- [ ] **Step 5: Verify the worker boundary**

Using worker credentials, put a 1-byte fixture under `f"bootstrap/{uuid.uuid4().hex}.bin"`, head it, read it, and list its exact prefix. Attempt `delete_object` and require an S3 403 response. Retain the fixture. Do not issue any root or worker delete call during cleanup.

- [ ] **Step 6: Run tests and commit**

Run: `uv run pytest -q tests/test_object_store.py tests/test_storage_cli.py`

Expected: PASS.

```bash
git add src/clawmarks/object_store.py src/clawmarks/storage_cli.py tests/test_object_store.py tests/test_storage_cli.py
git commit -m "feat(storage): bootstrap restricted result buckets"
```

### Task 4: Mirror The Complete Store And Prove Public Read/Write Safety

**Files:**
- Create: `src/clawmarks/object_backup.py`
- Create: `tests/test_object_backup.py`
- Modify: `src/clawmarks/object_store.py`
- Modify: `tests/test_object_store.py`
- Modify: `src/clawmarks/storage_cli.py`
- Modify: `tests/test_storage_cli.py`

**Interfaces:**
- Produces: `mirror_object_store(paths: ObjectStorePaths, now: datetime) -> dict`.
- Produces: `verify_object_store_mirror(paths, destination) -> dict`.
- Produces: `verify_storage_capacity(data_dir, maximum_job_count, maximum_output_bytes_per_job, reserve_bytes) -> dict`.
- Produces: `public_canary(config, bucket, payload: bytes = CANARY_BYTES) -> dict`.
- Produces: `verify_storage(config, paths, now, capacity_request) -> dict`.

- [ ] **Step 1: Write failing complete-mirror tests**

```python
def test_mirror_contains_every_object_and_iam_file_with_metadata(store_paths):
    write_fixture(store_paths.data_dir / "07-26/job/a.png", b"png", mode=0o640)
    write_fixture(store_paths.iam_dir / "accounts.json", b"iam", mode=0o600)
    receipt = mirror_object_store(store_paths, NOW)
    destination = Path(receipt["destination"])
    assert (destination / "objects/07-26/job/a.png").read_bytes() == b"png"
    assert (destination / "iam/accounts.json").read_bytes() == b"iam"
    assert receipt["verified"] is True
    assert receipt["file_count"] == 2


def test_corrupt_mirror_never_writes_success_receipt(store_paths, monkeypatch):
    write_fixture(store_paths.data_dir / "07-26/job/a.png", b"paid-output")
    monkeypatch.setattr(object_backup, "copy_regular_file", corrupting_copy)
    with pytest.raises(ObjectStoreUnsafe, match="SHA-256"):
        mirror_object_store(store_paths, NOW)
    assert list(store_paths.receipt_dir.glob("backup-success-*.json")) == []
```

Also test hidden files, empty directories, symlink and special-file rejection, exact relative paths, mode, nanosecond mtime, extended attributes where supported, fsync of every copied file and directory, lock serialization, source mutation detection, insufficient free space, and preservation of incomplete destinations.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_object_backup.py tests/test_object_store.py`

Expected: FAIL because backup and verification functions do not exist.

- [ ] **Step 3: Implement the complete mirror under one object-store lock**

Acquire `file_locks([paths.lock_path])`. Create a unique destination beneath `paths.backup_dir` with `objects/`, `iam/`, and `receipt.json`. Traverse both roots with `Path.rglob("*")`; do not use a git-aware file search. Reject symlinks and non-regular files. Copy each regular file to a same-directory temporary name, flush and `fsync`, apply mode, timestamps, and each `os.listxattr()` value, then atomically publish it. Create empty directories durably.

Build source and destination maps with this value shape:

```python
{
    "objects/07-26/job/a.png": {
        "sha256": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        "byte_count": 123,
        "mode": 0o640,
        "mtime_ns": 1784160000000000000,
        "xattrs": {"user.key": "base64:dmFsdWU="},
    }
}
```

Require exact map equality and unchanged source stat values before writing `verified: true`. Fsync all destination directories from deepest to backup root. Preserve a failed destination with `verified: false` and its bounded error.

- [ ] **Step 4: Implement capacity and public canary receipts**

Capacity requires:

```python
required_bytes = maximum_job_count * maximum_output_bytes_per_job + reserve_bytes
```

Reject booleans, non-integers, and negative values. Compare against `shutil.disk_usage(paths.data_dir).free`. Record all operands and the filesystem free-byte reading.

`public_canary()` uses the public endpoint and root client to write random bytes under `f"storage-canary/{uuid.uuid4().hex}.bin"`, then uses `head_object` and `get_object`, computes SHA-256, and lists the exact prefix. It retains the object. Record endpoint, bucket, key, byte count, digest, ETag, and timestamps, never credentials or a presigned URL.

Update `storage bootstrap` to call `mirror_object_store()` before any mutation of nonempty roots and
pass that verified receipt into `bootstrap_storage()`. Keep read-only idempotent reruns free of
unnecessary backups.

- [ ] **Step 5: Make `storage backup`, `verify`, and `status` real**

`backup` writes and prints the verified receipt. `verify` checks current and next ownership, worker denial, capacity, public canary, and exact prefix listing. `status` performs no writes: report resolved paths, Compose process state, configured endpoint hostname, both bucket assignments, free bytes, and the newest verified backup receipt. Never report a secret value.

- [ ] **Step 6: Run tests and commit**

Run: `uv run pytest -q tests/test_object_backup.py tests/test_object_store.py tests/test_storage_cli.py`

Expected: PASS.

```bash
git add src/clawmarks/object_backup.py src/clawmarks/object_store.py src/clawmarks/storage_cli.py tests/test_object_backup.py tests/test_object_store.py tests/test_storage_cli.py
git commit -m "feat(storage): verify complete store mirrors"
```

### Task 5: Gate On The Exact RunPod Upload Helper

**Files:**
- Create: `deploy/object-store/compat/verify_worker_upload.py`
- Create: `deploy/object-store/worker-path-style/Dockerfile`
- Create: `deploy/object-store/worker-path-style/patch_rp_upload.py`
- Modify: `src/clawmarks/storage_cli.py`
- Modify: `tests/test_storage_cli.py`
- Modify: `tests/test_object_store.py`

**Interfaces:**
- Produces: `verify_worker_upload(config, paths, now, run=subprocess.run) -> dict`.
- Adds the exact worker-helper check to `storage verify`.
- Defines but does not deploy the path-style fallback unless the upstream image fails.

- [ ] **Step 1: Write failing command and receipt tests**

```python
def test_worker_gate_runs_exact_pinned_image(fake_run, settings, paths):
    fake_run.stdout = json.dumps({
        "runpod_version": "1.8.1", "bucket": "07-26",
        "key": "compat-job/abcd1234.png", "byte_count": 68,
        "sha256": "sha256:" + "a" * 64,
    })
    receipt = verify_worker_upload(settings, paths, NOW, run=fake_run)
    command = fake_run.calls[0].args
    assert "runpod/worker-comfyui:5.8.6-base@sha256:52a6c9cb8cdd9398eac42485ac485d024873f66d69f1a10f9d008dd159cbd091" in command
    assert receipt["verified"] is True
```

Also assert secrets enter through subprocess environment, never argv; the returned URL is not persisted; the host independently lists and reads the key; deletion with worker credentials fails; a virtual-host DNS failure blocks production; and malformed helper output fails closed.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_storage_cli.py tests/test_object_store.py`

Expected: FAIL because the worker gate does not exist.

- [ ] **Step 3: Exercise `rp_upload.upload_image()` inside the pinned image**

The compatibility script creates this fixed 1x1 PNG in a temporary directory, calls the installed helper, reads the returned presigned URL, and prints one JSON object:

```python
from importlib.metadata import version
from runpod.serverless.utils import rp_upload

job_id = "compat-job-" + uuid.uuid4().hex
url = rp_upload.upload_image(job_id, str(image_path))
downloaded = urllib.request.urlopen(url, timeout=30).read()
result = {
    "runpod_version": version("runpod"),
    "bucket": datetime.now(timezone.utc).strftime("%m-%y"),
    "key_prefix": job_id + "/",
    "byte_count": len(downloaded),
    "sha256": "sha256:" + hashlib.sha256(downloaded).hexdigest(),
}
print(json.dumps(result, sort_keys=True))
```

Run the container with `BUCKET_ENDPOINT_URL`, `BUCKET_ACCESS_KEY_ID`,
`BUCKET_SECRET_ACCESS_KEY`, and `TZ=UTC` in its environment. Mount only the read-only compatibility
script. The host then lists exactly one object under the reported prefix, downloads it through the
worker client, verifies the same bytes and digest, confirms the presigned URL used path-style
`/MM-YY/job-id/key`, and requires delete denial. Retain the object.

- [ ] **Step 4: Add the fail-closed fallback image**

The fallback starts from the exact pinned worker digest. `patch_rp_upload.py` locates `runpod.serverless.utils.rp_upload.__file__`, requires exactly the two known `Config(` constructions, and inserts:

```python
s3={"addressing_style": "path"},
```

If the expected source shape or replacement count differs, the image build exits nonzero. After patching, the Dockerfile imports the module and asserts both `Config` calls contain path-style configuration. Do not alter the handler, ComfyUI, model setup, or upload key format.

Use the fallback only when the exact upstream image fails the live compatibility check. Record the derived image digest in the endpoint configuration and rerun the same gate before any paid generation.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_storage_cli.py tests/test_object_store.py tests/test_object_store_compose.py`

Expected: PASS without Docker or network; subprocesses are fakes.

```bash
git add deploy/object-store/compat/verify_worker_upload.py deploy/object-store/worker-path-style/Dockerfile deploy/object-store/worker-path-style/patch_rp_upload.py src/clawmarks/storage_cli.py tests/test_storage_cli.py tests/test_object_store.py tests/test_object_store_compose.py
git commit -m "test(storage): gate on RunPod S3 compatibility"
```

### Task 6: Import Known Job Results Without Clobbering Local Files

**Files:**
- Modify: `src/clawmarks/object_store.py`
- Create: `tests/test_s3_result_recovery.py`
- Modify: `src/clawmarks/atomic_io.py`
- Modify: `tests/test_atomic_io.py`

**Interfaces:**
- Produces: `StoredObject(bucket, key, etag, byte_count, last_modified)` frozen dataclass.
- Produces: `list_job_objects(client, buckets, provider_job_id, maximum_count) -> list[StoredObject]`.
- Produces: `import_job_objects(client, objects, destinations, publication_root, recovery_dir, endpoint_url, now) -> list[dict]`.
- Produces: `list_unclaimed_candidates(client, buckets, claimed_job_ids, submitted_after) -> list[dict]`.
- Consumes: `atomic_write_new(path, write_fn)` from Paid Trial Handoff Task 7 or adds its identical implementation if this task executes first.

- [ ] **Step 1: Write failing recovery and no-clobber tests**

```python
def test_known_job_imports_by_frozen_bucket_and_prefix(fake_s3, tmp_path):
    fake_s3.add("07-26", "job-123/abcd1234.png", PNG_BYTES, etag='"etag"')
    objects = list_job_objects(fake_s3, ("07-26", "08-26"), "job-123", maximum_count=1)
    receipts = import_job_objects(
        fake_s3, objects, [tmp_path / "result.png"], tmp_path, tmp_path / "recovery",
        SETTINGS.endpoint_url, NOW,
    )
    assert (tmp_path / "result.png").read_bytes() == PNG_BYTES
    assert receipts[0]["storage"]["key"] == "job-123/abcd1234.png"
    assert receipts[0]["storage"]["sha256"] == sha256_bytes(PNG_BYTES)


def test_different_existing_file_is_preserved_and_incoming_bytes_are_recoverable(fake_s3, tmp_path):
    target = tmp_path / "result.png"
    target.write_bytes(b"existing")
    fake_s3.add("07-26", "job-123/abcd1234.png", PNG_BYTES)
    with pytest.raises(StorageConflict):
        import_job_objects(
            fake_s3, list_objects(fake_s3), [target], tmp_path, tmp_path / "recovery",
            SETTINGS.endpoint_url, NOW,
        )
    assert target.read_bytes() == b"existing"
    assert next((tmp_path / "recovery").glob("*.png")).read_bytes() == PNG_BYTES
```

Also test extension allowlist `.png`, `.jpg`, `.jpeg`, and `.webp`; exact job-prefix validation; duplicate keys; duplicate logical destinations; zero objects; excess count; cross-bucket duplicates; reported `ContentLength` mismatch; stream failure; checksum mismatch; same-digest adoption; fsync before receipt; and no S3 delete calls.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_s3_result_recovery.py tests/test_atomic_io.py`

Expected: FAIL because S3 result recovery does not exist.

- [ ] **Step 3: Implement strict listing and streaming download**

Require `provider_job_id` to match the durable receipt exactly and reject `/`, `..`, empty, control
characters, or a prefix not equal to `f"{provider_job_id}/"`. List both frozen buckets with
`Prefix=provider_job_id + "/"`; reject pagination beyond `maximum_count + 1` rather than truncating
evidence.

Require every destination to resolve beneath `publication_root`. For each object, call `head_object`,
stream `get_object()["Body"]` into a same-directory temporary file while counting bytes and hashing,
require the count to equal `ContentLength`, flush and fsync, then publish through
`atomic_write_new()`. Adopt an existing destination only when its digest matches. Otherwise publish
incoming bytes under the receipt's unique recovery directory and raise `StorageConflict` without
changing the existing target.

- [ ] **Step 4: Build durable storage receipt fields**

Return this exact storage shape for the caller to write atomically before manifest changes:

```python
{
    "endpoint": endpoint_url,
    "bucket": stored.bucket,
    "key": stored.key,
    "etag": stored.etag,
    "byte_count": byte_count,
    "sha256": "sha256:" + digest.hexdigest(),
    "imported_path": destination.relative_to(publication_root).as_posix(),
    "uploaded_at": stored.last_modified_utc,
    "imported_at": now_utc,
}
```

Do not persist credentials, response bodies, or presigned URLs.

- [ ] **Step 5: Report ambiguous unclaimed prefixes without adoption**

List both frozen buckets after `submission_started_at`, group by first key segment, subtract every provider ID in durable job receipts, and return candidate prefix, bucket, object count, newest modification time, and total bytes. This function has no import or provider-submit callback. A caller must present candidates for manual reconciliation.

- [ ] **Step 6: Run tests and commit**

Run: `uv run pytest -q tests/test_s3_result_recovery.py tests/test_atomic_io.py tests/test_object_store.py`

Expected: PASS.

```bash
git add src/clawmarks/object_store.py src/clawmarks/atomic_io.py tests/test_s3_result_recovery.py tests/test_atomic_io.py tests/test_object_store.py
git commit -m "feat(storage): import durable S3 job results"
```

### Task 7: Make Storage A Mandatory Paid-Work Preflight

**Files:**
- Modify: `src/clawmarks/paid_work.py`
- Modify: `src/clawmarks/runpod_jobs.py`
- Modify: `tests/test_paid_work.py`
- Modify: `tests/test_runpod_jobs.py`
- Modify: `tests/test_paid_result_recovery.py`
- Modify: `tests/test_s3_result_recovery.py`

**Interfaces:**
- Produces: `PaidWorkGate.preflight_storage(launch_id, maximum_job_count, maximum_output_bytes_per_job) -> dict`.
- Extends each safety receipt with `object_store_backup`, `storage_capacity`, `storage_canary`, `storage_endpoint`, and `storage_candidate_buckets`.
- Extends each job receipt with frozen candidate buckets and the final `storage` receipt.
- `RunPodAdapter` collects completed jobs through `list_job_objects()` and `import_job_objects()`, not transient base64 output.

- [ ] **Step 1: Write failing paid-gate ordering tests**

```python
def test_storage_preflight_is_durable_before_first_provider_byte(gate, adapter, request_spy):
    launch = gate.create_or_resume(REQUEST, "fake-runpod-key")
    gate.run_preflight(launch["launch_id"])
    saved = gate.get_launch(launch["launch_id"])
    assert saved["safety_receipt"]["object_store_backup"]["verified"] is True
    assert saved["safety_receipt"]["storage_canary"]["verified"] is True
    assert saved["safety_receipt"]["storage_candidate_buckets"] == ["07-26", "08-26"]
    request_spy.assert_not_called()


def test_expired_runpod_result_recovers_from_s3_without_resubmit(worker, fake_s3, adapter):
    claim = known_claim(provider_id="job-123", candidate_buckets=("07-26", "08-26"))
    adapter.status_response = {"id": "job-123", "status": "COMPLETED"}
    fake_s3.add("07-26", "job-123/abcd1234.png", PNG_BYTES)
    worker.reconcile_claim(claim)
    assert claim.output_path.read_bytes() == PNG_BYTES
    assert adapter.submit_count == 0
    assert load_receipt(claim)["storage"]["key"] == "job-123/abcd1234.png"
```

Also test backup, bucket, owner, TLS, SigV4, canary, capacity, and Compose-health failure before `external_dispatch_started`; restart after provider ID persistence; partial upload; upload error in RunPod output; wrong count; ambiguous initial submission candidate reporting; result receipt before manifest update; and reservation retention until every expected object imports.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_paid_work.py tests/test_runpod_jobs.py tests/test_paid_result_recovery.py tests/test_s3_result_recovery.py`

Expected: FAIL because `PaidWorkGate` has no storage preflight or S3 collector.

- [ ] **Step 3: Insert storage into the exact paid preflight order**

After account reservation and complete leg backup, but before worker-start claim:

1. Mirror and verify object data plus IAM state.
2. Verify current and next UTC bucket ownership with root and worker clients.
3. Verify capacity using the launch maximum job count and profile's fixed maximum output bytes.
4. Send and read the public canary.
5. Persist endpoint, buckets, backup receipt, capacity receipt, and canary receipt in the launch safety receipt.
6. Revalidate public authenticated access immediately before the first initial `/run` request.

A preflight failure records `external_dispatch_started: false`, releases safe reservations according to the existing gate, and never starts a worker. Do not reuse a canary or backup receipt from another launch.

- [ ] **Step 4: Collect every known provider ID from S3**

When status is `COMPLETED`, treat RunPod's `output.images[*].data` URL as informational only. List the frozen buckets by provider ID, validate the expected object count, import through Task 6, atomically extend the job receipt with `storage`, then append manifest/trial/campaign provenance. A 404 or expired RunPod result still follows this same S3 path.

If the RunPod response reports an upload error or S3 has only a partial set, mark the job and launch `needs_reconciliation`; retain every remote and local object. If the initial submission has no provider ID, list unclaimed candidates and save them under `manual_storage_candidates`; never call `/run` or import a candidate automatically.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest -q tests/test_paid_work.py tests/test_runpod_jobs.py tests/test_paid_result_recovery.py tests/test_s3_result_recovery.py`

Expected: PASS with fake S3 and fake RunPod clients only.

```bash
git add src/clawmarks/paid_work.py src/clawmarks/runpod_jobs.py tests/test_paid_work.py tests/test_runpod_jobs.py tests/test_paid_result_recovery.py tests/test_s3_result_recovery.py
git commit -m "feat(paid): require durable S3 result storage"
```

### Task 8: Verify Deployment And One Bounded Live Recovery

**Files:**
- Modify: `.env.example`
- Modify: `deploy/object-store/.env.example`
- Modify: `src/clawmarks/storage_cli.py`
- Modify: `tests/test_storage_cli.py`
- Modify: `notes/lab_notebook.md`

**Interfaces:**
- `clawmarks storage status` provides the operator's final readiness view without secrets.
- The live check proves one paid image survives without RunPod's transient response.

- [ ] **Step 1: Run all automated storage tests**

Run:

```bash
uv run pytest -q tests/test_config.py tests/test_cli.py tests/test_storage_cli.py tests/test_object_store_compose.py tests/test_object_store.py tests/test_object_backup.py tests/test_s3_result_recovery.py tests/test_atomic_io.py tests/test_paid_work.py tests/test_runpod_jobs.py tests/test_paid_result_recovery.py
```

Expected: PASS with no production path, Docker service, Funnel endpoint, or RunPod request touched.

- [ ] **Step 2: Initialize and validate the host deployment**

After setting secrets in the gitignored `.envrc`, run:

```bash
uv run clawmarks storage paths
uv run clawmarks storage init
uv run clawmarks storage compose-config
docker compose --project-directory deploy/object-store -f deploy/object-store/compose.yaml up -d
uv run clawmarks storage bootstrap
uv run clawmarks storage verify
uv run clawmarks storage backup
uv run clawmarks storage status
```

Expected: both services run, the endpoint certificate matches the configured hostname, current and next buckets belong to the worker, worker deletion fails, public canary bytes match, the exact worker upload helper passes, and the final backup receipt verifies. Append each meaningful result and any gotcha to `notes/lab_notebook.md` immediately.

- [ ] **Step 3: Stop before changing RunPod**

Present the endpoint template change, exact worker image digest, three `BUCKET_*` variable names, current storage verification receipt, maximum one-job cost, and the no-delete retention rule. Obtain explicit user approval before changing the live RunPod template or submitting a job.

- [ ] **Step 4: Run one approved paid probe**

Update the endpoint template with the verified worker image, restricted worker credentials, and
`TZ=UTC`. Submit exactly one image through `PaidWorkGate`. Save the provider ID, ignore the transient
image URL, recover by frozen buckets plus provider-ID prefix, import through the no-clobber path,
verify the local and remote SHA-256 values, and verify the durable result receipt. Keep both copies.

If any response is ambiguous, stop at `needs_reconciliation`; do not submit another job. Record the result and exact cost in `notes/lab_notebook.md`, then invoke the `runpod-status` skill and pause any idle billable pod.

- [ ] **Step 5: Run final repository verification**

Run: `uv run pytest -q && uv run ruff check src tests && uv run mypy src && git diff --check`

Expected: PASS.

- [ ] **Step 6: Commit final operations evidence**

```bash
git add .env.example deploy/object-store/.env.example src/clawmarks/storage_cli.py tests/test_storage_cli.py notes/lab_notebook.md
git commit -m "docs(storage): record durable result verification"
```
