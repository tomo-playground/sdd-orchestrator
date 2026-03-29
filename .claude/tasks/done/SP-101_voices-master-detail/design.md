# SP-101: Voices 페이지 LibraryMasterDetail 전환 — 상세 설계

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `frontend/app/(service)/library/voices/page.tsx` | 전면 재작성 | 카드 그리드 → LibraryMasterDetail 전환 |
| `frontend/app/(service)/library/voices/VoiceDetailPanel.tsx` | 신규 | 뷰 모드 + 편집 모드 (MusicDetailPanel 패턴) |
| `frontend/app/(service)/library/voices/VoiceEditForm.tsx` | 신규 | 편집 폼 필드 추출 (MusicEditForm 패턴) |
| `frontend/app/hooks/useVoicePresets.ts` | 수정 | `onCreated` 콜백 추가 (생성 후 자동 선택) |
| `frontend/app/(service)/library/voices/VoiceCard.tsx` | 삭제 | LibraryMasterDetail로 대체 |
| `frontend/app/(service)/library/voices/VoiceCardSkeleton.tsx` | 삭제 | LibraryMasterDetail 내장 스켈레톤으로 대체 |

---

## DoD 1: Voices 페이지 LibraryMasterDetail 사용

### 참고 패턴

SP-102(Music) 구현을 1:1 참조. 구조:
- `page.tsx` → `LibraryMasterDetail<VoicePreset>` 사용
- `VoiceDetailPanel.tsx` → `MusicDetailPanel.tsx` 대응 (뷰/편집 모드 분기)
- `VoiceEditForm.tsx` → `MusicEditForm.tsx` 대응 (폼 필드)

### 구현 방법

#### 1-1. `page.tsx` 재작성

```typescript
// 기존: 카드 그리드 + 인라인 폼
// 변경: LibraryMasterDetail<VoicePreset>

export default function VoicesPage() {
  // useVoicePresets({ showToast, confirmDialog, onCreated })
  // useState<number | null>(null) for selectedId
  // LibraryMasterDetail<VoicePreset> with:
  //   - renderItem: 이름 + source_type 배지 + is_system 배지 + language
  //   - renderDetail: VoiceDetailPanel
  //   - filterFn: name + description 검색 (기존 동작 유지, voice_design_prompt는 포함하지 않음)
  //   - onAdd: handleCreateNew (selectedId null → handleCreate)
  //   - searchPlaceholder: "이름 또는 설명 검색..."
}
```

Escape 키 핸들러: 기존 Styles 패턴 그대로 유지 (selectedId → null).

#### 1-2. `VoiceDetailPanel.tsx` 신규

MusicDetailPanel.tsx 구조를 따른다.

```typescript
type Props = {
  preset?: VoicePreset;       // 뷰 모드 시 필수
  editing: EditingPreset | null;
  saving?: boolean;
  previewing?: boolean;
  previewUrl?: string | null;
  onEdit?: () => void;
  onDelete?: () => void;
  onSave: () => void;
  onCancel: () => void;
  onPreview: () => void;
  onPlayAudio: (url: string) => void;
  onSet: <K extends keyof EditingPreset>(key: K, value: EditingPreset[K]) => void;
};
```

- `editing != null` → VoiceEditForm 렌더
- `editing == null && preset` → 뷰 모드: 이름, 설명, voice_design_prompt, language, 재생 버튼

#### 1-3. `VoiceEditForm.tsx` 신규

기존 page.tsx 인라인 폼(라인 90-180)을 추출. 필드:
- Name (필수), Description, Voice Design Prompt (필수), Sample Text, Language (select)
- Preview 버튼 + Play Preview 버튼
- Save / Cancel 버튼

Language 옵션은 기존처럼 `/api/v1/presets` 에서 페치. `useEffect`로 마운트 시 로드.

#### 1-4. `useVoicePresets.ts` 수정

`UiCallbacks` 외에 `onCreated?: (id: number) => void` 콜백 추가:

```typescript
export function useVoicePresets(ui: UiCallbacks & { onCreated?: (id: number) => void }) {
```

`handleSave` 내부 create POST 성공 직후 (attach-preview 전):
```typescript
// CREATE POST 직후 호출 — attach-preview 완료를 기다리지 않음
// attach-preview 실패해도 항목은 생성됐으므로 선택 상태 유지가 올바른 UX
if (res.data.id) ui.onCreated?.(res.data.id);
```

#### 1-5. VoiceCard.tsx, VoiceCardSkeleton.tsx 삭제

LibraryMasterDetail의 master list + 내장 스켈레톤으로 대체.

### 동작 정의

| 상태 | Before | After |
|------|--------|-------|
| 목록 표시 | 카드 그리드 (3열) | 좌측 마스터 리스트 (w-80) |
| 선택 | 없음 (카드 클릭 → 편집 진입) | 클릭 → 우측 디테일 패널에 뷰 모드 |
| 편집 | 상단 인라인 폼 | 디테일 패널에서 Edit 버튼 → VoiceEditForm |
| 생성 | 상단 인라인 폼 | + 버튼 → 디테일 패널에 VoiceEditForm (생성 모드) |
| 검색 | 별도 input | 마스터 패널 상단 검색 |
| 삭제 | 카드 내 버튼 | 디테일 패널 헤더 버튼 |
| 모바일 | 카드 그리드 | 마스터 → 디테일 전환 (ArrowLeft 뒤로가기) |

### 엣지 케이스

1. **프리셋 0개**: `emptyState` prop으로 "음성 프리셋이 없습니다" + 생성 안내 표시
2. **검색 결과 0개**: LibraryMasterDetail 내장 "No results" 표시
3. **TTS 프리뷰 로딩 중**: `previewing` 상태 → 버튼 disabled + spinner
4. **오디오 재생**: 뷰 모드에서 Play 버튼 → `playAudio(preset.audio_url)`
5. **is_system 프리셋**: `renderDetail`에서 `onDelete` prop 미전달로 삭제 버튼 숨김 (`!item.is_system && onDelete={() => ...}`)
6. **생성 중 다른 항목 선택**: `handleCancel()` 호출 → 편집 상태 클리어
7. **모바일 생성 폼**: Music 패턴 동일 — absolute overlay + ArrowLeft 뒤로가기

### 영향 범위

- **Backend**: 변경 없음. 기존 API 그대로 사용.
- **다른 페이지**: 영향 없음. Voices 페이지 독립.
- **라우팅**: 변경 없음. `/library/voices` 유지.

---

## DoD 2: 기존 CRUD + TTS 미리보기 동일 동작

`useVoicePresets` 훅의 모든 기능이 그대로 유지됨을 확인:

| 기능 | 구현 위치 | 변경 여부 |
|------|-----------|-----------|
| 목록 조회 | `useVoicePresets.fetchPresets` | 변경 없음 |
| 생성 | `useVoicePresets.handleCreate` + `handleSave` | `onCreated` 콜백 추가만 |
| 편집 | `useVoicePresets.handleEdit` + `handleSave` | 변경 없음 |
| 삭제 | `useVoicePresets.handleDelete` | 변경 없음 |
| TTS 프리뷰 | `useVoicePresets.handlePreview` | 변경 없음 |
| 오디오 재생 | `useVoicePresets.playAudio` | 변경 없음 |

---

## DoD 3: VRT 베이스라인 갱신

- 레이아웃 변경이므로 기존 Voices 페이지 VRT 스냅샷이 있다면 갱신 필요
- E2E 테스트: CRUD + TTS 프리뷰 흐름 동작 확인

### 테스트 전략

기존 E2E가 있다면 레이아웃 변경에 따른 셀렉터 업데이트. 없다면:
- Voice 생성 → 리스트 표시 확인
- Voice 선택 → 디테일 패널 표시 확인
- Voice 편집 → 저장 → 반영 확인
- Voice 삭제 → 리스트에서 제거 확인

---

## Out of Scope

- Backend API 변경
- VoicePreset 타입 변경
- TTS 엔진 변경 (Qwen3 유지)
- 다른 Library 탭 변경
- 새로운 Voices 기능 추가
- `filterFn`에 `voice_design_prompt` 검색 추가 (기능 확장은 별도 태스크)

---

## 설계 리뷰 결과 (난이도: 중 — 패턴 복사, 에이전트 1라운드)

### 에이전트 설계 리뷰

| 리뷰어 | 판정 | 주요 피드백 |
|--------|------|------------|
| UI/UX Engineer | WARNING 2건 → 반영 완료 | 1) `onCreated` 호출 위치 명확화 (CREATE POST 직후, attach-preview 전) 2) `filterFn`에 `voice_design_prompt` 포함은 기능 확장 → Out of Scope로 분리 |
