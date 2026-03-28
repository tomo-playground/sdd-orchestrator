# SP-100 상세 설계: Styles → Master-Detail 전환

## 변경 파일 요약

| 파일 | 변경 | 난이도 |
|------|------|--------|
| `frontend/app/(service)/library/styles/page.tsx` | 카드 그리드 → LibraryMasterDetail 교체 | 중 |
| `frontend/app/(service)/library/styles/StyleProfileEditor.tsx` | onClose prop 제거, 레이아웃 조정 | 하 |
| `frontend/app/hooks/styles/useStyleTab.ts` | selectedId 상태 추가, handleLoadProfile 자동 호출 연결 | 하 |

난이도: **하** (변경 파일 3개, 신규 함수 없음, 기존 로직 재배치)

---

## DoD 1: Styles 페이지가 LibraryMasterDetail 사용

### 구현 방법

**page.tsx** — 카드 그리드 레이아웃을 `LibraryMasterDetail` 컴포넌트로 교체.

```
Before: 헤더 + 카드 그리드(2-3열) + 선택 시 사이드 패널
After:  LibraryMasterDetail (좌 목록 | 우 StyleProfileEditor)
```

**Props 매핑:**

| LibraryMasterDetail prop | 소스 |
|--------------------------|------|
| `items` | `styleProfiles` (StyleProfile은 이미 `{id, name}` 보유) |
| `selectedId` | `selectedProfileId` (useStyleTab에 추가) |
| `onSelect` | `handleSelectProfile(id)` — id 변경 시 `handleLoadProfile` 호출 |
| `renderDetail` | `(item) => <StyleProfileEditor profile={selectedProfile} .../>` |
| `renderItem` | 커스텀 행: `display_name ∥ name` + `is_default` 배지 + LoRA 수 |
| `onAdd` | `handleCreateStyle` |
| `searchPlaceholder` | `"화풍 검색..."` |
| `loading` | `isStyleLoading` |
| `emptyState` | "등록된 화풍이 없습니다" |
| `detailEmptyState` | "화풍을 선택하세요" |

**renderItem 커스텀 행 구조:**
```
┌─────────────────────────────┐
│ display_name || name        │
│ LoRA 2개 · 기본 ✓           │  ← is_default 시 배지
└─────────────────────────────┘
```

**useStyleTab 변경:**
- `selectedProfileId: number | null` 상태 추가 (기존 `selectedProfile` 객체와 병행)
- `handleSelectProfile(id: number | null)` 추가 — id 변경 시 `handleLoadProfile(id)` 호출, null이면 `setSelectedProfile(null)`

**StyleProfileEditor 변경:**
- `onClose` prop 제거 (Master-Detail에서는 목록 선택으로 전환, 별도 닫기 불필요)
- 헤더의 "Done" 버튼 → 제거 (모바일은 LibraryMasterDetail의 Back 버튼 사용)
- 최상위 컨테이너에 `p-6` 패딩 추가 (Detail 패널 내부 여백)

### 엣지 케이스

| 상황 | 처리 |
|------|------|
| 선택된 프로필 삭제 | `handleDeleteStyle` 후 `selectedProfileId = null` 리셋 |
| 새 프로필 생성 | `handleCreateStyle` 후 생성된 ID로 `selectedProfileId` 자동 설정 |
| 복제 | 복제된 프로필 ID로 `selectedProfileId` 자동 설정 |
| selectedProfile 로딩 중 | `selectedProfile === null && selectedProfileId !== null` → Detail 영역에 로딩 스피너 |
| 검색 필터 적용 중 선택 프로필이 필터에서 제외 | 선택 유지 (LibraryMasterDetail이 items에서 못 찾으면 detail은 빈 상태) |

### 영향 범위
- Styles 페이지 UI만 변경. API/스토어/타입 변경 없음.
- StyleProfileEditor 내부 로직(CRUD, LoRA 토글, 프롬프트 편집)은 변경 없음.
- useStyleTab의 기존 반환값은 유지, `selectedProfileId` + `handleSelectProfile` 추가만.

### 테스트 전략
- **Unit**: `useStyleTab`에서 `handleSelectProfile(id)` 호출 시 `handleLoadProfile` 연동 확인
- **VRT**: Styles 페이지 스크린샷 — Master-Detail 레이아웃, 선택/미선택 상태
- **E2E**: 기존 CRUD 플로우 (DoD 2에서 검증)

### Out of Scope
- LibraryMasterDetail 컴포넌트 자체 수정 (SP-099 소관)
- Characters/Voices/Music 탭 전환 (SP-101, SP-102 별도)
- API 엔드포인트 변경

---

## DoD 2: 기존 CRUD 기능 동일 동작

### 구현 방법

기존 `useStyleTab` 훅의 CRUD 함수를 그대로 사용. UI 바인딩만 변경.

| 기능 | 기존 트리거 | 변경 후 트리거 |
|------|-----------|-------------|
| 생성 | 헤더 "+ New Style" 버튼 | LibraryMasterDetail `onAdd` |
| 편집 | 카드 Edit 버튼 → 사이드 패널 | Master 목록 클릭 → Detail 패널 |
| 삭제 | 카드 삭제 아이콘 → ConfirmDialog | Detail 패널 내 삭제 버튼 또는 Master 행 컨텍스트 |
| 복제 | 카드 복제 아이콘 | Detail 패널 내 복제 버튼 |

**삭제/복제 버튼 위치:**
- Master 목록 `renderItem`에 삭제/복제 아이콘 배치 (hover 시 표시)
- 또는 Detail 패널 상단 액션 바에 배치
- **결정: Detail 상단 액션 바** — Master 행은 간결하게 유지, Detail에서 편집 중 삭제/복제가 자연스러움

**Detail 액션 바 구조:**
```
┌──────────────────────────────────────────────┐
│ [이름 편집]                   [복제] [삭제]   │
├──────────────────────────────────────────────┤
│ StyleProfileEditor 본문                      │
└──────────────────────────────────────────────┘
```

### 테스트 전략
- **E2E** (Playwright):
  1. 프로필 생성 → 목록에 표시 확인
  2. 프로필 선택 → Detail 패널에 에디터 표시 확인
  3. 이름 수정 → Master 목록 반영 확인
  4. 복제 → 새 항목 목록 추가 확인
  5. 삭제 → 목록에서 제거 + Detail 빈 상태 확인

### Out of Scope
- LoRA/Embedding 토글 로직 변경
- SD 모델 변경 로직 변경
- Admin API 엔드포인트 변경

---

## DoD 3: VRT 베이스라인 갱신

### 구현 방법
- 기존 Styles VRT 스크린샷 교체 (레이아웃 변경이므로 베이스라인 갱신 필수)
- 캡처 대상: 미선택 상태 (빈 Detail) + 선택 상태 (에디터 표시)

### 테스트 전략
- VRT `--update-snapshots` 실행 후 diff 확인
