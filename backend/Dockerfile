# ── Stage 1: build dependencies ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application source
COPY ./app ./app

# Make sure user-installed scripts are on PATH
ENV PATH=/root/.local/bin:$PATH

# Render injects PORT at runtime; default to 8000 for local docker run
ENV PORT=8000

EXPOSE $PORT

# Use shell form so $PORT is expanded at container start
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
