#!/bin/bash

# Shorts Producer - Audio Server (CUDA GPU)
# 2엔진 통합: Qwen3-TTS(씬TTS+보이스디자인) + MusicGen(BGM)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUDIO_DIR="$SCRIPT_DIR/audio"
VENV_DIR="$AUDIO_DIR/.venv"
PORT=8001

LOG_DIR="$AUDIO_DIR/logs"
LOG_FILE="$LOG_DIR/audio.log"
mkdir -p "$LOG_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

usage() {
  echo "Usage: $0 {start|stop|status|logs}"
  echo ""
  echo "  start   - Start audio server (Qwen3 + MusicGen)"
  echo "  stop    - Stop audio server"
  echo "  status  - Check server health"
  echo "  logs    - Tail server logs"
  exit 1
}

check_venv() {
  if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}venv not found. Creating...${NC}"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -e "$AUDIO_DIR"
  fi
}

get_pid() {
  pgrep -f "uvicorn main:app.*--port $PORT" 2>/dev/null || true
}

do_start() {
  PID=$(get_pid)
  if [ -n "$PID" ]; then
    echo -e "${YELLOW}Audio server already running (PID $PID)${NC}"
    exit 0
  fi

  # Docker 컨테이너가 같은 포트를 점유 중이면 중지
  DOCKER_NAME=$(docker ps --format '{{.Names}}' --filter "publish=$PORT" 2>/dev/null | head -1)
  if [ -n "$DOCKER_NAME" ]; then
    echo -e "${YELLOW}Docker container '$DOCKER_NAME' occupying port $PORT — stopping...${NC}"
    docker stop "$DOCKER_NAME" > /dev/null 2>&1
    sleep 1
  fi

  check_venv

  echo -e "${GREEN}Starting audio server on port $PORT (Qwen3 + MusicGen)...${NC}"
  cd "$AUDIO_DIR"
  export TTS_DEVICE=cuda
  export MUSICGEN_DEVICE=cpu
  "$VENV_DIR/bin/uvicorn" main:app \
    --host 0.0.0.0 --port "$PORT" \
    >> "$LOG_FILE" 2>&1 &

  echo "PID: $!"
  echo -e "Logs: ${YELLOW}$LOG_FILE${NC}"
  echo ""

  # Wait for health
  echo -n "Loading models"
  for i in $(seq 1 90); do
    if curl -sf "http://localhost:$PORT/health" > /dev/null 2>&1; then
      echo ""
      curl -s "http://localhost:$PORT/health" | python3 -m json.tool
      echo -e "\n${GREEN}Audio server ready!${NC}"
      return
    fi
    echo -n "."
    sleep 2
  done
  echo -e "\n${RED}Startup timeout (180s)${NC}"
}

do_stop() {
  PID=$(get_pid)
  if [ -n "$PID" ]; then
    kill "$PID"
    echo -e "${GREEN}Audio server stopped (PID $PID)${NC}"
  else
    echo "Audio server not running."
  fi
}

do_status() {
  PID=$(get_pid)
  if [ -z "$PID" ]; then
    echo -e "${RED}Audio server not running${NC}"
    exit 1
  fi

  echo -e "PID: $PID"
  RESP=$(curl -sf "http://localhost:$PORT/health" 2>/dev/null)
  if [ $? -eq 0 ]; then
    echo "$RESP" | python3 -m json.tool
  else
    echo -e "${YELLOW}Process running but not responding yet${NC}"
  fi
}

do_logs() {
  if [ ! -f "$LOG_FILE" ]; then
    echo "No log file found."
    exit 1
  fi
  tail -f "$LOG_FILE"
}

case "${1:-}" in
  start)  do_start ;;
  stop)   do_stop ;;
  status) do_status ;;
  logs)   do_logs ;;
  *)      usage ;;
esac
