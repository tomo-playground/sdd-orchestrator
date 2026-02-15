# Shorts Factory Master Roadmap

**원칙**: 안정성 → 리팩토링 → 안정성 → 신규 개발 사이클. 영상 품질 100% 일관성(Zero Variance) 유지.

---

## Phase 1-4: Foundation & Refactoring - ARCHIVED

완료. [Phase 1-4 아카이브](../99_archive/archive/ROADMAP_PHASE_1_4.md) 참조.

---

## Phase 5: High-End Production - ARCHIVED

검증된 안정적인 기반 위에 프로덕션 기능을 구축. **전체 완료**.

| 섹션 | 핵심 성과 | 상태 |
|------|----------|------|
| 5-1. 운영 효율화 | Resume/Checkpoint, Smart AutoRun, Secure Config | [x] |
| 5-2. 영상 품질 강화 | Ken Burns, Scene Text Animation, 13개 전환 효과, Full/Post Layout | [x] |
| 5-3. 콘텐츠 확장 | Preset System, Sample Topics, 일본어/수학 템플릿 | [x] |
| 5-4. Prompt Analytics | 정량적 품질 지표, Gemini 프롬프트 검증 | [x] |
| 5-5. UI/UX 개선 | SD 파라미터 Advanced 이동, Media Defaults, Render UX | [x] |
| 5-6. UI Polish | Loading/Error UI, Character Image Modal | [x] |
| 5-7. QA | Backend 335 + Frontend 67 = **총 402개** 테스트 | [x] |

미완료 항목은 Feature Backlog 또는 Phase 7-1로 이동.

---

## Phase 6: Character & Prompt System (v2.0) - ARCHIVED

다중 캐릭터 지원 및 프롬프트 빌더 시스템 구축. **전체 완료**.

**환경**: animagine-xl (SDXL), eureka_v9/chibi-laugh LoRA, 9종 Preset

| 섹션 | 핵심 성과 | 상태 |
|------|----------|------|
| 6-1~6-4. Core Architecture | PostgreSQL/Alembic, 12-Layer PromptBuilder, Gender/Pose/Expression, Civitai/ControlNet/IP-Adapter | [x] |
| 6-5. Stability & Integrity | P0/P1 25건 수정 (DB FK/인덱스, Session Leak, FFmpeg FPS, Gemini 파싱) | [x] |
| 6-6. Code Health & Testing | 대형 파일 5건 분리, Router/Service 분리, 비동기 Gemini, 786개 테스트 | [x] |
| 6-7. Infrastructure & DX | CI, Soft Delete, Common UI, WD14 Feedback, Voice/TTS, Batch Gen, Schema Cleanup | [x] |
| 6-8. Local AI Engine | Qwen3-TTS 로컬 (MPS), Stable Audio BGM, Voice/Music Presets CRUD | [x] |

미완료 항목은 Feature Backlog 또는 후속 Phase로 이동. 상세: [Phase 6 아카이브](../99_archive/archive/ROADMAP_PHASE_6.md)

---

## Phase 7-0: ControlNet & Pose Control - ARCHIVED

완료. ControlNet 포즈 제어, IP-Adapter 캐릭터 일관성 시스템 구축.
- 2026-02-02: thumbs_up 포즈 추가 (28번째 포즈, 포즈 에셋 + synonyms)

---

## Phase 7-1: UX & Feature Expansion

**목표**: 사용자 경험 개선 및 핵심 신규 기능 추가.
**선행**: Phase 6-7 완료 (CI, Soft Delete, UI Toolkit).

| # | 작업 | 분류 | 참조 | 상태 |
|---|------|------|------|------|
| 1 | Quick Start Flow: +New Story Lazy Creation (첫 Save/Generate 시 DB 저장), PlanTab 설정/스토리 재설계, 인라인 StyleProfile 셀렉터 | UX | [명세](FEATURES/UX_IMPROVEMENTS.md) | [x] |
| 2 | ~~Setup Wizard (첫 실행 가이드)~~ | ~~UX~~ | ~~[명세](FEATURES/UX_IMPROVEMENTS.md)~~ | N/A (ConnectionGuard + MaterialsCheck + StyleOnboarding으로 대체) |
| 3 | 접근성 기본 (ARIA, focus trap, keyboard) | UX | - | [x] |
| 4 | ~~이미지 생성 Progress (WebSocket/SSE)~~ | ~~기능~~ | → 7-5 B #11 | [x] |
| 5 | Multi-Character UI (DB 스키마 완료) | 기능 | [명세](FEATURES/MULTI_CHARACTER.md) | [x] |
| 6 | Scene Builder UI (배경/시간/날씨) | 기능 | [명세](FEATURES/SCENE_BUILDER_UI.md) | [x] |
| 7 | Structure별 전용 Gemini 템플릿 (3종 structure = 3종 템플릿 1:1 매핑 완료) | 기능 | - | [x] |
| 8 | Character Builder 위저드 (Quick Start 템플릿 + 3-step: Basic→Appearance→LoRA, 카테고리 칩 그리드, LoRA 카드 브라우저, SD 프리뷰) | 기능 | [명세](FEATURES/CHARACTER_BUILDER.md) | [x] |
| 25 | Character Management 독립 페이지 (/characters 목록 + /characters/[id] 상세/편집) | UX | [명세](FEATURES/CHARACTER_PAGE.md) · [와이어프레임](../02_design/wireframes/CHARACTER_PAGE_WIREFRAME.md) | [x] |
| 9 | OutputTab 채널/영상 분리 | UX | [설계](../02_design/UI_PROPOSAL.md) | [x] |
| 10 | Creative Lab & Engine (Tag Lab + Scene Lab + Multi-Agent Creative) | 기능 | [API](../03_engineering/api/REST_API_CREATIVE.md) | [x] |
| 11 | Studio UI Polish (Video탭 통합, Global 접기, Save 이동, 캐릭터 프리뷰 확대) | UX | - | [x] |
| 12 | 씬 텍스트 하단 배치 + 드롭섀도우 + Color Grade | 영상 품질 | - | [x] |
| 13 | Gemini 스크립트 길이 제한 강화 (30자/Korean) | 품질 | - | [x] |
| 14 | Character Identity Injection (Gemini 스토리보드에 캐릭터 태그/LoRA 주입 + 오토파일럿 overlay 수정) | 품질 | - | [x] |
| 15 | 좌측 사이드바 네비게이션 + 컨텍스트 전환 버그 수정 (Phase A 버그 6건 + Phase B 사이드바 완료. Phase C ContextBar 정리 보류) | UX | [명세](../99_archive/features/SIDEBAR_NAVIGATION.md) | [x] |
| 16 | Insights 탭 Studio → Manage 이동 (QualityDashboard + AnalyticsDashboard, 스토리보드 셀렉터) | UX | - | [x] |
| 17 | YouTube Shorts Upload (OAuth + per-project credential + upload modal) | 기능 | [명세](FEATURES/YOUTUBE_UPLOAD.md) | [x] |
| 18 | Dialogue & Narrated Dialogue 구조 (2-character + 3-speaker Narrator) | 기능 | - | [x] |
| 19 | 렌더링 진행률 SSE 스트리밍 (실시간 % 표시) | UX | - | [x] |
| 20 | Style LoRA Unification + Embedding trigger words 프롬프트 주입 | 품질 | - | [x] |
| 21 | Narrator Scene 스타일 적용 (image_prompt 백엔드 주입 + ControlNet/IP-Adapter 자동 비활성) | 품질 | - | [x] |
| 22 | image_url 정합성 강화 (JSONB 저장 방어, base64 전송 방지, stale ID 방어) | 안정성 | - | [x] |
| 23 | Background Scene 태그 필터링 (no_humans 감지 → 캐릭터 레이어 제거) + LoRA Weight Cap 통합 (0.76) | 품질 | - | [x] |
| 24 | Creative Lab V2: 쇼츠 멀티에이전트 시나리오 생성기 (9-Agent Pipeline + Studio 연동) | 기능 | [명세](../99_archive/features/CREATIVE_LAB_V2.md) | [x] |
| 26 | Storyboards 독립 페이지 (/storyboards 리스트 + 필터/검색/삭제, 홈 요약 축소) | UX | - | [x] |
| 27 | Production Workspace 네비게이션 (재료별 독립 메뉴 그룹핑 + Studio 분리 + Voices/Music 탑메뉴 승격) | UX | - | [x] |

---

## Phase 7-2: Project/Group System

**목표**: 채널(Project) + 시리즈(Group) 계층 구조 구현. 설정 상속, 서사 톤 자동 주입, 데이터 기반 태그 추천.
**선행**: Phase 6-7 일부 (DB 마이그레이션 인프라). Phase 0은 6-7과 병렬 가능.

| Phase | 핵심 | 상태 |
|-------|------|------|
| Phase 0: Foundation | DB 마이그레이션, CRUD API, FK 연결 | [x] |
| Phase 1: Core | FK 강화, 캐릭터 프로젝트 스코핑, 렌더 프리셋 분리, 설정 상속 엔진, 그룹 편집 UI | [x] |
| Phase 1.5: UX 정리 | Channel Profile → Project 통합, 캐릭터 글로벌화, +New Storyboard 그룹 내부 이동, Studio UX Polish | [x] |
| Phase 1.7: Group Defaults | 그룹 cascade 확장 (language, structure, duration, narrator_voice), Manage 그룹 기본값 편집 UI. [명세](../99_archive/features/GROUP_DEFAULTS.md) | [x] |
| Phase 2-1: Channel DNA | 그룹별 톤/세계관/가이드라인 JSONB 저장 + Gemini 스토리보드 자동 주입 | [x] |
| Phase 2-2~3: Intelligence | Tag Intelligence, Series Intelligence → Phase 9 Agentic Pipeline에서 통합 | [ ] |
| Phase 3: Advanced | 배치 렌더링, 브랜딩, 분석 대시보드 | [ ] |

**Phase 1.5 세부 완료 항목** (2026-02-02):
- Channel Profile → Project 통합 (profileSlice 삭제, avatar_key DB 이관)
- 캐릭터 글로벌화 (project_id nullable, 전역 유니크)
- ProjectDropdown 아바타/편집 UI, ProjectFormModal 캐릭터 셀렉터
- `page.tsx` God Component 분리 (545줄 → 107줄 + StoryboardsSection + CharactersSection)
- OutputTab 채널 프로필 섹션 제거, Current Style 섹션 제거
- TabBar 프로젝트 정보 중복 제거
- PromptSetupPanel Global/Actor A 탭 → 별도 카드 분리
- Actor A Advanced Settings (SD Parameters) 제거 (Style Profile로 통합)
- StoryboardActionsBar Reset 버튼 제거
- StoryboardGeneratorPanel Visual Style 필드 제거, Language select 전환
- ContextBar breadcrumb chevron 아이콘, Home 아이콘 전환
- Manage > Assets 표시명 개선 (확장자 제거, flex wrap)

상세: [기능 명세](FEATURES/PROJECT_GROUP.md)

---

## Phase 7-3: Production Workspace

**목표**: "재료 준비 → 통합 렌더링" 2단계 워크플로우. 각 재료를 독립 페이지로 분리하고 Studio는 조립 전용으로 전환.
**선행**: Phase 7-1 (Characters/Storyboards 독립 페이지 패턴 확립).

**비전**:
```
재료 준비 (각 독립 페이지)          통합 (Studio)
├── /storyboards  ✅ 완료           └── 재료 조합 → 렌더링 → 최종 영상
├── /characters   ✅ 완료
├── /voices       → Manage 탭 추출
├── /music        → Manage 탭 추출
└── /backgrounds  → 신규 (배경 에셋)
```

**접근 방식**: 점진적 마이그레이션. 기존 기능을 유지하면서 하나씩 독립 페이지로 추출.

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| 0 | 네비게이션 재구성 (Production/Studio/Tools 그룹, Voices/Music 탑메뉴 승격) | UX | [x] (7-1 #27) |
| 1 | `/voices` 독립 페이지 (Manage VoicePresetsTab 추출 + 카드 그리드 UI) | UX | [x] (2026-02-11) |
| 2 | `/music` 독립 페이지 (Manage MusicPresetsTab 추출 + 카드 그리드 UI) | UX | [x] (2026-02-11) |
| 3 | `/backgrounds` 배경 에셋 페이지 (DB 테이블 + CRUD API + 에셋 관리) | 기능 | [x] (2026-02-11) |
| 4 | ~~Studio "조립 공장" 전환~~ | ~~UX~~ | → 7-4로 확장 |
| 5 | ~~Zustand Store 분할~~ | ~~리팩토링~~ | → 7-4 Phase A로 흡수 |

**Backend 영향**: API 이미 리소스별 분리 완료. `/backgrounds` 신규 API만 추가 필요. 기존 파이프라인 변경 없음.

---

## Phase 7-4: Studio Coordinator + Script Vertical - ARCHIVED

Studio를 코디네이터(지휘자)로 전환하고, 대본 작성을 Script 버티컬로 분리. **전체 완료** (2026-02-11).

**명세**: [STUDIO_VERTICAL_ARCHITECTURE.md](FEATURES/STUDIO_VERTICAL_ARCHITECTURE.md)

| Phase | 핵심 성과 | 상태 |
|-------|----------|------|
| A. 기반 준비 | Zustand 4-Store 분할 (useUIStore/useContextStore/useStoryboardStore/useRenderStore), PersistentContextBar | [x] |
| B. Script 버티컬 | `/scripts` 페이지 (Manual + AI Agent 모드), storyboard.py 4모듈 분해, Materials Check API | [x] |
| C. Studio 코디네이터 | 칸반/타임라인 뷰, PlanTab 제거, Autopilot 범위 조정, 디자인 토큰/EmptyState/접근성 통일 | [x] |
| D. 정리 | 네비 정리, Lab creative 제거, 리다이렉트, deprecated API/별칭/호환 레이어/localStorage 레거시 제거 | [x] |

---

## Phase 7-5: UX/UI Quality & Reliability

**목표**: 8개 에이전트 크로스 분석 기반 전체 UX 품질 향상. 피드백 일관성, 에러 복구, 데이터 안전성, 접근성 강화.
**선행**: Phase 7-4 완료 (4-Store 분할, 디자인 토큰, 접근성 기반).
**분석 출처**: UI/UX Engineer, Frontend Dev, Backend Dev, QA Validator, Security Engineer, FFmpeg Expert, DBA, Prompt Engineer (총 89건 발견)

### Phase A: Quick Wins (UI 일관성 + 기존 인프라 연결) - DONE (2026-02-12)

| # | 작업 | 분류 | 발견자 | 상태 |
|---|------|------|--------|------|
| 1 | Toast 큐 시스템 (useUIStore toasts 배열 + 타이머 관리 + ToastContainer 스택 렌더링) | UX | QA, UI/UX | [x] |
| 2 | `window.confirm`/`window.prompt` → `useConfirm` 전면 교체 (6곳) + ConfirmDialog inputField 지원 추가 | UX | QA, UI/UX, FE | [x] |
| 3 | Studio dirty state `beforeunload` 가드 (isDirty 플래그 + beforeunload 조건 통합) | 안정성 | QA | [x] |
| 4 | `text-[8px]` → `text-[11px]` 폰트 위반 수정 7곳 (CLAUDE.md 최소 폰트 준수) | 접근성 | UI/UX | [x] |
| 5 | Suspense fallback 통일 3곳 (Scripts/Manage/Lab에 LoadingSpinner) | UX | UI/UX | [x] |
| 6 | `inputCls`/`labelCls` → variants.ts `FORM_INPUT_COMPACT_CLASSES` / `FORM_LABEL_COMPACT_CLASSES` 추가 + 7곳 교체 | 일관성 | UI/UX | [x] |
| 7 | TagValidationWarning → SceneFormFields 연결 (useTagValidation 훅 + debounced validateTags) | 품질 | Prompt | [x] |
| 8 | 후보 이미지 match_rate 뱃지 표시 (SceneImagePanel) | UX | Prompt | [x] |
| 9 | 렌더링 catch `err.message` → `getErrorMsg()` 활용 (RenderTab) | UX | FFmpeg | [x] |

### Phase B: 피드백 품질 + 에러 복구 + 성능 - DONE (2026-02-12)

| # | 작업 | 분류 | 발견자 | 상태 |
|---|------|------|--------|------|
| 10 | 에러 메시지 구조화: `str(exc)` → 사용자 친화적 한국어 메시지 래핑 (`error_responses.py` + 6개 라우터 적용) | 보안/UX | BE, Security | [x] |
| 11 | 이미지 생성 SSE 진행률 (`/scene/generate-async` + SD progress 폴링 + Scene 카드 진행률 바) | UX | BE, FFmpeg, Prompt | [x] |
| 12 | ScenesTab `useShallow` + 4그룹 selector 분리 (리렌더링 최적화) | 성능 | FE | [x] |
| 13 | Frontend 에러 헬퍼 통일: `getErrorMsg()` 구조화 에러 파싱 + 3곳 적용 | 안정성 | FE, QA | [x] |
| 14 | 파일 업로드 MIME 화이트리스트 + 매직 바이트 검증 + 10MB 크기 제한 (`upload_validation.py`) | 보안 | Security | [x] |
| 15 | MinIO 기본 credential 제거 + `validate_storage_config()` startup 검증 | 보안 | Security | [x] |
| 16 | Pydantic `max_length` 추가 (8필드: topic/title/caption/description/script/prompt) | 보안 | Security | [x] |
| 17 | 렌더링 ETA 표시 (BE: `_event_generator()` elapsed/eta 계산, FE: RenderSettingsPanel "남은 시간" 표시) | UX | FFmpeg | [x] |
| 18 | Duration 입력 JS 검증 (NaN 체크 + 1~10 클램핑 + onBlur 기본값 3 복원) | 안정성 | QA | [x] |
| 19 | 스토리보드 재생성 시 경고 (기존 씬 존재 시 ConfirmDialog "danger" 확인) | 안정성 | QA | [x] |
| 20 | SSE 재연결 (MAX_RETRIES=3, 지수 백오프 1s→2s→4s, 성공 시 카운터 리셋) | 안정성 | FFmpeg | [x] |

### Phase C: 구조적 개선 (데이터 안전성 + 컴포넌트 구조)

| # | 작업 | 분류 | 발견자 | 상태 |
|---|------|------|--------|------|
| 21 | 씬 Client-Side UUID 도입 (ID 재할당 레이스 컨디션 근본 해결) | 안정성 | QA, FE | [x] |
| 22 | Optimistic Locking (`version` 컬럼 + 409 Conflict, 멀티탭 데이터 유실 방지) | 안정성 | DBA | [x] |
| 23 | 핵심 엔드포인트 `response_model` 정리 (storyboard/scene/video 우선) | API 품질 | BE | [x] |
| 24 | 페이지네이션 통일 (스토리보드/태그/캐릭터 목록) | 성능 | BE, DBA | [x] |
| 25 | Skeleton 로딩 컴포넌트 도입 (LoadingSpinner → SkeletonCard) | UX | UI/UX | [x] |
| 26 | Soft Delete 복원 정합성 (삭제 timestamp 기반 필터 / batch_id 추가) | 안정성 | DBA | [x] |
| 27 | Active 상태 스타일 토큰 통일 (TAB_ACTIVE / FILTER_PILL_ACTIVE) | 일관성 | UI/UX | [x] |
| 28 | `list_storyboards` joinedload → selectinload 전환 (카르테시안 곱 방지) | 성능 | DBA | [x] |
| 29 | Backgrounds N+1 해결 (`joinedload(Background.image_asset)`) | 성능 | BE | [x] |
| 30 | LocalStorage Path Traversal 방어 (`resolve()` + base_dir 검증) | 보안 | Security | [x] |

---

## Phase 7-6: Scene UX Enhancement (Figma Prototype Analysis) - ARCHIVED

**목표**: Figma 프로토타입 비교 분석에서 도출된 씬 편집 UX 개선. 전체 Phase A~G 완료 (2026-02-13).
**명세**: [SCENE_UX_ENHANCEMENT.md](FEATURES/SCENE_UX_ENHANCEMENT.md)

| Phase | 핵심 성과 | 상태 |
|-------|----------|------|
| A. Quick Wins | 씬 완성도 4-dot, 프로젝트 인사이트 패널, 대본 글자수/읽기시간 (3개 언어) | [x] |
| B. Feature | 씬 편집 3탭 분리, 드래그&드롭 순서 변경, 3-Column 레이아웃 재설계 | [x] |
| C. Workspace 탭 | StudioWorkspace 3탭(Edit/Render/Output), Pipeline 도트, Materials 팝오버, 우측패널 3탭(Image/Tools/Insight) | [x] |
| D. 네비 재설계 | 8탭→4탭, Home 분리, Script→Studio 통합, Library 에셋 통합 | [x] |
| E. Publish 통합 | Render+Output→Publish, Script\|Edit\|Publish 3탭 선형 워크플로우 | [x] |
| F. 레이아웃 통일 | CSS 변수 3개, 사이드바 w-52, Secondary Panel 패턴, max-w-7xl 제거 | [x] |
| G. Script 리뷰 | Script 읽기 전용 리뷰 뷰, 칸반 반응형, Recently Updated 교체 | [x] |

---

## Phase 7-Y: Layout Standardization & Navigation Simplification

**목표**: Manage 페이지를 Library + Settings로 분리, 공유 레이아웃 시스템 도입, Home 페이지 리디자인.
**선행**: Phase 7-6, 7-X 완료.
**커밋**: `8a8850f` (2026-02-15)

### 주요 변경 요약

**1. 네비게이션 재구조화**: `[Home, Studio, Library, Lab, Manage]` → `[Home, Studio, Library, Settings]`
- Lab: 코멘트 아웃 (비활성화)
- Manage: **완전 삭제** → Library + Settings로 분리

**2. `/manage` → `/library` + `/settings` 분리**

| 페이지 | 탭 | 그룹 |
|--------|-----|------|
| `/library` (7개 탭) | Characters, Backgrounds, Styles \| Voices, Music \| Prompts, Tags | Visuals, Audio, Text & Meta |
| `/settings` (4개 탭) | General, Render Presets, YouTube \| Trash | General, Project + 시스템 |

**3. 공유 레이아웃 시스템 신규**

| 컴포넌트 | 역할 |
|----------|------|
| `AppThreeColumnLayout` | Left(사이드바) + Center(1fr 스크롤) + Right(300px 패널). Library/Settings 공용 |
| `AppSidebar` | 그룹 접기/펴기, localStorage 영속, CSS 변수 너비, 반응형(lg+ 표시) |
| `AppMobileTabBar` | 모바일 가로 스크롤 탭 바 (lg 미만 표시) |

**4. Home 페이지 리디자인**: 칸반 뷰 → `HomeVideoFeed`

| 컴포넌트 | 역할 |
|----------|------|
| `ShowcaseSection` | 최근 렌더링 영상 3건 (9:16 썸네일 + 클릭 프리뷰 모달), 비어있으면 CTA |
| `QuickActionsWidget` | New Project, Create Character, Browse Styles, Browse Voices 4개 액션 카드 |
| `QuickStatsWidget` | Characters/Styles/Voices/Music 4개 API 카운트 + Library 탭 링크 |

- 칸반 뷰는 Studio 내부로 이동 (스토리보드 미선택 시 `StudioKanbanView` 표시)
- `PersistentContextBar`: Home에서 숨김 (`isHome → return null`)

**5. 컴포넌트 정리**

| 분류 | 파일 |
|------|------|
| 삭제 | `CharacterEditModal`, `CharacterTagsEditor`, `GeminiPreviewEditModal`, `PreviewImageSection`, `ReferencePromptsPanel`, `CharacterFormSections`, `useCharacterForm`, `useCharacterPreview`, `parseRawTagText` |
| 이동 (manage→library) | `StyleProfileEditor`, `DeprecatedTagsPanel`, `TagsTab`, `StyleTab`, `PromptsTab`, `useCivitai`, `useLoraManagement`, `usePromptsTab`, `useStyleTab`, `useTagManagement` |
| 이동 (manage→settings) | `SettingsSecondaryPanel`(←ManageSecondaryPanel), `GeneralSettingsTab`(←SettingsTab), `YouTubeConnectTab`(←YouTubeTab), `RenderPresetsTab`, `TrashTab`, `useRenderPresetsTab`, `useSettingsTab`, `useTrashTab`, `useYouTubeTab` |

**6. 경로 변경**

| 기존 | 변경 후 |
|------|---------|
| `/manage` | 삭제 (디렉토리 전체 제거) |
| `/manage?tab=settings` | `/settings?tab=general` |
| `/manage?tab=presets` | `/settings?tab=presets` |
| `/manage?tab=youtube` | `/settings?tab=youtube` |
| `/manage?tab=trash` | `/settings?tab=trash` |
| `/manage?tab=tags` | `/library?tab=tags` |
| `/manage?tab=style` | `/library?tab=style` |
| `/manage?tab=prompts` | `/library?tab=prompts` |
| `/characters/[id]` | `/library?tab=characters&id=X` (리디렉트) |

### 테스트 동기화 (2026-02-15)

7-Y 변경으로 인한 39개 테스트 실패 수정:

| 파일 | 수정 | 원인 |
|------|------|------|
| Badge/Button/ConfirmDialog 테스트 (7개) | 색상 토큰 업데이트 | variants.ts 디자인 토큰 변경 (rose→red, blue→indigo, emerald-100→50 등) |
| validation.test.ts (19개) | `results[N]` → `results["scene-N"]` | `computeValidationResults` 반환 타입 변경 (배열 인덱싱 → client_id 키) |
| storyboardActions.test.ts (3개) | mapGeminiScenes id 기대값 + UI Store mock 보강 | `id: 0` 고정 + `useUIStore.set()` 누락 |
| test_storyboard.py (2개) | 페이지네이션 응답 대응 | `GET /storyboards` → `PaginatedStoryboardList` (items 키) |
| test_creative_pipeline.py (7개) | 4단계→5단계 | `tts_designer` 스텝 추가 |
| test_subtitle_rendering.py (1개) | 이모지 테스트 skip | 샘플 폰트 이모지 글리프 미지원 |

### 알려진 제한사항 (TODO)

| 항목 | 상태 | 설명 |
|------|------|------|
| 캐릭터 편집 | 임시 비활성 | Full Editor 삭제됨. `/characters/[id]` → Library 리디렉트. `/characters/new` → Wizard만 가능. 편집 기능 재구현 필요 |
| Lab 메뉴 | 숨김 | AppShell NAV_GROUPS에서 코멘트 아웃. `showLabMenu` 플래그로 제어 가능 |
| 스토리보드 삭제 UI | 누락 | `/storyboards` → `/` 리디렉트로 인해 삭제 진입점 없음. Settings > Trash에서만 복원 가능 |

---

## Phase 9: Agentic AI Pipeline (LangGraph Migration)

**목표**: 대본 생성 파이프라인을 LangGraph 기반 에이전틱 AI로 전환. 반복 개선, 메모리, 자율 판단 도입.
**선행**: Phase 7-6 완료 (씬 편집 UX 안정화) — **충족**.
**명세**: [AGENTIC_PIPELINE.md](FEATURES/AGENTIC_PIPELINE.md)

### 기술 스택 (결정: 2026-02-13)

| 컴포넌트 | 선택 |
|----------|------|
| 워크플로우 | LangGraph (`langgraph` + `langchain-core` 자동 포함, 풀 LangChain 불필요) |
| LLM | 기존 `google-genai` 유지 (노드에서 래핑, LangChain wrapper 전환 불필요) |
| Checkpointer | `AsyncPostgresSaver` (기존 PostgreSQL, `setup()` 자동 테이블) |
| Memory | `AsyncPostgresStore` — **Phase 2에서 도입** |
| Observability | LangFuse 셀프호스팅 — **Phase 2에서 도입** (Phase 0-1은 Python logging) |
| Frontend 연동 | SSE (기존 패턴 재활용) |
| 단일 생성 | 항상 Graph 경유 (quick/full config 분기로 이원화 방지) |
| Creative 테이블 | Phase 3에서 데이터 기반 **재평가** (전환/유지/폐기 결정) |
| Gemini 호출 | 최대 3회 (Draft 1 + Revise 2, `MAX_REVISIONS=2`) |

### 단계별 계획

> **원칙**: "동등 전환 먼저, 기능 확장은 안정화 후." Phase 1은 기존과 동일한 출력을 보장하는 것이 유일한 목표.

| Phase | 핵심 | 주요 작업 | 상태 |
|-------|------|----------|------|
| **0. Foundation** (1-2일) | 인프라 | LangGraph + AsyncPostgresSaver + psycopg v3, 2-노드 PoC, 스냅샷 10건 확보 | [x] (2026-02-13) |
| **1. 동등 전환** (3-5일) | 전환 | Draft→Review→Finalize 3노드, `/scripts/generate` Graph 교체, **Script 탭 Manual→Quick + AI Agent 유지**, SSE 진행률, 회귀 테스트 | [x] (2026-02-15) |
| **1.5. 기능 확장** (2-3일) | 개선 | Full 모드 Graph 확장(Creative Debate 흡수), Revise 루프, Human Gate, Quick/Full 토글 UI, reasoning [왜?] | [ ] |
| **2. Memory + Obs** (3-5일) | 학습 | AsyncPostgresStore, LangFuse Docker, Research/Learn 노드, 피드백 UI | [ ] |
| **3. Creative 재평가** | 결정 | Phase 2 후 데이터 기반 판단 (전환 vs 유지 vs 폐기) | [ ] |
| **4. 고도화** | 장기 | PipelineControl 커스텀, Explain Node, 병렬 실행, 분산 큐 | [ ] |

---

## Phase 8: Multi-Style Architecture (Future)

**목표**: Anime, Realistic, 3D 등 다양한 화풍 지원을 위한 유연한 파이프라인 구축.

---

## Feature Backlog

Phase 9 이후 또는 우선순위 미정 항목.

### Creative Lab 개선 — 완료, Phase 7-4에서 Script 버티컬로 이관 예정

쇼츠 파이프라인 표준화 완료 (2026-02-10). **7-4 Phase B-3에서 AI Agent 모드로 통합, Phase D-2에서 Lab에서 제거.**

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| 1 | category 목록 Backend SSOT 전환 (Frontend 하드코딩 제거) | SSOT | [x] |
| 2 | ~~V1 프리셋 `agent_role` 컬럼 추가~~ | ~~DB~~ | N/A (V1 제거됨) |
| 3 | ~~V1 Leader → preset 시스템 이관~~ | ~~리팩토링~~ | N/A (V1 제거됨) |
| 4 | Pipeline step 활성/비활성 설정 (Sound Designer/Copyright Reviewer optional화) | 기능 | [x] |
| 5 | 에이전트-템플릿 매핑 config.py 중앙화 (`CREATIVE_AGENT_TEMPLATES`) | SSOT | [x] |
| 6 | Reference Analyst 에이전트 실제 활성화 (이미 구현 확인) | 기능 | [x] |
| 7 | Script QC Agent + Interactive Review (Pause-Review-Resume 패턴, 스텝별 리뷰 UI, 자동 승인) | 품질 | [x] |

> **향후**: Creative Lab의 creative 탭은 7-4 Phase B-3에서 Script 버티컬 AI Agent 모드로 이동, Phase D-2에서 Lab에서 제거.

### 일반

| 기능 | 참조 |
|------|------|
| VEO Clip (Video Generation 통합) | [명세](FEATURES/VEO_CLIP.md) |
| Visual Tag Browser (태그별 예시 이미지) | [명세](FEATURES/VISUAL_TAG_BROWSER.md) |
| Profile Export/Import (Style Profile 공유) | [명세](FEATURES/PROFILE_EXPORT_IMPORT.md) |
| Scene Clothing Override (장면별 의상 변경) | [명세](FEATURES/SCENE_CLOTHING_OVERRIDE.md) |
| Scene 단위 자연어 이미지 편집 | [명세](FEATURES/SCENE_IMAGE_EDIT.md) |
| ~~AI BGM Generation~~ | ~~[명세](../99_archive/features/AI_BGM.md)~~ → 6-8 #7-11로 이동 (완료) |
| Storyboard Version History | - |
| LoRA Calibration Automation | - |
| v3_composition.py 하드코딩 프롬프트 DB/config 이동 (`_MALE_ENHANCEMENT` 등 10개 frozenset) | - |
| ~~V3 Compose 태그 중복 제거 (chibi 등 identity/style 태그 2회 주입 방지)~~ | ~~완료 (2026-02-11)~~ |
| ~~LoRA weight 부동소수점 정밀도 수정 (`0.600000000000001` → `0.6`)~~ | ~~완료 (2026-02-11)~~ |
| Real-time Prompt Preview (12-Layer) | - |
| ~~씬 순서 드래그 앤 드롭~~ | ~~완료 (2026-02-13, SceneFilmstrip DnD + reorderScenes)~~ |
| Studio 초기 로딩 최적화 (useEffect 워터폴 제거, API 병렬화) | - |
| ~~Backend response_model 전면 적용~~ | → 7-5 C #23으로 이동 |
| ~~YouTube Shorts Upload~~ | ~~[명세](FEATURES/YOUTUBE_UPLOAD.md)~~ → 7-1 #17로 이동 (완료) |

---

## Development Cycle

```
Phase 6-5 (Stability) → 6-6 (Code Health) → 6-7 (Infra/DX) → 6-8 (Local AI) → 7-0 (ControlNet) → 7-1 (UX/Feature)
     P0/P1 Fixes          Refactoring          CI + Soft Delete    TTS/Voice/BGM     Pose Control      New Features
                                                                                                       + Creative Lab
                                                                                                            ↓
               7-2 (Project/Group) → 7-3 (Production Workspace) → 7-4 (Studio + Script Vertical) → 7-5 (UX Quality)
                Cascading Config      재료 독립 페이지              Studio 코디네이터 + 대본 버티컬    피드백/안전성/일관성
                                                                                                            ↓
                              7-6 (Scene UX Enhancement) → 7-X (UI Polish) → 7-Y (Layout Standardization) → 9 (Agentic Pipeline)
                               Figma 기반 씬 편집 개선       공통 컴포넌트/단축키   Manage→Library+Settings 분리    LangGraph 전환
                                                                                                                          ↓
                                                                                                                    8 (Multi-Style)
                                                                                                                        Future
```

**현재 진행 상태** (2026-02-15):
- Phase 6-5 ~ 6-8: **완료** (6-8: AI BGM + TTS 품질 강화)
- Phase 7-0 (ControlNet): **완료** (ARCHIVED)
- Phase 6-7: **14/14 완료** (#2 VRT 완료 2026-02-12, #10 WD14 → Tier 1)
- Phase 7-1: **27/27 완료** (Character Builder Wizard Phase A-C 완료, 2026-02-13)
- Phase 7-2: Phase 1.7 **완료**, Phase 2-1 Channel DNA **완료** (2026-02-13), Phase 2-2~3 → Phase 9로 이관
- Phase 7-3: **3/3 완료** (#0~#3). #4~#5 → 7-4로 이관 완료
- Phase 7-4: **Phase A+B+C+D 완료** (ARCHIVED)
- Phase 7-5: **30/30 완료** (Phase A 9건 + Phase B 11건 + Phase C 10건)
- **Phase 7-6**: Scene UX Enhancement **완료** (Phase A~G)
- **Phase 7-X**: UI Polish & Standardization **완료** (2026-02-14). [가이드](../02_design/UI_COMPONENTS.md)
- **Phase 7-Y**: Layout Standardization **완료** (2026-02-15). Manage→Library+Settings 분리, 공유 레이아웃(AppThreeColumnLayout/AppSidebar/AppMobileTabBar), Home 리디자인(HomeVideoFeed), 네비 4탭(Home/Studio/Library/Settings), Lab 비활성화, 캐릭터 편집 임시 비활성. 테스트 동기화 39건 수정 완료
- **렌더링 품질 개선** (2026-02-14~15): Post Type Scene Text 동적 높이, Full Type Safe Zone, 블러 배경 품질, 폰트 크기 동적 조정, 배경 밝기 기반 텍스트 색상, 얼굴 감지 스마트 크롭, TTS 오디오 정규화, Post Type 해시태그 Instagram Blue. 총 52개 테스트 추가
- **Phase 9**: Agentic AI Pipeline — **Phase 0 Foundation 완료** (2026-02-13), **Phase 1 동등 전환 완료** (2026-02-15). Quick 모드 SSE 스트리밍 전환 (Manual→Quick 명칭, LangGraph 3-노드 파이프라인), AI Agent 탭 유지. Phase 1.5 기능 확장 착수 예정. [명세](FEATURES/AGENTIC_PIPELINE.md)
- **VRT Baseline**: 24개 스크린샷, 8개 스펙 완료 (6-7 #2)
- **테스트**: Backend 1,563 passed (13 skipped) + Frontend 299 passed = **총 1,862개**

### 잔여 작업 우선순위 (재정리 2026-02-15)

**완료된 Tier**: 7-4 Studio (02-11), 7-5 A~C (02-12), VRT Baseline (02-12), 7-6 Scene UX A~G (02-13), Character Builder A~C (02-13), Channel DNA (02-13), 7-X UI Polish (02-14), 7-Y Layout (02-15) — 모두 완료

**Tier 0 — Agentic AI 전환 (최우선, "동등 전환 → 기능 확장" 순)**
| 순위 | 출처 | 작업 | 기간 | 근거 |
|------|------|------|------|------|
| ~~1~~ | ~~9 P0~~ | ~~Foundation: LangGraph + Checkpointer + 2-노드 PoC + 스냅샷 확보~~ | ~~1-2일~~ | ~~2026-02-13 완료~~ |
| ~~2~~ | ~~9 P1~~ | ~~동등 전환: 3노드 Graph + API 교체 + Script 탭 Manual→Quick + AI Agent 유지 + SSE 진행률~~ | ~~3-5일~~ | ~~2026-02-15 완료~~ |
| 3 | 9 P1.5 | 기능 확장: Full 모드(Creative Debate 흡수) + Revise 루프 + Human Gate + reasoning [왜?] | 2-3일 | Quick/Full 선택 가능, 동등 전환 안정화 후 개선 |
| 4 | 9 P2 | Memory + Observability: Store + LangFuse + Research/Learn + 피드백 UI | 3-5일 | 세션 간 학습 + 실행 추적 |

**Tier 3 — 장기**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| 10 | 7-2 P3 | 배치 렌더링, 브랜딩, 분석 대시보드 | 대규모 운영 |
| 11 | 8 | Multi-Style Architecture | Anime 외 화풍 확장 |

**상세 변경 이력**: Phase별 변경사항은 각 Phase의 DoD 및 커밋 로그 참조. Phase 7-1 완료 항목 상세는 [Phase 7-1 커밋 로그](../99_archive/archive/) 참조.
