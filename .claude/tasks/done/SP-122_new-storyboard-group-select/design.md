# SP-122 상세 설계: 새 영상 생성 시 시리즈 선택 UX 개선

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `frontend/app/components/context/GroupSelectModal.tsx` | **신규** — 시리즈 선택 모달 |
| `frontend/app/hooks/useStudioInitialization.ts` | draft 생성 전 그룹 선택 게이트 추가 |
| `frontend/app/store/useUIStore.ts` | `pendingNewStoryboard` 플래그 추가 |
| `frontend/app/(service)/studio/page.tsx` | 모달 렌더링 + 선택 후 draft 생성 연결 |

## 설계 원칙

- 기존 `ensureDraftStoryboard` / `resetAllStores` 로직은 건드리지 않음
- 시리즈 선택을 **draft 생성 전에** 게이트로 삽입
- `GroupDropdown`의 `ConfigBadges` 패턴 재사용 (화풍/음성/프리셋 미리보기)

## 전체 흐름 (after)

```
홈 "새 영상" / Quick Start
  → /studio?new=true(&topic=X)
  → resetAllStores() (groupId 보존)
  → groupId 유효성 판단:
    ├─ groups.length === 0 → "시리즈 만들기" 안내 (기존)
    ├─ groups.length === 1 → 자동 선택, draft 생성 → 에디터
    └─ groups.length >= 2 → GroupSelectModal 표시
        → 사용자 선택
        → setContext({ groupId })
        → draft 생성 → 에디터
```

## DoD별 설계

### DoD-1: 시리즈 1개 → 자동 선택 → 에디터 즉시 진입

**구현 방법**: `useStudioInitialization.ts`의 `?new=true` 처리에서, `resetAllStores()` 후 groupId 유효성 체크 추가.

**before**:
```ts
await resetAllStores();
// 바로 ensureDraftStoryboard() 호출
const draftId = await ensureDraftStoryboard();
```

**after**:
```ts
await resetAllStores();

// groupId 유효성 체크 — 유효한 단일 그룹이면 자동 선택
const { groupId, groups } = useContextStore.getState();
const validGroups = groups.filter(g => g.id > 0);

if (validGroups.length === 0) {
  // 시리즈 없음 → gate 해제, 칸반의 "시리즈 만들기" UI로
  return;
}

if (validGroups.length === 1) {
  // 단일 시리즈 → 자동 선택
  useContextStore.getState().setContext({ groupId: validGroups[0].id });
} else if (!groupId || groupId <= 0 || !validGroups.some(g => g.id === groupId)) {
  // 복수 시리즈 + 유효한 groupId 없음 → 모달 표시 요청
  useUIStore.getState().set({ pendingNewStoryboard: true });
  return; // draft 생성은 모달 선택 후
}
// groupId가 유효하게 복원된 경우(localStorage) → 모달 없이 바로 진행

const draftId = await ensureDraftStoryboard();
// ... 기존 로직 계속
```

**엣지 케이스**:
- groupId가 localStorage에서 복원되어 유효한 그룹 ID인 경우 → 모달 없이 바로 진행 (마지막 사용 시리즈 자동 재선택)
- groups 로딩이 아직 안 끝난 경우 → `isLoadingGroups` 체크 필요. groups가 빈 배열이지만 로딩 중이면 대기

**영향 범위**: `useStudioInitialization` 내부만. 외부 인터페이스 변경 없음.
**Out of Scope**: `ensureDraftStoryboard` 내부 로직 변경. "유효 groupId가 있어도 항상 모달 표시" 옵션은 추후 UX 개선 백로그.

### DoD-2: 시리즈 2개+ → 선택 팝업 → 에디터 진입

**구현 방법**: `GroupSelectModal.tsx` 신규 생성 + `studio/page.tsx`에서 렌더.

**구현 기반**: `Modal` 컴포넌트 (`frontend/app/components/ui/Modal.tsx`) 래핑, `size="md"`. 그룹 카드는 `<button>` 요소로 구현. `ariaLabelledBy="group-select-title"`.

**GroupSelectModal Props**:
```ts
type Props = {
  groups: GroupItem[];
  onSelect: (groupId: number) => void;
  onClose: () => void;
};
```

**UI 구조** (`Modal` + `ConfigBadges` 패턴):
```
┌─────────────────────────────┐
│  어떤 시리즈에 만들까요?      │  ← h2#group-select-title
│                             │
│  ┌─ [button] ──────────────┐ │
│  │ 오늘도 출근했습니다       │ │
│  │ Flat Color Anime         │ │
│  │ 트렌디 내레이터 (25F)     │ │
│  │ Full 시네마틱             │ │
│  └─────────────────────────┘ │
│                             │
│  ┌─ [button] ──────────────┐ │
│  │ 우리가 닿는 순간         │ │
│  │ Romantic Warm Anime      │ │
│  │ 우아한 여성 (20대F)       │ │
│  │ Full 시네마틱             │ │
│  └─────────────────────────┘ │
└─────────────────────────────┘
```

**상태**:
- Loading: groups 로딩 중 → spinner (거의 발생 안 함, 이미 로드됨)
- Empty: groups 0개 → 이 모달은 표시하지 않음 (DoD-3에서 처리)
- Normal: 그룹 카드 목록
- Hover: 카드 hover 시 border 색상 변경
- Error: `ensureDraftStoryboard()` 실패 → Toast 에러 + 모달 닫기 + 칸반 복귀

**studio/page.tsx 연결**:
```tsx
const pendingNew = useUIStore(s => s.pendingNewStoryboard);

{pendingNew && groups.length >= 2 && (
  <GroupSelectModal
    groups={groups}
    onSelect={async (gId) => {
      useContextStore.getState().setContext({ groupId: gId });
      useUIStore.getState().set({ pendingNewStoryboard: false });
      const { ensureDraftStoryboard } = await import("../../store/actions/draftActions");
      const draftId = await ensureDraftStoryboard();
      if (draftId) {
        useUIStore.getState().set({ isNewStoryboardMode: true });
      } else {
        // Error: draft 생성 실패 → 칸반 복귀
        useUIStore.getState().showToast("초안 생성에 실패했습니다", "error");
        const url = new URL(window.location.href);
        url.searchParams.delete("new");
        window.history.replaceState({}, "", url.toString());
      }
    }}
    onClose={() => {
      useUIStore.getState().set({ pendingNewStoryboard: false });
      const url = new URL(window.location.href);
      url.searchParams.delete("new");
      window.history.replaceState({}, "", url.toString());
    }}
  />
)}
```

**엣지 케이스**:
- 모달 열린 상태에서 ESC → `Modal` 컴포넌트의 ESC 핸들러 → onClose → 칸반 복귀
- draft 생성 실패 → Toast + 모달 닫기 + 칸반 복귀
- 모달 열린 상태에서 브라우저 뒤로가기 → URL 변경 감지 → 모달 닫힘

**영향 범위**: studio/page.tsx에 모달 렌더링 추가. 다른 페이지 영향 없음.
**Out of Scope**: 모달 내 "새 시리즈 만들기" 버튼.

### DoD-3: 시리즈 0개 → 기존 동작 유지

**구현 방법**: 변경 없음. `StudioKanbanView.tsx:110`의 기존 "시리즈 만들기" UI 그대로.

`useStudioInitialization`에서 `validGroups.length === 0`이면 early return → `hasStoryboard = false` → `StudioKanbanView` 렌더 → 기존 안내.

### DoD-4: 홈 Quick Start 동일 흐름

**구현 방법**: 변경 없음. Quick Start도 `/studio?new=true&topic=X`로 이동하므로 동일한 `useStudioInitialization` 흐름. topic은 URL 파라미터로 유지되므로 시리즈 선택 후에도 `page.tsx`의 `topicParam` useEffect에서 정상 적용됨.

### DoD-5: 칸반 "+ 새 영상" 영향 없음 확인

**구현 방법**: 변경 없음. `StudioKanbanView.handleNewShorts()`는 이미 유효한 groupId 상태에서 호출됨. `pendingNewStoryboard` 플래그와 무관.

## useUIStore 추가 필드

```ts
pendingNewStoryboard: boolean; // 시리즈 선택 모달 대기 상태
```

initialState: `false`. `resetAllStores`에서 초기화됨 (transient).

## 테스트 전략

E2E mock 기반 (`tests/vrt/`):
1. groups 1개 mock → "새 영상" → 자동 선택 → 에디터 진입 확인
2. groups 2개 mock → "새 영상" → 모달 표시 → 선택 → 에디터 진입 확인
3. groups 0개 → "새 영상" → "시리즈 만들기" 안내 확인 (기존 동작)
4. 모달에서 ESC → 칸반 복귀 확인
5. 모달에서 선택 후 draft 실패 → Toast + 칸반 복귀 확인

## UI/UX 설계 리뷰 결과 (난이도: 중 — 2라운드)

### Round 1
| 리뷰어 | 판정 | 주요 피드백 |
|--------|------|------------|
| UI/UX Engineer | WARNING | Error 상태 누락 (draft 실패 시 모달 복구) |
| UI/UX Engineer | WARNING | Modal 기반 구현 + button 요소 + ariaLabelledBy 명시 필요 |

### Round 2 (반영 후)
- Error 상태 추가 완료 (Toast + 모달 닫기 + 칸반 복귀)
- `Modal` 컴포넌트 기반, `<button>` 요소, `ariaLabelledBy` 명시 완료
