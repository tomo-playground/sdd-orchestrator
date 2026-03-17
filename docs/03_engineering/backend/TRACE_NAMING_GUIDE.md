# LangFuse Trace 네이밍 가이드

**상태**: Active (v1.0)
**최종 업데이트**: 2026-03-17
**관련 문서**: `AGENT_SPEC.md`, `LLM_PROVIDER_ABSTRACTION.md`

---

## 1. 목적

LangFuse 트레이스의 네이밍 표준을 정의한다.
[OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) 기반.

**핵심 원칙**:
- **저카디널리티**: 이름은 그룹핑 가능해야 한다. 고유값(step 번호, ID)은 metadata로
- **`{operation} {agent}`**: OTel GenAI 표준 포맷
- **dot namespace**: 하위 분류는 점(`.`)으로 구분

---

## 2. 계층 구조

```
Trace                          ← 요청 1건 = 1 Trace
  name: "{workflow}.{action}"
│
└─ Root Span                   ← 파이프라인 실행 단위
     name: "pipeline.{action}"
   │
   ├─ Generation               ← 단일 LLM 호출
   │    name: "{operation} {agent}"
   │    metadata: {step, retry, attempt, ...}
   │
   └─ Generation               ← Tool-calling 멀티턴
        name: "invoke_agent {agent}"
        metadata: {step, fallback, tools_used, ...}
```

---

## 3. Trace 이름 규칙

**포맷**: `{workflow}.{action}`

| 상황 | Trace Name | 설명 |
|------|-----------|------|
| 스토리보드 신규 생성 | `storyboard.generate` | 처음부터 파이프라인 실행 |
| 스토리보드 재개 | `storyboard.resume` | Human/Concept Gate 이후 재개 |

**구현 방법**: LangFuse v3 `CallbackHandler`는 `run_name`을 지원하지 않는다.
`_langfuse_client.trace()`로 명시적 Trace를 생성한 뒤, 그 위에 Root Span과 CallbackHandler를 연결한다.

```python
# create_langfuse_handler() 내부
trace = _langfuse_client.trace(
    id=trace_id,
    name=f"{workflow}.{action}",   # "storyboard.generate"
    session_id=session_id,
)
root_span = trace.span(name=f"pipeline.{action}")
```

---

## 4. Root Span 이름 규칙

**포맷**: `pipeline.{action}`

| 상황 | Root Span Name |
|------|---------------|
| 신규 생성 | `pipeline.generate` |
| 재개 | `pipeline.resume` |

`create_langfuse_handler()`에 `action` 파라미터를 추가하여 호출자가 결정한다.

---

## 5. Generation 이름 규칙

### 5-1. Operation 분류

| Operation | 용도 | 해당 노드 |
|-----------|------|----------|
| `generate_content` | 콘텐츠 생성 (대본, 디자인 등) | director, writer, tts_designer, sound_designer, location_planner, explain, revise_expand |
| `evaluate` | 평가/리뷰/검증 | review, copyright_reviewer, director_checkpoint |
| `invoke_agent` | Tool-calling 멀티턴 에이전트 | cinematographer, research |

**경계 케이스**: `director_checkpoint`는 retry 시에도 `evaluate`를 유지한다. Operation은 **노드의 역할**로 결정하며, 개별 호출의 성격으로 바꾸지 않는다.

### 5-2. Generation 이름 매핑 (전체)

**포맷**: `{operation} {agent}` (하위 분류 시 `{operation} {agent}.{sub}`)

| 노드 | AS-IS | TO-BE | metadata |
|------|-------|-------|----------|
| director_plan | `director_plan` | `generate_content director_plan` | — |
| director | `director_step_{N}` | `generate_content director` | `{step: N}` |
| director (retry) | `director_step_{N}_retry` | `generate_content director` | `{step: N, retry: true}` |
| director_checkpoint | `director_checkpoint` | `evaluate director_checkpoint` | — |
| director_checkpoint (retry) | `director_checkpoint_retry` | `evaluate director_checkpoint` | `{retry: true}` |
| writer | `writer_planning` | `generate_content writer` | — |
| review (통합) | `review_unified_evaluate` | `evaluate review` | `{mode: "unified"}` |
| review (Gemini) | `review_gemini_evaluate` | `evaluate review` | `{mode: "gemini"}` |
| review (narrative) | `review_narrative_evaluate` | `evaluate review` | `{mode: "narrative"}` |
| review (self-reflect) | `review_self_reflect` | `evaluate review` | `{mode: "self_reflect"}` |
| location_planner | `location_planner` | `generate_content location_planner` | — |
| sound_designer | `sound_designer` | `generate_content sound_designer` | — |
| tts_designer | `tts_designer` | `generate_content tts_designer` | — |
| explain | `explain` | `generate_content explain` | — |
| copyright_reviewer | `copyright_reviewer` | `evaluate copyright_reviewer` | — |
| revise_expand | `revise_scene_expand` | `generate_content revise_expand` | — |
| research (분석) | `research_analyze_references` | `generate_content research.analyze` | — |
| research (tool-calling) | `research_tool_calling_step_{N}` | `invoke_agent research` | `{step: N}` |
| cinematographer (tool) | `cinematographer_tool_calling_step_{N}` | `invoke_agent cinematographer` | `{step: N}` |
| cinematographer (retry) | `cinematographer_direct_retry` | `generate_content cinematographer` | `{retry: true}` |
| cinematographer (fallback) | `cinematographer_tool_calling_fallback` | `invoke_agent cinematographer` | `{fallback: true}` |
| cinematographer_competition | `cinematographer_{role}_step_{N}` | `invoke_agent cinematographer.{role}` | `{step: N}` |
| cinematographer_competition (retry) | `cinematographer_{role}_direct_retry` | `generate_content cinematographer.{role}` | `{retry: true}` |

> **허용 role 값**: `bold`, `safe` (2종). 추가 시 이 테이블과 metadata 섹션을 함께 갱신한다.

### 5-3. GeminiProvider PROHIBITED fallback

`GeminiProvider`가 `PROHIBITED_CONTENT`로 차단 시 fallback 모델로 재시도한다.
이때 Generation 이름은 **원래 이름을 유지**하고, metadata로 fallback 정보를 기록한다.

| 함수 | AS-IS | TO-BE | metadata |
|------|-------|-------|----------|
| `generate()` fallback | `{step_name}_fallback` | `{step_name}` (변경 없음) | `{prohibited_fallback: true, fallback_model: "gemini-2.0-flash"}` |
| `generate_with_tools()` fallback | `{step_name}_fallback` | `{step_name}` (변경 없음) | `{prohibited_fallback: true, fallback_model: "gemini-2.0-flash"}` |

### 5-4. call_with_tools / call_direct 공통 유틸

| 함수 | AS-IS | TO-BE | metadata |
|------|-------|-------|----------|
| `call_with_tools` 루프 | `{trace_name}_step_{N}` | `invoke_agent {trace_name}` | `{step: N}` |
| `call_with_tools` fallback | `{trace_name}_fallback` | `invoke_agent {trace_name}` | `{fallback: true, reason: "no_text_response"}` |
| `call_direct` | `{trace_name}` (그대로) | `generate_content {trace_name}` | — |

### 5-5. _production_utils.py metadata 머지 패턴

`run_production_step()`은 기존 `metadata={"template": template_name}`에 step/retry 정보를 머지한다.

```python
# _production_utils.py
base_metadata = {"template": template_name}
if attempt > 1:
    base_metadata["retry"] = True
    base_metadata["attempt"] = attempt
# provider.generate(step_name=step_name, metadata=base_metadata, ...)
```

---

## 6. Metadata 표준 키

고카디널리티 정보는 이름이 아닌 metadata에 기록한다.

| Key | Type | 설명 | 예시 |
|-----|------|------|------|
| `step` | `int` | 멀티턴/ReAct 스텝 번호 | `1`, `2`, `3` |
| `retry` | `bool` | 재시도 여부 | `true` |
| `attempt` | `int` | 재시도 횟수 (1부터) | `2` |
| `fallback` | `bool` | 도구 없이 폴백 호출 (call_with_tools) | `true` |
| `reason` | `str` | fallback 사유 | `"no_text_response"` |
| `prohibited_fallback` | `bool` | PROHIBITED_CONTENT fallback | `true` |
| `fallback_model` | `str` | fallback에 사용된 모델 | `"gemini-2.0-flash"` |
| `mode` | `str` | 평가 모드 (review 노드) | `"unified"`, `"gemini"` |
| `role` | `str` | 경쟁 에이전트 역할 | `"bold"`, `"safe"` |
| `tools_used` | `list[str]` | 사용된 도구 이름 목록 | `["validate_danbooru_tag"]` |
| `template` | `str` | LangFuse 프롬프트 템플릿명 | `"pipeline/director"` |

---

## 7. 금지 사항

| 규칙 | 예시 (금지) | 이유 |
|------|-----------|------|
| 이름에 step 번호 포함 | `director_step_3` | 고카디널리티 → 그룹핑 불가 |
| 이름에 retry/fallback 접미사 | `cinematographer_direct_retry` | metadata로 분리 |
| 동사(operation) 없는 이름 | `sound_designer` | 무엇을 하는지 불명확 |
| SDK 기본값 사용 | `LangGraph` | 워크플로우 구분 불가 |
| 언더스코어로 계층 표현 | `review_narrative_evaluate` | dot namespace 사용 |

---

## 8. 구현 위치 (변경 우선순위 순)

| 순서 | 파일 | 역할 |
|------|------|------|
| 1 | `services/agent/observability.py` | Trace/Root Span 생성, `trace_llm_call()` |
| 2 | `services/llm/gemini_provider.py` | PROHIBITED fallback `_fallback` 접미사 제거 |
| 3 | `services/agent/tools/base.py` | `call_with_tools()`, `call_direct()` 공통 유틸 |
| 4 | `services/agent/nodes/_production_utils.py` | `run_production_step()` metadata 머지 |
| 5 | `services/agent/nodes/*.py` | 노드별 `step_name` / `trace_name` 전달 |
| 6 | `services/agent/cinematographer_competition.py` | 경쟁 에이전트 `trace_name` |
| 7 | `routers/scripts.py` | `_build_config()` — action 파라미터 전달 |

---

## 9. 신규 노드 추가 체크리스트

1. Operation 분류 결정: `generate_content` / `evaluate` / `invoke_agent`
2. Agent 이름 결정: 노드명 기반, 하위 분류 시 dot namespace
3. `step_name` 또는 `trace_name`에 `"{operation} {agent}"` 포맷 적용
4. 가변 정보(step, retry, fallback)는 `metadata` dict로 전달
5. GeminiProvider의 PROHIBITED fallback도 새 포맷을 따르는지 확인
6. 이 문서의 매핑 테이블에 추가
