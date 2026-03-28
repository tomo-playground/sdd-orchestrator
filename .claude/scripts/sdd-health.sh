#!/bin/bash
# 로컬 서비스 헬스체크 — cron에서 실행
# 실패 시 자동 재시작 + Slack 알림

FAILURES=""
RESTARTED=""

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
export SDD_PROJECT_ROOT="$PROJECT_DIR"
ORCH_DIR="$PROJECT_DIR/sdd-orchestrator"

# Slack notification via notify.py CLI (Block Kit)
notify_slack() {
  local msg="$1"
  local level="${2:-warning}"
  local link_args="${3:-}"
  # shellcheck disable=SC2086
  cd "$ORCH_DIR" && uv run python -m sdd_orchestrator.tools.notify "$msg" \
    --level "$level" $link_args 2>&1 | grep -v "^$" >&2 || true
}

# Backend (8000)
if ! curl -sf http://localhost:8000/health > /dev/null 2>&1; then
  FAILURES="${FAILURES}Backend "
  cd "$PROJECT_DIR/backend" && source .venv/bin/activate
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
  RESTARTED="${RESTARTED}Backend "
fi

# Frontend (3000)
if ! curl -sf -o /dev/null http://localhost:3000/ 2>&1; then
  FAILURES="${FAILURES}Frontend "
  cd "$PROJECT_DIR/frontend"
  npx next dev --webpack --hostname 0.0.0.0 > /tmp/frontend.log 2>&1 &
  RESTARTED="${RESTARTED}Frontend "
fi

# Audio (8001)
if ! curl -sf http://localhost:8001/health > /dev/null 2>&1; then
  FAILURES="${FAILURES}Audio "
  cd "$PROJECT_DIR/audio" && source .venv/bin/activate
  uvicorn main:app --host 0.0.0.0 --port 8001 > /tmp/audio.log 2>&1 &
  RESTARTED="${RESTARTED}Audio "
fi

# 장애 감지 시 Slack 알림
if [ -n "$FAILURES" ]; then
  notify_slack "[Health Check] 서비스 다운 감지: ${FAILURES}| 자동 재시작: ${RESTARTED}" "warning"
fi
