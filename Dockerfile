# syntax=docker/dockerfile:1

# Multi-stage Dockerfile for PBX System
# Stage 1: Builder stage for dependencies
FROM python:3.14-slim-bookworm AS builder

# Install system dependencies required for building Python packages
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libportaudio2 \
    portaudio19-dev \
    libopus-dev \
    libspeex-dev \
    libsndfile1-dev

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy dependency files first for layer caching
COPY pyproject.toml /tmp/
WORKDIR /tmp

# Install Python dependencies into the venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /opt/venv/bin/python --no-cache -e "."

# Stage 2: Runtime stage
FROM python:3.14-slim-bookworm

# Install runtime system dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    # Audio processing libraries
    ffmpeg \
    libportaudio2 \
    espeak \
    libopus0 \
    libspeex1 \
    libsndfile1 \
    # Database client libraries
    libpq5 \
    # Network utilities for troubleshooting
    netcat-openbsd \
    # TLS certificate handling
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r pbx && useradd -r -g pbx -u 1000 -s /usr/sbin/nologin pbx && \
    mkdir -p /app /data/recordings /data/voicemail /data/cdr /data/moh && \
    chown -R pbx:pbx /app /data

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=pbx:pbx . /app/

# Create necessary directories and set permissions
RUN mkdir -p \
    /app/auto_attendant \
    /app/voicemail_prompts \
    /app/logs \
    /app/provisioning_templates \
    && chown -R pbx:pbx /app

# Switch to non-root user
USER pbx

# Expose ports
# SIP signaling
EXPOSE 5060/udp
# RTP media ports (default range)
EXPOSE 10000-20000/udp
# HTTP API
EXPOSE 9000/tcp

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PBX_CONFIG=/app/config.yml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python", "/app/healthcheck.py"]

# Set entrypoint
ENTRYPOINT ["python"]
CMD ["/app/main.py"]
