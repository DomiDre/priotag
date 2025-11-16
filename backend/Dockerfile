FROM ubuntu:24.04 AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies and Python
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER ubuntu

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/ubuntu/.local/bin:$PATH"

# Set work directory
WORKDIR /app

# Copy project files
COPY --chown=ubuntu:ubuntu pyproject.toml uv.lock .python-version ./

# Create a minimal __init__.py to avoid sync issues
RUN mkdir -p src/priotag && touch src/priotag/__init__.py && touch README.md


# --- Development stage ---
FROM base AS development

# Install supercronic for development scheduler
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && curl -fsSL https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64 -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
USER ubuntu

# Install dependencies
RUN uv sync

# Copy source code (this will overwrite the dummy __init__.py)
COPY --chown=ubuntu:ubuntu src/ ./src/

# Copy scheduler scripts
COPY --chown=ubuntu:ubuntu scheduler.sh scheduler-dev.sh ./

# Create directories
RUN mkdir -p /app/static

# Expose port
EXPOSE 8000

# Run with uv
CMD ["uv", "run", "python", "-m", "uvicorn", "priotag.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# --- Production stage ---
FROM ubuntu:24.04 AS production

# Build arguments for metadata
ARG BUILD_VERSION="unknown"
ARG BUILD_COMMIT="unknown"
ARG BUILD_DATE="unknown"

# Install only essential runtime dependencies including supercronic
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    ca-certificates \
    && curl -fsSL https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64 -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1001 -s /bin/bash appuser

# Set work directory and change ownership
WORKDIR /app
RUN chown appuser:appuser /app

# Switch to non-root user BEFORE creating venv
USER appuser

# Copy project files as appuser
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

# Install uv for appuser (temporarily, just for installing deps)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/appuser/.local/bin:$PATH"

# Create dummy files for uv
RUN mkdir -p src/priotag && touch src/priotag/__init__.py && touch README.md

# Install production dependencies only
RUN uv sync --frozen --no-dev

# Remove uv to save space (optional)
RUN rm -rf /home/appuser/.local/bin/uv /home/appuser/.local/bin/uvx

# Copy application code
COPY --chown=appuser:appuser src/ ./src/

# Create build info file
RUN printf '{\n  "version": "%s",\n  "commit": "%s",\n  "build_date": "%s",\n  "source_url": "https://github.com/DomiDre/priotag/tree/%s"\n}' \
    "$BUILD_VERSION" "$BUILD_COMMIT" "$BUILD_DATE" "$BUILD_COMMIT" > /app/build_info.json

# Create necessary directories
RUN mkdir -p /app/static /app/uploads

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# Expose application port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

USER root
COPY --chown=root:root ./load-secrets.sh /usr/local/bin/load-secrets.sh
COPY --chown=appuser:appuser ./scheduler.sh /app/scheduler.sh
RUN chmod +x /usr/local/bin/load-secrets.sh && chmod +x /app/scheduler.sh
USER appuser

ENTRYPOINT ["/usr/local/bin/load-secrets.sh"]
# Run with gunicorn for production
CMD ["gunicorn", \
     "priotag.main:app", \
     "--config", \
     "/app/src/priotag/gunicorn_config.py"]
