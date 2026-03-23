# SP-059 상세 설계: multi 씬 활성화

## 근본 원인 분석

DB에 `scene_mode="multi"` 씬이 0건인 근본 원인은 **Finalize 과잉 보정이 아니라, Cinematographer가 scene_mode를 출력하지 않기 때문**이다.

- `build_multi_character_rules()`는 `gemini_generator.py`(직접 API 경로)에서만 호출됨
- Agent Pipeline의 Cinematographer 노드 → Compositor 서브 에이전트의 output format에 `scene_mode` 필드가 없음
- 결과: 모든 씬이 DB 기본값 `"single"`로 저장됨
- Finalize의 3가지 전환 조건(O-2b, O-2c, O-2e)은 모두 합리적인 가드 → 유지

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `nodes/_cine_compositor.py` | output format에 `scene_mode` 추가 + `_build_prompt()`에 multi rules 섹션 주입 |
| `nodes/cinematographer.py` | `is_multi` 계산 + `_run()` → `_run_team()` → `_run_team_inner()` → `run_compositor()` 전달 체인 + single fallback 반영 |
| `nodes/finalize.py` | multi >2개 시 상한 캡 추가 (warning → 강제 전환) |
| `prompt_builders_c.py` | 기존 `build_multi_character_rules()` 내부 위임으로 Compositor 전용 래퍼 추가 |
| `tests/test_validate_scene_modes.py` | `_validate_scene_modes()` 직접 테스트 (신규) |
| `tests/test_compositor_scene_mode.py` | Compositor multi rules 주입 + single fallback 테스트 (신규) |

---

## DoD 1: Cinematographer 프롬프트에서 scene_mode="multi" 출력 지시 강화

### 구현 방법

**1-a. `cinematographer.py` — `is_multi` 계산 + 4단계 전달 체인**

`_run()`에서 계산:

```python
structure = state.get("structure", "")
char_b = state.get("character_b_id") or state.get("draft_character_b_id")
is_multi = bool(char_b) and coerce_structure_id(structure) in ("dialogue", "narrated_dialogue")
```

전달 체인 (시그니처에 `is_multi: bool = False` 추가):
1. `_run()` — 계산
2. `_run_team(... is_multi)` — 전달
3. `_run_team_inner(... is_multi)` — 전달
4. `run_compositor(... is_multi)` — 소비

**1-b. `_cine_compositor.py` — output format + multi rules**

`run_compositor()` 시그니처에 `is_multi: bool = False` 추가.

`_build_prompt()`에서 `is_multi=True`일 때 `## Assembly Instructions` 앞에 multi rules 섹션 삽입:

```
## Multi-Character Scene Rules
- You MAY set "scene_mode": "multi" for 1-2 scenes where BOTH characters appear together
- Use ONLY when the scene script explicitly involves BOTH characters interacting
  (e.g., reunion, farewell, conflict, joint reaction to the same event)
- Do NOT use multi for scenes where only one character is speaking/thinking
- Multi scenes: subject should reflect both characters (e.g., "1boy, 1girl" / "2girls" / "2boys")
- Multi scenes: add interaction tags (e.g., "eye_contact", "looking_at_another", "hand_holding")
- Multi scenes: character identity/appearance tags are injected automatically — do NOT add them to image_prompt
- Multi scenes: speaker field can be "A" or "B" (whoever is speaking in that moment)
- All other scenes MUST use "scene_mode": "single"
- LIMIT: Maximum 2 multi scenes per storyboard
```

`_OUTPUT_FORMAT` 상수에 `"scene_mode": "single"` 필드 추가 (order 다음, script 앞).

**1-c. `cinematographer.py` single fallback — 동일 반영**

`_JSON_OUTPUT_INSTRUCTION`에 `"scene_mode": "single"` 필드 추가.
`is_multi=True`이면 single fallback 프롬프트에도 multi rules 삽입.

### 동작 정의

- Before: Compositor가 scene_mode 없이 JSON 출력 → 모든 씬 DB 기본값 `"single"`
- After: Compositor가 `"scene_mode": "single"|"multi"` 출력 → dialogue/narrated_dialogue에서 1-2씬이 `"multi"`로 생성

### 엣지 케이스

| 상황 | 처리 |
|------|------|
| `is_multi=False` (monologue) | multi rules 미삽입, scene_mode 필드는 output format에 포함 (항상 "single") |
| LLM이 scene_mode를 출력하지 않음 | Finalize에서 기본값 "single" 적용 (기존 동작) |
| LLM이 3개 이상 multi 출력 | Finalize 상한 캡에서 2개로 제한 (DoD 4) |

### 영향 범위

- Compositor/Single fallback의 Gemini 호출에 프롬프트 변경 → 토큰 소비 미세 증가 (~200 tokens)
- 기존 monologue 스토리보드 생성에는 영향 없음 (`is_multi=False` → rules 미삽입)

### 테스트 전략

- `is_multi=True`일 때 Compositor prompt에 "Multi-Character Scene Rules" 섹션 존재 확인
- `is_multi=False`일 때 해당 섹션 미존재 확인
- output format 문자열에 `"scene_mode"` 필드 존재 확인
- single fallback 경로에서 `is_multi=True` 시 multi rules 존재 확인

### Out of Scope

- LangFuse `creative/cinematographer` 템플릿 변경 (코드 내 프롬프트로 충분)
- 서브 에이전트(Framing/Action/Atmosphere) 변경 (Compositor만 최종 JSON 조립)

---

## DoD 2: 핵심 감정 장면에서 1-2씬 multi 지정 규칙

### 구현 방법

`prompt_builders_c.py`에 Compositor 전용 래퍼 함수 추가. 기존 `build_multi_character_rules()`의 공통 로직(성별 판별, subject 예시 생성)을 내부 위임하여 **코드 중복 방지**.

```python
def build_compositor_multi_rules(
    is_multi: bool,
    char_a_ctx: dict | None = None,
    char_b_ctx: dict | None = None,
) -> str:
```

- `is_multi=False` → 빈 문자열
- `is_multi=True` → Compositor 전용 포맷으로 multi rules 텍스트 블록 반환
- 성별 기반 subject 예시 생성은 `_resolve_subject_example(char_a_ctx, char_b_ctx)` 공통 헬퍼로 추출 (기존 `build_multi_character_rules()`도 이 헬퍼를 사용하도록 리팩토링)

**기존 함수와의 차이점:**
- `build_multi_character_rules()`: gemini_generator.py 전용, `⚠️` 경고 포맷, Writer가 draft_scenes에 scene_mode를 설정하는 용도
- `build_compositor_multi_rules()`: Compositor 전용, `##` 마크다운 섹션 포맷, Compositor가 최종 JSON에 scene_mode를 설정하는 용도
- 공통: 성별 판별 로직, subject 예시, 상한 2개 규칙

Compositor의 `_build_prompt()`에서 이 함수를 호출하여 삽입.

### 동작 정의

- Before: Cinematographer에 multi 씬 생성 지시 없음
- After: dialogue/narrated_dialogue 구조 + character_b 존재 시 "핵심 감정 장면에서 1-2씬 multi" 규칙 주입

### 엣지 케이스

- 성별 정보 없는 캐릭터 → 기본 subject 예시 "2 characters" 사용

### 테스트 전략

- `build_compositor_multi_rules(is_multi=True, ...)` 반환값에 "scene_mode" 포함 확인
- `build_compositor_multi_rules(is_multi=False)` → 빈 문자열
- `build_compositor_multi_rules(is_multi=True, char_a_ctx=None, char_b_ctx=None)` → "2 characters" 기본값
- `_resolve_subject_example()` 공통 헬퍼 단위 테스트 (male+male, female+female, mixed, unknown)

### Out of Scope

- 기존 `build_multi_character_rules()` 삭제 (gemini_generator.py 경로에서 계속 사용)

---

## DoD 3: multi 씬 예시를 JSON output format에 포함

### 구현 방법

`_cine_compositor.py`의 `_OUTPUT_FORMAT` 상수에 `"scene_mode"` 필드를 추가:

```python
_OUTPUT_FORMAT = '''{"scenes": [
  {
    "order": 0,
    "scene_mode": "single",
    "script": "...",
    ...
  },
  ...
]}'''
```

`is_multi=True`일 때 multi rules 섹션에 multi 예시 JSON 스니펫 추가:

```
Example multi scene: {"order": 3, "scene_mode": "multi", "speaker": "A", "image_prompt": "eye_contact, looking_at_another, ..."}
```

### 동작 정의

- Before: output format에 scene_mode 없음
- After: 모든 씬에 scene_mode 필드 포함, multi 예시도 제공

### 테스트 전략

- `_OUTPUT_FORMAT` 문자열에 `"scene_mode"` 존재 확인

### Out of Scope

- Single fallback의 output format 구조 변경 (scene_mode 필드만 추가, 나머지 유지)

---

## DoD 4: Finalize 보정 완화

### 구현 방법

`finalize.py`의 `_validate_scene_modes()`:

기존 3개 전환 조건(O-2b, O-2c, O-2e) **전부 유지** — 모두 합리적인 가드.

**변경점**: multi >2개 시 warning만 출력하던 것 → **3번째부터 `single`로 강제 전환** 추가.

```python
multi_count = sum(1 for s in scenes if s.get("scene_mode") == "multi")
if multi_count > 2:
    logger.warning("[Finalize] %d multi scenes -> capping to 2", multi_count)
    kept = 0
    for s in scenes:
        if s.get("scene_mode") == "multi":
            kept += 1
            if kept > 2:
                s["scene_mode"] = "single"
```

앞에서부터 순회하여 처음 2개만 유지, 나머지를 single로 전환 (스토리 앞부분의 핵심 장면 우선 보존).

### 동작 정의

- Before: multi 3개 이상이면 warning 로그만, 모두 multi 유지
- After: multi 2개 초과 시 3번째부터 single로 강제 전환

### 엣지 케이스

| 상황 | 처리 |
|------|------|
| multi 0개 | 변경 없음 |
| multi 1-2개 | 변경 없음 |
| multi 3개 이상 | 앞 2개만 multi 유지, 나머지 single |

### 영향 범위

- Finalize의 scene_mode 관련 로직만 변경, 다른 flags 로직 영향 없음

### 테스트 전략

- O-2b: character_b_id 없음 → 모든 multi가 single로 전환
- O-2c: monologue 구조 → 모든 multi가 single로 전환
- O-2c: narrated_dialogue 구조 → multi 허용 (replace("_"," ") 변환 검증)
- O-2e: Narrator speaker + multi → single 전환
- 상한 캡: dialogue + char_b_id 존재 + multi 3개 입력 → 앞 2개만 multi, 3번째 single
- 상한 캡: dialogue + char_b_id 존재 + multi 4개 입력 → 1,2번째 multi 유지, 3,4번째 single
- 정상 케이스: dialogue + character_b_id + multi 2개 → 변경 없음

### Out of Scope

- `_auto_populate_scene_flags()`의 multi 씬 처리 (이미 정상 동작)
- Finalize의 다른 검증 로직

---

## DoD 5: multi 씬 상한 2개 유지

DoD 4에서 구현. 별도 항목 없음.

---

## DoD 6-8: 동작 검증 (테스트로 커버)

### 테스트 전략

**신규 파일 1: `test_validate_scene_modes.py`**

| 테스트 | 입력 | 기대 결과 |
|--------|------|----------|
| `test_monologue_forces_all_single` | structure="monologue", scenes with multi | 모든 scene_mode="single" |
| `test_dialogue_allows_multi` | structure="dialogue", char_b_id=5, 1 multi scene | multi 유지 |
| `test_narrated_dialogue_allows_multi` | structure="narrated_dialogue", char_b_id=5 | multi 유지 |
| `test_narrated_dialogue_underscore_matching` | structure="narrated_dialogue" | replace("_"," ") 변환 후 매칭 확인 |
| `test_no_char_b_forces_single` | structure="dialogue", char_b_id=None, multi scenes | 모든 single |
| `test_narrator_speaker_forces_single` | speaker="Narrator", scene_mode="multi" | single |
| `test_cap_multi_at_2` | dialogue + char_b + 3개 multi | 앞 2개 multi, 3번째 single |
| `test_cap_preserves_first_two` | dialogue + char_b + 4개 multi | 1,2번째 multi, 3,4번째 single |
| `test_zero_multi_no_change` | 모든 single | 변경 없음 |

**신규 파일 2: `test_compositor_scene_mode.py`**

| 테스트 | 입력 | 기대 결과 |
|--------|------|----------|
| `test_multi_rules_injected_when_multi` | is_multi=True | prompt에 "Multi-Character" 포함 |
| `test_multi_rules_absent_when_not_multi` | is_multi=False | prompt에 "Multi-Character" 미포함 |
| `test_output_format_has_scene_mode` | - | _OUTPUT_FORMAT에 "scene_mode" 포함 |
| `test_build_compositor_multi_rules_true` | is_multi=True | 비빈 문자열, "scene_mode" 포함 |
| `test_build_compositor_multi_rules_false` | is_multi=False | 빈 문자열 |
| `test_build_compositor_multi_rules_no_gender` | is_multi=True, ctx=None | "2 characters" 기본값 |
| `test_single_fallback_multi_rules` | is_multi=True, single fallback | prompt에 multi rules 포함 |
| `test_single_fallback_output_has_scene_mode` | single fallback | output format에 "scene_mode" 포함 |
| `test_resolve_subject_example_variants` | 4가지 성별 조합 | 각각 올바른 subject 태그 |

### Out of Scope

- E2E 테스트 (실제 Gemini 호출 → multi 씬 생성 확인) — 수동 검증
- MultiCharacterComposer 변경 (이미 정상 동작)
- ControlNet/IP-Adapter 비활성화 변경 (이미 정상 동작)

---

## 에이전트 설계 리뷰 결과

| 리뷰어 | 판정 | 주요 피드백 | 반영 |
|--------|------|------------|------|
| Tech Lead | WARNING x3 | (1) is_multi 전달 체인 4단계 명시 필요 (2) build_compositor_multi_rules 중복 방지 (3) 테스트 3건 누락 | 반영 완료 — DoD 1-a 체인 구체화, DoD 2 내부 위임 설계, 테스트 8건 추가 |
| Prompt Reviewer | WARNING x3 | (1) "key emotional moments" 조건 느슨 (2) facing_another→looking_at_another 교체 (3) "character tags 자동 주입 금지" 규칙 누락 | 반영 완료 — 조건 구체화, 태그 교체, 규칙 2줄 추가 |
