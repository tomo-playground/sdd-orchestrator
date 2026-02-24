# Phase 8, 14, 16 Archive

Archived: 2026-02-24

---

## Phase 8: Multi-Style Architecture (완료 02-21)

**목표**: Anime, Realistic, 3D 등 다양한 화풍 지원을 위한 유연한 파이프라인 구축.

### Phase 8-0: Realistic Style Quick Fix (완료 2026-02-21)

| # | 항목 | 상태 |
|---|------|------|
| 1 | DEFAULT_SCENE/REFERENCE_NEGATIVE_PROMPT에서 Anime 전용 embedding 제거 | ✅ |
| 2 | Realistic StyleProfile 개선 (negative_embeddings=[], 품질/negative 태그) | ✅ |
| 3 | LoRA `base_model` 필드 추가 (ORM + 마이그레이션 + 스키마) | ✅ |
| 4 | StyleContext에 `sd_model_name`, `sd_model_base` 추가 | ✅ |
| 5 | 이미지 생성 전 Checkpoint 자동 전환 (`_ensure_correct_checkpoint`) | ✅ |
| 6 | Character LoRA 호환성 경고 (base_model 불일치 시 warning) | ✅ |

### Phase 8-1: Multi-Style Full Support (완료 02-21, 8/8)

| # | 항목 | 상태 |
|---|------|------|
| 1 | Style-Character Hierarchy (캐릭터 ↔ 화풍 연결) | ✅ (02-21) |
| 2 | Style Profile UI (Frontend 관리 화면) | ✅ (02-21) |
| 3 | Negative Embedding 스타일별 자동 주입 | ✅ (02-21) |
| 4 | LoRA/Embedding base_model 필터링 + UI 표시 | ✅ (02-21) |
| 5 | 화풍별 생성 파라미터 자동 적용 (steps/cfg/sampler/clip_skip) | ✅ (02-21) |
| 6 | IP-Adapter 모델 자동 선택 (clip_face/faceid) | ✅ (02-21) |
| 7 | 캐릭터 프리뷰 Checkpoint 자동 전환 | ✅ (02-21) |
| 8 | Hi-Res 기본값 자동 적용 (default_enable_hr) | ✅ (02-21) |

---

## Phase 14: ControlNet Pose Pipeline 완성 (완료 02-22)

**목표**: ControlNet 포즈가 실질적으로 작동하도록 파이프라인 갭 해소. Cinematographer → Finalize → auto_populate → ControlNet 전 경로에서 포즈 데이터 누락 방지.

| # | 항목 | 상태 |
|---|------|------|
| 1 | Cinematographer 템플릿 Available Poses 28개 전체 명시 | ✅ (02-22) |
| 2 | Finalize context_tags 누락 시 기본 pose/gaze 주입 | ✅ (02-22) |
| 3 | auto_populate 태그 카테고리 검증 (category mismatch 방지) | ✅ (02-22) |

### Phase 14-A: LLM 하드코딩 제거 (완료 02-22, 3/3)

| # | 항목 | 상태 |
|---|------|------|
| 1 | 씬별 LLM Negative Prompt (`negative_prompt_extra` 필드, Finalize 병합) | ✅ (02-22) |
| 2 | `detect_pose_from_prompt()` 단순화 (synonym 삭제, exact longest-match) | ✅ (02-22) |
| 3 | Environment Consistency 정규화 (`setting`→`environment`, keyword 충돌 삭제) | ✅ (02-22) |

---

## Phase 16: WD14 Smart Validation (완료 02-24)

**목표**: "WD14로 태그를 지우지 말고, WD14로 이미지를 검증하라". WD14가 신뢰 가능한 39개 태그 영역(의류, 성별, 머리, 표정, 포즈)에 집중하여 생성 품질을 검증하고 캐릭터 일관성을 보장한다.

**배경**: WD14 tag_effectiveness 기반 프롬프트 필터링이 프롬프트 품질을 오히려 저하시키는 "death spiral" 문제 발견. WD14는 9,083개 태그 중 ~39개(15%)만 신뢰 가능하게 감지하며, 나머지 85%(구도, 조명, 눈색, 스타일)는 감지 불가.

### Phase 16-0: Effectiveness 필터링 제거 (완료 02-24)

| # | 항목 | 상태 |
|---|------|------|
| 1 | `filter_prompt_tokens()` effectiveness 기반 태그 삭제 제거 | ✅ (02-24) |
| 2 | `_load_processed_tags()` effectiveness 기반 Gemini 태그 선택지 제한 제거 | ✅ (02-24) |
| 3 | 테스트 업데이트 (26개 PASS) | ✅ (02-24) |

### Phase 16-A: Critical Failure Detection (완료 02-24)

| # | 항목 | 상태 |
|---|------|------|
| 1 | `detect_critical_failure()` — 성별 반전/인물 부재/인물수 불일치 감지 | ✅ (02-24) |
| 2 | `validate_scene_image()` 응답에 `critical_failure` 필드 추가 | ✅ (02-24) |
| 3 | Frontend 경고 UI (Critical Failure 시 빨간 배지 + 토스트) | ✅ (02-24) |

### Phase 16-B: Adjusted Match Rate (완료 02-24)

| # | 항목 | 상태 |
|---|------|------|
| 1 | `WD14_DETECTABLE_GROUPS` 상수 정의 (subject, hair_color, clothing 등 14종) | ✅ (02-24) |
| 2 | `compute_adjusted_match_rate()` — 감지 가능 태그만으로 match_rate 재계산 | ✅ (02-24) |
| 3 | API 응답에 `adjusted_match_rate` + `match_rate` 분리 (하위 호환) | ✅ (02-24) |
| 4 | `_increment_tag_effectiveness()` 비감지 그룹 태그 제외 | ✅ (02-24) |

### Phase 16-C: Auto-Regeneration + Identity Ranking (완료 02-24)

| # | 항목 | 상태 |
|---|------|------|
| 1 | Critical Failure 시 seed 변경 자동 재생성 (최대 2회) | ✅ (02-24) |
| 2 | `compute_identity_score()` — 캐릭터 identity 태그 일치도 계산 | ✅ (02-24) |
| 3 | 후보 랭킹: identity_score 1순위 → adjusted_match_rate 2순위 | ✅ (02-24) |

### Phase 16-D: Cross-Scene Consistency (완료 02-24)

> 명세: [CROSS_SCENE_CONSISTENCY.md](../../01_product/FEATURES/CROSS_SCENE_CONSISTENCY.md)

| # | 항목 | 상태 |
|---|------|------|
| 1 | `CharacterSignature` — 캐릭터 시각적 시그니처 추출 + DB 확장 (D-1) | ✅ (02-24) |
| 2 | Drift 알고리즘 — 그룹별 가중치 기반 일관성 점수 (D-2) | ✅ (02-24) |
| 3 | `GET /quality/consistency/{storyboard_id}` API (D-3) | ✅ (02-24) |
| 4 | Frontend ConsistencyPanel + DriftHeatmap (D-4) | ✅ (02-24) |

---

## Pipeline Prompt Quality (SB#469 검수 기반, 완료 02-24)

스토리보드 469 검수에서 발견된 8건 이슈 중 6건 수정, 1건 P2 보류, 1건 기존 설계로 이슈 아님.

| # | 이슈 | 심각도 | 상태 | 수정 내용 |
|---|------|--------|------|----------|
| 1 | `high_quality` 비표준 품질 태그 | CRITICAL | ✅ | `_sanitize_quality_tags()` + `create_style_profiles.py` 소스 정리 |
| 2 | Context→Prompt 미반영 | CRITICAL | 📋 P2 | 설계 의도 — `/compose` API가 이미 병합. UI 표시 개선만 필요 |
| 3 | Context vs Script 감정 불일치 | CRITICAL | ✅ | emotion→expression 파생 (44개 매핑) |
| 4 | `gaze=crying` 카테고리 분류 오류 | CRITICAL | ✅ | `validate_context_tag_categories()` 재분류 |
| 5 | 비표준 mood 태그 | WARNING | ✅ | `validate_context_tag_categories()` mood drop |
| 6 | Camera 앵글 다양성 부족 | WARNING | ✅ | `check_camera_diversity()` 소프트 경고 |
| 7 | LoRA 위치 비일관 | WARNING | — | 12-Layer 순서 보장 (기존 설계, 이슈 아님) |
| 8 | 트리거 워드 누락 | WARNING | ✅ | `LoRAInfo` + scene-triggered/auto-triggered 트리거 주입 |

---

## 최근 작업 (02-20~02-22)

- **Cinematographer → Ken Burns 씬별 연결** (02-22): 감정/서사 기반 Ken Burns 모션 자동 지정. motion.py EMOTION_MOTION_MAP(27감정→프리셋), suggest_ken_burns_preset(). Finalize _validate_ken_burns_presets() 검증+fallback. Cinematographer 템플릿 Rule 15. VideoScene.ken_burns_preset 필드. resolve_scene_preset() 씬별>전역 우선순위. Frontend 전 경로 연결(mapGeminiScenes/mapEventScenes/sync/render). 테스트 22개 추가
- **파이프라인 → Frontend 씬 필드 매핑 갭 수정** (02-22): Finalize `_flatten_tts_designs()` — tts_design dict → voice_design_prompt/head_padding/tail_padding flat fields 분해. `scenes.controlnet_pose` 컬럼 추가 (DB_SCHEMA v3.29). Frontend 전 경로에 5필드 매핑 보강. 11파일 수정
- **DB 정합성 수정: bgm_mode 기본값 + gender_locked 설정 경로** (02-22): `render_presets.bgm_mode` NOT NULL 제약 적용. `LoRAUpdate` 스키마에 `gender_locked` 필드 추가 + Frontend EditLoraModal Gender Lock 드롭다운. DB_SCHEMA v3.28
- **Dead 컬럼 제거** (02-22): `scenes.description` + `creative_traces.diff_summary` DROP. Alembic 마이그레이션
- **Duration 부족 검증 + 자동 보정** (02-22): 목표 45s→실제 33.5s 버그 수정. 3단 방어: Review 검증 + Revise redistribute_durations + Finalize _ensure_minimum_duration. 11개 테스트
- **LLM 하드코딩 제거 3종** (02-22): Phase 14-A. negative_prompt_extra, detect_pose 단순화, Environment 정규화. 10개 테스트
- **Zustand isDirty subscribe + debounce 자동 저장** (02-22): isDirty 변경 감지 → 2초 debounce → persistStoryboard(). 6곳 수동 save 제거. 테스트 6개
- **SSE 이벤트에 controlnet_pose/ip_adapter_reference 전달** (02-22): ImageProgressEvent → Frontend → Zustand 스토어 → DB 자동 저장. 테스트 4개
- **character_actions DB 미저장 수정** (02-22): mapEventScenes/syncToGlobalStore에서 context_tags/character_actions 매핑 누락 수정
- **Safety Filter 에러 Frontend 미표시 수정** (02-22): route_after_revise short-circuit, route_after_finalize 에러 시 explain 스킵. 테스트 5건
- **레거시 mode 필드 완전 제거** (02-22): Quick/Full → skip_stages 전환. 22파일, 테스트 14파일 업데이트
- **Stage-Level Skip 통합 아키텍처** (02-22): skip_stages: list[str] 4단계. _skip_guard.py, 프리셋 재편, Frontend 동적 필터링. 29파일
- **비활성 태그 필터링 + Gemini 안전 필터** (02-22): is_active 필터, deprecated 태그 자동 대체, safety_settings BLOCK_NONE 보완
- **ControlNet Pose Pipeline 완성 + 씬 플래그** (02-22): 포즈 28개 명시, pose/gaze fallback, character_actions 확장, StyleProfile 필드 수정, Hi-Res 동기화
- **Finalize 노드 에러 전파 수정** (02-22): error 필드 무시 → 즉시 에러 반환
- **IP-Adapter 고도화 Phase 1~3 + Seed Anchoring** (02-22): Per-character 오버라이드, 실사 업로드+크롭, 멀티앵글, face tag suppression, 결정론적 seed. 테스트 4파일(888줄)
- **Cinematographer 연출력 강화 + 에이전트 경쟁** (02-22): Writer Plan 브릿지, 시네마틱 규칙 3개, 3 Lens 경쟁, 매트릭스 확장. 13개 테스트
- **StyleProfile별 Hi-Res/생성 파라미터 자동 적용** (02-21): default_enable_hr + default_steps/cfg/sampler/clip_skip. Realistic/Anime 프리셋. DB_SCHEMA v3.24~25
- **FaceID + IP-Adapter 모델 자동 선택** (02-21): faceid control_mode 강화, style_profiles.default_ip_adapter_model. ConsistencyResolver 3단계 우선순위
- **TagClassifier 비동기 + Circuit Breaker** (02-21): Danbooru 호출 BackgroundTasks 전환, 타임아웃 3초, Circuit breaker
- **캐릭터 프리뷰 Checkpoint 전환 + project_id 제거** (02-21): _ensure_correct_checkpoint 호출 누락 수정, 미사용 FK 정리. DB_SCHEMA v3.23
- **Phase 8-1 Style-Character Hierarchy** (02-21): style_profile_id FK, Wizard 화풍 선택, LoRA 호환성 필터, Style Profile UI. Backend 14파일 + Frontend 7파일
- **Phase 8-0 Realistic Style Quick Fix** (02-21): Anime embedding 범용화, LoRA base_model, Checkpoint 자동 전환. 7개 테스트
- **SSE 스트림 에러 수정 + 캐릭터 프리뷰 Gemini 복원** (02-20): CancelledError 핸들링, Enhance/Edit 버튼 복원
- **캐릭터 태그 정비 + Studio Ghibli** (02-20): 8캐릭터 identity/clothing 분리, Civitai 6526 LoRA, Hana/Sora 캐릭터
- **BGM 모드 리팩토링 + Phase 13-A Quick Wins** (02-20): 3-mode→2-mode, Review Gemini 통합, Learn 병렬화. 25개 테스트
- **TTS Speakable Flag + Duration Auto-Calculation** (02-20): speakable 플래그, READING_SPEED SSOT, estimate_reading_duration(). 23개 테스트
- **Phase 11~13 완료** (02-20): Phase 11 정면 편향 해소 14건, Phase 12 Agent Enhancement 26건, Phase 13 Creative Control 23건. [Phase 11 아카이브](ROADMAP_PHASE_11.md) · [Phase 12~13 아카이브](ROADMAP_PHASE_12_13.md)
- **Cinematographer 프롬프트 품질 + 렌더링 품질** (02-14~20): negative_prompt Finalize 주입, characters_tags 전달, 환경 태그 제약, Scene Text 동적 높이/폰트, Safe Zone, 얼굴 감지. 61개 테스트
