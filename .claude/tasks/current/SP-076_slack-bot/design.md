# SP-076 상세 설계: Slack Bot 양방향 연동 + 알림 품질 개선

> 간소화 설계 (변경 파일 9개, DB/API 변경 없음)

## 설계 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 수신 방식 | Socket Mode (`connect_async()`) | 웹서버 불필요, 무료 플랜 호환, asyncio 블로킹 없음 |
| 알림 표준화 | 방안 A: shell → notify.py CLI | Block Kit 한 곳에서 관리, Python 환경 이미 존재 |
| 명령 실행 | `do_*` 코어 함수 직접 호출 | MCP 래퍼 우회, 사이클 대기 없이 즉시 응답 |
| Signing Secret | Socket Mode에서는 불필요 | WebSocket 연결이므로 HTTP 서명 검증 불필요 |

---

## 변경 파일 요약

| 파일 | 유형 | 설명 |
|------|------|------|
| `orchestrator/tools/slack_bot.py` | 신규 | Socket Mode 리스너 + 명령 파싱/실행 |
| `orchestrator/tools/notify.py` | 수정 | `links` 필드 추가 → Block Kit 버튼 렌더링 + CLI 엔트리포인트 |
| `orchestrator/config.py` | 수정 | Slack Bot 환경변수 + timeout 상수 추가 |
| `orchestrator/main.py` | 수정 | Socket Mode 리스너 기동 + 재시작 래퍼 + pause_event |
| `orchestrator/tools/__init__.py` | 수정 안 함 | SlackBotListener는 MCP 도구가 아닌 내부 컴포넌트 |
| `.claude/scripts/sdd-health.sh` | 수정 | `notify_slack()` → notify.py CLI 호출로 교체 |
| `.claude/scripts/sdd-sentry.sh` | 수정 | `notify_slack()` → notify.py CLI 호출로 교체 |
| `.claude/scripts/sdd-qa.sh` | 수정 | `notify_slack()` → notify.py CLI 호출로 교체 |
| `backend/.env.example` | 수정 | `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` 추가 |

---

## DoD 1: Slack App 설정 + Socket Mode 기동

### 구현 방법

**`config.py`** — 환경변수 + 상수 추가:
```python
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")  # xapp- 접두사, Socket Mode 전용
SLACK_BOT_API_TIMEOUT = 10.0  # chat_postMessage timeout
SLACK_BOT_CHAT_INTERVAL = 0.5  # rate limit 여유분 (500ms)
```

**`slack_bot.py`** — `SlackBotListener` 클래스:
```python
class SlackBotListener:
    def __init__(self, daemon: OrchestratorDaemon)
    async def start(self) -> None          # connect_async() — 논블로킹 연결
    async def stop(self) -> None           # disconnect_async() — graceful shutdown
    async def _handle_mention(self, event, say)  # app_mention 핸들러
    async def _handle_command(self, text, channel, thread_ts) -> str  # 명령 파싱 + 실행
    async def _post_message_rate_limited(self, channel, blocks, thread_ts)  # rate limit 방어
```

- **의존성**: `slack-bolt[async] >= 1.18` (slack-sdk는 자동 포함, 별도 선언 안 함)
- **초기화**: `AsyncApp(token=SLACK_BOT_TOKEN)` — signing_secret 불필요 (Socket Mode)
- **web_client**: `self.web_client = self.app.client` (AsyncWebClient, timeout=SLACK_BOT_API_TIMEOUT)
- **`app_mention` 이벤트만 수신**
- **봇 자기 메시지 방어**: `_handle_mention` 첫 줄에 `if event.get("bot_id"): return`
- **재연결**: bolt 내장 자동 재연결에 위임. 래퍼는 `start()` 자체 실패만 감지 (WebSocket silent drop은 bolt 내부 처리)

**Socket Mode 연결** — `connect_async()` 패턴 (이벤트 루프 블로킹 방지):
```python
async def start(self) -> None:
    self.handler = AsyncSocketModeHandler(self.app, SLACK_APP_TOKEN)
    await self.handler.connect_async()  # 백그라운드 WebSocket, 즉시 리턴

async def stop(self) -> None:
    if self.handler:
        await self.handler.disconnect_async()
```

**`main.py`** — 재시작 래퍼 + pause_event:
```python
class OrchestratorDaemon:
    def __init__(self, ...):
        # 기존 ...
        self.pause_event = asyncio.Event()  # set = 일시정지, clear = 재개

    async def run(self) -> None:
        if SLACK_BOT_TOKEN and SLACK_APP_TOKEN:
            self.slack_bot = SlackBotListener(daemon=self)
            asyncio.create_task(self._run_slack_bot_with_restart())
        # 기존 while loop ...

    async def _run_slack_bot_with_restart(self) -> None:
        restart_count = 0
        max_restarts = 3
        while restart_count < max_restarts and not self.stop_event.is_set():
            try:
                await self.slack_bot.start()
                await self.stop_event.wait()  # 종료 신호까지 대기
            except Exception:
                restart_count += 1
                try:
                    await self.slack_bot.stop()  # 이전 연결 정리
                except Exception:
                    pass
                logger.warning("SlackBot crashed (%d/%d), restart in 30s", restart_count, max_restarts)
                await asyncio.sleep(30)
        if restart_count >= max_restarts:
            logger.error("SlackBot failed %d times, giving up", max_restarts)

    async def _run_cycle(self) -> None:
        if self.pause_event.is_set():
            logger.info("Paused, skipping cycle")
            return
        # 기존 사이클 로직 ...
```

### 엣지 케이스
- 토큰 미설정 → Socket Mode 미기동, 로그 경고만
- 연결 끊김 → slack-bolt 자동 재연결 + 예외 시 래퍼가 30초 후 재시작 (최대 3회)
- 오케스트레이터 종료 시 → `stop()` → `disconnect_async()` 호출

### 테스트 전략

| 테스트 | 검증 |
|--------|------|
| `test_slack_bot_no_tokens` | 토큰 미설정 시 리스너 미기동 |
| `test_slack_bot_handle_mention` | app_mention → `_handle_command` 호출 |
| `test_slack_bot_ignore_bot_message` | `bot_id` 있는 이벤트 → 무시 |
| `test_slack_bot_restart_on_crash` | 예외 발생 → 재시작 래퍼 동작 |

---

## DoD 2: 명령 처리

### 구현 방법

**명령 매핑**:
```
"상태"           → _cmd_status()
"실행 SP-NNN"    → _cmd_launch(sp_id)
"머지 #NNN"      → _cmd_merge(pr_num)
"중지"           → _cmd_pause()
"시작"           → _cmd_resume()
"백로그"         → _cmd_backlog()
기타             → _cmd_help()
```

**`do_*` 코어 함수 직접 호출** (MCP 래퍼 우회):
- `_cmd_status()` → `parse_backlog()` + `_run_gh_command()` 직접 조합
- `_cmd_launch(sp_id)` → `do_launch_sdd_run(sp_id)` 직접 호출
- `_cmd_merge(pr_num)` → `do_merge_pr(pr_num)` 직접 호출
- `_cmd_pause()` → `self.daemon.pause_event.set()` (stop_event 아님!)
- `_cmd_resume()` → `self.daemon.pause_event.clear()`
- `_cmd_backlog()` → `parse_backlog()` → 상위 5개 필터링

**동시 명령 race condition 방어** — 읽기/쓰기 분리:
```python
_READ_COMMANDS = {"상태", "백로그"}

class SlackBotListener:
    def __init__(self, ...):
        self._cmd_lock = asyncio.Lock()  # 쓰기 명령 직렬화

    async def _handle_command(self, text, channel, thread_ts):
        cmd_key = self._parse_cmd_key(text)
        if cmd_key in _READ_COMMANDS:
            return await self._dispatch_command(text, channel, thread_ts)
        async with self._cmd_lock:  # 실행/머지/중지/시작만 직렬화
            return await self._dispatch_command(text, channel, thread_ts)
```

**rate limit 방어** — `_post_message_rate_limited()`:
```python
async def _post_message_rate_limited(self, channel, blocks, thread_ts=None):
    async with self._post_lock:
        elapsed = time.monotonic() - self._last_post
        if elapsed < SLACK_BOT_CHAT_INTERVAL:
            await asyncio.sleep(SLACK_BOT_CHAT_INTERVAL - elapsed)
        try:
            resp = await self.web_client.chat_postMessage(
                channel=channel, blocks=blocks, thread_ts=thread_ts
            )
            self._last_post = time.monotonic()
            return resp
        except SlackApiError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", "10"))
                await asyncio.sleep(retry_after)
                return await self.web_client.chat_postMessage(
                    channel=channel, blocks=blocks, thread_ts=thread_ts
                )
            raise
```

> `_post_lock`과 `_cmd_lock`은 별도 — 같은 락 사용 시 데드락 위험

### 엣지 케이스
- 존재하지 않는 SP-NNN → "태스크를 찾을 수 없습니다" 응답
- status가 approved가 아닌 태스크에 실행 명령 → "설계 승인이 필요합니다" 응답
- 머지 불가 PR → do_merge_pr의 에러 메시지를 그대로 응답
- 동시 쓰기 명령 → `_cmd_lock`으로 직렬화, 읽기 명령은 병렬 허용

### 테스트 전략

| 테스트 | 검증 |
|--------|------|
| `test_cmd_status` | 상태 명령 → parse_backlog + gh 호출 확인 |
| `test_cmd_launch` | "실행 SP-077" → do_launch_sdd_run 호출 |
| `test_cmd_merge` | "머지 #177" → do_merge_pr 호출 |
| `test_cmd_backlog` | 백로그 → 상위 5개 반환 |
| `test_cmd_unknown` | 미인식 명령 → help 메시지 반환 |
| `test_cmd_launch_invalid` | 존재하지 않는 SP → 에러 응답 |
| `test_cmd_pause_uses_pause_event` | 중지 → pause_event.set(), stop_event 미사용 확인 |
| `test_concurrent_write_serialized` | 동시 쓰기 명령 → 직렬 실행 확인 |

---

## DoD 3: 알림 품질 개선 — notify.py links 필드 + CLI

### 구현 방법

**`notify.py`** — 타임스탬프 KST 변환 + links 추가:

```python
# context 블록의 타임스탬프를 KST로 변경
from datetime import timezone, timedelta
KST = timezone(timedelta(hours=9))
# 기존: datetime.now(UTC).strftime('%H:%M UTC')
# 변경: datetime.now(KST).strftime('%H:%M KST')
# send_daily_report()의 today도 동일하게 KST 적용

links = args.get("links", [])

if links:
    blocks.append({
        "type": "actions",
        "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": link["text"]},
             "url": link["url"]}
            for link in links[:5]
        ]
    })
```

**`notify.py`** — CLI 엔트리포인트 추가:

```python
async def _cli_main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("message")
    parser.add_argument("--level", default="info", choices=["info", "warning", "critical"])
    parser.add_argument("--link", nargs=2, action="append", metavar=("TEXT", "URL"))
    args = parser.parse_args()
    links = [{"text": t, "url": u} for t, u in (args.link or [])]
    await do_notify_human({"message": args.message, "level": args.level, "links": links})

if __name__ == "__main__":
    asyncio.run(_cli_main())
```

**MCP tool 스키마 + 시스템 프롬프트 — 반드시 동시 커밋**:
- `notify_human` 스키마에 `links` property 추가
- `LEAD_AGENT_SYSTEM_PROMPT`에 "Slack Link Rules" 섹션 추가
- 분리 커밋 시 프롬프트가 존재하지 않는 필드를 참조하는 시간 창 발생

### 엣지 케이스
- links 빈 배열 → actions 블록 미생성 (기존 동작 유지)
- links 5개 초과 → 처음 5개만 사용
- CLI `--link` 미지정 → links 빈 배열

### 테스트 전략

| 테스트 | 검증 |
|--------|------|
| `test_notify_with_links` | links 전달 시 actions 블록 포함 |
| `test_notify_without_links` | links 미전달 시 기존 동작 유지 |
| `test_notify_links_max_5` | 6개 links → 5개만 렌더링 |
| `test_cli_entrypoint` | CLI 인자 파싱 → do_notify_human 호출 |

---

## DoD 4: Shell 스크립트 알림 표준화

### 구현 방법

3개 shell 스크립트의 `notify_slack()` / `curl` 호출을 **notify.py CLI**로 교체.

```bash
ORCH_DIR="$(cd "$(dirname "$0")/../../orchestrator" && pwd)"
notify_slack() {
  local msg="$1"
  local level="${2:-info}"
  local link_args="${3:-}"
  cd "$ORCH_DIR" && uv run python -m orchestrator.tools.notify "$msg" \
    --level "$level" $link_args 2>&1 | grep -v "^$" >&2 || true
}
```

> 실패 시 stderr에 기록 (`2>/dev/null` 대신 `2>&1 | grep >&2`) — 알림 실패 이력 보존

### 테스트 전략
- Shell 단위 테스트는 Out of Scope (수동 검증)
- notify.py CLI 테스트로 간접 검증

---

## DoD 5: 응답 포맷

### 구현 방법

각 명령 결과를 Block Kit으로 구조화하여 스레드 응답.
`_post_message_rate_limited(channel, blocks, thread_ts)` 사용.

### 테스트 전략

| 테스트 | 검증 |
|--------|------|
| `test_status_response_format` | 상태 응답이 Block Kit 형식인지 |
| `test_thread_reply` | thread_ts 포함 확인 |

---

## Out of Scope

| 항목 | 이유 |
|------|------|
| 멀티턴 대화 | 스펙 제약: 단일 명령 + 응답 |
| Slack App 생성 (UI 작업) | 수동 설정 필요 (api.slack.com) |
| DM 수신 | app_mention만 지원 |
| `message.channels` 이벤트 | 스펙 대비 축소 — app_mention만으로 충분 |
| 중지/시작 영구 상태 저장 | 오케스트레이터 재시작 시 리셋 허용 |

---

## 의존성 추가

```
# orchestrator/pyproject.toml
slack-bolt[async] >= 1.18
```

> `slack-sdk`는 `slack-bolt`에 자동 포함. 별도 선언 안 함.

---

## 에이전트 설계 리뷰 결과

| 리뷰어 | 판정 | 주요 피드백 | 반영 |
|--------|------|------------|------|
| Tech Lead | BLOCKER → 반영 완료 | Socket Mode `create_task(start_async())` 블로킹 위험 | `connect_async()` 패턴으로 수정 |
| Tech Lead | WARNING → 반영 완료 | MCP 래퍼 대신 `do_*` 코어 함수 직접 호출 | DoD 2 수정 |
| Tech Lead | WARNING → 반영 완료 | `stop_event` 오용 → 데몬 종료 위험 | `pause_event` 도입 |
| Tech Lead | WARNING → 반영 완료 | `slack-sdk` 중복 선언 + signing_secret 명시 | 의존성/설계 결정 수정 |
| Tech Lead | WARNING → 반영 완료 | `message.channels` 드롭 미기재 | Out of Scope 추가 |
| Perf Eng | BLOCKER → 반영 완료 | 동시 명령 race condition (TOCTOU) | 읽기/쓰기 분리 `asyncio.Lock` |
| Perf Eng | BLOCKER → 반영 완료 | 봇 자기 메시지 재귀 트리거 | `bot_id` 체크 방어 |
| Perf Eng | WARNING → 반영 완료 | `chat_postMessage` timeout 미설정 | `SLACK_BOT_API_TIMEOUT` 상수 |
| Perf Eng | WARNING → 반영 완료 | Socket Mode 태스크 예외 종료 감시 없음 | 재시작 래퍼 |
| Perf Eng | WARNING → 반영 완료 | CLI 실패 로그 소실 | stderr 출력으로 변경 |
| Perf Eng | WARNING → 반영 완료 | rate limit 429 처리 없음 | `_post_message_rate_limited` |
| Perf Eng | PASS | 시스템 프롬프트 변경 기존 동작 영향 없음 | — |
