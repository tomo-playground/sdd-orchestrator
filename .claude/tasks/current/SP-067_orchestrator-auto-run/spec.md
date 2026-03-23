---
id: SP-067
priority: P0
scope: infra
branch: feat/SP-067-orchestrator-auto-run
created: 2026-03-23
status: approved
approved_at: 2026-03-23
depends_on: SP-066
label: feat
---

## 무엇을 (What)
오케스트레이터가 approved 상태의 태스크를 자동으로 워크트리에서 /sdd-run 실행하고, PR 생성 후 품질 게이트를 모니터링하고, 통과 시 자동 머지한다.

## 왜 (Why)
SP-066 뼈대는 읽기 전용이다. 실제 가치는 "approved 태스크 → PR 머지"까지 사람 개입 없이 자동으로 흘러가는 것이다. 현재 사람이 하는 `/sdd-run 기동 → PR 확인 → 머지` 3단계를 자동화한다.

## 완료 기준 (DoD)

### 워크트리 자동 기동

- [ ] `orchestrator/tools/worktree.py` — `launch_sdd_run` 도구: `claude --worktree SP-NNN --dangerously-skip-permissions -p "/sdd-run SP-NNN"` 실행
- [ ] 동시 실행 상한(MAX_PARALLEL, 기본값 2)을 config로 관리한다
- [ ] 실행 중인 워크트리를 state에 기록하고, 완료/실패를 감지한다

### PR 모니터링

- [ ] `check_pr_status` 도구를 확장하여 PR의 CI 체크 + 리뷰 상태를 종합 판정한다 (pass/pending/fail)
- [ ] 5분마다 열린 PR 상태를 체크하고, state를 업데이트한다

### 자동 머지

- [ ] `orchestrator/tools/github.py` — `merge_pr` 도구: `gh pr merge --squash` 실행
- [ ] 자동 머지 조건: CI passed + 리뷰 approved + changes_requested 없음
- [ ] 머지 후 state에서 해당 run을 완료 처리한다

### 자동 머지 규칙

- [ ] `orchestrator/rules.py` — 자동 머지 규칙 정의 (CI, 리뷰, 커버리지 등)
- [ ] 규칙 미충족 시 머지하지 않고 대기 (사람 알림은 SP-069)

### 실패 처리

- [ ] /sdd-run 실패 (exit code != 0) → state에 failed 기록 + 콘솔 경고
- [ ] CI 3회 연속 실패 → 해당 태스크 blocked 처리 + 콘솔 경고
- [ ] PR changes_requested → 자동 수정 시도 (gh workflow run sdd-review.yml) → 재확인

### 통합

- [ ] approved 태스크가 backlog에 있으면 자동으로 워크트리 기동 → PR → 머지까지 무인 실행된다
- [ ] 기존 테스트 영향 없음
- [ ] 린트 통과

## 제약
- 설계 자동 작성/승인은 SP-068
- Slack 알림은 SP-069 (콘솔 출력만)
- 동시 실행 수는 GPU/메모리 제약에 따라 조정

## 힌트
- `claude --worktree` 는 격리된 git worktree에서 Claude Code를 실행
- 워크트리 완료 감지: 프로세스 종료 + exit code 확인
- `gh pr merge --squash --auto` 로 CI 통과 후 자동 머지 예약 가능
