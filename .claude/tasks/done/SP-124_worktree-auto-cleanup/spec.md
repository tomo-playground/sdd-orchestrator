# SP-124: Worktree 자동 정리 — 프로세스 종료 후 잔류 방지

- **branch**: feat/SP-124_worktree-auto-cleanup
- **priority**: P1
- **scope**: sdd-orchestrator, .claude/scripts
- **assignee**: AI
- **created**: 2026-03-31

## 배경

worktree 생성 후 프로세스 종료 시 디렉토리가 삭제되지 않아 잔류.
같은 이름의 worktree 재생성 시 데이터 충돌 발생.

### 생성 경로 (4곳)

| 경로 | 이름 패턴 | 정리 |
|------|----------|------|
| 오케스트레이터 launch_sdd_run | SP-NNN | heal에서 빈 것만 |
| sdd-fix.sh (conflict/피드백) | feat+SP-NNN_* | Phase 0 머지/닫힌 PR만 |
| GitHub Actions (sentry-autofix) | claude+issue-* | 없음 |
| 수동 claude --worktree | 임의 | 없음 |

### 현재 정리 로직 한계

- heal: 커밋 0개인 worktree만 삭제 → PR push 완료한 건 잔류
- sdd-sync.sh: SP-ID 패턴만 매칭 → claude+issue-* 미매칭
- sdd-fix.sh Phase 0: 실행 중 프로세스의 머지/닫힌 PR만 → 종료된 프로세스 대상 아님

## 목표

프로세스 종료 후 worktree를 안전하게 자동 삭제. 재생성 시 충돌 방지.

## DoD (Definition of Done)

- [ ] 오케스트레이터 `_watch_process`: 프로세스 종료 후 worktree remove
- [ ] sdd-sync.sh: 전체 `.claude/worktrees/*/` 스캔, PID 없는 worktree 일괄 삭제
- [ ] 삭제 전 안전 체크: uncommitted 변경이 있으면 로그 경고만 (force 삭제 안 함)
- [ ] pgrep 패턴의 regex 특수문자 이슈 처리 (claude+issue-* 등)
- [ ] launch_sdd_run 시 기존 worktree 잔류 감지 → 삭제 후 생성

## 수정 대상 파일

- `sdd-orchestrator/src/sdd_orchestrator/tools/worktree.py`
- `.claude/scripts/sdd-sync.sh`
