# Multi-stage Dockerfile for AI Cryptocurrency Auto-Trading System
# Production-ready configuration with security best practices

#
# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_WARN_SCRIPT_LOCATION=1

# Set working directory
WORKDIR /app
# Install system dependencies for building
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
# Copy dependency files
COPY pyproject.toml ./
COPY src/ ./src/
# Install dependencies with pip cache mounted from builder stage
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.11-slim AS runtime
# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_WARN_SCRIPT_LOCATION=1
# Set working directory
WORKDIR /app
# Create non-root user for security
RUN groupadd -r appgroup -g 1001 appuser && \
    useradd -r appuser -u 1001 -g appgroup && \
    chown -R appuser:appgroup /app
# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# Copy application code
COPY --chown=appuser:appgroup src/ /app/src
# Switch to non-root user
USER appuser
# Expose port
EXPOSE 8000
# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
# Default command
CMD ["python", "-m", "gpt_bitcoin.cli"]
