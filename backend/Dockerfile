# ============================================================
# audio-glyph-inference - Backend (Python 3.11+ / FastAPI)
# ============================================================
# Single-stage slim build. Python scientific wheels need glibc,
# so we use the slim (Debian) base, not Alpine. Python 3.11
# matches the pyproject.toml floor and avoids surprise wheel gaps.
#
# Uses uv for dependency installation.
# ============================================================
FROM python:3.11-slim

# Base-image security patches. The Debian slim bases currently ship a util-linux that Trivy
# flags HIGH (CVE-2026-53612..53615, fixed upstream in 2.41.5). These packages come from the
# base layer, so this is required even though nothing below installs them.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# System dependencies:
#   libsndfile1   - required by soundfile / librosa at runtime
#   libgl1        - required by opencv-python-headless
#   libglib2.0-0  - required by opencv-python-headless
#   ffmpeg        - AAC-in-MP4 / .m4a decoding support
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 \
        libgl1 \
        libglib2.0-0 \
        ffmpeg \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx

WORKDIR /app

# Copy only the dependency manifest first for layer caching.
COPY pyproject.toml ./

# Install project dependencies into a local .venv managed by uv. pycma (`cma`)
# is pure Python, so the Phase-2 CMA-ES dependency needs no apt package.
# We compile pyproject.toml to a requirements file first because shell process
# substitution is bash-only and fails under /bin/sh.
# uv resolves torch/torchaudio to +cpu builds via [tool.uv.sources]; the flat
# requirements.txt cannot carry a per-package index, so install adds the
# PyTorch CPU index explicitly to locate those pinned wheels.
RUN uv venv /opt/venv \
    && uv pip compile pyproject.toml -o /tmp/requirements.txt \
    && uv pip install --no-cache --python /opt/venv/bin/python \
        --extra-index-url https://download.pytorch.org/whl/cpu -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy source after deps are installed.
COPY src ./src
COPY scripts ./scripts
COPY data ./data
COPY experiments ./experiments
COPY alembic.ini ./
COPY migrations ./migrations
COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh

EXPOSE 8000

# Healthcheck hits the /health endpoint exposed by FastAPI.
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# entrypoint runs `alembic upgrade head` then exec's uvicorn.
# local-dev container, not a public-facing service,
# so non-root is exempt per global CLAUDE.md section 9. A non-root USER would also break the
# bind-mounted host directories this image reads and writes at runtime. Revisit before any
# deployment beyond localhost.
# nosemgrep: dockerfile.security.missing-user-entrypoint.missing-user-entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
