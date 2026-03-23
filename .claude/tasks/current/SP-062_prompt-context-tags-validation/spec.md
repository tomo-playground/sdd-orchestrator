---
id: SP-062
priority: P1
scope: backend
branch: feat/SP-062-prompt-context-tags-validation
created: 2026-03-23
status: approved
depends_on:
label: feat
---

## 무엇을 (What)
Finalize 노드에 image_prompt/context_tags 코드 레벨(L2) 검증을 추가하여, Cinematographer가 생성한 프롬프트/태그의 유효성을 코드로 강제한다.

## 왜 (Why)
Cinematographer 프롬프트에 15개 규칙이 있지만 전부 L1(프롬프트 지시) — Gemini가 무시하면 안전망이 없다. image_prompt의 금지 태그, 비표준 형식, context_tags의 무효한 값이 SD 이미지 생성까지 그대로 전달되어 실패하거나 엉뚱한 결과를 낳는다. Finalize에서 별칭 적용과 스타일 제거는 하지만, 태그 유효성/형식/충돌 검증은 없다.

## 완료 기준 (DoD)

### 금지 태그 필터

- [ ] config.py에 `PROHIBITED_IMAGE_TAGS` set을 정의한다 (cinematic_shadows, happy_smile, medium_shot, computer_monitor 등 Cinematographer 프롬프트의 FORBIDDEN 목록 기반)
- [ ] Finalize에서 image_prompt 토큰 중 `PROHIBITED_IMAGE_TAGS`에 해당하는 것을 자동 제거하고 로그에 WARNING을 남긴다

### Danbooru 형식 정규화

- [ ] image_prompt의 모든 태그를 언더바 형식으로 정규화한다 (공백→언더바). LoRA 트리거와 하이픈 태그(`close-up`)는 예외 처리한다

### context_tags 유효성 검증

- [ ] `context_tags.emotion`이 config.py `ALLOWED_EMOTIONS` set에 없으면 가장 가까운 값으로 매핑하거나 기본값("calm")으로 대체한다
- [ ] `context_tags.camera`가 유효한 카메라 태그 set에 없으면 WARNING 로그 + 기본값("cowboy_shot") 대체한다
- [ ] `context_tags.gaze`가 유효한 시선 태그 set에 없으면 WARNING 로그 + 기본값("looking_at_viewer") 대체한다

### 재조립 후 sanity check

- [ ] `_rebuild_image_prompt_from_context_tags()` 이후 `_validate_final_image_prompt()`를 실행하여: 빈 프롬프트, 이중 쉼표, 태그 50개 초과, weight 문법 오류를 검출하고 자동 정리한다

### 통합

- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 영향 분석
- 관련 파일: `backend/services/agent/nodes/finalize.py`, `backend/services/agent/nodes/_finalize_validators.py`, `backend/config.py`
- 상호작용: `_rebuild_image_prompt_from_context_tags()`가 context_tags 기반으로 프롬프트 재조립 → 그 직후에 검증 실행
- Finalize 실행 시간 미미하게 증가 (순수 함수, Gemini 호출 없음)

## 제약
- 변경 파일 5개 이하
- image_prompt↔script 정합성 (Cross-modal 검증)은 이 태스크 범위 밖 (향후 별도)
- 태그 화이트리스트(전체 Danbooru 태그 DB)는 도입하지 않음 — 블랙리스트(금지 태그) 방식

## 힌트
- `ALLOWED_EMOTIONS`: Cinematographer 프롬프트 Rule 6의 30개 감정 리스트
- 기존 `_validate_cross_field_consistency()`가 일부 camera↔gaze 충돌 검사 — 이를 확장
- `_QUALITY_TAG_FIXES`, `_CAMERA_GAZE_CONFLICTS` 등 기존 상수 참조
