# Shorts Producer — Master Roadmap

**원칙**: 안정성 → 리팩토링 → 안정성 → 신규 개발 사이클. 영상 품질 100% 일관성(Zero Variance) 유지.

---

## 현재 상태 (2026-03-19)

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
| **Phase 32 (Auto Run Pipeline Hardening)** | **전체 완료 (ARCHIVED)** |
| **Phase 33 (Hybrid Match Rate)** | **전체 완료 (ARCHIVED)** |
| **TTS 파이프라인 일원화 (Sprint A~D)** | **전체 완료 (ARCHIVED)** |
| **Phase 35 (GPT-SoVITS TTS 전환)** | **전체 완료** |
| **Phase 36 (LangFuse Prompt Quality Hardening)** | **전체 완료** |
| **Phase 37 (Korean Script Quality)** | **전체 완료** |
| **Phase 38 (LangFuse Scoring)** | **전체 완료** |
| **Enum ID 정규화 (Sprint A)** | **전체 완료** |
| 테스트 | Backend 3,765 + Frontend 599 (65파일) + 16 = **총 4,380개** (03-19 기준) |

### 진행 중

> 현재 태스크는 `.claude/tasks/current.md` 참조.

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
| 32 | Auto Run Pipeline Hardening | Stage 루프 버그, TTS 단계 추가, Resume 연결, Preflight 정확성, 코드 품질. 17/17 | [아카이브](../99_archive/archive/ROADMAP_PHASE_32_33.md) · [명세](FEATURES/AUTO_RUN_PIPELINE_HARDENING.md) |
| 33 | Hybrid Match Rate | WD14+Gemini Vision 2-Phase, group_name 태그 라우팅, 배치 Gemini 병합, 테스트 33개. 22/22 | [아카이브](../99_archive/archive/ROADMAP_PHASE_32_33.md) · [명세](FEATURES/HYBRID_MATCH_RATE.md) |
| — | TTS 파이프라인 일원화 (Sprint A~D) | `generate_tts_audio()` SSOT, preview/prebuild/render 3경로 통합, tts_asset_id 자동 무효화, prebuild 자동 삽입, scene_processing.py 슬림화 | [설계](../03_engineering/backend/TTS_PIPELINE_UNIFICATION.md) |
| 38 | LangFuse Scoring | 9개 SDK Score + 3개 LLM-as-Judge, observation-level, Score Config API 등록, Gemini client 재연결, 환경 가이드. 테스트 +35개 | [명세](FEATURES/LANGFUSE_SCORING.md) |
| — | Enum ID 정규화 (Sprint A) | Structure/Language snake_case SSOT, coerce 과도기 함수, 중복 상수 6곳 통합, normalize_structure 제거, 47+ 방어 패턴 제거. 테스트 +33개 | [명세](FEATURES/ENUM_ID_NORMALIZATION.md) |

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
    P33 -.-> P34["Phase 34<br/>GPU 순차 독점<br/>& BGM 고도화<br/>(DROPPED)"]

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
    style P33 fill:#4CAF50,color:#fff
    style P34 fill:#F44336,color:#fff
```

---

## Backlog

> 태스크 큐는 `.claude/tasks/backlog.md`로 이관됨 (2026-03-19).
> Roadmap은 Phase/마일스톤 레벨만 관리한다. 개별 태스크를 여기에 쓰지 않는다.
