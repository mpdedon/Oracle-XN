# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# ORACLE-X/N  —  Multi-stage Dockerfile
# Stage 1: builder — install all Python deps
# Stage 2: runtime  — copy site-packages only, keep image lean
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps needed for some packages (e.g. chromadb, sentence-transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# ── Step 1: CPU-only torch in its own committed layer ────────────────────────
# BuildKit cache mount persists pip's download cache between build attempts.
# If this layer succeeds once, Docker never re-runs it (it's committed).
# Removing --no-cache-dir allows pip to reuse partial downloads on retry.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
 && pip install --timeout 300 --retries 10 \
    torch --index-url https://download.pytorch.org/whl/cpu

# ── Step 2: All other requirements ───────────────────────────────────────────
# The pip cache mount means any wheel already downloaded in a previous failed
# attempt is found on disk and skipped — so a retry resumes, not restarts.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 300 --retries 10 -r requirements.txt

# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project source
COPY . .

# Ensure data directories exist
RUN mkdir -p /data/chroma_db /data/sqlite

# Env defaults (override via docker-compose or -e flags)
ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL="sqlite:////data/sqlite/oracle_xn.db" \
    CHROMA_PERSIST_DIR="/data/chroma_db" \
    GRAPH_PERSIST_PATH="/data/oracle_graph.pkl"

EXPOSE 8000

CMD ["python", "main.py"]
