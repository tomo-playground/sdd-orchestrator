# SP-086: Slack 메시지 템플릿 모듈화 — 상세 설계

> 난이도: 하 | 에이전트 리뷰: 생략

## 변경 파일 요약

| 파일 | 액션 | 변경 내용 |
|------|------|-----------|
| `orchestrator/tools/slack_templates.py` | **신규** | Block Kit 헬퍼 + 4개 메시지 템플릿 |
| `orchestrator/tools/notify.py` | 수정 | 인라인 블록 제거 → 템플릿 호출 |
| `orchestrator/tools/slack_bot.py` | 수정 | 로컬 헬퍼 제거 → 템플릿 import |
| `orchestrator/tests/test_slack_templates.py` | **신규** | 템플릿 단위 테스트 |
| `orchestrator/tests/test_notify.py` | 수정 | import 경로 변경 |
| `orchestrator/tests/test_slack_bot.py` | 수정 | import 경로 변경 |

---

## DoD 1: 공용 Block Kit 헬퍼

### 구현 방법

`orchestrator/tools/slack_templates.py` 신규 생성. slack_bot.py의 로컬 헬퍼 + notify.py의 `_build_link_buttons`를 이동.

```python
# orchestrator/tools/slack_templates.py

def header_block(text: str) -> dict: ...
def section_block(text: str) -> dict: ...
def divider() -> dict: ...
def context_block(text: str) -> dict: ...
def link_buttons(links: list[dict], max_count: int = 5) -> dict | None: ...
def blocks_to_fallback(blocks: list[dict], max_len: int = 200) -> str: ...
```

### 동작 정의

- before: `_header_block()` 등이 slack_bot.py 모듈 private, notify.py는 별도 `_build_link_buttons` 보유
- after: 모든 헬퍼가 `slack_templates`에 public 함수로 통합, 두 모듈에서 import

### 엣지 케이스

- `link_buttons([])` → `None` 반환 (기존 동작 유지)
- `blocks_to_fallback([])` → 빈 문자열

### 영향 범위

- notify.py, slack_bot.py의 import 변경
- 외부 인터페이스(MCP 도구, Slack API 호출) 변경 없음

### 테스트 전략

- `test_slack_templates.py::TestBlockKitHelpers` — 각 헬퍼의 반환 구조 검증
- `link_buttons`: 빈 리스트, 1개, 5개 초과 케이스
- `blocks_to_fallback`: header+section 블록 → 평문 변환

### Out of Scope

- 새 헬퍼 추가 (fields_block 등) — 필요 시 SP-081에서

---

## DoD 2: 메시지 템플릿 함수

### 구현 방법

동일 파일(`slack_templates.py`)에 4개 템플릿 함수 추가. 각 함수는 `(blocks, fallback)` 튜플 반환.

```python
# ── 상수 (notify.py에서 이동) ──
KST = timezone(timedelta(hours=9))
_LEVEL_EMOJI = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}

# ── 템플릿 ──
def notification_blocks(
    level: str, message: str, links: list[dict] | None = None,
) -> tuple[list[dict], str]: ...

def daily_report_blocks(summary: dict) -> tuple[list[dict], str]: ...

def error_blocks(message: str) -> list[dict]: ...

def agent_response_blocks(text: str) -> list[dict]: ...
```

### 동작 정의

#### `notification_blocks(level, message, links)`
- before: `do_notify_human()` 내부에서 15줄 인라인 구성
- after: 동일 블록을 반환하는 순수 함수. blocks + fallback 텍스트 튜플
- 레이아웃: section(emoji+level+message) → context(KST 시각) → actions(링크, 선택)

#### `daily_report_blocks(summary)`
- before: `send_daily_report()` 내부에서 40줄 인라인 구성
- after: 동일 블록을 반환하는 순수 함수
- `_fmt_list()` 내부 헬퍼로 이동 (모듈 private)
- 레이아웃: header → divider → 머지/PR/태스크/블로커/Sentry → rollback(조건부)

#### `error_blocks(message)`
- slack_bot.py `_error_blocks` 그대로 이동

#### `agent_response_blocks(text)`
- slack_bot.py `_text_to_blocks` 그대로 이동
- `\n\n` 분할 → section + divider, 2900자 제한

### 엣지 케이스

- `notification_blocks` — SLACK_MAX_MESSAGE_LENGTH 초과 시 fallback 잘림 + `(truncated)`
- `daily_report_blocks` — summary 키 누락 시 기본값 (`[]`, `"?/?"`, `0`)
- `agent_response_blocks` — 빈 텍스트 → `(빈 응답)` section 반환

### 영향 범위

- 순수 함수, 사이드 이펙트 없음

### 테스트 전략

- `test_slack_templates.py::TestNotificationBlocks` — level별 이모지, 링크 유/무, truncation
- `test_slack_templates.py::TestDailyReportBlocks` — 정상 summary, 빈 summary, rollback 조건
- `test_slack_templates.py::TestErrorBlocks` — header+section 구조
- `test_slack_templates.py::TestAgentResponseBlocks` — 단일 문단, 복수 문단, 길이 초과

### Out of Scope

- 레이아웃/텍스트 변경 — 기존과 100% 동일 출력 유지

---

## DoD 3: notify.py 리팩토링

### 구현 방법

```python
# before (notify.py)
from orchestrator.config import SLACK_MAX_MESSAGE_LENGTH, ...

_LEVEL_EMOJI = { ... }        # 삭제
_LEVEL_COLOR = { ... }        # 삭제 (미사용)
def _build_link_buttons(): ...  # 삭제

# after (notify.py)
from orchestrator.tools.slack_templates import (
    notification_blocks,
    daily_report_blocks,
)
```

#### `do_notify_human()` 변경

```python
# before: 15줄 인라인 블록 구성
blocks = [{"type": "section", ...}, {"type": "context", ...}]
actions_block = _build_link_buttons(links)
...

# after: 1줄 호출
blocks, fallback = notification_blocks(level, message, links)
```

#### `send_daily_report()` 변경

```python
# before: 40줄 인라인 블록 + _fmt_list 로컬 함수
def _fmt_list(items, limit=5): ...
blocks = [{"type": "header", ...}, ...]
fallback = f"Coding Machine Report {today}: ..."

# after: 1줄 호출
blocks, fallback = daily_report_blocks(summary)
```

### 동작 정의

- 외부 인터페이스(MCP 도구 시그니처, `_send_slack_message` 호출) 변경 없음
- Slack에 전송되는 메시지 내용 동일

### 엣지 케이스

없음 (기존 로직 그대로 위임)

### 영향 범위

- `_LEVEL_COLOR` dict 삭제 — 현재 미사용 (dead code 제거)
- `KST` 상수 — templates로 이동하되, notify.py 내 다른 참조 없으면 제거

### 테스트 전략

- 기존 `test_notify.py` 전체 통과 (동작 변경 없으므로)
- `_build_link_buttons` import 테스트 → `slack_templates.link_buttons`로 경로 변경

### Out of Scope

- `_send_slack_message()` 전송 로직 — 변경하지 않음
- CLI entrypoint — 변경하지 않음

---

## DoD 4: slack_bot.py 리팩토링

### 구현 방법

```python
# before (slack_bot.py 하단)
def _header_block(text): ...      # 삭제
def _section_block(text): ...     # 삭제
def _error_blocks(message): ...   # 삭제
def _text_to_blocks(text): ...    # 삭제
def _blocks_to_fallback(blocks):  # 삭제

# after (slack_bot.py 상단 import)
from orchestrator.tools.slack_templates import (
    agent_response_blocks,
    blocks_to_fallback,
    error_blocks,
)
```

#### 호출부 변경

| 위치 | before | after |
|------|--------|-------|
| `_handle_mention` L167 | `_error_blocks(...)` | `error_blocks(...)` |
| `_handle_mention` L177 | `_text_to_blocks(response)` | `agent_response_blocks(response)` |
| `_handle_mention` L180 | `_error_blocks(...)` | `error_blocks(...)` |
| `_handle_mention` L183 | `_error_blocks(...)` | `error_blocks(...)` |
| `_post_message` L232 | `_blocks_to_fallback(blocks)` | `blocks_to_fallback(blocks)` |

### 동작 정의

- 함수 이름 변경: `_text_to_blocks` → `agent_response_blocks`, `_error_blocks` → `error_blocks`
- 로직/출력 동일

### 엣지 케이스

없음

### 영향 범위

- 모듈 외부 인터페이스 변경 없음 (SlackBotListener 클래스 API 유지)

### 테스트 전략

- 기존 `test_slack_bot.py` 전체 통과
- import 경로 변경: `from orchestrator.tools.slack_bot import _error_blocks, _text_to_blocks` → `from orchestrator.tools.slack_templates import error_blocks, agent_response_blocks`

### Out of Scope

- SlackBotListener 클래스 로직
- MCP 도구 (pause/resume)

---

## DoD 5: 기존 테스트 통과

### 구현 방법

#### `test_notify.py` 변경
- L12: `_build_link_buttons` import → `from orchestrator.tools.slack_templates import link_buttons`
- `TestBuildLinkButtons` 클래스 내 호출 → `link_buttons(...)` (함수명 변경)

#### `test_slack_bot.py` 변경
- L12-13: `_error_blocks, _text_to_blocks` import → `from orchestrator.tools.slack_templates import error_blocks, agent_response_blocks`
- `TestBlockKit` 클래스 내 호출명 업데이트

### 동작 정의

- 모든 기존 테스트 assertion 변경 없음 (출력 동일)

### 테스트 전략

- `pytest orchestrator/tests/test_notify.py orchestrator/tests/test_slack_bot.py` — 전체 PASS

### Out of Scope

- 새 테스트 케이스 추가는 DoD 6에서

---

## DoD 6: slack_templates.py 단위 테스트

### 구현 방법

`orchestrator/tests/test_slack_templates.py` 신규 생성.

```python
class TestBlockKitHelpers:
    def test_header_block_structure(self): ...
    def test_section_block_mrkdwn(self): ...
    def test_divider(self): ...
    def test_context_block(self): ...
    def test_link_buttons_empty(self): ...
    def test_link_buttons_max_5(self): ...
    def test_blocks_to_fallback(self): ...

class TestNotificationBlocks:
    def test_info_level(self): ...
    def test_warning_level(self): ...
    def test_critical_level(self): ...
    def test_with_links(self): ...
    def test_without_links(self): ...
    def test_truncation(self): ...
    def test_kst_timestamp(self): ...

class TestDailyReportBlocks:
    def test_full_summary(self): ...
    def test_empty_summary(self): ...
    def test_with_rollbacks(self): ...

class TestErrorBlocks:
    def test_structure(self): ...

class TestAgentResponseBlocks:
    def test_single_paragraph(self): ...
    def test_multi_paragraph_with_dividers(self): ...
    def test_empty_text(self): ...
    def test_long_text_truncation(self): ...
```

### 테스트 전략

- 순수 함수 테스트 — mock 불필요
- 블록 구조(type, text 키) + 내용(이모지, 타임스탬프) 검증

### Out of Scope

- 통합 테스트 (Slack API 호출)
