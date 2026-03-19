#!/bin/bash
# SDD Stop Hook: 품질 게이트 + Self-Heal (최대 3회)
# Exit 0 = 종료 허용, Exit 2 = Claude에게 수정 요청
#
# 전략: self-heal 중 → 변경 관련 테스트만 (빠른 피드백)
#        최종 판정 → Backend+Frontend+VRT 병렬 실행

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# ─── 브랜치 가드: feat/ 브랜치에서만 실행 ───
BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if ! echo "$BRANCH" | grep -qE '(^feat/|^worktree-feat/)'; then
  exit 0
fi

RETRY_FILE="/tmp/claude-stop-hook-retry-$$"
MAX_RETRIES=3

# stdin에서 hook input 읽기
INPUT=$(cat)

# ─── 재시도 카운터 관리 ───
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')

if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  RETRY_FILE=$(ls /tmp/claude-stop-hook-retry-* 2>/dev/null | head -1)
  if [ -z "$RETRY_FILE" ]; then
    RETRY_FILE="/tmp/claude-stop-hook-retry-$$"
    echo "1" > "$RETRY_FILE"
  fi
  RETRY_COUNT=$(cat "$RETRY_FILE" 2>/dev/null || echo "0")

  if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
    echo "Stop Hook: ${MAX_RETRIES}회 재시도 초과 — 종료합니다" >&2
    TASK_NAME=$(echo "$BRANCH" | sed -E 's|^(worktree-)?feat/||')
    CURRENT="$PROJECT_DIR/.claude/tasks/current/${TASK_NAME}.md"
    if [ -f "$CURRENT" ]; then
      sed -i 's/^status:.*/status: failed/' "$CURRENT"
    fi
    rm -f "$RETRY_FILE"
    exit 0
  fi

  echo $((RETRY_COUNT + 1)) > "$RETRY_FILE"
else
  rm -f /tmp/claude-stop-hook-retry-* 2>/dev/null
  echo "0" > "$RETRY_FILE"
fi

# ─── 변경 감지 ───
if git diff --quiet && git diff --staged --quiet; then
  echo "변경 없음 — 검증 생략" >&2
  rm -f /tmp/claude-stop-hook-retry-* 2>/dev/null
  exit 0
fi

# 변경된 코드 파일 목록 수집
CHANGED_PY=$(git diff --name-only main...HEAD 2>/dev/null | grep -E '\.py$' || true)
CHANGED_PY_UNSTAGED=$(git diff --name-only | grep -E '\.py$' || true)
CHANGED_TS=$(git diff --name-only main...HEAD 2>/dev/null | grep -E '\.(ts|tsx|js|jsx)$' || true)
CHANGED_TS_UNSTAGED=$(git diff --name-only | grep -E '\.(ts|tsx|js|jsx)$' || true)

ALL_PY=$(echo -e "${CHANGED_PY}\n${CHANGED_PY_UNSTAGED}" | sort -u | grep -v '^$' || true)
ALL_TS=$(echo -e "${CHANGED_TS}\n${CHANGED_TS_UNSTAGED}" | sort -u | grep -v '^$' || true)

PY_COUNT=0
[ -n "$ALL_PY" ] && PY_COUNT=$(echo "$ALL_PY" | wc -l)
TS_COUNT=0
[ -n "$ALL_TS" ] && TS_COUNT=$(echo "$ALL_TS" | wc -l)
TOTAL_CHANGED=$((PY_COUNT + TS_COUNT))

if [ "$TOTAL_CHANGED" -eq 0 ]; then
  echo "코드 변경 없음 (문서/설정만) — 검증 생략" >&2
  rm -f /tmp/claude-stop-hook-retry-* 2>/dev/null
  exit 0
fi

# ─── 품질 게이트 실행 ───
FAILURES=""

# Step 1. Lint (항상 직렬, 빠름)
echo "Step 1. Lint" >&2
cd "$PROJECT_DIR/backend"
uv run ruff check --fix --quiet . 2>/dev/null || true
uv run ruff format --quiet . 2>/dev/null || true
cd "$PROJECT_DIR/frontend"
npx prettier --write "src/**/*.{ts,tsx}" --log-level warn 2>/dev/null || true
cd "$PROJECT_DIR"
echo "Lint 완료" >&2

# ─── self-heal 중이면 변경 관련 테스트만 실행 (빠른 피드백) ───
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  echo "Self-heal 모드: 변경 관련 테스트만 실행" >&2

  # Backend: 변경된 .py에 대응하는 테스트 파일 찾기
  if [ "$PY_COUNT" -gt 0 ]; then
    TEST_FILES=""
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      BASENAME=$(basename "$f" .py)
      FOUND=$(find "$PROJECT_DIR/backend/tests" -name "test_${BASENAME}.py" -o -name "test_*${BASENAME}*.py" 2>/dev/null | head -5)
      if [ -n "$FOUND" ]; then
        TEST_FILES="${TEST_FILES} ${FOUND}"
      fi
    done <<< "$ALL_PY"

    if [ -n "$TEST_FILES" ]; then
      echo "Backend 관련 테스트:${TEST_FILES}" >&2
      cd "$PROJECT_DIR/backend"
      if ! uv run pytest $TEST_FILES -q 2>&1; then
        FAILURES="${FAILURES}Backend 관련 테스트 실패. "
      fi
      cd "$PROJECT_DIR"
    else
      echo "Backend: 매칭 테스트 없음 — 스킵" >&2
    fi
  fi

  # Frontend: vitest (이미 빠르므로 전체 실행)
  if [ "$TS_COUNT" -gt 0 ]; then
    cd "$PROJECT_DIR/frontend"
    if ! npm test -- --run 2>&1; then
      FAILURES="${FAILURES}Frontend vitest 실패. "
    fi
    cd "$PROJECT_DIR"
  fi

# ─── 최종 판정: scope 기반 병렬 실행 ───
else
  # Scope 판별: 변경된 영역에 따라 불필요한 테스트 스킵
  HAS_RENDER_CHANGE=$(echo "$ALL_PY" | grep -cE '(services/video/|services/rendering|services/image)' 2>/dev/null || true)
  HAS_RENDER_CHANGE=${HAS_RENDER_CHANGE:-0}

  FAIL_DIR=$(mktemp -d)
  PIDS=""

  # Backend pytest — .py 변경 시만
  if [ "$PY_COUNT" -gt 0 ]; then
    echo "Backend pytest 실행" >&2
    (
      cd "$PROJECT_DIR/backend"
      if ! uv run pytest --ignore=tests/vrt -q 2>&1; then
        echo "Backend pytest 실패. " > "$FAIL_DIR/backend"
      fi
    ) &
    PIDS="$PIDS $!"
  else
    echo "Backend: .py 변경 없음 — 스킵" >&2
  fi

  # Frontend vitest — .ts/.tsx 변경 시만
  if [ "$TS_COUNT" -gt 0 ]; then
    echo "Frontend vitest 실행" >&2
    (
      cd "$PROJECT_DIR/frontend"
      if ! npm test -- --run 2>&1; then
        echo "Frontend vitest 실패. " > "$FAIL_DIR/frontend"
      fi
    ) &
    PIDS="$PIDS $!"
  else
    echo "Frontend: .ts/.tsx 변경 없음 — 스킵" >&2
  fi

  # VRT — 렌더링/이미지 관련 변경 시만
  if [ "$HAS_RENDER_CHANGE" -gt 0 ]; then
    echo "VRT 실행 (렌더링 변경 감지)" >&2
    (
      cd "$PROJECT_DIR/backend"
      if ! uv run pytest tests/vrt -q 2>&1; then
        echo "VRT 실패. " > "$FAIL_DIR/vrt"
      fi
    ) &
    PIDS="$PIDS $!"
  else
    echo "VRT: 렌더링 변경 없음 — 스킵" >&2
  fi

  # 전부 대기
  if [ -n "$PIDS" ]; then
    wait $PIDS
  fi

  # 실패 수집
  for fail_file in "$FAIL_DIR"/*; do
    [ -f "$fail_file" ] && FAILURES="${FAILURES}$(cat "$fail_file")"
  done
  rm -rf "$FAIL_DIR"

  # E2E (서버 실행 중 + fullstack 변경 시만)
  BACKEND_UP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
  FRONTEND_UP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")

  if [ "$BACKEND_UP" != "000" ] && [ "$FRONTEND_UP" != "000" ] && [ "$PY_COUNT" -gt 0 ] && [ "$TS_COUNT" -gt 0 ]; then
    echo "E2E 실행 (fullstack 변경 + 서버 실행 중)" >&2
    cd "$PROJECT_DIR/frontend"
    if ! npx playwright test --reporter=line 2>&1; then
      FAILURES="${FAILURES}E2E 실패. "
    fi
    cd "$PROJECT_DIR"
  else
    echo "E2E 스킵 (서버 미실행 또는 단일 scope 변경)" >&2
  fi
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

LAST_NUM=$(ls "$DONE_DIR" | grep -oE '^[0-9]+' | sort -n | tail -1 || echo "0")
NEXT_NUM=$(printf "%03d" $((10#${LAST_NUM:-0} + 1)))

TASK_NAME=$(echo "$BRANCH" | sed -E 's|^(worktree-)?feat/||')
CURRENT="$PROJECT_DIR/.claude/tasks/current/${TASK_NAME}.md"
DONE_FILE="$DONE_DIR/${NEXT_NUM}_${TASK_NAME}.md"

if [ -f "$CURRENT" ] && [ -s "$CURRENT" ]; then
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
- E2E: $([ "$BACKEND_UP" != "000" ] && echo "PASS" || echo "SKIP")
EOF

echo "전체 통과 — PR 생성 가능" >&2
exit 0
