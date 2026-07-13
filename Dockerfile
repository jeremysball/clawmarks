# Serves curation_server.py only. The heavy hyperparameter-search tooling (RunPod driver,
# generation scripts) stays host-side; this image just needs enough of the repo for
# clawmarks.config.repo_root() to find pyproject.toml and for the curation views to import.
FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.9.7

# seeds.html's "Generate" button shells out to `opencode run` (curation_server.py's
# /api/seeds/generate). Headless auth comes from OPENAI_API_KEY at runtime (docker-compose.yml),
# not the interactive `opencode auth login` OAuth flow used on the host, so no credential file
# gets baked into or mounted into this image.
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://opencode.ai/install | bash && \
    mv /root/.opencode/bin/opencode /usr/local/bin/opencode

WORKDIR /app

# notes/ and corrected_dataset_extract/ are excluded by .dockerignore: real training images and
# RunPod-billed generation output must never be baked into an image layer. They're bind-mounted
# at runtime instead (see docker-compose.yml), so pyproject.toml still lands at /app/pyproject.toml
# and clawmarks.config.repo_root() resolves ROOT=/app with no CLAWMARKS_ROOT override needed.
COPY . .

RUN uv sync --frozen --no-dev

EXPOSE 8420

CMD ["uv", "run", "python3", "-m", "clawmarks.curation_server", "8420"]
