#!/bin/bash
# E2E Backend entrypoint: schema → seed → serve
set -e

echo "[E2E] Running Alembic migrations..."
uv run alembic upgrade head

echo "[E2E] Seeding test data..."
psql "$DATABASE_URL" -f /app/scripts/e2e-seed.sql

echo "[E2E] Starting backend server..."
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
