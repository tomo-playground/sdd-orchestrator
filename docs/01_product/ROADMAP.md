# Shorts Producer — Master Roadmap

**원칙**: 안정성 → 리팩토링 → 안정성 → 신규 개발 사이클. 영상 품질 100% 일관성(Zero Variance) 유지.

---

## 현재 상태 (2026-03-03)

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
| **Phase 26 (Script 협업형 UX)** | **P0+P1 완료** — 스트리밍 메시지 + 3단계 모드 + Plan 검토 + 대화형 씬 수정 |
| **Character-Group 소유권 개편** | **Phase 1-4 전체 완료** — DB 마이그레이션, GroupStep 위저드, 편집 시리즈 변경, 목록 그룹화, 캐릭터 복제 |
| 테스트 | Backend 3,095 + Frontend 543 + E2E 36 = **총 3,674개** |

### 최근 작업

- **캐릭터 스타일 일관성 + 포즈 다양성 구조 개선** (03-03): 스토리보드 1063 분석 기반 3가지 문제 해결. ① Cinematographer 태그 계층화 — `_load_single_character_tags()` flat list → `{identity, appearance, lora_triggers, action_hints}` dict, 템플릿 `NEVER modify` / `ALWAYS include` 디렉티브로 LLM의 외모 태그 임의 변형 방지. `action_hints`(Layer 8: pose/action/gesture)를 "Preferred actions" 레이어로 전달하여 캐릭터 기본 동작 누락 방지. ② IP-Adapter weight 포즈 테이블 제거 — 비정면 포즈 억제 요인(back=0.0~0.2) 해소, Cinematographer에게 null 생성 지시, `normalize_ip_adapter_weights(db=)`로 캐릭터 DB 기본값 통일(Narrator=0.0, DB 세션 재사용). ③ Finalize 교정 로직 3종 추가 — `filter_style_modifiers()` 10종 스타일 수식어 자동 제거(StyleProfile 영역 침범 방지), `diversify_gazes()` emotion→gaze 매핑(23개 emotion, looking_at_viewer >50% 교정, 연속 방지). LoRA N+1 쿼리→IN절 배치 조회 개선. finalize_node DB 세션 단일화. 테스트 21개 추가(filter 8+normalize 6+gaze 7). 코드 리뷰 2회 PASS.
- **TTS 음성 자연스러움 복원 + 마지막 짤림 수정** (03-02): ① Voice Design Gemini 복원 — `ccc765b`(시드 결정론화)에서 프리셋 존재 시 Gemini context-aware voice design이 비활성화되어 단순 문자열 연결(`"base, happy"`)만 사용하던 문제 수정. `generate_context_aware_voice_prompt(script, context, base_prompt=preset)` 호출 복원. seed는 프리셋 기반 고정 유지(같은 목소리), voice_design만 씬별 Gemini 변형(자연스러운 톤 변화). Gemini 실패 시 단순 연결 fallback. ② TTS 마지막 씬 짤림 수정 — `calculate_scene_durations()`에서 `adelay`가 모든 씬에 `transition_dur`만큼 오디오 시작을 미루는데 duration 계산에서 누락. 마지막 씬 유효 패딩 0.3s→0.8s 전체 보존. ③ LoRA 카드 컴팩트화 — 프리뷰 이미지 없는 회색 영역(`aspect-[3/2]`) 제거, 이름+배지+트리거+weight+버튼만 남긴 컴팩트 카드. 방어 테스트 4개 추가(adelay 보상, 긴 TTS, tail_padding, 유효 패딩 검증). 총 24 passed.
- **Character-Group 소유권 Phase 3-4** (03-02): 편집 페이지 시리즈 변경 + 목록 그룹화 + 캐릭터 복제. ① Backend — `POST /characters/{id}/duplicate` API(schemas 2개+crud `duplicate_character()`+라우터), 필드/태그 복사, LoRA/프리뷰 선택 복사, 409 이름 충돌 처리. 테스트 5개(success/conflict/not_found/tags/loras). ② 편집 페이지 — BasicInfoSection 시리즈 `<select>` 드롭다운(읽기전용 배지→편집 가능), 화풍 읽기전용 derived state, `handleGroupChange`+isDirty group_id 비교, save payload group_id 포함. ③ DuplicateDialog 신규 — 대상 시리즈/새 이름/LoRA·프리뷰 체크박스, 409 전용 에러 처리, 성공 시 새 캐릭터 페이지로 이동. ④ 목록 페이지 — CharacterGroupSection(접기/펼치기+시리즈명+화풍배지+캐릭터수+추가 버튼), `charactersByGroup` useMemo, 검색/필터 시 플랫 그리드 폴백. ⑤ GroupStep — 각 카드에 소속 캐릭터 수 표시. 코드 리뷰 수정 4건(enriched loras raw 복사, character mutate→derived state, button>a 시맨틱 수정, groups 빈 배열 fallback). [설계](../02_design/CHARACTER_GROUP_OWNERSHIP_UI.md)
- **Character-Group 소유권 Phase 1-2** (03-02): `character.style_profile_id` 제거 → `character.group_id` NOT NULL FK(`ondelete=RESTRICT`). Group이 화풍(StyleProfile)의 유일한 SSOT. ① Alembic 2-Step 마이그레이션 — nullable 추가→데이터 매핑(13명 5그룹)→orphan 검증→NOT NULL 제약→style_profile_id DROP. ② Backend 서비스 전환 — crud.py joinedload 2-hop(`Character.group.style_profile`), preview.py/controlnet.py `resolve_style_context_from_group(group_id)` 직접 호출, generation_prompt.py joinedload 추가. ③ Agent 4곳 단순화 — `valid_style_profile_ids`/`_load_all_characters` 제거. ④ Frontend — StyleStep→GroupStep(시리즈 선택+baseModel resolve), CharacterFull.style_profile_id dead field 제거, useStyleTab groupStyleMap 간접 집계, CharacterWizard URL param baseModel resolve. ⑤ 스키마 — CharacterBase/Update `group_id`, CharacterResponse `group_name`, SDModelBrief `base_model`. ⑥ group_id 존재 검증(create/update_character). 코드 리뷰 2회(Backend PASS, Frontend BLOCKER 1+WARNING 2 수정). ~120줄 삭제, ~20줄 추가. [설계](../02_design/CHARACTER_GROUP_OWNERSHIP_UI.md)
- **Service vs Admin API 분리 리팩토링** (03-02): 서비스 화면에서 어드민 API를 직접 호출하던 19개 엔드포인트를 기능 기반으로 재분류하여 `/api/v1`으로 이동. ① characters.py 9개(CRUD/프리뷰/레퍼런스), ② prompt.py 4개(번역/편집/태그검증), ③ controlnet.py 2개(IP-Adapter 레퍼런스 조회/이미지), ④ youtube.py 4개(OAuth/credentials). Frontend 12개 파일에서 `ADMIN_API_BASE`→`API_BASE` 변경. CLAUDE.md에 분리 기준 섹션 추가.
- **Gemini Client Shutdown 에러 수정** (03-02): `main.py` lifespan shutdown에 `gemini_client.aio.aclose()` 추가. 전역 싱글톤 `genai.Client` 내부 httpx 연결이 event loop 종료 후 GC 정리 시 `RuntimeError: Event loop is closed` 발생하던 문제 해결. 기존 `close_store()`/`close_checkpointer()` 패턴과 동일.
- **Prompt 3-Tier 소유권 계층 구조** (03-02): 12-Layer 시스템에 Tier 소유권 규칙 도입. ① `LAYER_OWNERS` 상수(config_prompt.py) — Tier 1(StyleProfile): L0/L11, Tier 2(Character): L1~L6, Tier 3(Scene): L7~L10. ② Quality 태그 L0 직접 주입 — `compose_for_character(quality_tags=)` + `apply_style_profile_to_prompt(skip_quality=True)`로 이중 주입 방지. ③ `_collect_character_tags()` 중복 제거 — DB 태그/custom_base_prompt 동일 name skip, 동일 group은 custom 우선(override). 테스트 7개 추가, 기존 190개 전체 PASS. [명세](FEATURES/PROMPT_TIER_HIERARCHY.md)
- **Realistic 배경 품질 + 프롬프트 방어 강화** (03-02): ① Realistic 배경 생성 품질 개선 — `_generate_background_image`에 `_adjust_parameters()` 적용(StyleProfile steps/cfg/sampler/Hi-Res), default_positive → 포토그래피 태그(`RAW photo, soft ambient lighting, muted tones, 35mm film`), Civitai 권장 negative(deformed iris/pupils, semi-realistic) + UnrealisticDream 임베딩 교체. ② Style Conflict Filter — `_tag_base_key()`로 가중치 토큰`(anime:1.3)` 필터링 수정, 템플릿 Realistic 금지 태그 명시. ③ Negative Prompt 3-레이어 원칙 정립 — StyleProfile=품질/화풍, Character=캐릭터 특화, `normalize_negative_prompt()` 가중치 우선 dedup, 전체 13개 캐릭터 custom_negative_prompt 정리. ④ `_ensure_framing_tag()` — standing+framing 없을 때 full_body 자동 삽입(4개 compose 메서드). ⑤ 캐릭터 base_prompt 수정 — 수빈/지호 Gemini 안전 위반 표현 제거(10 year old→chibi tags), 하나/소라 null→기본 설명 추가. ⑥ Makoto Shinkai StyleProfile 수정 — positive 괄호 그룹 버그, negative embedding 텍스트 중복 제거. ⑦ Code Review P1 fixes — `Any` 반환 타입, None 가드, token-exact 매칭, `_SKIP_ENV_REF_TAGS` 모듈 상수. PROMPT_SPEC_V2.md 섹션 11 대폭 보강.
- **TTS 시드 결정론화 + Narrator 옵션 스피커** (03-01): ① Video 삭제 404 버그(`ADMIN_API_BASE`→`API_BASE`) 수정. ② TTS 시드 불일치 근본 수정 — `hash()` → `hashlib.sha256`, `TTS_DEFAULT_SEED=42` 상수화, `_resolve_voice_preset_id` preset bypass 제거, `_get_voice_design_for_scene` 우선순위 역전(preset 항상 우선). ③ Narrator 옵션 스피커 — Monologue/Dialogue/Confession 전 구조에서 Narrator 선택적 허용, `_VALID_SPEAKERS` 모듈 상수, creative_qc+review+revise 검증/auto-fix 업데이트, 템플릿 3개, tts_designer Narrator 컨텍스트 로딩. 테스트 12개 추가.
- **QA 리그레션 테스트 + 커버리지 확장** (03-01): Agent Team(backend-qa+frontend-qa+e2e-qa) 병렬 실행. 신규 테스트 246개(Backend 108+Frontend 105+E2E 33), stale test 44건 수정(Backend 8+VRT/E2E 36), Frontend 커버리지 55.6%→64.4%(+8.8%p). 런타임 버그 0건. [상세](../03_engineering/testing/BUG_REPORT.md)
- **LoRA/프롬프트 안정화 + Debug Payload 표준화** (03-01): Shinkai StyleProfile LoRA 수정 3건(random trigger word→결정적 선택, 가중치 cap 중복 로직→공통 헬퍼 추출, 배경 억제 negative 수정), debug_payload `{request, actual}` 2레벨 구조 표준화(SSE+Sync 통일), seed 필드 추가(schema+frontend), `filter_prompt_tokens()` NULL tag_alias 방어, TRANSIENT_KEYS 캐릭터 필드 추가, SSE timeout 감지 강화. 10파일, 코드 리뷰 2회.
- **Phase 26: Script 협업형 UX** (03-01): P0+P1 완료. P0: director_plan_gate 노드 추가(19노드), interaction_mode 3단계, PipelineStepCard·PlanReviewCard. P1: 생성 후 대화형 씬 수정 — `POST /scripts/edit-scenes` (Gemini 단일 호출), SceneEditDiffCard(Before/After diff), Accept/Reject, 편집 모드 ChatInput. Backend 4파일 + Frontend 7파일. [명세](FEATURES/SCRIPT_COLLABORATIVE_UX.md)
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
| IP-Adapter 캐릭터 유사도 고도화 (SD1.5 완료, SDXL 보류 — GPU 한계) | [명세](FEATURES/CHARACTER_CONSISTENCY.md) |
| 캐릭터 레퍼런스 9세트 프롬프트 생성 + 품질 체크 | 캐릭터 생성 시 포즈/표정/앵글 조합으로 9세트 레퍼런스 프롬프트를 생성하고, WD14 등으로 캐릭터 특징 반영 여부를 자동 검증. 현재는 단일 프롬프트+검증 없음 |

### Intelligence & Automation

| 기능 | 참조 |
|------|------|
| Tag Intelligence (채널별 태그 정책 + 데이터 기반 추천) | [명세](FEATURES/PROJECT_GROUP.md) §3-1 |
| Series Intelligence (에피소드 연결 + 성공 패턴 학습) | [명세](FEATURES/PROJECT_GROUP.md) §3-2 |
| LoRA Calibration Automation | — |

### UX & Workflow

| 기능 | 참조 |
|------|------|
| YouTube Upload Phase 2~3 (Quota 대시보드, 업로드 큐, 예약 업로드) | [명세](FEATURES/YOUTUBE_UPLOAD.md) §Phase 2~3 |
| ~~Express 모드 재검토~~ | **Phase 25에서 해결** — Director 자율 실행으로 대체. 프리셋 제거 완료 |
| ~~Script 생성 후 대화형 수정 루프 (씬 부분 재생성)~~ | **Phase 26 P1에서 완료** — edit-scenes API + SceneEditDiffCard |
| Script Canvas 분할 뷰 (좌 채팅 + 우 씬 프리뷰) | [명세](FEATURES/SCRIPT_COLLABORATIVE_UX.md) §P2 |

### Infrastructure & Scale

| 기능 | 참조 |
|------|------|
| PipelineControl 커스텀 (노드 on/off) + 분산 큐 (Celery/Redis) | Phase 9-4 잔여 |
| 배치 렌더링 + 큐 (그룹 일괄 렌더, WebSocket 진행률) | [명세](FEATURES/PROJECT_GROUP.md) §3-3 |
| 브랜딩 시스템 (로고/워터마크, 인트로/아웃트로, 플랫폼별 출력) | [명세](FEATURES/PROJECT_GROUP.md) §3-3 |
| 분석 대시보드 (Match Rate 추이, 프로젝트 간 비교) | [명세](FEATURES/PROJECT_GROUP.md) §3-3 |
