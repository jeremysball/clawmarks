# CLAWMARKS

CLAWMARKS trains an SDXL LoRA on a personal art style and ships a curation
server for reviewing generated images against the training set. The
methodology (dataset construction, hyperparameter search, evaluation) lives
in [`notes/lab_notebook.md`](notes/lab_notebook.md); this file only covers
running the code.

`CLAUDE.md` at the repo root is written for an AI coding assistant, not for
you — skip it unless you're pairing with one.

## Run the curation server (local, no Docker)

Requires [uv](https://docs.astral.sh/uv/) and Python >= 3.10 (uv provisions
its own 3.12 automatically).

```bash
uv sync --extra dev
CLAWMARKS_HOST=127.0.0.1 uv run python -m clawmarks.curation_server 8420
```

Then open `http://127.0.0.1:8420/`. Without `CLAWMARKS_HOST` set, the server
binds to your Tailscale IP instead, which fails if Tailscale isn't running —
set it for a plain local run.

The `clawmarks` CLI (`uv run clawmarks --help`) also has a `serve`
subcommand, but it always binds port 8420 and ignores any port you pass —
use the module invocation above if you need a different port.

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
