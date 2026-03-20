---
id: SP-011
priority: P0
scope: frontend
branch: feat/SP-011-new-storyboard-stale-data
created: 2026-03-20
status: running
depends_on:
---

## 무엇을
기존 영상 확인 후 "새 영상" 생성 시 이전 스토리보드 데이터가 잔류하는 버그 수정

## 왜
- 재현율 100%: 기존 영상 열기 → 빠져나가기 → "새 영상" 클릭 → 이전 제목/채팅/breadcrumb 표시
- 사용자가 새 영상을 만들 수 없는 치명적 UX 버그

## 재현 경로
1. 기존 영상(storyboard X) 열기
2. 빠져나가기 (X 버튼 또는 칸반으로 이동)
3. "새 영상" 클릭
4. 이전 스토리보드 X의 제목, 채팅, breadcrumb이 그대로 표시
5. URL: `?new=true` 잠깐 나왔다 `/studio`로 변경됨

## 이전 분석 (PR #49, 미완성)

### 수정 시도 (전부 실패)
1. `resetAllStores`에서 `:new` localStorage 키 삭제
2. ContextStore에서 storyboardId persist 제외 (TRANSIENT_CONTEXT_KEYS)
3. chatMessages save debounce 취소
4. `resetTransientStores`에 chatStore 정리 추가

### 추정 근본 원인
- `resetAllStores()`가 async — await 중 React 렌더 사이클이 이전 상태 표시
- Zustand persist middleware rehydration이 reset 직후 동기적으로 이전 데이터 복원
- `useStudioInitialization` useEffect 실행 순서 문제로 reset 후 이전 storyboardId로 DB 재로드

### 디버깅 필요 항목
- `console.log`로 `resetAllStores` 전후 각 store 상태 추적
- Zustand persist `onRehydrateStorage` 콜백에 로그 추가
- `useStudioInitialization`의 3개 useEffect 실행 순서 확인
- `handleDismiss` (빠져나가기) 시 store 상태 변화 추적

## 완료 기준 (DoD)
- [ ] 재현 경로에서 새 영상 생성 시 빈 상태로 시작
- [ ] 기존 영상 → 빠져나가기 → 새 영상 → 이전 데이터 미표시
- [ ] 기존 영상 → 다른 기존 영상 → 데이터 정상 전환 (regression 없음)
- [ ] localStorage.clear() 없이 정상 동작
- [ ] 기존 테스트 통과

## 제약
- fix/new-storyboard-stale-rehydration 브랜치의 부분 수정 참고 가능
- Zustand persist middleware 구조 변경 시 다른 store (RenderStore, ChatStore) 영향도 확인

## 힌트
- 관련 파일:
  - `frontend/app/hooks/useStudioInitialization.ts` — ?new=true 처리 + DB 로드
  - `frontend/app/hooks/useChatMessages.ts` — 채팅 save debounce + storyboardId 전환
  - `frontend/app/store/resetAllStores.ts` — resetAllStores + resetTransientStores
  - `frontend/app/store/useContextStore.ts` — storyboardId persist
  - `frontend/app/store/useStoryboardStore.ts` — Zustand persist + scoped storage
  - `frontend/app/components/context/PersistentContextBar.tsx` — handleDismiss
  - `frontend/app/components/studio/StudioKanbanView.tsx` — handleNewShorts
- PR #49 코멘트에 상세 분석 있음
