#!/bin/bash
# SDD Orchestrator 기동/중지/상태 확인
# Usage: ./scripts/sdd-orch.sh [start|stop|status|restart]

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
ORCH_DIR="$PROJECT_DIR/orchestrator"
LOG_FILE="/tmp/orchestrator.log"
PID_FILE="/tmp/orchestrator.pid"

start() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "이미 실행 중 (PID: $(cat "$PID_FILE"))"
    return 0
  fi

  # backend/.env에서 Slack/Sentry 환경변수 로드
  _SLACK=$(grep '^SLACK_WEBHOOK_URL=' "$PROJECT_DIR/backend/.env" 2>/dev/null | cut -d= -f2-)
  _SENTRY=$(grep '^SENTRY_AUTH_TOKEN=' "$PROJECT_DIR/backend/.env" 2>/dev/null | cut -d= -f2-)

  cd "$ORCH_DIR"
  ORCH_AUTO_RUN="${ORCH_AUTO_RUN:-1}" \
  ORCH_AUTO_DESIGN="${ORCH_AUTO_DESIGN:-1}" \
  SLACK_WEBHOOK_URL="${_SLACK}" \
  SENTRY_AUTH_TOKEN="${_SENTRY}" \
  nohup uv run python -m orchestrator > "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  echo "Orchestrator 시작 (PID: $!, log: $LOG_FILE)"
}

stop() {
  if [ ! -f "$PID_FILE" ]; then
    echo "PID 파일 없음 — 실행 중이 아닙니다"
    return 0
  fi

  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "Orchestrator 중지 (PID: $PID)"
  else
    echo "프로세스 이미 종료됨"
  fi
  rm -f "$PID_FILE"
}

status() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "실행 중 (PID: $(cat "$PID_FILE"))"
    echo "--- 최근 로그 ---"
    tail -5 "$LOG_FILE" 2>/dev/null || echo "(로그 없음)"
  else
    echo "중지됨"
    rm -f "$PID_FILE"
  fi
}

case "${1:-status}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; sleep 1; start ;;
  status)  status ;;
  *)       echo "Usage: $0 [start|stop|status|restart]" ;;
esac
