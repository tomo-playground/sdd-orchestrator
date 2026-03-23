## 상세 설계 (How)

### DoD-A: 노드 시작 이벤트

**구현방법**:
`stream_mode="updates"` → `stream_mode=["updates", "debug"]` 변경.
혼합 모드에서 각 이벤트는 `tuple(stream_mode, data)` 형태로 반환된다.

- `("debug", {"type": "task_started", "payload": {"name": "writer", ...}})` → 노드 시작
- `("updates", {"writer": {...}})` → 노드 완료 (기존과 동일)

`stream_graph_events()`에서 튜플을 분기 처리:
```python
async for event in stream:
    mode, data = event  # 혼합 모드 → 튜플
    if mode == "debug" and data.get("type") == "task_started":
        node_name = data["payload"]["name"]
        yield build_starting_payload(node_name, thread_id)
    elif mode == "updates":
        for node_name, node_output in data.items():
            # 기존 로직 유지
```

`build_starting_payload()` 신규 함수:
```python
def build_starting_payload(node_name: str, thread_id: str | None) -> str:
    meta = NODE_META.get(node_name, {"label": node_name, "percent": 50})
    # 시작 percent = 이전 노드 percent + 1 (점프 완화)
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

NODE_META에 누락 노드 2개 추가:
- `"location_planner": {"label": "로케이션 설계", "percent": 22}`
- `"director_checkpoint": {"label": "연출 판단", "percent": 58}`

**Frontend 변경**:

`sseProcessor.ts` — `processSSEStream()`에서 `status === "starting"` 분기 추가:
```typescript
if (event.status === "starting") {
    return {
        ...base,
        progress: { node: event.node, label: event.label, percent: event.percent },
        // pipelineSteps는 업데이트하지 않음 (완료 시에만)
    };
}
```

`useStreamingPipeline.ts` — `onNodeEvent()`에서 starting 이벤트 시 ProgressBar만 갱신:
```typescript
if (event.status === "starting") {
    setActiveProgress({ node: event.node, label: event.label, percent: event.percent });
    return; // Chat 메시지 생성 안 함
}
```

`ProgressBar.tsx` — status가 "starting"이면 라벨에 "시작 중..." 표시, 스피너 유지. 현재 이미 스피너가 있으므로 라벨만 즉시 갱신하면 체감 개선.

**동작정의**:
- 파이프라인 연결 직후 director_plan 시작 이벤트가 1초 이내 표시
- ProgressBar: "디렉터 계획 시작 중..." → (완료 시) "대본 생성 중..." 순서
- PipelineStepCard는 완료 시에만 생성 (시작 시에는 Chat에 카드 안 뜸)

**엣지케이스**:
- debug 이벤트에 NODE_META 미등록 노드 → fallback `{"label": node_name, "percent": 50}` (기존 로직)
- debug 이벤트 중 `task_started` 외 타입(`task_scheduled`, `task_result` 등) → 무시 (skip)
- stream_mode 리스트 미지원 LangGraph 버전 → 런타임 에러. 현재 0.3.0+ 확인됨

**영향범위**:
- `backend/routers/_scripts_sse.py`: stream_mode 변경 + 이벤트 파싱 분기 + `build_starting_payload()` 추가 + NODE_META 2개 추가
- `frontend/app/hooks/scriptEditor/sseProcessor.ts`: starting status 분기
- `frontend/app/hooks/useStreamingPipeline.ts`: starting 이벤트 처리
- `frontend/app/types/index.ts`: ScriptStreamEvent.status에 "starting" 추가

**테스트전략**:
- Backend: `stream_mode=["updates", "debug"]` 이벤트 파싱 단위 테스트 (mock stream)
- Backend: `build_starting_payload()` 단위 테스트
- Frontend: sseProcessor에서 starting 이벤트 처리 확인

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

3. **Interrupt** (기존 trace_id → trace_url로 통일):
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
- 기존 SSE 스트리밍 관련 테스트가 있으면 regression 확인
- ruff lint 통과 확인
- Frontend build 통과 확인

---

### 변경 파일 요약 (8개, 제약 10개 이하)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 1 | `backend/routers/_scripts_sse.py` | stream_mode 변경, 이벤트 파싱 분기, build_starting_payload(), NODE_META 추가 |
| 2 | `backend/services/agent/observability.py` | get_trace_url() 추가 |
| 3 | `backend/tests/test_sp053_pipeline_progress.py` | 신규 테스트 |
| 4 | `frontend/app/types/index.ts` | ScriptStreamEvent에 starting, trace_url 추가 |
| 5 | `frontend/app/hooks/scriptEditor/sseProcessor.ts` | starting 분기 + trace_url 전달 |
| 6 | `frontend/app/hooks/useStreamingPipeline.ts` | starting 이벤트 처리 |
| 7 | `frontend/app/components/chat/messages/CompletionCard.tsx` | trace 링크 |
| 8 | `frontend/app/components/chat/messages/ErrorCard.tsx` | trace 링크 |
