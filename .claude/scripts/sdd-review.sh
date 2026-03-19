#!/bin/bash
# SDD Auto Review + Fix: 리뷰 → 이슈 발견 → 자동 수정 → push
# cron 5분 간격 실행

set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/$(ls $HOME/.nvm/versions/node/ 2>/dev/null | tail -1)/bin:$PATH"

PROJECT_DIR="/home/tomo/Workspace/shorts-producer"
cd "$PROJECT_DIR"
LOG="/tmp/sdd-review.log"

# ─── Phase 1: 리뷰 안 된 PR → 코드 리뷰 실행 ───
UNREVIEWED=$(gh pr list --state open --base main --json number,headRefName \
  --jq '[.[] | select(true)] | .[].number' 2>/dev/null || true)

for PR_NUM in $UNREVIEWED; do
  # 이미 Claude 리뷰 코멘트가 있는지 확인
  HAS_REVIEW=$(gh api "repos/tomo-playground/shorts-producer/issues/${PR_NUM}/comments" \
    --jq '[.[] | select(.body | test("Code review"))] | length' 2>/dev/null || echo "0")
  [ "$HAS_REVIEW" -gt 0 ] && continue

  LOCK="/tmp/sdd-review-${PR_NUM}.lock"
  [ -f "$LOCK" ] && continue
  touch "$LOCK"

  echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} 리뷰 시작" >> "$LOG"
  claude -p "/code-review:code-review ${PR_NUM}" --dangerously-skip-permissions 2>>"$LOG" || true
  rm -f "$LOCK"
  echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} 리뷰 완료" >> "$LOG"
done

# ─── Phase 2: 리뷰 이슈 있는 PR → 자동 수정 ───
REVIEWED_PRS=$(gh pr list --state open --base main --json number,headRefName \
  --jq '.[].number' 2>/dev/null || true)

for PR_NUM in $REVIEWED_PRS; do
  # 대응이 필요한 코멘트 감지:
  # 1. Claude 리뷰 이슈 ("Found N issues")
  # 2. 사람 코멘트 (Claude "Code review"/"Generated with" 제외한 모든 코멘트)
  HAS_ISSUES=$(gh api "repos/tomo-playground/shorts-producer/issues/${PR_NUM}/comments" \
    --jq '[.[] | select(
      (.body | test("Found [0-9]+ issue")) or
      ((.body | test("Code review|Generated with")) | not)
    )] | length' 2>/dev/null || echo "0")
  [ "$HAS_ISSUES" -eq 0 ] && continue

  # 마지막 코멘트 시각 (리뷰 이슈 또는 사람 코멘트)
  LAST_COMMENT_DATE=$(gh api "repos/tomo-playground/shorts-producer/issues/${PR_NUM}/comments" \
    --jq '[.[] | select(
      (.body | test("Found [0-9]+ issue")) or
      ((.body | test("Code review|Generated with")) | not)
    )] | last | .created_at' 2>/dev/null || true)
  LAST_PUSH_DATE=$(gh api "repos/tomo-playground/shorts-producer/pulls/${PR_NUM}" \
    --jq '.updated_at' 2>/dev/null || true)

  # 리뷰 이후 push가 있으면 이미 수정됨
  if [ -n "$LAST_COMMENT_DATE" ] && [ -n "$LAST_PUSH_DATE" ] && [[ "$LAST_PUSH_DATE" > "$LAST_COMMENT_DATE" ]]; then
    continue
  fi

  LOCK="/tmp/sdd-fix-${PR_NUM}.lock"
  [ -f "$LOCK" ] && continue
  touch "$LOCK"

  # PR의 브랜치명 가져오기
  BRANCH=$(gh pr view "$PR_NUM" --json headRefName --jq '.headRefName' 2>/dev/null || true)
  [ -z "$BRANCH" ] && { rm -f "$LOCK"; continue; }

  echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} (${BRANCH}) 리뷰 이슈 수정 시작" >> "$LOG"

  # 해당 브랜치에서 Claude로 수정 실행
  claude -p "PR #${PR_NUM} 코드 리뷰 이슈를 수정하세요. gh api repos/tomo-playground/shorts-producer/issues/${PR_NUM}/comments 로 리뷰 코멘트를 읽고, 이슈를 수정한 뒤 커밋+push 하세요. 브랜치: ${BRANCH}" \
    --dangerously-skip-permissions 2>>"$LOG" || true

  rm -f "$LOCK"
  echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} 수정 완료" >> "$LOG"
done
