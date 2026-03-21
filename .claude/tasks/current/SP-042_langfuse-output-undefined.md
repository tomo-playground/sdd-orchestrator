---
id: SP-042
priority: P1
scope: backend
branch: feat/SP-042-langfuse-output-undefined
created: 2026-03-21
status: pending
depends_on:
label: bug
reviewer: stopper2008
assignee: stopper2008
---

## 무엇을
LangFuse observation output `undefined` 버그 수정 — trace_context + with_agent_trace 2건

## 왜
LangFuse 대시보드에서 `topic.analyze` 등의 Output이 `undefined`로 표시.
트레이스 분석/디버깅 시 노드 결과를 확인할 수 없어 파이프라인 품질 추적이 불가능.

## 근본 원인 2개

### Bug 1: `trace_context` span output 미기록 (3곳)
`observability.py` L82-120의 `trace_context()`가 span을 열고 `yield`만 하고, 종료 시 output을 기록하지 않음.

영향 범위:
- `services/scripts/topic_analysis.py` L83 — `topic.analyze`
- `routers/video.py` L485 — `video.extract_caption`
- `routers/video.py` L542 — `video.extract_hashtags`

### Bug 2: `@with_agent_trace` 데코레이터 output 미기록 + 이중 AGENT span (6곳)
`with_agent_trace` wrapper가 `trace_agent()`를 `as agent_obs` 없이 호출 → 노드 반환값을 span에 기록 안 함.
동시에 `script_graph.py`의 `_wrap_node()`도 같은 노드를 감싸서 **동일 이름 AGENT observation 2개** 생성.

영향 범위 (이중 래핑):
- `director_plan.py` L67 — `@with_agent_trace("director_plan")`
- `writer.py` L160 — `@with_agent_trace("writer")`
- `review.py` L297 — `@with_agent_trace("review")`
- `director.py` L43 — `@with_agent_trace("director")`
- `cinematographer.py` L125 — `@with_agent_trace("cinematographer")`
- `finalize.py` L962 — `@with_agent_trace("finalize")`

## 완료 기준 (DoD)

### Part A: trace_context output 기록
- [ ] `trace_context()`가 yield로 반환된 결과를 span output에 기록
  - 방법: `yield` → generator의 `send()` 패턴 또는 output 콜백 인자 추가
  - 또는 호출처에서 `span.update(output=...)` 직접 호출 (단순)
- [ ] `topic.analyze`, `video.extract_caption`, `video.extract_hashtags` 3곳 수정
- [ ] LangFuse에서 output 표시 확인

### Part B: with_agent_trace 이중 래핑 제거
- [ ] `@with_agent_trace` 데코레이터를 6개 노드에서 **제거**
  - `_wrap_node()`이 이미 외부 AGENT span을 생성하고 output도 기록하므로 중복
- [ ] LangFuse에서 동일 이름 AGENT observation이 1개만 생성되는지 확인
- [ ] 기존 트레이스 구조 regression 없음

### Part C: 검증
- [ ] pytest 통과
- [ ] 린트 통과
- [ ] 실제 파이프라인 실행 후 LangFuse 트레이스에서 output 확인

## 제약
- `observability.py` + 6개 노드 파일 + 3개 호출처 = 최대 10개 파일
- `_wrap_node()`의 output 기록 로직은 변경하지 않음 (이미 정상 동작)
- trace_llm_call의 GENERATION output 기록은 변경하지 않음 (이미 정상)

## 힌트

### Part A 구현 패턴 (가장 단순한 방법)
호출처에서 직접 output 기록:
```python
async with trace_context("topic.analyze", input_data={"topic": topic}) as span:
    # ... LLM 호출 ...
    if span:
        span.update(output={"status": result.status, "duration": result.duration})
```
→ `trace_context`가 span 객체를 yield하도록 수정

### Part B 구현
6개 노드에서 `@with_agent_trace("...")` 데코레이터 한 줄 삭제 + import 정리.
`_wrap_node()`이 모든 노드를 이미 감싸므로 기능 손실 없음.
