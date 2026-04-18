# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Build-time system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libmagic-dev \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Copy project manifest first so the layer is cached unless deps change
COPY pyproject.toml ./
# Ensure hatchling can find the package during install
COPY src/ ./src/

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir "prometheus-fastapi-instrumentator>=7.0.0"

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Runtime-only system libs
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
        curl \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy application source
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser pyproject.toml ./
# Copy static assets served at /public/samples/*
COPY --chown=appuser:appuser public_assets/ ./public_assets/

USER appuser

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8100/healthz || exit 1

CMD ["uvicorn", "src.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8100", \
     "--workers", "4", \
     "--timeout-keep-alive", "65", \
     "--timeout-graceful-shutdown", "30"]
