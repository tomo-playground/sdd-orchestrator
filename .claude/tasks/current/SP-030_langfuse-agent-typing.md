---
id: SP-030
priority: P1
scope: backend
branch: feat/SP-030-langfuse-agent-typing
created: 2026-03-21
status: running
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
LangFuse 트레이스 타입 분류 — AGENT/TOOL/CHAIN 타입 적용으로 Agentic Pipeline 가시성 확보

## 왜
- 21개 노드 LangGraph Agentic Pipeline인데 LangFuse에 GENERATION과 SPAN만 기록
- AGENT(노드별 에이전트), TOOL(Function Calling), CHAIN(라우팅 경로) 타입 미사용
- LangFuse 대시보드에서 파이프라인 흐름 추적 불가

## 현재 상태
| LangFuse 타입 | 사용 | 기록 내용 |
|:---:|:---:|---|
| GENERATION | 19개 | Gemini API 호출 |
| SPAN | 10개 | LangChain CallbackHandler 자동 |
| AGENT | 0 | 미사용 |
| TOOL | 0 | 미사용 |
| CHAIN | 0 | 미사용 |

## 구현 범위

### 1. AGENT 타입 — 노드별 에이전트 추적
- Director, Writer, Cinematographer, Critic 등 21개 노드
- 각 노드 실행을 `start_observation(as_type="agent")` 래핑
- input: state 요약, output: 결과 요약

### 2. TOOL 타입 — Function Calling 추적
- Gemini Function Calling 도구 (search_compositions, analyze_reference 등)
- `as_type="tool"` — 도구명, input params, output result

### 3. CHAIN 타입 — 라우팅 경로 추적
- 조건부 라우팅 (routing.py)의 결정 경로
- 어떤 노드에서 어떤 노드로 분기했는지 기록

### 4. 계층 구조
```
Trace: storyboard.generate
  └── AGENT: director
       └── GENERATION: generate_content director
  └── AGENT: writer
       └── GENERATION: generate_content writer
  └── CHAIN: route_after_writer → cinematographer
  └── AGENT: cinematographer
       └── GENERATION: generate_content cinematographer
       └── TOOL: search_compositions
  └── AGENT: finalize
```

## 관련 파일
- `backend/services/agent/observability.py` — trace_llm_call, trace_context
- `backend/services/agent/nodes/*.py` — 21개 노드
- `backend/services/agent/routing.py` — 라우팅 로직
- `backend/services/agent/tools/*.py` — Function Calling 도구

## 완료 기준 (DoD)
- [ ] 주요 노드(Director, Writer, Cinematographer, Finalize) AGENT 타입 기록
- [ ] Gemini Function Calling TOOL 타입 기록
- [ ] 라우팅 분기 CHAIN 타입 기록
- [ ] LangFuse 대시보드에서 파이프라인 흐름 시각화 확인
- [ ] 기존 테스트 통과
- [ ] 성능 영향 최소 (LangFuse 비활성 시 no-op)

## 제약
- LangFuse SDK v3 API 사용 (`start_observation(as_type=...)`)
- 기존 GENERATION 추적 유지 (하위 호환)
- LangFuse 비활성 시 graceful degradation 유지
