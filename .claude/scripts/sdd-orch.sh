#!/bin/bash
# SDD Orchestrator 기동/중지/상태 확인
# Usage: ./scripts/sdd-orch.sh [start|stop|status|restart]

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
export SDD_PROJECT_ROOT="$PROJECT_DIR"
ORCH_DIR="$PROJECT_DIR/sdd-orchestrator"
LOG_FILE="$ORCH_DIR/logs/orchestrator.log"
PID_FILE="/tmp/orchestrator.pid"

start() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "이미 실행 중 (PID: $(cat "$PID_FILE"))"
    return 0
  fi

  # sdd-orchestrator/.env에서 환경변수 로드 (키 없으면 빈 문자열)
  _SENTRY=$(grep '^SENTRY_AUTH_TOKEN=' "$ORCH_DIR/.env" 2>/dev/null | cut -d= -f2- || true)
  _BOT_TOKEN=$(grep '^SLACK_BOT_TOKEN=' "$ORCH_DIR/.env" 2>/dev/null | cut -d= -f2- || true)
  _APP_TOKEN=$(grep '^SLACK_APP_TOKEN=' "$ORCH_DIR/.env" 2>/dev/null | cut -d= -f2- || true)
  _BOT_CHANNEL=$(grep '^SLACK_BOT_ALLOWED_CHANNEL=' "$ORCH_DIR/.env" 2>/dev/null | cut -d= -f2- || true)
  _BOT_USERS=$(grep '^SLACK_BOT_ALLOWED_USERS=' "$ORCH_DIR/.env" 2>/dev/null | cut -d= -f2- || true)

  mkdir -p "$ORCH_DIR/logs"
  cd "$ORCH_DIR"
  export ORCH_AUTO_RUN="${ORCH_AUTO_RUN:-1}"
  export ORCH_AUTO_DESIGN="${ORCH_AUTO_DESIGN:-1}"
  export SENTRY_AUTH_TOKEN="${_SENTRY}"
  export SLACK_BOT_TOKEN="${_BOT_TOKEN}"
  export SLACK_APP_TOKEN="${_APP_TOKEN}"
  export SLACK_BOT_ALLOWED_CHANNEL="${_BOT_CHANNEL}"
  export SLACK_BOT_ALLOWED_USERS="${_BOT_USERS}"
  nohup uv run python -m sdd_orchestrator > "$LOG_FILE" 2>&1 &
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
