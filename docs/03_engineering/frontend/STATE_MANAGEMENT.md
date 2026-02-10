# Frontend State Management

## Abstract
본 문서는 Shorts Producer 프론트엔드(Next.js 15)의 상태 관리 전략을 설명합니다. Zustand 5를 이용한 전역 데이터 흐름과 커스텀 훅을 통한 서버 데이터 연동 방식을 다룹니다.

---

## 1. 전역 상태 관리 (Zustand)

애플리케이션의 핵심 도메인 상태는 `app/store` 하위의 모듈화된 Zustand Store로 관리됩니다.

### Modular Store Structure (`useStudioStore`)

```typescript
// app/store/useStudioStore.ts
export type StudioState = PlanSlice & ScenesSlice & OutputSlice & MetaSlice & ContextSlice;
```

| Slice | 파일 | 역할 |
|-------|------|------|
| **`planSlice`** | `slices/planSlice.ts` | 전략적 설정 (Character, Style Profile, LoRA 가중치 등) |
| **`scenesSlice`** | `slices/scenesSlice.ts` | 현재 작업 중인 스토리보드의 모든 씬 데이터 및 편집 상태 |
| **`metaSlice`** | `slices/metaSlice.ts` | 스토리보드 메타 정보 (제목, ID, 타임스탬프 등) |
| **`outputSlice`** | `slices/outputSlice.ts` | 렌더링 결과물 링크 및 렌더 설정 |
| **`contextSlice`** | `slices/contextSlice.ts` | Project/Group 컨텍스트 및 Cascading Config 상태 |

> **삭제됨** (Phase 7-2 1.5): `profileSlice` — Channel Profile → Project로 통합됨. 스타일 프로필 관련 로직은 `actions/styleProfileActions.ts`로 이관.

### `contextSlice` 상세 (Phase 7-2 신규)

Cascading Config 시스템의 프론트엔드 상태를 관리합니다.

```typescript
interface ContextSlice {
  projects: ProjectItem[];
  groups: GroupItem[];
  isLoadingProjects: boolean;
  isLoadingGroups: boolean;
  effectivePresetName: string | null;    // 적용 중인 Render Preset 이름
  effectivePresetSource: string | null;  // 설정 출처 ("project" | "group" | "system_default")
  effectiveStyleProfileId: number | null;
  effectiveCharacterId: number | null;
  effectiveConfigLoaded: boolean;
}
```

### Persistence
- `persist` 미들웨어를 사용하여 `localStorage`에 자동 저장.
- 페이지 새로고침 후에도 작업 상태 유지 (`useDraftPersistence` 훅 연동).
- `draftMigration.ts`: 버전별 자동 마이그레이션 (예: `subtitleFont` → `sceneTextFont`).

---

## 2. Actions (비동기 액션)

`app/store/actions/` 폴더에서 도메인별 비동기 액션을 관리합니다.

| 파일 | 역할 |
|------|------|
| `autopilotActions.ts` | Compose → Generate → Validate 워크플로우 |
| `batchActions.ts` | 배치 이미지 생성 |
| `groupActions.ts` | Group CRUD 및 선택 |
| `imageActions.ts` | 이미지 생성/저장/후보 관리 |
| `outputActions.ts` | 렌더링 결과물 관리 |
| `projectActions.ts` | Project CRUD 및 선택 |
| `promptActions.ts` | 프롬프트 Compose/Rewrite |
| `promptHelperActions.ts` | 프롬프트 보조 (split, suggest) |
| `sceneActions.ts` | 씬 편집/순서 변경 |
| `storyboardActions.ts` | 스토리보드 CRUD/로드/저장 |
| `styleProfileActions.ts` | Style Profile 선택/적용 |
| `youtubeActions.ts` | YouTube OAuth 및 업로드 |

---

## 3. Selectors

`app/store/selectors/` 폴더에서 파생 상태를 계산합니다.

| 파일 | 역할 |
|------|------|
| `projectSelectors.ts` | 현재 프로젝트/그룹 관련 파생 상태 |

---

## 4. 서버 데이터 연동 (Custom Hooks & Axios)

React Query 대신, 도메인별 커스텀 훅을 통해 `axios`로 데이터를 페칭하고 로컬 상태(`useState`)로 관리하는 패턴을 사용합니다.

| Hook | 역할 |
|------|------|
| **`useAutopilot`** | 복합 생성 시퀀스 (Compose → Generate → Validate) 워크플로우 제어 |
| **`useCharacters`** | 캐릭터 목록 및 선택 관리 |
| **`useDraftPersistence`** | localStorage 드래프트 자동 저장/복원 |
| **`useProjectGroups`** | Project/Group 목록 로드 및 CRUD |
| **`useStudioInitialization`** | 스튜디오 페이지 초기화 (데이터 로드, 컨텍스트 설정) |
| **`useStudioOnboarding`** | 첫 실행 온보딩 가이드 |
| **`useTagClassifier`** | 태그 자동 분류 |
| **`useTagValidation`** | 태그 충돌/의존성 검증 |
| **`useTags`** | 태그 목록 조회 및 그룹화 |
| **`useYouTubeUpload`** | YouTube OAuth 연동 및 영상 업로드 워크플로우 |

---

## 5. 데이터 흐름 패턴

```
[User Action]
     ↓
[Action Dispatch] (app/store/actions/)
     ↓
[Backend API Call] (axios)
     ↓
[Store Update] (Zustand set())
     ↓
[Re-render] (React)
```

1. **Backend Fetch**: 커스텀 훅에서 API 호출.
2. **Global Sync**: 핵심 정보(선택된 캐릭터 ID, 프로젝트/그룹 등)를 Zustand Store에 저장.
3. **Action Dispatch**: 사용자 입력은 `actions/` 폴더의 비동기 액션으로 Backend 요청과 Store 업데이트를 동시 처리.
4. **Cascading Config**: Project/Group 선택 시 `contextSlice`에 effective 설정 로드.

---

**Last Updated:** 2026-02-10
