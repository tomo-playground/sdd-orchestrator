#!/bin/bash
# E2E Backend entrypoint: schema → seed → serve
set -e

echo "[E2E] Creating database schema..."
uv run python -c "
from models.base import Base
from models import *  # noqa: F403 — 모든 모델 import (테이블 등록)
from sqlalchemy import create_engine
import os

engine = create_engine(os.environ['DATABASE_URL'])
Base.metadata.create_all(engine)
engine.dispose()
print('[E2E] Schema created.')
"

echo "[E2E] Stamping Alembic head..."
uv run alembic stamp head

echo "[E2E] Seeding test data..."
psql "$DATABASE_URL" -f /app/scripts/e2e-seed.sql

echo "[E2E] Starting backend server..."
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
