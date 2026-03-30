#!/bin/bash
# SDD Auto Review + Fix: 리뷰 → 이슈 발견 → 자동 수정 → push
# cron 5분 간격 실행

set -euo pipefail

# 동시 실행 방지
exec 9>/tmp/sdd-fix.lock
flock -n 9 || exit 0

export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/$(ls $HOME/.nvm/versions/node/ 2>/dev/null | tail -1)/bin:$PATH"

PROJECT_DIR="/home/tomo/Workspace/shorts-producer"
cd "$PROJECT_DIR"
LOG="/tmp/sdd-review.log"

# ─── Phase 0: 좀비 정리 — 머지/닫힌 PR의 claude 프로세스 + worktree ───
for CLAUDE_PID in $(pgrep -f "claude.*--worktree" 2>/dev/null || true); do
  WT_NAME=$(ps -p "$CLAUDE_PID" -o args= 2>/dev/null | grep -oP '(?<=--worktree )\S+' || true)
  [ -z "$WT_NAME" ] && continue
  # worktree 이름(SP-NNN)에서 SP-ID 추출 → PR 브랜치 패턴 매칭
  WT_SP_ID=$(echo "$WT_NAME" | grep -oE 'SP-[0-9]+' || true)
  [ -z "$WT_SP_ID" ] && continue
  PR_STATE=$(gh pr list --state all --json number,headRefName,state \
    --jq "[.[] | select(.headRefName | test(\"${WT_SP_ID}\"))] | .[0].state // empty" 2>/dev/null || true)
  if [ "$PR_STATE" = "MERGED" ] || [ "$PR_STATE" = "CLOSED" ]; then
    kill "$CLAUDE_PID" 2>/dev/null && echo "$(date '+%Y-%m-%d %H:%M') 좀비 kill: PID=$CLAUDE_PID worktree=$WT_NAME ($PR_STATE)" >> "$LOG"
    # worktree 정리
    git worktree remove "$PROJECT_DIR/.claude/worktrees/$WT_NAME" --force 2>/dev/null || true
    git worktree prune 2>/dev/null || true
    rm -f "/tmp/sdd-fix-*.lock" "/tmp/sdd-review-*.lock"
  fi
done

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

# ─── Phase 1.5: conflict 있는 PR → 자동 rebase ───
CONFLICT_PRS=$(gh pr list --state open --base main --json number,headRefName,mergeable \
  --jq '.[] | select(.mergeable == "CONFLICTING") | "\(.number) \(.headRefName)"' 2>/dev/null || true)

echo "$CONFLICT_PRS" | while read -r PR_NUM BRANCH; do
  [ -z "$PR_NUM" ] && continue
  echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} (${BRANCH}) conflict rebase 시작" >> "$LOG"

  # 1차: git rebase 시도 (단순 충돌)
  git fetch origin main "$BRANCH" 2>/dev/null || continue
  git checkout "$BRANCH" 2>/dev/null || continue

  if git rebase origin/main 2>/dev/null; then
    git push --force-with-lease 2>/dev/null && echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} rebase 성공" >> "$LOG"
  else
    git rebase --abort 2>/dev/null
    # 2차: Claude가 conflict 해결
    echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} conflict → Claude 해결 시도" >> "$LOG"
    SP_ID=$(echo "$BRANCH" | grep -oE 'SP-[0-9]+' || echo "conflict-${PR_NUM}")
    # 기존 worktree: 프로세스 없으면 삭제, 있으면 스킵
    if [ -d "$PROJECT_DIR/.claude/worktrees/${SP_ID}" ]; then
      if pgrep -f "worktree.*${SP_ID}[^0-9]" > /dev/null 2>&1 || pgrep -f "worktree ${SP_ID} " > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M') ${SP_ID} worktree 사용 중 — conflict 스킵" >> "$LOG"
        git checkout main 2>/dev/null || true
        continue
      fi
      git worktree remove "$PROJECT_DIR/.claude/worktrees/${SP_ID}" --force 2>/dev/null; git worktree prune 2>/dev/null
    fi
    claude --worktree "${SP_ID}" --dangerously-skip-permissions -p \
      "PR #${PR_NUM} (${BRANCH})에 merge conflict가 있습니다.
1. git fetch origin ${BRANCH} && git checkout ${BRANCH}
2. git rebase origin/main
3. conflict 파일을 읽고 양쪽 의도를 파악하여 해결
4. git rebase --continue
5. git push --force-with-lease
6. 해결 불가하면 PR에 코멘트: 'conflict 자동 해결 실패 — 수동 확인 필요'" \
      2>>"$LOG" || {
        gh pr comment "$PR_NUM" --body "conflict 자동 해결 실패 — [사람] 수동 rebase 필요" 2>/dev/null || true
        echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} conflict 자동 해결 실패" >> "$LOG"
      }
  fi

  git checkout main 2>/dev/null || true
done

# ─── Phase 2: 리뷰 이슈 있는 PR → 자동 수정 ───
REVIEWED_PRS=$(gh pr list --state open --base main --json number,headRefName \
  --jq '.[].number' 2>/dev/null || true)

for PR_NUM in $REVIEWED_PRS; do
  # 대응이 필요한 코멘트 감지:
  # 1. 이슈 코멘트: Claude 리뷰 이슈 또는 사람 코멘트
  # 2. 인라인 리뷰 코멘트 (PR review comments)
  ISSUE_COMMENTS=$(gh api "repos/tomo-playground/shorts-producer/issues/${PR_NUM}/comments" \
    --jq '[.[] | select(
      (.body | test("Found [0-9]+ issue")) or
      ((.body | test("Code review|Generated with")) | not)
    )] | length' 2>/dev/null || echo "0")
  REVIEW_COMMENTS=$(gh api "repos/tomo-playground/shorts-producer/pulls/${PR_NUM}/comments" \
    --jq 'length' 2>/dev/null || echo "0")
  HAS_ISSUES=$((ISSUE_COMMENTS + REVIEW_COMMENTS))
  [ "$HAS_ISSUES" -eq 0 ] && continue

  # 마지막 코멘트 시각 (이슈 코멘트 + 인라인 리뷰 코멘트 중 최신)
  LAST_ISSUE_DATE=$(gh api "repos/tomo-playground/shorts-producer/issues/${PR_NUM}/comments" \
    --jq '[.[] | select(
      (.body | test("Found [0-9]+ issue")) or
      ((.body | test("Code review|Generated with")) | not)
    )] | last | .created_at // ""' 2>/dev/null || true)
  LAST_REVIEW_DATE=$(gh api "repos/tomo-playground/shorts-producer/pulls/${PR_NUM}/comments" \
    --jq 'last | .created_at // ""' 2>/dev/null || true)
  LAST_COMMENT_DATE=$(echo -e "${LAST_ISSUE_DATE}\n${LAST_REVIEW_DATE}" | sort -r | head -1)
  # 마지막 커밋 시각 (PR updated_at은 코멘트로도 갱신되므로 부적합)
  LAST_PUSH_DATE=$(gh api "repos/tomo-playground/shorts-producer/pulls/${PR_NUM}/commits" \
    --jq 'last | .commit.committer.date // ""' 2>/dev/null || true)

  # 리뷰 이후 push가 있으면 이미 수정됨
  if [ -n "$LAST_COMMENT_DATE" ] && [ -n "$LAST_PUSH_DATE" ] && [[ "$LAST_PUSH_DATE" > "$LAST_COMMENT_DATE" ]]; then
    continue
  fi

  LOCK="/tmp/sdd-fix-${PR_NUM}.lock"
  [ -f "$LOCK" ] && continue

  # 동일 PR 연속 수정 횟수 제한 (무한 루프 방지)
  FIX_COUNT_FILE="/tmp/sdd-fix-${PR_NUM}.count"
  FIX_COUNT=$(cat "$FIX_COUNT_FILE" 2>/dev/null || echo "0")
  if [ "$FIX_COUNT" -ge 3 ]; then
    echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} 수정 3회 도달 — 스킵 (사람 확인 필요)" >> "$LOG"
    continue
  fi
  echo $((FIX_COUNT + 1)) > "$FIX_COUNT_FILE"

  touch "$LOCK"

  # PR의 브랜치명 가져오기
  BRANCH=$(gh pr view "$PR_NUM" --json headRefName --jq '.headRefName' 2>/dev/null || true)
  [ -z "$BRANCH" ] && { rm -f "$LOCK"; continue; }

  echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} (${BRANCH}) 리뷰 이슈 수정 시작" >> "$LOG"

  # 워크트리에서 Claude로 판단 기반 대응 (main 브랜치 오염 방지)
  SP_ID=$(echo "$BRANCH" | grep -oE 'SP-[0-9]+' || echo "fix-${PR_NUM}")
  # 기존 worktree: 프로세스 없으면 삭제, 있으면 스킵
  if [ -d "$PROJECT_DIR/.claude/worktrees/${SP_ID}" ]; then
    if pgrep -f "worktree.*${SP_ID}[^0-9]" > /dev/null 2>&1 || pgrep -f "worktree ${SP_ID} " > /dev/null 2>&1; then
      echo "$(date '+%Y-%m-%d %H:%M') ${SP_ID} worktree 사용 중 — 피드백 스킵" >> "$LOG"
      rm -f "$LOCK"
      continue
    fi
    git worktree remove "$PROJECT_DIR/.claude/worktrees/${SP_ID}" --force 2>/dev/null; git worktree prune 2>/dev/null
  fi
  claude --worktree "${SP_ID}" --dangerously-skip-permissions -p "PR #${PR_NUM} (브랜치: ${BRANCH}) 피드백을 대응하세요.

0. 먼저 git fetch origin ${BRANCH} && git checkout ${BRANCH} 실행.

1. gh api repos/tomo-playground/shorts-producer/issues/${PR_NUM}/comments 와 gh api repos/tomo-playground/shorts-producer/pulls/${PR_NUM}/comments 로 모든 코멘트를 읽으세요.

2. 각 코멘트를 분류하세요:
   - 버그 지적 → 즉시 수정
   - 설계 질문/개선 제안 → CLAUDE.md 규칙과 대조하여 판단
   - 스타일/Nit → 합리적이면 수정, 아니면 스킵

3. 동의하는 피드백: 코드 수정 + 커밋 + push + PR에 '수정했습니다: [변경 내용]' 코멘트
4. 비동의하는 피드백: 코드 수정 없이 PR에 '현행 유지 이유: [근거]' 코멘트" \
    2>>"$LOG" || true

  # CodeRabbit CHANGES_REQUESTED 해소 트리거
  CR_STATE=$(gh api "repos/tomo-playground/shorts-producer/pulls/${PR_NUM}/reviews" \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]" and .state == "CHANGES_REQUESTED")] | length' 2>/dev/null || echo "0")
  if [ "$CR_STATE" -gt 0 ]; then
    gh pr comment "$PR_NUM" --body "@coderabbitai resolve" 2>/dev/null || true
    echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} @coderabbitai resolve 요청" >> "$LOG"
  fi

  rm -f "$LOCK"
  echo "$(date '+%Y-%m-%d %H:%M') PR #${PR_NUM} 수정 완료" >> "$LOG"
done
