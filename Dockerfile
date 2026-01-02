# Multi-stage Dockerfile for PBX System
# Stage 1: Builder stage for dependencies
FROM python:3.12-slim-bookworm AS builder

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libportaudio2 \
    portaudio19-dev \
    libopus-dev \
    libspeex-dev \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files
COPY requirements.txt /tmp/
WORKDIR /tmp

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.12-slim-bookworm

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Audio processing libraries
    ffmpeg \
    libportaudio2 \
    portaudio19-dev \
    espeak \
    libopus0 \
    libspeex1 \
    libsndfile1 \
    # Database client libraries
    libpq5 \
    # Network utilities for troubleshooting
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r pbx && useradd -r -g pbx -u 1000 pbx && \
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
EXPOSE 8880/tcp

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PBX_CONFIG=/app/config.yml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python", "/app/healthcheck.py"]

# Set entrypoint
ENTRYPOINT ["python"]
CMD ["/app/main.py"]
