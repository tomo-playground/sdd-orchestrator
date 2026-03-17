# Studio UI & Design Guide (v4.1)

Phase 7-6 ~ 9-2 반영. UI 아키텍처, 레이아웃 시스템, 디자인 토큰, 상태 관리를 정의합니다.

## 1. 글로벌 네비게이션

`AppShell` (`components/shell/AppShell.tsx`)이 모든 페이지를 감싸며, 상단 고정 네비바를 제공합니다.

| 탭 | 라우트 | 설명 |
|----|--------|------|
| **Home** | `/` | 대시보드 (Continue Working + Showcase + Quick Actions + Stats) |
| **Studio** | `/studio` | 스토리보드 칸반 또는 Script/Stage/Direct/Publish 4탭 에디터 |
| **Library** | `/library` | 에셋 라이브러리 (7탭: Characters, Backgrounds, Styles, Voices, Music, Prompts, Tags) |
| **Settings** | `/settings` | 앱/프로젝트 설정 (5탭: General, Memory, Presets, YouTube, Trash) |

**네비바 스타일**: `TAB_ACTIVE` (bg-zinc-900 text-white) / `TAB_INACTIVE`, Lucide 아이콘 + 텍스트 라벨.
**접근성**: Skip-to-content 링크, `Cmd+K` CommandPalette, `Cmd+S` 저장, `Cmd+Enter` AutoRun.

---

## 2. 레이아웃 시스템

### 2-1. StudioThreeColumnLayout (Studio 전용)

`components/studio/StudioThreeColumnLayout.tsx` -- Script/Stage/Direct/Publish 탭에서 사용.

```
[Left 280px] | [Center flex-1] | [Right 300px]
```

- **CSS**: `grid grid-cols-[280px_1fr_300px] gap-0 h-full min-h-[600px]`
- Left/Right: `bg-zinc-50/50` 배경, `border-r` / `border-l` 구분선
- Center: `flex flex-col overflow-y-auto`
- 디자인 토큰: `STUDIO_3COL_LAYOUT`, `LEFT_PANEL_CLASSES`, `CENTER_PANEL_CLASSES`, `RIGHT_PANEL_CLASSES`

### 2-2. AppThreeColumnLayout (Library / Settings 공용)

`components/layout/AppThreeColumnLayout.tsx` -- 접기 가능한 사이드바 포함.

```
[AppSidebar collapsible] | [Center flex-1] | [Right 300px]
```

- Left: `AppSidebar` (그룹별 접기/펴기, localStorage 영속)
- Center: 독립 스크롤, `bg-white`
- Right: 고정 300px, `bg-zinc-50/50`, padding 4

### 2-3. Home 레이아웃

`components/home/HomeVideoFeed.tsx` -- 반응형 2컬럼 대시보드.

```
[Primary 2fr] | [Sidebar 1fr (lg+)]
```

- Primary: `ContinueWorkingSection` + `ShowcaseSection`
- Sidebar: `QuickActionsWidget` + `QuickStatsWidget`
- CSS: `grid gap-6 lg:grid-cols-[2fr_1fr]`

### 2-4. Studio Kanban (스토리보드 미선택 시)

`/studio` 진입 시 스토리보드 ID가 없으면 `StudioKanbanView` 칸반 보드 표시.

```
[Kanban Columns (Draft | In Prod | Rendered | Published)] | [Secondary Panel (xl+)]
```

- CSS: `PAGE_2COL_LAYOUT` = `grid gap-6 xl:grid-cols-[1fr_var(--secondary-panel-width)]`
- Secondary: `HomeSecondaryPanel` (Quick Stats + Recently Updated)

---

## 3. Studio 4탭 워크플로우

### 3-1. Script 탭

대본 작성. Quick/Full 모드 토글.

| 패널 | 컴포넌트 | 역할 |
|------|----------|------|
| LEFT | `ScriptSceneList` | 씬 아웃라인 목록 + Approve 버튼 |
| CENTER | `ManualScriptEditor` | 토픽 입력, 씬 생성/편집 (Quick/Full 토글) |
| RIGHT | `ScriptSidePanel` | Status(모드/씬수) + Tips |

### 3-2. Stage 탭

이미지/TTS/BGM 사전 준비 단계. 씬별 에셋을 생성하고 검증한다.

| 패널 | 컴포넌트 | 역할 |
|------|----------|------|
| LEFT | `SceneListPanel` | 드래그&드롭 순서 변경, 완성도 표시(4-dot), 이미지 검증 상태 |
| CENTER | 씬 이미지 생성 + TTS/BGM 준비 | 씬별 이미지 생성, 음성/배경음악 사전 준비 |
| RIGHT | 에셋 상태 패널 | 씬별 에셋 준비 상태 확인 |

### 3-3. Direct 탭

씬 편집 (이미지 생성, 프롬프트, 캐릭터 액션 등).

| 패널 | 컴포넌트 | 역할 |
|------|----------|------|
| LEFT | `SceneListPanel` | 드래그&드롭 순서 변경, 완성도 표시(4-dot), 이미지 검증 상태 |
| CENTER | `SceneNavHeader` + `SceneCard` | 씬 네비게이션(이전/다음) + 스크립트/프롬프트/이미지/액션 편집 |
| RIGHT | Image / Tools / Insight 서브탭 | 이미지 설정, 도구, 인사이트 |

### 3-4. Publish 탭

렌더링 설정 + 미리보기 + 배포.

| 패널 | 컴포넌트 | 역할 |
|------|----------|------|
| LEFT | `RenderSidePanel` | Layout 선택, Frame 스타일, Render 버튼, Progress/ETA |
| CENTER | `VideoPreviewHero` + `RenderMediaPanel` | 비디오 미리보기(9:16) + 미디어 설정(폰트/BGM/음성/전환) |
| RIGHT | `PublishCaptionLikes` + `PublishVideosSection` | 캡션/좋아요 설정 + 최근 렌더 영상 목록 |

### Sub-Nav Bar (Studio 에디터 모드)

스토리보드 선택 시 표시되는 서브 네비바.

```
[ContextBar 제목] | [PipelineStatusDots + MaterialsPopover + StudioWorkspaceTabs] | [StoryboardActionsBar]
```

- `PipelineStatusDots`: Script/Stage/Direct/Publish 4단계 상태 (done/progress/idle)
- `StudioWorkspaceTabs`: Script | Stage | Direct | Publish 4탭 (배지: 씬 수, 렌더 진행률)
- `StoryboardActionsBar`: AutoRun, Save 버튼

---

## 4. Library 페이지

`/library?tab=<tab>` -- `AppThreeColumnLayout` + `AppSidebar` 사용.

### 사이드바 그룹

| 그룹 | 탭 |
|------|-----|
| **Visuals** | Characters, Backgrounds, Styles |
| **Audio** | Voices, Music |
| **Text & Meta** | Prompts, Tags |

**모바일**: `AppMobileTabBar` (lg 미만에서 상단 스크롤 가능 탭바 표시).

### 콘텐츠 영역

각 탭은 독립 컴포넌트를 렌더링합니다: `CharactersContent`, `BackgroundsContent`, `StyleTab`, `VoicesContent`, `MusicContent`, `PromptsTab`, `TagsTab`.

Right 패널: `LibrarySecondaryPanel` (탭별 보조 정보).

---

## 5. Settings 페이지

`/settings?tab=<tab>` -- `AppThreeColumnLayout` + `AppSidebar` 사용.

### 사이드바 그룹

| 그룹 | 탭 |
|------|-----|
| **General** | App Settings, AI Memory |
| **Project** | Render Presets, YouTube |
| **(System)** | Trash |

> Trash는 시스템 아이템으로 분리되어 ungrouped 영역에 배치됩니다.

Right 패널: `SettingsSecondaryPanel` (탭별 보조 정보).

---

## 6. 독립 페이지

라우트 그룹 `(app)/` 내의 독립 페이지들입니다.

| 라우트 | 컴포넌트 | 설명 |
|--------|----------|------|
| `/characters` | `CharactersContent` | 캐릭터 목록 (카드 그리드) |
| `/characters/[id]` | `CharacterDetailSections` | 캐릭터 상세 (태그, LoRA, 프롬프트) |
| `/characters/new` | 리다이렉트 | 캐릭터 빌더로 리다이렉트 |
| `/characters/builder` | `CharacterWizard` | 3단계 위자드 (Basic Info, Appearance, LoRA) |
| `/storyboards` | `StoryboardCard` 리스트 | 스토리보드 목록 |
| `/voices` | `VoiceCard` 리스트 | 음성 프리셋 목록 |
| `/music` | `MusicCard` 리스트 | 음악 프리셋 목록 |
| `/backgrounds` | `BackgroundCard` 리스트 | 배경 에셋 목록 |
| `/scripts` | 스크립트 관리 | 스크립트 페이지 |
| `/lab` | `LabSidebar` + 3탭 | 실험 기능 (SceneLab, TagLab, Analytics) |
| `/pipeline-demo` | 파이프라인 데모 | 파이프라인 시각화 |

---

## 7. 공유 레이아웃 컴포넌트

### AppShell

`components/shell/AppShell.tsx` -- 모든 페이지의 최상위 레이아웃.

- `ConnectionGuard`로 Backend 연결 상태 감시
- 글로벌 네비바 (Home, Studio, Library, Settings)
- `CommandPalette` (`Cmd+K`)
- Toast 렌더링

### AppSidebar

`components/layout/AppSidebar.tsx` -- Library/Settings 공용 사이드바.

- **Props**: `groups` (NavGroup[]), `items` (NavItem[]), `ungroupedItems`, `activeTab`, `onTabChange`
- **기능**: 접기/펴기 (localStorage 영속), 그룹 접기/펴기, 아이콘 + 라벨
- **스타일**: `SIDEBAR_ACTIVE` (border-l-2 + bg-zinc-100), `SIDEBAR_INACTIVE`
- **반응형**: `hidden lg:flex` (모바일에서 숨김, `AppMobileTabBar`로 대체)

### AppMobileTabBar

`components/layout/AppMobileTabBar.tsx` -- 모바일 전용 상단 탭바.

- `lg:hidden`, 고정 위치 (top: nav-height), 수평 스크롤
- `TAB_ACTIVE` / `TAB_INACTIVE` 스타일

---

## 8. 디자인 토큰 (variants.ts)

`components/ui/variants.ts`에 모든 디자인 토큰을 중앙 관리합니다.

### 레이아웃

| 토큰 | 값 | 용도 |
|------|-----|------|
| `STUDIO_3COL_LAYOUT` | `grid grid-cols-[280px_1fr_300px]...` | Studio 3컬럼 |
| `PAGE_2COL_LAYOUT` | `grid gap-6 xl:grid-cols-[1fr_var(--secondary-panel-width)]` | 2컬럼 (Kanban) |
| `CONTAINER_CLASSES` | `mx-auto w-full max-w-7xl px-6` | 페이지 컨테이너 |

### 네비게이션

| 토큰 | 용도 |
|------|------|
| `NAV_CLASSES` | 최상위 네비바 (sticky, backdrop-blur) |
| `SUB_NAV_CLASSES` | 서브 네비바 (Studio 에디터) |

### 패널

| 토큰 | 용도 |
|------|------|
| `LEFT_PANEL_CLASSES` | Studio 좌측 패널 (bg-zinc-50/50, border-r) |
| `RIGHT_PANEL_CLASSES` | Studio 우측 패널 (bg-zinc-50/50, border-l, p-4) |
| `CENTER_PANEL_CLASSES` | Studio 중앙 패널 (flex-col, overflow-y-auto) |
| `SIDE_PANEL_CLASSES` | 플로팅 사이드 카드 (sticky, rounded-2xl, border) |
| `SIDE_PANEL_LABEL` | 사이드 패널 섹션 라벨 (12px uppercase tracking) |

### 인터랙티브 상태

| 토큰 | 값 |
|------|-----|
| `TAB_ACTIVE` | `bg-zinc-900 text-white` |
| `TAB_INACTIVE` | `text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100` |
| `SIDEBAR_ACTIVE` | `border-l-2 border-zinc-900 bg-zinc-100 pl-2 font-medium text-zinc-900` |
| `SIDEBAR_INACTIVE` | `text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700` |
| `FILTER_PILL_ACTIVE` | `bg-zinc-900 text-white` |
| `FILTER_PILL_INACTIVE` | `bg-zinc-100 text-zinc-500 hover:bg-zinc-200` |

### 폼

| 토큰 | 용도 |
|------|------|
| `FORM_INPUT_CLASSES` | 기본 인풋 (rounded-2xl) |
| `FORM_INPUT_COMPACT_CLASSES` | 컴팩트 인풋 (rounded-lg) |
| `FORM_TEXTAREA_CLASSES` | 텍스트에어리어 (rounded-2xl, shadow-inner) |
| `FORM_LABEL_CLASSES` | 폼 라벨 (12px uppercase) |
| `FORM_LABEL_COMPACT_CLASSES` | 컴팩트 라벨 (text-xs semibold) |

### 시맨틱 컬러

| 상태 | BG | Text | Border | Button |
|------|-----|------|--------|--------|
| Success | `bg-emerald-50` | `text-emerald-700` | `border-emerald-200` | `bg-emerald-600` |
| Error | `bg-red-50` | `text-red-700` | `border-red-200` | `bg-red-600` |
| Warning | `bg-amber-50` | `text-amber-700` | `border-amber-200` | `bg-amber-600` |
| Info | `bg-indigo-50` | `text-indigo-700` | `border-indigo-200` | `bg-indigo-600` |

---

## 9. 테마 & Typography

### 테마

- **Light Theme**: zinc 기반 (bg-gradient-to-br from-zinc-50 via-white to-zinc-100)
- 사이드바/패널: `bg-zinc-50/50`, 카드: `bg-white`
- Dark Theme는 Phase 7-X에서 제거됨

### Typography 규칙 (CLAUDE.md SSOT)

| 용도 | 최소 크기 | 권장 |
|------|----------|------|
| 배지/보조 텍스트 | `text-[11px]` | 11px |
| 라벨/캡션 | `text-[12px]` | 12px |
| 본문/버튼/탭 | `text-xs` (13px) | `text-xs` 이상 |
| 입력 필드/제목 | `text-sm` (15px) | `text-sm` 이상 |

**금지**: `text-[9px]`, `text-[10px]` 사용 금지.

---

## 10. 상태 관리 (Zustand)

4개 스토어로 관심사 분리.

| 스토어 | 파일 | 역할 |
|--------|------|------|
| `useUIStore` | `store/useUIStore.ts` | UI 상태 (activeTab, rightPanelTab, 모달, 토스트) |
| `useStoryboardStore` | `store/useStoryboardStore.ts` | 씬 데이터, 유효성 검증, 이미지 생성 상태 |
| `useRenderStore` | `store/useRenderStore.ts` | 렌더링 설정, 진행률, 비디오 URL |
| `useContextStore` | `store/useContextStore.ts` | 프로젝트/그룹/프리셋 컨텍스트 |

**리셋**: `resetAllStores.ts`로 전체 초기화 (스토리보드 삭제 시).

상세는 [STATE_MANAGEMENT.md](../03_engineering/frontend/STATE_MANAGEMENT.md) 참조.

---

## 11. UI Components

공통 컴포넌트(Input, Textarea, Button, Modal, ConfirmDialog, Toast, Badge, EmptyState, Skeleton 등)의 상세 사용법은 [UI Components Guide](UI_COMPONENTS.md)를 참조하세요.
