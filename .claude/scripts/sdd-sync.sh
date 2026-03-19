#!/bin/bash
# SDD Post-Merge Sync: 머지된 PR 감지 → main pull + 브랜치 삭제 + 태스크 정리
# 사용: sdd-sync (수동) 또는 cron (자동 5분 간격)

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# main 브랜치가 아니면 스킵
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if [ "$CURRENT_BRANCH" != "main" ]; then
  exit 0
fi

# 변경사항이 있으면 스킵 (작업 중)
if ! git diff --quiet 2>/dev/null || ! git diff --staged --quiet 2>/dev/null; then
  exit 0
fi

# main 업데이트
git pull --ff-only 2>/dev/null || exit 0

# 최근 1시간 내 머지된 PR의 브랜치 목록
MERGED=$(gh pr list --state merged --base main \
  --json headRefName,mergedAt \
  --jq '[.[] | select(.mergedAt > (now - 3600 | todate))] | .[].headRefName' 2>/dev/null || true)

[ -z "$MERGED" ] && exit 0

CHANGED=false

for BRANCH in $MERGED; do
  TASK=$(echo "$BRANCH" | sed -E 's|^(worktree-)?feat/||')
  CURRENT="$PROJECT_DIR/.claude/tasks/current/${TASK}.md"
  DONE_DIR="$PROJECT_DIR/.claude/tasks/done"

  if [ -f "$CURRENT" ]; then
    # done/ 번호 채번
    LAST=$(ls "$DONE_DIR" 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -1 || echo "0")
    NEXT=$(printf "%03d" $((10#${LAST:-0} + 1)))

    # status 업데이트 + 이동
    sed -i 's/^status:.*/status: done/' "$CURRENT"
    mv "$CURRENT" "$DONE_DIR/${NEXT}_${TASK}.md"
    echo "✅ ${TASK} → done/${NEXT}_${TASK}.md"
    CHANGED=true
  fi

  # 로컬 + 원격 브랜치 삭제
  git branch -d "$BRANCH" 2>/dev/null && echo "🗑️ 로컬 브랜치 삭제: $BRANCH"
  git push origin --delete "$BRANCH" 2>/dev/null && echo "🗑️ 원격 브랜치 삭제: $BRANCH"
  git remote prune origin 2>/dev/null || true
done

# 변경사항 커밋 + 푸시
if [ "$CHANGED" = true ] && ! git diff --quiet .claude/tasks/; then
  git add .claude/tasks/
  git commit -m "chore: 머지 완료 태스크 정리 → done/ 이동

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
  git push
  echo "📦 태스크 정리 커밋 완료"
fi
