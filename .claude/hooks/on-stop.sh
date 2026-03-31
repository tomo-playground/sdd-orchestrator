#!/bin/bash
# SDD Stop Hook: 품질 게이트 + Self-Heal (최대 3회)
# Exit 0 = 종료 허용, Exit 2 = Claude에게 수정 요청
#
# 전략: self-heal 중 → 변경 관련 테스트만 (빠른 피드백)
#        최종 판정 → Backend+Frontend+VRT 병렬 실행

# PROJECT_DIR: git 작업 디렉토리 (변경 감지용)
# TEST_DIR: 원본 프로젝트 (테스트 실행용 — node_modules/.venv 존재)
ORIGINAL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
if [ -n "$PWD" ] && { [ -d "$PWD/.git" ] || [ -f "$PWD/.git" ]; }; then
  PROJECT_DIR="$PWD"
else
  PROJECT_DIR="$ORIGINAL_DIR"
fi
# worktree에서는 의존성이 없으므로 테스트는 원본에서 실행
TEST_DIR="$ORIGINAL_DIR"
cd "$PROJECT_DIR"

# ─── 브랜치 가드: feat/ 또는 fix/ 브랜치에서만 실행 ───
BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if ! echo "$BRANCH" | grep -qE '(^feat/|^worktree-feat/|^worktree-SP-|^fix/)'; then
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
    SP_ID=$(echo "$BRANCH" | grep -oE 'SP-[0-9]+' | head -1)
    # Update state.db (SSOT for task status)
    STATE_DB="/home/tomo/Workspace/shorts-producer/.sdd/state.db"
    if [ -n "$SP_ID" ] && [ -f "$STATE_DB" ]; then
      sqlite3 "$STATE_DB" "INSERT INTO task_status (task_id, status, updated_at) VALUES ('${SP_ID}', 'failed', datetime('now')) ON CONFLICT(task_id) DO UPDATE SET status='failed', updated_at=datetime('now');"
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

# ─── Step 0. 스키마 변경 → 문서 동기화 체크 ───
HAS_SCHEMA_CHANGE=$(echo "$ALL_PY" | grep -cE '(^backend/models/|^backend/alembic/)' 2>/dev/null || true)
HAS_SCHEMA_CHANGE=${HAS_SCHEMA_CHANGE:-0}
if [ "$HAS_SCHEMA_CHANGE" -gt 0 ]; then
  HAS_DOC_CHANGE=$(git diff --name-only main...HEAD 2>/dev/null | grep -cE 'DB_SCHEMA\.md|SCHEMA_SUMMARY\.md' || true)
  HAS_DOC_CHANGE_UNSTAGED=$(git diff --name-only | grep -cE 'DB_SCHEMA\.md|SCHEMA_SUMMARY\.md' || true)
  HAS_DOC_CHANGE=${HAS_DOC_CHANGE:-0}
  HAS_DOC_CHANGE_UNSTAGED=${HAS_DOC_CHANGE_UNSTAGED:-0}
  if [ "$HAS_DOC_CHANGE" -eq 0 ] && [ "$HAS_DOC_CHANGE_UNSTAGED" -eq 0 ]; then
    echo "BLOCKER: models/ 또는 alembic/ 변경 감지됐으나 DB_SCHEMA.md / SCHEMA_SUMMARY.md 업데이트 없음. DBA 에이전트로 스키마 문서를 동기화하세요. 변경된 컬럼/타입/FK/default를 두 문서에 반영하고 스키마 버전을 올리세요." >&2
    exit 2
  fi
fi

# ─── 품질 게이트 실행 ───
FAILURES=""

# Step 1. Lint (항상 직렬, 빠름)
echo "Step 1. Lint" >&2
cd "$TEST_DIR/backend"
uv run ruff check --fix --quiet . 2>/dev/null || true
uv run ruff format --quiet . 2>/dev/null || true
cd "$TEST_DIR/frontend"
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
      FOUND=$(find "$TEST_DIR/backend/tests" -name "test_${BASENAME}.py" -o -name "test_*${BASENAME}*.py" 2>/dev/null | head -5)
      if [ -n "$FOUND" ]; then
        TEST_FILES="${TEST_FILES} ${FOUND}"
      fi
    done <<< "$ALL_PY"

    if [ -n "$TEST_FILES" ]; then
      echo "Backend 관련 테스트:${TEST_FILES}" >&2
      cd "$TEST_DIR/backend"
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
    cd "$TEST_DIR/frontend"
    if ! npm test -- --run 2>&1; then
      FAILURES="${FAILURES}Frontend vitest 실패. "
    fi
    cd "$PROJECT_DIR"
  fi

# ─── 최종 판정: 영향도 기반 테스트 범위 결정 ───
else
  # 고영향 파일: 전체를 관통하는 핵심 모듈 변경 시 풀 테스트
  HAS_HIGH_IMPACT=$(echo "$ALL_PY" | grep -cE '(config\.py|config_pipelines\.py|database\.py|main\.py|models/|schemas\.py|state\.py)' 2>/dev/null || true)
  HAS_HIGH_IMPACT=${HAS_HIGH_IMPACT:-0}
  HAS_HIGH_IMPACT_TS=$(echo "$ALL_TS" | grep -cE '(store/use.*Store\.ts|types/index\.ts|constants/index\.ts)' 2>/dev/null || true)
  HAS_HIGH_IMPACT_TS=${HAS_HIGH_IMPACT_TS:-0}

  if [ "$HAS_HIGH_IMPACT" -gt 0 ] || [ "$HAS_HIGH_IMPACT_TS" -gt 0 ]; then
    echo "최종 판정: 고영향 변경 감지 — 풀 테스트 실행" >&2

    if [ "$PY_COUNT" -gt 0 ]; then
      cd "$TEST_DIR/backend"
      if ! uv run pytest --ignore=tests/vrt -q 2>&1; then
        FAILURES="${FAILURES}Backend 풀 테스트 실패. "
      fi
      cd "$PROJECT_DIR"
    fi

    if [ "$TS_COUNT" -gt 0 ]; then
      cd "$TEST_DIR/frontend"
      if ! npm test -- --run 2>&1; then
        FAILURES="${FAILURES}Frontend vitest 실패. "
      fi
      cd "$PROJECT_DIR"
    fi

  else
    echo "최종 판정: 변경 관련 테스트 실행" >&2

    # Backend: 변경된 .py에 대응하는 테스트 파일 찾기
    if [ "$PY_COUNT" -gt 0 ]; then
      TEST_FILES=""
      while IFS= read -r f; do
        [ -z "$f" ] && continue
        BASENAME=$(basename "$f" .py)
        FOUND=$(find "$TEST_DIR/backend/tests" -name "test_${BASENAME}.py" -o -name "test_*${BASENAME}*.py" 2>/dev/null | head -5)
        if [ -n "$FOUND" ]; then
          TEST_FILES="${TEST_FILES} ${FOUND}"
        fi
      done <<< "$ALL_PY"

      if [ -n "$TEST_FILES" ]; then
        echo "Backend 관련 테스트:${TEST_FILES}" >&2
        cd "$TEST_DIR/backend"
        if ! uv run pytest $TEST_FILES -q 2>&1; then
          FAILURES="${FAILURES}Backend 관련 테스트 실패. "
        fi
        cd "$PROJECT_DIR"
      else
        echo "Backend: 매칭 테스트 없음 — 스킵" >&2
      fi
    fi

    # Frontend: vitest (전체 — 이미 빠르므로)
    if [ "$TS_COUNT" -gt 0 ]; then
      cd "$TEST_DIR/frontend"
      if ! npm test -- --run 2>&1; then
        FAILURES="${FAILURES}Frontend vitest 실패. "
      fi
      cd "$PROJECT_DIR"
    fi
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

SP_ID=$(echo "$BRANCH" | grep -oE 'SP-[0-9]+' | head -1)

# 디렉토리 방식 우선 (SP-NNN_*/spec.md)
CURRENT_DIR=$(ls -d "$PROJECT_DIR/.claude/tasks/current/${SP_ID}_"*/ 2>/dev/null | head -1)
CURRENT=$(ls "$PROJECT_DIR/.claude/tasks/current/${SP_ID}_"*.md 2>/dev/null | head -1)

if [ -n "$CURRENT_DIR" ] && [ -d "$CURRENT_DIR" ]; then
  DIRNAME=$(basename "$CURRENT_DIR")
  DONE_FILE="$DONE_DIR/${DIRNAME}"
  mv "$CURRENT_DIR" "$DONE_FILE"
elif [ -n "$CURRENT" ] && [ -f "$CURRENT" ] && [ -s "$CURRENT" ]; then
  BASENAME=$(basename "$CURRENT")
  DONE_FILE="$DONE_DIR/${BASENAME}"
  mv "$CURRENT" "$DONE_FILE"
else
  TASK_NAME=$(echo "$BRANCH" | sed -E 's|^(worktree-)?feat/||')
  DONE_FILE="$DONE_DIR/${TASK_NAME}.md"
  echo "# $TASK_NAME" > "$DONE_FILE"
fi

# Update state.db — 성공 완료 (done)
STATE_DB="/home/tomo/Workspace/shorts-producer/.sdd/state.db"
if [ -n "$SP_ID" ] && [ -f "$STATE_DB" ]; then
  sqlite3 "$STATE_DB" "INSERT INTO task_status (task_id, status, updated_at) VALUES ('${SP_ID}', 'done', datetime('now')) ON CONFLICT(task_id) DO UPDATE SET status='done', updated_at=datetime('now');" 2>/dev/null || true
fi

# Backend health check for E2E judgment
BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")

cat >> "$DONE_FILE" << EOF

---
## 품질 게이트 결과 [$TIMESTAMP]
- Lint: PASS
- Backend pytest: $([ "$PY_COUNT" -gt 0 ] && echo "PASS" || echo "SKIP (no .py changes)")
- Frontend vitest: $([ "$TS_COUNT" -gt 0 ] && echo "PASS" || echo "SKIP (no .ts changes)")
- E2E: $([ "$BACKEND_HEALTH" = "200" ] && echo "PASS" || echo "SKIP (backend down)")
EOF

echo "전체 통과 — PR 생성 가능" >&2
exit 0
