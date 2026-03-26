# SP-099 설계

## 구현 방법

### 1. 신규 파일: `frontend/app/components/layout/LibraryMasterDetail.tsx`

제네릭 Master-Detail 레이아웃 컴포넌트 (약 150줄).

**Props 인터페이스:**
```ts
type LibraryMasterDetailProps<T extends { id: number }> = {
  // 데이터
  items: T[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  isLoading?: boolean;

  // 마스터 패널 (좌측)
  renderItem: (item: T, isSelected: boolean) => ReactNode;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  headerAction?: ReactNode;        // "+ New" 버튼 등
  headerTitle?: string;            // "Styles (3)" 등
  emptyState?: ReactNode;          // 커스텀 EmptyState

  // 디테일 패널 (우측)
  renderDetail: (item: T) => ReactNode;
  detailEmptyTitle?: string;       // 미선택 시 안내 문구
  detailEmptyDescription?: string;
};
```

**레이아웃 구조:**
```
┌──────────────────────────────────────────────────┐
│ (SubNavShell 탭 바 — 기존 유지)                     │
├──────────────┬───────────────────────────────────┤
│  Master      │  Detail                          │
│  w-80 (320px)│  flex-1                          │
│              │                                   │
│  [검색 입력]   │  (선택 시) renderDetail(item)      │
│  [+ 추가 버튼] │  (미선택 시) 안내 문구 + 아이콘      │
│              │                                   │
│  [아이템 1]   │                                   │
│  [아이템 2]   │                                   │
│  [아이템 3]   │                                   │
│  ...         │                                   │
└──────────────┴───────────────────────────────────┘
```

**반응형 동작 (모바일 < 768px):**
- `selectedId === null`: 마스터 패널만 전체 폭 렌더링
- `selectedId !== null`: 디테일 패널 전체 폭 + 상단에 "< 목록" 뒤로가기 버튼
- 구현: `md:flex` 미디어쿼리로 2패널 표시, 모바일은 조건부 렌더링

**마스터 패널 세부:**
- 상단: `headerTitle` + `headerAction` 가로 배치
- 검색: `searchValue` / `onSearchChange` 제공 시 검색 입력 렌더링 (SEARCH_INPUT_CLASSES 재사용)
- 목록: `overflow-y-auto`로 스크롤, 아이템 클릭 시 `onSelect(item.id)` 호출
- 로딩: `isLoading` 시 `LoadingSpinner` 표시
- 빈 상태: 아이템 0개 시 `emptyState` 또는 기본 EmptyState 표시

**디테일 패널 세부:**
- 미선택 시: 중앙에 안내 아이콘 + 텍스트 (EmptyState variant="default" 활용)
- 선택 시: `renderDetail(selectedItem)` 렌더링, `overflow-y-auto`

### 2. 기존 파일 수정: `frontend/app/components/layout/AppSidebar.tsx`

**결정: 삭제하지 않고 보류.**

근거:
- AppSidebar는 현재 코드베이스에서 import 0건 (미사용)
- LibraryMasterDetail의 마스터 패널과 역할이 겹치지만, AppSidebar는 collapsible + group 기능에 특화
- LibraryMasterDetail은 검색 + 단순 리스트에 특화 — 용도가 다름
- AppSidebar는 향후 Settings 등에서 활용 가능성 존재
- DoD의 "처리 결정" 항목은 "삭제하지 않고 보류" 로 충족

### 3. 타입 파일 수정 없음

`LibraryMasterDetailProps`는 컴포넌트 파일 내부에 정의.
- 후속 태스크(SP-060a/b/c)에서 각 도메인별 아이템 타입은 이미 `app/types/index.ts`에 존재 (StyleProfileFull, VoicePreset 등)
- 이 컴포넌트는 제네릭 `T extends { id: number }`로 동작하므로 추가 타입 불필요

### 4. 파일 변경 요약

| 파일 | 변경 | 설명 |
|------|------|------|
| `frontend/app/components/layout/LibraryMasterDetail.tsx` | **신규** | 공통 Master-Detail 레이아웃 (~150줄) |

총 변경 파일: 1개 (신규)

---

## 테스트 전략

### 1. 단위 테스트: `frontend/app/components/__tests__/LibraryMasterDetail.test.tsx`

기존 컴포넌트 테스트 패턴(`Button.test.tsx` 등) 준수. vitest + @testing-library/react.

**테스트 케이스 (7개):**

| # | 테스트 | 검증 내용 |
|---|--------|----------|
| 1 | 기본 렌더링 | items 전달 시 renderItem이 각 아이템에 대해 호출됨 |
| 2 | 아이템 선택 | 아이템 클릭 시 onSelect 콜백 호출 |
| 3 | 디테일 렌더링 | selectedId 설정 시 renderDetail 호출, 결과 DOM에 존재 |
| 4 | 미선택 상태 | selectedId=null일 때 detailEmptyTitle 텍스트 표시 |
| 5 | 검색 입력 | searchValue/onSearchChange 제공 시 검색 입력 렌더링, 입력 시 콜백 호출 |
| 6 | 로딩 상태 | isLoading=true 시 LoadingSpinner 렌더링 |
| 7 | 빈 목록 | items=[] 시 emptyState 또는 기본 빈 상태 표시 |

### 2. VRT / E2E

SP-099 자체는 신규 컴포넌트만 추가하므로 기존 페이지에 영향 없음. VRT/E2E는 후속 태스크(SP-060a/b/c)에서 각 페이지 전환 시 수행.
