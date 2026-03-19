#!/bin/bash
# SDD Auto Review: 리뷰 안 된 PR 감지 → Claude 코드 리뷰 자동 실행
# cron 5분 간격 실행

set -euo pipefail

PROJECT_DIR="/home/tomo/Workspace/shorts-producer"
cd "$PROJECT_DIR"

# 열린 PR 중 리뷰 코멘트가 없는 것 찾기
OPEN_PRS=$(gh pr list --state open --base main --json number,headRefName,reviews \
  --jq '[.[] | select((.reviews | length) == 0)] | .[].number' 2>/dev/null || true)

[ -z "$OPEN_PRS" ] && exit 0

for PR_NUM in $OPEN_PRS; do
  # 이미 리뷰 중인지 확인 (lock file)
  LOCK="/tmp/sdd-review-${PR_NUM}.lock"
  if [ -f "$LOCK" ]; then
    continue
  fi
  touch "$LOCK"

  echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} 리뷰 시작" >> /tmp/sdd-review.log

  # Claude로 코드 리뷰 실행 (non-interactive)
  claude -p "/code-review:code-review ${PR_NUM}" --dangerously-skip-permissions 2>>/tmp/sdd-review.log || true

  rm -f "$LOCK"
  echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} 리뷰 완료" >> /tmp/sdd-review.log
done
