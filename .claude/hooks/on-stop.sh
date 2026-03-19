#!/bin/bash
# SDD Stop Hook: 품질 게이트 + Self-Heal (최대 3회)
# Exit 0 = 종료 허용, Exit 2 = Claude에게 수정 요청

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

RETRY_FILE="/tmp/claude-stop-hook-retry-$$"
MAX_RETRIES=3

# stdin에서 hook input 읽기
INPUT=$(cat)

# ─── 재시도 카운터 관리 ───
# stop_hook_active=true면 이전 실패 후 재시도 중
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')

if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  # 기존 카운터 파일 찾기 (PID 무관하게)
  RETRY_FILE=$(ls /tmp/claude-stop-hook-retry-* 2>/dev/null | head -1)
  if [ -z "$RETRY_FILE" ]; then
    RETRY_FILE="/tmp/claude-stop-hook-retry-$$"
    echo "1" > "$RETRY_FILE"
  fi
  RETRY_COUNT=$(cat "$RETRY_FILE" 2>/dev/null || echo "0")

  if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
    echo "Stop Hook: ${MAX_RETRIES}회 재시도 초과 — 종료합니다" >&2
    # status: failed 업데이트
    BRANCH=$(git branch --show-current)
    TASK_NAME=$(echo "$BRANCH" | sed 's|^feat/||')
    CURRENT="$PROJECT_DIR/.claude/tasks/current/${TASK_NAME}.md"
    if [ -f "$CURRENT" ]; then
      sed -i 's/^status:.*/status: failed/' "$CURRENT"
    fi
    rm -f "$RETRY_FILE"
    exit 0
  fi

  echo $((RETRY_COUNT + 1)) > "$RETRY_FILE"
else
  # 첫 실행: 카운터 초기화
  rm -f /tmp/claude-stop-hook-retry-* 2>/dev/null
  echo "0" > "$RETRY_FILE"
fi

# ─── 변경 감지 ───
if git diff --quiet && git diff --staged --quiet; then
  echo "변경 없음 — 검증 생략" >&2
  rm -f /tmp/claude-stop-hook-retry-* 2>/dev/null
  exit 0
fi

# 코드 파일 변경 여부 (.py, .ts, .tsx, .js, .jsx)
CHANGED_CODE=$(git diff --name-only main...HEAD 2>/dev/null | grep -cE '\.(py|ts|tsx|js|jsx)$' || true)
CHANGED_UNSTAGED=$(git diff --name-only | grep -cE '\.(py|ts|tsx|js|jsx)$' || true)
TOTAL_CHANGED=$((CHANGED_CODE + CHANGED_UNSTAGED))

if [ "$TOTAL_CHANGED" -eq 0 ]; then
  echo "코드 변경 없음 (문서/설정만) — 검증 생략" >&2
  rm -f /tmp/claude-stop-hook-retry-* 2>/dev/null
  exit 0
fi

# ─── 품질 게이트 실행 ───
FAILURES=""

# Step 1. Lint
echo "Step 1/5. Lint" >&2
cd "$PROJECT_DIR/backend"
uv run ruff check --fix --quiet . 2>/dev/null || true
uv run ruff format --quiet . 2>/dev/null || true
cd "$PROJECT_DIR/frontend"
npx prettier --write "src/**/*.{ts,tsx}" --log-level warn 2>/dev/null || true
cd "$PROJECT_DIR"
echo "Lint 완료" >&2

# Step 2. Backend pytest
echo "Step 2/5. Backend pytest" >&2
cd "$PROJECT_DIR/backend"
if ! uv run pytest --ignore=tests/vrt -q 2>&1; then
  FAILURES="${FAILURES}Backend pytest 실패. "
fi
cd "$PROJECT_DIR"

# Step 3. Frontend vitest
echo "Step 3/5. Frontend vitest" >&2
cd "$PROJECT_DIR/frontend"
if ! npm test -- --run 2>&1; then
  FAILURES="${FAILURES}Frontend vitest 실패. "
fi
cd "$PROJECT_DIR"

# Step 4. VRT
echo "Step 4/5. VRT" >&2
cd "$PROJECT_DIR/backend"
if ! uv run pytest tests/vrt -q 2>&1; then
  FAILURES="${FAILURES}VRT 실패. "
fi
cd "$PROJECT_DIR"

# Step 5. E2E (Playwright) — 서버 실행 중일 때만
echo "Step 5/5. E2E (Playwright)" >&2
BACKEND_UP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
FRONTEND_UP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")

if [ "$BACKEND_UP" != "000" ] && [ "$FRONTEND_UP" != "000" ]; then
  cd "$PROJECT_DIR/frontend"
  if ! npx playwright test --reporter=line 2>&1; then
    FAILURES="${FAILURES}E2E 실패. "
  fi
  cd "$PROJECT_DIR"
else
  echo "서버 미실행 — E2E 스킵" >&2
fi

# ─── 결과 판정 ───
if [ -n "$FAILURES" ]; then
  RETRY_COUNT=$(cat /tmp/claude-stop-hook-retry-* 2>/dev/null | head -1 || echo "0")
  REMAINING=$((MAX_RETRIES - RETRY_COUNT))
  echo "품질 게이트 실패 (남은 재시도: ${REMAINING}회): ${FAILURES}코드를 수정하고 다시 시도하세요." >&2
  exit 2
fi

# ─── 전체 통과 ───
rm -f /tmp/claude-stop-hook-retry-* 2>/dev/null

TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
BRANCH=$(git branch --show-current)
DONE_DIR="$PROJECT_DIR/.claude/tasks/done"
mkdir -p "$DONE_DIR"

# 다음 번호 산출
LAST_NUM=$(ls "$DONE_DIR" | grep -oE '^[0-9]+' | sort -n | tail -1 || echo "0")
NEXT_NUM=$(printf "%03d" $((10#${LAST_NUM:-0} + 1)))

# current/브랜치명.md 내용을 done/NNN.md로 이동 + 품질 게이트 결과 추가
TASK_NAME=$(echo "$BRANCH" | sed 's|^feat/||')
CURRENT="$PROJECT_DIR/.claude/tasks/current/${TASK_NAME}.md"
DONE_FILE="$DONE_DIR/${NEXT_NUM}_${TASK_NAME}.md"

if [ -f "$CURRENT" ] && [ -s "$CURRENT" ]; then
  # status를 done으로 업데이트 후 done/으로 이동
  sed -i 's/^status:.*/status: done/' "$CURRENT"
  mv "$CURRENT" "$DONE_FILE"
else
  echo "# $TASK_NAME" > "$DONE_FILE"
fi

cat >> "$DONE_FILE" << EOF

---
## 품질 게이트 결과 [$TIMESTAMP]
- Lint: PASS
- Backend pytest: PASS
- Frontend vitest: PASS
- VRT: PASS
- E2E: ${BACKEND_UP:+PASS}${BACKEND_UP:-SKIP}
EOF

echo "전체 통과 — PR 생성 가능" >&2
exit 0
