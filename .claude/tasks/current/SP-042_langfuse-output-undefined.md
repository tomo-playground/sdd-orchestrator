---
id: SP-042
priority: P1
scope: backend
branch: feat/SP-042-langfuse-trace-cleanup
created: 2026-03-21
status: pending
depends_on:
label: bug
reviewer: stopper2008
assignee: stopper2008
---

## 무엇을
LangFuse 트레이스 품질 개선 — output undefined 수정 + 이중 observation 제거 + CHAIN 중복 정리

## 왜
최신 파이프라인 트레이스 분석 결과 (storyboard.generate, 628초, $0.285):
- **200개 observation** 중 이중 생성이 대량 발생 → LangFuse 대시보드 읽기 불가
- **16개 AGENT observation에 output undefined** → 노드 결과 추적 불가
- **route_* CHAIN이 전부 x2 중복** → 노이즈
- 디버깅/비용 분석/품질 추적이 사실상 불가능한 상태

### 트레이스 데이터 근거

```
=== 모델별 비용 ===
gemini-2.5-pro       16x   95,434tok  $0.1583 (59.1%)  410s
gemini-2.5-flash     26x  260,021tok  $0.1012 (37.8%)  362s
gemini-2.0-flash      4x   63,931tok  $0.0085 ( 3.2%)   41s

=== 이중 Observation (심각) ===
review               AGENT      x16  ← 8회 실행인데 16개 (이중 래핑)
route_after_review   CHAIN      x16  ← 라우팅 체인도 2배
writer               AGENT      x6   ← 3회 실행인데 6개
director_checkpoint  AGENT      x4   ← 2회 실행인데 4개

=== AGENT output undefined: 16건 ===
writer, review, cinematographer, director, finalize
```

## 근본 원인 3개

### Bug 1: `trace_context` span output 미기록 (3곳)
`observability.py`의 `trace_context()`가 span을 열고 `yield`만 하고 output 기록 안 함.

| 파일 | trace 이름 |
|------|-----------|
| `services/scripts/topic_analysis.py` L83 | `topic.analyze` |
| `routers/video.py` L485 | `video.extract_caption` |
| `routers/video.py` L542 | `video.extract_hashtags` |

### Bug 2: `@with_agent_trace` 이중 래핑 + output 미기록 (6곳)
`_wrap_node()`이 외부 AGENT span을 생성 + output 기록.
`@with_agent_trace`가 내부 AGENT span을 추가 생성 + output 미기록.
→ 동일 이름 AGENT x2, 내부 output은 undefined.

| 노드 | `@with_agent_trace` 위치 | `_wrap_node` 등록 |
|------|--------------------------|------------------|
| director_plan | L67 | script_graph.py L107 |
| writer | L160 | L114 |
| review | L297 | L115 |
| director | L43 | L122 |
| cinematographer | L125 | L118 |
| finalize | L962 | L124 |

### Bug 3: GENERATION output undefined (5건)
`writer` GENERATION 4건 + `invoke_agent cinematographer.contrast` 1건에서 output 미기록.
writer 내부 planning/반복 호출, cinematographer tool-calling agent 응답 누락.

| 이름 | 건수 | 추정 원인 |
|------|------|----------|
| `writer` GENERATION | 4건 | writer 내부 sub-call에서 `llm.record()` 누락 |
| `invoke_agent cinematographer.contrast` | 1건 | tool-calling agent 응답 미기록 |

### Bug 4: route_* CHAIN 중복 (LangGraph + observability 이중 기록)
`route_after_review` x16, `route_after_writer` x6 등 라우팅 CHAIN도 2배 중복.
LangGraph 자체 트레이싱 + observability의 `trace_chain` 양쪽에서 기록.

## 실패 테스트 (TDD)

구현 전 작성 → RED 확인 → 구현 → GREEN 확인 순서로 진행.

### Bug 1: trace_context span output 미기록
```python
# tests/test_observability_trace_context.py
async def test_trace_context_span_output_is_set():
    """trace_context yield 후 span.output이 None이 아닌지 확인."""
    captured = {}

    async with trace_context("test.op", input_data={"x": 1}) as span:
        # 호출처에서 output을 기록
        if span:
            span.update(output={"result": "ok"})
        captured["span"] = span

    assert captured["span"] is not None, "span 객체가 yield되어야 함"
    # span.output이 None이 아님 — LangFuse SDK mock으로 검증
    assert captured["span"].output is not None, "span.output이 기록되어야 함"
```

### Bug 2: @with_agent_trace 이중 래핑
```python
# tests/test_observability_double_wrap.py
async def test_no_duplicate_agent_observation_after_node_run():
    """노드 실행 후 동일 이름 AGENT observation이 1개만 생성되는지 확인."""
    observations = []

    # LangFuse client mock — create_span 호출을 수집
    with patch("services.agent.observability.langfuse_client") as mock_lf:
        mock_lf.span.side_effect = lambda **kw: observations.append(kw) or MagicMock()
        await writer_node(mock_state, config=None)

    agent_obs = [o for o in observations if o.get("name") == "writer"]
    assert len(agent_obs) == 1, f"writer AGENT observation이 1개여야 함, 실제: {len(agent_obs)}"
```

### Bug 3: GENERATION output undefined
```python
# tests/test_observability_generation_output.py
async def test_writer_generation_output_is_not_none():
    """writer/cinematographer GENERATION의 output이 None이 아닌지 확인."""
    generation_outputs = []

    with patch("services.agent.observability.langfuse_client") as mock_lf:
        def capture_generation(**kw):
            gen = MagicMock()
            gen.name = kw.get("name", "")
            generation_outputs.append(gen)
            return gen
        mock_lf.generation.side_effect = capture_generation

        await writer_node(mock_state, config=None)

    for gen in generation_outputs:
        assert gen.output is not None, f"GENERATION '{gen.name}'의 output이 None이면 안 됨"
```

## 완료 기준 (DoD)

### Part A: trace_context output 기록
- [ ] **실패 테스트 → GREEN**: `test_trace_context_span_output_is_set` 통과
- [ ] `trace_context()`가 span 객체를 yield하도록 수정
- [ ] 3개 호출처에서 `span.update(output=...)` 호출
- [ ] LangFuse에서 topic.analyze 등의 output 표시 확인

### Part B: @with_agent_trace 이중 래핑 제거
- [ ] **실패 테스트 → GREEN**: `test_no_duplicate_agent_observation_after_node_run` 통과
- [ ] 6개 노드에서 `@with_agent_trace` 데코레이터 **제거**
- [ ] import 정리 (`from services.agent.observability import with_agent_trace` 제거)
- [ ] LangFuse에서 동일 이름 AGENT observation이 **1개만** 생성 확인
- [ ] output에 `{"updated_keys": [...]}` 정상 표시 확인

### Part C: GENERATION output undefined 수정 (5건)
- [ ] **실패 테스트 → GREEN**: `test_writer_generation_output_is_not_none` 통과
- [ ] `writer` 내부 sub-call (planning 등)에서 `llm.record()` 누락 지점 확인 + 수정
- [ ] `invoke_agent cinematographer.contrast` tool-calling agent 응답 기록 확인 + 수정
- [ ] LangFuse에서 GENERATION output 0% undefined 확인

### Part D: route_* CHAIN 중복 조사 + 정리
- [ ] `trace_chain` 호출이 LangGraph 자체 트레이싱과 중복되는지 확인
- [ ] 중복 원인 파악 후 한쪽 제거 (LangGraph 측 또는 observability 측)
- [ ] 정리 후 observation 수가 절반 수준으로 감소 확인

### Part E: 검증
- [ ] pytest 통과
- [ ] 린트 통과
- [ ] 실제 파이프라인 실행 후 LangFuse 트레이스 검증:
  - observation 수 200개 → ~100개 이하
  - 모든 AGENT에 output 표시
  - 이중 이름 observation 0건

## 제약
- `observability.py` + 6개 노드 + 3개 호출처 + `script_graph.py` = 최대 11개 파일
- `_wrap_node()`의 output 기록 로직 변경 안 함 (정상 동작)
- `trace_llm_call`의 GENERATION output 기록 변경 안 함 (정상)
- CHAIN 정리 시 LangGraph 내장 트레이싱과 충돌하지 않도록 주의

## 힌트

### Part A: trace_context에서 span yield
```python
# AS-IS: yield만 하고 output 없음
async with trace_context("topic.analyze", input_data=...) as ctx:
    ...  # ctx는 None

# TO-BE: span 객체를 yield
async with trace_context("topic.analyze", input_data=...) as span:
    result = await llm_call(...)
    if span:
        span.update(output={"status": "recommend", "duration": 30})
```

### Part B: 데코레이터 제거 (1줄 삭제)
```python
# AS-IS
@with_agent_trace("writer")
async def writer_node(state, config=None):

# TO-BE
async def writer_node(state, config=None):
```

### Part C: CHAIN 중복 조사
- `observability.py`의 `trace_chain` 사용처 확인
- `script_graph.py`의 `_wrap_node`에서 routing 노드도 래핑하는지 확인
- LangGraph의 `astream(stream_mode="updates")`가 routing 이벤트를 emit하는지 확인
