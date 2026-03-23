# SP-072 상세 설계: Narrator 씬 지능형 no_humans 판단

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `backend/config_prompt.py` | 수정 | `CROWD_INDICATOR_TAGS` 공통 상수 정의 (SSOT) |
| `backend/services/generation_prompt.py` | 수정 | `_PERSON_INDICATORS`에 `CROWD_INDICATOR_TAGS` 합성 |
| `backend/services/agent/nodes/finalize.py` | 수정 | `_rebuild_image_prompt_from_context_tags()` 군중 Narrator 예외 |
| `backend/services/agent/nodes/_cine_compositor.py` | 수정 | Compositor 프롬프트 — Narrator 군중 분기 규칙 |
| `backend/services/agent/nodes/_cine_action.py` | 수정 | Action 프롬프트 — Narrator 군중 씬 예외 규칙 |
| `backend/services/agent/nodes/_cine_framing.py` | 수정 | Framing 프롬프트 — Narrator 군중 힌트 |
| `backend/services/agent/nodes/_cine_atmosphere.py` | — | 변경 없음 (이미 적절) |
| `backend/tests/test_generation_prompt.py` | 수정 | Narrator 군중 씬 테스트 추가 |
| `backend/tests/test_finalize_context_tags.py` | 수정 | Finalize 군중 Narrator 테스트 추가 |

---

## 공통: 군중 태그 SSOT

### 구현 방법

**파일**: `backend/config_prompt.py`

군중 인디케이터 태그를 1곳에 정의하여 `generation_prompt.py`와 `finalize.py` 양쪽에서 import.

```python
# 군중/불특정 다수 인디케이터 (Danbooru 표준 태그)
CROWD_INDICATOR_TAGS: frozenset[str] = frozenset({
    "crowd",         # 일반 군중
    "many_others",   # 배경 엑스트라 다수
    "6+girls",       # 6명 이상 여성
    "6+boys",        # 6명 이상 남성
})
```

> **Danbooru 검증 (Prompt Reviewer BLOCKER 반영)**:
> - `multiple_others` → `many_others` 변경 (정확한 Danbooru 태그)
> - `people` 제거 (Alias, 직접 사용 불가)
> - `everyone` 제거 (의미적 오용 위험 — "특정 작품의 전원 멤버" 의미)

---

## DoD-A: `_inject_narrator_defense()` 개선

### 구현 방법

**파일**: `backend/services/generation_prompt.py`

1. `_PERSON_INDICATORS` (L23) 확장 — `CROWD_INDICATOR_TAGS` import 합성:
```python
from config_prompt import CROWD_INDICATOR_TAGS

_PERSON_INDICATORS = frozenset({
    "1girl", "1boy", "2girls", "2boys", "3girls", "3boys",
    "solo", "couple", "group",
}) | CROWD_INDICATOR_TAGS
```

2. `_inject_narrator_defense()` (L114-122) — 변경 불필요:
   - 이미 `has_person = any(ind in prompt_norm for ind in _PERSON_INDICATORS)` 로직으로 substring 매칭
   - `crowd`, `many_others` 등이 추가되면 자동으로 감지하여 `no_humans` 주입을 스킵

3. `_append_narrator_negative()` (L125-132) — 변경 불필요:
   - `"no_humans" not in request.prompt` 이면 early return
   - `_inject_narrator_defense()`가 `no_humans`를 주입하지 않으면, 이 함수도 자동으로 person-exclusion 태그를 주입하지 않음
   - 즉, `_PERSON_INDICATORS` 확장만으로 DoD-A의 3개 항목이 모두 달성됨

### 동작 정의

| 입력 | Before | After |
|------|--------|-------|
| `prompt="scenery, crowd, busy_street"`, `character_id=None` | `no_humans` 주입 | `crowd` 감지 → `no_humans` 미주입 |
| `prompt="scenery, empty_classroom"`, `character_id=None` | `no_humans` 주입 | 동일 (변경 없음) |
| `prompt="scenery, many_others, office"`, `character_id=None` | `no_humans` 주입 | `many_others` 감지 → `no_humans` 미주입 |

### 엣지 케이스
- **`character_id`가 있는 씬**: `_inject_narrator_defense()`가 L116에서 early return → 영향 없음
- **`prompt_pre_composed=True`**: 동일하게 early return → 영향 없음
- **substring 매칭 오탐**: `crowd` 가 `crowded`에도 매칭되지만, `crowded`는 사람이 많다는 의미이므로 의도된 동작

### 영향 범위
- `_inject_narrator_defense()` → `_append_narrator_negative()` 체인 한정
- **긍정적 사이드 이펙트**: 군중 Narrator 씬에서 `no_humans`가 없으므로 `generation_controlnet.py`의 환경 레퍼런스가 활성화됨 (군중 씬은 환경이 중요하므로 오히려 바람직)

### 테스트 전략
- `test_crowd_narrator_skips_no_humans()`: `prompt="scenery, crowd, busy_street"` → `no_humans` 미주입
- `test_many_others_narrator_skips_no_humans()`: `prompt="scenery, many_others, office"` → `no_humans` 미주입
- `test_empty_scene_narrator_still_injects_no_humans()`: `prompt="scenery, empty_room"` → `no_humans` 주입 (기존 동작 유지)
- `test_crowd_narrator_skips_negative_extra()`: 군중 씬 → `NARRATOR_NEGATIVE_PROMPT_EXTRA` 미추가

### Out of Scope
- `_PERSON_INDICATORS`의 substring 매칭 → exact token 매칭 전환 (별도 태스크)
- NLP 기반 script 텍스트 분석 (Gemini가 이미 script → 태그 변환 수행)

---

## DoD-B: Finalize 노드 Narrator 처리

### 구현 방법

**파일**: `backend/services/agent/nodes/finalize.py`

1. `CROWD_INDICATOR_TAGS` import (config_prompt.py SSOT):
```python
from config_prompt import CROWD_INDICATOR_TAGS
```

2. 헬퍼 함수 추가:
```python
def _has_crowd_indicators(scene: dict) -> bool:
    """Check if scene's image_prompt or context_tags contain crowd indicators.

    OR 조건: image_prompt 또는 context_tags 중 하나라도 군중 태그가 있으면 True.
    """
```
- `scene["image_prompt"]`를 토큰 분리하여 `CROWD_INDICATOR_TAGS`와 대조
- `context_tags` 내 `action`/`environment` 값도 `CROWD_INDICATOR_TAGS`와 대조
- 둘 중 하나라도 매칭되면 `True` (OR 조건)

3. `_rebuild_image_prompt_from_context_tags()` (L818-819) 수정:
```python
# Before:
if is_narrator:
    tags.extend(["no_humans", "scenery"])

# After:
if is_narrator:
    if _has_crowd_indicators(scene):
        tags.append("scenery")  # scenery는 유지, no_humans만 스킵
    else:
        tags.extend(["no_humans", "scenery"])
```

4. `_inject_negative_prompts()` (L88-97) — 변경 불필요:
   - `negative_prompt_extra` 필드를 병합하는 범용 로직
   - Cinematographer가 군중 Narrator 씬에 `negative_prompt_extra`를 빈 문자열로 설정하도록 프롬프트 변경(DoD-C)하면 자동으로 처리됨

### 동작 정의

| 씬 | context_tags/image_prompt | Before | After |
|----|--------------------------|--------|-------|
| Narrator + `crowd` in image_prompt | `{action: null, environment: ["busy_street"]}` | `["no_humans", "scenery", ...]` | `["scenery", ...]` (crowd 유지) |
| Narrator + 빈 공간 | `{environment: ["empty_classroom"]}` | `["no_humans", "scenery", ...]` | 동일 |

### 엣지 케이스
- **context_tags 없는 구 스토리보드**: `_rebuild_image_prompt_from_context_tags()`가 skip → 영향 없음
- **multi 씬 + Narrator**: 현재 multi는 Narrator와 조합되지 않지만, 만약 조합되면 multi_preserved 태그가 선행하고 crowd 판단도 정상 동작

### 영향 범위
- `_rebuild_image_prompt_from_context_tags()` 내부만 변경. 다른 Finalize 함수에 영향 없음.

### 테스트 전략
- `test_narrator_crowd_scene_no_humans_skipped()`: Narrator + crowd in image_prompt → rebuild 시 `no_humans` 없음, `scenery` 있음
- `test_narrator_empty_scene_no_humans_injected()`: Narrator + 빈 공간 → `no_humans` 주입 (기존 동작)
- `test_has_crowd_indicators_with_crowd_tag()`: `_has_crowd_indicators()` — image_prompt에 crowd → True
- `test_has_crowd_indicators_in_context_tags()`: context_tags.action에 crowd → True
- `test_has_crowd_indicators_with_no_crowd()`: 군중 태그 없는 씬 → False

### Out of Scope
- `_validate_scene_prompts()` (L1017)의 fallback 로직 — Narrator 빈 프롬프트 처리이므로 군중과 무관
- `background_generator.py`의 Stage 워크플로우 — "배경 전용 생성" 경로이므로 군중 예외를 적용하지 않음 (별도 스코프)

---

## DoD-C: Cinematographer 프롬프트 업데이트

### 구현 방법

**파일 1**: `backend/services/agent/nodes/_cine_compositor.py` (L140)

```python
# Before (L140):
"- For Narrator scenes: add no_humans, scenery. Set negative_prompt_extra to '1girl, 1boy, person'",

# After:
"- For Narrator scenes (speaker='Narrator'):",
"  - If script implies people/crowd activity (busy office, crowded street, festival): add crowd + scenery. Do NOT add no_humans. Set negative_prompt_extra to empty string ''.",
"  - If script implies empty/quiet space (empty room, silent corridor, night sky): add no_humans + scenery. Set negative_prompt_extra to '1girl, 1boy, person'.",
```

**파일 2**: `backend/services/agent/nodes/_cine_action.py` (L47-48)

```python
# Before:
"   For Narrator scenes: set controlnet_pose to null.\n"
"5. **Narrator scenes**: No action/pose/emotion. Set all to null. Props only if relevant."

# After:
"   For Narrator scenes: set controlnet_pose to null.\n"
"5. **Narrator scenes**: No CHARACTER action/pose/emotion. Set to null.\n"
"   - Exception: if script implies crowd/people activity, set action to 'crowd'. Props if relevant."
```

**파일 3**: `backend/services/agent/nodes/_cine_framing.py` (L39)

```python
# Before:
'5. **Narrator scenes** (speaker="Narrator"): wide_shot or from_above preferred. ken_burns still required.'

# After:
'5. **Narrator scenes** (speaker="Narrator"): wide_shot or from_above preferred. ken_burns still required.\n'
'   - Crowd Narrator: wide_shot strongly preferred to capture multiple people.'
```

**파일 4**: `backend/services/agent/nodes/_cine_atmosphere.py` (L42-43)

변경 불필요. 이미 "Use cinematic techniques aggressively"로 군중/빈 공간 모두에 적용 가능.

### 동작 정의

Gemini(Cinematographer)가 script 의미를 분석하여:
- "정신없는 사무실 풍경" → `crowd, scenery, office, ...` + `negative_prompt_extra: ""`
- "조용한 복도" → `no_humans, scenery, corridor, ...` + `negative_prompt_extra: "1girl, 1boy, person"`

### 엣지 케이스
- **Gemini가 군중 판단을 틀리는 경우**: Finalize의 `_rebuild_image_prompt_from_context_tags()`가 2차 방어선. Gemini가 `crowd` 태그를 넣었으면 Finalize도 `no_humans`를 스킵.
- **프롬프트 길이 증가**: 규칙 2줄 추가 (약 200자) — 컨텍스트 윈도우 영향 미미

### 영향 범위
- Cinematographer 서브에이전트 프롬프트 변경 → Gemini 출력이 달라짐
- 기존 빈 공간 Narrator 씬은 기존과 동일한 태그 생성 (후방 호환)

### 테스트 전략
- 프롬프트 문자열 변경은 단위 테스트 대상 아님 (Gemini 출력은 비결정적)
- DoD-A, B의 테스트가 end-to-end 방어

### Out of Scope
- LangFuse 프롬프트 업데이트 (Cinematographer 프롬프트는 코드 내 하드코딩, LangFuse 아님)
- Gemini 출력 품질 검증 (별도 QA 필요)

---

## DoD-D: 테스트

### 테스트 파일 및 케이스

**파일 1**: `backend/tests/test_generation_prompt.py`

| 테스트 함수 | 검증 내용 |
|------------|----------|
| `test_crowd_narrator_skips_no_humans` | `prompt="scenery, crowd, busy_street"` + `character_id=None` → `no_humans` 미주입 |
| `test_many_others_narrator_skips_no_humans` | `prompt="scenery, many_others, office"` → `no_humans` 미주입 |
| `test_empty_scene_narrator_still_injects_no_humans` | `prompt="scenery, empty_classroom"` → `no_humans` 주입 (regression) |
| `test_crowd_narrator_skips_negative_extra` | 군중 씬 → `NARRATOR_NEGATIVE_PROMPT_EXTRA` 미추가 |

**파일 2**: `backend/tests/test_finalize_context_tags.py`

| 테스트 함수 | 검증 내용 |
|------------|----------|
| `test_narrator_crowd_skips_no_humans_in_rebuild` | Narrator + `image_prompt`에 `crowd` → rebuild 시 `no_humans` 없음, `scenery` 있음 |
| `test_narrator_empty_keeps_no_humans_in_rebuild` | Narrator + 빈 공간 → `no_humans, scenery` 유지 (regression) |
| `test_has_crowd_indicators_with_crowd_tag` | `_has_crowd_indicators()` — image_prompt에 crowd → True |
| `test_has_crowd_indicators_in_context_tags` | context_tags.action에 crowd → True |
| `test_has_crowd_indicators_with_no_crowd` | 군중 태그 없는 씬 → False |

### 린트
- `ruff check backend/` + `ruff format --check backend/` 통과 필수

---

## 에이전트 설계 리뷰 결과

| 리뷰어 | 판정 | 주요 피드백 | 반영 |
|--------|------|------------|------|
| **Prompt Reviewer** | BLOCKER → 반영 완료 | `multiple_others`→`many_others`, `people`/`everyone` 제거 (Danbooru 미준수) | 태그 목록 전면 수정 |
| **Tech Lead** | WARNING → 반영 완료 | (1) `_CROWD_TAGS`/`_PERSON_INDICATORS` 이중 관리 → `config_prompt.py` SSOT 통합 | `CROWD_INDICATOR_TAGS` 공통 상수 도입 |
| **Tech Lead** | WARNING → 반영 완료 | (2) `background_generator.py` Stage 경로 누락 → Out of Scope 명시 | DoD-B Out of Scope에 추가 |
| **Tech Lead** | INFO → 반영 완료 | `generation_controlnet.py` 환경 레퍼런스 활성화 (긍정적 사이드 이펙트) | DoD-A 영향 범위에 명시 |
| **Tech Lead** | INFO → 반영 완료 | `_has_crowd_indicators` OR 조건 명시 필요 | DoD-B 헬퍼 함수 설명에 명시 |
