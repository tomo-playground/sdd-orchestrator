# Draft Storyboard 조기 생성

## 개요

스크립트 생성 전에 Storyboard 레코드를 먼저 확보하여 디버깅, LangFuse 트레이싱, 작업 복구를 가능하게 한다.

---

## 문제 정의

### 1. 디버깅 추적 불가

AS IS: 스크립트 생성 요청이 실패하면, 서버 로그에서 해당 시도를 특정할 식별자가 없다. `POST /scripts/generate`는 storyboard가 없는 상태에서 호출되므로 group_id와 timestamp 조합으로 추측할 수밖에 없다.

TO BE: Draft 생성으로 확보한 `storyboard_id`를 모든 후속 API 호출에 포함한다. 로그 검색이 `storyboard_id={N}`으로 즉시 가능하다.

### 2. LangFuse 트레이스 단절

AS IS: `analyze-topic` 호출과 `generate-stream` 호출이 각각 독립적인 LangFuse trace로 기록된다. 동일 영상 작업에 속하는 두 trace를 연결할 키가 없어서 LangFuse 대시보드에서 "이 분석과 이 생성이 같은 영상이다"를 확인할 수 없다.

TO BE: Draft의 `storyboard_id`를 기반으로 `session_id=storyboard-{id}`를 설정하여 동일 영상의 모든 LLM 호출을 LangFuse Session으로 그룹핑한다.

### 3. 작업 유실

AS IS: 사용자가 Chat에서 주제 분석 → 설정 조정까지 마친 후 브라우저를 닫으면, 아직 Storyboard가 생성되지 않은 상태이므로 모든 작업이 유실된다.

TO BE: 첫 Chat 메시지 전송 직전에 Draft가 생성되므로, DB에 storyboard 레코드가 존재한다. 재접속 시 draft 상태의 storyboard 목록에서 복구 가능하다.

---

## AS IS / TO BE 플로우

### AS IS

```
"새 영상" 클릭
  -> Chat 입력
  -> POST /scripts/analyze-topic  (storyboard_id 없음)
  -> POST /scripts/generate       (storyboard_id 없음)
  -> POST /storyboards            (여기서 최초 storyboard 생성)
```

- analyze-topic ~ generate 구간에 DB 레코드 부재
- 에러 시 추적 불가, LangFuse trace 연결 불가

### TO BE

```
"새 영상" 클릭
  -> Store 리셋
  -> 첫 Chat 메시지 전송 직전:
     POST /storyboards/draft { title, group_id }
       -> storyboard_id 확보
       -> contextStore / URL / chatStore 동기화
  -> POST /scripts/analyze-topic  { storyboard_id }
  -> POST /scripts/generate       { storyboard_id }
  -> POST /storyboards            (기존 storyboard에 scenes 저장)
```

- 모든 구간에서 storyboard_id로 추적 가능
- LangFuse session_id로 trace 그룹핑

---

## API 스펙

### POST /api/v1/storyboards/draft

씬 없이 스토리보드 레코드만 생성한다 (ID 예약).

**Request Body**

```json
{
  "title": "My Draft",   // optional, default "Draft", max 200자
  "group_id": 1           // required
}
```

**Response** (200 OK)

```json
{
  "storyboard_id": 42,
  "title": "My Draft",
  "created": true
}
```

**Error Cases**

| Status | 조건 | 설명 |
|--------|------|------|
| 422 | `group_id` 누락 | Pydantic validation error |
| 500 | DB 오류 | 내부 서버 오류 |

**서비스 로직** (`services/storyboard/crud.py::create_draft`)

1. title이 빈 문자열이나 None이면 `"Draft"` 기본값 적용
2. title이 있으면 `truncate_title()`로 190자 제한
3. `Storyboard(title, group_id)` INSERT + commit
4. `{ storyboard_id, title, created: True }` 반환

---

## 변경 파일 목록

### Backend

| 파일 | 변경 내용 |
|------|----------|
| `schemas.py` | `StoryboardDraftRequest`, `StoryboardDraftResponse` 추가 |
| `routers/storyboard.py` | `POST /storyboards/draft` 엔드포인트 추가 |
| `services/storyboard/crud.py` | `create_draft()` 함수 추가 |
| `services/storyboard/__init__.py` | `create_draft` re-export 추가 |
| `routers/scripts.py` | `_build_config()` session_id 분리, 로깅에 storyboard_id 포함 |
| `tests/test_draft_storyboard.py` | API 통합 + 서비스 유닛 테스트 11개 |

### Frontend

| 파일 | 변경 내용 |
|------|----------|
| `store/actions/draftActions.ts` | `ensureDraftStoryboard()` 신규 |
| `hooks/useTopicAnalysis.ts` | `sendMessage()`에서 draft 호출 + storyboard_id 전달 |
| `hooks/scriptEditor/actions.ts` | `buildGenerateBody()`에 storyboard_id 포함 |

---

## LangFuse session_id 연결 방식

### thread_id vs session_id 분리

LangGraph의 `thread_id`와 LangFuse의 `session_id`는 용도가 다르므로 분리한다.

| 식별자 | 용도 | 생성 방식 | 생명주기 |
|--------|------|-----------|----------|
| `thread_id` | LangGraph 체크포인터 키 | `uuid.uuid4()` | 요청별 (매 invoke마다 새로 생성) |
| `session_id` | LangFuse 트레이스 그룹핑 | `f"storyboard-{storyboard_id}"` | 스토리보드 수명 동안 유지 |

### 연결 흐름

```
[Frontend]
  ensureDraftStoryboard() -> storyboard_id=42

  POST /scripts/analyze-topic
    body: { storyboard_id: 42, ... }

[Backend: routers/scripts.py]
  _build_config(request):
    thread_id = str(uuid.uuid4())              # LangGraph 체크포인터 (매번 새로)
    session_id = f"storyboard-{request.storyboard_id}"  # LangFuse 그룹핑 키

[Backend: services/agent/observability.py]
  create_langfuse_handler(
    trace_id=trace_id,
    session_id=session_id,       # -> metadata.session_id에 기록
  )
    -> Langfuse root span의 metadata에 session_id 포함
    -> 동일 storyboard_id의 모든 trace가 LangFuse Session으로 묶임
```

### LangFuse v3 SDK 제약

Langfuse v3 `CallbackHandler`는 `session_id` 파라미터를 직접 지원하지 않는다. 따라서 root span의 `metadata`에 `{"session_id": "storyboard-42"}` 형태로 포함시킨다. LangFuse 대시보드에서 metadata 필터로 검색 가능하다.

---

## 제약 조건

- DB 스키마 변경 없음 (기존 `storyboards` 테이블 그대로 사용)
- 기존 `autoSave` / `persistStoryboard` 플로우 변경하지 않음
- Draft는 scenes 없이 생성되므로 kanban_status는 자동으로 `"draft"` 파생
- 오버엔지니어링 금지: 멱등성, TTL 만료 등 부가 기능은 필요 시 별도 Phase에서 추가
