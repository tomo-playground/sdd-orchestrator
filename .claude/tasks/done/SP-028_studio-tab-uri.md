---
id: SP-028
priority: P2
scope: frontend
branch: feat/SP-028-studio-tab-uri
created: 2026-03-21
status: done
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
Studio 탭 URI 표현 — `?tab=script/stage/direct/publish` 딥링크

## 왜
- 현재 탭 상태가 URL에 반영되지 않아 딥링크/북마크 불가
- 페이지 새로고침 시 항상 Script 탭으로 초기화
- 공유 URL로 특정 탭 직접 접근 불가

## 완료 기준 (DoD)
- [ ] URL 쿼리 파라미터 `?tab=` 로 탭 상태 반영
- [ ] 탭 전환 시 URL 자동 업데이트 (replaceState)
- [ ] URL의 `?tab=` 값으로 초기 탭 설정
- [ ] `?tab=` 없거나 잘못된 값이면 script 폴백
- [ ] `?new=true` 시 `?tab=` 무시하고 항상 script
- [ ] 기존 `?id=`, `?new=true` 파라미터와 공존
- [ ] 기존 기능 regression 없음

## 제약
- 변경 파일 5개 이하 목표
- 건드리면 안 되는 것: `useStudioInitialization` 로직 (탭 파라미터만 추가)

## 힌트
- 관련 파일: `frontend/app/(service)/studio/page.tsx`, `frontend/app/store/useUIStore.ts`
- `window.history.replaceState` 패턴은 `useStudioInitialization.ts`에서 이미 사용 중
