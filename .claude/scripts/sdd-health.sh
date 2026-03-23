#!/bin/bash
# 로컬 서비스 헬스체크 — cron에서 실행
# 실패 시 자동 재시작 + Slack 알림

SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"
FAILURES=""
RESTARTED=""

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

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
if [ -n "$FAILURES" ] && [ -n "$SLACK_WEBHOOK" ]; then
  curl -s -X POST "$SLACK_WEBHOOK" \
    -H 'Content-type: application/json' \
    -d "{\"text\": \"[Health Check] 서비스 다운 감지: ${FAILURES}| 자동 재시작: ${RESTARTED}\"}" \
    > /dev/null 2>&1
fi
