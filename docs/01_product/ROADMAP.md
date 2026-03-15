# Shorts Producer — Master Roadmap

**원칙**: 안정성 → 리팩토링 → 안정성 → 신규 개발 사이클. 영상 품질 100% 일관성(Zero Variance) 유지.

---

## 현재 상태 (2026-03-15)

| 항목 | 상태 |
|------|------|
| Phase 5~7 계열 | 전체 완료 (ARCHIVED) |
| Phase 8 (Multi-Style) | 전체 완료 (ARCHIVED) |
| Phase 9 (Agentic Pipeline) | 전체 완료 (ARCHIVED) |
| Phase 10 (True Agentic) | 전체 완료 (ARCHIVED) |
| Phase 11 (Scene Diversity) | 전체 완료 (ARCHIVED) |
| Phase 12 (Agent Enhancement & AI BGM) | 전체 완료 (ARCHIVED) |
| Phase 13 (Creative Control & Production Speed) | 전체 완료 (ARCHIVED) |
| Phase 14 (ControlNet Pose Pipeline) | 전체 완료 (ARCHIVED) |
| Phase 15 (Prompt Input UX 고도화) | 전체 완료 (ARCHIVED) |
| Phase 16 (WD14 Smart Validation) | 전체 완료 (ARCHIVED) |
| Phase 17 (Service/Admin 분리) | 전체 완료 (ARCHIVED) |
| Cross Audit P0~P3 | 전체 완료 — 106건 |
| Phase 18 (Stage Workflow) | 전체 완료 (ARCHIVED) |
| Phase 19 (Studio 탭 페르소나 재배치) | 전체 완료 (ARCHIVED) |
| Phase 20 (Agent-Aware Inventory) | 전체 완료 (ARCHIVED) |
| DB Schema Cleanup | 전체 완료 (ARCHIVED) |
| Phase 21 (Persona-based Menu Reorganization) | 전체 완료 (ARCHIVED) |
| Phase 22 (Backend Complete Image Generation) | 전체 완료 (ARCHIVED) |
| Phase 23 (Project/Group UX 개선) | 전체 완료 (ARCHIVED) |
| Phase 24 (Script 탭 → 하이브리드 채팅 AI) | 전체 완료 (ARCHIVED) |
| Phase 25 (Director 자율 실행 계획) | 전체 완료 (ARCHIVED) |
| Phase 26 (Script 협업형 UX) | 전체 완료 (ARCHIVED) |
| Character-Group 소유권 개편 | 전체 완료 (ARCHIVED) |
| Phase 27 (Chat System UX & Architecture) | 전체 완료 (ARCHIVED) |
| Phase 28 (Pipeline Resilience) | 전체 완료 (ARCHIVED) |
| Phase 29 (Video Pre-validation) | 전체 완료 (ARCHIVED) |
| Casting 네이밍 정규화 | 전체 완료 (ARCHIVED) |
| Checkpointer 리팩토링 | 전체 완료 (ARCHIVED) |
| **Phase 30 (Character Consistency V2)** | **전체 완료 (ARCHIVED)** |
| **Phase 31 (UX Navigation Overhaul)** | **전체 완료 (ARCHIVED)** |
| **Forge 전환 (Stage 1)** | **전체 완료 (ARCHIVED)** |
| **NoobAI-XL V-Pred 전환 (Stage 4)** | **전체 완료 (ARCHIVED)** |
| **LLM Provider 추상화 Phase A~E** | **전체 완료 (ARCHIVED)** |
| **Phase 32 (Auto Run Pipeline Hardening)** | **전체 완료 (17/17)** |
| 테스트 | Backend 3,466 + Frontend 543 + E2E 36 = **총 4,045개** |

### 진행 중

- **Phase 33**: Hybrid Match Rate (WD14 + Gemini Vision) — 21/22 완료 (잔여: E-2) ([명세](FEATURES/HYBRID_MATCH_RATE.md))

### 최근 작업

- **03-15 Phase 33 진행**: Sprint A~E 구현 (21/22) — DB evaluation_details JSONB + Frontend wd14_match_rate 표시 + PENDING 뱃지 + validation_gemini.py 분리 + 테스트 26개
- **03-15 Phase 32 완료**: Auto Run Pipeline Hardening 17/17 — TTS prebuild API + AutoRun Progress Bar + BG Quality SSOT + SCENE_TRANSIENT_FIELDS 정합성 + preflight.ts 분리 + 테스트 61개 추가
- **03-15 Phase 32 착수**: Stage 루프 버그(A-1/A-2) + TTS is_temp promote(B-2) + Preflight bgmMode(C-1/C-2) + ResumeConfirmModal 연결(D-1) + 완료 단계 비활성화(D-2) + batch seed/canStore(D-3/D-4) + TTS_ENGINE SSOT(E-1) + location key 헬퍼(E-3) + polling AbortSignal(E-4) + asyncio.gather 병렬화(E-6). 14/17 항목 완료
- **03-15 안정화**: Finalize identity 태그 누출 차단(`_enforce_character_clothing` 3단계 제거 로직) + context_tags alias 재적용 순서 보장(`_rebuild_image_prompt_from_context_tags` 후 `_apply_tag_aliases` 재실행) + TTS decrackle voiced-region P99.5 기반 정밀화 + `_load_tags_by_groups` DB 쿼리 통합 + 테스트 +15건
- **03-03~03-15 작업**: Phase 29~31, Forge 전환, NoobAI-XL V-Pred 전환, LLM Provider 추상화 A~E, LangFuse Observability 개선, MusicGen/TTS 품질, 안정화. [아카이브](../99_archive/archive/ROADMAP_PHASE_27_31.md)
- **03-01~03-02 작업**: Phase 26~28, Chat System, Pipeline Resilience, Character-Group 소유권, Service/Admin 분리, Casting/Checkpointer, QA 테스트 등. [아카이브](../99_archive/archive/ROADMAP_PHASE_27_31.md)
- **03-01 이전 작업**: Phase 25, Studio 감사, Danbooru 태그 수정 등. [아카이브](../99_archive/archive/ROADMAP_PHASE_25_26.md)
- **02-28 작업**: Phase 21~24 구현, StyleProfile 5개 체제 정립, DB Schema 정리. [아카이브](../99_archive/archive/ROADMAP_PHASE_21_24.md)
- **02-26~02-27 작업**: Phase 18~20, Cross Audit 106건. [아카이브](../99_archive/archive/ROADMAP_PHASE_19_20.md)

---

## Completed Phases (ARCHIVED)

| Phase | 이름 | 핵심 성과 | 아카이브 |
|-------|------|----------|----------|
| 1-4 | Foundation & Refactoring | 기반 구축 + 코드 정리 | [아카이브](../99_archive/archive/ROADMAP_PHASE_1_4.md) |
| 5 | High-End Production | Ken Burns, Scene Text, 13종 전환, Preset System, 402개 테스트 | [아카이브](../99_archive/archive/ROADMAP_PHASE_1_4.md) |
| 6 | Character & Prompt System (v2.0) | PostgreSQL/Alembic, 12-Layer PromptBuilder, Qwen3-TTS, 786개 테스트 | [아카이브](../99_archive/archive/ROADMAP_PHASE_6.md) |
| 7-0 | ControlNet & Pose Control | ControlNet 포즈 제어, IP-Adapter 캐릭터 일관성, 28개 포즈 | — |
| 7-1 | UX & Feature Expansion | Quick Start, Multi-Character, Scene Builder, YouTube Upload 등 27건 | [아카이브](../99_archive/archive/ROADMAP_PHASE_7_1.md) |
| 7-2 | Project/Group System | 채널/시리즈 계층, 설정 상속 엔진, Channel DNA | [명세](FEATURES/PROJECT_GROUP.md) |
| 7-3 | Production Workspace | /voices, /music, /backgrounds 독립 페이지 | [아카이브](../99_archive/archive/ROADMAP_PHASE_7_3.md) |
| 7-4 | Studio + Script Vertical | Zustand 4-Store 분할, /scripts 페이지, 칸반/타임라인 뷰 | [명세](FEATURES/STUDIO_VERTICAL_ARCHITECTURE.md) |
| 7-5 | UX/UI Quality & Reliability | 8개 에이전트 크로스 분석, 30건 (Toast, SSE, UUID, 페이지네이션) | [아카이브](../99_archive/archive/ROADMAP_PHASE_7_5.md) |
| 7-6 | Scene UX Enhancement | Figma 기반 씬 편집, 완성도 dot, 3탭 분리, DnD, Publish 통합 | [명세](FEATURES/SCENE_UX_ENHANCEMENT.md) |
| 7-Y | Layout Standardization | Library+Settings 분리, 공유 레이아웃, 네비 4탭, Setup Wizard | [아카이브](../99_archive/archive/ROADMAP_PHASE_7_Y.md) |
| 7-Z | Home Dashboard & Publish UX | 창작 대시보드 전환, 2-Column Home, 3-Column Publish | [아카이브](../99_archive/archive/ROADMAP_PHASE_7_Z.md) |
| 8 | Multi-Style Architecture | StyleProfile, LoRA base_model, Checkpoint 자동 전환, Hi-Res 기본값 | [아카이브](../99_archive/archive/ROADMAP_PHASE_8_14_16.md) |
| 9 | Agentic AI Pipeline | LangGraph 19-노드, Memory Store, LangFuse, Concept Gate, NarrativeScore | [아카이브](../99_archive/archive/ROADMAP_PHASE_9.md) · [명세](FEATURES/AGENTIC_PIPELINE.md) |
| 10 | True Agentic Architecture | ReAct Loop, Director-as-Orchestrator, Gemini Function Calling, 3-Architect Debate | [아카이브](../99_archive/archive/ROADMAP_PHASE_10.md) · [명세](FEATURES/AGENTIC_PIPELINE.md) |
| 11 | Scene Diversity & Frontal Bias Fix | 정면 편향 해소, Gaze 5종, 정면 비율 22%, Tier 2 Pipeline 고도화 | [아카이브](../99_archive/archive/ROADMAP_PHASE_11.md) |
| 12 | Agent Enhancement & AI BGM | Agent Bug Fix 5건, Data Flow 10건, 3-Mode BGM, Gemini Model Upgrade | [아카이브](../99_archive/archive/ROADMAP_PHASE_12_13.md) |
| 13 | Creative Control & Production Speed | 성능 최적화 9건, 이미지 UX 5건, Structure 6건, Clothing Override 3건 | [아카이브](../99_archive/archive/ROADMAP_PHASE_12_13.md) |
| 14 | ControlNet Pose Pipeline | 포즈 28개 명시, pose/gaze fallback, LLM 하드코딩 제거 3종 | [아카이브](../99_archive/archive/ROADMAP_PHASE_8_14_16.md) |
| 15 | Prompt Input UX 고도화 | 12-Layer 미리보기, TagAutocomplete 8곳, 태그 검증 5곳, Visual Tag Browser. 18/18 | [아카이브](../99_archive/archive/ROADMAP_PHASE_15.md) · [명세](FEATURES/PROMPT_INPUT_UX.md) |
| 16 | WD14 Smart Validation | Effectiveness 필터링 제거, Critical Failure, Adjusted Match Rate, Cross-Scene Consistency | [아카이브](../99_archive/archive/ROADMAP_PHASE_8_14_16.md) · [명세](FEATURES/CROSS_SCENE_CONSISTENCY.md) |
| 17 | Service/Admin 분리 | API 29개 라우터, `/api/v1/` + `/api/admin/` 2-tier, Route Group, UI 간소화. 26항목 | [아카이브](../99_archive/archive/ROADMAP_PHASE_17.md) · [명세](FEATURES/SERVICE_ADMIN_SEPARATION.md) |
| 18 | Stage Workflow | Script→Stage→Direct→Publish 4단계, Background Generation Pipeline, 29건 | [아카이브](../99_archive/archive/ROADMAP_PHASE_19_20.md) · [명세](FEATURES/STAGE_WORKFLOW.md) |
| 19 | Studio 탭 페르소나 재배치 | Stage SSOT, Direct 경량화, Publish 읽기 전용, Dead code 삭제. 15/15 | [아카이브](../99_archive/archive/ROADMAP_PHASE_19_20.md) · [명세](FEATURES/STUDIO_TAB_PERSONA_REORGANIZATION.md) |
| 20 | Agent-Aware Inventory | Director 캐스팅, Autonomous Express, Casting UX, inventory_resolve 노드. 22/22 | [아카이브](../99_archive/archive/ROADMAP_PHASE_19_20.md) · [명세](FEATURES/AGENT_AWARE_INVENTORY_PIPELINE.md) |
| DB Cleanup | Schema Cleanup | Sprint A 7건 FIX + Sprint B 3건 DROP + Checkpoint GC. 10/11 (1건 취소) | [아카이브](../99_archive/archive/ROADMAP_PHASE_19_20.md) · [명세](FEATURES/DB_SCHEMA_CLEANUP.md) |
| 21 | Persona-based Menu Reorganization | Library/Settings/Dev 3-tier, Shell 3종, admin dead code 제거. 6/6 | [아카이브](../99_archive/archive/ROADMAP_PHASE_21_24.md) · [명세](FEATURES/PERSONA_MENU_REORGANIZATION.md) |
| 22 | Backend Complete Image Generation | SD 생성→저장 Backend 자율 완결, Frontend SPOF 제거, Graceful Degradation | [아카이브](../99_archive/archive/ROADMAP_PHASE_21_24.md) · [명세](FEATURES/IMAGE_GENERATION_PROGRESS.md) |
| 23 | Project/Group UX 개선 | Zero-Config, 용어 통일(채널/시리즈/영상), ConfigBadges, 내비게이션 개선. 4/4 | [아카이브](../99_archive/archive/ROADMAP_PHASE_21_24.md) · [명세](FEATURES/PROJECT_GROUP.md) |
| 24 | Script 탭 → 하이브리드 채팅 AI | 좌측 설정 사이드바+우측 채팅, analyze-topic API, SSE 콜백, Chat UI 7종, 코드 리뷰 7건 수정 | [아카이브](../99_archive/archive/ROADMAP_PHASE_21_24.md) |
| 25 | Director 자율 실행 계획 | 프리셋 제거, Director execution_plan 자율 결정, director_plan_lite/human_gate 삭제, production 항상 실행 | [아카이브](../99_archive/archive/ROADMAP_PHASE_25_26.md) |
| 26 | Script 협업형 UX | 스트리밍 메시지, 3단계 모드, Plan 검토, 대화형 씬 수정 | [아카이브](../99_archive/archive/ROADMAP_PHASE_25_26.md) · [명세](FEATURES/SCRIPT_COLLABORATIVE_UX.md) |
| 27 | Chat System UX & Architecture | Discriminated Union, Zustand persist, AbortController, a11y, 에러 복구, chat_context→Writer/Director 연결 | [아카이브](../99_archive/archive/ROADMAP_PHASE_27_31.md) · [명세](FEATURES/CHAT_SYSTEM_ENHANCEMENT.md) |
| 28 | Pipeline Resilience | Phase A(빈 씬 가드)+B(에러 복구+글로벌 캡)+C(관측성+배지)+D(데이터 무결성). 70개 테스트 | [아카이브](../99_archive/archive/ROADMAP_PHASE_27_31.md) · [명세](FEATURES/PIPELINE_RESILIENCE.md) |
| 29 | Video Pre-validation | TTS 프리뷰/렌더 연결, Spread Passthrough 8함수, 타임라인 시각화, 사전검증 리포트 7항목 | [아카이브](../99_archive/archive/ROADMAP_PHASE_27_31.md) · [명세](FEATURES/VIDEO_PREVALIDATION.md) |
| 30 | Character Consistency V2 | B+(복장 교정 2단계)+H~P(context_tags/역할분리/LoRA스케일/프롬프트통합/sitting/Multi-char/배경일관성), Location Planner 독립 노드 | [아카이브](../99_archive/archive/ROADMAP_PHASE_27_31.md) · [명세](FEATURES/CHARACTER_CONSISTENCY_V2.md) |
| 31 | UX Navigation Overhaul | Admin 유령 삭제, 상태 누수, LoRA split, SubNavShell, Quick-Start, Group SoftDelete+Trash | [아카이브](../99_archive/archive/ROADMAP_PHASE_27_31.md) · [명세](FEATURES/UX_NAVIGATION_OVERHAUL.md) |
| — | Forge 전환 + NoobAI-XL V-Pred | A1111→Forge Docker, SD1.5→NoobAI-XL V-Pred 1.0, CFG 4.5/832x1216, SDXL LoRA 3종, DB 클렌징 | [아카이브](../99_archive/archive/ROADMAP_PHASE_27_31.md) |
| — | LLM Provider 추상화 (A~E) | `services/llm/` 패키지, `google.genai` 직결 제거, trace+PROHIBITED fallback 중복 해소, ruff CLEAN | [아카이브](../99_archive/archive/ROADMAP_PHASE_27_31.md) · [설계](../03_engineering/backend/LLM_PROVIDER_ABSTRACTION.md) |

---

## Phase 32: Auto Run Pipeline Hardening (진행중)

**목표**: Auto Run(Autopilot) 핵심 버그 수정 + TTS 단계 추가 + Resume 기능 연결
**명세**: [FEATURES/AUTO_RUN_PIPELINE_HARDENING.md](FEATURES/AUTO_RUN_PIPELINE_HARDENING.md)

### Sprint A: Stage 루프 버그 수정 (P0)
- [x] A-1: `checkStageStep` 환경 태그 없는 씬 예외 처리 — `hasEnvironmentTags()` 헬퍼 + `withoutBg` 필터 조건 추가
- [x] A-2: stage 부분 할당 실패 경고 로그 — assign 후 env 태그 있는 미할당 씬 카운트 경고

### Sprint B: TTS 단계 추가 및 Asset 보호 (P0)
- [x] B-1: `AUTO_RUN_STEPS`에 "tts" 단계 추가 + TTS prebuild API 구현 (Backend) + `checkTtsStep` 추가
- [x] B-2: render 완료 후 사용된 tts_asset `is_temp=False` promote — GC 손실 방지 (`scene_processing.py`)
- [x] B-3: `SCENE_TRANSIENT_FIELDS`와 `tts_asset_id` 의미론적 정합성 명시

### Sprint C: Preflight 정확성 개선 (P0)
- [x] C-1: `checkBgm()`에 `bgmMode` 파라미터 추가 — bgmMode="auto" 시 BGM 경고 제거
- [x] C-2: `pendingAutoRun`/`onResume`/`onRestart` 3곳 모두 preflight 기반 `stepsToRun` 결정

### Sprint D: P1 버그 수정
- [x] D-1: `ResumeConfirmModal` 연결 — `studio/page.tsx` checkpoint localStorage 저장/로드 + 모달 표시 + resume 로직
- [x] D-2: Resume 시 완료된 단계 버튼 비활성 — `AutoRunStatus.tsx` isDone 단계는 span 렌더링
- [x] D-3: `batchActions.ts` seed 강제 `-1` 제거 → `Math.random()` 명시적 seed
- [x] D-4: `generateBatchImages` canStore=false → `console.warn` 경고 로그
- [x] D-5: `autoRunProgress` progress bar 연결 — `AutoRunStatus` props에 전달

### Sprint E: P2 코드 품질
- [x] E-1: `tts_engine: "qwen"` 하드코딩 2곳 → `TTS_ENGINE` 상수 SSOT (`constants/index.ts`)
- [x] E-2: `_BG_QUALITY_OVERRIDES` StyleProfile ID 하드코딩 → DB/config.py 이동 (DBA 리뷰)
- [x] E-3: location key 계산 로직 중복 → `_compute_location_key()` 헬퍼로 통합
- [x] E-4: `renderWithProgress` polling 폴백에 AbortSignal 전달
- [x] E-5: `lastRenderHash` 미사용 필드 JSDoc 주석 명시
- [x] E-6: Stage location 생성 `asyncio.gather` 병렬화

---

## Phase 33: Hybrid Match Rate — WD14 + Gemini Vision

**목표**: 하드코딩(`WD14_UNMATCHABLE_TAGS`) 제거, `group_name` 기반 태그 라우팅으로 100% 커버리지 매치레이트 구현
**명세**: [FEATURES/HYBRID_MATCH_RATE.md](FEATURES/HYBRID_MATCH_RATE.md)

### Sprint A: 그룹 매핑 정비 (P0)
- [x] A-1: `WD14_DETECTABLE_GROUPS` 확장 — 레거시 미분류 5개 추가 (clothing, action, gesture, eye_detail, identity)
- [x] A-2: `GEMINI_DETECTABLE_GROUPS` 상수 정의 — DB 실제 group_name 기반 11개
- [x] A-3: `SKIPPABLE_GROUPS` 상수 정의 — quality, skip, style 등 6개
- [x] A-4: `WD14_UNMATCHABLE_TAGS` 제거 — 그룹 기반 라우팅으로 완전 대체
- [x] A-5: `classify_prompt_tokens()` — group_name 기반 3그룹 분류 (wd14/gemini/skipped)

### Sprint B: Gemini Vision 평가 엔진 (P0)
- [x] B-1: `evaluate_tags_with_gemini()` — 이미지(base64) + 태그 → 태그별 present/confidence
- [x] B-2: Gemini 프롬프트 템플릿 (`validate_image_tags.j2`) — Danbooru 태그 설명 포함
- [x] B-3: PROHIBITED_CONTENT 폴백 — `_extract_gemini_block_reason()` + `GEMINI_FALLBACK_MODEL` 1회 재시도
- [x] B-4: JSON 파싱 + 에러 처리 (실패 시 빈 리스트, graceful degradation)

### Sprint C: 통합 매치레이트 (P0)
- [x] C-1: `validate_scene_image()` 리팩토링 — WD14 즉시 + Gemini 비동기 (2-Phase)
- [x] C-2: `compare_prompt_to_tags()` 수정 — `only_tokens` 파라미터로 wd14_tokens만 비교
- [x] C-3: `compute_adjusted_match_rate()` deprecated — `wd14_rate` 직접 사용
- [x] C-4: `apply_gemini_evaluation()` — Background task로 Gemini 결과 → DB match_rate 갱신
- [x] C-5: `SceneValidationResponse` 스키마 확장 — `wd14_match_rate`, `gemini_tokens` 필드 추가

### Sprint D: DB + Frontend (P1)
- [x] D-1: `evaluation_details` JSONB 컬럼 추가 (Alembic) — `scene_quality_scores.evaluation_details` JSONB
- [x] D-2: Frontend — `wd14_match_rate` 우선 표시 + PENDING 뱃지 (ValidationOverlay, StoryboardInsights)
- [x] D-3: `SceneInsightsContent` 매치레이트 색상 기준 조정 — `wd14_match_rate ?? match_rate` 폴백
- [x] D-4: 매치레이트 상세 — `gemini_tokens` 대기 개수 표시 + 툴팁 상세

### Sprint E: 최적화 + 테스트 (P2)
- [x] E-1: gemini_tokens 0개면 API 호출 스킵 (apply_gemini_evaluation + router 조건 가드)
- [ ] E-2: 배치 평가 시 Gemini 호출 병합
- [x] E-3: 단위 테스트 18개 (classify_prompt_tokens 6 + _is_skippable_tag 3 + apply_gemini_evaluation 6 + _update_db_match_rate 4 + _parse_gemini_json_array 5)
- [x] E-4: compare_prompt_to_tags only_tokens 테스트 2개 + _update_db_match_rate evaluation_details 테스트 1개 — 총 26개

---

## Development Cycle

```mermaid
graph LR
    P5["Phase 5<br/>High-End<br/>Production"] --> P6["Phase 6<br/>Character &<br/>Prompt v2.0"]
    P6 --> P70["Phase 7-0<br/>ControlNet<br/>& Pose"]
    P70 --> P71["Phase 7-1<br/>UX & Feature<br/>Expansion"]
    P71 --> P72["Phase 7-2<br/>Project/Group<br/>System"]
    P72 --> P73["Phase 7-3<br/>Production<br/>Workspace"]
    P73 --> P74["Phase 7-4<br/>Studio +<br/>Script Vertical"]
    P74 --> P75["Phase 7-5<br/>UX/UI<br/>Quality"]
    P75 --> P76["Phase 7-6<br/>Scene UX<br/>Enhancement"]
    P76 --> P7Y["Phase 7-Y<br/>Layout<br/>Standardization"]
    P7Y --> P7Z["Phase 7-Z<br/>Home &<br/>Publish UX"]
    P7Z --> P9["Phase 9<br/>Agentic<br/>Pipeline"]
    P9 --> P10["Phase 10<br/>True Agentic<br/>Architecture"]
    P10 --> P11["Phase 11<br/>Scene Diversity<br/>& Frontal Bias"]
    P11 --> P12["Phase 12<br/>Agent Enhancement<br/>& AI BGM"]
    P12 --> P13["Phase 13<br/>Creative Control<br/>& Speed"]
    P13 --> P8["Phase 8<br/>Multi-Style"]
    P8 --> P14["Phase 14<br/>ControlNet<br/>Pose"]
    P14 --> P15["Phase 15<br/>Prompt Input<br/>UX 고도화"]
    P15 --> P16["Phase 16<br/>WD14 Smart<br/>Validation"]
    P16 --> P17["Phase 17<br/>Service/Admin<br/>분리"]
    P17 --> P18["Phase 18<br/>Stage<br/>Workflow"]
    P18 --> P19["Phase 19<br/>탭 페르소나<br/>재배치"]
    P19 --> P20["Phase 20<br/>Agent-Aware<br/>Inventory"]
    P20 --> P21["Phase 21<br/>Persona Menu<br/>Reorganization"]
    P21 --> P22["Phase 22<br/>Backend Complete<br/>Image Generation"]
    P22 --> P23["Phase 23<br/>Project/Group<br/>UX 개선"]
    P23 --> P24["Phase 24<br/>하이브리드<br/>채팅 AI"]
    P24 --> P25["Phase 25<br/>Director 자율<br/>실행 계획"]
    P25 --> P26["Phase 26<br/>Script 협업형<br/>UX"]
    P26 --> P27["Phase 27<br/>Chat System<br/>UX & Architecture"]
    P27 --> P28["Phase 28<br/>Pipeline<br/>Resilience"]
    P28 --> P29["Phase 29<br/>Video<br/>Pre-validation"]
    P29 --> P30["Phase 30<br/>Character<br/>Consistency V2"]
    P30 --> P31["Phase 31<br/>UX Navigation<br/>Overhaul"]
    P31 --> P32["Phase 32<br/>Auto Run<br/>Pipeline"]
    P32 --> P33["Phase 33<br/>Hybrid<br/>Match Rate"]

    style P5 fill:#4CAF50,color:#fff
    style P6 fill:#4CAF50,color:#fff
    style P70 fill:#4CAF50,color:#fff
    style P71 fill:#4CAF50,color:#fff
    style P72 fill:#4CAF50,color:#fff
    style P73 fill:#4CAF50,color:#fff
    style P74 fill:#4CAF50,color:#fff
    style P75 fill:#4CAF50,color:#fff
    style P76 fill:#4CAF50,color:#fff
    style P7Y fill:#4CAF50,color:#fff
    style P7Z fill:#4CAF50,color:#fff
    style P9 fill:#4CAF50,color:#fff
    style P10 fill:#4CAF50,color:#fff
    style P11 fill:#4CAF50,color:#fff
    style P12 fill:#4CAF50,color:#fff
    style P13 fill:#4CAF50,color:#fff
    style P8 fill:#4CAF50,color:#fff
    style P14 fill:#4CAF50,color:#fff
    style P15 fill:#4CAF50,color:#fff
    style P16 fill:#4CAF50,color:#fff
    style P17 fill:#4CAF50,color:#fff
    style P18 fill:#4CAF50,color:#fff
    style P19 fill:#4CAF50,color:#fff
    style P20 fill:#4CAF50,color:#fff
    style P21 fill:#4CAF50,color:#fff
    style P22 fill:#4CAF50,color:#fff
    style P23 fill:#4CAF50,color:#fff
    style P24 fill:#4CAF50,color:#fff
    style P25 fill:#4CAF50,color:#fff
    style P26 fill:#4CAF50,color:#fff
    style P27 fill:#4CAF50,color:#fff
    style P28 fill:#4CAF50,color:#fff
    style P29 fill:#4CAF50,color:#fff
    style P30 fill:#4CAF50,color:#fff
    style P31 fill:#4CAF50,color:#fff
    style P32 fill:#4CAF50,color:#fff
    style P33 fill:#FF9800,color:#fff
```

---

## Feature Backlog

Phase 20 이후 또는 우선순위 미정 항목.

### Content & Creative

| 기능 | 참조 |
|------|------|
| VEO Clip (Video Generation 통합) | [명세](FEATURES/VEO_CLIP.md) |
| Profile Export/Import (Style Profile 공유) | [명세](FEATURES/PROFILE_EXPORT_IMPORT.md) |
| Storyboard Version History | — |
| ~~IP-Adapter 캐릭터 유사도 고도화~~ | **Phase 30으로 승격** — [V1 명세](FEATURES/CHARACTER_CONSISTENCY.md) · [V2 명세](FEATURES/CHARACTER_CONSISTENCY_V2.md) |
| 캐릭터 LoRA 학습 파이프라인 | LoRA 트레이닝용 레퍼런스 9세트 생성 + 학습 자동화 (우선순위 낮음) |

### Intelligence & Automation

| 기능 | 참조 |
|------|------|
| Tag Intelligence (채널별 태그 정책 + 데이터 기반 추천) | [명세](FEATURES/PROJECT_GROUP.md) §3-1 |
| Series Intelligence (에피소드 연결 + 성공 패턴 학습) | [명세](FEATURES/PROJECT_GROUP.md) §3-2 |
| LoRA Calibration Automation | — |

### UX & Workflow

| 기능 | 참조 |
|------|------|
| ~~YouTube Upload Phase 2~3~~ | **드롭** — Quota 대시보드/업로드 큐/예약 업로드. Phase 1(수동 업로드)로 충분, 추가 개발 대비 실용 가치 낮음 |
| ~~Express 모드 재검토~~ | **Phase 25에서 해결** — Director 자율 실행으로 대체. 프리셋 제거 완료 |
| ~~Script 생성 후 대화형 수정 루프 (씬 부분 재생성)~~ | **Phase 26 P1에서 완료** — edit-scenes API + SceneEditDiffCard |
| ~~동선 일관성 개편 (Admin 정리, LoRA Library 이동, 상태 누수, API 통일)~~ | **Phase 31로 승격** — [명세](FEATURES/UX_NAVIGATION_OVERHAUL.md) |
| Script Canvas 분할 뷰 (좌 채팅 + 우 씬 프리뷰) | [명세](FEATURES/SCRIPT_COLLABORATIVE_UX.md) §P2 |

### Image Quality & Pose Control

| 기능 | 설명 |
|------|------|
| ~~sitting 계열 ControlNet 근본 해결~~ | **효용 없음으로 보류** — Phase 30-M/N에서 동적 weight + camera 태그 강제로 실용적 해결 완료. 전용 에셋(sitting_side/floor/knees_up) 생성 시 개선 폭 미미 판단 |

### Infrastructure & Scale

| 기능 | 참조 |
|------|------|
| **LLM Provider 추상화 Phase A~E 완료** | [설계](../03_engineering/backend/LLM_PROVIDER_ABSTRACTION.md) — `services/llm/` 패키지 구축, `google.genai` 직결 제거, trace + PROHIBITED fallback 중복 해소. Phase F(OllamaProvider)는 아래 LiteLLM 항목으로 대체 예정 |
| **LiteLLM SDK 도입 (Phase F 대체)** | Gemini 외 두 번째 Provider 실제 도입 시점에 착수. `GeminiProvider` 내부를 LiteLLM 호출로 교체 → 100+ Provider 지원, 폴백/재시도 내장, `OllamaProvider` 직접 구현 불필요. 트레이스 중복 방지를 위해 LiteLLM 자동 LangFuse 콜백 비활성화 + 기존 `trace_llm_call()` 유지 필수. OSS LLMOps Stack(LangGraph + LangFuse + LiteLLM) 표준 조합 완성. **착수 조건**: Ollama/Claude 등 두 번째 Provider 실제 사용 확정 시 |
| PipelineControl 커스텀 (노드 on/off) + 분산 큐 (Celery/Redis) | Phase 9-4 잔여 |
| 배치 렌더링 + 큐 (그룹 일괄 렌더, WebSocket 진행률) | [명세](FEATURES/PROJECT_GROUP.md) §3-3 |
| 브랜딩 시스템 (로고/워터마크, 인트로/아웃트로, 플랫폼별 출력) | [명세](FEATURES/PROJECT_GROUP.md) §3-3 |
| 분석 대시보드 (Match Rate 추이, 프로젝트 간 비교) | [명세](FEATURES/PROJECT_GROUP.md) §3-3 |
