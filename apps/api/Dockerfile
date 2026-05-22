# API container — Python 3.12 + uv + uvicorn. Target: Railway (also runs
# locally with `docker build -t tce-api . && docker run -p 8000:8000 tce-api`).
#
# The uv image is the recommended base when the project uses uv as its package
# manager: it already has uv on PATH and a properly configured Python.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Faster, deterministic installs; never write to ~/.cache inside the image.
ENV UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies first so the layer cache survives source-only changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy the source last.
COPY src ./src
COPY scripts ./scripts

# Railway injects $PORT at runtime; default 8000 for local docker test.
ENV PORT=8000
EXPOSE 8000

# Bind to 0.0.0.0 so the container is reachable from the host/load balancer.
# Single worker — keeps cvxpy / QuantLib memory footprint predictable. Scale
# horizontally on Railway by increasing replicas, not workers.
CMD ["sh", "-c", "uv run uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}"]
