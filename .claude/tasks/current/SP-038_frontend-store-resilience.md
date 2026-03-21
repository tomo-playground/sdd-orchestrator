---
id: SP-038
priority: P2
scope: frontend
branch: feat/SP-038-frontend-store-resilience
created: 2026-03-21
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
Zustand persist store version + migrate 패턴 전체 적용

## 왜
- 4개 persist store 중 1개(RenderStore)만 version+migrate 있음
- 스키마 변경 시 나머지 3개 store에서 stale 데이터 문제 발생 가능
- SP-011 stale data 버그와 동일 유형의 잠재 위험

## 수정 범위
1. `useStoryboardStore.ts`: version + migrate 추가
2. `useContextStore.ts`: version + migrate 추가
3. `useChatStore.ts`: version + migrate 추가

## 완료 기준 (DoD)
- [ ] 4개 persist store 전부 version + migrate 패턴 적용
- [ ] 기존 localStorage 데이터와 호환 (마이그레이션)
- [ ] 기존 테스트 통과
