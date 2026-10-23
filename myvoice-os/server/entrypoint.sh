#!/bin/sh
set -e

echo "[MyVoice OS] Running database migrations..."
alembic upgrade head

echo "[MyVoice OS] Starting Uvicorn production server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
