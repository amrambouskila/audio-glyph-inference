# ============================================================
# audio-glyph-inference — Backend (Python 3.11+ / FastAPI)
# ============================================================
# Single-stage slim build. Python scientific wheels need glibc,
# so we use the slim (Debian) base — not Alpine. We pin to
# Python 3.11 to match the pyproject.toml floor and to avoid
# surprise on wheel availability for torch/librosa/opencv.
#
# Uses uv for dependency installation (per global CLAUDE.md
# section 5: "Package manager: uv — never pip").
# ============================================================
FROM python:3.11-slim

# System dependencies:
#   libsndfile1  — required by soundfile / librosa at runtime
#   libgl1       — required by opencv-python-headless
#   libglib2.0-0 — required by opencv-python-headless
#   build-essential — for any source wheels (e.g. numba compilation)
#   ffmpeg       — optional audio decoding support
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 \
        libgl1 \
        libglib2.0-0 \
        build-essential \
        ffmpeg \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx

WORKDIR /app

# Copy only the dependency manifest first for layer caching.
COPY pyproject.toml ./

# Install project dependencies into a local .venv managed by uv.
RUN uv venv /opt/venv \
    && . /opt/venv/bin/activate \
    && uv pip install --no-cache -r <(uv pip compile pyproject.toml)

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy source after deps are installed.
COPY src ./src
COPY data ./data
COPY experiments ./experiments

EXPOSE 8000

# Healthcheck hits the /health endpoint exposed by FastAPI.
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]