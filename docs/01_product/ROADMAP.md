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
| 2 | Setup Wizard (첫 실행 가이드) | UX | [명세](FEATURES/UX_IMPROVEMENTS.md) | [ ] |
| 3 | 접근성 기본 (ARIA, focus trap, keyboard) | UX | - | [x] |
| 4 | 이미지 생성 Progress (WebSocket/SSE) | 기능 | - | [ ] |
| 5 | Multi-Character UI (DB 스키마 완료) | 기능 | [명세](FEATURES/MULTI_CHARACTER.md) | [x] |
| 6 | Scene Builder UI (배경/시간/날씨) | 기능 | [명세](FEATURES/SCENE_BUILDER_UI.md) | [ ] |
| 7 | Structure별 전용 Gemini 템플릿 (3종 structure = 3종 템플릿 1:1 매핑 완료) | 기능 | - | [x] |
| 8 | Character Builder 위저드 | 기능 | [명세](FEATURES/CHARACTER_BUILDER.md) | [ ] |
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
| Phase 2: Differentiation | Channel DNA (톤/세계관 주입), Tag Intelligence, Series Intelligence | [ ] |
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

## Phase 7-4: Studio Coordinator + Script Vertical

**목표**: Studio를 코디네이터(지휘자)로 전환하고, 대본 작성을 Script 버티컬로 분리. 모든 버티컬의 AI 에이전트화 첫 시험대상.
**선행**: Phase 7-3 #0~#2 완료 (독립 페이지 패턴 확립), Creative Lab V2 완료.
**명세**: [STUDIO_VERTICAL_ARCHITECTURE.md](FEATURES/STUDIO_VERTICAL_ARCHITECTURE.md)

**비전**:
```
Studio 코디네이터 (/studio)
├── 미선택: 칸반 뷰 (전체 스토리보드 관리)
├── 선택: 타임라인 뷰 (Materials → Scenes → Render → Output)
└── PlanTab 제거, 이미지 설정은 Scenes 영역으로 이동

Script 버티컬 (/scripts)
├── 스토리보드 목록 (기존 /storyboards 흡수)
├── Manual 모드 (기존 PlanTab → Gemini 1회 생성)
└── AI Agent 모드 (기존 Creative Lab → 9-Agent Pipeline)
```

**의존성**: Phase A 완료 → B/C 착수 가능 (블로커). B와 C는 병렬 가능하나 C-3은 B 완료 후.

### Phase A: 기반 준비 — COMPLETE (2026-02-11)

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| A-1 | `useUIStore` 추출 (toast → 앱 전역, persist 없음) | 리팩토링 | [x] |
| A-2 | `useContextStore` 추출 (projectId/groupId/storyboardId → 앱 전역, persist) | 리팩토링 | [x] |
| A-3 | 영속적 컨텍스트 바 (`PersistentContextBar`: Studio 외 페이지에서 breadcrumb 표시) | UX | [x] |
| A-4 | Bridge 호환 레이어 (양방향 subscribe 동기화, 기존 32+ 파일 수정 불필요) | 리팩토링 | [x] |

### Phase B: Script 버티컬 구축 — COMPLETE (2026-02-11)

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| B-1 | `/scripts` 페이지 생성 (목록 + 검색 + 필터, `/storyboards` 흡수) | UX | [x] |
| B-2 | Manual 모드 (PlanTab 대본 관심사 이동: Topic/Structure/Language/Duration/Characters) | 기능 | [x] |
| B-3 | AI Agent 모드 (Creative Lab 흡수: Debate + Pipeline + QC Review) | 기능 | [x] |
| B-4 | Backend `services/storyboard.py` 분해 (4모듈 패키지: crud/helpers/scene_builder/serializer) | 리팩토링 | [x] |
| B-5 | Backend `/scripts/generate` 라우터 + `response_model` 추가 | API | [x] |
| B-6 | Backend Materials Check API (`GET /storyboards/{id}/materials`) | API | [x] |

Phase B 추가 구현 (B-1~B-6 기반 통합 품질 개선):
- `useScriptEditor` 컨텍스트 동기화 (save/load → `useContextStore` + list refresh 이벤트)
- ManualScriptEditor URL 연동 (`onSaved` → `router.replace`)
- ScriptListPanel 삭제 기능 (`useConfirm` + ConfirmDialog)
- Manual/AI Agent 모드 전환 탭 (ScriptEditorPanel 2-탭 바)
- Agent 파이프라인 결과 → Scripts 연동 (`onStoryboardCreated` 콜백 체인)

### Phase C: Studio 코디네이터 전환 — COMPLETE (2026-02-11)

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| C-1 | Studio 칸반 뷰 (미선택 상태, 기존 스키마에서 런타임 상태 파생) | UX | [x] |
| C-2 | Studio 타임라인 뷰 + Materials Check + Pipeline Progress | UX | [x] |
| C-3 | PlanTab 제거 → Image Settings를 Scenes 영역으로 이동 (**B 완료 후**) | 리팩토링 | [x] |
| C-4 | `useStoryboardStore` + `useRenderStore` 분리 (호환 레이어 유지) | 리팩토링 | [x] |
| C-5 | Autopilot 범위 조정 (Scenes → Render → Output, 대본 생성 제외) | 기능 | [x] |

Phase C 추가 구현 (UI 품질 통일):
- 페이지 내 중복 Project/Group 셀렉터 제거 → 글로벌 PersistentContextBar 단일화
- GroupDropdown "All Groups" 옵션 추가 (`ALL_GROUPS_ID=-1` sentinel)
- `PAGE_TITLE_CLASSES`, `SEARCH_INPUT_CLASSES` 디자인 토큰 추출 (5개 리스트 페이지 통일)
- `EmptyState` 공통 컴포넌트 도입 (6개 페이지 통일)
- `LoadingSpinner` 텍스트 기반 로딩 → 스피너 통일 (6곳)
- `useFocusTrap` 훅 도입 + 전체 모달 ARIA 접근성 강화

### Phase D: 정리

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| D-1 | 네비게이션 최종 정리 (Home 제거, Script 추가, Studio 최좌측) | UX | [ ] |
| D-2 | Lab creative 탭 제거 + `/scripts/sessions/*` 라우터 통합 (Creative 세션 이관) | 정리 | [ ] |
| D-3 | `/storyboards` → `/scripts` 리다이렉트 | 정리 | [ ] |
| D-4 | deprecated API/호환 레이어 제거 | 정리 | [ ] |
| D-5 | localStorage 마이그레이션 (기존 store 키 → 신규 키) | 정리 | [ ] |

---

## Phase 8: Multi-Style Architecture (Future)

**목표**: Anime, Realistic, 3D 등 다양한 화풍 지원을 위한 유연한 파이프라인 구축.

---

## Feature Backlog

Phase 8 이후 또는 우선순위 미정 항목.

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
| 씬 순서 드래그 앤 드롭 | - |
| Studio 초기 로딩 최적화 (useEffect 워터폴 제거, API 병렬화) | - |
| Backend response_model 전면 적용 (125개 엔드포인트 중 핵심 경로 우선, dict 타입 구체화) | - |
| ~~YouTube Shorts Upload~~ | ~~[명세](FEATURES/YOUTUBE_UPLOAD.md)~~ → 7-1 #17로 이동 (완료) |

---

## Development Cycle

```
Phase 6-5 (Stability) → 6-6 (Code Health) → 6-7 (Infra/DX) → 6-8 (Local AI) → 7-0 (ControlNet) → 7-1 (UX/Feature)
     P0/P1 Fixes          Refactoring          CI + Soft Delete    TTS/Voice/BGM     Pose Control      New Features
                                                                                                       + Creative Lab
                                                                                                            ↓
                               7-2 (Project/Group) → 7-3 (Production Workspace) → 7-4 (Studio + Script Vertical) → 8 (Multi-Style)
                                Cascading Config      재료 독립 페이지              Studio 코디네이터 + 대본 버티컬    Future
                                                                                  AI 에이전트 버티컬 첫 시험대상
```

**현재 진행 상태** (2026-02-11):
- Phase 6-5 ~ 6-8: **완료** (6-8: AI BGM + TTS 품질 강화)
- Phase 7-0 (ControlNet): **완료** (ARCHIVED)
- Phase 6-7: **14/14 완료** (2건 Tier 재분류: #2 VRT → Tier 3, #10 WD14 → Tier 1)
- Phase 7-1: **24/27** 완료 (잔여: #2 Wizard, #4 생성 Progress, #6 Scene Builder, #8 Char Builder)
- Phase 7-2: Phase 1.7 **완료**, Phase 2-3 대기
- Phase 7-3: **4/6** 완료 (#0~#3, #4~#5 → 7-4로 확장)
- Phase 7-4: **Phase A+B+C 완료** (Store 분할 + Script 버티컬 + Studio 코디네이터 + UI 토큰 통일 + 접근성), Phase D 미착수
- **Backend 테스트**: 1,399개 수집

### 잔여 작업 우선순위 (재정리 2026-02-11)

**Tier 1 — Studio Coordinator + Script Vertical (핵심 방향)**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| ~~1~~ | ~~7-4 A~~ | ~~Store 분할 + 컨텍스트 바 (기반 준비)~~ | ~~완료 (2026-02-11)~~ |
| ~~2~~ | ~~7-4 B~~ | ~~Script 버티컬 구축 (목록 + Manual + AI Agent)~~ | ~~완료 (2026-02-11)~~ |
| ~~3~~ | ~~7-4 C~~ | ~~Studio 코디네이터 전환 (칸반 + 타임라인 + Materials Check)~~ | ~~완료 (2026-02-11)~~ |
| 4 | 7-4 D | 정리 (Lab creative 제거, 리다이렉트, 레거시 제거) | 기술 부채 해소 |

**Tier 2 — Production 재료 확장**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| 5 | ~~7-3 #3~~ | ~~/backgrounds 배경 에셋 페이지~~ | ~~완료 (2026-02-11)~~ |
| 6 | 7-1 #6 | Scene Builder UI (→ `/backgrounds` 기반) | 씬 표현력 확장 |
| 7 | 7-1 #8 | Character Builder 위저드 | 캐릭터 AI 에이전트화 선행 |

**Tier 3 — 후순위**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| 8 | 7-2 P2 | Channel DNA + Tag Intelligence | 프로젝트 차별화 |
| 9 | 7-1 #4 | 이미지 생성 Progress (SSE) | 배치 카운터로 대체 가능 |
| 10 | 6-7 #2 | VRT Baseline System | CI 존재, 추가 안정성 |
| 11 | 7-1 #2 | Setup Wizard (첫 실행 가이드) | 현재 단일 사용자 |
| ~~12~~ | ~~7-1 #3~~ | ~~접근성 기본 (ARIA, focus trap, keyboard)~~ | ~~완료 (2026-02-11)~~ |
| 13 | 7-2 P3 | 배치 렌더링, 브랜딩, 분석 대시보드 | 장기 |

**7-1 최근 완료 (2026-02-05 ~ 02-11)**:
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
