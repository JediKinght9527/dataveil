# syntax=docker/dockerfile:1

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml README.md ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Create non-root user
RUN groupadd -r dataveil && useradd -r -g dataveil dataveil

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY dv/ ./dv/

# Create data directory
RUN mkdir -p /home/dataveil/.dataveil && \
    chown -R dataveil:dataveil /home/dataveil

USER dataveil

# Expose gateway port
EXPOSE 8787

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8787/health')" || exit 1

# Default command
CMD ["python", "-m", "dv", "start", "--host", "0.0.0.0", "--port", "8787"]
