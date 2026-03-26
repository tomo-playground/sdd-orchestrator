---
id: SP-080
priority: P1
scope: infra
branch: feat/SP-080-auto-rollback
created: 2026-03-26
status: pending
depends_on:
label: feature
---

## 무엇을 (What)
머지 후 5분 내 Sentry 에러 급증을 감지하면 자동으로 revert PR을 생성하는 안전망.

## 왜 (Why)
코딩머신이 자율 실행 + 오케스트레이터가 자동 머지하는 구조에서, 머지 후 프로덕션 에러가 발생하면 사람이 인지하기 전에 피해가 확산될 수 있음. 자동 롤백이 있으면 머지를 더 공격적으로 할 수 있고, 사고 복구 시간(MTTR)이 크게 줄어듦.

## 완료 기준 (DoD)

### Phase A: Sentry 에러 급증 감지
- [ ] 오케스트레이터에 `post_merge_monitor` 도구 추가 — 머지 직후부터 5분간 Sentry 에러율 모니터링
- [ ] 머지 전 에러 카운트 스냅샷 저장 (baseline)
- [ ] 5분 내 에러 카운트가 baseline 대비 N건 이상 증가하면 "급증" 판정
- [ ] 급증 임계값은 `config.py`에서 설정 가능 (`ROLLBACK_ERROR_THRESHOLD`, 기본값: 5)

### Phase B: 자동 Revert PR 생성
- [ ] 급증 감지 시 `gh api`로 revert PR 자동 생성 (`Revert "원본 PR 제목"`)
- [ ] revert PR에 `auto-rollback` 라벨 추가
- [ ] Slack 알림: `[ROLLBACK] PR #N 머지 후 Sentry 에러 급증 — revert PR #M 생성됨`
- [ ] revert PR은 **자동 머지하지 않음** — 사람이 확인 후 머지 (안전장치)

### Phase C: 상태 추적
- [ ] `state.db`에 `rollbacks` 테이블 추가 (원본 PR, revert PR, 에러 수, 타임스탬프)
- [ ] 중복 rollback 방지 — 같은 PR에 대해 revert가 이미 생성되었으면 skip
- [ ] 데일리 리포트에 rollback 이력 포함

### 공통
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 힌트
- 오케스트레이터의 `merge_pr` 도구(`tools/github.py`) 실행 직후 모니터링 시작
- Sentry API: `GET /api/0/projects/{org}/{project}/issues/?query=is:unresolved&sort=date` — 이미 `tools/sentry.py`에 구현됨
- `gh pr create --title "Revert ..." --body "..." --label auto-rollback` 로 revert PR 생성
- 비동기 모니터링: `asyncio.create_task`로 5분 타이머 실행, 메인 루프 비차단

## 참고
- 오케스트레이터 구조: `orchestrator/main.py`, `orchestrator/tools/`
- Sentry 스캔: `orchestrator/tools/sentry.py`
- PR 관리: `orchestrator/tools/github.py`
- 상태 DB: `orchestrator/state.py`
