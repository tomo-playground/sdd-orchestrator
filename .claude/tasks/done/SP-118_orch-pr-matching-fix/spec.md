# SP-118: 오케스트레이터 PR 매칭 오류 수정

- **approved_at**: 2026-03-29
- **priority**: P1
- **scope**: sdd-orchestrator
- **assignee**: AI
- **created**: 2026-03-29

## 배경

오케스트레이터가 approved 태스크를 auto-launch할 때, 다른 태스크의 PR을 잘못 매칭하여 실행을 차단하는 버그.

### 재현

```
SP-117 (approved) auto-launch 시도
→ "SP-117 already has open PR (PR #283)" 에러
→ PR #283은 SP-111의 PR (feat/SP-111-e2e-docker-ci)
→ SP-117은 PR이 없는데 차단됨
```

## 목표

태스크 번호(SP-NNN)와 PR 브랜치명을 정확히 매칭하여, 다른 태스크의 PR로 인해 차단되지 않도록 수정.

## DoD (Definition of Done)

- [ ] PR 매칭 로직에서 태스크 번호 정확 매칭 (SP-117 ≠ SP-111)
- [ ] auto-launch 차단 시 정확한 PR 번호/브랜치 로그 출력
- [ ] 테스트: 다른 태스크의 PR이 있어도 해당 태스크의 auto-launch는 정상 동작

## 참고

- 오케스트레이터 로그: `Auto-launch SP-117 failed: Error: SP-117 already has open PR (PR #283) — skipping launch`
- PR #283: `feat/SP-111-e2e-docker-ci` (SP-111 태스크)
