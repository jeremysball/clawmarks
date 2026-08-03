# OpenCode Guide Design

## Goal

Provide a dismissible research conversation on every curation page. The Guide helps the researcher
interpret evidence, challenge explanations, structure trials, and debrief results while leaving
all evidence changes, paid actions, and conclusions under human control.

## Role

The Guide may:

- explain the current page in plain language;
- summarize Focus evidence;
- propose competing interpretations;
- challenge a hypothesis with contradictory evidence;
- draft a six-part test contract;
- compare completed results with a frozen expectation;
- propose a Focus text edit for human review.

The Guide may not:

- select or change Focus members;
- alter source evidence or human judgments;
- update a Focus without a separate reviewed UI action;
- launch, stop, or retry paid work;
- decide that a hypothesis won;
- claim visual interpretation when it received metadata only.

## Presentation

Every shared header contains a Guide button. It opens:

- a right-side drawer or overlay on desktop, preserving enough width to inspect the source page;
- a pull-up sheet on mobile, with a visible drag handle and close control.

Closing the Guide hides the surface but preserves its thread, current response, and scroll position.
Reopening it on another page resumes the same Focus-scoped conversation and sends fresh page
context with the next message.

The drawer contains:

- a context receipt naming page, expedition, leg, Focus, Focus revision, and local selection;
- the persisted message history;
- clear speaker labels;
- a composer and send button;
- a working state that survives dismissal;
- readable retry text after a failed request;
- a metadata-only or image-grounded capability label;
- reviewed proposal controls when a response includes a Focus edit.

The Guide must never become a permanent page column. Maps, comparisons, and evidence views retain
their full width when the Guide is closed.

## Thread Scope and Storage

A Focus has one primary Guide thread. Pages without a Focus use one temporary leg-scoped thread and
offer Attach to Focus after the researcher creates a Focus.

Thread records live at:

```text
$CLAWMARKS_STATE_DIR/guide_threads/<expedition>/<leg>/<thread-id>.json
```

Each record contains:

```json
{
  "schema_version": 1,
  "thread_id": "guide_<uuid>",
  "scope": {"expedition": "...", "leg": "..."},
  "focus_id": "focus_<uuid>",
  "opencode_session_id": "...",
  "messages": [
    {
      "message_id": "message_<uuid>",
      "role": "user",
      "text": "...",
      "context_receipt": {},
      "created_at": "..."
    }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

Assistant messages add `capability_mode`, the authoritative context receipt, and an optional
validated `proposal`. OpenCode must return one JSON object with exactly `text` and `proposal` at the
top level. `text` is the visible assistant response; `proposal` is `null` or the structured Focus
proposal below. The server concatenates the final turn's OpenCode `text` events, parses the complete
string as JSON, and validates both fields. If parsing or proposal validation fails, it saves the raw
text as prose, saves `proposal: null`, and records a bounded protocol warning. When the top-level
object and `text` are valid but only the proposal is invalid, it saves the validated `text`, drops
the proposal, and records the warning. It never guesses a patch from prose.

`focus_id` is `null` only for an unattached temporary leg-scoped thread. Attaching a thread writes
the Focus ID and an `attached_at` timestamp under both the thread-record and Focus-record locks. The
server finds a primary Focus thread by scanning the scoped thread directory; duplicate matches are
an integrity error and remain untouched for recovery.

Writes use the same file `fsync`, atomic replace, and parent-directory `fsync` pattern as Focus
records. The server persists the user message before starting OpenCode and persists the assistant
message before reporting completion to the browser. A failed or interrupted response remains
visible as request state, not a fabricated assistant message.

## Context Receipt

The browser sends IDs and local UI state. The server resolves authoritative records and builds the
model context. A receipt contains:

```json
{
  "page": "redundancy",
  "scope": {"expedition": "trent_v3_epoch4", "leg": "freeform1"},
  "focus": {"focus_id": "focus_<uuid>", "revision": 3},
  "local_selection": {"threshold": 0.74, "cluster_ids": [1, 4]},
  "evidence": {
    "member_count": 18,
    "missing_member_count": 0,
    "real_anchor_count": 1,
    "summary": "six effective clusters at threshold 0.74"
  },
  "visual_input": {
    "mode": "images",
    "generated_count": 6,
    "real_anchor_count": 1
  }
}
```

Each turn includes fresh context. The OpenCode session supplies conversational continuity; it does
not replace the current receipt.

The server limits context to the active Focus and local selection. It does not send secrets, API
keys, raw embedding tensors, unrelated state directories, or arbitrary browser-supplied paths.

## Visual Grounding

The Guide has two honest capability modes:

- **Metadata context only:** receives tags, prompts, scalar scores, comparisons, and summaries. It
  may reason about those records but must not say it inspected image content.
- **Image grounded:** receives representative Focus members, contradictory examples, and real-art
  anchors as actual image inputs to a model that supports images.

Image-grounded requests use a bounded sample, initially at most six generated images and two real
anchors. The server selects paths from validated Focus tags. The browser cannot submit arbitrary
filesystem paths.

If the configured OpenCode model cannot accept images, the server uses metadata mode and labels it
in the prompt, persisted message receipt, and UI. Every metadata-only response displays a fixed
system-controlled disclaimer: "This response used metadata, not image pixels." Guide prose never
updates a Focus automatically, so an unreliable semantic classifier is not required to decide
whether the model sounded visual.

An image-grounded structured proposal cites the image tags that support each visual claim. The
server verifies that every citation was an attached image in that request. Metadata-only proposals
may cite scores, prompts, comparisons, and summaries, but cannot carry image citations.

## OpenCode Process Boundary

The server invokes OpenCode with `--pure --agent <guide-agent>` from a fresh empty temporary
directory. The dedicated agent denies every tool that could discover or change state, including
`read`, `glob`, `grep`, `list`, `edit`, `bash`, `task`, `skill`, web tools, and every
mutation-capable MCP tool. It receives validated images only through explicit `--file` attachments.
The subprocess environment removes `RUNPOD_API_KEY`, `CIVITAI_TOKEN`, and unrelated credentials.
The current `--dangerously-skip-permissions` Autopilot invocation is not an acceptable Guide
boundary.

The server starts a new OpenCode session for the first message and stores the returned session ID.
Later messages resume that session and prepend the fresh context receipt. Pure mode, the empty
working directory, denied discovery tools, a minimal environment, and explicit attachments confine
the process to the prompt and validated images required for that turn.

The implementation must prove the restricted profile in a test or integration fixture before the
Guide ships. If the installed OpenCode version cannot enforce the restriction, the Guide remains
disabled and reports the missing safety capability.

The supported deployment is the Linux container. Before starting either the verifier or a model
process, the server requires `/etc/opencode` to be absent; an administrator-managed config can use
`{file:...}` substitution while OpenCode resolves it, before post-resolution checks could stop the
read. A present file, directory, or symlink disables Guide without invoking OpenCode. The worker
repeats this check and resolved-profile verification for every turn, so a configuration introduced
after server startup cannot bypass the boundary.

At startup the server runs `opencode debug config --pure` under the restricted environment and
verifies that the resolved global and `guide` permission trees contain only `deny` terminal values,
including the `*` entries. A specific `allow` or `ask` override fails even when `*` remains `deny`.
The verifier also requires sharing and snapshots disabled, no plugin, an empty MCP map, and exactly
the `openai` provider allowlist. It requires `instructions` and commands empty, formatter and LSP
false, main and small model equal to the configured model, the Guide prompt and model equal to the
server's constants, and the only provider option to be OpenAI's exact
`https://api.openai.com/v1` base URL. Any resolved file substitution, custom provider endpoint,
agent override, or executable extension therefore fails closed. This catches a higher-precedence
remote or managed configuration that would weaken the inline profile. A malformed or mismatched
value disables Guide before any model request.

The server supplies the Guide agent through `OPENCODE_CONFIG_CONTENT`, not project or user config.
That inline configuration sets `share: "disabled"`, `snapshot: false`, an explicit model from the
required `CLAWMARKS_GUIDE_MODEL` environment variable, and one primary `guide` agent with every tool
and permission denied. The subprocess also sets `OPENCODE_DISABLE_DEFAULT_PLUGINS=1`,
`OPENCODE_DISABLE_CLAUDE_CODE=1`, `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT=1`,
`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`, `OPENCODE_DISABLE_EXTERNAL_SKILLS=1`,
`OPENCODE_DISABLE_LSP_DOWNLOAD=1`, and Guide-specific XDG data, cache, state, and config roots under
`$CLAWMARKS_STATE_DIR/guide_opencode/`. The external-skills flag prevents automatic discovery from
project, `.opencode`, `.claude`, and `.agents` skill directories even though the `skill` tool itself
is already denied. The initial version
accepts only `openai/*` models and builds the subprocess environment from an empty mapping. It adds
only fixed Guide XDG paths and disable flags, `PATH`, locale and TLS-certificate variables from a
non-secret allowlist, and `OPENAI_API_KEY` from the server's credential environment. The inline
config also sets `autoupdate: false`, `plugin: []`, `mcp: {}`,
`enabled_providers: ["openai"]`, global `permission: {"*": "deny"}`, and the same wildcard denial
on the `guide` agent. It sets `small_model` to the configured model, `instructions: []`,
`command: {}`, `formatter: false`, `lsp: false`, and the fixed OpenAI base URL. Adding another
provider requires an explicit credential allowlist and a new
confinement test. It runs:

```text
opencode run --pure --format json --agent guide --model <configured-model>
```

Later turns add `--session <persisted-session-id>`. Image-grounded turns append validated `--file`
arguments. `CLAWMARKS_GUIDE_INPUT_MODE` is required and accepts `metadata` or `images`. At startup,
the server runs `opencode models openai --pure --verbose`, finds the exact configured model block,
and requires `capabilities.input.image: true` before enabling `images`. A missing model block,
malformed capability output, or false image flag disables image mode and reports the reason instead
of making a paid inference probe or silently claiming visual access. Missing model or input-mode
configuration disables the Guide without affecting the rest of the curation server.

## Asynchronous Request API

OpenCode responses may outlive one HTTP request. The Guide uses background request records:

```text
$CLAWMARKS_STATE_DIR/guide_requests/<expedition>/<leg>/<request-id>.json
```

```json
{
  "schema_version": 1,
  "request_id": "guide_request_<uuid>",
  "thread_id": "guide_<uuid>",
  "message_id": "message_<uuid>",
  "status": "queued",
  "process": {"pid": null, "start_time_ticks": null},
  "capability_mode": "metadata",
  "started_at": null,
  "completed_at": null,
  "failure": null
}
```

Request status transitions use a cross-process request-record lock and durable atomic writes.
`process.start_time_ticks` uses the Linux `/proc/<pid>/stat` identity check already established by
`search/run_manager.py`; a reused PID never counts as the original Guide process.

```text
GET  /api/guide/thread?expedition=<name>&leg=<name>&focus_id=<id>
POST /api/guide/messages
GET  /api/guide/requests/<request-id>?expedition=<name>&leg=<name>
POST /api/guide/requests/<request-id>/retry
POST /api/guide/threads/<thread-id>/attach
```

`POST /api/guide/messages` validates the scope and Focus, persists the user message, starts one
background OpenCode process, and returns HTTP 202 with a request ID. One thread may have only one
active request. `GET /api/guide/thread` is read-only and returns HTTP 404 when no matching thread
exists; the first message POST creates it under the thread lock.

The HTTP server actually starts a detached `clawmarks.guide_worker` process with the scoped request
ID. That worker writes its own PID and process-start ticks, invokes OpenCode, and persists the
assistant message and terminal request state itself. The server does not own an in-memory pipe or
daemon thread required to finish the request. After a server restart, a live matching worker can
still complete; a queued or running request without that live worker identity becomes `interrupted`.

`GET /api/guide/requests/<request-id>` returns `queued`, `running`, `completed`, `failed`, or
`interrupted`. Completion includes the saved assistant message. Closing the drawer does not cancel
the request. After a server restart, any process without a live identity becomes `interrupted` and
the UI offers Retry from the saved user message.

The server enforces a timeout, captures bounded stderr for diagnosis, and never returns raw secrets
or an unrestricted stack trace to the browser.

User message text is limited to 8,000 Unicode code points, serialized context to 64 KiB, assistant
text to 32,000 code points, and persisted stderr to its final 8 KiB. Oversized input returns HTTP
413 before a request record or model call.

Attach requires explicit expedition, leg, Focus ID, and `expected_focus_revision`. The server
accepts only an unattached temporary thread from the same scope. If the thread was already attached,
the Focus changed, or that Focus already has a primary thread, it returns HTTP 409 and preserves
both records. It never merges histories implicitly.

## Reviewed Focus Proposals

A Guide response may include one optional structured proposal:

```json
{
  "kind": "focus_text_patch",
  "focus_id": "focus_<uuid>",
  "expected_revision": 3,
  "changes": {
    "hypothesis_text": "...",
    "test_contract": {}
  },
  "reason": "..."
}
```

The server validates the shape but does not apply it. The only valid `changes` keys are `question`,
`observation`, `hypothesis_text`, and `test_contract`. The UI displays old and proposed values and
offers Apply or Dismiss. Apply calls the normal revision-checked Focus PATCH endpoint. Membership,
anchors, score ranges, human judgments, trial payloads, and paid actions are never valid proposal
fields.

## Failure Behavior

- OpenCode unavailable: preserve the message and show Retry.
- Timeout: mark the request failed and preserve bounded diagnostics.
- Drawer closed: continue the request and restore its state on reopen.
- Scope changed mid-request: save the response to its original thread and label the old scope when
  shown later.
- Focus revision changed mid-request: keep the response, mark its receipt stale, and require a
  fresh proposal before Apply.
- Invalid structured output: show the prose response without proposal controls.
- Image attachment missing: fall back to metadata only and state the change before dispatch.

Retry requires the original request scope, accepts only `failed` or `interrupted`, reuses its saved
user message and context source IDs, creates a new request record, and does not append a duplicate
user message. The new turn rebuilds authoritative context so its receipt can differ from the failed
attempt. The original request remains unchanged and links to `retried_by_request_id`.

## Accessibility and Mobile

- Focus moves into the drawer when it opens and returns to the Guide trigger when it closes.
- Escape closes the desktop drawer. The close button remains visible and labeled.
- The drawer traps keyboard focus while open; the source page becomes inert.
- New messages use a polite live region. The working indicator has text, not animation alone.
- The mobile composer remains visible above the software keyboard.
- Drawer and sheet buttons, inputs, and icon controls provide at least a 44px by 44px touch target.
  The send action has a text label.

## Acceptance Criteria

- Every tool page opens the same Focus-scoped thread from the shared header.
- Closing and reopening the Guide preserves the thread and in-flight request.
- Every turn stores and displays an explicit context receipt.
- Every response stores and displays its system-controlled metadata-only or image-grounded mode;
  metadata-only prose cannot enter a Focus without a reviewed Apply action.
- Image-grounded requests use validated bounded image attachments and a capable model.
- OpenCode runs in pure mode from an empty directory with discovery, mutation, delegation, web, and
  MCP tools denied.
- The Guide cannot alter evidence or start paid work.
- Focus text proposals require a visible diff and explicit revision-checked Apply action.
- Desktop and 390px mobile layouts remain usable with keyboard, touch, and screen reader controls.
