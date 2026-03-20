# Development Dockerfile
# Not for production use — see Dockerfile.prod
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user even for dev
RUN addgroup --system artist && \
    adduser --system --ingroup artist --home /app artist

# Install Python dependencies before copying code for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=artist:artist ./artist /app/artist
COPY --chown=artist:artist ./static /app/static 2>/dev/null || true
COPY --chown=artist:artist ./migrations /app/migrations
COPY --chown=artist:artist ./alembic.ini /app/alembic.ini

# Create runtime directories
RUN mkdir -p /app/models /app/logs && \
    chown -R artist:artist /app

USER artist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "artist.main"]
