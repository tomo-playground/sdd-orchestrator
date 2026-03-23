---
id: SP-068
priority: P0
scope: infra
branch: feat/SP-068-orchestrator-auto-design
created: 2026-03-23
status: done
approved_at: 2026-03-23
depends_on: SP-067
label: feat
---

## 무엇을 (What)
오케스트레이터가 pending 상태의 태스크를 자동으로 설계(design.md 작성)하고, BLOCKER 없으면 자동 승인하여 SP-067의 자동 실행 파이프라인에 투입한다.

## 왜 (Why)
SP-067까지는 사람이 설계를 승인해야 실행이 시작된다. 이 단계를 자동화하면 사람은 spec 작성만 하면 된다. "뭘 만들지" 한 줄 → 설계 → 구현 → PR → 머지가 전부 자동으로 흐른다.

## 완료 기준 (DoD)

### Designer 서브에이전트

- [x] `orchestrator/agents.py`에 designer 서브에이전트를 정의한다 (Opus 모델)
- [x] designer 프롬프트에 현재 `/sdd-design` 로직(코드 탐색 → 소크라테스 질문 없이 → 6항목 설계)을 포함한다
- [x] designer가 spec.md를 읽고 design.md를 생성한다

### 자동 승인 규칙

- [x] `orchestrator/rules.py`에 자동 승인 조건을 정의한다:
  - BLOCKER 0건
  - 변경 파일 6개 이하
  - DB 스키마 변경 없음
  - 외부 의존성 추가 없음
- [x] 조건 충족 시 spec.md의 status를 `approved`로 변경하고 커밋한다
- [x] 조건 미충족 시 사람에게 알림 (SP-069 전까지는 콘솔 출력)

### 리뷰어 서브에이전트 (설계 리뷰)

- [ ] 설계 작성 후 Tech Lead/DBA 등 리뷰어 에이전트를 자동 호출한다 (현재 /sdd-design Phase 4.5 로직) <!-- deferred: design.md의 변경 파일 파싱 후 리뷰어 결정 로직은 설계에 포함되었으나, 서브에이전트 실제 호출은 Lead Agent 통합 후 추가 예정 -->
- [ ] BLOCKER 피드백은 자동 반영 후 재리뷰, 3회 실패 시 사람 알림 <!-- deferred: 리뷰어 호출 연동 시 함께 구현 -->

### 통합

- [x] pending + spec 있는 태스크 → 자동 설계 → 자동 승인 → 자동 실행 파이프라인 연결
- [x] 린트 통과

## 제약
- 소크라테스 질문은 생략 (FEATURES 명세 + CLAUDE.md + 코드 패턴으로 해결)
- DB 스키마 변경이 포함된 태스크는 자동 승인 불가 → 사람 판단 필수
- Sentry 연동은 SP-069

## 힌트
- 현재 /sdd-design Phase 1~5 로직을 designer 프롬프트에 포함
- AgentDefinition(model="opus") 로 설계 품질 확보
- 설계 리뷰는 별도 서브에이전트로 병렬 실행
