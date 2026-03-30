#!/bin/bash
# E2E 전체 사이클 실행 래퍼
# Usage: ./scripts/run-e2e.sh [--keep]
#   --keep: 테스트 후 컨테이너 유지 (디버깅용)
set -euo pipefail

COMPOSE_FILE="docker-compose.e2e.yml"
export COMPOSE_PROJECT_NAME="shorts-e2e"
KEEP=false

for arg in "$@"; do
  case "$arg" in
    --keep) KEEP=true ;;
  esac
done

cleanup() {
  if [ "$KEEP" = false ]; then
    echo "[E2E] Tearing down..."
    docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
  else
    echo "[E2E] --keep: containers left running. Cleanup with:"
    echo "  docker compose -f $COMPOSE_FILE down -v --remove-orphans"
  fi
}
trap cleanup EXIT

# 이전 실행 정리
docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true

echo "[E2E] Building and starting Docker environment..."
docker compose -f "$COMPOSE_FILE" up -d --build

# Backend health wait
echo "[E2E] Waiting for backend..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:18000/health > /dev/null 2>&1; then
    echo "[E2E] Backend ready (${i}s)"
    break
  fi
  [ "$i" -eq 60 ] && { echo "[E2E] Backend timeout"; exit 1; }
  sleep 1
done

# Frontend health wait
echo "[E2E] Waiting for frontend..."
for i in $(seq 1 90); do
  if curl -sf http://localhost:13000 > /dev/null 2>&1; then
    echo "[E2E] Frontend ready (${i}s)"
    break
  fi
  [ "$i" -eq 90 ] && { echo "[E2E] Frontend timeout"; exit 1; }
  sleep 1
done

echo "[E2E] Environment ready!"
echo "  Frontend: http://localhost:13000"
echo "  Backend:  http://localhost:18000"
echo ""

# Playwright 실행 (있으면)
if [ -d frontend/e2e ] && command -v npx &> /dev/null; then
  echo "[E2E] Running Playwright tests..."
  cd frontend
  E2E_DOCKER=1 npx playwright test --config=playwright.e2e.config.ts --reporter=list
  EXIT_CODE=$?
  cd ..
  echo "[E2E] Tests finished with exit code: $EXIT_CODE"
  exit $EXIT_CODE
else
  echo "[E2E] No test runner available. Environment is ready for manual testing."
  if [ "$KEEP" = false ]; then
    echo "[E2E] Use --keep to keep containers running."
    KEEP=true  # keep containers since no tests ran
  fi
fi
