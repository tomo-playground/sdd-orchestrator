# SP-062 상세 설계 (How)

## 개요
Finalize 노드에 image_prompt/context_tags 코드 레벨(L2) 검증을 추가한다. Cinematographer가 생성한 프롬프트/태그의 유효성을 코드로 강제하여, Gemini가 프롬프트 지시(L1)를 무시해도 안전망을 제공한다.

---

## DoD 1: 금지 태그 필터

### 구현 방법
- `config.py`에 `PROHIBITED_IMAGE_TAGS: frozenset[str]`을 정의한다.
- Cinematographer 프롬프트 Rule 1의 FORBIDDEN 목록 기반:
  - 조합형 비표준 태그: `cinematic_shadows`, `computer_monitor`, `glowing_screen`, `dark_room`, `high_contrast_shadow`
  - 감정 형용사(비 Danbooru): `confident`, `satisfied`, `anxious`, `tormented`, `resigned`, `paranoid`
  - 복합 expression: `happy_smile`, `sly_smile`, `pensive_expression`, `puzzled_expression`
  - 성별 태그(시스템 자동 주입): `female`, `male`
  - 제로 포스트 태그: `bishoujo`, `daylight`, `extreme_close-up`
  - 기타 비표준: `medium_shot`, `rim_light`, `dramatic_lighting`, `cinematic_lighting`, `warm_lighting`, `cold_lighting` (Rule 12 INVALID 목록)
- `finalize.py`에 `_filter_prohibited_tags(scenes: list[dict]) -> None` 함수를 추가한다.
- 각 씬의 `image_prompt`를 `,` 분할하여 토큰별로 `_strip_token_weight()` 후 `PROHIBITED_IMAGE_TAGS`에 해당하면 제거한다.
- 제거된 태그는 `logger.warning("[Finalize] Prohibited tags removed: %s", removed_list)` 로 기록한다.
- 실행 위치: `finalize_node()` 그룹 3.5 (`_validate_cross_field_consistency` 이전)에 배치. `_rebuild_image_prompt_from_context_tags()` 전에 실행해야 재조립에 금지 태그가 포함되지 않는다.

### 동작 정의
- input: `scenes` (list[dict]), 각 씬에 `image_prompt` 문자열 포함
- output: 금지 태그가 제거된 `image_prompt`로 in-place 업데이트
- 빈 프롬프트(`""` 또는 None)는 건너뜀
- weight 구문 `(tag:1.15)` 안의 태그도 검출 (`_strip_token_weight()` 활용)

### 엣지 케이스
- LoRA 태그 `<lora:xxx>` 형식은 금지 태그 검사에서 제외 (이미 `_strip_token_weight`가 빈 문자열 반환하므로 자연스럽게 skip)
- 금지 태그와 부분 일치하는 유효 태그 보호: `medium_shot` 삭제 시 `shot`은 보호됨 (토큰 단위 매칭이므로 문제 없음)
- `high_contrast` vs `high_contrast_shadow`: `high_contrast`는 유효(Danbooru 존재), `high_contrast_shadow`만 금지. 정확 일치 비교로 오탈 방지

### 영향 범위
- `config.py`: 상수 추가 (1줄)
- `finalize.py`: 함수 추가 + `finalize_node()` 호출 1줄 추가

### 테스트 전략
- `test_filter_prohibited_tags_removes_known_forbidden`: 금지 태그 포함 프롬프트 → 제거 확인
- `test_filter_prohibited_tags_preserves_valid`: 유효 태그만 있는 프롬프트 → 변경 없음
- `test_filter_prohibited_tags_weighted`: `(cinematic_shadows:1.2)` → 제거 확인
- `test_filter_prohibited_tags_empty_prompt`: 빈 프롬프트 → 에러 없이 skip
- `test_filter_prohibited_tags_similar_valid_preserved`: `high_contrast` 유지, `high_contrast_shadow` 제거

### Out of Scope
- 금지 태그 DB 관리 (현재 config.py 상수로 충분)
- Cinematographer 프롬프트 자체 수정 (L1 레이어)

---

## DoD 2: Danbooru 형식 정규화

### 구현 방법
- `finalize.py`에 `_normalize_danbooru_format(scenes: list[dict]) -> None` 함수를 추가한다.
- 각 씬의 `image_prompt` 토큰을 순회하며:
  1. LoRA 태그 (`<lora:...>`) 건너뜀
  2. 하이픈 태그 (`close-up`, `half-closed_eyes` 등) 건너뜀 — Danbooru 표준에 하이픈이 포함된 태그는 그대로 유지
  3. LoRA 트리거 워드 건너뜀 — `LoRATriggerCache.get_lora_name(token)`으로 조회, 트리거이면 원본 유지
  4. 나머지: 공백 → 언더바 변환 (`token.replace(" ", "_")`)
- 실행 위치: `finalize_node()` 그룹 3.5에서 `_filter_prohibited_tags()` 직후, `_validate_cross_field_consistency()` 이전.

### 동작 정의
- input: `scenes` (list[dict])
- output: 공백이 언더바로 변환된 `image_prompt`로 in-place 업데이트
- weight 구문 보존: `(brown hair:1.2)` → `(brown_hair:1.2)` (괄호 안의 태그만 변환)

### 엣지 케이스
- 이미 언더바 형식인 태그: 변환 불필요, 무해하게 통과
- 혼합 형식 (`brown_hair, blue eyes, close-up`): 각 토큰 독립 처리
- LoRA 트리거 `flat color` → 원본 유지 (LoRATriggerCache 조회)
- weight 구문 내부: `(blue eyes:1.3)` → 괄호+weight를 분리하여 내부 태그만 변환 → `(blue_eyes:1.3)` 재조립
- 하이픈 판정: 토큰에 `-`가 포함되면 Danbooru 하이픈 태그로 간주하고 skip (공백→언더바 변환만 하지 않음이 아니라, 하이픈 자체는 유지하되 공백은 변환). 실제로는 `close-up`처럼 하이픈이 있는 토큰도 공백이 있을 수 있으므로, 공백→언더바 변환은 수행하되 하이픈은 건드리지 않는다.

### 영향 범위
- `finalize.py`: 함수 추가 + 호출 1줄

### 테스트 전략
- `test_normalize_spaces_to_underscores`: `"blue eyes, brown hair"` → `"blue_eyes, brown_hair"`
- `test_normalize_preserves_hyphens`: `"close-up, half-closed_eyes"` → 변경 없음
- `test_normalize_preserves_lora_tags`: `"<lora:style_xl:0.8>"` → 변경 없음
- `test_normalize_preserves_lora_triggers`: LoRA 트리거 `flat color` → 원본 유지 (LoRATriggerCache mock 사용)
- `test_normalize_weight_syntax`: `"(blue eyes:1.3)"` → `"(blue_eyes:1.3)"`

### Out of Scope
- context_tags 내부 값의 형식 정규화 (context_tags는 이미 `_context_tag_utils.py`의 alias/카테고리 검증에서 처리됨)

---

## DoD 3: context_tags 유효성 검증

### 구현 방법

#### 3a. emotion 유효성
- `_context_tag_utils.py`에 이미 `VALID_EMOTIONS` frozenset과 `_normalize_emotion()` 함수가 존재한다.
- `finalize.py`에 `_validate_context_tag_values(scenes: list[dict]) -> None` 함수를 추가한다.
- 각 씬의 `context_tags.emotion`을 검증:
  1. `_normalize_emotion(raw)`을 호출하여 정규화 시도
  2. 정규화 결과가 `VALID_EMOTIONS`에 있으면 교체
  3. 없으면 `"calm"` (기본값)으로 대체 + WARNING 로그
- 리스트 형태(`["happy", "sad"]`)는 `_coerce_str()`로 첫 번째 값 추출 후 검증

#### 3b. camera 유효성
- `CATEGORY_PATTERNS["camera"]`에 유효한 카메라 태그 목록이 이미 정의되어 있다.
- `_validate_context_tag_values()` 내에서:
  1. `context_tags.camera`가 유효 카메라 셋에 없으면
  2. 공백→언더바 정규화 후 재검증
  3. 여전히 무효하면 `"cowboy_shot"` (기본값)으로 대체 + WARNING 로그

#### 3c. gaze 유효성
- `CATEGORY_PATTERNS["gaze"]`에 유효한 시선 태그 목록이 이미 정의되어 있다.
- `_validate_context_tag_values()` 내에서:
  1. `context_tags.gaze`가 유효 시선 셋에 없으면
  2. `_GAZE_ALIASES` 매핑 시도 (이미 `_context_tag_utils.py`에 존재)
  3. alias 매핑 성공하면 교체, 실패하면 `"looking_at_viewer"` (기본값)으로 대체 + WARNING 로그
- 기존 `validate_context_tag_categories()`와의 관계: 기존 함수는 expression/gaze/pose의 카테고리 재분류에 집중. 새 함수는 emotion/camera/gaze의 유효값 대체(fallback)에 집중. 실행 순서: 기존 `validate_context_tag_categories()` → 새 `_validate_context_tag_values()`.

### 동작 정의
- input: `scenes` (list[dict])
- output: 무효한 context_tags 값이 유효한 기본값으로 in-place 대체됨
- Narrator 씬도 camera는 검증 대상 (Narrator도 카메라 앵글 사용)
- Narrator 씬의 emotion/gaze는 없어도 무방 (존재 시에만 검증)

### 엣지 케이스
- `context_tags`가 None인 씬: skip (이미 `_inject_default_context_tags`에서 처리)
- 한국어 emotion (`"기쁨"`, `"슬픔"`): `_normalize_emotion()` 내부의 한국어 별칭 매핑으로 처리
- 복합 emotion (`"lonely_expression"`): `_normalize_emotion()`의 부분 매칭으로 `"lonely"` 추출
- camera가 리스트(`["close-up", "from_above"]`): `_coerce_str()`로 첫 번째 값 추출 후 검증
- gaze가 `_GAZE_ALIASES`에 있는 비표준 값(`"looking_at_another"`): alias로 교체

### 영향 범위
- `finalize.py`: 함수 추가 + `finalize_node()` 그룹 2 끝에 호출 추가
- `_context_tag_utils.py`: `VALID_EMOTIONS`, `_normalize_emotion` import (이미 존재하는 코드 재활용)

### 테스트 전략
- `test_emotion_valid_unchanged`: `"happy"` → 그대로 유지
- `test_emotion_korean_normalized`: `"기쁨"` → `"happy"`
- `test_emotion_invalid_fallback`: `"perplexed"` → `"calm"`
- `test_emotion_compound_normalized`: `"lonely_expression"` → `"lonely"`
- `test_camera_valid_unchanged`: `"cowboy_shot"` → 유지
- `test_camera_space_normalized`: `"cowboy shot"` → `"cowboy_shot"`
- `test_camera_invalid_fallback`: `"medium_shot"` → `"cowboy_shot"`
- `test_gaze_valid_unchanged`: `"looking_down"` → 유지
- `test_gaze_alias_applied`: `"looking_at_another"` → `"looking_to_the_side"`
- `test_gaze_invalid_fallback`: `"staring_into_space"` → `"looking_at_viewer"`
- `test_narrator_camera_validated`: Narrator 씬도 camera 검증됨
- `test_no_context_tags_skip`: context_tags 없는 씬 → 에러 없이 skip

### Out of Scope
- pose 유효성 검증: 이미 `validate_context_tag_categories()`와 `validate_controlnet_poses()`에서 처리
- expression 유효성: 이미 `validate_context_tag_categories()`에서 처리 + emotion→expression 자동 파생

---

## DoD 4: 재조립 후 sanity check

### 구현 방법
- `finalize.py`에 `_validate_final_image_prompt(scenes: list[dict]) -> None` 함수를 추가한다.
- `_rebuild_image_prompt_from_context_tags()` 직후에 실행한다.
- 검증 및 자동 정리 항목:
  1. **빈 프롬프트**: `image_prompt`가 빈 문자열이면 WARNING 로그 (Narrator는 `"no_humans, scenery"` fallback 주입)
  2. **이중 쉼표**: `", ,"` 또는 연속 공백 쉼표 → `re.sub(r",\s*,+", ",", prompt)` + 선행/후행 쉼표 strip
  3. **태그 50개 초과**: `,` 기준 토큰 수 > 50이면 WARNING 로그 + 50개까지만 유지 (뒤에서 절단)
  4. **weight 문법 오류**: 열린 괄호 `(`와 닫힌 괄호 `)`의 수가 불일치하면 짝 없는 괄호 제거. `(tag:)` 또는 `(:1.2)` 형태의 불완전 weight 구문 제거.

### 동작 정의
- input: `scenes` (list[dict])
- output: 정리된 `image_prompt`로 in-place 업데이트
- 모든 검증은 비파괴적: 프롬프트를 삭제하지 않고, 문제 부분만 정리
- 실행 위치: `finalize_node()` 그룹 3.5에서 `_rebuild_image_prompt_from_context_tags()` 직후, `_apply_tag_aliases()` 재적용 직전

### 엣지 케이스
- 재조립 skip된 씬 (구 스토리보드, context_tags 비어있음): image_prompt 원본이 남아있으므로 sanity check 대상
- Narrator 씬에 빈 프롬프트: `"no_humans, scenery"` fallback 주입
- weight `(tag:1.2)` 안의 쉼표: SD weight 구문 내부에는 쉼표가 없으므로 문제 없음
- 괄호 중첩 `((tag:1.2):1.3)`: SD 중첩 weight는 유효하므로 쌍이 맞으면 유지

### 영향 범위
- `finalize.py`: 함수 추가 + 호출 1줄

### 테스트 전략
- `test_empty_prompt_narrator_fallback`: Narrator 씬 빈 프롬프트 → `"no_humans, scenery"` 주입
- `test_empty_prompt_character_warning`: 캐릭터 씬 빈 프롬프트 → WARNING 로그 (삭제하지 않음)
- `test_double_comma_cleanup`: `"tag_a,, tag_b, , tag_c"` → `"tag_a, tag_b, tag_c"`
- `test_tag_count_over_50_truncated`: 60개 태그 프롬프트 → 50개로 절단
- `test_tag_count_under_50_unchanged`: 30개 태그 → 변경 없음
- `test_unmatched_parenthesis_removed`: `"(tag:1.2, orphan_paren("` → 짝 없는 `(` 제거
- `test_incomplete_weight_removed`: `"(tag:), (:1.2), valid_tag"` → 불완전 구문 제거
- `test_valid_weight_preserved`: `"(tag:1.2), ((emphasis))"` → 변경 없음

### Out of Scope
- 프롬프트 의미적 검증 (태그 간 논리적 일관성) — cross-modal 검증은 향후 별도 태스크
- 태그 중복 제거 — 이미 `normalize_prompt_tokens()`에서 처리

---

## DoD 5: 통합 (기존 테스트 regression 없음 + 린트)

### 구현 방법
- 새 함수들의 `finalize_node()` 내 실행 순서:
  ```
  그룹 2 끝: _validate_context_tag_values()  ← DoD 3
  그룹 3.5:
    _filter_prohibited_tags()                 ← DoD 1
    _normalize_danbooru_format()              ← DoD 2
    _validate_cross_field_consistency()       ← 기존
    _rebuild_image_prompt_from_context_tags() ← 기존
    _validate_final_image_prompt()            ← DoD 4
    _apply_tag_aliases()                      ← 기존 (재적용)
  ```
- 각 새 함수는 try/except로 래핑 (non-fatal, 기존 패턴 준수)
- 테스트 파일: `backend/tests/test_finalize_prompt_validation.py` (신규)

### 동작 정의
- 기존 `finalize_node()` 테스트 전체 통과 확인
- 새 테스트 약 20개 추가
- ruff lint + prettier 통과

### 엣지 케이스
- 함수 실행 순서 의존성: `_filter_prohibited_tags()` → `_normalize_danbooru_format()` → `_rebuild` 순서 필수. 금지 태그 제거 후 형식 정규화, 그 후 재조립이어야 깨끗한 프롬프트 보장.
- context_tags 검증은 그룹 2 끝에 배치해야 함: `_inject_default_context_tags()` 이후여야 기본값이 주입된 상태에서 검증.

### 영향 범위
- `config.py`: `PROHIBITED_IMAGE_TAGS` 상수 1개 추가
- `finalize.py`: 4개 함수 추가 + `finalize_node()` 내 호출 4줄 추가
- `backend/tests/test_finalize_prompt_validation.py`: 신규 테스트 파일
- 변경 파일 총 3개 (제약 5개 이하 충족)

### 테스트 전략
- `pytest backend/tests/test_finalize_*.py` 전체 실행으로 regression 확인
- `ruff check backend/` 통과
- 새 테스트 파일 단독 실행 확인

### Out of Scope
- image_prompt↔script 정합성 (Cross-modal 검증)
- 태그 화이트리스트(전체 Danbooru 태그 DB) 도입

---

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `backend/config.py` | `PROHIBITED_IMAGE_TAGS` frozenset 추가 |
| `backend/services/agent/nodes/finalize.py` | `_filter_prohibited_tags()`, `_normalize_danbooru_format()`, `_validate_context_tag_values()`, `_validate_final_image_prompt()` 4개 함수 추가 + `finalize_node()` 호출 통합 |
| `backend/tests/test_finalize_prompt_validation.py` | 신규: 약 20개 테스트 |

## 미결 질문
없음. 기존 코드에 충분한 인프라(`VALID_EMOTIONS`, `CATEGORY_PATTERNS`, `_normalize_emotion`, `_strip_token_weight`, `LoRATriggerCache`)가 있어 새 로직은 이들을 조합하는 수준이다.
