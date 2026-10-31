# Multi-stage build for zyPlat backend
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create app user
# Container storage is ephemeral: mount a persistent volume at INSTANCE_DATA_DIR in production.
ENV INSTANCE_DATA_DIR=/app/data/instance-data
RUN useradd -m -u 1000 app && \
    mkdir -p /app /app/data/instance-data && \
    chown -R app:app /app

WORKDIR /app

# Copy requirements first for better caching
COPY --chown=app:app backend/requirements.txt ./backend/
RUN pip install --upgrade pip && \
    pip install -r backend/requirements.txt

# Copy application code
COPY --chown=app:app backend/ ./backend/
COPY --chown=app:app alembic.ini ./

# Switch to app user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
