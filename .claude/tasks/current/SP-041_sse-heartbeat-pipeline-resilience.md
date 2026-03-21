---
id: SP-041
priority: P0
scope: fullstack
branch: feat/SP-041-sse-heartbeat
created: 2026-03-21
status: pending
depends_on:
label: bug
reviewer: stopper2008
assignee: stopper2008
---

## 무엇을
SSE heartbeat 도입 + director_checkpoint 모델 분리 — 파이프라인 안정성 근본 개선

## 왜
SP-010(3/20)에서 Next.js rewrite 프록시 경유로 전환 후, critic 노드가 **100% 실패**.
Next.js 내장 프록시는 idle timeout(~30초)이 있어, 장시간 노드 실행 중 SSE 이벤트가 없으면 연결을 끊는다.
critic(3인 Architect 병렬 토론)은 25~30초간 SSE 이벤트 없이 실행 → 프록시 timeout → uvicorn cancel scope → 노드 사망.

LangFuse 기록: 3/21 critic 5건 연속 ERROR (`Cancelled via cancel scope`), 3/18 이전에는 84~114초 정상 완료.

추가로 director_checkpoint가 불필요하게 Gemini 2.5 Pro를 사용 중 — Flash로 분리하여 비용/지연 절감.

## 완료 기준 (DoD)

### A. SSE Heartbeat (핵심)
- [ ] `stream_graph_events()`에서 graph.astream() 실행 중 주기적 heartbeat 전송
  - SSE 표준 comment 형식: `:heartbeat\n\n` (클라이언트 파싱에 영향 없음)
  - 간격: 15초 (Next.js proxy 30초 timeout의 절반)
- [ ] Frontend `parseSSEStream()`이 `:` 시작 comment를 무시하는지 확인 (SSE 표준이므로 이미 무시할 가능성 높음)
- [ ] critic 노드가 30초+ 실행에도 연결 유지 확인 (수동 테스트)
- [ ] 기존 SSE 이벤트 흐름에 영향 없음 (interrupt, error, completed 등)

### B. Director Checkpoint 모델 분리
- [ ] `config_pipelines.py`에 `DIRECTOR_CHECKPOINT_MODEL` 환경변수 추가 (기본값: `gemini-2.5-flash`)
- [ ] `director_checkpoint.py`에서 `DIRECTOR_CHECKPOINT_MODEL` 사용
- [ ] 기존 `DIRECTOR_MODEL`(2.5 Pro)은 director_plan, director 노드에서 유지

### C. 검증
- [ ] Backend 테스트 통과 (pytest)
- [ ] Frontend 테스트 통과 (vitest) — parseSSEStream heartbeat 무시 테스트
- [ ] 린트 통과

## 제약
- 변경 파일 10개 이하 목표
- heartbeat 구현은 `_scripts_sse.py`의 `stream_graph_events()` 내부에서만
- `asyncio.Task` + `asyncio.Event` 패턴 또는 `async for` + timeout 래퍼 사용
- critic/director 노드 코드 자체는 변경하지 않음 — SSE 레이어에서 해결
- 의존성 추가 금지

## 힌트
- 관련 파일:
  - `backend/routers/_scripts_sse.py` — `stream_graph_events()`: heartbeat 추가 위치
  - `frontend/app/hooks/scriptEditor/sseProcessor.ts` — `parseSSEStream()`: heartbeat 무시 확인
  - `backend/services/agent/nodes/director_checkpoint.py` — 모델 변경
  - `backend/config_pipelines.py` — `DIRECTOR_CHECKPOINT_MODEL` 추가
- heartbeat 구현 패턴:
  ```python
  async def _heartbeat_sender(send: Callable, interval: float = 15):
      while True:
          await asyncio.sleep(interval)
          await send(":heartbeat\n\n")
  ```
  - `stream_graph_events()`를 `asyncio.TaskGroup` 또는 `asyncio.create_task`로 heartbeat과 graph stream을 병렬 실행
  - graph stream 완료 시 heartbeat task cancel
- SSE 표준: `:` 시작 라인은 comment로 클라이언트가 무시 (RFC 8895)
- LangFuse 트레이스 증거: trace `be0bf258`, observation `cdaea46ac22a01ba`
