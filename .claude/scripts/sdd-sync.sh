#!/bin/bash
# SDD Post-Merge Sync: 머지된 PR 감지 → main pull + 브랜치 삭제 + 태스크 정리
# GitHub Actions sdd-sync.yml에서 호출 또는 수동 실행

set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/$(ls $HOME/.nvm/versions/node/ 2>/dev/null | tail -1)/bin:$PATH"

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

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

# main 업데이트 (ff-only 실패 시 rebase fallback)
if ! git pull --ff-only 2>/dev/null; then
  git pull --rebase 2>/dev/null || {
    echo "⚠️ git pull 실패 — main 동기화 불가"
    [ "$STASHED" = true ] && git stash pop 2>/dev/null
    exit 1
  }
fi

# current/에 있는 태스크의 브랜치와 머지된 PR을 매칭
# 디렉토리 방식 (SP-NNN_*/spec.md) + 레거시 (SP-NNN_*.md) 모두 탐색
MERGED=""
for TASK_FILE in "$PROJECT_DIR/.claude/tasks/current"/SP-*/spec.md "$PROJECT_DIR/.claude/tasks/current"/SP-*.md; do
  [ -f "$TASK_FILE" ] || continue
  TASK_BRANCH=$(grep '^branch:' "$TASK_FILE" | sed 's/^branch: *//' | tr -d '[:space:]')
  [ -z "$TASK_BRANCH" ] && continue
  IS_MERGED=$(gh pr list --state merged --base main --head "$TASK_BRANCH" --json number --jq '.[0].number' 2>/dev/null || true)
  if [ -z "$IS_MERGED" ]; then
    IS_MERGED=$(gh pr list --state merged --base main --head "worktree-${TASK_BRANCH}" --json number --jq '.[0].number' 2>/dev/null || true)
  fi
  if [ -n "$IS_MERGED" ]; then
    MERGED="${MERGED} ${TASK_BRANCH}"
  fi
done
MERGED=$(echo "$MERGED" | xargs)

[ -z "$MERGED" ] && { [ "$STASHED" = true ] && git stash pop 2>/dev/null; exit 0; }

CHANGED=false
CHECKED_IDS=""

for BRANCH in $MERGED; do
  SP_ID=$(echo "$BRANCH" | sed -E 's#^(worktree-)?(feat|fix|chore|hotfix)/##' | grep -oE 'SP-[0-9]+' || true)
  if [ -z "$SP_ID" ]; then
    echo "⚠️ SP-ID 추출 실패, 브랜치 스킵: $BRANCH"
    continue
  fi
  DONE_DIR="$PROJECT_DIR/.claude/tasks/done"

  # 디렉토리 방식 (SP-NNN_*/) 먼저 시도
  CURRENT_DIR=$(ls -d "$PROJECT_DIR/.claude/tasks/current/${SP_ID}_"*/ 2>/dev/null | head -1)
  if [ -n "$CURRENT_DIR" ] && [ -d "$CURRENT_DIR" ]; then
    DIRNAME=$(basename "$CURRENT_DIR")
    sed -i 's/^status:.*/status: done/' "$CURRENT_DIR/spec.md"
    mv "$CURRENT_DIR" "$DONE_DIR/${DIRNAME}"
    echo "✅ ${DIRNAME}/ → done/"
    CHANGED=true
  else
    # 레거시 파일 방식 fallback (SP-NNN_*.md)
    CURRENT=$(ls "$PROJECT_DIR/.claude/tasks/current/${SP_ID}_"*.md 2>/dev/null | head -1)
    if [ -n "$CURRENT" ] && [ -f "$CURRENT" ]; then
      BASENAME=$(basename "$CURRENT")
      sed -i 's/^status:.*/status: done/' "$CURRENT"
      mv "$CURRENT" "$DONE_DIR/${BASENAME}"
      echo "✅ ${BASENAME} → done/"
      CHANGED=true
    fi
  fi

  # backlog.md 체크오프 (stash pop 후 재적용 필요 → ID를 수집해두고 나중에 처리)
  CHECKED_IDS="${CHECKED_IDS:-} ${SP_ID}"

  # 1. worktree 정리 (브랜치 삭제 전에 — worktree가 브랜치를 잡고 있으면 삭제 실패)
  git worktree prune 2>/dev/null || true
  for WT_DIR in "$PROJECT_DIR/.claude/worktrees/${BRANCH}" "$PROJECT_DIR/.claude/worktrees/${SP_ID}"; do
    [ -d "$WT_DIR" ] || continue
    if pgrep -f "worktree.*${SP_ID}\|worktree.*${BRANCH}" > /dev/null 2>&1; then
      echo "⚠️ worktree 스킵 (Claude 세션 실행 중): $WT_DIR"
    else
      git worktree remove "$WT_DIR" --force 2>/dev/null && echo "🗑️ worktree 삭제: $WT_DIR" || true
    fi
  done
  git worktree prune 2>/dev/null || true

  # 2. 원격 브랜치 삭제 (|| true — 실패해도 계속)
  git push origin --delete "$BRANCH" 2>/dev/null && echo "🗑️ 원격 브랜치 삭제: $BRANCH" || true
  git remote prune origin 2>/dev/null || true

  # 3. 로컬 브랜치 강제 삭제 (|| true — 실패해도 계속)
  git branch -D "$BRANCH" 2>/dev/null && echo "🗑️ 로컬 브랜치 삭제: $BRANCH" || true
  git branch -D "worktree-${BRANCH}" 2>/dev/null || true
  git branch -D "worktree-${SP_ID}" 2>/dev/null || true
done

# ── 좀비 워크트리 정리 (done/에 있는데 워크트리가 남은 태스크) ──
for WT_DIR in "$PROJECT_DIR/.claude/worktrees"/SP-*; do
  [ -d "$WT_DIR" ] || continue
  ZID=$(basename "$WT_DIR" | grep -oE 'SP-[0-9]+' || true)
  [ -z "$ZID" ] && continue
  if ls "$PROJECT_DIR/.claude/tasks/done/${ZID}_"* >/dev/null 2>&1; then
    if pgrep -f "worktree.*${ZID}" > /dev/null 2>&1; then
      echo "⚠️ 좀비 스킵 (세션 실행 중): $WT_DIR"
    else
      git worktree remove "$WT_DIR" --force 2>/dev/null && echo "🧟 좀비 워크트리 삭제: $(basename "$WT_DIR")" || true
    fi
  fi
done

# ── 고아 워크트리 정리 (agent-*, silly-*, stale) ──
git worktree prune 2>/dev/null || true
for ORPHAN_DIR in "$PROJECT_DIR/.claude/worktrees"/agent-* "$PROJECT_DIR/.claude/worktrees"/silly-*; do
  [ -d "$ORPHAN_DIR" ] || continue
  git worktree remove "$ORPHAN_DIR" --force 2>/dev/null && echo "🗑️ 고아 worktree 삭제: $(basename "$ORPHAN_DIR")" || true
done
# worktrees/ 내 빈 디렉토리 정리
find "$PROJECT_DIR/.claude/worktrees" -maxdepth 1 -type d -empty -delete 2>/dev/null || true
git worktree prune 2>/dev/null || true

# ── 머지/닫힌 PR의 stale 브랜치 정리 ──
for LOCAL_BR in $(git branch --format='%(refname:short)' | grep -E '^(feat/|fix/|worktree-)'); do
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

# 변경사항 커밋 + 푸시 (current/ → done/ 이동분)
if [ "$CHANGED" = true ] && ! git diff --quiet .claude/tasks/; then
  git add .claude/tasks/
  git commit -m "chore: 머지 완료 태스크 정리 → done/ 이동

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
  git push
  echo "📦 태스크 정리 커밋 완료"
fi

# auto-stash 복원 (backlog.md 로컬 수정본 복원)
if [ "$STASHED" = true ]; then
  git stash pop 2>/dev/null && echo "📂 stash 복원 완료"
fi

# backlog.md 체크오프 — stash pop 이후에 적용해야 덮어쓰기 방지
CHECKED_IDS=$(echo "${CHECKED_IDS:-}" | xargs)
if [ -n "$CHECKED_IDS" ]; then
  BACKLOG="$PROJECT_DIR/.claude/tasks/backlog.md"
  BACKLOG_CHANGED=false
  for SP_ID in $CHECKED_IDS; do
    if [ -f "$BACKLOG" ] && grep -q "^\- \[ \] ${SP_ID} " "$BACKLOG"; then
      sed -i "s/^- \[ \] ${SP_ID} \(—\||\)/- [x] ~~${SP_ID}~~ \1/" "$BACKLOG"
      echo "☑️ backlog 체크: ${SP_ID}"
      BACKLOG_CHANGED=true
    fi
  done
  if [ "$BACKLOG_CHANGED" = true ]; then
    git add .claude/tasks/backlog.md
    git commit -m "chore: backlog 완료 체크 — $(echo $CHECKED_IDS | tr ' ' ',')

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
    git push
    echo "📦 backlog 업데이트 커밋 완료"
  fi
fi
