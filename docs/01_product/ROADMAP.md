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

## Phase 7-1: UX & Feature Expansion - ARCHIVED

사용자 경험 개선 및 핵심 신규 기능 **27건 완료**. Quick Start, Multi-Character, Scene Builder, Character Builder, Creative Lab V2, YouTube Upload, Production Workspace 네비게이션 등. 상세: [Phase 7-1 아카이브](../99_archive/archive/ROADMAP_PHASE_7_1.md)

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

## Phase 7-3: Production Workspace - ARCHIVED

재료 독립 페이지 **4건 완료** (2026-02-11). /voices, /music, /backgrounds 페이지 + 네비게이션 재구성. #4~#5는 7-4로 이관. 상세: [Phase 7-3 아카이브](../99_archive/archive/ROADMAP_PHASE_7_3.md)

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

## Phase 7-5: UX/UI Quality & Reliability - ARCHIVED

8개 에이전트 크로스 분석 기반 **30건 완료** (2026-02-12). Phase A(Quick Wins 9건: Toast, useConfirm, dirty guard, 폰트 수정 등) + Phase B(피드백/에러 11건: SSE 진행률, 보안 강화, ETA 표시 등) + Phase C(구조적 개선 10건: Client-Side UUID, Optimistic Locking, 페이지네이션, Path Traversal 방어 등). 상세: [Phase 7-5 아카이브](../99_archive/archive/ROADMAP_PHASE_7_5.md)

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

## Phase 7-Y: Layout Standardization & Navigation Simplification - ARCHIVED

Manage→Library+Settings 분리, 공유 레이아웃 시스템(AppThreeColumnLayout/AppSidebar/AppMobileTabBar), Home 리디자인(HomeVideoFeed), 네비 4탭(Home/Studio/Library/Settings), Unified Setup Wizard 추가. 테스트 39건 수정. **알려진 제한사항**: 캐릭터 편집 임시 비활성, Lab 숨김, 스토리보드 삭제 UI 누락. 상세: [Phase 7-Y 아카이브](../99_archive/archive/ROADMAP_PHASE_7_Y.md)

---

## Phase 7-Z: Home Dashboard & Publish UX Redesign

**목표**: Home 페이지를 "비디오 갤러리 뷰어"에서 "창작 대시보드"로 전환. Publish 탭의 비디오 프리뷰 우선 배치.
**선행**: Phase 7-Y 완료 (Home 리디자인 기반, 공유 레이아웃 시스템).

### Phase A: Home Dashboard (레이아웃 + 핵심 기능)

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| 1 | 2-Column 대시보드 레이아웃 (단일 컬럼 → `grid-cols-[2fr_1fr]`, Quick Actions/Stats Above-the-fold 노출) | UX | [x] 2026-02-15 |
| 2 | "Continue Working" 섹션 (최근 수정 스토리보드 2-3개, 워크플로우 단계 표시 Script/Edit/Publish, Continue CTA) | UX | [x] 2026-02-15 |
| 3 | Video Gallery 컴팩트화 (그리드 → 수평 스크롤 캐러셀, 카드 높이 400px→220px, "모두 보기" 링크) | UX | [x] 2026-02-15 |

### Phase B: Publish 탭 레이아웃 재설계

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| 7 | Publish 3-Column 재배치: LEFT(Layout 선택+Render 버튼+Progress) / CENTER(비디오 프리뷰 크게+설정 접힘) / RIGHT(Caption/Likes+Recent Videos 리스트) | UX | [x] 2026-02-15 |
| 8 | Render Settings `<details>` 래핑 (기본 접힘 상태, 설정보다 결과물 우선) | UX | [x] 2026-02-15 |

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
| **1.5. 기능 확장** (2-3일) | 개선 | Full 모드 Graph 확장(Creative Debate 흡수), Revise 루프, Human Gate, Quick/Full 토글 UI, reasoning [왜?] | [x] (2026-02-15) |
| **2. Memory + Obs** (3-5일) | 학습 | AsyncPostgresStore, LangFuse Docker, Research/Learn 노드, 피드백 UI | [x] (2026-02-15) |
| **3. Creative 재평가** | 폐기(C) | Creative Lab UI/라우터 이미 삭제 완료 (Phase 7-4 D). 잔여 서비스(debate_agents, creative_qc 등)는 LangGraph 노드에서 활용 중. creative_utils.py 데드 코드 258줄 정리 | [x] (2026-02-16) |
| **4A. E2E Pipeline** | 자동화 | Script 생성 완료 후 Post-generation CTA → persistStoryboard → Preflight → AutoRun(Image→Validate→Render) 자동 체인. `pendingAutoRun` Zustand 시그널 패턴, `justGenerated` 플래그로 CTA 표시 제어 | [x] (2026-02-16) |
| **4B. Agent Spec + Director** | 아키텍처 | Agentic AI 기준 에이전트 분류 체계 정립(AI Agent/Hybrid/System), 네이밍 통일(debate→critic, draft→writer), **Director Agent 신규 구현**(Production chain 통합 검증). 12→13노드 파이프라인, AGENT_SPEC.md 엔지니어링 스펙 문서 | [x] (2026-02-16) |
| **4C. Pipeline 고도화** | 품질 | Director feedback→타겟 노드 주입 (W-2 수정), Production Chain 병렬화 (LangGraph fan-out: tts/sound/copyright 동시 실행), Explain Node (Full 모드 창작 결정 설명), fallback 패턴 (병렬 안전). 13→**14노드** 파이프라인 | [x] (2026-02-16) |
| **4. 고도화 (잔여)** | 장기 | PipelineControl 커스텀, 분산 큐 | [ ] |
| **5A. Narrative Quality** | 서사 품질 | Hook 구조 가이드 + 서사 품질 평가 (Review 노드 확장) + NarrativeScore | [x] (2026-02-17) |
| **5B. Concept Gate** | 컨셉 선택 | Critic 3컨셉 사용자 노출 + concept_gate 노드 + Creator interrupt | [x] (2026-02-17) |
| **5C. AI Transparency** | 투명성 UX | Pipeline Stepper + Agent Reasoning 패널 + Narrative Score 시각화 | [x] (2026-02-17) |
| **5D. Interactive Feedback** | 피드백 | 프리셋 피드백 버튼 4종 + Concept Gate 재생성/직접입력 + 파라미터 피드백 | [x] (2026-02-17) |
| **5E. Research References** | 소재 분석 | URL/텍스트 소재 분석 (httpx fetch + SSRF 방어 + Gemini 요약), References API 필드 | [x] (2026-02-17) |

---

## Phase 10: True Agentic Architecture (최우선)

**목표**: DAG Workflow → 진정한 Agentic AI 전환. ReAct Loop, Tool-Calling, Agent Communication 도입.
**선행**: Phase 9 완료 (LangGraph 파이프라인 안정화) — **충족**.
**명세**: [TRUE_AGENTIC_ARCHITECTURE.md](FEATURES/TRUE_AGENTIC_ARCHITECTURE.md)

**진단**: 현재 15노드 파이프라인은 LangGraph를 사용하지만 실질은 "State Machine 기반 DAG Workflow". LLM이 자율적 의사결정, Tool Use, Planning, Self-Reflection, 에이전트 간 소통 **5대 Agentic 요건을 모두 미충족**.

**설계 완료** (2026-02-18): 기능 명세 작성, Gemini 크로스 리뷰 4대 리스크 대응 반영, A/B 벤치마크 샘플 10건 설계 완료. 구현 대기.

### Phase 0: Benchmark Baseline 수집

| # | 작업 | 핵심 | 상태 |
|---|------|------|------|
| 0 | 벤치마크 샘플 10건 + 자동화 스크립트 | `scripts/benchmark/` (run_benchmark.py, benchmark_samples.json, compare_results.py). BM-01~10 각 3회 Baseline 실행 (진행 중), LangFuse "baseline" 태그. TDD 18개 테스트, SSE 파싱 수정, Gemini safety filter 해결 완료 (2026-02-18) | [x] |

### Phase A: ReAct Loop + Self-Reflection (Level 1)

| # | 작업 | 핵심 | 상태 |
|---|------|------|------|
| 1 | Director ReAct Loop | Single-shot → Observe→Think→Act 루프 (최대 3 스텝). 사고 과정 기록 | [x] 2026-02-18 |
| 2 | Review Self-Reflection | 실패 시 원인 분석 + 구체적 수정 전략 수립 → revise에 전달 | [x] 2026-02-18 |
| 3 | Writer Planning Step | 즉시 생성 → 계획 수립(Hook 전략, 감정 곡선, 씬 배분) → 계획 기반 생성 | [x] 2026-02-18 |

### Phase B: Tool-Calling Agent (Level 2)

| # | 작업 | 핵심 | 상태 |
|---|------|------|------|
| 4 | Gemini Function Calling 인프라 | `tools/` 패키지, `define_tool()`, `call_with_tools()`, MAX_TOOL_CALLS 가드레일, ToolCallLog, LangFuse 통합 | [x] 2026-02-18 |
| 5 | Research Agent Tool-Calling | 고정 순회 → LLM이 필요한 도구 선택적 호출 (히스토리/URL/트렌딩/채널DNA). 5개 도구 (`search_topic_history`, `search_character_history`, `fetch_url_content`, `analyze_trending`, `get_group_dna`), `research_tool_logs` 상태 필드 추가 | [x] 2026-02-18 |
| 6 | Cinematographer Agent Tool-Calling | 고정 템플릿 → LLM이 태그 검증/호환성 체크/레퍼런스 검색 도구 호출. 4개 도구 (`validate_danbooru_tag`, `search_similar_compositions`, `get_character_visual_tags`, `check_tag_compatibility`), `cinematographer_tool_logs` 상태 필드 추가 | [x] 2026-02-18 |

### Phase C: Agent Communication (Level 3)

| # | 작업 | 핵심 | 상태 |
|---|------|------|------|
| 7 | Agent Message Protocol + State Condensation | AgentMessage TypedDict + 노드별 상태 압축 (컨텍스트 오염 방지). `messages.py`: format/condense/truncate 유틸리티, MAX_MESSAGE_WINDOW=10, MAX_CONTEXT_TOKENS=2000. ScriptState: `agent_messages`, `agent_summary` 필드 추가 | [x] 2026-02-18 |
| 8 | Director ↔ Production 양방향 소통 | 직접 피드백/응답 메시지 + Speculative Execution (레이턴시 대응) | [x] 2026-02-18 |
| 9 | Critic 실시간 토론 + KPI 수렴 | 3인 상호 비평 + NarrativeScore 기반 수렴 + Groupthink 방지 + Fallback | [x] 2026-02-18 |

**리스크 대응** (Gemini 크로스 리뷰): 예측 불가능성(KPI 수렴+Fallback), 비용 ROI(Phase별 A/B 테스트 필수), 레이턴시(Speculative Execution), State 비대화(Condensation). [상세](FEATURES/TRUE_AGENTIC_ARCHITECTURE.md#6-리스크-대응-gemini-크로스-리뷰-반영)

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
| ~~LoRA trigger word 중복 주입 수정 (`flat_color` + `flat color` 3중 적용 → dedup 정규화)~~ | ~~완료 (2026-02-15)~~ |
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
                              7-6 (Scene UX Enhancement) → 7-X (UI Polish) → 7-Y (Layout Standardization) → 7-Z (Home & Publish UX)
                               Figma 기반 씬 편집 개선       공통 컴포넌트/단축키   Manage→Library+Settings 분리    대시보드+Publish 재설계
                                                                                                                          ↓
                                                                                                                    9 (Agentic Pipeline)
                                                                                                                     LangGraph 전환
                                                                                                                          ↓
                                                                                                                    10 (True Agentic) ★최우선
                                                                                                                     ReAct+Tools+Communication
                                                                                                                          ↓
                                                                                                                    8 (Multi-Style)
                                                                                                                        Future
```

**현재 진행 상태** (2026-02-18):
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
- **Phase 7-Y**: Layout Standardization **완료** (2026-02-15). Manage→Library+Settings 분리, 공유 레이아웃(AppThreeColumnLayout/AppSidebar/AppMobileTabBar), Home 리디자인(HomeVideoFeed), 네비 4탭(Home/Studio/Library/Settings), Lab 비활성화. 테스트 동기화 39건 수정 완료. **Unified Setup Wizard** 추가 (채널→시리즈 2-step, 5곳 트리거). **캐릭터 편집 UX 통일** (02-17): 위자드(AppearanceStep/LoraStep) 재활용으로 편집 페이지 태그/LoRA 편집 활성화, `useTagData` 훅 + `tagUtils` 순수함수 추출로 중복 ~90줄 제거, Gender/PromptMode pill 스타일 통일, Input/Textarea 컴포넌트 통일
- **렌더링 품질 개선** (2026-02-14~17): Post Type Scene Text 동적 높이, Full Type Safe Zone, 블러 배경 품질, 폰트 크기 동적 조정, 배경 밝기 기반 텍스트 색상, 얼굴 감지 스마트 크롭, TTS 오디오 정규화, Post Type 해시태그 Instagram Blue. **얼굴 감지 개선** (02-17): anime cascade 우선 + 오감지 검증 강화(최소 크기 8%+하단 30% 필터, 표준 cascade minNeighbors 5→8). SB426 검증: OLD 7감지(오감지 3건)→NEW 4감지(오감지 0건). 총 52개 테스트 추가
- **Phase 7-Z**: Home Dashboard & Publish UX Redesign — **Phase A+C 완료** (2026-02-15). Home 2-Column 대시보드 + Continue Working + Gallery 캐러셀 + QuickActions/Stats 사이드바 컴팩트화 + `formatRelativeTime` 공통 유틸 추출(+10 테스트). **Phase C**: Publish 3-Column 재배치(VideoPreviewHero 센터, 설정 접힘, Recent Videos 리스트), `usePublishRender` 훅 추출(349→112줄) + `useShallow` 선택적 구독 최적화(30→21필드, `getState()` 콜백 패턴), 3탭 UI 일관성 통일(패딩/헤더/max-width). **Quick Actions 개선** (02-17): New Project→Create Story 교체(`/studio?new=true` 직행, useUIStore 의존 제거). **Phase A+B 완료** (Phase B/D 불필요 항목 제거)
- **Phase 9**: Agentic AI Pipeline — **Phase 0~5E 완료** (2026-02-15~17). **15-노드** 조건 분기 그래프 (Quick 6노드 / Full 14노드), Quick/Full 모드 + Preset 3종, Revise 루프 + Human Gate, reasoning [왜?] 패널. **Phase 2**: AsyncPostgresStore Memory, LangFuse v3 Docker Observability, Research/Learn 노드 구현, 피드백 수집 API+UI, Memory 관리 Settings 탭. **AsyncPostgresStore 싱글턴 버그 수정** (from_conn_string async context manager → 직접 AsyncConnection 패턴). **LangFuse v3 Docker 인프라 완전 가동** (2026-02-16): docker-compose 6서비스(PG+ClickHouse+Redis+MinIO+Web+Worker), MinIO 버킷 생성(langfuse-events/langfuse-media), S3 Region 설정, observability.py SDK v3 API 대응(`Langfuse()` 전역 초기화 + `CallbackHandler`), langchain 의존성 추가, LangGraph 대본 생성 트레이스 기록 확인 완료. **human_gate interrupt 시 중간 결과 기록** (2026-02-16): `update_trace_on_interrupt()`로 트레이스 output=null → draft_scenes/review_result 기록, ERROR 상태 방지. **Phase 3 Creative 재평가 완료** (2026-02-16): 선택지 C(폐기) 결정 — Creative Lab UI/라우터/파이프라인은 Phase 7-4 D에서 이미 삭제됨. 잔여 서비스(debate_agents, creative_qc)는 LangGraph Production 노드로 흡수. creative_utils.py V2 데드 코드 258줄 정리. **Phase 4B Agent Spec + Director 완료** (2026-02-16): Agentic AI 기준 분류 체계(AI Agent 7 / Hybrid 2 / System 4), 네이밍 통일(debate→critic, draft→writer), Director Agent 신규(Production chain 통합 검증 + revision 루프), `_DIRECTOR_DECISION_MAP` 명시적 라우팅, AGENT_SPEC.md 엔지니어링 스펙. **Phase 4C Pipeline 고도화 완료** (2026-02-16): Director feedback→타겟 노드 주입(cinematographer/tts/sound/copyright/revise), Production Chain 병렬화(LangGraph fan-out: tts/sound/copyright 동시 실행), Explain Node(Full 모드 창작 결정 설명), fallback 패턴(tts/sound 에러 시 빈 결과 반환, 병렬 안전). 13→14노드, AGENT_SPEC.md v1.1. **Phase 5 설계 완료** (2026-02-17): 4-Agent 크로스 분석 합의 — Multi-draft(3x) 반대, Concept Gate 방식 채택. 5A 서사 품질 평가(Hook 40%+감정 25%+반전 20%+톤 10%+정합성 5%), 5B Concept Gate(Critic 3컨셉 사용자 선택), 5C AI 투명성 UX(Pipeline Stepper+Reasoning 패널+Score 시각화), 5D 프리셋 피드백 버튼. [명세](FEATURES/SCRIPT_QUALITY_UX.md) [Agent 스펙](../03_engineering/backend/AGENT_SPEC.md)
- **VRT Baseline**: 24개 스크린샷, 8개 스펙 완료 (6-7 #2)
- **안정성 수정** (2026-02-16~17): Script 탭 unmount 시 scenes 소실 버그 수정 (save() 후 useStoryboardStore 즉시 동기화), ScenesTab 리팩터링 잔여 데드코드 제거 (resolvedIpAdapter), TTS normalization 플레이키 테스트 수정, **Edit→Script 탭 전환 시 대본 소실 수정** (StudioWorkspace 조건부 렌더링 → CSS hidden으로 ScriptTab 상태 유지), **Character Preset 동기화 수정** (useScriptEditor 로컬 state의 characterId/Name을 syncToGlobalStore로 useStoryboardStore에 전파 → AutoRun Preflight에서 캐릭터 인식), **빠른 수정 대본 미반영 수정** (02-17): 자동 review 루프의 revision_count가 사용자 수동 수정과 공유되어 카운터 소진 시 revise_node no-op 리턴 → human_gate에서 revise 시 revision_count 리셋 + 현재 대본 컨텍스트를 Gemini에 주입하여 실질적 수정 가능
- **Phase 9-5A Narrative Quality 완료** (2026-02-17): `create_storyboard.j2`에 Hook/Rising/Climax/Resolution 구조 가이드 추가. Review 노드 3-tier 검증(규칙→Gemini 피드백→서사 품질 평가). `NarrativeScore` TypedDict(Hook 40%+감정 25%+반전 20%+톤 10%+정합성 5%), `narrative_review.j2` 템플릿, `LANGGRAPH_NARRATIVE_THRESHOLD=0.6` 임계값, Revise 노드 narrative feedback 주입. Quick 모드 스킵, Gemini 에러 시 graceful degradation. 10개 테스트 추가
- **Phase 9-5B Concept Gate 완료** (2026-02-17): concept_gate 노드 삽입(critic↔writer 사이), Creator 모드 interrupt()로 3컨셉 사용자 선택, Full Auto pass-through. Writer가 selected_concept를 description에 주입. SSE 일반화(_read_interrupt_state → tuple[str, dict] 반환, 동적 interrupt 노드명). ConceptSelectionPanel UI(AI 추천 뱃지, 카드 선택). 14→**15노드** 파이프라인. 10개 테스트 추가
- **Phase 9-5D Interactive Feedback 완료** (2026-02-17): FEEDBACK_PRESETS 4종(hook_boost/more_dramatic/tone_change/shorten) config SSOT, concept_gate 3-action 분기(select/regenerate/custom_concept), route_after_concept_gate 조건 라우팅(concept_gate→writer|critic), MAX_CONCEPT_REGEN=2 제한. FeedbackPresetButtons UI(파라미터 chip 선택), ConceptSelectionPanel 재생성/직접입력 폼, ReviewApprovalPanel 프리셋 통합, useScriptEditor resume 확장(ResumeOptions). _update_user_preferences → services/agent/feedback.py 추출. 10개 테스트 추가
- **Phase 9-5C AI Transparency UX 완료** (2026-02-17): Backend `_build_node_payload()` → `_extract_node_result()` 매핑 딕셔너리로 critic/review/director/explain의 reasoning 데이터를 `node_result` SSE 필드로 전달. Frontend `pipelineSteps.ts` 순수 함수(15노드→7/3 논리 스텝 매핑), `PipelineStepper` 수평 멀티스텝 인디케이터(done/running/idle/error 상태 + pulse 애니메이션), `NarrativeScoreChart` 5메트릭 바 차트(compact/full 모드), `AgentReasoningPanel` 아코디언(Critic/Review/Director/Explain 섹션, `reasoning/ReasoningSections.tsx` 분리), ReviewApprovalPanel NarrativeScore compact 내장, ManualScriptEditor Progress bar→PipelineStepper 교체 + AgentReasoningPanel 통합 + References 입력(Full mode). `isNarrativeScore()` 타입 가드로 런타임 안전성 강화. 10개 pipelineSteps 단위 테스트 추가
- **Phase 9-5E Research References 완료** (2026-02-17): Research 노드에 사용자 소재(URL/텍스트) 분석 기능 추가. `references` 필드 API→State 전파(schemas→routers→state). URL fetch: httpx + SSRF 방어(private IP 차단, timeout/size 제한), HTML strip → Gemini 분석 → research_brief 구성, Gemini 실패 시 원문 fallback. `config_pipelines` RESEARCH_* 상수 3개. 테스트 22개 추가(URL 판별, SSRF 12케이스, HTML→text, Gemini mock, fallback)
- **Langfuse Trace 통합** (2026-02-17): interrupt/resume 별도 trace → 동일 trace 통합. 요청별 `CallbackHandler` 생성(싱글턴→per-request)으로 동시성 안전 보장. generate 시 trace_id를 SSE로 클라이언트 전달 → resume 시 동일 trace_id로 handler 생성. Frontend `traceId` 상태 관리 + `ScriptResumeRequest.trace_id` 필드 추가. **Per-node trace 확장**: review(gemini_evaluate+narrative_evaluate), production(cinematographer/tts/sound/copyright), creative_agent(GeminiProvider), writer(gemini_generator) — 모든 Gemini LLM 호출에 `trace_llm_call` 컨텍스트 매니저 래핑. **v3 SDK 마이그레이션 수정** (02-17): `CallbackHandler(trace_id=)` v2 API → `CallbackHandler(trace_context={"trace_id":})` v3 API 전환, `last_trace_id` 속성 → `trace_context` dict 접근으로 교체. v2 파라미터 TypeError가 except에서 조용히 잡혀 핸들러 None 반환 → 각 Gemini 호출이 개별 트레이스로 분리되던 버그 해소
- **Phase 10**: True Agentic Architecture — **Phase 0+A+B+C-1 완료** (2026-02-18). Phase 0: 벤치마크 인프라. **Phase A**: Director ReAct Loop, Review Self-Reflection, Writer Planning Step. **Phase B**: Gemini Function Calling 인프라, Research Agent Tool-Calling (5개 도구), Cinematographer Agent Tool-Calling (4개 도구). **Phase C-1 완료** (2026-02-18): Agent Message Protocol + State Condensation. `messages.py`: AgentMessage TypedDict, format/condense/truncate 유틸리티, MAX_MESSAGE_WINDOW=10, MAX_CONTEXT_TOKENS=2000. ScriptState: `agent_messages`, `agent_summary` 필드. 13개 신규 테스트. 76개 테스트 추가 (Phase A 27 + Phase B 36 + Phase C-1 13). 다음: Phase C-2 Director ↔ Production 양방향 소통. [명세](FEATURES/TRUE_AGENTIC_ARCHITECTURE.md)
- **테스트**: Backend 1,719 passed + Frontend 319 passed = **총 2,038개** (Phase 10: 76개)

### 잔여 작업 우선순위 (재정리 2026-02-18)

**Tier 0 — True Agentic Architecture (최우선)**

> **Gate 규칙**: 각 Phase 완료 후 A/B 테스트로 품질 효과 검증. 미달 시 롤백/조정 후 다음 Phase 진행.

| 순위 | 출처 | 작업 | 기간 | Gate 조건 |
|------|------|------|------|----------|
| 0 | 10 P0 | **Benchmark Baseline 수집** (샘플 10건 × 10회 = 100회, LangFuse 기록) | 1일 | Baseline 데이터 확보 |
| 1 | 10 A-1 | Director ReAct Loop (Observe→Think→Act) | 2-3일 | — |
| 2 | 10 A-2 | Review Self-Reflection (실패 원인 분석 + 수정 전략) | 1-2일 | — |
| 3 | 10 A-3 | Writer Planning Step (계획 → 생성) | 1일 | **Phase A Gate**: NarrativeScore +10% (10회 A/B) |
| 4 | 10 B-1 | Gemini Function Calling 인프라 | 2일 | — |
| 5 | 10 B-2 | Research Agent Tool-Calling | 2-3일 | — |
| 6 | 10 B-3 | Cinematographer Agent Tool-Calling | 2일 | **Phase B Gate**: Match Rate +15% |
| 7 | 10 C-1~3 | Agent Communication + Speculative Execution + State Condensation | 7-10일 | **Phase C Gate**: 복합 +20%, 레이턴시 120초 이내 |

**Tier 3 — 장기**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| 8 | 9 P4 | PipelineControl 커스텀, 분산 큐 | 규모 확장 시 |
| 9 | 7-2 P3 | 배치 렌더링, 브랜딩, 분석 대시보드 | 대규모 운영 |
| 10 | 8 | Multi-Style Architecture | Anime 외 화풍 확장 |

**상세 변경 이력**: Phase별 변경사항은 각 Phase의 DoD 및 커밋 로그 참조. Phase 7-1 완료 항목 상세는 [Phase 7-1 커밋 로그](../99_archive/archive/) 참조.
