# S3 Funnel Durable Results Design

**Status:** Approved 2026-07-16

## Purpose

RunPod retains asynchronous results for only 30 minutes. A completed paid generation can therefore
disappear if CLAWMARKS crashes, loses connectivity, or fails to poll in time. This design gives the
existing RunPod ComfyUI worker a durable destination that it writes before reporting completion.

The storage service runs on the user's own Docker host. VersityGW provides the S3-compatible API over
a normal POSIX directory. A dedicated Tailscale sidecar exposes that API through Tailscale Funnel at
one public HTTPS hostname. CLAWMARKS then imports and verifies each object into its expedition and leg
without depending on RunPod's result-retention window.

## Goals

- Preserve every successfully uploaded paid image independently of RunPod result retention.
- Deploy with one small, separate Docker Compose project.
- Use maintained Go services for the storage and network boundary.
- Keep object data visible as ordinary host files that the existing backup workflow can inspect.
- Expose only the authenticated S3 API to the public internet.
- Recover a known RunPod job by listing objects under its job-ID prefix.
- Preserve the paid-work gate's intent-once and no-clobber rules.
- Fail closed before paid dispatch when storage, backup, capacity, TLS, or authentication is unsafe.

## Non-Goals

- Distributed or multi-host object storage.
- Automatic object expiration or garbage collection.
- Public bucket access or an internet-facing administration UI.
- Replacing the expedition and leg output directory with S3 as the primary application filesystem.
- General-purpose storage for unrelated projects.
- Replacing the existing RunPod endpoint, model volume, or ComfyUI workflow.

## Chosen Architecture

The deployment is a separate Compose project under `deploy/object-store/`. It does not share the
existing curation server's lifecycle, Watchtower scope, Tailscale identity, or `docker compose down`
operation.

The project contains two long-running services:

1. `storage-tailscale` runs the official Tailscale container as a dedicated
   `clawmarks-storage` node.
2. `versitygw` runs a pinned VersityGW release with the POSIX backend and
   `network_mode: service:storage-tailscale`.

VersityGW listens on `127.0.0.1:7070` inside the shared network namespace. Neither service publishes
a host port. Tailscale Serve configuration terminates HTTPS on port 443 and proxies `/` to the local
S3 API. `AllowFunnel` is true only for that HTTPS listener.

The stack uses Tailscale's default userspace networking. It needs neither `/dev/net/tun` nor
`NET_ADMIN`. The Compose file pins `tailscale/tailscale:v1.98.9` at manifest digest
`sha256:f15d5d3f4a68773a853180b72496f70ba614b64de0878c43fe3da39fe0afba47` and
`versity/versitygw:v1.7.0` at manifest digest
`sha256:c4cbd9d9cb8dedbb055ac788dbd02635651b9b1cebac95b095b3217231aa87ad`. It never uses `latest`.

The public endpoint is:

```text
https://clawmarks-storage.<tailnet>.ts.net
```

S3 clients use path-style addressing:

```text
https://clawmarks-storage.<tailnet>.ts.net/<bucket>/<key>
```

Virtual-host addressing is forbidden because Tailscale provisions one certificate for the node
hostname, not wildcard certificates for bucket subdomains.

## Host State And Data

Every host path has an explicit override and an XDG default:

| Purpose | Override | Default |
|---|---|---|
| Object data | `CLAWMARKS_OBJECT_DATA_DIR` | `$XDG_DATA_HOME/clawmarks/object-store/objects` |
| Object-store backups | `CLAWMARKS_OBJECT_BACKUP_DIR` | `$XDG_DATA_HOME/clawmarks/object-store-backups` |
| VersityGW IAM state | `CLAWMARKS_OBJECT_IAM_DIR` | `$XDG_STATE_HOME/clawmarks/object-store/iam` |
| Tailscale identity | `CLAWMARKS_OBJECT_TS_STATE_DIR` | `$XDG_STATE_HOME/clawmarks/object-store/tailscale` |

When an XDG variable is unset, data defaults below `~/.local/share` and state defaults below
`~/.local/state`. A setup command resolves these paths before invoking Compose. The Compose file
does not contain a username, home directory, workspace path, or other host-specific absolute path.

VersityGW's POSIX backend maps buckets to top-level directories and objects to ordinary files. IAM
metadata remains separate from object data. The deployment does not depend on experimental object
versioning for correctness. Unique provider job IDs and no-clobber local publication provide the
primary overwrite defense.

## Tailscale Identity And Policy

The sidecar enrolls through an OAuth client with only `auth_keys:write` and permission to apply
`tag:clawmarks-storage`. Enrollment creates a non-ephemeral tagged node. `TS_STATE_DIR` persists the
node identity so ordinary restarts keep the same Funnel hostname.

Tailnet policy:

- defines `tag:clawmarks-storage` with administrative ownership;
- grants the Funnel node attribute only to `tag:clawmarks-storage`;
- grants the storage node no access to unrelated tailnet services;
- leaves MagicDNS and HTTPS enabled.

The OAuth secret and all S3 credentials live in the repository's gitignored `.envrc`, never in a
tracked Compose file, image, script, or documentation example. The OAuth client cannot alter DNS,
policy, users, or unrelated devices.

## S3 Accounts And Buckets

VersityGW runs internal IAM with two credential classes:

- Root credentials stay on the Docker host and support bootstrap, bucket assignment, and recovery.
- A dedicated worker account is the only S3 identity copied into the RunPod template.

The worker account receives access only to assigned result buckets. Its bucket policy allows put,
get, head, and list operations and denies object deletion, bucket deletion, policy mutation, and ACL
mutation. CLAWMARKS contains no automatic remote-delete call.

The upstream `runpod` upload helper used by `worker-comfyui:5.8.6-base` selects a bucket named from
the worker's UTC completion month in `MM-YY` form and writes each image below:

```text
<runpod-job-id>/<random-eight-hex>.<extension>
```

The RunPod template and compatibility container set `TZ=UTC`. The upstream helper calls local
`time.strftime("%m-%y")`; fixing the process timezone makes that external behavior match the UTC
bucket calculation at month boundaries.

`clawmarks storage bootstrap` creates or verifies the current and next UTC month buckets and assigns
both to the worker account. The command is safe to rerun and must run again when `storage status`
reports that the next month is absent. Paid preflight verifies both assignments and fails closed with
the exact bootstrap command when either is missing. RunPod job TTL is at most seven days, so these
two buckets cover every permitted month boundary. The paid-launch record freezes both candidate
bucket names before `/run`.

Initial bootstrap may write without a mirror only when both object and IAM roots contain zero files.
An idempotent rerun that makes no change is read-only. Any later bootstrap mutation first takes and
verifies the complete object plus IAM mirror described below and proves that its source map still
matches the live roots.

## Compatibility Gate

The RunPod worker's upload helper is convenient but its S3 addressing behavior is an external
contract. Implementation begins with a compatibility test that uses the exact `runpod` Python
package version from the pinned worker image to upload a tiny PNG through the Funnel endpoint.

The gate proves all of the following:

- botocore signs the request in path style;
- Funnel preserves the signed `Host` header;
- VersityGW accepts the signed `PutObject` request;
- the returned presigned URL reads the same bytes;
- listing the job-ID prefix returns the object;
- the worker account cannot delete the disposable compatibility object.

If the upstream helper uses virtual-host addressing, the implementation builds a minimal derived
worker image from the already-pinned `5.8.6-base` digest. The derived layer changes only the upload
client configuration to `addressing_style="path"` and adds a regression test. It does not fork
ComfyUI, the handler, model loading, or generation logic. No paid production job runs until either
the upstream image or this defined fallback passes the compatibility gate.

## Backup Contract

The object store becomes a directory of irreplaceable RunPod-billed output. The project-wide
complete-mirror rule therefore applies before every paid operation that can write to it.

The paid-work gate takes two verified mirrors before dispatch:

1. the existing complete expedition and leg mirror;
2. a complete object-store mirror containing object data and VersityGW IAM metadata.

The object-store mirror is written outside the live object root. It preserves file contents,
directory structure, permissions, timestamps, and extended attributes. It `fsync`s copied files and
directories, then verifies file count and SHA-256 content before the launch safety receipt can
succeed. A same-filesystem hard-link or reflink snapshot is acceptable only when its implementation
preserves the old inode after VersityGW's atomic publication. The verifier must prove that property
with a disposable fixture before enabling the optimization. Otherwise the gate performs a full
copy.

No backup or restore test writes to production object data. Recovery tests use disposable temporary
roots. Any future production restore starts by taking and verifying another complete mirror of the
current state.

## Paid Launch Sequence

The existing `PaidWorkGate` remains the only route to RunPod. Storage adds these steps before its
provider dispatch:

1. Verify the immutable paid payload, account reservation, endpoint settings, and complete leg
   backup as already specified.
2. Take and verify the complete object-store mirror.
3. Verify the current and next UTC result buckets and worker ownership.
4. Check free storage against `maximum_job_count * maximum_output_bytes_per_job` plus a configured
   reserve.
5. Send an authenticated write/read canary through the public Funnel endpoint and compare SHA-256.
6. Persist the endpoint, candidate buckets, canary receipt, capacity receipt, and object-store
   backup receipt in the paid-launch safety receipt.
7. Revalidate the public endpoint immediately before the first `/run` request.

Any failure occurs before provider request bytes leave the process and releases the attempt's cost
reservation according to the existing preflight rules.

## Result Import And Recovery

RunPod uploads every generated image before it returns `COMPLETED`. Its presigned response URL is a
convenience, not the durable identity.

For each known provider job ID, CLAWMARKS:

1. lists the two frozen candidate buckets under `<runpod-job-id>/`;
2. rejects unexpected extensions, keys outside the prefix, duplicate keys, and object counts above
   the claimed slot's maximum;
3. downloads each object through an authenticated S3 client to a temporary file in the intended
   local directory;
4. verifies byte count and SHA-256;
5. flushes and `fsync`s the temporary file;
6. publishes only when the intended path does not exist, then `fsync`s the parent directory;
7. adopts an existing same-digest file and preserves a different-digest file in the receipt's
   recovery directory;
8. atomically writes a result receipt before updating manifests, launches, or trials.

Each result receipt adds:

```json
{
  "storage": {
    "endpoint": "https://clawmarks-storage.example.ts.net",
    "bucket": "07-26",
    "key": "provider-job-id/abcd1234.png",
    "etag": "quoted-etag",
    "byte_count": 123456,
    "sha256": "sha256:lowercase-hex",
    "imported_path": "relative/path.png",
    "uploaded_at": "2026-07-16T00:00:00Z",
    "imported_at": "2026-07-16T00:01:00Z"
  }
}
```

A slot reaches `completed` only after every expected object has a durable receipt and verified local
copy. A launch reaches `completed` only after every claimed slot completes.

If RunPod's status result expires, reconciliation uses the durable provider job ID and frozen bucket
set to recover the same objects. If the initial `/run` response was ambiguous and no provider ID was
recorded, reconciliation lists unclaimed prefixes created after `submission_started_at` and presents
them as manual candidates. It never adopts a candidate automatically and never submits another
initial request.

Remote objects remain after successful import. A later provenance-repair operation can therefore
rebuild a missing local receipt or manifest link without paying for generation again.

## Failure Rules

- Missing storage configuration disables paid dispatch, not read-only curation.
- Unavailable Funnel, invalid TLS, failed SigV4, failed canary, low capacity, failed backup, wrong
  bucket owner, or unhealthy Compose service blocks dispatch.
- A worker upload error after generation moves the slot and launch to `needs_reconciliation`.
- Partial uploads remain recoverable; they are never deleted to make the object count look clean.
- A checksum mismatch, unexpected key, excess object count, or local path conflict requires manual
  reconciliation.
- A storage restart during generation does not authorize another provider submission.
- Credentials rotate in four steps: add new credentials, verify them locally, update and probe the
  RunPod template, then revoke the old credentials.
- Remote retention is indefinite. Cleanup needs its own approved design and complete backup.

## Operations

The CLI gains a `clawmarks storage` command group:

- `storage paths` prints resolved XDG paths without changing them.
- `storage init` creates durable host directories and validates required environment names.
- `storage compose-config` validates the rendered Compose configuration without starting services.
- `storage bootstrap` creates IAM accounts and current/next buckets idempotently.
- `storage verify` performs health, public canary, permissions, capacity, and prefix-list checks.
- `storage backup` takes and verifies a complete mirror.
- `storage status` reports Compose health, Funnel URL, bucket readiness, free space, and last backup.

Commands that write the live store take the object-store backup lock. Commands never print secrets.

## Verification

Automated tests cover:

- XDG path resolution and explicit overrides;
- Compose rendering without host-specific paths or unpinned images;
- bucket month-boundary calculation;
- IAM bootstrap idempotency and worker delete denial;
- public-canary verification and free-space failures;
- complete object-store backup and content verification;
- known-job recovery after simulated RunPod result expiry;
- partial upload, wrong count, checksum mismatch, duplicate key, and no-clobber conflicts;
- manual candidate reporting for an ambiguous initial submission;
- result receipt durability before manifest and trial updates;
- absence of any automatic S3 delete or repeat `/run` path.

Integration verification uses a disposable VersityGW root and the exact worker upload helper. It
uploads, lists, downloads, and compares a PNG through the user-facing Funnel URL.

The final live check requires explicit user approval because it changes RunPod endpoint environment
and incurs a bounded generation charge. It generates one image, ignores the transient RunPod output,
recovers the image from S3 by provider job ID, imports it through the no-clobber path, and verifies
the final receipt. The test keeps both the remote and local image.

## Delivery Estimate

The implementation should take three to five focused engineering hours:

- 45 to 75 minutes for the Compose stack, XDG paths, and bootstrap;
- 60 to 90 minutes for storage preflight, backup, and compatibility checks;
- 60 to 90 minutes for paid-result import and reconciliation;
- 45 to 75 minutes for automated and live verification.

If the pinned upstream worker requires the defined path-style derived image, allow up to one extra
hour.
