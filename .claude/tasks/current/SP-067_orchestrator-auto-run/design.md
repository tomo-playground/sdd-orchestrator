# SP-067 상세 설계: 오케스트레이터 Phase 2 — 자동 실행

> 간소화 설계 (변경 파일 4~7, DB/API 변경 없음)

## 변경 파일 요약

| 파일 | 변경 | 신규 |
|------|------|------|
| `orchestrator/config.py` | 상수 추가 | |
| `orchestrator/state.py` | runs 테이블 + 메서드 추가 | |
| `orchestrator/agents.py` | system prompt + allowed_tools 확장 | |
| `orchestrator/main.py` | 사이클 후 액션 실행 루프 추가 | |
| `orchestrator/tools/__init__.py` | 신규 도구 등록 | |
| `orchestrator/tools/worktree.py` | | 신규 |
| `orchestrator/tools/github.py` | merge_pr 도구 추가 | |
| `orchestrator/rules.py` | | 신규 |
| `orchestrator/tests/test_worktree.py` | | 신규 |
| `orchestrator/tests/test_rules.py` | | 신규 |
| `orchestrator/tests/test_state.py` | runs 테이블 테스트 추가 | |

---

## DoD별 구현 방법 + 테스트 전략

### 1. 워크트리 자동 기동

**구현 방법:**
- `orchestrator/tools/worktree.py` 신규 파일
  - `launch_sdd_run(task_id: str) -> dict` — MCP 도구
    - `asyncio.create_subprocess_exec("claude", "--worktree", task_id, "--dangerously-skip-permissions", "-p", f"/sdd-run {task_id}")` 실행
    - state에 run 기록 (`start_run`)
    - **`asyncio.create_task(_watch_process(proc, task_id, state))`로 백그라운드 감시** — proc.wait() → exit code 수집 → finish_run() 자동 호출. PID 폴링 불필요.
  - `check_running_worktrees() -> dict` — MCP 도구
    - state 테이블에서 running 상태인 run 목록 조회 (PID 확인 불필요, _watch_process가 상태를 업데이트하므로)
- `orchestrator/config.py`에 `MAX_PARALLEL_RUNS = 2` 추가
- `orchestrator/config.py`에 `ENABLE_AUTO_RUN: bool` 추가 — 환경변수 `ORCH_AUTO_RUN=1`로 제어. False면 launch/merge 도구를 allowed_tools에서 제외 (Phase 1 읽기 전용 모드 유지)

**테스트 전략:**
- `test_launch_blocks_over_max_parallel` — MAX_PARALLEL 초과 시 거부
- `test_check_running_detects_finished` — PID 종료 감지

### 2. PR 모니터링

**구현 방법:**
- 기존 `check_prs` 도구는 이미 CI + review 상태를 반환
- `summarize_prs()`에 `mergeable` 필드 추가: `ci_status == "success" and review == "APPROVED"`
- Lead Agent system prompt에서 "recommend merge" → `merge_pr` 도구 호출로 전환

**테스트 전략:**
- `test_summarize_prs_mergeable_field` — 조건 충족 시 `mergeable: true`

### 3. 자동 머지

**구현 방법:**
- `orchestrator/tools/github.py`에 `merge_pr` MCP 도구 추가
  - `merge_pr(args: {pr_number: int}) -> dict`
  - `_run_gh_command("pr", "merge", str(pr_number), "--squash", "--delete-branch")`
  - 머지 성공 시 state에서 해당 run 완료 처리

**테스트 전략:**
- `test_merge_pr_success` — subprocess mock으로 성공 케이스
- `test_merge_pr_failure` — 실패 시 에러 반환

### 4. 자동 머지 규칙

**구현 방법:**
- `orchestrator/rules.py` 신규 파일
  - `can_auto_merge(pr_summary: dict) -> tuple[bool, str]`
    - CI passed (`ci_status == "success"`)
    - 리뷰 approved (`review == "APPROVED"`)
    - changes_requested 없음
    - 반환: `(True, "reason")` 또는 `(False, "blocking_reason")`
- Lead Agent가 `check_prs` → `can_auto_merge` 판단 → `merge_pr` 호출

**테스트 전략:**
- `test_can_merge_all_pass` — 모든 조건 충족
- `test_cannot_merge_ci_fail` — CI 실패
- `test_cannot_merge_no_review` — 리뷰 없음
- `test_cannot_merge_changes_requested` — 수정 요청

### 5. 실패 처리

**구현 방법:**
- `check_running_worktrees()`에서 exit code != 0 감지 → state에 `failed` 기록 + 로그 경고
- `orchestrator/state.py`에 `get_consecutive_failures(task_id: str) -> int` 추가
- 3회 연속 실패 → `blocked` 상태로 변경
- changes_requested PR → `_run_gh_command("workflow", "run", "sdd-review.yml")` 트리거
  - **중복 트리거 가드**: state의 runs 테이블에 `review_triggered_at` 필드 추가. 이미 트리거된 PR은 재트리거하지 않음 (무한 루프 방지)

**테스트 전략:**
- `test_consecutive_failure_blocked` — 3회 실패 후 blocked

### 6. 통합 — Lead Agent 역할 전환

**구현 방법:**
- `config.py`의 `LEAD_AGENT_SYSTEM_PROMPT` 업데이트:
  - Phase 1 "READ ONLY" → Phase 2 "READ + EXECUTE"
  - Decision Rules에 실행 액션 추가:
    - approved 태스크 + 슬롯 여유 → `launch_sdd_run` 호출
    - mergeable PR → `merge_pr` 호출
    - 실패 PR → `sdd-review.yml` 트리거
- `agents.py`의 `allowed_tools`에 신규 도구 추가:
  - `mcp__orch__launch_sdd_run`
  - `mcp__orch__check_running_worktrees`
  - `mcp__orch__merge_pr`
- `tools/__init__.py`에 신규 도구 등록

**테스트 전략:**
- `test_allowed_tools_includes_new` — 도구 목록 확인

### 7. State 확장

**구현 방법:**
- `state.py`에 `runs` 테이블 추가:
  ```sql
  CREATE TABLE IF NOT EXISTS runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_id TEXT NOT NULL,
      pid INTEGER,
      status TEXT NOT NULL DEFAULT 'running',
      exit_code INTEGER,
      pr_number INTEGER,
      started_at TEXT NOT NULL,
      finished_at TEXT
  );
  ```
- 메서드: `start_run()`, `finish_run()`, `get_running_runs()`, `get_consecutive_failures()`

**테스트 전략:**
- `test_run_lifecycle` — start → finish → 조회
- `test_get_running_excludes_finished` — running만 반환

---

## Out of Scope
- 설계 자동 작성/승인 (SP-068)
- Slack/외부 알림 (SP-069)
- sdd-sync 개선 (별도)
