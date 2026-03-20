---
id: SP-011
priority: P0
scope: frontend
branch: feat/SP-011-new-storyboard-stale-data
created: 2026-03-20
status: running
depends_on:
label: bug
assignee: stopper2008
---

## 무엇을
기존 영상 확인 후 "새 영상" 생성 시 이전 스토리보드 데이터가 잔류하는 버그 수정

## 왜
- 재현율 100%: 기존 영상 열기 → 빠져나가기 → "새 영상" 클릭 → 이전 제목/채팅/breadcrumb 표시
- 사용자가 새 영상을 만들 수 없는 치명적 UX 버그

## QA E2E 테스트 결과 (2026-03-20)

### 발견 버그 5건

**BUG #1 (Critical): `handleDismiss` 후 이전 영상 재로드**
- 경로: 기존 영상 → X(Dismiss) → 2초 뒤 이전 영상 데이터 복귀
- 원인: `clearStudioUrlParams()`(replaceState)와 `router.replace("/studio")` 경쟁 조건
- Next.js `useSearchParams`가 여전히 `?id=1120` 반환 → useStudioInitialization이 DB 재로드

**BUG #2 (High): 뒤로가기 시 stale breadcrumb**
- 경로: 기존 영상 → 브라우저 뒤로가기 → breadcrumb에 이전 제목 잔류
- 원인: ContextStore `storyboardId`가 persist 대상 → rehydration으로 복원

**BUG #3 (High): Dismiss 시 URL 미정리**
- 경로: Dismiss(X) → URL에 `?id=1120` 잔류
- 원인: `clearStudioUrlParams`(replaceState)를 Next.js `router.replace`가 덮어씀

**BUG #4 (Medium): ContextStore storyboardId persist**
- 새 탭/새로고침 시 이전 storyboardId 복원
- 원인: `TRANSIENT_CONTEXT_KEYS`에 `storyboardId`/`storyboardTitle` 미포함

**BUG #5 (Medium): `:new` localStorage 키 stale**
- 새 영상 작업 → 나가기 → 다시 새 영상 → 이전 `:new` 데이터 로드
- 원인: `getStoryboardPersistKey()` → storyboardId=null → `:new` 키 → 이전 세션 데이터

### 근본 원인 데이터 흐름

```
handleDismiss() 호출
    ├── resetContext()            → storyboardId = null  (동기)
    ├── resetTransientStores()    → stores reset          (동기)
    ├── clearStudioUrlParams()    → replaceState("/studio") (동기)
    └── router.replace("/studio") → Next.js SPA 내비 (비동기)
         │
         ├── [타이밍 갭] useSearchParams 아직 ?id=1120 반환
         │
         └── useStudioInitialization useEffect 트리거
              └── storyboardId = "1120" (URL에서)
              └── axios.get(/storyboards/1120) → DB 재로드
              └── setContext({ storyboardId: 1120 })  ← 다시 설정!
```

**핵심**: `?new=true` 경로는 `resetAllStores()` 덕에 정상. `handleDismiss` 경로만 실패.

## 수정 계획

### Fix 1: `handleDismiss` URL 정리 경쟁 조건 해소 (BUG #1, #3)
- `PersistentContextBar.tsx`의 `handleDismiss`에서 `clearStudioUrlParams()` 제거
- `router.replace("/studio")`만 사용 (Next.js가 URL + searchParams 일괄 처리)
- 또는 dismiss 상태 플래그로 useStudioInitialization의 DB 재로드 방지

### Fix 2: ContextStore storyboardId transient 처리 (BUG #2, #4)
- `TRANSIENT_CONTEXT_KEYS`에 `storyboardId`, `storyboardTitle` 추가
- URL이 storyboardId의 SSOT — persist 불필요

### Fix 3: `:new` localStorage 키 정리 (BUG #5)
- `resetAllStores()`에서 `:new` 키도 명시적 삭제
- 또는 `resetTransientStores()`에서도 scoped storage 키 삭제

## 관련 파일
- `frontend/app/components/context/PersistentContextBar.tsx` — handleDismiss
- `frontend/app/hooks/useStudioInitialization.ts` — ?new=true + ?id= 처리
- `frontend/app/store/useContextStore.ts` — storyboardId persist
- `frontend/app/store/resetAllStores.ts` — resetAllStores + resetTransientStores
- `frontend/app/store/useStoryboardStore.ts` — scoped storage + getStoryboardPersistKey
- `frontend/app/hooks/useChatMessages.ts` — chatResetToken 감지
- `frontend/app/components/studio/StudioKanbanView.tsx` — handleNewShorts
- `frontend/app/utils/url.ts` — clearStudioUrlParams

## 완료 기준 (DoD)
- [ ] BUG #1: Dismiss → 이전 영상 재로드 안 됨
- [ ] BUG #2: 뒤로가기 시 breadcrumb 초기화
- [ ] BUG #3: Dismiss 후 URL에 ?id= 미잔류
- [ ] BUG #4: 새로고침/새 탭에서 stale storyboardId 미복원
- [ ] BUG #5: 새 영상 → 나가기 → 새 영상 → 빈 상태
- [ ] 기존 영상 → 다른 기존 영상 → 데이터 정상 전환 (regression 없음)
- [ ] 기존 테스트 통과

## 제약
- Zustand persist middleware 구조 변경 시 다른 store (RenderStore, ChatStore) 영향도 확인
- `storyboardId` persist 제거 시 "새로고침 후 복귀" UX 영향 검토 필요
