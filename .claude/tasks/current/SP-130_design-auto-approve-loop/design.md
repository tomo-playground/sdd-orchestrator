# SP-130: design 상태 태스크 자동 승인 재평가 루프 — 상세 설계

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| `sdd-orchestrator/src/sdd_orchestrator/main.py` | `_retry_design_approval()` 메서드 추가, `_run_cycle()`에서 호출 |
| `sdd-orchestrator/src/sdd_orchestrator/state.py` | `approval_attempts` 테이블 DDL + `get/increment_approval_attempts()` 메서드 2개 |
| `sdd-orchestrator/tests/test_design.py` | `_retry_design_approval` 관련 테스트 추가 |

---

## DoD-1: `design` 상태 태스크를 재평가하는 로직 추가

### 구현 방법

**`main.py` — `OrchestratorDaemon._retry_design_approval()` 신규 메서드**

`_run_cycle()` 내에서 `_auto_launch_approved()` **직전**에 호출. design → approved 전환이 먼저 일어나야 같은 사이클에서 즉시 launch 가능.

```python
# main.py — _run_cycle() 변경
async def _run_cycle(self) -> None:
    if self.pause_event.is_set():
        logger.info("Paused, skipping cycle")
        return

    # NEW: Re-evaluate design tasks before launching
    await self._retry_design_approval()

    # Deterministic: auto-launch approved tasks before LLM cycle
    await self._auto_launch_approved()
    # ... (기존 LLM cycle 코드 그대로)
```

**`_retry_design_approval()` 구현:**

```python
async def _retry_design_approval(self) -> None:
    """Re-evaluate 'design' status tasks for auto-approval.

    Handles the case where design.md exists but auto-approve failed
    on the initial attempt (git push failure, transient error, etc.).
    """
    from sdd_orchestrator.config import ENABLE_AUTO_DESIGN, TASKS_CURRENT_DIR
    from sdd_orchestrator.rules import can_auto_approve
    from sdd_orchestrator.tools.notify import do_notify_human
    from sdd_orchestrator.tools.task_utils import git_commit_files

    if not ENABLE_AUTO_DESIGN:
        return

    statuses = self.state.get_all_task_statuses()
    design_tasks = [tid for tid, st in statuses.items() if st == "design"]
    if not design_tasks:
        return

    for task_id in design_tasks:
        # 1. Find design.md
        matches = list(TASKS_CURRENT_DIR.glob(f"{task_id}_*/design.md"))
        if not matches:
            logger.warning("Task %s status='design' but no design.md found", task_id)
            continue

        design_path = matches[0]

        # 2. Check attempt count (무한 루프 방지)
        attempts = self.state.get_approval_attempts(task_id)
        if attempts >= 3:
            continue  # 이미 알림 발송 완료, 이후 사이클에서 스킵

        # 3. Read design content & evaluate
        design_content = design_path.read_text(encoding="utf-8")
        approved, reason = can_auto_approve(design_content)

        # 4. Increment attempt counter
        self.state.increment_approval_attempts(task_id)
        new_attempts = attempts + 1

        if approved:
            self.state.set_task_status(task_id, "approved")
            await git_commit_files(
                [str(design_path.parent)],
                f"chore(auto): {task_id} 재평가 자동 승인 — {reason}",
            )
            logger.info("Re-approval succeeded for %s: %s", task_id, reason)
        elif new_attempts >= 3:
            await do_notify_human({
                "message": (
                    f"⚠️ {task_id} 자동 승인 3회 실패 — 수동 승인 필요\n"
                    f"사유: {reason}"
                ),
                "level": "warning",
            })
            logger.warning(
                "Task %s: 3 approval attempts exhausted — reason: %s",
                task_id, reason,
            )
        else:
            logger.info(
                "Re-approval attempt %d/3 failed for %s: %s",
                new_attempts, task_id, reason,
            )
```

### 동작 정의

1. 매 사이클 `_auto_launch_approved()` 직전에 `_retry_design_approval()` 호출
2. `ENABLE_AUTO_DESIGN=0`이면 즉시 리턴 (기존 feature flag 존중)
3. `state.db`에서 `status == "design"`인 태스크를 전부 수집
4. 각 태스크의 `design.md`를 읽어 `can_auto_approve()` 재평가
5. 승인 통과 시 `approved`로 전환 + git commit
6. 같은 사이클의 `_auto_launch_approved()`에서 즉시 launch 가능

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| design.md 없이 status=design | `logger.warning` 후 스킵 |
| `ENABLE_AUTO_DESIGN=0` | 즉시 리턴. design 재평가도 auto-design 기능 범위 |
| `ENABLE_AUTO_RUN=0` | 재평가+승인 전환은 실행됨 (launch만 비활성). `ENABLE_AUTO_DESIGN`만 게이트 |
| git commit 실패 | status는 이미 DB에서 `approved`로 변경됨. commit은 best-effort |
| can_auto_approve가 항상 실패 (BLOCKER 등) | 3회 시도 후 알림 → 이후 스킵. 사람이 수동 승인 |
| design.md 빈 파일 | `can_auto_approve("")` → 파싱 실패 → 거부 → 카운트 증가 |

---

## DoD-2: `can_auto_approve(design_content)` 통과 시 `approved`로 자동 전환

### 구현 방법

위 `_retry_design_approval()` 내부에서 처리. 기존 `rules.py`의 `can_auto_approve()` 함수를 **그대로 재사용** — 변경 없음.

```python
approved, reason = can_auto_approve(design_content)
if approved:
    self.state.set_task_status(task_id, "approved")
```

### 동작 정의

- `can_auto_approve`는 순수 함수 (design_md 텍스트만 평가) — 부작용 없음
- 승인 조건: BLOCKER 없음 + 파일 6개 이하 + DB 변경 없음 + 의존성 변경 없음
- 통과 시 `state.db`의 `task_status` 테이블을 `approved`로 upsert

### 엣지 케이스

- 사람이 design.md에서 BLOCKER 제거 후 push: 다음 사이클에서 재평가 → 자동 승인됨 ✅ (attempts < 3인 경우)

---

## DoD-3: 실패 시 로그 + 재시도 (최대 3회 후 알림)

### 구현 방법

**`state.py` — `approval_attempts` 테이블 추가**

기존 `task_status` 테이블에 컬럼을 추가하지 않고, 별도 테이블 사용. 이유: approval retry는 design 재평가 전용 관심사이며, `task_status`는 범용 상태 테이블.

> 메모리 dict가 아닌 SQLite 테이블을 사용하는 이유: 오케스트레이터 재시작 시에도 카운터가 유지되어야 함. 재시작마다 리셋되면 알림이 반복 발송됨.

```python
# state.py — _init_tables()의 executescript에 추가
CREATE TABLE IF NOT EXISTS approval_attempts (
    task_id TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
```

**StateStore 메서드 2개 추가:**

```python
def get_approval_attempts(self, task_id: str) -> int:
    """Get the number of auto-approval retry attempts for a task."""
    row = self.conn.execute(
        "SELECT attempts FROM approval_attempts WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    return row["attempts"] if row else 0

def increment_approval_attempts(self, task_id: str) -> int:
    """Increment and return the approval attempt count."""
    now = datetime.now(UTC).isoformat()
    self.conn.execute(
        "INSERT INTO approval_attempts (task_id, attempts, updated_at)"
        " VALUES (?, 1, ?)"
        " ON CONFLICT(task_id) DO UPDATE SET"
        " attempts = approval_attempts.attempts + 1,"
        " updated_at = excluded.updated_at",
        (task_id, now),
    )
    self.conn.commit()
    row = self.conn.execute(
        "SELECT attempts FROM approval_attempts WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    return row["attempts"]
```

### 동작 정의

| 시도 | 동작 |
|------|------|
| 1회차 | `can_auto_approve` 실행 → 실패 → 로그 `"Re-approval attempt 1/3 failed"` |
| 2회차 | 동일 → 로그 `"Re-approval attempt 2/3 failed"` |
| 3회차 | 실패 → Slack 알림 `"⚠️ SP-XXX 자동 승인 3회 실패 — 수동 승인 필요"` + warning 로그 |
| 4회차~ | `attempts >= 3` → 즉시 `continue` (알림 중복 방지, CPU 낭비 방지) |

**카운터 리셋:** 별도 구현 불필요. 사람이 수동으로 `approved`로 전환하면 `status != "design"`이므로 재평가 대상에서 자동 제외. `approval_attempts` row는 남지만 참조되지 않음.

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| 오케스트레이터 재시작 | SQLite 영속 → 카운터 유지, 알림 중복 없음 |
| attempts=3 이후 design.md 수정 | 재평가 스킵됨. 사람이 직접 `approved`로 전환 필요 |
| Slack 알림 실패 | `do_notify_human`은 내부적으로 예외 삼킴 → 재평가 루프 영향 없음 |
| 승인 성공 시 카운터 | 리셋하지 않음 (불필요 — `approved` 전환 후 재평가 대상에서 제외) |

---

## 영향 범위

| 모듈 | 영향 |
|------|------|
| `main.py` | `_run_cycle()` 호출 순서에 1줄 추가 + `_retry_design_approval()` 메서드 추가 (~40줄) |
| `state.py` | `_init_tables()`에 DDL 1개 + 메서드 2개 (~20줄) |
| `rules.py` | 변경 없음 (기존 `can_auto_approve` 재사용) |
| `design.py` | 변경 없음 (초기 생성 경로는 그대로 유지) |
| `config.py` | 변경 없음 (`ENABLE_AUTO_DESIGN` 기존 flag 재사용) |

---

## 테스트 전략

**파일:** `sdd-orchestrator/tests/test_design.py`에 추가

### 테스트 케이스

1. **`test_retry_approves_design_task`** — status=design + design.md 존재 + BLOCKER 없음 → approved 전환 확인
2. **`test_retry_skips_when_auto_design_disabled`** — `ENABLE_AUTO_DESIGN=False` → 재평가 스킵
3. **`test_retry_skips_no_design_md`** — status=design이지만 design.md 없음 → warning 로그 + 스킵
4. **`test_retry_respects_max_attempts`** — 3회 실패 후 4회차에서 `can_auto_approve` 호출 안 됨 확인
5. **`test_retry_sends_notification_on_3rd_failure`** — 3회차 실패 시 `do_notify_human` 1회 호출 확인
6. **`test_retry_no_duplicate_notification`** — 4회차에서 `do_notify_human` 재호출 안 됨 확인
7. **`test_approval_attempts_persist`** — `StateStore.increment_approval_attempts` 영속성 확인 (SQLite 재연결 후)

### 테스트 구조

기존 `test_design.py`의 `store`, `task_env` fixture 패턴을 재사용. `_retry_design_approval`은 `OrchestratorDaemon` 인스턴스 메서드이므로, 최소한의 daemon fixture 생성:

```python
@pytest.fixture()
def daemon(tmp_path: Path) -> OrchestratorDaemon:
    """Minimal daemon for testing retry logic."""
    return OrchestratorDaemon(interval=0, db_path=tmp_path / "test.db")
```

`TASKS_CURRENT_DIR`, `ENABLE_AUTO_DESIGN`, `git_commit_files`, `do_notify_human`을 patch하여 격리 테스트.

---

## Out of Scope

- `approval_attempts` 카운터 리셋 기능 (수동 승인 시 자동 제외되므로 불필요)
- `can_auto_approve` 규칙 자체의 변경 (기존 rules.py 그대로 사용)
- Slack `/approve` 명령어 추가 (별도 태스크)
- `_heal_inconsistent_states()`와의 통합 (heal은 running 상태 전용, design과 무관)
- Lead Agent LLM 판단 로직 변경
- design.md 자동 수정/보완