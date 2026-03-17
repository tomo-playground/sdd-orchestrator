# Shorts Producer — Master Roadmap

**원칙**: 안정성 → 리팩토링 → 안정성 → 신규 개발 사이클. 영상 품질 100% 일관성(Zero Variance) 유지.

---

## 현재 상태 (2026-03-17)

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
| 테스트 | Backend 3,517 + Frontend 543 + E2E 36 = **총 4,096개** |

### 진행 중

(없음)

### 최근 작업

- **03-17 LangFuse Prompt Management 전체 이전 완료**: 28개 프롬프트 chat 타입 LangFuse 관리. Phase 0(트레이싱 가시성 — template_name+system_instruction metadata) → Phase 1(A등급 14개 runtime fetch+fallback) → Phase 1.5(chat 전환 — system/user 분리) → Phase 2(B등급 9개 + include 5개 파셜→Python 변수). `prompt_partials.py`(5개 파셜 Python 전환), `langfuse_prompt.py`(PromptBundle), 업로드 스크립트(chat/text 자동 분류). 29개 테스트 PASS
- **03-16 SSOT 위반 정리 P1+P2 완료 (46/49건)**: config.py 상수화(Hi-Res 4개+SAMPLERS+TTS_ENGINE+ENABLE_HR), `/presets` API 확장(hi_res_defaults+samplers+tts_engine+image_defaults+pipeline_metadata), Frontend 하드코딩 제거(constants→store/presets 동기화, 해상도 6곳→상수/store), controlnet.py weight fallback→상수 참조
- **03-17 Phase 35 완료**: GPT-SoVITS v2 TTS 통합 — SoVITS(:9880 일상TTS) + Qwen3(:8001 보이스디자인 on-demand) + MusicGen(CPU 상주). audio_client SoVITS→Qwen3 fallback, 캐릭터 보이스 레퍼런스 API, 감정별 레퍼런스 탐색, Text Normalization, E2E 검증 완료. SSOT 위반 P0~P2 52건+ 정리
- **03-17 이미지 품질 개선 + 오디오 상주 모드**: 씬 배경 사라짐 근본 수정(캐릭터 negative 정리, scenery 자동주입, IP-Adapter/Reference AdaIN 비활성화), StyleProfile flat_color_v2:0.3 최적화, IP-Adapter weight SSOT 통일(Backend+Frontend), MeMaXL v6 설치, 오디오 서버 persistent 모드(TTS GPU + MusicGen CPU 상주 로드)
- **03-17 Speaker Balance 검증 강화**: Narrated Dialogue 캐릭터 배분 수정 — Review에 비율 검증(20% 미만 ERROR) + Narrator 존재 검증(WARNING) 추가, Revise에서 비율 불균형 Tier 3 재생성 위임, ensure_dialogue_speakers 최종 방어선 비율 검사. 테스트 24개 PASS
- **03-17 화풍/IP-Adapter/프롬프트 품질 개선**: Romantic Warm Anime StyleProfile 구축(flat_color+감성조명), IP-Adapter clip_face→clip(NOOB-IPA-MARK1) SD1.5 잔재 전수 정리, ControlNet 모델명 동적 resolve(Forge 해시 풀네임 호환), CLIP-ViT-bigG preprocessor 자동 매칭, 프롬프트 이중 괄호 방지(weight 재감싸기), TTS 503 재시도(모델 로드 대기), autoSave 무한 재시도 방지, Voice Preset 정비(15개 라인업), Pose 다양성 테스트 12개, system_instruction 사용자 데이터 분리. "우리가 닿는 순간" 시리즈 + 캐릭터(하린/준서) 구축
- **03-16 FastTrack 안정화 + GPU OOM 방지**: FastTrack에서 Cinematographer 실행(캐릭터 일관성), Writer character_id auto-resolve(group fallback), SSE→handleStreamOutcome 캐릭터 반영 통합, Graph 엣지 cinematographer 누락 수정, hydration 가드(ChatArea+ChatMessageList), GPU OOM 방지(TTS on-demand 로드 + idle 2분 자동 언로드). 테스트 33개 PASS
- **03-16 BGM prebuild + Gemini 안전필터 수정 + 인프라 정리**: STAGE에서 BGM 사전 생성(`/stage/bgm-prebuild` API + MusicGen), Gemini system_instruction↔contents 분리(gemini_generator+tag_classifier_llm), FastTrack 기본 BGM 추천, 오디오 서버 CUDA 수정(`run_audio.sh` export), `docker-compose.audio.yml` 삭제, ChatMessageList hydration 가드, TTS_SETUP.md CUDA 문서화. 테스트 48개 PASS
- **03-16 FastTrack 강화 + 새 영상 채팅 잔류 버그 수정**: FastTrack production skip 추가, skip_stages Backend SSOT화(`/presets` API). "새 영상" 클릭 시 이전 채팅이 남는 버그 수정(`chatResetToken` 메커니즘). `storyboardActions.ts` 리팩토링(448→371줄, 헬퍼 추출). `persistStoryboard` 404 재귀 방어 + `pendingAutoRun` storyboardId null 방어. 테스트 37개 PASS
- **03-16 Script 탭 코드 리뷰 4건 수정**: 에러 이중 표시(ErrorCard+Toast→ErrorCard만), ProgressBar label SSOT(Backend label 우선), typing indicator contentType 분리, 새 영상 채팅 히스토리 보존(`__new__` 임시 key). 테스트 +9개
- **03-16 씬 소실 방어 + LangFuse 정확성**: syncToGlobalStore→onSaved 순서 보장, pendingAutoRun scenesReady 가드, CompletionCard Zustand 직참조, LangFuse interrupt→metadata 이동 + interrupt_node 동적 전달 + final_output 캡처
- **03-16 스크립트 생성 후 씬 소실 버그 수정**: `useStreamingPipeline`에서 `editor.save()` race condition — onNodeEvent(SSE 처리 중) vs handleStreamOutcome(SSE 종료 후) 타이밍 불일치로 빈 씬 PUT. autoSave(Zustand SSOT) 경로로 전환
- **03-16 TTS 파이프라인 일원화 완료**: Sprint A~D — `generate_tts_audio()` SSOT 코어, preview/prebuild/render 3경로 통합, tts_asset_id 자동 무효화, prebuild 자동 삽입, scene_processing.py 슬림화(645→295줄). 테스트 51개 PASS
- **03-16 Phase 33 완료**: Sprint A~E 구현 (22/22) — E-2 배치 Gemini 호출 병합 + validate-batch API + 테스트 33개
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
| 32 | Auto Run Pipeline Hardening | Stage 루프 버그, TTS 단계 추가, Resume 연결, Preflight 정확성, 코드 품질. 17/17 | [아카이브](../99_archive/archive/ROADMAP_PHASE_32_33.md) · [명세](FEATURES/AUTO_RUN_PIPELINE_HARDENING.md) |
| 33 | Hybrid Match Rate | WD14+Gemini Vision 2-Phase, group_name 태그 라우팅, 배치 Gemini 병합, 테스트 33개. 22/22 | [아카이브](../99_archive/archive/ROADMAP_PHASE_32_33.md) · [명세](FEATURES/HYBRID_MATCH_RATE.md) |
| — | TTS 파이프라인 일원화 (Sprint A~D) | `generate_tts_audio()` SSOT, preview/prebuild/render 3경로 통합, tts_asset_id 자동 무효화, prebuild 자동 삽입, scene_processing.py 슬림화 | [설계](../03_engineering/backend/TTS_PIPELINE_UNIFICATION.md) |

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

## Feature Backlog

### ⭐ 최우선 백로그 (P1)

순서대로 진행. ComfyUI 전환이 선행, 캐릭터 일관성 V3가 후행.

| # | 기능 | 설명 | 명세 |
|---|------|------|------|
| 1 | **ComfyUI 마이그레이션** | ForgeUI→ComfyUI 전환 + SD Client 추상화. 실험 검증(4회 54장): CN+IPA 동시투입 실패 → 모듈 분리 필수 확정. Phase A(추상화)→B(ComfyUI 구현)→C(프로덕션+FaceID) | [명세](FEATURES/COMFYUI_MIGRATION.md) |
| 2 | **캐릭터 일관성 V3** | ComfyUI 전환 후 착수. 4-Module 파이프라인(Identity→Context→Refinement→Upscale). FaceID+CN 1-step, 2-Step CN→IPA 폴백, 배치 4씬 일괄, 의상 가변, 멀티캐릭터 FaceID 복수 주입 | [명세](FEATURES/CHARACTER_CONSISTENCY_V3.md) |

### Content & Creative

| 기능 | 참조 |
|------|------|
| VEO Clip (Video Generation 통합) | [명세](FEATURES/VEO_CLIP.md) |
| Profile Export/Import (Style Profile 공유) | [명세](FEATURES/PROFILE_EXPORT_IMPORT.md) |
| Storyboard Version History | — |
| ~~IP-Adapter 캐릭터 유사도 고도화~~ | **Phase 30으로 승격** — [V1 명세](FEATURES/CHARACTER_CONSISTENCY.md) · [V2 명세](FEATURES/CHARACTER_CONSISTENCY_V2.md) |
| 캐릭터 LoRA 학습 파이프라인 | LoRA 트레이닝용 레퍼런스 9세트 생성 + 학습 자동화 (우선순위 낮음) |
| ~~SoVITS TTS 품질 고도화~~ | **보류** — SoVITS(합성음 ref_audio 복제)는 품질 한계 확인. Qwen3 직접 생성이 우수. Sprint A(파라미터 전달) 완료, Sprint B 보류 |
| **Qwen3 씬 TTS 일관성 개선** | Qwen3를 씬 TTS 기본 엔진으로 전환 + `TTS_VOICE_CONSISTENCY_MODE=true`(동일 preset prompt + 고정 seed → 목소리 일관성). SoVITS는 실제 녹음 ref_audio 확보 시 재검토 |

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
| ~~Phase 34: GPU 순차 독점 실행 & BGM 고도화~~ | **드롭** — ComfyUI 전환으로 GPU 관리 방식 자체가 변경될 예정. Forge 전용 `forge_control.py` 구현이 무의미해짐. BGM(ACE-Step) 고도화는 별도 항목으로 재검토 |
| ~~**LangFuse Prompt Management 전체 이전**~~ | **완료** — 28개 프롬프트 chat 타입(system/user 분리). `prompt_partials.py` 파셜 Python 전환, `_partials/` 삭제. 29개 테스트 |
| **LangFuse Prompt Ops 2차 개선** (P2) | Sprint 1: A/B 테스트(label 분기, ScriptState 전파, ~120줄) → Sprint 2: Evaluation(자동 스코어링 5종, trace_id 보존, ~200줄+마이그레이션) → Sprint 3: Dataset(골든 16케이스, 노드 격리 회귀, ~250줄) → Sprint 4: 비-Agent 확장(3개 프롬프트, ~100줄). 이원화 해소: LLM 지표=LangFuse SSOT, 이미지/도메인=DB SSOT. DoD 8항목, 테스트 ~30개. [명세](FEATURES/LANGFUSE_PROMPT_OPS.md) |
| **LLM Provider 추상화 Phase A~E 완료** | [설계](../03_engineering/backend/LLM_PROVIDER_ABSTRACTION.md) — `services/llm/` 패키지 구축, `google.genai` 직결 제거, trace + PROHIBITED fallback 중복 해소. Phase F(OllamaProvider)는 아래 LiteLLM 항목으로 대체 예정 |
| **LiteLLM SDK 도입 (Phase F 대체)** | Gemini 외 두 번째 Provider 실제 도입 시점에 착수. `GeminiProvider` 내부를 LiteLLM 호출로 교체 → 100+ Provider 지원, 폴백/재시도 내장, `OllamaProvider` 직접 구현 불필요. 트레이스 중복 방지를 위해 LiteLLM 자동 LangFuse 콜백 비활성화 + 기존 `trace_llm_call()` 유지 필수. OSS LLMOps Stack(LangGraph + LangFuse + LiteLLM) 표준 조합 완성. **착수 조건**: Ollama/Claude 등 두 번째 Provider 실제 사용 확정 시 |
| PipelineControl 커스텀 (노드 on/off) + 분산 큐 (Celery/Redis) | Phase 9-4 잔여 |
| 배치 렌더링 + 큐 (그룹 일괄 렌더, WebSocket 진행률) | [명세](FEATURES/PROJECT_GROUP.md) §3-3 |
| 브랜딩 시스템 (로고/워터마크, 인트로/아웃트로, 플랫폼별 출력) | [명세](FEATURES/PROJECT_GROUP.md) §3-3 |
| 분석 대시보드 (Match Rate 추이, 프로젝트 간 비교) | [명세](FEATURES/PROJECT_GROUP.md) §3-3 |
| **파이프라인 이상 탐지 자동화** | 시스템 상태 통합 health API, 파이프라인 완료 시 자동 검증 (speaker 배분, TTS 실패, 이미지 미생성), LangFuse 이상 탐지 (노드 실패율/소요시간), GPU VRAM 모니터링 |
| ~~SSOT 위반 정리 (P1~P3, 49건)~~ | **P1+P2 완료 (46/49건, 94%)** — Hi-Res 4상수+SAMPLERS+TTS_ENGINE+enable_hr+controlnet weight+해상도 6곳+image_defaults+pipeline_metadata. 잔여 P3 3건(CATEGORY_DESCRIPTIONS, 주석 검증)은 리스크 없어 보류 |
| ~~Phase 35: GPT-SoVITS v2 TTS 전환~~ | **완료** — SoVITS(:9880) + Qwen3(보이스디자인 on-demand) + MusicGen(CPU). GPU 전환은 cu128 대기 |
| **클라우드 TTS/BGM 전환** | Replicate(현재 모델 클라우드 실행) 또는 ElevenLabs/Suno. GPU 경합 완전 해소, 비용 발생 |
| **씬 단위 순차 생성** | IMAGE→TTS를 씬별로 처리 (현재: 전체 IMAGE→전체 TTS). GPU 순차 독점 자연 해결 + 즉시 프리뷰 |
| ~~ComfyUI 마이그레이션~~ | **⭐ 최우선 백로그로 이동** — [명세](FEATURES/COMFYUI_MIGRATION.md) |
| ~~캐릭터 일관성 V3~~ | **⭐ 최우선 백로그로 이동** — [명세](FEATURES/CHARACTER_CONSISTENCY_V3.md) |
