#!/bin/bash
# SDD Post-Merge Sync: 머지된 PR 감지 → main pull + 브랜치 삭제 + 태스크 정리
# 사용: sdd-sync (수동) 또는 cron (자동 5분 간격)

set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/$(ls $HOME/.nvm/versions/node/ 2>/dev/null | tail -1)/bin:$PATH"

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# main 브랜치가 아니면 스킵
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if [ "$CURRENT_BRANCH" != "main" ]; then
  exit 0
fi

# 변경사항이 있으면 자동 stash (이전: 스킵 → 사용자 혼란)
STASHED=false
if ! git diff --quiet 2>/dev/null || ! git diff --staged --quiet 2>/dev/null; then
  git stash --include-untracked -m "sdd-sync auto-stash" 2>/dev/null && STASHED=true
fi

# main 업데이트
git pull --ff-only 2>/dev/null || exit 0

# 최근 1시간 내 머지된 PR의 브랜치 목록
# current/에 있는 태스크의 브랜치와 머지된 PR을 매칭
MERGED=""
for TASK_FILE in "$PROJECT_DIR/.claude/tasks/current"/SP-*.md; do
  [ -f "$TASK_FILE" ] || continue
  TASK_BRANCH=$(grep '^branch:' "$TASK_FILE" | sed 's/^branch: *//' | tr -d '[:space:]')
  [ -z "$TASK_BRANCH" ] && continue
  # 이 브랜치가 머지됐는지 확인 (worktree- prefix도 매칭)
  IS_MERGED=$(gh pr list --state merged --base main --head "$TASK_BRANCH" --json number --jq '.[0].number' 2>/dev/null || true)
  if [ -z "$IS_MERGED" ]; then
    IS_MERGED=$(gh pr list --state merged --base main --head "worktree-${TASK_BRANCH}" --json number --jq '.[0].number' 2>/dev/null || true)
  fi
  if [ -n "$IS_MERGED" ]; then
    MERGED="${MERGED} ${TASK_BRANCH}"
  fi
done
MERGED=$(echo "$MERGED" | xargs)

[ -z "$MERGED" ] && exit 0

CHANGED=false

for BRANCH in $MERGED; do
  SP_ID=$(echo "$BRANCH" | sed -E 's|^(worktree-)?feat/||' | grep -oE '^SP-[0-9]+')
  CURRENT=$(ls "$PROJECT_DIR/.claude/tasks/current/${SP_ID}_"*.md 2>/dev/null | head -1)
  DONE_DIR="$PROJECT_DIR/.claude/tasks/done"

  if [ -n "$CURRENT" ] && [ -f "$CURRENT" ]; then
    BASENAME=$(basename "$CURRENT")
    sed -i 's/^status:.*/status: done/' "$CURRENT"
    mv "$CURRENT" "$DONE_DIR/${BASENAME}"
    echo "✅ ${BASENAME} → done/"
    CHANGED=true
  fi

  # 원격 브랜치 삭제 → prune → 로컬 강제 삭제
  git push origin --delete "$BRANCH" 2>/dev/null && echo "🗑️ 원격 브랜치 삭제: $BRANCH"
  git remote prune origin 2>/dev/null || true
  git branch -D "$BRANCH" 2>/dev/null && echo "🗑️ 로컬 브랜치 삭제: $BRANCH"
  # worktree- prefix 로컬 브랜치도 정리
  git branch -D "worktree-${BRANCH}" 2>/dev/null
  git branch -D "worktree-${SP_ID}" 2>/dev/null

  # worktree 정리 (git worktree remove → 깔끔한 제거)
  WORKTREE_DIR="$PROJECT_DIR/.claude/worktrees/${BRANCH}"
  if [ -d "$WORKTREE_DIR" ]; then
    git worktree remove "$WORKTREE_DIR" --force 2>/dev/null && echo "🗑️ worktree 삭제: $WORKTREE_DIR"
  fi
  # SP-009 같은 짧은 이름 worktree도 정리
  SHORT_WORKTREE="$PROJECT_DIR/.claude/worktrees/${SP_ID}"
  if [ -d "$SHORT_WORKTREE" ]; then
    git worktree remove "$SHORT_WORKTREE" --force 2>/dev/null && echo "🗑️ worktree 삭제: $SHORT_WORKTREE"
  fi
done

# 고아 worktree 정리 (prunable 상태 제거)
git worktree prune 2>/dev/null

# 변경사항 커밋 + 푸시
if [ "$CHANGED" = true ] && ! git diff --quiet .claude/tasks/; then
  git add .claude/tasks/
  git commit -m "chore: 머지 완료 태스크 정리 → done/ 이동

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
  git push
  echo "📦 태스크 정리 커밋 완료"
fi

# auto-stash 복원
if [ "$STASHED" = true ]; then
  git stash pop 2>/dev/null && echo "📂 stash 복원 완료"
fi
