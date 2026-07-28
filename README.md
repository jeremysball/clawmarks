# CLAWMARKS

CLAWMARKS trains an SDXL LoRA on a personal art style and ships a curation
server for reviewing generated images against the training set. The
methodology (dataset construction, hyperparameter search, evaluation) lives
in [`notes/lab_notebook.md`](notes/lab_notebook.md); this file only covers
running the code.

`CLAUDE.md` at the repo root is written for an AI coding assistant, not for
you. Skip it unless you're pairing with one.

## Run the curation server (local, no Docker)

Requires [uv](https://docs.astral.sh/uv/) and Python >= 3.10 (uv provisions
its own 3.12 automatically).

```bash
uv sync --extra dev
CLAWMARKS_HOST=127.0.0.1 uv run python -m clawmarks.curation_server 8420
```

Then open `http://127.0.0.1:8420/`. Without `CLAWMARKS_HOST` set, the server
tries your Tailscale IP first and **falls back to `0.0.0.0`** if Tailscale
isn't running — that exposes the unauthenticated server on every interface
the host has, not just tailnet-only. Set `CLAWMARKS_HOST=127.0.0.1` for a
plain local run to avoid that.

The `clawmarks` CLI (`uv run clawmarks --help`) also has a `serve`
subcommand, but it doesn't accept a port argument (`clawmarks serve 8420`
errors with `unrecognized arguments`). Use the module invocation above if
you need a port other than the 8420 default.

Run the test suite with `uv run pytest -q` (656 tests, ~2.5 minutes). Lint
and typecheck with `uv run ruff check src tests` and `uv run mypy src`.

## Run the full stack (Docker + Tailscale)

`docker-compose.yml` runs the published image
(`ghcr.io/jeremysball/clawmarks-lora:latest`) behind a Tailscale sidecar, with
RunPod/Civitai/OpenAI API keys for the generation and curation workflow.
Copy [`.env.example`](.env.example) to `.env`, fill in the keys it lists, then:

```bash
docker compose up -d
```
