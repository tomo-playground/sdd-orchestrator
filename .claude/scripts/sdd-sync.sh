#!/bin/bash
# SDD Post-Merge Sync: 머지된 PR 감지 → main pull + 브랜치 삭제 + 태스크 정리
# GitHub Actions sdd-sync.yml에서 호출 또는 수동 실행

set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/$(ls $HOME/.nvm/versions/node/ 2>/dev/null | tail -1)/bin:$PATH"

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# state.db 경로 (태스크 상태 SSOT)
STATE_DB="$PROJECT_DIR/.sdd/state.db"

# main 브랜치가 아니면 스킵
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if [ "$CURRENT_BRANCH" != "main" ]; then
  exit 0
fi

# 변경사항이 있으면 자동 stash
STASHED=false
if ! git diff --quiet 2>/dev/null || ! git diff --staged --quiet 2>/dev/null; then
  git stash --include-untracked -m "sdd-sync auto-stash" 2>/dev/null && STASHED=true
fi

# main 업데이트 (post-merge hook에서 호출 시 SKIP_PULL=1로 중복 pull 방지)
PULL_OK=true
if [ "${SKIP_PULL:-}" != "1" ]; then
  if ! git pull --ff-only 2>/dev/null; then
    git pull --rebase 2>/dev/null || {
      echo "⚠️ git pull 충돌 — rebase abort 후 정리 계속 진행"
      git rebase --abort 2>/dev/null || true
      PULL_OK=false
    }
  fi
fi

# current/에 있는 태스크의 브랜치와 머지된 PR을 매칭
# pull 실패 시에도 브랜치/워크트리 정리는 진행하되, 태스크 이동은 스킵
MERGED=""
if [ "$PULL_OK" = false ]; then
  echo "⚠️ pull 실패 — 태스크 이동 스킵, 브랜치/워크트리 정리만 진행"
fi
for TASK_FILE in "$PROJECT_DIR/.claude/tasks/current"/SP-*/spec.md "$PROJECT_DIR/.claude/tasks/current"/SP-*.md; do
  [ -f "$TASK_FILE" ] || continue
  TASK_BRANCH=$(grep -iE '^\*{0,2}-?\s*\*{0,2}branch\*{0,2}:' "$TASK_FILE" 2>/dev/null | sed -E 's/^.*branch\*{0,2}:\s*//' | tr -d '[:space:]' || true)
  # branch 필드 없으면 스킵 (퍼지 검색은 오탐 위험 — SP-111→SP-035 사고)
  if [ -z "$TASK_BRANCH" ]; then
    continue
  fi
  IS_MERGED=$(gh pr list --state merged --base main --head "$TASK_BRANCH" --json number --jq '.[0].number' 2>/dev/null || true)
  if [ -z "$IS_MERGED" ]; then
    IS_MERGED=$(gh pr list --state merged --base main --head "worktree-${TASK_BRANCH}" --json number --jq '.[0].number' 2>/dev/null || true)
  fi
  if [ -n "$IS_MERGED" ]; then
    MERGED="${MERGED} ${TASK_BRANCH}"
  fi
done
MERGED=$(echo "$MERGED" | xargs)

CHANGED=false
CHECKED_IDS=""

for BRANCH in $MERGED; do
  SP_ID=$(echo "$BRANCH" | sed -E 's#^(worktree-)?(feat|fix|chore|hotfix)/##' | grep -oE 'SP-[0-9]+' || true)
  if [ -z "$SP_ID" ]; then
    echo "⚠️ SP-ID 추출 실패, 브랜치 스킵: $BRANCH"
    continue
  fi
  DONE_DIR="$PROJECT_DIR/.claude/tasks/done"

  # 디렉토리 방식 (SP-NNN_*/) 먼저 시도 — pull 성공 시에만 이동
  CURRENT_DIR=$(ls -d "$PROJECT_DIR/.claude/tasks/current/${SP_ID}_"*/ 2>/dev/null | head -1)
  if [ "$PULL_OK" = true ] && [ -n "$CURRENT_DIR" ] && [ -d "$CURRENT_DIR" ]; then
    DIRNAME=$(basename "$CURRENT_DIR")
    # 미완료 DoD 추출 (머지 후 수동 작업 알림용)
    UNDONE=$(grep -E '^\- \[ \]' "$CURRENT_DIR/spec.md" 2>/dev/null | sed 's/^- \[ \] /  • /' || true)

    # Update task status in state.db (SSOT for status)
    if [ -f "$STATE_DB" ]; then
      sqlite3 "$STATE_DB" "INSERT INTO task_status (task_id, status, updated_at) VALUES ('${SP_ID}', 'done', datetime('now')) ON CONFLICT(task_id) DO UPDATE SET status='done', updated_at=datetime('now');"
    fi
    mv "$CURRENT_DIR" "$DONE_DIR/${DIRNAME}"
    echo "✅ ${DIRNAME}/ → done/"
    CHANGED=true

    # 미완료 DoD가 있으면 알림 파일에 기록 (오케스트레이터가 Slack 발송)
    if [ -n "$UNDONE" ]; then
      NOTIFY_FILE="/tmp/sdd-postmerge-${SP_ID}.notify"
      echo -e "📋 [${SP_ID}] 머지 완료 — 수동 작업 필요\n\n${UNDONE}" > "$NOTIFY_FILE"
      echo "📋 ${SP_ID} 미완료 DoD → $NOTIFY_FILE"
    fi
  else
    # 레거시 파일 방식 fallback (SP-NNN_*.md)
    CURRENT=$(ls "$PROJECT_DIR/.claude/tasks/current/${SP_ID}_"*.md 2>/dev/null | head -1)
    if [ "$PULL_OK" = true ] && [ -n "$CURRENT" ] && [ -f "$CURRENT" ]; then
      BASENAME=$(basename "$CURRENT")
      # Update task status in state.db (SSOT for status)
      if [ -f "$STATE_DB" ]; then
        sqlite3 "$STATE_DB" "INSERT INTO task_status (task_id, status, updated_at) VALUES ('${SP_ID}', 'done', datetime('now')) ON CONFLICT(task_id) DO UPDATE SET status='done', updated_at=datetime('now');"
      fi
      mv "$CURRENT" "$DONE_DIR/${BASENAME}"
      echo "✅ ${BASENAME} → done/"
      CHANGED=true
    fi
  fi

  # backlog.md에서 제거 (stash pop 후 재적용 필요 → ID를 수집해두고 나중에 처리)
  CHECKED_IDS="${CHECKED_IDS:-} ${SP_ID}"

  # 1. worktree 정리 (브랜치 삭제 전에 — worktree가 브랜치를 잡고 있으면 삭제 실패)
  #    SP-ID like 검색: SP-097 → SP-097, feat+SP-097-*, worktree-feat+SP-097-* 모두 매칭
  git worktree prune 2>/dev/null || true
  for WT_DIR in "$PROJECT_DIR/.claude/worktrees"/*"${SP_ID}"*; do
    [ -d "$WT_DIR" ] || continue
    if pgrep -af "claude" 2>/dev/null | grep -qF -- "${SP_ID}"; then
      echo "⚠️ worktree 스킵 (Claude 세션 실행 중): $WT_DIR"
    else
      git worktree remove "$WT_DIR" --force 2>/dev/null && echo "🗑️ worktree 삭제: $(basename "$WT_DIR")" || true
    fi
  done
  git worktree prune 2>/dev/null || true

  # 2. 원격 브랜치 삭제 (|| true — 실패해도 계속)
  git push origin --delete "$BRANCH" 2>/dev/null && echo "🗑️ 원격 브랜치 삭제: $BRANCH" || true
  git remote prune origin 2>/dev/null || true

  # 3. 로컬 브랜치 강제 삭제 — SP-ID like 검색으로 관련 브랜치 모두 정리
  git branch -D "$BRANCH" 2>/dev/null && echo "🗑️ 로컬 브랜치 삭제: $BRANCH" || true
  for STALE_BR in $(git branch --format='%(refname:short)' | grep -F "$SP_ID" || true); do
    [ "$STALE_BR" = "main" ] && continue
    git branch -D "$STALE_BR" 2>/dev/null && echo "🗑️ 로컬 브랜치 삭제: $STALE_BR" || true
  done
done

# ── 태스크 이동 커밋 (cleanup 전에 먼저 저장 — cleanup 실패해도 태스크 추적 유지) ──
if [ "$CHANGED" = true ] && ! git diff --quiet .claude/tasks/; then
  git add .claude/tasks/
  git commit -m "chore: 머지 완료 태스크 정리 → done/ 이동

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
  git push
  echo "📦 태스크 정리 커밋 완료"
fi

# ── 좀비 워크트리 정리 (done/에 있는데 워크트리가 남은 태스크) ──
# SP-* 뿐 아니라 feat+SP-*, worktree-SP-* 등 모든 SP-ID 포함 디렉토리 대상
for WT_DIR in "$PROJECT_DIR/.claude/worktrees"/*/; do
  [ -d "$WT_DIR" ] || continue
  ZID=$(basename "$WT_DIR" | grep -oE 'SP-[0-9]+' || true)
  [ -z "$ZID" ] && continue
  if ls "$PROJECT_DIR/.claude/tasks/done/${ZID}_"* >/dev/null 2>&1; then
    if pgrep -af "claude" 2>/dev/null | grep -qF -- "${ZID}"; then
      echo "⚠️ 좀비 스킵 (세션 실행 중): $WT_DIR"
    else
      git worktree remove "$WT_DIR" --force 2>/dev/null && echo "🧟 좀비 워크트리 삭제: $(basename "$WT_DIR")" || true
    fi
  fi
done

# ── PID-less 워크트리 일괄 정리 (SP-*, claude+issue-*, agent-*, 모든 패턴) ──
git worktree prune 2>/dev/null || true
for WT_DIR in "$PROJECT_DIR/.claude/worktrees"/*/; do
  [ -d "$WT_DIR" ] || continue
  WT_NAME=$(basename "$WT_DIR")

  # 실행 중인 claude 프로세스가 이 worktree를 사용 중인지 확인
  # grep -F (고정 문자열) — claude+issue-* 등의 regex 특수문자 안전 처리
  if pgrep -af "claude" 2>/dev/null | grep -qF -- "--worktree $WT_NAME"; then
    continue  # 프로세스 살아있음 → 스킵
  fi

  # 안전 체크: uncommitted 변경 확인
  if git -C "$WT_DIR" status --porcelain 2>/dev/null | grep -q .; then
    echo "⚠️ worktree 스킵 (uncommitted 변경): $WT_NAME"
    continue
  fi

  git worktree remove "$WT_DIR" --force 2>/dev/null && echo "🗑️ PID-less worktree 삭제: $WT_NAME" || true
done
# worktrees/ 내 빈 디렉토리 정리
find "$PROJECT_DIR/.claude/worktrees" -maxdepth 1 -type d -empty -delete 2>/dev/null || true
git worktree prune 2>/dev/null || true

# ── 머지/닫힌 PR의 stale 브랜치 정리 ──
for LOCAL_BR in $(git branch --format='%(refname:short)' | grep -E '^(feat/|fix/|worktree-)' || true); do
  # main, 현재 브랜치는 스킵
  [ "$LOCAL_BR" = "main" ] && continue
  # 원격에 존재하는지 확인
  REMOTE_EXISTS=$(git ls-remote --heads origin "$LOCAL_BR" 2>/dev/null | wc -l)
  if [ "$REMOTE_EXISTS" -eq 0 ]; then
    # 원격에 없는 로컬 브랜치 = 이미 삭제됨 → 로컬도 정리
    git branch -D "$LOCAL_BR" 2>/dev/null && echo "🗑️ stale 로컬 브랜치 삭제: $LOCAL_BR" || true
  else
    # 원격에 있지만 PR이 머지/닫힘 확인
    PR_STATE=$(gh pr list --state all --head "$LOCAL_BR" --json state --jq '.[0].state' 2>/dev/null || true)
    if [ "$PR_STATE" = "MERGED" ] || [ "$PR_STATE" = "CLOSED" ]; then
      git push origin --delete "$LOCAL_BR" 2>/dev/null && echo "🗑️ stale 원격 브랜치 삭제: $LOCAL_BR" || true
      git branch -D "$LOCAL_BR" 2>/dev/null && echo "🗑️ stale 로컬 브랜치 삭제: $LOCAL_BR" || true
    fi
  fi
done
git remote prune origin 2>/dev/null || true

# auto-stash 복원 (backlog.md 로컬 수정본 복원)
if [ "$STASHED" = true ]; then
  git stash pop 2>/dev/null && echo "📂 stash 복원 완료"
fi

# backlog.md에서 완료 태스크 제거 — stash pop 이후에 적용해야 덮어쓰기 방지
CHECKED_IDS=$(echo "${CHECKED_IDS:-}" | xargs)
if [ -n "$CHECKED_IDS" ]; then
  BACKLOG="$PROJECT_DIR/.claude/tasks/backlog.md"
  BACKLOG_CHANGED=false
  for SP_ID in $CHECKED_IDS; do
    if [ -f "$BACKLOG" ] && grep -q "^\- \[ \] ${SP_ID} " "$BACKLOG"; then
      sed -i "/^\- \[ \] ${SP_ID} /d" "$BACKLOG"
      echo "🗑️ backlog 제거: ${SP_ID}"
      BACKLOG_CHANGED=true
    fi
  done
  if [ "$BACKLOG_CHANGED" = true ]; then
    git add .claude/tasks/backlog.md
    git commit -m "chore: backlog 완료 태스크 제거 — $(echo $CHECKED_IDS | tr ' ' ',')

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
    git push
    echo "📦 backlog 업데이트 커밋 완료"
  fi
fi

# ── sdd-orchestrator 별도 레포 — feat 브랜치 + PR ──
ORCH_DIR="$PROJECT_DIR/sdd-orchestrator"
if [ -d "$ORCH_DIR/.git" ] && [ -n "$(git -C "$ORCH_DIR" status --porcelain 2>/dev/null)" ]; then
  ORCH_BRANCH="chore/sync-$(date '+%Y%m%d-%H%M')"
  ORCH_DIFF=$(git -C "$ORCH_DIR" diff --stat 2>/dev/null || true)
  if ! git -C "$ORCH_DIR" checkout -b "$ORCH_BRANCH" 2>/dev/null; then
    echo "sdd-orchestrator 브랜치 생성 실패: $ORCH_BRANCH"
    git -C "$ORCH_DIR" checkout main 2>/dev/null || true
  else
    git -C "$ORCH_DIR" add -A 2>/dev/null
    git -C "$ORCH_DIR" commit -m "chore: auto-commit from sdd-sync ($(date '+%Y-%m-%d %H:%M'))" 2>/dev/null || true
    if git -C "$ORCH_DIR" push -u origin "$ORCH_BRANCH" 2>/dev/null; then
      echo "sdd-orchestrator push: $ORCH_BRANCH"

      # PR 생성 (이미 존재하면 스킵)
      ORCH_PR_URL=$(gh pr create --repo tomo-playground/sdd-orchestrator \
        --base main --head "$ORCH_BRANCH" \
        --title "chore: auto-update from sdd-sync" \
        --body "## Summary
- sdd-sync post-merge에 의한 자동 변경

## Changes
\`\`\`
${ORCH_DIFF}
\`\`\`

Auto-generated by sdd-sync" 2>/dev/null || true)

      [ -n "$ORCH_PR_URL" ] && echo "sdd-orchestrator PR: $ORCH_PR_URL"
    else
      echo "sdd-orchestrator push 실패: $ORCH_BRANCH"
    fi

    # main으로 복귀
    git -C "$ORCH_DIR" checkout main 2>/dev/null || true
  fi
fi
