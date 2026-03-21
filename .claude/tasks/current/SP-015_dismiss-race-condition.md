---
id: SP-015
priority: P0
scope: frontend
branch: feat/SP-015-dismiss-race-condition
created: 2026-03-21
status: pending
depends_on:
label: bug
assignee: stopper2008
---

## 무엇을
handleDismiss 경쟁 조건 해소 + `:new` localStorage stale 키 정리

## 왜
- SP-011 QA E2E 테스트에서 발견된 잔여 버그 (BUG #1/#3/#5)
- PR #50/#52로 주요 경로(?new=true) 해결됨, Dismiss 경로만 잔류
- Dismiss(X) 클릭 → 2초 뒤 이전 영상 데이터 완전 재로드

## 버그 상세

### BUG #1 (Critical): handleDismiss 후 이전 영상 재로드
- 경로: 기존 영상 → X(Dismiss) → 2초 뒤 이전 영상 데이터 복귀
- 원인: `clearStudioUrlParams()`(replaceState)와 `router.replace("/studio")` 경쟁 조건
- Next.js `useSearchParams`가 여전히 `?id=1120` 반환 → useStudioInitialization이 DB 재로드

### BUG #3 (High): Dismiss 시 URL 미정리
- 경로: Dismiss(X) → URL에 `?id=1120` 잔류
- 원인: `clearStudioUrlParams`(replaceState)를 Next.js `router.replace`가 덮어씀

### BUG #5 (Medium): `:new` localStorage 키 stale
- 경로: 새 영상 작업 → 나가기 → 다시 새 영상 → 이전 `:new` 데이터 로드
- 원인: `getStoryboardPersistKey()` → storyboardId=null → `:new` 키 → 이전 세션 데이터

## 수정 계획

### Fix 1: handleDismiss URL 정리 단순화 (BUG #1, #3)
- `clearStudioUrlParams()` 제거 → `router.replace("/studio")`만 사용
- 또는 dismiss 상태 플래그로 useStudioInitialization의 DB 재로드 방지

### Fix 2: `:new` localStorage 키 정리 (BUG #5)
- `resetAllStores()`에서 `:new` 키도 명시적 삭제
- 또는 `resetTransientStores()`에서도 scoped storage 키 삭제

## 관련 파일
- `frontend/app/components/context/PersistentContextBar.tsx` — handleDismiss
- `frontend/app/hooks/useStudioInitialization.ts` — ?new=true + ?id= 처리
- `frontend/app/store/resetAllStores.ts` — resetAllStores + resetTransientStores
- `frontend/app/store/useStoryboardStore.ts` — getStoryboardPersistKey, scoped storage
- `frontend/app/utils/url.ts` — clearStudioUrlParams

## 완료 기준 (DoD)
- [ ] Dismiss → 이전 영상 재로드 안 됨
- [ ] Dismiss 후 URL에 ?id= 미잔류
- [ ] 새 영상 → 나가기 → 새 영상 → 빈 상태
- [ ] 기존 영상 → 다른 기존 영상 → 데이터 정상 전환 (regression 없음)
- [ ] 빌드 + 기존 테스트 통과
