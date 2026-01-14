# =============================================================================
# Books API Dockerfile
# =============================================================================
# This Dockerfile creates a production-ready container for the Books API.
#
# MULTI-STAGE BUILD
# =================
# We use a multi-stage build to:
# 1. Keep the final image small (no build tools)
# 2. Separate build-time dependencies from runtime
# 3. Improve security (fewer packages = smaller attack surface)
#
# SECURITY BEST PRACTICES
# =======================
# - Non-root user (app runs as 'appuser')
# - No shell in final image (optional, can add for debugging)
# - Minimal base image (python:3.12-slim)
# - Fixed versions for reproducibility

# =============================================================================
# Stage 1: Builder
# =============================================================================
# This stage installs dependencies and can be discarded after

FROM python:3.12-slim as builder

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files
# PYTHONUNBUFFERED: Ensures Python output is sent straight to terminal
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # pip settings
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
# gcc, libpq-dev: Required for psycopg2 compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt


# =============================================================================
# Stage 2: Production
# =============================================================================
# This is the final, minimal image that will be deployed

FROM python:3.12-slim as production

# Labels for container metadata
LABEL maintainer="Your Name <your.email@example.com>" \
    version="0.1.0" \
    description="Books API - FastAPI application"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Application settings
    APP_HOME=/app \
    # Use the virtual environment
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
# libpq5: PostgreSQL client library (runtime, not -dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
# Running as root is a security risk
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR $APP_HOME

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

# Expose port (documentation, doesn't actually publish)
EXPOSE 8000

# Health check
# Docker will periodically run this to check if container is healthy
# --interval: How often to check (30s)
# --timeout: How long to wait for response (10s)
# --start-period: Initial delay before starting checks (10s)
# --retries: How many failures before marking unhealthy (3)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Default command
# uvicorn: ASGI server
# app.main:app: The FastAPI application
# --host 0.0.0.0: Listen on all interfaces
# --port 8000: Port to listen on
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
