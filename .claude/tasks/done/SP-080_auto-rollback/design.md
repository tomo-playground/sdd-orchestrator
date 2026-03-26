# SP-080 상세 설계: 자동 롤백 (머지 후 Sentry 에러 급증 감지)

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `orchestrator/tools/rollback.py` | **신규** | 포스트머지 모니터링 + revert PR 생성 로직 |
| `orchestrator/tools/github.py` | 수정 | `do_merge_pr()` 성공 후 모니터링 시작 훅 |
| `orchestrator/state.py` | 수정 | `rollbacks` 테이블 추가 |
| `orchestrator/config.py` | 수정 | 롤백 설정 상수 추가 |
| `orchestrator/tools/__init__.py` | 수정 | rollback 모듈 import (MCP tool 등록 없음 — 내부 전용) |
| `orchestrator/tools/sentry.py` | 수정 | public `fetch_error_counts()` 헬퍼 추출, `since_hours` float 타입 변경 |
| `orchestrator/tests/test_rollback.py` | **신규** | 롤백 로직 테스트 |

**난이도: 중** (변경 파일 6개, DB 테이블 추가(SQLite), 외부 API 호출)

---

## Phase A: Sentry 에러 급증 감지

### DoD-A1: `post_merge_monitor` — 머지 직후 5분간 Sentry 모니터링

**구현 방법:**
- `rollback.py` 신규 파일 생성
- `start_post_merge_monitor(pr_number: int, merge_sha: str) -> None`:
  - `asyncio.create_task`로 백그라운드 태스크 생성
  - **태스크 참조 보관 필수** (R1 BLOCKER 반영): 모듈 레벨 `_active_monitors: set[asyncio.Task] = set()`에 strong reference 유지, 완료 시 `done_callback`으로 제거 (worktree.py `_watch_tasks` 패턴 동일)
  - 5분(300초) 동안 30초 간격으로 Sentry 에러 카운트 체크
- `_monitor_loop(pr_number, merge_sha)` 내부에서 **단일 httpx.AsyncClient를 5분간 유지** (R1 반영):
  ```python
  async with httpx.AsyncClient(timeout=..., headers=...) as client:
      baseline = await fetch_error_counts(client, since_hours=0.1)
      for _ in range(10):
          await asyncio.sleep(30)
          current = await fetch_error_counts(client, since_hours=0.1)
          ...
  ```
- `sentry.py`에 **public 헬퍼 추출** (R1 BLOCKER 반영):
  - `async def fetch_error_counts(client: httpx.AsyncClient, since_hours: float = 0.1) -> dict[str, int]`:
  - 기존 `_fetch_sentry_issues()` 래핑, 각 프로젝트별 이슈 수 반환
  - `rollback.py`는 이 public 함수만 호출 (캡슐화 유지, 인증 코드 중복 방지)
- `_check_surge(baseline: dict[str, int], current: dict[str, int]) -> tuple[bool, int]`:
  - 순수 계산 함수 (외부 API 호출 없음)
  - delta = `sum(current.values()) - sum(baseline.values())`
  - `delta >= ROLLBACK_ERROR_THRESHOLD` 이면 `(True, delta)`
  - firstSeen 기반 필터링은 `fetch_error_counts(since_hours=0.1)` 측에서 처리 (Gemini R1 반영)

**동작 정의:**
- Before: 머지 후 에러 감시 없음
- After: 머지 → baseline 스냅샷 → 30초 간격 체크 (최대 10회) → 급증 시 revert PR 생성

**엣지 케이스:**
- Sentry API 타임아웃 → 해당 체크 스킵, 다음 주기에 재시도
- 5분 이내 오케스트레이터 재시작 → 모니터링 태스크 소실 (수용 가능 — 재시작 자체가 드뭄)
- 동시 다발 머지 → 각 PR마다 독립 모니터링 태스크 실행

**영향 범위:**
- `sentry.py`의 `_fetch_sentry_issues()` 재사용 — httpx 클라이언트 생성 필요 (SENTRY_AUTH_TOKEN 의존)

**테스트 전략:**
- `_take_sentry_snapshot` mock: 프로젝트별 이슈 수 반환
- `_check_surge` 단위 테스트: threshold 경계값 테스트 (4→9: surge=True, 4→8: surge=False when threshold=5)
- 전체 모니터링 flow mock: baseline → 2회 정상 → 3회째 surge 감지 → revert 호출 확인

**Out of Scope:**
- Sentry webhook 기반 실시간 감지 (polling으로 충분)
- 프로젝트별 개별 임계값 (전체 합산으로 단순화)
- 사람이 GitHub UI에서 직접 revert PR을 머지하는 경우의 재모니터링 (R1 INFO 반영)
- rollback.py를 MCP tool로 등록하지 않음 — `do_merge_pr` 내부에서만 호출되는 내부 모듈

---

### DoD-A2: baseline 스냅샷 저장

**구현 방법:**
- `start_post_merge_monitor` 시작 시 `_take_sentry_snapshot()` 호출
- 결과를 로컬 변수로 유지 (모니터링 태스크의 closure)
- DB에는 저장하지 않음 (5분 임시 데이터, 영속 불필요)

**동작 정의:**
- 머지 직후 Sentry 3개 프로젝트의 unresolved 이슈 수를 스냅샷

---

### DoD-A3: 급증 임계값 설정

**구현 방법:**
- `config.py`에 추가:
  ```python
  ROLLBACK_ERROR_THRESHOLD = int(os.environ.get("ORCH_ROLLBACK_THRESHOLD", "5"))
  ROLLBACK_MONITOR_DURATION = 300  # 5 minutes
  ROLLBACK_CHECK_INTERVAL = 30    # 30 seconds
  GIT_CLONE_TIMEOUT = 60          # git clone 전용 (GH_TIMEOUT 재사용 금지)
  GH_PR_CREATE_TIMEOUT = 30       # gh pr create 전용
  SENTRY_TIMEOUT_WRITE = 5.0      # (기존 하드코딩 상수화)
  SENTRY_TIMEOUT_POOL = 5.0       # (기존 하드코딩 상수화)
  ```
  기존 `do_sentry_scan()`의 `httpx.Timeout(write=5.0, pool=5.0)` 하드코딩도 이 상수로 전환.

**since_hours 타입 (R1 반영):** `_fetch_sentry_issues`의 `since_hours` 타입 힌트를 `int → float`로 변경 (0.1 전달 지원)

---

## Phase B: 자동 Revert PR 생성

### DoD-B1: revert PR 자동 생성

**구현 방법:**
- `_create_revert_pr(pr_number: int, merge_sha: str) -> int | None`:
  - `gh api repos/{owner}/{repo}/pulls` POST로 revert PR 생성
  - 또는 `git revert` + branch + push + `gh pr create` 패턴
  - **선택: `gh api` 직접 호출** — 오케스트레이터가 working tree를 갖고 있지 않으므로 git 조작보다 GitHub API가 안전
  - 실제로는 `gh pr create` 대신 GitHub의 revert API 사용: `POST /repos/{owner}/{repo}/pulls/{number}/revert`는 없으므로...
  - **최종 선택: 임시 디렉토리 git clone 방식** (Gemini R1 반영 — 오케스트레이터 working directory 보호)
    1. `tempfile.TemporaryDirectory()`로 격리된 임시 디렉토리 생성
    2. `git clone --depth=5 --branch main <repo_url> <tmpdir>`
    3. tmpdir에서: `git checkout -b revert/PR-{number}`
    4. tmpdir에서: `git revert --no-edit {merge_sha}`
    5. tmpdir에서: `git push origin revert/PR-{number}`
    6. `gh pr create --title "Revert #{number}: {title}" --label auto-rollback`
    7. TemporaryDirectory 자동 정리
  - 모든 git/gh 명령은 `asyncio.create_subprocess_exec`로 실행, cwd=tmpdir (기존 패턴)

**동작 정의:**
- Before: 에러 급증 시 수동 대응
- After: 에러 급증 감지 → 자동 revert PR 생성 (머지는 하지 않음)

**엣지 케이스:**
- merge conflict로 revert 실패 → Slack warning + PR 미생성
- 이미 같은 PR에 대한 revert가 존재 → state.db에서 중복 체크 후 skip
- merge_sha가 유효하지 않음 → git revert 실패 → 로그 + Slack 알림
- **무한 롤백 방지** (Gemini R1 반영): `auto-rollback` 라벨 PR이 머지되면 모니터링 시작하지 않음 → `do_merge_pr`에서 라벨 체크

**영향 범위:**
- git 작업은 임시 디렉토리에서 수행 → 오케스트레이터 working directory 영향 없음
- 다른 워크트리와 충돌 없음

**테스트 전략:**
- git/gh subprocess mock: revert branch 생성, PR 생성 성공/실패
- merge conflict 시 적절한 에러 처리 확인

---

### DoD-B2: `auto-rollback` 라벨 추가

**구현 방법:**
- `gh pr create` 시 `--label auto-rollback` 포함
- **라벨 사전 생성 필요** (R2 반영): `gh label create` 없으면 422 에러. revert PR 생성 전 `gh label create auto-rollback --color FF0000 --force` 실행 (이미 존재하면 무시)

---

### DoD-B3: Slack 알림

**구현 방법:**
- `do_notify_human()` 재사용 (기존 패턴)
- 급증 감지 시:
  ```python
  await do_notify_human({
      "message": f"[ROLLBACK] PR #{pr_number} 머지 후 Sentry 에러 급증 ({delta}건)\n\n"
                 f"원인: 머지 5분 내 에러 +{delta}건 (임계값: {threshold})\n"
                 f"조치: revert PR #{revert_pr} 생성됨\n"
                 f"영향: [사람] revert PR 확인 후 머지 필요",
      "level": "critical",
      "links": [
          {"text": f"원본 PR #{pr_number}", "url": f"https://github.com/tomo-playground/shorts-producer/pull/{pr_number}"},
          {"text": f"Revert PR #{revert_pr}", "url": f"https://github.com/tomo-playground/shorts-producer/pull/{revert_pr}"},
      ],
  })
  ```
- revert PR 생성 실패 시:
  ```python
  await do_notify_human({
      "message": f"[ROLLBACK] PR #{pr_number} revert PR 생성 실패\n\n"
                 f"원인: {error_reason}\n"
                 f"조치: [사람] 수동 revert 필요",
      "level": "critical",
  })
  ```

---

### DoD-B4: revert PR은 자동 머지하지 않음

**구현 방법:**
- `auto-rollback` 라벨이 있는 PR은 `do_merge_pr()`에서 skip
- `github.py`의 `do_merge_pr()` 수정:
  ```python
  # auto-rollback PR은 사람이 확인 후 머지
  if "auto-rollback" in pr_summary.get("labels", []):
      return _tool_error(f"PR #{pr_number} is an auto-rollback — requires human merge")
  ```

---

## Phase C: 상태 추적

### DoD-C1: `rollbacks` 테이블 추가

**구현 방법:**
- `state.py`의 `_init_tables()`에 추가:
  ```sql
  CREATE TABLE IF NOT EXISTS rollbacks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      original_pr INTEGER NOT NULL,
      revert_pr INTEGER,
      error_count INTEGER NOT NULL,
      baseline_count INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'monitoring',
      created_at TEXT NOT NULL,
      finished_at TEXT
  );
  -- status 가능 값: 'monitoring' | 'no_surge' | 'surge_detected' | 'reverted' | 'revert_failed'
  ```
- 헬퍼 메서드:
  - `record_rollback(original_pr, revert_pr, error_count, baseline_count) -> int`
  - `update_rollback_status(rollback_id: int, status: str) -> None` — status 전이 관리
  - `has_rollback(original_pr) -> bool` — 중복 방지

---

### DoD-C2: 중복 rollback 방지

**구현 방법:**
- `_create_revert_pr` 호출 전 `state.has_rollback(pr_number)` 체크
- True면 skip + 로그

---

### DoD-C3: 데일리 리포트에 rollback 이력 포함

**구현 방법:**
- `main.py`의 `_gather_daily_summary()`에 rollback 수 추가:
  ```python
  summary["rollbacks"] = state.get_recent_rollbacks(hours=24)
  ```
- `notify.py`의 `send_daily_report()`에 rollback 섹션 추가

**영향 범위:**
- `_gather_daily_summary` 시그니처 변경 없음 (dict에 키 추가)

---

## github.py 통합

### `do_merge_pr()` 수정

**구현 방법:**
- 머지 성공 후 merge commit SHA를 가져와 모니터링 시작:
  ```python
  # 기존 머지 로직 이후 추가
  # 무한 롤백 방지: auto-rollback PR은 모니터링 skip
  if "auto-rollback" not in pr_summary.get("labels", []):
      merge_sha = await _get_merge_sha(pr_number)
      if merge_sha:
          from orchestrator.tools.rollback import start_post_merge_monitor
          start_post_merge_monitor(pr_number, merge_sha)
  ```
- `_get_merge_sha(pr_number) -> str | None`:
  - `gh pr view {number} --json mergeCommit --jq '.mergeCommit.oid'`

**동작 정의:**
- Before: 머지 후 즉시 반환
- After: 머지 후 모니터링 백그라운드 태스크 시작 → 즉시 반환 (비차단)

---

## 실행 순서

```
Phase A (A1, A2, A3) — 모니터링 + 스냅샷 + config
Phase B (B1 → B2, B3, B4) — revert PR 생성 + 알림 + 머지 차단
Phase C (C1, C2, C3) — 상태 추적 + 데일리 리포트
github.py 통합 — do_merge_pr 훅 추가
```

**권장 실행 순서:**
1. Phase C1 (rollbacks 테이블) — 다른 Phase의 전제
2. Phase A (config → snapshot → monitor)
3. Phase B (revert PR → 알림 → 머지 차단)
4. Phase C2, C3 (중복 방지 + 리포트)
5. github.py 통합
6. 테스트
