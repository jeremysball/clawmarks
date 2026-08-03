# OpenCode Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent, Focus-scoped research Guide that runs OpenCode in a tool-denied process and can only propose reviewable Focus text edits.

**Architecture:** Keep Guide storage and process control in `guide.py`; HTTP handlers only validate scope and serialize responses. Every user turn becomes a durable request record before a detached `guide_worker` starts, and that worker persists completion without relying on server memory. The shared browser asset renders one accessible desktop drawer/mobile sheet on every page and polls persisted request state.

**Tech Stack:** Python 3.10+, OpenCode CLI 1.17.18, subprocess JSONL, POSIX process identity, server-rendered HTML/JavaScript, pytest, Playwright MCP.

## Global Constraints

- Initial provider support is `openai/*` only and passes only `OPENAI_API_KEY`.
- Require `CLAWMARKS_GUIDE_MODEL` and `CLAWMARKS_GUIDE_INPUT_MODE=metadata|images`; missing config disables only Guide.
- Run OpenCode with `--pure --format json --agent guide --model <configured-model>` from a fresh empty directory.
- Global and agent permission trees contain only `deny` values, including `{"*":"deny"}`. Sharing, snapshots, plugins, MCP, autoupdate, Claude Code compatibility, external skill discovery, LSP downloads, and default plugins are disabled.
- Never pass `RUNPOD_API_KEY`, `CIVITAI_TOKEN`, the repository, arbitrary browser paths, raw embeddings, or unrelated state.
- Persist the user message before process start and the assistant message before reporting completion.
- Metadata responses display: “This response used metadata, not image pixels.”
- Guide never applies a proposal or launches paid work.
- Run Python and tests through `uv run` only.

## Dependencies

- Complete the shared shell, Focus persistence, and research-workspace navigation plans first.
- Consume `Scope`, `FocusStore`, `record_locks()`, `utc_now()`, and `new_id()` from those plans.

## File Structure

- Create `src/clawmarks/guide.py`: config, model capability parsing, stores, context, subprocess, and recovery.
- Create `src/clawmarks/guide_worker.py`: detached request worker entry point.
- Modify `src/clawmarks/curation_server.py`: Guide routes and startup reconciliation.
- Modify `src/clawmarks/shared_ui.py`: drawer/sheet markup, CSS, and Guide browser code.
- Modify `Dockerfile`, `docker-compose.yml`, and `.env.example`: pinned CLI and required config.
- Create `tests/test_guide.py`: unit and confinement tests.
- Create `tests/test_curation_server_guide_routes.py`: HTTP lifecycle tests.
- Modify `tests/test_shared_ui.py`: accessible presentation.

### Task 1: Build And Prove The Restricted OpenCode Profile

**Files:**
- Create: `src/clawmarks/guide.py`
- Create: `tests/test_guide.py`

**Interfaces:**
- Produces: `GuideConfig.from_environ(environ: Mapping[str, str], state_dir: Path) -> GuideConfig`.
- Produces: `GuideDisabled(reason: str)`.
- Produces: `build_opencode_environment(config: GuideConfig, base_environ: Mapping[str, str]) -> dict[str, str]`.
- Produces: `opencode_command(config: GuideConfig, session_id: str | None, attachments: Sequence[Path]) -> list[str]`.
- Produces: `assert_no_managed_opencode_config(path: Path = Path("/etc/opencode")) -> None`.
- Produces: `verify_resolved_profile(config: GuideConfig, run_fn=subprocess.run) -> None`.

- [ ] **Step 1: Write failing confinement tests**

```python
def test_guide_environment_contains_only_allowlisted_secret(tmp_path):
    env = build_opencode_environment(
        GuideConfig("openai/gpt-5.5", "metadata", tmp_path, timeout_s=120),
        {
            "PATH": "/bin", "OPENAI_API_KEY": "openai-secret",
            "RUNPOD_API_KEY": "runpod-secret", "CIVITAI_TOKEN": "civitai-secret",
        },
    )
    assert env["OPENAI_API_KEY"] == "openai-secret"
    assert "RUNPOD_API_KEY" not in env
    assert "CIVITAI_TOKEN" not in env
    inline = json.loads(env["OPENCODE_CONFIG_CONTENT"])
    assert inline["permission"] == {"*": "deny"}
    assert inline["agent"]["guide"]["permission"] == {"*": "deny"}
    assert inline["enabled_providers"] == ["openai"]
    assert inline["share"] == "disabled"
    assert env["OPENCODE_DISABLE_EXTERNAL_SKILLS"] == "1"


def test_opencode_command_never_auto_approves(tmp_path):
    command = opencode_command(
        GuideConfig("openai/gpt-5.5", "metadata", tmp_path, 120), None, []
    )
    assert command[:3] == ["opencode", "run", "--pure"]
    assert "--format" in command and "json" in command
    assert "--auto" not in command
    assert "--dangerously-skip-permissions" not in command
```

Also assert only `openai/*` models pass, state roots live under `state_dir / "guide_opencode"`, and attachment paths must be validated absolute files supplied by the server. A temporary managed config path, directory, or symlink must raise before `run_fn` is called. Feed `verify_resolved_profile()` resolved fixtures containing `{"*":"deny","bash":"allow"}`, `{"*":"deny","read":"ask"}`, a non-empty MCP map, a plugin, another enabled provider, an instruction path, command, formatter, LSP, changed small model, changed Guide prompt, provider API key, or custom base URL; each must raise `GuideDisabled` before any model command. Put an unrelated `UNRELATED_CREDENTIAL_SENTINEL` in `base_environ` and assert it never reaches the subprocess.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_guide.py`

Expected: FAIL because `guide.py` does not exist.

- [ ] **Step 3: Implement exact inline configuration**

```python
inline = {
    "$schema": "https://opencode.ai/config.json",
    "model": config.model,
    "small_model": config.model,
    "autoupdate": False,
    "share": "disabled",
    "snapshot": False,
    "instructions": [],
    "plugin": [],
    "mcp": {},
    "command": {},
    "formatter": False,
    "lsp": False,
    "enabled_providers": ["openai"],
    "provider": {"openai": {"options": {"baseURL": "https://api.openai.com/v1"}}},
    "permission": {"*": "deny"},
    "agent": {
        "guide": {
            "description": "Read-only CLAWMARKS research Guide",
            "mode": "primary",
            "model": config.model,
            "prompt": GUIDE_SYSTEM_PROMPT,
            "permission": {"*": "deny"},
        }
    },
}
```

Start from an empty environment. Copy only `PATH`, `LANG`, `LC_ALL`, `SSL_CERT_FILE`, and
`SSL_CERT_DIR` when present, plus `OPENAI_API_KEY`. Set `HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`,
`XDG_STATE_HOME`, `XDG_CONFIG_HOME`, and `TMPDIR` to Guide-specific directories. Set
`OPENCODE_DISABLE_DEFAULT_PLUGINS=1`, `OPENCODE_DISABLE_CLAUDE_CODE=1`,
`OPENCODE_DISABLE_CLAUDE_CODE_PROMPT=1`, `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`,
`OPENCODE_DISABLE_EXTERNAL_SKILLS=1`, `OPENCODE_DISABLE_LSP_DOWNLOAD=1`,
`OPENCODE_DISABLE_AUTOUPDATE=1`, `OPENCODE_ENABLE_EXA=0`, and `OPENCODE_CONFIG_CONTENT`.

Run `opencode debug config --pure` with that environment and parse its JSON. Recursively inspect the
resolved global and `guide` permission values; every terminal string must equal `deny`, each tree
must contain `"*": "deny"`, and unknown value shapes fail closed. Require `share == "disabled"`,
`snapshot is False`, `plugin == []`, `mcp == {}`, `instructions == []`, `command == {}`,
`formatter is False`, `lsp is False`, and `enabled_providers == ["openai"]`. Require `model` and
`small_model` to equal `config.model`; require the resolved Guide model and prompt to equal
`config.model` and `GUIDE_SYSTEM_PROMPT`; require its options and tools empty; and require
`provider == {"openai": {"options": {"baseURL": "https://api.openai.com/v1"}}}`. Reject any
resolved provider `apiKey`, file content, or additional option. Treat malformed output or any
mismatch as `GuideDisabled`.

Call `assert_no_managed_opencode_config()` before `opencode debug config` so a managed
`{file:...}` expression cannot read during resolution. Support the Linux container only for this
initial boundary; another platform requires its managed-config locations and tests before enabling
Guide.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_guide.py`

Expected: PASS.

```bash
git add src/clawmarks/guide.py tests/test_guide.py
git commit -m "feat(guide): define confined OpenCode profile"
```

### Task 2: Detect Model Image Capability Without Inference

**Files:**
- Modify: `src/clawmarks/guide.py`
- Create: `src/clawmarks/guide_worker.py`
- Modify: `tests/test_guide.py`

**Interfaces:**
- Produces: `parse_model_capability(output: str, model: str) -> bool`.
- Produces: `probe_guide_capability(config, run_fn=subprocess.run) -> Literal["metadata", "images"]`.

- [ ] **Step 1: Write failing parser tests**

```python
def test_model_capability_requires_exact_model_and_image_true():
    output = """openai/gpt-5.5
{"capabilities":{"input":{"text":true,"image":true}}}
openai/other
{"capabilities":{"input":{"text":true,"image":false}}}
"""
    assert parse_model_capability(output, "openai/gpt-5.5") is True
    assert parse_model_capability(output, "openai/other") is False


def test_malformed_model_output_fails_closed():
    with pytest.raises(GuideDisabled, match="capability"):
        parse_model_capability("openai/gpt-5.5\nnot-json", "openai/gpt-5.5")
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_guide.py`

Expected: FAIL because capability parsing is absent.

- [ ] **Step 3: Implement non-inference probing**

Run `["opencode", "models", "openai", "--pure", "--verbose"]` with the same restricted environment and a 30-second timeout. Parse each model-name line followed by one balanced JSON object. Metadata mode does not require image capability. Image mode fails disabled if the exact block is missing, malformed, or reports false.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_guide.py`

Expected: PASS.

```bash
git add src/clawmarks/guide.py tests/test_guide.py
git commit -m "feat(guide): verify model image capability"
```

### Task 3: Persist Threads And Asynchronous Requests

**Files:**
- Modify: `src/clawmarks/guide.py`
- Modify: `tests/test_guide.py`

**Interfaces:**
- Produces: `GuideStore(state_dir: Path)`.
- Produces: `get_thread(scope, focus_id) -> dict`, `list_threads_for_focus(scope, focus_id) -> list[dict]`, `create_thread(scope, focus_id) -> dict`, `attach_thread(...) -> dict`.
- Produces: `append_user_message(thread_id, scope, text, receipt) -> dict` and `append_assistant_message(...) -> dict`.
- Produces: `create_request(scope, thread_id, message_id, capability_mode) -> dict`, `get_request(...) -> dict`, and `transition_request(...) -> dict`.

- [ ] **Step 1: Write failing storage tests**

```python
def test_user_message_is_durable_before_request_creation(store, scope):
    focus_id = "focus_11111111111111111111111111111111"
    thread = store.create_thread(scope, focus_id)
    message = store.append_user_message(thread["thread_id"], scope, "Challenge this", {"page": "map"})
    request = store.create_request(scope, thread["thread_id"], message["message_id"], "metadata")
    reloaded = store.get_thread(scope, focus_id)
    assert reloaded["messages"][-1]["message_id"] == request["message_id"]


def test_only_one_active_request_per_thread(store, scope):
    thread, message = thread_with_message(store, scope)
    store.create_request(scope, thread["thread_id"], message["message_id"], "metadata")
    with pytest.raises(GuideConflict, match="active request"):
        store.create_request(scope, thread["thread_id"], message["message_id"], "metadata")
```

Also test duplicate primary Focus threads as integrity errors, same-scope attach, revision conflict, retry without duplicate user message, and malformed file preservation.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_guide.py`

Expected: FAIL on missing store methods.

- [ ] **Step 3: Implement stores under record locks**

Use `guide_<uuid>`, `message_<uuid>`, and `guide_request_<uuid>`. Store paths exactly as specified. Attach acquires sorted thread and Focus locks. Request transitions accept only:

```python
ALLOWED_REQUEST_TRANSITIONS = {
    "queued": {"running", "failed", "interrupted"},
    "running": {"completed", "failed", "interrupted"},
    "completed": set(), "failed": set(), "interrupted": set(),
}
```

Retry creates another queued request and writes `retried_by_request_id` to the original without appending another user message.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_guide.py`

Expected: PASS.

```bash
git add src/clawmarks/guide.py tests/test_guide.py
git commit -m "feat(guide): persist threads and requests"
```

### Task 4: Build Authoritative Context And Bounded Attachments

**Files:**
- Modify: `src/clawmarks/guide.py`
- Modify: `tests/test_guide.py`

**Interfaces:**
- Produces: `build_context_receipt(scope, page, focus, local_selection, manifest, judgments, derived) -> dict`.
- Produces: `select_attachments(scope, focus, manifest, real_dir, mode) -> list[Path]`.
- Produces: `build_turn_prompt(receipt, user_text, mode) -> str`.

- [ ] **Step 1: Write failing context security tests**

```python
def test_context_ignores_browser_paths_and_resolves_focus_tags(tmp_path):
    receipt = build_context_receipt(
        scope, "redundancy", focus,
        {"threshold": 0.74, "paths": ["/etc/passwd"]},
        manifest, judgments={}, derived={"cluster_count": 6},
    )
    assert "paths" not in receipt["local_selection"]
    assert "/etc/passwd" not in json.dumps(receipt)


def test_image_mode_caps_six_generated_and_two_real(store_fixture):
    attachments = select_attachments(scope, focus, manifest, real_dir, "images")
    assert len([p for p in attachments if p.parent == scope_dir]) <= 6
    assert len([p for p in attachments if p.parent == real_dir]) <= 2
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_guide.py`

Expected: FAIL on missing context functions.

- [ ] **Step 3: Implement an allowlisted context schema**

Allow local-selection keys per page in one constant. Resolve all evidence from Focus tags and the scoped manifest. Choose generated attachments in stored Focus order, then contradictory examples named by validated local state, capped at six; choose anchors in stored order, capped at two. Metadata mode returns no files and injects the exact disclaimer into both prompt and receipt.

The system prompt requires one top-level JSON object:

```json
{"text":"plain-language response","proposal":null}
```

or a valid `focus_text_patch`. It forbids visual claims in metadata mode and asks for image-tag citations in image mode.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_guide.py`

Expected: PASS.

```bash
git add src/clawmarks/guide.py tests/test_guide.py
git commit -m "feat(guide): build bounded evidence context"
```

### Task 5: Run OpenCode And Parse Its JSONL Safely

**Files:**
- Modify: `src/clawmarks/guide.py`
- Modify: `tests/test_guide.py`

**Interfaces:**
- Produces: `parse_opencode_events(stdout: str) -> {"session_id": str, "text": str}`.
- Produces: `parse_guide_response(text: str, focus: dict) -> {"text": str, "proposal": dict | None, "protocol_warning": str | None}`.
- Produces: `start_guide_worker(config, request_id, scope, popen_fn=subprocess.Popen) -> int`.
- Produces: `run_guide_request(config, store, request_id, scope, context_builder, popen_fn=subprocess.Popen) -> None`, called by `guide_worker`.
- Produces: `reconcile_interrupted_requests(store) -> int`.

- [ ] **Step 1: Write failing subprocess tests**

```python
def test_jsonl_parser_collects_text_and_session():
    output = "\n".join([
        json.dumps({"type": "step_start", "sessionID": "ses_1"}),
        json.dumps({"type": "text", "sessionID": "ses_1", "part": {"type": "text", "text": "{\"text\":\"Hi\","}}),
        json.dumps({"type": "text", "sessionID": "ses_1", "part": {"type": "text", "text": "\"proposal\":null}"}}),
    ])
    assert parse_opencode_events(output) == {
        "session_id": "ses_1", "text": '{"text":"Hi","proposal":null}'
    }


def test_invalid_proposal_is_saved_as_prose_only(focus):
    result = parse_guide_response(
        '{"text":"Idea","proposal":{"kind":"focus_text_patch","changes":{"source":{}}}}',
        focus,
    )
    assert result["text"] == "Idea"
    assert result["proposal"] is None
    assert result["protocol_warning"]
```

Add timeout, nonzero exit, bounded 8 KiB stderr, missing text event, session resume, PID reuse, assistant-persisted-before-completion, detached worker argv, and server-restart reconciliation tests.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_guide.py`

Expected: FAIL on missing runner methods.

- [ ] **Step 3: Implement process lifecycle**

`start_guide_worker()` launches `[sys.executable, "-m", "clawmarks.guide_worker", "--expedition", scope.expedition, "--leg", scope.leg, "--request-id", request_id]` with `start_new_session=True` and stdio set to `DEVNULL`. The worker transitions queued to running and writes its own PID and `/proc/<pid>/stat` start-time ticks before invoking OpenCode.

Inside the worker, create a fresh empty `TemporaryDirectory` under the Guide TMPDIR for each turn. Start OpenCode with text pipes, the restricted environment, and the prompt as the final positional argument. On timeout, terminate the OpenCode process group, wait five seconds, kill if needed, and mark failed. Persist completion directly through `GuideStore`; do not send the result through the HTTP server process.

Immediately before each model process, rerun `assert_no_managed_opencode_config()` and
`verify_resolved_profile()` in the worker. Disable that request if either check changed since server
startup.

Concatenate only top-level OpenCode events with `type == "text"` and `part.type == "text"`. Persist the first consistent `sessionID`. Validate proposals against the current Focus ID, expected revision, and the allowed keys `question`, `observation`, `hypothesis_text`, and `test_contract`.

After parsing the top-level object, cap its visible `text` at 32,000 Unicode code points and record
a protocol warning when truncation occurs. Persist only the final 8 KiB of stderr. Never truncate
the JSONL before parsing, because that can turn a valid response into fabricated prose.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_guide.py`

Expected: PASS.

```bash
git add src/clawmarks/guide.py src/clawmarks/guide_worker.py tests/test_guide.py
git commit -m "feat(guide): execute persisted OpenCode turns"
```

### Task 6: Expose Guide APIs

**Files:**
- Modify: `src/clawmarks/curation_server.py`
- Modify: `src/clawmarks/build/explore_hub.py`
- Create: `tests/test_curation_server_guide_routes.py`
- Modify: `tests/test_explore_hub.py`

**Interfaces:**
- Produces the five Guide endpoints in the specification.
- Returns HTTP 202 for accepted messages/retries, 404 for absent read-only thread/request, 409 for active-request/attach/revision conflicts, and 503 when Guide is disabled.

- [ ] **Step 1: Write failing lifecycle route tests**

```python
def test_message_post_persists_and_returns_pollable_request(server, focus, monkeypatch):
    monkeypatch.setattr(guide, "start_guide_worker", lambda *args, **kwargs: 1234)
    status, accepted = post_json(server, "/api/guide/messages", {
        "scope": {"expedition": "demo", "leg": "round1"},
        "focus_id": focus["focus_id"], "page": "map",
        "local_selection": {"member_tags": ["a"]}, "text": "Challenge this.",
    })
    assert status == 202
    status, request = get_json(
        server,
        f"/api/guide/requests/{accepted['request_id']}?expedition=demo&leg=round1",
    )
    assert status == 200 and request["status"] == "queued"
```

Add thread 404, one-active-request conflict, attach conflict, retry eligibility, and disabled configuration cases.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_curation_server_guide_routes.py`

Expected: FAIL with unknown endpoints.

- [ ] **Step 3: Add handlers and startup recovery**

Resolve scope and Focus through explicit payload/query values, never global selection. Start one detached worker only after queued state is durable. On server startup, call `reconcile_interrupted_requests()`: leave a matching live worker running, and mark queued or running requests with no matching worker interrupted. Return saved assistant messages only after completion state is durable. Reject user text over 8,000 code points or context over 64 KiB with HTTP 413 before creating the request. Pass `GuideStore.list_threads_for_focus()` into Explore's existing `guide_threads` aggregation input so Guide messages appear in the Focus activity ledger.

- [ ] **Step 4: Run focused tests and commit**

Run: `uv run pytest -q tests/test_curation_server_guide_routes.py tests/test_guide.py tests/test_curation_server_startup.py`

Expected: PASS.

```bash
git add src/clawmarks/curation_server.py src/clawmarks/build/explore_hub.py tests/test_curation_server_guide_routes.py tests/test_curation_server_startup.py tests/test_explore_hub.py
git commit -m "feat(guide): expose asynchronous Guide APIs"
```

### Task 7: Add The Shared Drawer And Mobile Sheet

**Files:**
- Modify: `src/clawmarks/shared_ui.py`
- Modify: `tests/test_shared_ui.py`

**Interfaces:**
- Produces: one `#guideDrawer` dialog in `nav_bar_html()`.
- Produces: `GUIDE_JS` served through `/guide.js`.
- Consumes: current page and explicit URL context; sends only allowlisted local UI state.

- [ ] **Step 1: Write failing semantic UI tests**

```python
def test_guide_dialog_has_accessible_controls_and_live_state():
    markup = nav_bar_html("map.html", "demo", "round1", focus=FOCUS)
    assert 'id="guideDrawer"' in markup
    assert 'role="dialog"' in markup
    assert 'aria-modal="true"' in markup
    assert 'aria-live="polite"' in markup
    assert '>Send<' in markup
    assert 'aria-label="Close Guide"' in markup
    assert 'data-capability-mode' in markup
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest -q tests/test_shared_ui.py`

Expected: FAIL because the header only has a Guide trigger.

- [ ] **Step 3: Implement drawer state and polling**

Use native dialog semantics or equivalent focus trap, set the source document inert while open, restore focus to `#guideOpen`, and close on Escape. Keep the dialog mounted when hidden so history and scroll position remain. Poll active requests with capped backoff from 500ms to 3s; dismissal does not cancel.

Render messages as ruled rows, not bubbles. Show the context receipt, fixed metadata disclaimer, working text, bounded failure text, Retry, and proposal old/new diff. Apply calls the ordinary Focus PATCH endpoint with `expected_revision`; Dismiss only hides the proposal.

At 700px and below, position it as a pull-up sheet with a drag handle, available-height cap, sticky composer above the software keyboard, and 44px controls.

- [ ] **Step 4: Run tests and commit**

Run: `uv run pytest -q tests/test_shared_ui.py tests/test_curation_server_static_assets.py`

Expected: PASS.

```bash
git add src/clawmarks/shared_ui.py src/clawmarks/curation_server.py tests/test_shared_ui.py tests/test_curation_server_static_assets.py
git commit -m "feat(guide): add accessible shared Guide surface"
```

### Task 8: Pin Runtime Configuration And Verify Live Behavior

**Files:**
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `src/clawmarks/guide.py`
- Modify: `src/clawmarks/guide_worker.py`
- Modify: `src/clawmarks/curation_server.py`
- Modify: `src/clawmarks/shared_ui.py`
- Modify: `tests/test_guide.py`
- Create: `tests/test_guide_opencode_integration.py`
- Modify: `tests/test_curation_server_guide_routes.py`
- Modify: `tests/test_shared_ui.py`

**Interfaces:**
- Produces: OpenCode 1.17.18 in the image.
- Produces: documented `CLAWMARKS_GUIDE_MODEL`, `CLAWMARKS_GUIDE_INPUT_MODE`, and `CLAWMARKS_GUIDE_TIMEOUT_S` environment values.
- Produces: `uv run python -m clawmarks.guide --verify-config`, which checks confinement without model inference.

- [ ] **Step 1: Pin the Docker install**

Change the install pipeline to:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://opencode.ai/install | VERSION=1.17.18 bash && \
    mv "$HOME/.opencode/bin/opencode" /usr/local/bin/opencode && \
    test "$(opencode --version)" = "1.17.18"
```

Add the three Guide variables to compose and `.env.example`. Do not add a real key or default model that silently incurs spend.

After the existing `COPY` and `uv sync`, add this Docker build check:

```dockerfile
RUN CLAWMARKS_STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/clawmarks-guide-check" \
    CLAWMARKS_GUIDE_MODEL=openai/gpt-5.5 \
    CLAWMARKS_GUIDE_INPUT_MODE=metadata \
    OPENAI_API_KEY=build-check-not-a-real-key \
    uv run python -m clawmarks.guide --verify-config
```

- [ ] **Step 2: Run all local tests**

Run: `uv run pytest -q && uv run ruff check src tests && uv run mypy src && git diff --check`

Expected: PASS. Docker build verification remains CI's `verify` job if Docker is unavailable locally.

- [ ] **Step 3: Verify with Playwright MCP**

Start the live server against disposable state. Test desktop and 390px mobile: open, dismiss during a mocked in-flight request, reopen, resume on another page, retry a failure, inspect metadata disclaimer, apply a revision-current proposal, reject a stale proposal, close with Escape, and verify focus restoration. Check console errors and overflow.

- [ ] **Step 4: Run a confinement smoke fixture**

With a fake OpenCode executable on `PATH`, record argv, cwd, and environment. Assert cwd is empty, no secret except fake `OPENAI_API_KEY` appears, `OPENCODE_DISABLE_EXTERNAL_SKILLS=1`, every resolved global and Guide permission terminal is `deny`, MCP, plugins, instructions, and commands are empty, the provider base URL is exact, and attachments are only validated fixture images. Put sentinel skills under the fake project, `.opencode`, `.claude`, and `.agents` roots and assert none appears in the resolved profile or model prompt.

Add `tests/test_guide_opencode_integration.py`, skipped only when `opencode` is absent, that calls
`verify_resolved_profile()` against the real installed CLI with a temporary XDG tree. In the
Dockerfile, after `COPY` and `uv sync`, run the same verifier with a dummy OpenAI key and metadata
mode. This must execute `opencode debug config --pure` only; it must not send a model request.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .env.example src/clawmarks/guide.py src/clawmarks/guide_worker.py src/clawmarks/curation_server.py src/clawmarks/shared_ui.py tests/test_guide.py tests/test_guide_opencode_integration.py tests/test_curation_server_guide_routes.py tests/test_shared_ui.py tests/test_curation_server_static_assets.py tests/test_curation_server_startup.py
git commit -m "build(guide): pin confined OpenCode runtime"
```
