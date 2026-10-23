# Stage 1: Build Frontend Assets
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY server/frontend/package*.json ./
RUN npm ci

COPY server/frontend/ ./
RUN npm run build

# Stage 2: Production Python Backend
FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY server/ ./
COPY --from=frontend-builder /app/static/ ./static/

RUN mkdir -p /app/firmware_catalog /app/data && \
    useradd -m -u 1000 -s /bin/bash myvoice && \
    chown -R myvoice:myvoice /app && \
    chmod +x /app/entrypoint.sh

USER myvoice

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
