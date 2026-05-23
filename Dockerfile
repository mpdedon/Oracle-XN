# ─────────────────────────────────────────────────────────────────────────────
# ORACLE-X/N  —  Multi-stage Dockerfile
# Stage 1: builder — install all Python deps
# Stage 2: runtime  — copy site-packages only, keep image lean
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System build tools needed for C-extension packages (chromadb, faiss-cpu)
# ForceIPv4 avoids IPv6 resolution hangs inside Docker Desktop on Windows
RUN apt-get -o Acquire::ForceIPv4=true update && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# ── Step 1: pip upgrade + CPU-only torch (large wheel, separate layer) ───────
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir --timeout 600 --retries 5 \
        torch --index-url https://download.pytorch.org/whl/cpu

# ── Step 2: All other requirements ───────────────────────────────────────────
RUN pip install --no-cache-dir --timeout 300 --retries 5 -r requirements.txt

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
