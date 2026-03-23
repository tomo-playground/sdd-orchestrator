# SDD + TDD 구축 가이드

> 새 프로젝트에서 SDD + TDD 방법론을 처음부터 세팅하는 단계별 가이드.
> 사람이 스펙과 실패 테스트를 쓰면, AI가 테스트를 GREEN으로 만들고 PR까지 자율 실행.
> **"AI를 믿지 말고, 테스트를 믿어라."**
> 최종 업데이트: 2026-03-21

---

## 1. 전제 조건

### 필수 도구

| 도구 | 용도 | 설치 |
|------|------|------|
| Claude Code CLI | AI 자율 구현 엔진 | `npm install -g @anthropic-ai/claude-code` |
| GitHub CLI (gh) | PR/Issue/Actions 제어 | `brew install gh` or `apt install gh` |
| Git | 버전 관리 + worktree | 기본 설치 |
| CodeRabbit | 독립 AI 리뷰어 | GitHub App 설치 (선택) |

### 인증 설정

```bash
# Claude Code 인증 (구독 플랜 — Pro/Max)
claude setup-token
# → 브라우저 인증 → 토큰 발급
# → GitHub Secrets에 CLAUDE_CODE_OAUTH_TOKEN으로 등록

# GitHub CLI 인증
gh auth login
```

---

## 2. 디렉토리 구조 생성

```bash
mkdir -p .claude/tasks/current
mkdir -p .claude/tasks/done
mkdir -p .claude/scripts
mkdir -p .claude/hooks
mkdir -p .claude/commands
mkdir -p .claude/worktrees
```

```
.claude/
├── tasks/
│   ├── _template.md          # 태스크 작성 템플릿
│   ├── backlog.md            # 실행 대기 큐 (우선순위 순)
│   ├── current/              # 활성 태스크 (8개 이하)
│   └── done/                 # 완료 이력
├── commands/                 # 슬래시 커맨드 정의
│   ├── sdd-run.md
│   ├── sdd-sync.md
│   └── sdd-review.md
├── scripts/
│   └── sdd-sync.sh           # 머지 후 정리 스크립트
├── hooks/
│   ├── auto-lint.sh           # PostToolUse: 자동 린트
│   └── on-stop.sh             # Stop: 품질 게이트
├── worktrees/                 # 워크트리 작업 디렉토리 (자동)
└── settings.json              # Hook 설정
```

---

## 3. 핵심 파일 작성

### 3-1. 태스크 템플릿

```bash
cat > .claude/tasks/_template.md << 'EOF'
---
id: SP-NNN
priority:              # P0 / P1 / P2 / P3
scope:                 # backend / frontend / fullstack / infra
branch: feat/SP-NNN-설명
created:               # YYYY-MM-DD
status: pending        # pending → running → done
depends_on:
---

## 무엇을
[한 줄 설명]

## 왜
[이유/배경]

## 완료 기준 (DoD)
- [ ] 핵심 기능 동작
- [ ] 테스트 통과
- [ ] 기존 기능 regression 없음

## 제약
- 변경 파일 10개 이하 목표
EOF
```

**태스크 관리 원칙**:
- 태스크 파일은 **착수 직전에 생성** (미리 만들어두면 코드 변경으로 낡음)
- backlog.md 한 줄이 SSOT, 태스크 파일은 실행 계약서
- current/는 **8개 이하** 유지. 대형 피처는 backlog에만 기록

### 3-2. Backlog

```bash
cat > .claude/tasks/backlog.md << 'EOF'
# Backlog

> 실행 가능한 태스크 큐. 우선순위 순서대로 진행.

---

## P0 (긴급)

## P1 (최우선)

## P2 (기능 확장)

## P3 (인프라/자동화)
EOF
```

### 3-3. CLAUDE.md (프로젝트 규칙)

프로젝트 루트에 `CLAUDE.md`를 만든다. AI 에이전트가 참조하는 SSOT 규칙 문서.

필수 섹션:
- **아키텍처**: 레이어, 기술 스택, 디렉토리 구조
- **코드 규칙**: 파일 크기, 네이밍, 모듈화 원칙
- **커밋 경로 규칙**: main 직접 허용 범위 vs feat 브랜치 필수 범위
- **SDD 자율 실행 워크플로우**: 세션 부팅/종료 프로토콜, 자율 범위, 즉시 중단 조건
- **용어 정의**: 혼용 금지 용어 사전

---

## 4. Hook 설정

### 4-1. 자동 린트 (PostToolUse)

```bash
cat > .claude/hooks/auto-lint.sh << 'SCRIPT'
#!/bin/bash
# Edit/Write 후 자동 린트
FILE="$CLAUDE_FILE_PATH"
[[ -z "$FILE" || ! -f "$FILE" ]] && exit 0

case "$FILE" in
  *.py)  ruff check --fix "$FILE" 2>/dev/null; ruff format "$FILE" 2>/dev/null ;;
  *.ts|*.tsx) npx prettier --write "$FILE" 2>/dev/null ;;
esac
exit 0
SCRIPT
chmod +x .claude/hooks/auto-lint.sh
```

### 4-2. 품질 게이트 (Stop Hook)

```bash
cat > .claude/hooks/on-stop.sh << 'SCRIPT'
#!/bin/bash
# 5단계 품질 게이트 + self-heal (최대 3회)
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

# self-heal 카운터 (3회 초과 시 통과)
COUNTER_FILE="/tmp/sdd_stop_hook_counter_$$"
COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo "0")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"
if [ "$COUNT" -gt 3 ]; then
  rm -f "$COUNTER_FILE"
  exit 0
fi

FAILED=false

# Step 1: Lint
if ls "$PROJECT_DIR"/backend/*.py &>/dev/null; then
  ruff check "$PROJECT_DIR/backend/" 2>&1 || FAILED=true
fi

# Step 2: Backend 테스트
if [ -d "$PROJECT_DIR/backend/tests" ]; then
  cd "$PROJECT_DIR/backend" && python -m pytest tests/ -x -q 2>&1 || FAILED=true
fi

# Step 3: Frontend 테스트
if [ -f "$PROJECT_DIR/frontend/package.json" ]; then
  cd "$PROJECT_DIR/frontend" && npx vitest run --reporter=verbose 2>&1 || FAILED=true
fi

if [ "$FAILED" = true ]; then
  exit 2  # Claude에게 에러 전달 → self-heal 시도
fi

rm -f "$COUNTER_FILE"
exit 0
SCRIPT
chmod +x .claude/hooks/on-stop.sh
```

### 4-3. settings.json

```bash
cat > .claude/settings.json << 'EOF'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/auto-lint.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/on-stop.sh"
          }
        ]
      }
    ]
  }
}
EOF
```

---

## 5. 슬래시 커맨드 정의

### 5-1. /sdd-run

```bash
cat > .claude/commands/sdd-run.md << 'EOF'
# /sdd-run $ARGUMENTS

태스크를 워크트리에서 자율 실행합니다.

## 실행 순서
1. `$ARGUMENTS`에서 SP-NNN 추출
2. `.claude/tasks/current/SP-NNN_*/spec.md` 매칭 (fallback: `SP-NNN_*.md`)
3. worktree 생성 + feat 브랜치
4. 태스크 읽기 → 구현 → 테스트 → 커밋 → PR 생성
5. 셀프 리뷰 실행

## 자율 규칙
- 사용자 확인 금지 — PR 생성까지 끝까지 진행
- 즉시 중단: DB 스키마 변경, 외부 의존성 추가
EOF
```

### 5-2. /sdd-sync

```bash
cat > .claude/commands/sdd-sync.md << 'EOF'
# /sdd-sync

머지 완료된 태스크를 정리합니다.

## 실행
```bash
bash .claude/scripts/sdd-sync.sh
```

## 동작
1. git pull (main 최신화)
2. current/ 태스크 중 머지된 PR 감지
3. 태스크 → done/ 이동
4. 브랜치/워크트리 삭제
5. 자동 커밋 + 푸시
EOF
```

---

## 6. GitHub Actions 설정

### 6-1. 머지 후 자동 정리 (sdd-sync)

```bash
cat > .github/workflows/sdd-sync.yml << 'EOF'
name: SDD Sync

on:
  pull_request:
    types: [closed]
    branches: [main]

permissions:
  contents: write
  pull-requests: write

concurrency:
  group: sdd-sync
  cancel-in-progress: false

jobs:
  cleanup:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest  # 또는 [self-hosted, sdd]
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
          fetch-depth: 0
      - run: bash .claude/scripts/sdd-sync.sh
EOF
```

### 6-2. PR 자동 리뷰 — Claude (sdd-review.yml)

PR 생성/push마다 Claude가 CLAUDE.md 기준으로 **리뷰만** 합니다 (코드 수정 안 함).
CodeRabbit과 병렬 동작.

```bash
cat > .github/workflows/sdd-review.yml << 'EOF'
name: SDD Review — PR 자동 리뷰

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write
  issues: write
  id-token: write
  actions: read

concurrency:
  group: claude-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  review:
    runs-on: ubuntu-latest  # self-hosted: [self-hosted, sdd]
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: anthropics/claude-code-action@v1
        with:
          # 구독 플랜:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          # API 플랜:
          # anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          track_progress: true

          prompt: |
            REPO: ${{ github.repository }}
            PR NUMBER: ${{ github.event.pull_request.number }}
            CLAUDE.md를 읽고 프로젝트 규칙 기준으로 리뷰하세요.
            리뷰만 하세요. 코드 수정은 하지 마세요.

          claude_args: |
            --allowedTools "mcp__github_inline_comment__create_inline_comment,Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*),Bash(gh api:*),Read,Glob,Grep"
EOF
```

### 6-3. 리뷰 자동 수정 — Claude (sdd-fix.yml)

CodeRabbit/Claude 리뷰에서 `changes_requested` 시 Claude가 **자동으로 코드 수정**.
추가로 `@claude` 멘션으로 수동 요청도 가능.

```bash
cat > .github/workflows/sdd-fix.yml << 'EOF'
name: SDD Fix — 리뷰 자동 수정 + @claude 수동 대응

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  pull_request_review:
    types: [submitted]

permissions:
  contents: write
  pull-requests: write
  issues: write
  id-token: write
  actions: read

concurrency:
  group: sdd-review-${{ github.event.issue.number || github.event.pull_request.number }}
  cancel-in-progress: false  # true면 봇 코멘트가 원본 run을 취소함

jobs:
  # Job 1: CodeRabbit/Claude 리뷰 → 자동 수정
  auto-fix:
    if: |
      (
        github.event_name == 'pull_request_review' &&
        github.event.review.state == 'changes_requested' &&
        (github.event.review.user.login == 'coderabbitai[bot]' || github.event.review.user.login == 'claude[bot]')
      ) ||
      (
        github.event_name == 'pull_request_review_comment' &&
        (github.event.comment.user.login == 'coderabbitai[bot]' || github.event.comment.user.login == 'claude[bot]')
      )
    runs-on: ubuntu-latest  # self-hosted: [self-hosted, sdd]
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: anthropics/claude-code-action@v1
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          track_progress: true
          prompt: |
            REPO: ${{ github.repository }}
            PR NUMBER: ${{ github.event.pull_request.number }}
            리뷰 코멘트를 읽고 코드를 수정하세요.
            버그 → 수정+커밋+push. 스타일 → 스킵.

          claude_args: |
            --allowedTools "mcp__github_inline_comment__create_inline_comment,Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*),Bash(gh api:*),Bash(git:*),Read,Edit,Write,Glob,Grep"

  # Job 2: @claude 멘션 → 수동 대응
  manual:
    if: |
      !endsWith(github.event.comment.user.login || '', '[bot]') &&
      (
        (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@claude')) ||
        (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@claude')) ||
        (github.event_name == 'pull_request_review' && contains(github.event.review.body, '@claude'))
      )
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: anthropics/claude-code-action@v1
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          trigger_phrase: "@claude"
          track_progress: true
          claude_args: |
            --allowedTools "mcp__github_inline_comment__create_inline_comment,Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*),Bash(gh api:*),Bash(git:*),Read,Edit,Write,Glob,Grep"
EOF
```

### 전체 흐름도

```
PR push
  ├─ Claude 리뷰 (sdd-review.yml) — 리뷰만, 수정 안 함
  └─ CodeRabbit 리뷰 (자동)          — 리뷰만
        ↓
    둘 중 하나라도 changes_requested
        ↓
    Claude 자동 수정 (sdd-fix.yml auto-fix) → push
        ↓
    CodeRabbit + Claude 재리뷰
        ↓
    사람이 머지 판단

    추가: @claude 멘션으로 수동 요청 가능 (sdd-fix.yml manual)

별도 루프: Sentry 에러 → GitHub Issue → 태스크 → 수정
    sentry-patrol (매일 cron) → Sentry 에러 감지 → GitHub Issue 자동 생성
    → 사람이 Issue → 태스크 전환 → /sdd-run → 버그 수정 PR
```

---

## 7. sdd-sync.sh 스크립트

```bash
cat > .claude/scripts/sdd-sync.sh << 'SCRIPT'
#!/bin/bash
# SDD Post-Merge Sync: 머지된 PR 감지 → 태스크 정리 + 브랜치 삭제
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
[ "$CURRENT_BRANCH" != "main" ] && exit 0

# main 업데이트
git pull --ff-only 2>/dev/null || git pull --rebase 2>/dev/null || exit 1

# 머지된 PR 매칭
MERGED=""
for TASK_FILE in "$PROJECT_DIR/.claude/tasks/current"/SP-*/spec.md "$PROJECT_DIR/.claude/tasks/current"/SP-*.md; do
  [ -f "$TASK_FILE" ] || continue
  TASK_BRANCH=$(grep '^branch:' "$TASK_FILE" | sed 's/^branch: *//' | tr -d '[:space:]')
  [ -z "$TASK_BRANCH" ] && continue
  IS_MERGED=$(gh pr list --state merged --base main --head "$TASK_BRANCH" \
    --json number --jq '.[0].number' 2>/dev/null || true)
  [ -n "$IS_MERGED" ] && MERGED="${MERGED} ${TASK_BRANCH}"
done
MERGED=$(echo "$MERGED" | xargs)

[ -z "$MERGED" ] && exit 0

CHANGED=false
for BRANCH in $MERGED; do
  SP_ID=$(echo "$BRANCH" | sed -E 's#^(worktree-)?(feat|fix|chore|hotfix)/##' \
    | grep -oE 'SP-[0-9]+' || true)
  [ -z "$SP_ID" ] && continue

  CURRENT=$(ls "$PROJECT_DIR/.claude/tasks/current/${SP_ID}_"*.md 2>/dev/null | head -1)
  if [ -n "$CURRENT" ] && [ -f "$CURRENT" ]; then
    sed -i 's/^status:.*/status: done/' "$CURRENT"
    mv "$CURRENT" "$PROJECT_DIR/.claude/tasks/done/$(basename "$CURRENT")"
    CHANGED=true
  fi

  # 브랜치/워크트리 정리
  git worktree prune 2>/dev/null || true
  git push origin --delete "$BRANCH" 2>/dev/null || true
  git branch -D "$BRANCH" 2>/dev/null || true
done

# 커밋 + 푸시
if [ "$CHANGED" = true ] && ! git diff --quiet .claude/tasks/; then
  git add .claude/tasks/
  git commit -m "chore: 머지 완료 태스크 정리"
  git push
fi
SCRIPT
chmod +x .claude/scripts/sdd-sync.sh
```

---

## 8. 실행 플로우 (SDD + TDD)

```
[사람] backlog에 한 줄 등록
  ↓
[사람] 착수 결정 → 태스크 파일 + 실패 테스트 작성 (RED)
  ↓
[사람] pytest/vitest 실행 → FAIL 확인 → main 커밋
  ↓
[사람] /sdd-run SP-NNN → 워크트리 기동
  ↓
[AI] 실패 테스트를 GREEN으로 만드는 코드 작성 → Stop Hook 자동 검증
  ↓  RED → self-heal (최대 3회)
  ↓  ALL GREEN → 커밋 → push → PR 생성
  ↓
[병렬 리뷰]
  ├─ Claude 리뷰 — 설계 품질 검증
  └─ CodeRabbit 리뷰 — 규칙 준수 검증
  ↓
[changes_requested 시]
  ↓
[Claude 자동 수정] → push → 재리뷰
  ↓
[사람] 머지 판단
  ↓
[GitHub Actions] sdd-sync → 태스크 done/ + 브랜치 삭제
```

> **핵심**: 사람은 "무엇을 만들지"(테스트)만 정의. AI는 "어떻게 만들지"(구현)를 자율 결정.
> 테스트가 곧 스펙이고, GREEN이 곧 완료.

---

## 9. 교훈 & 안티패턴

### 해야 할 것

| 원칙 | 이유 |
|------|------|
| 태스크 파일은 착수 직전에 작성 | 미리 쓰면 코드 변경으로 낡음 |
| current/는 8개 이하 유지 | 뭐가 진행 중인지 파악 불가 |
| 인프라 변경 시 SSE/WebSocket 검증 | 프록시 도입 등으로 long-poll이 깨질 수 있음 |
| 회고 교훈은 Hook/CLAUDE.md에 하드코딩 | memory에만 두면 반복됨 |
| sdd-sync 스크립트 방어적 작성 | `set -e` + 방어 없는 grep → 한 패턴 미스에 전체 크래시 |
| 버그 수정 시 재현 먼저 | 추측 패치 → 부작용 → 또 패치 반복 |

### 하지 말 것

| 안티패턴 | 결과 |
|----------|------|
| 태스크 파일 미리 15개 생성 | 관리 부채, "뭐가 진행 중?" 혼란 |
| main에 직접 코드 커밋 | SDD 프로세스 이탈, 리뷰 누락 |
| 모든 코멘트에 자동 수정 트리거 | 봇 핑퐁, timeout 폭발 |
| `--dangerously-skip-permissions` | 보안 위험, allowedTools로 대체 |
| 회고만 하고 코드에 반영 안 함 | 같은 실수 반복 |

---

## 10. 체크리스트: 신규 프로젝트 SDD 세팅

```
[ ] 1. Claude Code CLI 설치 + 인증 (setup-token)
[ ] 2. gh CLI 인증
[ ] 3. .claude/ 디렉토리 구조 생성
[ ] 4. _template.md, backlog.md 작성
[ ] 5. CLAUDE.md 작성 (아키텍처, 코드 규칙, SDD 워크플로우)
[ ] 6. auto-lint.sh + on-stop.sh Hook 작성
[ ] 7. settings.json Hook 등록
[ ] 8. sdd-sync.sh 스크립트 작성
[ ] 9. 슬래시 커맨드 정의 (sdd-run, sdd-sync)
[ ] 10. GitHub Secrets 등록 (CLAUDE_CODE_OAUTH_TOKEN)
[ ] 11. GitHub Actions 워크플로우 배포 (sdd-sync, claude-review)
[ ] 12. CodeRabbit 설치 (선택)
[ ] 13. 첫 태스크 작성 → /sdd-run으로 검증
```
