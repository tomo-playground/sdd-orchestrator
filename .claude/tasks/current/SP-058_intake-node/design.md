# SP-058 상세 설계: Intake 노드

> 간소화 설계 (변경 파일 7개, DB/API 변경 없음)

## 설계 결정: 단일 interrupt 패턴

DoD는 "interrupt() 루프로 다중 Q&A 라운드"를 명시하지만, Tech Lead 리뷰 결과 **단일 interrupt**로 변경한다.

**이유**:
- LangGraph는 조건부 interrupt 스킵을 명시적으로 금지 (인덱스 불일치 위험)
- 프로젝트의 resume 인프라가 "1 노드 = 1 interrupt = 1 resume" 전제
- 단일 interrupt로도 다중 질문 전달 가능 (payload에 questions 배열)
- 네트워크 왕복 3회 → 1회 감소

**구현**: LLM이 토픽을 분석하여 structure/tone을 제안. 모든 질문 + 제안을 하나의 interrupt payload로 전달. Frontend가 위자드/카드 UI로 표시하고, 한 번의 resume으로 모든 답변 수집.

---

## 변경 파일 요약

| 파일 | 유형 | 설명 |
|------|------|------|
| `backend/services/agent/nodes/intake.py` | 신규 | Intake 노드 (LLM 분석 + 단일 interrupt) |
| `backend/services/agent/script_graph.py` | 수정 | 노드 등록 + 엣지 + conditional_edges 목적지 + docstring |
| `backend/services/agent/routing.py` | 수정 | route_after_start에 intake 분기 추가 |
| `backend/services/agent/state.py` | 수정 | `intake_summary` 필드 추가 |
| `backend/routers/_scripts_sse.py` | 수정 | NODE_META + read_interrupt_state에 intake 케이스 |
| `backend/schemas/scripts.py` | 수정 | ScriptResumeRequest에 intake 필드 |
| `frontend/app/hooks/scriptEditor/sseProcessor.ts` | 수정 | intake interrupt 이벤트 처리 (최소) |

---

## DoD 1: Intake 노드 구현 + 그래프 통합

### 구현 방법

**`intake.py`** — `async def intake_node(state: ScriptState, config=None) -> dict`

```
1. 인벤토리 로드: load_full_inventory(group_id) → characters
2. LLM 분석 (1회): _analyze_topic() → suggested_structure, suggested_tone, reasoning
3. 단일 interrupt: 질문 3종 + LLM 제안을 payload로 전달
4. resume 값 파싱: structure, tone, character_id, character_b_id 추출
5. 결과 반환: {structure, tone, character_id, character_b_id, intake_summary}
```

**`script_graph.py`** — 노드 등록 + 엣지

```python
graph.add_node("intake", intake_node)
graph.add_edge("intake", "director_plan")

# 기존: graph.add_conditional_edges(START, route_after_start, ["director_plan", "writer"])
# 변경: "intake" 추가
graph.add_conditional_edges(START, route_after_start, ["intake", "director_plan", "writer"])
```

> docstring의 경로 설명도 `START -> intake -> director_plan` 으로 업데이트.

**`routing.py`** — route_after_start 수정

```python
def route_after_start(state: ScriptState) -> str:
    skip = state.get("skip_stages") or []
    if skip:
        return "writer"
    mode = coerce_interaction_mode(state.get("interaction_mode"))
    if mode == "fast_track":
        return "director_plan"   # FastTrack: intake 건너뜀
    return "intake"              # Guided: intake 먼저
```

> 기존 `skip_stages → writer` 분기는 그대로 유지.
> FastTrack 스킵을 라우팅 레벨에서 처리하여 노드 실행 자체를 회피.

**`state.py`** — 필드 추가

```python
class ScriptState(TypedDict, total=False):
    # ... 기존 필드 ...
    intake_summary: str   # Intake 결정 요약 (예: "학교 괴담, 대화형, 서스펜스, 미도리↔하루")
```

> `structure`, `tone`, `character_id`, `character_b_id`는 이미 State에 존재.
> `intake_summary`만 추가.

### 테스트 전략

| 테스트 | 검증 |
|--------|------|
| `test_intake_fast_track_skipped` | FastTrack 모드 → route_after_start가 "director_plan" 반환 |
| `test_intake_guided_enters` | Guided 모드 → route_after_start가 "intake" 반환 |
| `test_intake_skip_stages_bypasses` | skip_stages 설정 → "writer" 반환 (기존 동작 보존) |
| `test_graph_intake_edge` | intake → director_plan 엣지 존재 확인 |

---

## DoD 2: 질문 흐름 (단일 interrupt)

### 구현 방법

**노드 흐름 상세**:

```python
async def intake_node(state: ScriptState, config=None) -> dict:
    topic = state.get("topic", "")
    description = state.get("description", "")
    group_id = state.get("group_id")

    # ── 인벤토리 로드 ──
    inventory = load_full_inventory(group_id)
    characters = inventory.get("characters", [])

    # ── LLM 분석 (1회) ──
    analysis = await _analyze_topic(topic, description, config)
    # analysis = {suggested_structure, suggested_tone, reasoning}

    # ── 단일 interrupt: 모든 질문을 한 번에 전달 ──
    user_input = interrupt({
        "type": "intake",
        "analysis": {
            "suggested_structure": analysis.get("suggested_structure"),
            "suggested_tone": analysis.get("suggested_tone"),
            "reasoning": analysis.get("reasoning", ""),
        },
        "questions": [
            {
                "key": "structure",
                "message": "어떤 형태의 영상을 상상하고 계세요?",
                "options": [
                    {"id": s.id, "label": s.label_ko,
                     "description": _structure_hint(s.id)}
                    for s in STRUCTURE_METADATA
                ],
            },
            {
                "key": "tone",
                "message": "어떤 분위기를 원하세요?",
                "options": [
                    {"id": t.id, "label": t.label_ko,
                     "description": TONE_HINTS[t.id]}
                    for t in TONE_METADATA
                ],
            },
            {
                "key": "characters",
                "message": "캐릭터를 골라볼까요?",
                "applicable": True,   # Frontend가 structure 선택에 따라 표시/숨김
                "needs_two": True,
                "characters": [
                    {"id": c.id, "name": c.name, "gender": c.gender,
                     "summary": c.appearance_summary}
                    for c in characters
                ],
            },
        ],
    })

    # ── resume 값 파싱 ──
    structure = coerce_structure_id(
        user_input.get("structure")
        or analysis.get("suggested_structure")
        or "monologue"
    )
    tone = coerce_tone_id(
        user_input.get("tone")
        or analysis.get("suggested_tone")
        or "intimate"
    )

    # 캐릭터: resume에서 받거나 기존값 유지
    char_a = user_input.get("character_id") or state.get("character_id")
    char_b = user_input.get("character_b_id") or state.get("character_b_id")

    # 2인 구조인데 캐릭터 미선택 시 → 기본값 유지 (Director Plan이 캐스팅 추천)
    if structure not in MULTI_CHAR_STRUCTURES:
        char_b = None

    # ── 결과 ──
    summary = _build_intake_summary(topic, structure, tone, characters, char_a, char_b)

    return {
        "structure": structure,
        "tone": tone,
        "character_id": char_a,
        "character_b_id": char_b,
        "intake_summary": summary,
    }
```

**interrupt payload 구조** (Backend → Frontend):

```json
{
  "type": "intake",
  "analysis": {
    "suggested_structure": "dialogue",
    "suggested_tone": "suspense",
    "reasoning": "두 사람이 대화하는 형태의 공포 이야기로 판단됩니다"
  },
  "questions": [
    {"key": "structure", "message": "...", "options": [...]},
    {"key": "tone", "message": "...", "options": [...]},
    {"key": "characters", "message": "...", "characters": [...], "needs_two": true}
  ]
}
```

**resume payload 구조** (Frontend → Backend):

```json
{
  "action": "answer",
  "intake_value": {
    "structure": "dialogue",
    "tone": "suspense",
    "character_id": 5,
    "character_b_id": 8
  }
}
```

**LLM 분석 함수**: `_analyze_topic(topic, description, config) -> dict`

```
- LangFuse 프롬프트: "creative/intake" (system + user)
- 모델: GEMINI_FLASH (가벼운 분류 태스크)
- temperature: 0 (결정론적)
- 출력 스키마: {suggested_structure: str, suggested_tone: str, reasoning: str}
- safety_settings: GEMINI_SAFETY_SETTINGS (config.py SSOT)
- system_instruction 분리 (CLAUDE.md Gemini 규칙 준수)
- LangFuse 프롬프트 미존재 시 fallback: 하드코딩 기본 프롬프트로 graceful degradation
  (프롬프트 생성은 별도 작업이므로 런타임 에러 방지 필수)
```

**헬퍼 함수**:

| 함수 | 역할 |
|------|------|
| `_analyze_topic()` | LLM 토픽 분석 → 구조/톤 제안 |
| `_structure_hint(id)` | structure별 한 줄 설명 (사용자 친화적) |
| `_build_intake_summary()` | 결정 요약 문자열 생성 |

### 테스트 전략

| 테스트 | 검증 |
|--------|------|
| `test_intake_structure_from_resume` | resume에서 structure 올바르게 파싱 |
| `test_intake_tone_from_resume` | resume에서 tone 올바르게 파싱 |
| `test_intake_characters_from_resume` | resume에서 character_id, character_b_id 파싱 |
| `test_intake_fallback_to_suggestion` | resume에 값 없으면 LLM 제안값 사용 |
| `test_intake_fallback_to_default` | LLM 제안도 없으면 기본값 (monologue/intimate) |
| `test_intake_monologue_clears_char_b` | monologue 선택 시 character_b_id = None |
| `test_intake_invalid_structure_coerced` | 잘못된 structure 값 → coerce_structure_id 정규화 |
| `test_intake_invalid_tone_coerced` | 잘못된 tone 값 → coerce_tone_id 정규화 |
| `test_intake_characters_preserved_if_set` | state에 char 이미 설정 + resume에 없으면 기존값 유지 |
| `test_intake_empty_group_no_characters` | 그룹에 캐릭터 0명 → characters 빈 배열 전달 |
| `test_analyze_topic_langfuse_missing` | LangFuse 프롬프트 없을 때 fallback 동작 |

---

## DoD 3: 출력 + Director Plan 연동

### 구현 방법

**Intake → State 저장 필드**:

| 필드 | 소스 | 설명 |
|------|------|------|
| `structure` | resume 선택 / LLM 제안 / 기본값 | coerce_structure_id() 정규화 |
| `tone` | resume 선택 / LLM 제안 / 기본값 | coerce_tone_id() 정규화 |
| `character_id` | resume / 기존값 | Speaker A |
| `character_b_id` | resume / 기존값 / None | Speaker B (2인 구조만) |
| `intake_summary` | 자동 생성 | "학교 괴담, 대화형, 서스펜스, 미도리↔하루" |

**Director Plan 연동**: 변경 불필요.
- `director_plan_node`는 이미 `state.get("structure")`, `state.get("tone")` 등을 읽음
- Intake가 state에 값을 설정하면 Director Plan이 자동으로 소비

**SSE 연동** (`_scripts_sse.py`):

NODE_META에 intake 항목 추가:
```python
NODE_META = {
    # ... 기존 항목 ...
    "intake": {"label": "의도 파악", "percent": 3},
}
```

read_interrupt_state()에 intake 케이스 추가:
```python
if interrupt_node == "intake":
    tasks = snapshot.tasks
    interrupt_data = {}
    if tasks:
        for task in tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                interrupt_data = task.interrupts[-1].value
                break
    result = {
        "type": "intake",
        **interrupt_data,
    }
```

**Resume 스키마** (`schemas/scripts.py`):

```python
class ScriptResumeRequest(BaseModel):
    # ... 기존 필드 ...
    # Intake 전용 (optional, 하위 호환)
    intake_value: dict | None = None   # {"structure": str, "tone": str, "character_id": int, ...}
```

Resume 핸들러 (`scripts.py`):
```python
if request.intake_value is not None:
    resume_value.update(request.intake_value)
```

### 테스트 전략

| 테스트 | 검증 |
|--------|------|
| `test_intake_summary_format` | intake_summary가 "토픽, 구조, 톤" 형식 |
| `test_intake_output_consumed_by_director` | Intake 출력 후 director_plan_node가 올바른 structure/tone 사용 |
| `test_read_interrupt_state_intake` | read_interrupt_state가 intake 노드의 interrupt 데이터 반환 |

---

## DoD 4: Frontend 최소 변경

### 구현 방법

**`sseProcessor.ts`** — intake interrupt 이벤트 핸들링:

```typescript
// Intake interrupt
if (
  event.status === "waiting_for_input" &&
  event.node === "intake" &&
  event.result?.type === "intake"
) {
  return {
    ...base,
    isGenerating: false,
    isWaitingForIntake: true,
    intakeData: event.result,  // {analysis, questions}
  };
}
```

**ScriptEditorState** — 상태 필드 추가:
```typescript
isWaitingForIntake: false,    // INITIAL_STATE
intakeData: null,             // INITIAL_STATE
```

> Intake 전용 UI 컴포넌트(IntakeModal/IntakeWizard)는 별도 태스크로 분리 가능.
> 최소 구현: 기존 catch-all `isWaitingForInput` 핸들러로 대체 동작 보장.

### 테스트 전략

| 테스트 | 검증 |
|--------|------|
| `test_sse_intake_event_sets_state` | intake waiting_for_input → isWaitingForIntake: true |

---

## DoD 5: 품질 게이트

### 구현 방법

- 기존 테스트 regression: 전체 `pytest` 통과 확인
- 린트: ruff + prettier 통과 (auto-lint hook)
- 신규 테스트: 위 DoD 1~4의 테스트 전략 항목 (총 19개)

### 테스트 파일 구조

```
backend/tests/services/agent/nodes/test_intake.py
  - test_intake_fast_track_skipped
  - test_intake_guided_enters
  - test_intake_structure_from_resume
  - test_intake_tone_from_resume
  - test_intake_characters_from_resume
  - test_intake_fallback_to_suggestion
  - test_intake_fallback_to_default
  - test_intake_monologue_clears_char_b
  - test_intake_invalid_structure_coerced
  - test_intake_invalid_tone_coerced
  - test_intake_characters_preserved_if_set
  - test_intake_empty_group_no_characters
  - test_intake_summary_format
  - test_intake_output_consumed_by_director
  - test_analyze_topic_langfuse_missing

backend/tests/services/agent/test_routing.py (기존 파일에 추가)
  - test_route_after_start_guided_intake
  - test_route_after_start_fast_track_director
  - test_route_after_start_skip_stages_writer

backend/tests/routers/test_scripts_sse.py (기존 파일에 추가)
  - test_read_interrupt_state_intake
```

---

## 에이전트 설계 리뷰 결과

| 리뷰어 | 판정 | 주요 피드백 | 반영 |
|--------|------|------------|------|
| Tech Lead | BLOCKER → 반영 완료 | 다중 interrupt → 단일 interrupt 전환 권고 | 전면 반영: 단일 interrupt 패턴으로 재설계 |
| Tech Lead | WARNING → 반영 완료 | NODE_META에 "intake" 항목 누락 | DoD 3에 추가 |
| Tech Lead | WARNING → 반영 완료 | add_conditional_edges 목적지 리스트 변경 누락 | DoD 1에 명시 |
| Tech Lead | WARNING → 반영 완료 | LangFuse 프롬프트 fallback 로직 미정의 | DoD 2 LLM 분석 함수에 fallback 명시 |

---

## Out of Scope (이번 태스크에서 제외)

| 항목 | 이유 |
|------|------|
| 질문 축소 (LLM 판단으로 라운드 자동 스킵) | 단일 interrupt에서는 불필요. Frontend가 suggested 기반으로 프리필 |
| Intake 전용 UI 컴포넌트 (IntakeWizard) | scope: backend. catch-all 핸들러로 대체 |
| LangFuse 프롬프트 콘텐츠 작성 | LangFuse 관리 영역. fallback 로직으로 런타임 보호 |
| Director Plan prompt에 intake_summary 주입 | 기존 state 필드 소비로 충분. 필요 시 후속 |
