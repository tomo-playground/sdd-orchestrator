# SP-069 상세 설계: 오케스트레이터 Sentry/알림/GHA 통합

> 풀 설계 (변경 파일 8+, 외부 API 호출: Sentry API + Slack Webhook + gh CLI)

## 변경 파일 요약

| 파일 | 변경 | 신규 |
|------|------|------|
| `orchestrator/config.py` | Sentry/Slack/GHA 상수 추가 | |
| `orchestrator/tools/sentry.py` | | 신규 |
| `orchestrator/tools/github.py` | `trigger_workflow`, `cancel_workflow` 추가 | |
| `orchestrator/tools/notify.py` | | 신규 |
| `orchestrator/tools/__init__.py` | 신규 도구 등록 | |
| `orchestrator/agents.py` | Lead Agent system prompt 확장 + allowed_tools 추가 | |
| `orchestrator/main.py` | preflight에 Sentry/Slack 검증 추가, 일일 리포트 스케줄 | |
| `orchestrator/tests/test_sentry.py` | | 신규 |
| `orchestrator/tests/test_notify.py` | | 신규 |
| `orchestrator/tests/test_github_extended.py` | | 신규 |

---

## DoD별 구현 방법

### 1. Sentry 연동 — `sentry_scan` 도구

**구현 방법:**
- `orchestrator/config.py`에 추가:
  - `SENTRY_AUTH_TOKEN: str` — `os.environ.get("SENTRY_AUTH_TOKEN", "")` (backend/.env에서 로드)
  - `SENTRY_ORG = "tomo-playground"`
  - `SENTRY_PROJECTS = ["shorts-producer-backend", "shorts-producer-frontend", "shorts-producer-audio"]`
  - `SENTRY_API_BASE = "https://sentry.io/api/0"`
  - `SENTRY_SCAN_INTERVAL = 3600` — 1시간 (초)
  - `SENTRY_SCAN_LOOKBACK_HOURS = 2` — 조회 범위 (스캔 간격보다 넓게)
  - `SENTRY_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)` — 세분화된 타임아웃
- `orchestrator/tools/sentry.py` 신규:
  - **커넥션 풀 공유**: `sentry_scan` 전체 스코프에서 단일 `httpx.AsyncClient` 인스턴스를 생성하고, 내부 함수들에 `client` 파라미터로 전달 (함수마다 새로 생성하지 않음)
  - `async def _fetch_sentry_issues(client: httpx.AsyncClient, project: str, since_hours: int) -> list[dict]`
    - Sentry API 호출: `GET /projects/{org}/{project}/issues/?query=is:unresolved&sort=date&limit=25`
    - `firstSeen` 기준 since 필터링
    - 429 응답 시 `Retry-After` 헤더 파싱 → 해당 시간만큼 대기 후 1회 재시도
    - 반환: `[{id, title, culprit, level, firstSeen, lastSeen, count, permalink}]`
  - `async def _fetch_latest_stacktrace(client: httpx.AsyncClient, issue_id: str) -> str`
    - `GET /issues/{issue_id}/events/latest/`
    - 스택트레이스 추출 (기존 sentry-patrol.sh jq 로직 동일)
  - `async def _get_existing_sentry_ids() -> set[str]`
    - `gh issue list --label sentry --state all --limit 500 --json title,body`
    - body에서 `sentry-id: NNN` 파싱 → 중복 방지
  - `async def _create_github_issue(project: str, issue_data: dict, stacktrace: str) -> int | None`
    - `gh issue create` 호출 (기존 sentry-patrol.sh 본문 포맷 동일)
    - `--label sentry --label bug --assignee stopper2008`
    - 반환: 생성된 issue 번호
  - `@tool("sentry_scan") async def sentry_scan(args: dict) -> dict`
    - 단일 `httpx.AsyncClient(timeout=SENTRY_TIMEOUT)` 생성
    - 3개 프로젝트 **순차** 순회 (rate limit 안전) → 신규 이슈 감지 → GitHub Issue 생성
    - 생성된 Issue에 대해 `trigger_workflow("sentry-autofix.yml", {issue_number: N})` 자동 호출
    - 반환: `{new: N, skipped: N, created: N, triggered: N}`

**동작 정의:**
- before: Sentry 에러는 cron(매일 09:00)으로만 수집, GitHub Actions 경유
- after: 오케스트레이터가 1시간마다 직접 Sentry API 스캔 → Issue 생성 → autofix 트리거

**엣지 케이스:**
- `SENTRY_AUTH_TOKEN` 미설정 → sentry_scan 호출 시 에러 반환 (크래시 안 함)
- Sentry API 429 (rate limit) → `Retry-After` 헤더 파싱 → 짧은 대기 후 1회 재시도, 재실패 시 다음 사이클
- Sentry API 타임아웃 → 개별 프로젝트 스킵, 나머지 계속
- GitHub Issue 생성 실패 → 로그 + 스킵 (다음 스캔에서 재시도)
- 기존 cron과 중복 실행 → `_get_existing_sentry_ids()`로 중복 방지 (동일 sentry-id 검사)

**영향 범위:**
- 기존 `sentry-patrol.yml` 워크플로우는 수정하지 않음 (cron 유지 = 백업)
- 새 외부 의존성: `httpx` (오케스트레이터 pyproject.toml에 추가)

**테스트 전략:**
- `test_fetch_sentry_issues_success` — mock httpx → 정상 응답 파싱
- `test_fetch_sentry_issues_timeout` — 타임아웃 시 빈 리스트 반환
- `test_fetch_sentry_issues_auth_error` — 401 시 빈 리스트 + 로그
- `test_get_existing_sentry_ids` — gh 응답에서 sentry-id 파싱
- `test_sentry_scan_dedup` — 이미 Issue 있는 에러는 스킵
- `test_sentry_scan_creates_and_triggers` — Issue 생성 후 autofix 트리거 확인
- `test_sentry_scan_no_token` — 토큰 없으면 에러 반환

**Out of Scope:**
- Sentry Webhook 수신 (push 방식) — 현재는 pull 방식으로 충분
- Sentry Issue resolve/ignore 처리

---

### 2. GitHub Actions 제어 — `trigger_workflow`, `cancel_workflow`

**구현 방법:**
- `orchestrator/tools/github.py`에 추가:
  - `@tool("trigger_workflow") async def trigger_workflow(args: dict) -> dict`
    - `args`: `{workflow: str, inputs?: dict}`
    - **allowlist 검사**: `workflow`가 `GH_MONITORED_WORKFLOWS`에 포함되지 않으면 즉시 에러 반환 (의도치 않은 워크플로우 트리거 방지)
    - `gh workflow run {workflow}` 또는 `gh api` 사용
    - 반환: `{success: bool, message: str}`
  - `@tool("cancel_workflow") async def cancel_workflow(args: dict) -> dict`
    - `args`: `{run_id: int}`
    - `gh run cancel {run_id}`
    - 반환: `{success: bool, message: str}`
- `config.py`에 추가:
  - `GH_MONITORED_WORKFLOWS = ["sdd-review.yml", "sdd-fix.yml", "sdd-sync.yml", "sentry-autofix.yml"]`

**동작 정의:**
- before: stuck 워크플로우 감지만 (read-only)
- after: stuck 감지 → `cancel_workflow` 호출 가능, autofix 트리거 → `trigger_workflow` 호출

**엣지 케이스:**
- workflow 파일명이 allowlist(`GH_MONITORED_WORKFLOWS`)에 없음 → 즉시 에러 반환 (gh 호출 전 차단)
- run_id 없는 경우 → validation 에러
- 이미 완료된 run 취소 시도 → gh가 에러 반환 → 로그 + 무시

**영향 범위:**
- 기존 `check_workflows`, `check_prs` 도구는 변경 없음
- `agents.py` allowed_tools에 2개 도구 추가

**테스트 전략:**
- `test_trigger_workflow_success` — mock gh → 성공 반환
- `test_trigger_workflow_with_inputs` — inputs 전달 확인
- `test_trigger_workflow_not_in_allowlist` — allowlist 외 워크플로우 → 즉시 에러
- `test_cancel_workflow_success` — mock gh → 취소 성공
- `test_cancel_workflow_already_completed` — 에러 처리
- `test_trigger_workflow_gh_error` — gh 실패 시 에러 반환

**Out of Scope:**
- 워크플로우 재실행 (re-run) — 현재는 cancel + 새 trigger로 대체
- 워크플로우 로그 수집

---

### 3. Slack 알림 — `notify_human` 도구

**구현 방법:**
- `orchestrator/config.py`에 추가:
  - `SLACK_WEBHOOK_URL: str` — `os.environ.get("SLACK_WEBHOOK_URL", "")`
  - `SLACK_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)` — 세분화된 타임아웃
  - `SLACK_MIN_INTERVAL = 1.0` — Slack rate limit 준수 (1msg/sec)
- `orchestrator/tools/notify.py` 신규:
  - `_last_slack_sent: float = 0` — 모듈 레벨 타임스탬프 (rate limit 제어)
  - `async def _send_slack_message(text: str) -> bool`
    - `httpx.AsyncClient(timeout=SLACK_TIMEOUT)`로 Webhook POST
    - `{"text": text}` 페이로드
    - `SLACK_MIN_INTERVAL` 준수: 이전 전송으로부터 1초 미만이면 `asyncio.sleep` 대기
    - 반환: 성공 여부
  - `@tool("notify_human") async def notify_human(args: dict) -> dict`
    - `args`: `{message: str, level: "info" | "warning" | "critical"}`
    - level에 따라 이모지 prefix: info=ℹ️, warning=⚠️, critical=🚨
    - `SLACK_WEBHOOK_URL` 미설정 시 로그만 출력 (에러 아님)
    - 반환: `{sent: bool, channel: "slack" | "log_only"}`
  - `async def send_daily_report(summary: dict) -> bool`
    - 일일 리포트 포맷팅 + notify_human 호출
    - `summary`: `{completed_prs, in_progress, blockers, sentry_issues}`

**동작 정의:**
- before: 오케스트레이터 출력은 콘솔 로그만
- after: 판단 필요 시 Slack으로 즉시 알림 + 매일 09:00 일일 리포트

**알림 조건 (Lead Agent system prompt에 명시):**
- 설계에 BLOCKER 발견 (자동 승인 불가) → `critical`
- CI 3회 연속 실패 → `warning`
- Sentry critical 에러 → `critical`
- DB 스키마 변경 감지 → `warning`
- PR에 사람이 changes_requested → `info`

**엣지 케이스:**
- `SLACK_WEBHOOK_URL` 미설정 → fallback: 로그 출력만 (graceful degradation)
- Slack API 타임아웃/5xx → 로그 + 무시 (알림 실패가 파이프라인을 중단하면 안 됨)
- 메시지가 너무 긴 경우 (>4000자) → 자동 잘라내기 + "(truncated)" 추가

**영향 범위:**
- `main.py`의 `_run_cycle` 후 일일 리포트 조건 체크 로직 추가
- 새 외부 의존성 없음 (httpx는 sentry에서 이미 추가)

**테스트 전략:**
- `test_send_slack_message_success` — mock httpx → 200 OK
- `test_send_slack_message_timeout` — 타임아웃 시 False
- `test_send_slack_message_no_webhook` — URL 없으면 로그만
- `test_notify_human_level_prefix` — level별 이모지 확인
- `test_notify_human_truncation` — 긴 메시지 자동 잘라내기
- `test_send_daily_report_format` — 리포트 포맷 검증

**Out of Scope:**
- Slack Interactive Messages (버튼, 액션)
- Slack Bot Token 기반 API (Webhook만 사용)
- 이메일/SMS 등 다른 채널

---

### 4. 일일 리포트

**구현 방법:**
- `orchestrator/main.py`에 추가:
  - `self._last_report_date: str | None = None` — 마지막 리포트 날짜
  - `_run_cycle` 내에서 현재 시간 체크 → 09:00 KST(00:00 UTC) 이후 + 오늘 아직 리포트 안 했으면 실행
  - `async def _maybe_send_daily_report(self) -> None`
    - `scan_backlog` + `check_prs` + `check_workflows` 결과 수집
    - `send_daily_report(summary)` 호출
    - `self._last_report_date` 업데이트
- 리포트 포맷 (Slack mrkdwn):
  ```
  📋 *SDD Daily Report* — 2026-03-23

  ✅ *완료 PR*: #65 (SP-067), #66 (SP-068)
  🔄 *진행 중*: SP-069 (design)
  🚫 *블로커*: SP-070 (DB 변경 — 사람 승인 필요)
  🐛 *Sentry*: 2건 open, 1건 autofix PR 생성
  ```

**동작 정의:**
- before: 일일 리포트 없음
- after: 매일 00:00 UTC (09:00 KST) 이후 첫 사이클에서 Slack 리포트 전송

**엣지 케이스:**
- 00:00 UTC에 정확히 오케스트레이터가 꺼져있으면 → 다음 기동 시 오늘 리포트 안 했으면 즉시 전송
- Slack 전송 실패 → 로그만 (다음 날 재시도, 같은 날 반복 시도 안 함)

**영향 범위:**
- `main.py` `__init__`에 `_last_report_date` 필드 추가
- `_run_cycle`에 리포트 체크 로직 3줄 추가

**테스트 전략:**
- `test_daily_report_sent_once_per_day` — 같은 날 2번째 사이클에서는 스킵
- `test_daily_report_on_restart` — 리포트 안 한 날 기동 시 즉시 전송

**Out of Scope:**
- 리포트 시간 커스터마이징
- 리포트 히스토리 DB 저장

---

### 5. 통합 — Lead Agent 확장

**구현 방법:**
- `orchestrator/config.py`의 `LEAD_AGENT_SYSTEM_PROMPT` 확장:
  - `## Your Tools` 섹션에 추가:
    - `4. **sentry_scan** — Sentry API에서 미해결 에러 조회 + GitHub Issue 생성 + autofix 트리거`
    - `5. **trigger_workflow** — GitHub Actions 워크플로우 수동 트리거`
    - `6. **cancel_workflow** — stuck 워크플로우 취소`
    - `7. **notify_human** — Slack으로 사람에게 알림 전송`
  - `## Decision Rules` 섹션에 추가:
    - `매 사이클 시작 시 sentry_scan 호출 (1시간 간격 제어는 도구 내부)`
    - `stuck 워크플로우 발견 시 → cancel_workflow 호출`
    - `BLOCKER/critical 발견 시 → notify_human 호출`
    - `CI 3회 연속 실패 → notify_human(level="warning")`
    - `PR에 changes_requested → notify_human(level="info")`
  - `## Each Cycle` 업데이트:
    - 기존 3단계 → 5단계 (sentry_scan + notify 추가)
- `orchestrator/agents.py`의 `allowed_tools` 확장:
  - `"mcp__orch__sentry_scan"`, `"mcp__orch__trigger_workflow"`, `"mcp__orch__cancel_workflow"`, `"mcp__orch__notify_human"` 추가
- `orchestrator/tools/__init__.py`에 도구 등록:
  - `from orchestrator.tools.sentry import sentry_scan`
  - `from orchestrator.tools.notify import notify_human`
  - `tools=[scan_backlog, check_prs, check_workflows, sentry_scan, trigger_workflow, cancel_workflow, notify_human]`
- `orchestrator/main.py` preflight 확장:
  - `SENTRY_AUTH_TOKEN` 없으면 경고 (에러 아님 — graceful degradation)
  - `SLACK_WEBHOOK_URL` 없으면 경고 (에러 아님)

**동작 정의:**
- before: read-only 모니터링 (3도구)
- after: Sentry 스캔 + GHA 제어 + Slack 알림 (7도구)

**엣지 케이스:**
- Sentry/Slack 토큰 없이 시작 → 해당 도구 호출 시 graceful 에러 (오케스트레이터 자체는 계속 동작)
- Lead Agent가 도구를 적절히 호출하지 않는 경우 → system prompt의 Decision Rules로 유도

**영향 범위:**
- Lead Agent의 턴 수 증가 → `MAX_AGENT_TURNS` 10→15 확정 (7도구 순차 호출 시)
- `AGENT_QUERY_TIMEOUT` 300→600 확정 (Sentry API 호출 시간 추가: 최악 ~60초)

**테스트 전략:**
- `test_tools_registered` — 7개 도구 모두 MCP 서버에 등록 확인
- `test_system_prompt_contains_new_tools` — system prompt에 새 도구 언급 확인

**Out of Scope:**
- Lead Agent 모델 변경 (Sonnet 유지)
- 도구별 rate limiting (Lead Agent의 판단에 위임)

---

## 의존성

- `httpx` — 오케스트레이터 pyproject.toml에 추가 필요 (Sentry API + Slack Webhook 호출)
- 기존 `gh` CLI 의존성 유지 (trigger/cancel도 gh 사용)

## 환경변수 추가

| 변수 | 용도 | 필수 |
|------|------|------|
| `SENTRY_AUTH_TOKEN` | Sentry API 인증 | 아니오 (없으면 sentry_scan 비활성) |
| `SLACK_WEBHOOK_URL` | Slack 알림 전송 | 아니오 (없으면 로그만) |

---

## 에이전트 설계 리뷰 결과

| 리뷰어 | 판정 | 주요 피드백 |
|--------|------|------------|
| Performance Engineer | WARNING x7 → 전부 반영 완료 | httpx 커넥션 풀 공유, Timeout 세분화(connect/read 분리), 429 Retry-After 파싱, trigger_workflow allowlist 검사, Slack rate limit(1msg/sec) 가드, 프로젝트 순차 순회, AGENT_QUERY_TIMEOUT=600 확정 |

### 반영 상세

| # | 지적 | 반영 내용 |
|---|------|----------|
| W-1 | Sentry 클라이언트 루프 내 N회 생성 | `sentry_scan` 스코프에서 단일 `AsyncClient` 공유, 내부 함수에 `client` 파라미터 전달 |
| W-2 | 429 `Retry-After` 헤더 미처리 | `_fetch_sentry_issues`에서 429 시 헤더 파싱 → 대기 후 1회 재시도 |
| W-3 | Slack 연속 호출 빈도 제어 없음 | `SLACK_MIN_INTERVAL=1.0` + `_last_slack_sent` 타임스탬프 가드 |
| W-4 | `trigger_workflow` allowlist 없음 | `GH_MONITORED_WORKFLOWS` allowlist 선검사 추가 |
| W-5 | `AGENT_QUERY_TIMEOUT` 미확정 | 600초로 확정 |
| W-6 | `httpx.Timeout` 단일값 | `Timeout(connect=5.0, read=15.0)` 세분화 (Sentry/Slack 각각) |
| W-7 | 프로젝트 순회 전략 미명시 | 3개 프로젝트 순차 순회 명시 (rate limit 안전) |
