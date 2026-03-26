# SP-082 상세 설계: Slack Bot Claude Agent 전환

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `orchestrator/tools/slack_bot.py` | 수정 | 키워드 매칭 → Claude Agent 위임, pause/resume MCP tool 추가 |
| `orchestrator/agents.py` | 수정 | `create_slack_bot_options(mcp_server)` 추가 |
| `orchestrator/config.py` | 수정 | Slack Bot Agent 시스템 프롬프트 + 설정 상수 추가 |
| `orchestrator/tests/test_slack_bot.py` | 수정 | 키워드 테스트 → Agent 호출 테스트 전환 |

**난이도: 하** (변경 파일 3개, 기존 패턴 재사용)

---

## 설계 핵심

기존 `_dispatch_command`의 키워드 매칭을 제거하고, `query_agent()`에 메시지를 통째로 위임.
Agent가 기존 MCP tools(scan_backlog, check_prs, launch_sdd_run 등)를 자율 호출하여 응답 생성.

```
Before: @bot 상태 → _parse_cmd_key("상태") → _cmd_status() → Block Kit
After:  @bot SP-084 어떻게 돼? → query_agent("SP-084 어떻게 돼?") → [도구 호출] → 텍스트 → Block Kit
```

---

## Phase A: Claude Agent 통합

### DoD-A1: `_handle_mention` → Agent 위임

**구현 방법:**
- `slack_bot.py`의 `_handle_mention()` 수정:
  ```python
  async def _handle_mention(self, event, say):
      # 채널/사용자 allowlist 체크 (기존 유지)
      ...
      text = re.sub(r"<@[A-Z0-9]+>\s*", "", event["text"]).strip()

      # Agent 호출
      response = await self._ask_agent(text)
      blocks = _text_to_blocks(response)
      await self._post_message(channel, blocks, thread_ts)
  ```
- `_ask_agent(text: str) -> str` 신규 메서드:
  ```python
  async def _ask_agent(self, text: str) -> str:
      from orchestrator.agents import create_slack_bot_options
      options = create_slack_bot_options(self._mcp_server)
      return await query_agent(options, text)
  ```
- `SlackBotListener.__init__`에 `self._mcp_server` 저장 — daemon에서 전달받음

**동작 정의:**
- Before: 6개 키워드만 인식, 나머지는 help 출력
- After: 모든 자연어를 Claude Agent가 처리, 도구를 자율 호출

**엣지 케이스:**
- Agent 타임아웃 (응답 없음) → 에러 메시지 + 로그
- Agent가 도구 호출 없이 텍스트만 반환 → 그대로 전달 (정상)
- 빈 메시지 → Agent에 그대로 전달, Agent가 help 안내

**영향 범위:**
- `_dispatch_command`, `_parse_cmd_key`, `_cmd_*` 함수들 전부 삭제
- `_READ_COMMANDS` 상수 삭제
- `_cmd_lock` 삭제 (Agent 호출은 단일 비동기이므로 내부에서 직렬화 불필요 — MCP tool 레벨에서 처리)

**테스트 전략:**
- `query_agent` mock → Agent 응답 텍스트 → Block Kit 변환 확인
- 채널/사용자 allowlist 테스트 유지
- 타임아웃 시 에러 메시지 반환 확인

**Out of Scope:**
- 대화 히스토리 (멀티턴) — 현재는 단발 질문/응답
- 파일 업로드/이미지 처리

---

### DoD-A2: MCP server 공유

**구현 방법:**
- `OrchestratorDaemon.__init__`에서 생성한 `self.mcp_server`를 Slack Bot에 전달:
  ```python
  # main.py _maybe_start_slack_bot()
  self.slack_bot = SlackBotListener(daemon=self, mcp_server=self.mcp_server)
  ```
- `SlackBotListener.__init__`에 `mcp_server` 파라미터 추가

**동작 정의:**
- Lead Agent와 Slack Bot Agent가 동일한 MCP server 인스턴스 공유
- 도구 목록 동일 (scan_backlog, check_prs, launch_sdd_run 등)

---

### DoD-A3: pause/resume MCP tool 추가

**구현 방법:**
- `slack_bot.py`에 모듈 레벨 daemon 참조 + MCP tool 추가:
  ```python
  _daemon = None

  def set_daemon(daemon) -> None:
      global _daemon
      _daemon = daemon

  @tool("pause_orchestrator", "Pause the orchestrator cycle loop", {})
  async def pause_orchestrator(args: dict) -> dict:
      if _daemon and hasattr(_daemon, "pause_event"):
          _daemon.pause_event.set()
          return _ok("오케스트레이터를 일시정지했습니다.")
      return _error("Daemon not available")

  @tool("resume_orchestrator", "Resume the orchestrator cycle loop", {})
  async def resume_orchestrator(args: dict) -> dict:
      if _daemon and hasattr(_daemon, "pause_event"):
          _daemon.pause_event.clear()
          return _ok("오케스트레이터를 재개했습니다.")
      return _error("Daemon not available")
  ```
- `__init__.py`의 `create_orchestrator_mcp_server()`에 이 2개 tool 등록
- `main.py`에서 `set_daemon(self)` 호출

---

## Phase B: Agent 설정

### DoD-B1: `create_slack_bot_options` 추가

**구현 방법:**
- `agents.py`에 추가:
  ```python
  def create_slack_bot_options(mcp_server) -> ClaudeAgentOptions:
      tools = get_allowed_tools()
      tools.extend(["mcp__orch__pause_orchestrator", "mcp__orch__resume_orchestrator"])
      return ClaudeAgentOptions(
          model=SLACK_BOT_AGENT_MODEL,
          system_prompt=SLACK_BOT_AGENT_PROMPT,
          mcp_servers={"orch": mcp_server},
          allowed_tools=tools,
          permission_mode="default",
          max_turns=SLACK_BOT_MAX_TURNS,
          cwd=PROJECT_ROOT,
      )
  ```

### DoD-B2: 시스템 프롬프트 + 설정 상수

**구현 방법:**
- `config.py`에 추가:
  ```python
  SLACK_BOT_AGENT_MODEL = "claude-haiku-4-5"   # 빠른 응답 우선
  SLACK_BOT_MAX_TURNS = 8                       # 도구 호출 최대 횟수
  SLACK_BOT_AGENT_TIMEOUT = 60                  # 초

  SLACK_BOT_AGENT_PROMPT = """\
  당신은 SDD 오케스트레이터 Slack Bot입니다.

  ## 역할
  사용자의 자연어 메시지를 이해하고, MCP 도구를 사용하여 정보를 조회하거나 액션을 실행합니다.

  ## 응답 규칙
  - 한국어로 응답
  - 간결하게 (최대 2000자)
  - 정보 조회 시: 핵심만 요약, 불필요한 설명 생략
  - 액션 실행 시: 실행 결과를 한 줄로 보고
  - 모르는 질문: "해당 정보를 확인할 수 없습니다" (추측 금지)

  ## 사용 가능 도구
  - scan_backlog: 백로그 + 태스크 상태 조회
  - check_prs: 열린 PR 상태 조회
  - check_workflows: GitHub Actions 상태
  - check_running_worktrees: 실행 중 워크트리
  - sentry_scan: Sentry 에러 스캔
  - launch_sdd_run: 태스크 워크트리 실행 (task_id 필요)
  - merge_pr: PR 머지 (pr_number 필요)
  - trigger_sdd_review: PR 수정 트리거
  - pause_orchestrator: 오케스트레이터 일시정지
  - resume_orchestrator: 오케스트레이터 재개
  - notify_human: Slack 알림 전송
  """
  ```

**모델 선택 근거:** Slack 응답은 빠른 속도가 중요. haiku로 충분한 자연어 이해 + 도구 호출 가능. 비용(구독)도 효율적.

---

## Phase C: 응답 포맷

### DoD-C1: Agent 텍스트 → Block Kit 변환

**구현 방법:**
- `_text_to_blocks(text: str) -> list[dict]` 신규 헬퍼:
  ```python
  def _text_to_blocks(text: str) -> list[dict]:
      # 4000자 초과 시 truncate
      if len(text) > 3800:
          text = text[:3800] + "\n\n(응답이 잘렸습니다)"
      return [_section_block(text)]
  ```
- 기존 `_header_block`, `_section_block`, `_error_blocks` 헬퍼 유지 (에러 시 사용)

**동작 정의:**
- Agent 텍스트 응답 → mrkdwn section block으로 래핑
- 마크다운(볼드, 코드, 리스트)은 Slack mrkdwn과 호환

---

## 삭제 대상

| 삭제 항목 | 이유 |
|----------|------|
| `_parse_cmd_key()` | 키워드 매칭 불필요 |
| `_dispatch_command()` | Agent가 대체 |
| `_cmd_status()` | scan_backlog + check_prs + check_running_worktrees로 대체 |
| `_cmd_launch()` | launch_sdd_run tool로 대체 |
| `_cmd_merge()` | merge_pr tool로 대체 |
| `_cmd_pause()` / `_cmd_resume()` | pause/resume MCP tool로 대체 |
| `_cmd_backlog()` | scan_backlog tool로 대체 |
| `_cmd_help()` | Agent가 자연어로 안내 |
| `_READ_COMMANDS` | 불필요 |
| `_cmd_lock` | Agent 단일 호출로 불필요 |
| `SP_RE`, `PR_RE` | Agent가 자연어에서 직접 파싱 |

---

## 실행 순서

1. Phase B (config + agents) — Agent 설정 선행
2. Phase A3 (pause/resume tool) — MCP server에 등록
3. Phase A1 + A2 (slack_bot.py 리팩토링)
4. Phase C (응답 포맷)
5. 테스트
