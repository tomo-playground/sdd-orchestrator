## 상세 설계 (How)

### DoD-A: 노드 시작 이벤트

**구현방법**:
`stream_mode="updates"` → `stream_mode=["updates", "custom"]` 변경.
`custom` 모드 + `get_stream_writer()`로 각 노드 진입 시 시작 이벤트를 직접 발행한다.
LangGraph 내부 debug 이벤트 형식에 의존하지 않고 이벤트 구조를 완전 제어한다.

**1) 데코레이터 추가** (`backend/services/agent/observability.py`):
```python
import functools
from langgraph.config import get_stream_writer

def with_starting_event(name: str | None = None):
    """노드 진입 시 custom stream으로 starting 이벤트를 자동 발행하는 데코레이터."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            node_name = name or fn.__name__.replace("_node", "")
            try:
                writer = get_stream_writer()
                writer({"type": "node_starting", "node": node_name})
            except Exception:
                pass  # stream_writer 미사용 컨텍스트(테스트 등)에서 무시
            return await fn(*args, **kwargs)
        return wrapper
    return decorator
```

**2) 각 노드에 데코레이터 적용** (기존 노드 파일 변경 없이 `script_graph.py`에서 래핑):
```python
# script_graph.py — 그래프 빌드 시 래핑
from services.agent.observability import with_starting_event

graph.add_node("director_plan", with_starting_event("director_plan")(director_plan_node))
graph.add_node("writer", with_starting_event("writer")(writer_node))
# ... 모든 노드에 동일 적용
```
→ 개별 노드 파일 수정 불필요. `script_graph.py` 1곳에서 일괄 래핑.

**3) `stream_graph_events()` 이벤트 파싱** (`_scripts_sse.py`):
혼합 모드에서 이벤트는 `tuple(mode, data)` 형태:
- `("custom", {"type": "node_starting", "node": "writer"})` → 시작 이벤트
- `("updates", {"writer": {...}})` → 완료 이벤트 (기존)

```python
stream = graph.astream(graph_input, config, stream_mode=["updates", "custom"])
# ...
event = pending.result()  # tuple(mode, data)
mode, data = event

if mode == "custom" and isinstance(data, dict) and data.get("type") == "node_starting":
    node_name = data["node"]
    yield _build_starting_payload(node_name, thread_id)
    pending = asyncio.ensure_future(stream.__anext__())
    continue

if mode == "updates" and isinstance(data, dict):
    for node_name, node_output in data.items():
        # 기존 로직 유지 (build_node_payload 등)
```

**4) `_build_starting_payload()` 신규 함수**:
```python
def _build_starting_payload(node_name: str, thread_id: str | None) -> str:
    meta = NODE_META.get(node_name, {"label": node_name, "percent": 50})
    starting_percent = max(1, meta["percent"] - 5)
    payload = {
        "node": node_name,
        "label": meta["label"],
        "percent": starting_percent,
        "status": "starting",
        "thread_id": thread_id,
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
```

**5) NODE_META 누락 노드 추가**:
- `"location_planner": {"label": "로케이션 설계", "percent": 22}`
- `"director_checkpoint": {"label": "연출 판단", "percent": 58}`

**Frontend 변경**:

`sseProcessor.ts` — `processSSEStream()`에서 `status === "starting"` **early return**:
```typescript
// updatePipelineSteps 호출 전에 early return (step 상태 변경 방지)
if (event.status === "starting") {
    return {
        ...prev,
        progress: { node: event.node, label: event.label, percent: event.percent },
    };
}
// 이후 기존 로직 (updatePipelineSteps 등)
```

`useStreamingPipeline.ts` — `onNodeEvent()`에서 starting 이벤트 시 ProgressBar만 갱신:
```typescript
if (event.status === "starting") {
    setActiveProgress({ node: event.node, label: event.label, percent: event.percent });
    return; // Chat 메시지 생성 안 함
}
```

**동작정의**:
- 파이프라인 연결 직후 director_plan 시작 이벤트가 1초 이내 표시
- ProgressBar: "디렉터 계획 중..." → (완료 시) "대본 생성 중..." 순서
- PipelineStepCard는 완료 시에만 생성 (시작 시에는 Chat에 카드 안 뜸)

**엣지케이스**:
- custom 이벤트에 NODE_META 미등록 노드 → fallback `{"label": node_name, "percent": 50}`
- `get_stream_writer()`를 단위 테스트에서 호출 시 → `try/except`로 무시 (데코레이터가 방어)
- heartbeat 루프: tuple unpacking 후 mode 분기 → custom은 즉시 yield + continue, updates는 기존 로직
- 기존 heartbeat 테스트의 `_FakeAsyncIter`: `("updates", {...})` tuple을 반환하도록 수정

**영향범위**:
- `backend/services/agent/observability.py`: `with_starting_event()` 데코레이터 추가
- `backend/services/agent/script_graph.py`: 노드 등록 시 데코레이터 래핑
- `backend/routers/_scripts_sse.py`: stream_mode 변경, tuple 파싱 분기, `_build_starting_payload()`, NODE_META 2개 추가
- `frontend/app/hooks/scriptEditor/sseProcessor.ts`: starting early return
- `frontend/app/hooks/useStreamingPipeline.ts`: starting 이벤트 처리
- `frontend/app/types/index.ts`: ScriptStreamEvent.status에 "starting" 추가

**테스트전략**:
- Backend: `_build_starting_payload()` 단위 테스트
- Backend: stream_mode=["updates", "custom"] 이벤트 파싱 단위 테스트 (mock stream, tuple 형식)
- Backend: 기존 heartbeat 테스트를 tuple 형식으로 수정 후 regression 확인
- Backend: `with_starting_event()` 데코레이터가 writer를 호출하는지 단위 테스트

**Out of Scope**:
- 노드 내부 서브스텝 진행 (Gemini 호출 중 토큰 단위 스트리밍)
- percent의 실시간 애니메이션 (CSS transition으로 자연스럽게 보이는 것은 기존 ProgressBar 기능)

---

### DoD-B: LangFuse 트레이스 링크

**구현방법**:

`backend/services/agent/observability.py`에서 `get_trace_url()` 함수 추가:
```python
def get_trace_url() -> str | None:
    trace_id = _current_trace_id.get(None)
    if not trace_id or not LANGFUSE_ENABLED:
        return None
    return f"{LANGFUSE_BASE_URL}/trace/{trace_id}"
```

`stream_graph_events()` — 스트림 종료 시점(completion/error)에 `trace_url` 포함:

1. **정상 완료** (finalize 후 최종 payload):
```python
final_payload["trace_url"] = get_trace_url()
```

2. **에러 발생** (except 블록):
```python
error_payload["trace_url"] = get_trace_url()
```

3. **Interrupt** (기존 trace_id 필드 유지 + trace_url 추가):
```python
interrupt_payload["trace_url"] = get_trace_url()
# trace_id 필드는 하위 호환 유지
```

**Frontend 변경**:

`CompletionCard.tsx` — trace_url이 있으면 링크 버튼 표시:
```tsx
{traceUrl && (
    <a href={traceUrl} target="_blank" rel="noopener noreferrer">
        LangFuse에서 상세 보기
    </a>
)}
```

`ErrorCard.tsx` — 동일 패턴으로 trace 링크 표시.

`ScriptStreamEvent` 타입에 `trace_url?: string` 추가.
`processSSEStream()`에서 completion/error 시 trace_url을 Chat 메시지 데이터에 포함.

**동작정의**:
- LangFuse 활성 시: 완료/에러 카드에 "LangFuse에서 상세 보기" 링크 표시
- LangFuse 비활성 시: trace_url = null → 링크 미표시
- URL 형식: `{LANGFUSE_BASE_URL}/trace/{trace_id}`

**엣지케이스**:
- LANGFUSE_ENABLED=false → trace_url=None → UI 링크 없음 (graceful)
- trace_id 미생성 (observability 초기화 실패) → None 반환
- 사용자가 외부 네트워크에서 접근 시 localhost URL 접근 불가 → 향후 LANGFUSE_BASE_URL을 외부 URL로 변경하면 해결

**영향범위**:
- `backend/services/agent/observability.py`: `get_trace_url()` 추가
- `backend/routers/_scripts_sse.py`: completion/error payload에 trace_url 추가
- `frontend/app/components/chat/messages/CompletionCard.tsx`: 링크 버튼
- `frontend/app/components/chat/messages/ErrorCard.tsx`: 링크 버튼
- `frontend/app/types/index.ts`: trace_url 필드

**테스트전략**:
- Backend: get_trace_url() 활성/비활성 단위 테스트
- Backend: completion/error payload에 trace_url 포함 확인

**Out of Scope**:
- LangFuse 외부 노출 설정 (인프라)
- trace 상세 페이지 커스터마이징

---

### DoD-C: 품질

**테스트전략**:
- 기존 SSE 스트리밍 테스트(heartbeat 등) tuple 형식으로 수정 후 regression 확인
- ruff lint 통과 확인
- Frontend build 통과 확인

---

### 변경 파일 요약 (10개, 제약 이내)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 1 | `backend/services/agent/observability.py` | `with_starting_event()` 데코레이터 + `get_trace_url()` |
| 2 | `backend/services/agent/script_graph.py` | 노드 등록 시 데코레이터 래핑 |
| 3 | `backend/routers/_scripts_sse.py` | stream_mode 변경, tuple 파싱 분기, `_build_starting_payload()`, NODE_META 추가, trace_url |
| 4 | `backend/tests/test_sp053_pipeline_progress.py` | 신규 테스트 |
| 5 | `frontend/app/types/index.ts` | ScriptStreamEvent에 starting, trace_url 추가 |
| 6 | `frontend/app/hooks/scriptEditor/sseProcessor.ts` | starting early return + trace_url 전달 |
| 7 | `frontend/app/hooks/useStreamingPipeline.ts` | starting 이벤트 처리 |
| 8 | `frontend/app/components/chat/messages/CompletionCard.tsx` | trace 링크 |
| 9 | `frontend/app/components/chat/messages/ErrorCard.tsx` | trace 링크 |
| 10 | `backend/tests/test_sse_heartbeat.py` | 기존 테스트 tuple 형식 수정 (regression) |
