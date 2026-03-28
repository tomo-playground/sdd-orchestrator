# SP-108 상세 설계: Slack 발송 경로 SlackBot 단일화

## 변경 파일 요약

| 파일 | 변경 | 난이도 |
|------|------|--------|
| `orchestrator/tools/notify.py` | httpx 제거, SlackBot 경유로 전환 | 중간 |
| `orchestrator/tools/slack_bot.py` | `post_notification()` 공개 메서드 추가 | 낮음 |
| `orchestrator/main.py` | `set_slack_bot()` 브릿지 제거, 직접 참조 | 낮음 |
| `orchestrator/tests/test_notify.py` | mock 대상 변경 | 낮음 |

> 난이도: **하** (변경 4파일, 신규 함수 1개, DB/API 변경 없음)

---

## DoD-1: `_send_slack_message()` (httpx) 제거 + SlackBot 경유

### 구현 방법

**1. `slack_bot.py` — `post_notification()` 공개 메서드 추가**

```python
async def post_notification(self, text: str, blocks: list[dict] | None = None) -> str | None:
    """외부에서 호출 가능한 알림 발송. ts 반환 + active thread 등록."""
```

- `_post_message()` 호출 → `chat_postMessage` 실행
- 반환: `response["ts"]` (성공) 또는 `None` (실패/미연결)
- 성공 시 `register_active_thread(ts)` 자동 호출
- `web_client`가 None이면 (미연결) → `None` 반환 + 로그 fallback

**2. `notify.py` — 리팩터**

- `_send_slack_message()` (httpx) 삭제
- `set_slack_bot()`, `_slack_bot_instance`, `_register_thread()` 삭제
- `_last_slack_sent`, `httpx` import 삭제
- 모듈 레벨 싱글턴: `_bot: SlackBotListener | None = None`
- `init_notify(bot)` → `_bot` 설정 (main에서 호출)
- `do_notify_human()` → `_bot.post_notification(fallback, blocks)` 호출
- `send_daily_report()` → `_bot.post_notification(fallback, blocks)` 호출
- `_bot`이 None이면 → 로그 fallback (기존 동작 유지)

**3. `main.py` — 브릿지 제거**

```python
# Before
from orchestrator.tools.notify import set_slack_bot
set_slack_bot(self.slack_bot)

# After
from orchestrator.tools.notify import init_notify
init_notify(self.slack_bot)
```

### 동작 정의

| Before | After |
|--------|-------|
| `do_notify_human()` → httpx REST → 일방향 | `do_notify_human()` → `SlackBot.post_notification()` → active thread 등록 → 양방향 |
| `send_daily_report()` → httpx REST → 일방향 | `send_daily_report()` → `SlackBot.post_notification()` → 양방향 |
| rate limit: httpx 측 `_last_slack_sent` + SlackBot `_post_lock` 이중 | SlackBot `_post_lock` 단일 |

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| SlackBot 미시작 (토큰 미설정) | `_bot = None` → `do_notify_human`이 로그 fallback |
| SlackBot 크래시 후 재시작 | `main._run_slack_bot_with_restart()`가 새 인스턴스 생성 → `init_notify()` 재호출 필요 |
| `_cli_main()` (CLI 단독 실행) | SlackBot 없이 실행 → `_bot = None` → 로그 fallback |

### 테스트 전략

```python
# _send_slack_message 대신 SlackBot.post_notification mock
@patch.object(SlackBotListener, "post_notification", new_callable=AsyncMock, return_value="1234.5678")
async def test_notify_uses_bot(mock_post):
    result = await do_notify_human({"message": "test", "level": "info"})
    mock_post.assert_called_once()
    assert "1234.5678" in result["content"][0]["text"]

# SlackBot 미연결 시 fallback
async def test_notify_fallback_when_no_bot():
    init_notify(None)
    result = await do_notify_human({"message": "test", "level": "info"})
    assert "log_only" in result["content"][0]["text"]
```

### Out of Scope

- SlackBot Socket Mode 로직 변경
- `_handle_thread_message` 기능 변경
- Slack Block Kit 템플릿 변경
- `_post_message()`의 `thread_ts` 파라미터 (알림은 항상 채널 루트에 발송)

---

## DoD-2: `_active_threads` 자동 등록

`post_notification()` 내부에서 `register_active_thread(ts)` 호출로 자동 처리. 별도 구현 불필요.

---

## DoD-3: 기존 테스트 업데이트

- `test_notify.py`의 `_send_slack_message` mock → `SlackBotListener.post_notification` mock으로 교체
- httpx 관련 테스트 제거
- `set_slack_bot` → `init_notify` 교체

## 테스트 파일

| 테스트 파일 | 대상 |
|------------|------|
| `orchestrator/tests/test_notify.py` | notify 함수 + SlackBot 연동 |
| `orchestrator/tests/test_slack_bot.py` | `post_notification()` 단위 테스트 |
