# SP-131: 파이프라인 finalize 후 백엔드 DB 직접 저장 — 상세 설계

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `backend/routers/_scripts_sse.py` | `stream_graph_events()` 정상 완료 시 `_persist_finalized_scenes()` 호출 |
| `backend/services/storyboard/crud.py` | `persist_pipeline_scenes()` 함수 추가 — 파이프라인 결과를 DB에 직접 저장 |
| `backend/tests/test_persist_pipeline_scenes.py` | 신규 테스트 |

---

## DoD-1: finalize 완료 시 씬을 DB에 직접 저장

### 구현 방법

**`_scripts_sse.py` — `stream_graph_events()` 수정**

스트림 정상 완료 시 (라인 440 `else` 블록), `final_output`과 `storyboard_id`가 모두 존재하면 DB 저장 실행.

```python
# stream_graph_events() 내, 정상 완료 분기 (else 블록)
else:
    update_trace_on_completion(trace_id=handler_trace_id, output_data=final_output)
    # NEW: 파이프라인 결과를 DB에 직접 저장
    if final_output and storyboard_id:
        await _persist_finalized_scenes(storyboard_id, final_output)
```

**`_persist_finalized_scenes()` — 신규 헬퍼 (같은 파일)**

```python
async def _persist_finalized_scenes(storyboard_id: int, final_output: dict) -> None:
    """파이프라인 finalize 결과를 DB에 직접 저장. SSE 유실과 무관하게 씬 보존."""
```

- `get_db()` 세션을 수동 생성 (SSE generator 내부이므로 Depends 불가)
- `crud.persist_pipeline_scenes()` 호출
- 예외 시 로그 + Sentry 전송 (SSE 스트림에 영향 주지 않음)

### 동작 정의

**Before**: finalize 완료 → SSE 전송만 → 프론트엔드 autoSave에 의존
**After**: finalize 완료 → SSE 전송 + **백엔드 DB 직접 저장** → 프론트엔드 autoSave는 보조 역할

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| storyboard_id가 None (신규) | 저장 스킵 (프론트엔드가 POST로 생성해야 함) |
| DB 저장 실패 | 로그 + Sentry, SSE 스트림은 정상 종료 (기존 동작 유지) |
| 프론트엔드 autoSave와 동시 실행 | version 체크로 충돌 방지 (아래 DoD-3) |

### 영향 범위

- SSE 스트림 종료 직후 실행이므로 SSE 응답 자체에 영향 없음
- `persist_pipeline_scenes()`는 신규 함수라 기존 코드와 충돌 없음

### 테스트 전략

- finalize 결과 dict + storyboard_id → DB에 씬 저장 확인
- storyboard_id=None → 저장 스킵 확인
- DB 예외 시 에러 전파 안 됨 확인

### Out of Scope

- 프론트엔드 autoSave 제거/변경
- SSE 재연결 로직
- 신규 스토리보드 (storyboard_id 없는 경우) 자동 생성

---

## DoD-2: stage_status 업데이트

### 구현 방법

`persist_pipeline_scenes()` 내에서 씬 저장 후 `storyboard.stage_status`를 `None`으로 리셋. 이유: 스크립트가 새로 생성되면 기존 배경(stage)은 무효화됨.

```python
storyboard.stage_status = None  # 새 스크립트 → stage 리셋
```

### 동작 정의

- 씬 저장 성공 시 `stage_status = None` (배경 재생성 필요 상태)
- 프론트엔드는 Stage 탭 진입 시 `stage_status`를 조회하여 적절한 UI 표시

---

## DoD-3: 프론트엔드 autoSave와 충돌 방지

### 구현 방법

`persist_pipeline_scenes()`는 **version을 증가**시킨다. 프론트엔드의 후속 autoSave가 `PUT /storyboards/{id}`를 호출할 때 stale version이면 409 Conflict → 프론트엔드가 최신 데이터를 다시 fetch.

기존 `update_storyboard_in_db()`에 이미 optimistic locking이 있으므로 (라인 406-410) 추가 구현 불필요. `persist_pipeline_scenes()`에서 version을 +1 하면 자연스럽게 충돌 방지됨.

### 동작 정의

| 시나리오 | 동작 |
|---------|------|
| SSE 정상 수신 + autoSave | 백엔드 먼저 저장 (v+1) → autoSave 409 → fetch 후 재저장 |
| SSE 유실 + autoSave 없음 | 백엔드가 저장 완료 → 프론트엔드 새로고침 시 DB에서 로드 |
| SSE 정상 + autoSave 먼저 | autoSave 성공 (v 동일) → 백엔드 저장 시 씬 덮어쓰기 (동일 데이터) |

### 엣지 케이스

- autoSave가 캐릭터/메타 변경을 포함할 수 있으므로, `persist_pipeline_scenes()`는 **씬만 교체** — 메타데이터는 건드리지 않음

---

## DoD-4: SSE 유실 후 프론트엔드 재접속 시 DB에서 씬 로드

### 구현 방법

기존 `GET /storyboards/{id}` 응답에 이미 `scenes` 포함. 백엔드가 씬을 저장하면 프론트엔드 새로고침/재접속 시 자동으로 DB에서 로드됨. **추가 구현 불필요.**

### 동작 정의

프론트엔드가 Studio 페이지 마운트 시 `GET /storyboards/{id}` → scenes 포함 응답 → 스토어에 로드.

---

## `persist_pipeline_scenes()` 시그니처

```python
# services/storyboard/crud.py

def persist_pipeline_scenes(
    db: Session,
    storyboard_id: int,
    scenes: list[dict],
    *,
    structure: str | None = None,
    character_id: int | None = None,
    character_b_id: int | None = None,
) -> bool:
    """파이프라인 finalize 결과를 DB에 직접 저장.

    Returns True if saved successfully, False otherwise.
    기존 씬을 soft-delete 후 신규 씬 생성.
    storyboard.version을 +1하여 autoSave 충돌 방지.
    """
```

- 기존 씬 soft-delete (`deleted_at` 설정)
- `final_scenes` dict를 Scene ORM 객체로 변환하여 bulk insert
- `storyboard.version += 1`
- `storyboard.character_id`, `character_b_id` 업데이트 (Director 캐스팅 결정 반영)
- `storyboard.structure` 업데이트
- `storyboard.stage_status = None`
