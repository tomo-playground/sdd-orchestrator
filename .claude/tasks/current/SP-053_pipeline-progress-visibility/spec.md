---
id: SP-053
priority: P2
scope: fullstack
branch: feat/SP-053-pipeline-progress-visibility
created: 2026-03-22
status: pending
depends_on:
label: feat
---

## 무엇을 (What)
파이프라인 실행 중 각 노드의 시작/진행 상태를 채팅 UI에 실시간으로 표시하고, 완료 후 LangFuse 트레이스 링크를 제공한다.

## 왜 (Why)
현재 LangGraph `stream_mode="updates"`는 노드 **완료 후**에만 이벤트를 보낸다. Writer가 Gemini를 호출하며 30초 걸리는 동안 ProgressBar만 멈춰 있어서 사용자는 파이프라인이 무엇을 하고 있는지 알 수 없다. "파이프라인 연결 중... 0%"에서 첫 노드 완료까지 아무 피드백이 없는 것이 핵심 문제.

## 완료 기준 (DoD)

### A. 노드 시작 이벤트
- [ ] 각 노드 진입 시 `status: "starting"` SSE 이벤트를 즉시 전송한다 (노드 완료 전)
- [ ] 프론트엔드 ProgressBar에 "리서치 진행 중...", "대본 작성 중..." 등 시작 상태를 즉시 반영한다
- [ ] PipelineStepCard에 노드 시작 시 스피너(또는 펄스 애니메이션)를 표시하고, 완료 시 체크 아이콘으로 전환한다
- [ ] 파이프라인 연결 직후 첫 노드(director_plan) 시작 이벤트가 1초 이내에 표시된다

### B. LangFuse 트레이스 링크
- [ ] 파이프라인 완료(또는 에러) 시 SSE 이벤트에 `trace_url` 필드를 포함한다
- [ ] CompletionCard(또는 ErrorCard)에 "LangFuse에서 상세 보기" 링크를 표시한다
- [ ] trace_url은 `{LANGFUSE_HOST}/trace/{trace_id}` 형식이다

### C. 품질
- [ ] 기존 SSE 스트리밍 테스트 regression 없음
- [ ] 린트 통과

## 영향 분석

- 관련 함수/파일:
  - `backend/routers/_scripts_sse.py` — `stream_graph_events()`, `build_node_payload()`
  - `backend/services/agent/observability.py` — `create_langfuse_handler()`, trace_id 관리
  - `frontend/app/hooks/useStreamingPipeline.ts` — `onNodeEvent()`
  - `frontend/app/hooks/scriptEditor/sseProcessor.ts` — SSE 파싱
  - `frontend/app/components/chat/messages/PipelineStepCard.tsx` — 노드 상태 렌더링
  - `frontend/app/components/chat/ProgressBar.tsx` — 진행률 바
  - `frontend/app/components/chat/messages/CompletionCard.tsx` — 완료 카드
  - `frontend/app/components/chat/messages/ErrorCard.tsx` — 에러 카드
- 관련 Invariant: 없음
- 관련 ADR: 없음

## 제약 (Boundaries)
- 변경 파일 10개 이하 목표
- Gemini 스트리밍 중계(토큰 단위)는 이번 스코프 아님
- 노드 내부 서브스텝 로깅은 이번 스코프 아님
- LangGraph stream_mode 변경 시 기존 updates 모드 동작 보장 필수

## 힌트
- LangGraph `stream_mode=["updates", "debug"]` 조합으로 노드 시작 이벤트 수신 가능 (debug 모드에서 `task` 이벤트)
- 또는 각 노드 함수 진입 시 state에 마커를 쓰는 방식도 가능
- LangFuse trace_id는 `observability.py`의 `ContextVar`에서 관리 중
- `LANGFUSE_HOST`는 `config.py`에서 가져올 수 있음
