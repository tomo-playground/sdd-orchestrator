# Phase 32~33 Archive

> 아카이브 일자: 2026-03-16

---

## Phase 32: Auto Run Pipeline Hardening (17/17 완료)

**목표**: Auto Run(Autopilot) 핵심 버그 수정 + TTS 단계 추가 + Resume 기능 연결
**명세**: [FEATURES/AUTO_RUN_PIPELINE_HARDENING.md](../../01_product/FEATURES/AUTO_RUN_PIPELINE_HARDENING.md)

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

## Phase 33: Hybrid Match Rate — WD14 + Gemini Vision (22/22 완료)

**목표**: 하드코딩(`WD14_UNMATCHABLE_TAGS`) 제거, `group_name` 기반 태그 라우팅으로 100% 커버리지 매치레이트 구현
**명세**: [FEATURES/HYBRID_MATCH_RATE.md](../../01_product/FEATURES/HYBRID_MATCH_RATE.md)

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
- [x] E-2: 배치 평가 시 Gemini 호출 병합 — `batch_apply_gemini_evaluation()` + `/scene/validate-batch` API + 이미지 해시 기반 중복 제거
- [x] E-3: 단위 테스트 18개 (classify_prompt_tokens 6 + _is_skippable_tag 3 + apply_gemini_evaluation 6 + _update_db_match_rate 4 + _parse_gemini_json_array 5)
- [x] E-4: compare_prompt_to_tags only_tokens 테스트 2개 + _update_db_match_rate evaluation_details 테스트 1개 — 총 26개
