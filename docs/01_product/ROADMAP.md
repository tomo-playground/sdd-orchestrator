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

## Phase 7-6: Scene UX Enhancement (Figma Prototype Analysis)

**목표**: Figma 프로토타입 비교 분석에서 도출된 씬 편집 UX 개선. "Simple by default, Powerful when needed" 원칙 적용.
**선행**: Phase 7-5 완료 (Toast, ConfirmDialog, SSE 인프라, 디자인 토큰).
**출처**: Figma 프로토타입 vs 현행 UI 비교 분석 (2026-02-13)
**명세**: [SCENE_UX_ENHANCEMENT.md](FEATURES/SCENE_UX_ENHANCEMENT.md)

### Phase A: Quick Wins - DONE (2026-02-13)

| # | 작업 | 난이도 | 상태 |
|---|------|--------|------|
| 1 | **씬 완성도 도트**: SceneFilmstrip 각 씬에 4-dot 상태 표시 (대본/이미지/검증/액션). 색상: 완료(green)/부분(amber)/미완(red)/N/A(gray) | 10분 | [x] |
| 2 | **프로젝트 인사이트 패널**: SceneSidePanel 상단에 집계 표시 — 총 길이, 씬 완성도, 이미지 생성률, 평균 Match Rate, 렌더 준비 상태 | 30분 | [x] |
| 3 | **대본 글자수/읽기시간**: SceneFormFields 하단에 "18자 · 읽기 2.3초" 인라인 표시 + 권장 범위 초과 시 경고 뱃지 (Korean/Japanese/English 3개 언어 지원) | 10분 | [x] |

**DoD (Phase A)**:
- [x] 도트: 스크립트 유무/이미지 존재/match_rate 기준/character_actions 유무로 4색 표시
- [x] 인사이트: 기존 storyboard/scene 데이터에서 실시간 집계, 추가 API 없음
- [x] 글자수: Korean(4자/s)/Japanese(5字/s)/English(2.5w/s) 언어별 계산, 권장 범위 표시
- [x] 빌드 PASS + 기존 테스트 통과

### Phase B: Feature (~반나절)

| # | 작업 | 난이도 | 상태 |
|---|------|--------|------|
| 4 | **씬 편집 탭 분리**: SceneCard 내부를 "대본/비주얼/고급" 3탭으로 분리. 기존 컴포넌트 재배치 수준, 신규 UI 없음 | 1-2시간 | [x] (2026-02-13) |
| 5 | ~~**노트 & 메모**~~ | ~~1시간~~ | 취소 |
| 6 | ~~**씬별 AI 재생성**~~ | ~~반나절~~ | 취소 |
| 7 | **씬 순서 드래그 앤 드롭**: SceneFilmstrip HTML5 Drag API + `reorderScenes` 스토어 액션. client_id 기반 선택 추적, isDirty 연동, 범위 검증. SceneFormFields → SceneScriptFields + ScenePromptFields 파일 분리 | 30분 | [x] (2026-02-13) |
| 8 | **3-Column 레이아웃 재설계**: 참조 Figma 사이트 기반. 좌측 수직 씬 리스트(SceneListPanel) + 중앙 편집기(SceneNavHeader + SceneCard 3탭) + 우측 도구 패널(SceneSidePanel). SceneFilmstrip/SceneListHeader 삭제, SidePanelControls 분리, SceneAdvancedFields→SceneSettingsFields 리네임, STUDIO_CONTAINER_CLASSES SSOT | 2시간 | [x] (2026-02-13) |

**DoD (Phase B)**:
- [x] 탭 분리: 대본/비주얼/설정 3탭 전환 (고급→설정 리네임)
- ~~노트: 취소~~
- ~~AI 재생성: 취소 (기존 AI Edit + Auto Suggest로 커버)~~
- [x] DnD 순서 변경: SceneListPanel 드래그 앤 드롭 + reorderScenes 스토어 액션
- [x] 3-Column 레이아웃: 좌측 SceneListPanel(280px) + 중앙 SceneCard(1fr) + 우측 SceneSidePanel(300px)
- [x] Studio 페이지 정렬 통일: STUDIO_CONTAINER_CLASSES (max-w-7xl)
- [x] 빌드 PASS + ESLint PASS

### Phase C: Studio Workspace 탭 재구성 - DONE (2026-02-13)

**문제**: 6개 섹션 수직 스크롤(~2000px), 편집-설정 컨텍스트 단절, 보조정보 과잉 노출(255px).
**해결**: 워크스페이스 탭 + 컴팩트 상태표시 + 우측패널 통합.

| # | 작업 | 상태 |
|---|------|------|
| 9 | **워크스페이스 탭**: StudioTimelineView(수직 스크롤) → StudioWorkspace([Edit\|Render\|Output] 탭). StudioTab `"scenes"` → `"edit"` 리네이밍. StudioTimelineView 삭제 | [x] |
| 10 | **Pipeline/Materials 컴팩트화**: PipelineProgressBar(90px) → PipelineStatusDots(인라인 4-도트 + 호버 툴팁). MaterialsCheckSection(165px) → MaterialsPopover(배지 + 팝오버). Sub-Nav에 인라인 배치 | [x] |
| 11 | **우측패널 탭 통합**: SceneSidePanel + ImageSettingsSection → RightPanelTabs([Image\|Tools\|Insight]). ImageSettingsContent/SceneToolsContent/SceneInsightsContent 3개 콘텐츠 컴포넌트 분리 | [x] |
| 12 | **품질 개선**: 비주얼 탭 이미지 max-w-[320px] 제약, SceneToolsContent 20+props→스토어 직접 소비(ScenesTab 368→291줄), RightPanelTabs 탭 상태 영속(useUIStore), PipelineStatusDots render 도트 isRendering 분리 | [x] (2026-02-13) |

**DoD (Phase C)**:
- [x] 탭 전환: Edit/Render/Output 클릭 한 번으로 접근 (2000px 스크롤 제거)
- [x] Sub-Nav 컴팩트화: Pipeline 도트(완료=green/진행=pulse/미시작=gray) + Materials 배지("3/5" 클릭→팝오버)
- [x] 우측 패널: [Image] 캐릭터/프롬프트 설정 + [Tools] ControlNet/IP-Adapter + [Insight] 검증/Match Rate
- [x] 뷰포트 높이: `h-[calc(100vh-121px)]` 전체 뷰포트 활용 (STUDIO_3COL_LAYOUT → h-full)
- [x] 비주얼 탭 이미지 크기 제약 + 프롬프트 한 화면 표시
- [x] 코드 품질: ScenesTab 300줄 이내, SceneToolsContent 0-props, 우측패널 탭 영속
- [x] 빌드 PASS + Tech Lead 리뷰 통과

### Phase D: 네비게이션 재설계 - DONE (2026-02-13)

**문제**: 상단 네비 8개 탭 플랫 나열 (`Studio | Scripts Characters Voices Music Backgrounds | Lab Manage`). 외부 12개 도구 분석 결과: Scripts/Studio 분리 사례 0건, 에셋 별도 최상위 페이지 사례 거의 없음.
**해결**: 대시보드(Home) + 에셋 통합(Library) + Script를 Studio 편집기 탭으로 흡수. `[Home] [Library] | [Lab] [Manage]` 4개 탭.

| # | 작업 | 상태 |
|---|------|------|
| 13 | **Home 분리**: 칸반 뷰를 `/`(Home)으로 이동. Studio는 편집 전용 (`/studio?id=X`, `/studio?new=true`) | [x] |
| 14 | **Script 탭 통합**: StudioTab에 `"script"` 추가, ScriptTab 컴포넌트 생성. `?new=true` → Script 탭 자동 활성화. Save 성공 → Edit 탭 전환 + URL 반영 | [x] |
| 15 | **Library 통합**: `/library` 페이지 (사이드바 + 탭). Characters/Voices/Music/Backgrounds 4개 에셋을 named export + 탭별 렌더링. 기존 에셋 경로 → `/library?tab=X` 리다이렉트 | [x] |
| 16 | **경로 정리**: `/scripts` → `/studio` 리다이렉트, `/storyboards` → `/` 리다이렉트, `/characters/[id]` 역참조 → `/library?tab=characters`, MaterialsPopover → Script 탭 전환 + Library 경로 | [x] |

**DoD (Phase D)**:
- [x] `/` → 칸반 뷰, 칸반 "New Shorts" → `/studio?new=true` → Script 탭
- [x] Script 탭에서 Save → Edit 탭 자동 전환 + `?id=X` URL 반영
- [x] `/library` → 사이드바 + Characters/Voices/Music/Backgrounds 탭
- [x] 기존 에셋 경로 (`/characters`, `/voices`, `/music`, `/backgrounds`) → `/library?tab=X` 리다이렉트
- [x] `/characters/[id]` 상세 페이지 정상 유지 (역참조 `/library?tab=characters`로 수정)
- [x] 상단 네비 4개만 표시: Home, Library, Lab, Manage
- [x] 빌드 PASS + ESLint PASS + Tech Lead 리뷰 통과

### Phase E: Publish 탭 통합 (Render + Output → Publish) - DONE (2026-02-13)

**문제**: Studio 워크스페이스 탭 `Script | Edit | Render | Output` 중 Render→Output이 부모-자식 관계인데 형제 탭으로 표시. 업계 표준(CapCut/Premiere/InVideo)은 Export/Publish를 단일 뷰로 처리.
**해결**: Render + Output을 `Publish` 탭 하나로 통합. `Script | Edit | Publish` 3탭 선형 워크플로우.

| # | 작업 | 상태 |
|---|------|------|
| 17 | **StudioTab 타입 변경**: `"render" \| "output"` → `"publish"`. useUIStore, StudioWorkspaceTabs, StudioWorkspace 수정 | [x] |
| 18 | **PublishTab 생성**: PublishTab(317줄) + PublishMetaPanel(191줄). RenderMediaPanel(좌측) + RenderedVideosSection(좌측 하단) + RenderSidePanel+Caption/Likes(우측 sticky). RenderTab/OutputTab 삭제 | [x] |
| 19 | **Autopilot 경로 수정**: `setActiveTab("render")` / `setActiveTab("output")` → `setActiveTab("publish")` | [x] |
| 20 | **뱃지 통합**: render progress% + output 영상 수 → publish 뱃지 하나로 병합 | [x] |

**DoD (Phase E)**:
- [x] Studio 탭 3개만 표시: Script, Edit, Publish
- [x] Publish 좌측: 렌더 설정 + 결과 영상, 우측: 렌더 버튼 + Caption/Likes + YouTube
- [x] Autopilot 렌더 단계 → Publish 탭 자동 전환
- [x] 빌드 PASS + ESLint PASS

### Phase F: 레이아웃 공백 효율화 + Secondary Panel - DONE (2026-02-13)

**문제**: 4개 메뉴(Home/Library/Lab/Manage)의 사이드바 너비 불일치(w-48/w-56), 모든 페이지 `max-w-7xl` 제약으로 넓은 화면 양쪽 빈 공간 낭비, Studio Script/Publish 탭 공간 활용 불일치.
**해결**: CSS 변수 통일 + Primary/Secondary 2컬럼 패턴 + max-w-7xl 전면 제거.

| # | 작업 | 상태 |
|---|------|------|
| 21 | **디자인 토큰 정비**: globals.css 변수 3개 (--sidebar-width:208px, --sidebar-collapsed-width:56px, --secondary-panel-width:280px), variants.ts 토큰 3개 (SIDE_PANEL_LAYOUT 280px, PAGE_2COL_LAYOUT, SECONDARY_PANEL_CLASSES) | [x] |
| 22 | **사이드바 통일**: Library(w-48)/Lab(w-56)/Manage(w-56) → CSS 변수 참조 (w-52 통일) | [x] |
| 23 | **Home 2컬럼**: StudioKanbanView CONTAINER_CLASSES 제거 + HomeSecondaryPanel (Quick Stats, Quick Actions) | [x] |
| 24 | **Library 2컬럼**: PAGE_2COL_LAYOUT 래핑 + 4개 콘텐츠 CONTAINER_CLASSES 제거 + LibrarySecondaryPanel (탭별 가이드) | [x] |
| 25 | **Manage 2컬럼**: PAGE_2COL_LAYOUT 래핑 + ManageSecondaryPanel (탭별 도움말) | [x] |
| 26 | **Lab max-w 제거**: 콘텐츠 자연스럽게 풀 너비 활용 | [x] |
| 27 | **Studio Script 탭 사이드 패널**: ScriptTab SIDE_PANEL_LAYOUT 적용 + ScriptSidePanel (Status, Tips) | [x] |
| 28 | **Studio max-w-7xl 전면 제거**: StudioWorkspace Script/Publish 래퍼 + studio/page.tsx sub-nav/배너 (CONTAINER_CLASSES → px-6) | [x] |

**DoD (Phase F)**:
- [x] 사이드바 3개 CSS 변수 통일 (w-52)
- [x] Home/Library/Manage에 Secondary 패널 (280px, xl+ 표시)
- [x] Script/Publish 탭 동일한 SIDE_PANEL_LAYOUT (1fr+280px)
- [x] max-w-7xl 잔여: characters/[id] (독립 상세), Footer.tsx (전역) — 적절
- [x] 반응형: <lg 사이드바 숨김, <xl Secondary 숨김
- [x] 빌드 PASS + Tech Lead 리뷰 통과

### Phase G: Script 읽기 전용 리뷰 + 레이아웃 패치 - DONE (2026-02-13)

**문제**: (1) Script 탭과 Edit 탭 양쪽에서 씬 스크립트 편집 가능 → 중복 혼란. (2) Home 칸반 xl 브레이크포인트에서 QUICK STATS 우측 잘림. (3) Home `+New Shorts` 버튼 칸반 헤더/Quick Actions 중복 노출.
**해결**: Script 탭 씬 목록을 읽기 전용 리뷰 뷰로 전환 (Agentic Human-in-the-loop 준비), 칸반 반응형 그리드 + overflow 방어, Quick Actions → Recently Updated로 교체.

| # | 작업 | 상태 |
|---|------|------|
| 29 | **Script 씬 목록 읽기 전용**: ScriptSceneList textarea 제거 → `<p>` 읽기 전용 텍스트. `onUpdateScene`/`storyboardId` props 제거, `onApprove` + `approveLabel` prop 도입. Studio: "Approve & Edit →" (저장+Edit탭 이동), Scripts: "Save" (기본값) | [x] |
| 30 | **Home 칸반 반응형**: `grid-cols-4` → `grid-cols-2 lg:grid-cols-4`. AppShell 콘텐츠 `overflow-x-hidden` 추가 | [x] |
| 31 | **Home Quick Actions → Recently Updated**: 중복 `+New Shorts` 버튼 제거 (칸반 헤더에만 유지). QUICK ACTIONS 섹션 → Recently Updated 섹션 (전체 컬럼에서 `updated_at` 최신 3건 표시, 상태별 컬러 dot, 클릭 시 스토리보드 진입). Resume Last 기능을 자연스럽게 대체 | [x] |

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
| **1. 동등 전환** (3-5일) | 전환 | Draft→Review→Finalize 3노드, `/scripts/generate` Graph 교체, **Script 탭 Manual 제거→Quick 단일 모드**, SSE 진행률, 회귀 테스트 | [ ] |
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
                                                                              7-6 (Scene UX Enhancement) → 9 (Agentic Pipeline)
                                                                               Figma 기반 씬 편집 개선        LangGraph 전환
                                                                                                                    ↓
                                                                                                              8 (Multi-Style)
                                                                                                                  Future
```

**현재 진행 상태** (2026-02-13):
- **Autopilot 이미지 유실 버그 수정** (2026-02-13): (1) `generateBatchImages` candidates 미저장 버그 수정 (image_asset_id만 저장, candidates 누락 → 페이지 새로고침 시 이미지 사라짐). (2) 오토파일럿 부분 실패 시 `persistStoryboard()` 미호출 → 성공한 이미지도 전량 유실 → 실패 수집 후 저장 완료 이후 에러 throw로 변경. (3) AutoRunStatus 로그 높이 제한 + 접기/펴기 토글. 테스트 5개 추가 (batchActions 3 + autopilotActions 2).
- Phase 6-5 ~ 6-8: **완료** (6-8: AI BGM + TTS 품질 강화)
- Phase 7-0 (ControlNet): **완료** (ARCHIVED)
- Phase 6-7: **14/14 완료** (#2 VRT 완료 2026-02-12, #10 WD14 → Tier 1)
- Phase 7-1: **27/27 완료** (Character Builder Wizard Phase A-C 완료, 2026-02-13)
- Phase 7-2: Phase 1.7 **완료**, Phase 2-1 Channel DNA **완료** (2026-02-13), Phase 2-2~3 → Phase 9로 이관
- Phase 7-3: **4/6** 완료 (#0~#3, #4~#5 → 7-4로 확장)
- Phase 7-4: **Phase A+B+C+D 완료** (ARCHIVED)
- Phase 7-5: **30/30 완료** (Phase A 9건 + Phase B 11건 + Phase C 10건)
- **Phase 7-6**: Scene UX Enhancement **완료** (Phase A~G: 씬 편집 탭/DnD/3-Column/Workspace 탭/네비 재설계/Publish 통합/레이아웃 통일/Script 읽기전용+칸반 반응형+Home Recently Updated)
- **Phase 9**: Agentic AI Pipeline — **Phase 0 Foundation 완료** (2026-02-13). LangGraph + AsyncPostgresSaver + psycopg v3, 2-노드 PoC(draft→finalize), DB 테이블 4개 + lifespan 초기화, 스냅샷 10건 fixture + 회귀 테스트 23건 + Integration 1건 = **27건 PASS**. Phase 1 동등 전환 착수 예정. [명세](FEATURES/AGENTIC_PIPELINE.md)
- **VRT Baseline**: 24개 스크린샷, 8개 스펙 완료 (6-7 #2)
- **Backend 테스트**: 1,456개 수집

### 잔여 작업 우선순위 (재정리 2026-02-13)

**완료된 Tier** (아카이브):
- ~~Tier 1: 7-4 A~D Studio Coordinator + Script Vertical~~ (2026-02-11 완료)
- ~~Tier 2-1: 7-5 A Quick Wins 9건~~ (2026-02-12 완료)
- ~~Tier 2-2: 7-5 B 피드백 품질 11건~~ (2026-02-12 완료)
- ~~Tier 2-3: 7-5 C 구조적 개선 10건~~ (2026-02-12 완료)
- ~~Tier 3: 6-7 #2 VRT Baseline System~~ (2026-02-12 완료, 24 screenshots / 8 specs)

**Tier 0 — Scene UX Enhancement (최우선, Figma 분석 기반)**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| ~~1~~ | ~~7-6 A #1~3~~ | ~~Quick Wins: 완성도 도트 + 인사이트 패널 + 글자수 표시~~ | ~~2026-02-13 완료~~ |
| ~~2~~ | ~~7-6 B #4~~ | ~~탭 분리~~ | ~~2026-02-13 완료~~ |
| ~~2.1~~ | ~~7-6 B #7~~ | ~~씬 순서 DnD~~ | ~~2026-02-13 완료~~ |
| ~~2.5~~ | ~~7-6 B #5~~ | ~~노트 기능~~ | ~~취소~~ |
| ~~3~~ | ~~7-6 B #6~~ | ~~씬별 AI 재생성~~ | ~~취소 (기존 AI Edit/Auto Suggest로 커버)~~ |
| ~~3.5~~ | ~~7-6 C #9~12~~ | ~~Workspace 탭 + Pipeline 컴팩트 + 우측패널 통합 + 품질~~ | ~~2026-02-13 완료~~ |
| ~~4~~ | ~~7-6 D #13~16~~ | ~~네비 재설계: 8탭→4탭 (Home/Library/Lab/Manage)~~ | ~~2026-02-13 완료~~ |
| ~~4.5~~ | ~~7-6 E #17~20~~ | ~~Publish 탭 통합: Render+Output→Publish (4탭→3탭)~~ | ~~2026-02-13 완료~~ |
| ~~5~~ | ~~7-6 F #21~28~~ | ~~레이아웃 통일: 사이드바 w-52 + Secondary Panel + max-w 제거~~ | ~~2026-02-13 완료~~ |

**~~Tier 1 — Character Builder 위저드 (7-1 #8)~~** — 완료 (2026-02-13)

외부 사례 분석 반영 (NovelAI/Civitai/VRoid/Pixai/Character.ai). [상세 명세](FEATURES/CHARACTER_BUILDER.md)

| 순위 | Phase | 작업 | 상태 |
|------|-------|------|------|
| ~~4-A~~ | ~~A~~ | ~~위저드 골격 + Quick Start 템플릿 + Step 1-2 (카테고리 칩 그리드, 인기순 강조) + Save~~ | ~~완료~~ |
| ~~4-B~~ | ~~B~~ | ~~Step 3 LoRA 카드 그리드 (썸네일+메타+인라인 weight) + Type/Gender 필터~~ | ~~완료~~ |
| ~~4-C~~ | ~~C~~ | ~~`POST /characters/preview` + `assign-preview` API + 프리뷰 생성~~ | ~~완료~~ |

**Tier 1.5 — Feature 확장**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| ~~5~~ | ~~7-2 P2-1~~ | ~~Channel DNA (톤/세계관/가이드라인 JSONB + Gemini 주입)~~ | ~~2026-02-13 완료~~ |
| ~~6~~ | ~~7-1 #2~~ | ~~Setup Wizard~~ | ~~N/A (기존 기능으로 대체)~~ |

**Tier 0 — Agentic AI 전환 (최우선, "동등 전환 → 기능 확장" 순)**
| 순위 | 출처 | 작업 | 기간 | 근거 |
|------|------|------|------|------|
| ~~1~~ | ~~9 P0~~ | ~~Foundation: LangGraph + Checkpointer + 2-노드 PoC + 스냅샷 확보~~ | ~~1-2일~~ | ~~2026-02-13 완료~~ |
| 2 | 9 P1 | 동등 전환: 3노드 Graph + API 교체 + **Script 탭 Manual→Quick 통합** + 회귀 테스트 | 3-5일 | 기존 동작 100% 유지 + UI 이원화 해소 |
| 3 | 9 P1.5 | 기능 확장: Full 모드(Creative Debate 흡수) + Revise 루프 + Human Gate + reasoning [왜?] | 2-3일 | Quick/Full 선택 가능, 동등 전환 안정화 후 개선 |
| 4 | 9 P2 | Memory + Observability: Store + LangFuse + Research/Learn + 피드백 UI | 3-5일 | 세션 간 학습 + 실행 추적 |

**Tier 3 — 장기**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| 10 | 7-2 P3 | 배치 렌더링, 브랜딩, 분석 대시보드 | 대규모 운영 |
| 11 | 8 | Multi-Style Architecture | Anime 외 화풍 확장 |

**VRT Baseline 완료 (2026-02-12)**:
- (2026-02-12) 6-7 #2 VRT Baseline System: Playwright `toHaveScreenshot()` 기반 8개 스펙 파일, 24개 스크린샷 (list + empty 상태). Mock fixture 분리 (8개 파일), 페이지별 mock 함수 15개, vrtUtils (waitForPageReady/hideAnimations/clearLocalStorage). VRT_GUIDE.md + TEST_STRATEGY.md 문서화.

**7-5 최근 완료 (2026-02-12)**:
- (2026-02-12) Phase B 11건 완료: Pydantic max_length 8필드, MinIO credential 제거 + startup 검증, MIME 화이트리스트 + 매직 바이트 + 10MB 제한, 에러 한국어화 (error_responses.py + 6라우터), Frontend getErrorMsg 구조화 에러 파싱, Duration 1~10 클램핑, 재생성 ConfirmDialog 경고, SSE 3회 재연결 + 지수 백오프, 렌더링 ETA 표시, ScenesTab useShallow 4그룹 최적화, 이미지 SSE 진행률 (generate-async + SD 폴링 + Scene 카드 진행률 바). 빌드 PASS, 테스트 1,456개 통과.
- (2026-02-12) Phase A Quick Wins 9건 전량 완료: Toast 큐 시스템 (useUIStore toasts 배열 + ToastContainer 스택), `window.confirm`/`window.prompt` → `useConfirm` 6곳 교체 + ConfirmDialog inputField 지원, Studio dirty state beforeunload 가드 (isDirty + 조건 통합), `text-[8px]` → `text-[11px]` 폰트 위반 7곳 수정, Suspense fallback 통일 3곳, variants.ts `FORM_INPUT_COMPACT_CLASSES`/`FORM_LABEL_COMPACT_CLASSES` 7곳 교체, TagValidationWarning → SceneFormFields 연결 (useTagValidation + debounced), match_rate 뱃지 (SceneImagePanel), 렌더링 `getErrorMsg()` 활용. 빌드 PASS, 테스트 287개 전체 통과.

**7-1 최근 완료 (2026-02-05 ~ 02-13)**:
- (2026-02-13) Character Builder Wizard Phase A-C 완료 (#8): 3-step 위저드(Basic Info→Appearance→LoRA), Quick Start 템플릿 6종, 카테고리 칩 그리드(인기순 강조+색상 dot), LoRA 카드 브라우저(썸네일+뱃지+인라인 weight+Type/Gender 필터), SD 프리뷰 생성(`POST /characters/preview` + `assign-preview` API), `useWizardPreview` 훅 분리, `wizardReducer` 상태 관리, `CategorySection` 컴포넌트 분리
- Creative Lab & Engine: evaluation 시스템 → Lab 전환, Tag/Scene Lab, Multi-Agent Creative Engine (Director/Writer/Reviewer), Lab V3 통합 (`image_generation_core.py`)
- Dialogue(2-char) + Narrated Dialogue(3-speaker) 구조 추가, Narrator 씬 전용 처리
- 렌더링 SSE 진행률, Style LoRA 통합, image_url 정합성 강화
- TTS 품질: Context-Aware Voice, 환각 감지/제거, 반복 방지, 자동 재생성
- (2026-02-09) Background Scene 태그 필터링: `no_humans` 감지 → CHARACTER_ONLY_LAYERS(1-8) 제거 + 캐릭터 카메라 태그 필터. LoRA Weight Cap `STYLE_LORA_WEIGHT_CAP=0.76` 무조건 적용으로 통합
- (2026-02-09) Creative Lab V2 MVP: 9-Agent 시스템, Phase 1 Concept Debate + Phase 2 Production Pipeline, 6 Jinja2 Templates, Frontend V1/V2 모드 전환
- (2026-02-10) Creative Lab V2 Phase 3: Multi-Character Dialogue (character_ids 매핑, CharacterPicker 컴포넌트), Sound Designer 에이전트 (BGM 추천), Copyright Reviewer 에이전트, send-to-studio 서비스 추출 (creative_studio.py), QC feedback retry 개선, SSOT presets API 연동, 단위 테스트 14개
- (2026-02-10) 모듈화 위반 전면 리팩토링 (TDD 22건): `split_prompt_tokens` SSOT 통합, `resolve_style_loras` config cascade 통합, `creative_studio._build_scene` V3 composition 파이프라인 적용 (style_loras + negative_prompt), `lab.py` V3 이중 호출 제거, `controlnet.py` 태그 underscore 포맷 수정, 모놀로그 캐릭터 링크 누락 수정, V3 `_distribute_tags` LoRA 이중 주입 방지
- (2026-02-10) `compose_scene_with_style` SSOT 추출: Creative Lab/Studio Direct 프롬프트 파이프라인 단일화 (StyleProfile → V3 composition). `generate_image_with_v3`도 통합. `prompt_pre_composed` 경로 LoRA 이중 적용 버그 수정 (`skip_loras=True` + defense-in-depth 중복 방어)
- (2026-02-10) Creative Lab 쇼츠 표준화: V1(Free Debate) 코드/테스트/컴포넌트 전량 삭제 (5 backend + 2 frontend 파일), category 리네이밍 (`v2_concept`→`concept`, `v2_production`→`production`), SSOT 전환 (categories + agent-template 매핑 config.py), `session_type` 기본값 `"shorts"` 전환, Alembic 마이그레이션 2건
- (2026-02-10) Script QC Agent + Interactive Review: Pause-Review-Resume 패턴 (파이프라인 스텝 완료 후 `step_review` 상태 전환 → 사용자 리뷰 → 승인/리비전), Script QC 프롬프트 (`script_qc.j2`, 6가지 가중 평가), `creative_review.py` 모듈 분리, 자동 승인 (`score≥0.85` + critical 0건), 챗봇식 리뷰 UI (QCSummaryCard + StepReviewView), `with_for_update()` 동시성 방어, 단위 테스트 15개
- (2026-02-10) Multi-Character UI 5-Phase 통합: SceneCharacterAction 타입/스토어, SpeakerBadge 드롭다운, SceneCharacterActions 태그 편집 UI, `auto_populate_character_actions` context_tags→actions 자동 변환, V3 12-Layer scene_character_actions 주입, `resolve_action_tag_ids` tag_name→tag_id 해결, QC 스키마 Gemini 출력 유연화 (500 에러 수정), `NegativePromptToggle` 컴포넌트 분리, 테스트 55개 추가
- (2026-02-11) Multi-Character LoRA 지원: `loras` 테이블에 멀티캐릭터 필드 3개 추가 (`is_multi_character_capable`, `multi_char_weight_scale`, `multi_char_trigger_prompt`), `scenes.scene_mode` 필드 추가 (`single`/`multi`), Scene Generate/Prompt Compose API에 `character_b_id` 파라미터 지원, 2인 동시 출연 시 LoRA weight 자동 축소
- (2026-02-11) CharacterEditModal P0 UI/UX: `alert()`/`confirm()` 7개 → Toast + ConfirmDialog 교체 (DI 패턴), `text-[9px]`/`text-[10px]` 26개 → `text-[11px]`, 접근성 (`role="dialog"`, `aria-label`, Escape 닫기), `UiCallbacks` 타입 추출
- (2026-02-11) 캐릭터 Identity Tag 체계: `a_cute_boy`/`a_cute_girl` 태그 등록, 캐릭터별 identity tag 연결 (bishounen 성인화 문제 해결), Voice Preset (지호/수빈) 생성 + 캐릭터 연동
- (2026-02-11) Character Management 독립 페이지: `/characters` 리스트 (검색+필터+카드 그리드), `/characters/[id]` 상세/편집 (2컬럼 레이아웃), `/characters/new` 생성, CharacterEditModal 6개 섹션 추출 → 공유 컴포넌트, `useCharacterPreview` + `parseRawTagText` 훅 분리, Home CharactersSection 축소 (미니카드 3개 + View All)
- (2026-02-11) Storyboards 독립 페이지: `/storyboards` 리스트 (Project/Group select 필터, 검색, ConfirmDialog 삭제), `useStoryboards` 훅 추출 (Zustand 비침습), `StoryboardCard`/`DraftCard` 공유 컴포넌트, Home StoryboardsSection 요약 축소 (최근 3개 + View All), AppShell NAV 추가
- (2026-02-11) 캐릭터 편집 이탈 경고 (AC#3): `isDirty` JSON 스냅샷 비교, `beforeunload` 브라우저 경고, "← Characters" ConfirmDialog 이탈 확인
- (2026-02-11) Production Workspace 네비게이션: AppShell NAV_GROUPS 재구성 (Production: Home/Stories/Characters/Voices/Music | Studio | Tools: Lab/Manage), Voices/Music 탑메뉴 승격 (`/manage?tab=voice`, `/manage?tab=music` 임시 연결), `isNavActive` query param 매칭, NavBar Suspense 분리
- (2026-02-11) `/voices`, `/music` 독립 페이지 분리: Manage VoicePresetsTab·MusicPresetsTab → 독립 카드 그리드 UI 추출, 공유 훅(`useVoicePresets`, `useMusic`) 분리, Manage 중복 탭·훅 제거
