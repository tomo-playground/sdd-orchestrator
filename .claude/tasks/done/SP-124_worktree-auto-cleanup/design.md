Now let me check the worktree directory structure and the `.claude/worktrees` path:
Now I have all the context needed. Let me write the design.


# SP-124: Worktree 자동 정리 — 설계 문서

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `sdd-orchestrator/src/sdd_orchestrator/tools/worktree.py` | 수정 | `_watch_process`에 worktree remove 추가, `do_launch_sdd_run`에 잔류 감지+삭제 추가 |
| `.claude/scripts/sdd-sync.sh` | 수정 | 전체 worktrees 스캔, PID 없는 worktree 일괄 삭제 로직 추가 |
| `sdd-orchestrator/tests/test_worktree.py` | 수정 | 신규 동작 테스트 추가 |

---

## DoD 1: `_watch_process` — 프로세스 종료 후 worktree remove

### 구현 방법

**파일**: `sdd-orchestrator/src/sdd_orchestrator/tools/worktree.py` — `_watch_process()` 함수

프로세스 종료(`await proc.wait()`) 직후, 기존 상태 업데이트 로직 뒤에 worktree 삭제 로직을 추가한다.

```python
async def _watch_process(proc, task_id, run_id):
    try:
        exit_code = await proc.wait()
        # ... 기존 상태 업데이트 로직 유지 ...

        # ── 신규: worktree 자동 정리 ──
        await _cleanup_worktree(task_id)
    except Exception:
        # ... 기존 예외 처리 유지 ...
        await _cleanup_worktree(task_id)
```

**신규 함수** `_cleanup_worktree(task_id: str)` 추가:

```python
async def _cleanup_worktree(task_id: str) -> None:
    """프로세스 종료 후 worktree 디렉토리를 안전하게 삭제."""
    import subprocess
    from sdd_orchestrator.config import PROJECT_ROOT

    wt_dir = PROJECT_ROOT / ".claude/worktrees" / task_id
    if not wt_dir.exists():
        return

    # 안전 체크: uncommitted 변경 확인
    if _has_uncommitted_changes(wt_dir):
        logger.warning("⚠️ worktree %s에 uncommitted 변경 있음 — 삭제 스킵", task_id)
        return

    try:
        result = subprocess.run(
            ["git", "worktree", "remove", str(wt_dir), "--force"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            logger.info("🗑️ worktree 자동 삭제: %s", task_id)
        else:
            logger.warning("worktree 삭제 실패 %s: %s", task_id, result.stderr.strip())
    except Exception:
        logger.warning("worktree 삭제 예외 %s", task_id, exc_info=True)
```

### 동작 정의

1. 프로세스가 정상 종료(exit_code=0) 또는 비정상 종료(exit_code≠0) 모두에서 worktree 삭제 시도
2. uncommitted 변경이 있으면 로그 경고만 출력하고 삭제하지 않음 (DoD 3 연계)
3. worktree 디렉토리가 이미 없으면 조용히 리턴 (멱등성)
4. 삭제 실패 시 경고 로그만 — 예외 전파하지 않음 (기존 상태 업데이트 로직에 영향 없도록)

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| worktree 이미 삭제됨 | `wt_dir.exists()` 체크 → 조용히 리턴 |
| git worktree remove 실패 (lock 등) | 경고 로그, 다음 heal/sdd-sync 사이클에서 재시도 |
| _watch_process 예외 핸들러 진입 | except 블록에서도 `_cleanup_worktree` 호출 |
| asyncio에서 subprocess 호출 | `subprocess.run`은 짧은 작업(timeout=10)이므로 blocking 허용 (기존 패턴 동일) |

---

## DoD 2: sdd-sync.sh — 전체 worktrees 스캔, PID 없는 worktree 일괄 삭제

### 구현 방법

**파일**: `.claude/scripts/sdd-sync.sh`

기존 "좀비 워크트리 정리" 섹션(line 147~160)과 "고아 워크트리 정리" 섹션(line 162~170) 사이에, **범용 PID-less worktree 정리 섹션**을 추가한다.

기존 좀비/고아 정리 로직은 SP-ID 패턴과 `agent-*`/`silly-*` 패턴만 매칭했다. 새 로직은 **모든** worktree 디렉토리를 스캔하되, claude 프로세스가 살아있는지 확인한다.

기존 고아 워크트리 정리 섹션(agent-*, silly-*)을 새 범용 로직으로 **교체**한다:

```bash
# ── PID-less 워크트리 일괄 정리 (SP-*, claude+issue-*, agent-*, 모든 패턴) ──
for WT_DIR in "$PROJECT_DIR/.claude/worktrees"/*/; do
  [ -d "$WT_DIR" ] || continue
  WT_NAME=$(basename "$WT_DIR")

  # 실행 중인 claude 프로세스가 이 worktree를 사용 중인지 확인
  # pgrep에 regex 특수문자가 들어가지 않도록 fgrep(고정 문자열) 사용
  if pgrep -af "claude" 2>/dev/null | grep -qF -- "--worktree $WT_NAME"; then
    continue  # 프로세스 살아있음 → 스킵
  fi
  if pgrep -af "claude" 2>/dev/null | grep -qF -- "--worktree ${WT_NAME} "; then
    continue
  fi

  # 안전 체크: uncommitted 변경 확인
  if git -C "$WT_DIR" status --porcelain 2>/dev/null | grep -q .; then
    echo "⚠️ worktree 스킵 (uncommitted 변경): $WT_NAME"
    continue
  fi

  git worktree remove "$WT_DIR" --force 2>/dev/null && echo "🗑️ PID-less worktree 삭제: $WT_NAME" || true
done
git worktree prune 2>/dev/null || true
```

**기존 코드 교체 범위**:
- line 162~170의 고아 워크트리 정리 (agent-*, silly-*) → 새 범용 로직으로 교체
- line 147~160의 좀비 워크트리 정리는 유지 (done/ 태스크 전용 로직이므로)

### 동작 정의

1. `.claude/worktrees/*/` 하위 **모든 디렉토리**를 스캔
2. `pgrep -af "claude"` 결과에서 `--worktree <이름>`을 **고정 문자열 검색**(`grep -qF`)으로 매칭
3. 프로세스가 없고, uncommitted 변경도 없으면 `git worktree remove --force`
4. 기존 done/ 좀비 정리(SP-ID 기반)는 그대로 유지하여 이중 안전망

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| `claude+issue-*` 같은 `+` 문자 포함 이름 | `grep -qF`(고정 문자열)로 regex 해석 방지 (DoD 4 연계) |
| 빈 worktrees 디렉토리 | glob이 매칭 안 되면 `[ -d ]` 체크에서 스킵 |
| worktree 내 uncommitted 변경 | `git status --porcelain`으로 감지 → 경고 로그만 (DoD 3 연계) |
| git worktree remove 실패 | `|| true`로 계속 진행 |

---

## DoD 3: 삭제 전 안전 체크 — uncommitted 변경 시 경고만

### 구현 방법

**파일**: `sdd-orchestrator/src/sdd_orchestrator/tools/worktree.py`

**신규 함수** `_has_uncommitted_changes(wt_dir: Path) -> bool` 추가:

```python
def _has_uncommitted_changes(wt_dir: Path) -> bool:
    """worktree에 uncommitted 변경(unstaged + staged)이 있는지 확인."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", str(wt_dir), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return True  # 확인 불가 시 안전하게 "있음" 반환
```

**적용 위치**:
- `_cleanup_worktree()` (DoD 1에서 추가)
- `_remove_stale_worktree()` (DoD 5에서 추가)

**파일**: `.claude/scripts/sdd-sync.sh`

sdd-sync.sh의 범용 정리 로직에서는 `git -C "$WT_DIR" status --porcelain`으로 동일 체크 (DoD 2 코드에 이미 포함).

### 동작 정의

1. `git status --porcelain` 출력이 비어있지 않으면 uncommitted 변경 있음
2. uncommitted 변경 있으면 **경고 로그만** 출력, `--force` 삭제 안 함
3. git 명령 자체가 실패하면 (디렉토리 손상 등) 안전하게 `True` 반환 → 삭제 스킵

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| git 디렉토리 손상 | `except`에서 `True` 반환 → 삭제 스킵 |
| staged만 있고 unstaged 없음 | `--porcelain`은 둘 다 표시 → 정상 감지 |
| untracked 파일만 존재 | `--porcelain`은 `??`로 표시 → uncommitted로 간주 → 삭제 스킵 |

---

## DoD 4: pgrep 패턴의 regex 특수문자 이슈 처리

### 구현 방법

**파일**: `.claude/scripts/sdd-sync.sh`

**문제**: 기존 코드에서 `pgrep -f "worktree.*${SP_ID}"` 패턴 사용 시 `claude+issue-*` 같은 worktree 이름의 `+`가 regex 특수문자로 해석됨.

**해결**: 두 곳 수정

1. **DoD 2의 신규 범용 정리 로직**: `pgrep -af "claude" | grep -qF -- "--worktree $WT_NAME"` 사용 (고정 문자열 매칭). 이미 DoD 2 설계에 반영됨.

2. **기존 좀비 워크트리 정리 (line 117, 154)**: `pgrep -f "worktree.*${SP_ID}"` → `pgrep -af "claude" | grep -qF -- "${SP_ID}"` 로 변경

```bash
# Before (line 117):
if pgrep -f "worktree.*${SP_ID}" > /dev/null 2>&1; then

# After:
if pgrep -af "claude" 2>/dev/null | grep -qF -- "${SP_ID}"; then
```

동일하게 line 154도 수정.

### 동작 정의

1. worktree 이름에 `+`, `*`, `.`, `[`, `]` 등 regex 특수문자가 포함되어도 정확히 매칭
2. `grep -F`는 고정 문자열 매칭이므로 regex 해석 없음
3. `--`로 옵션 종료 표시 → worktree 이름이 `-`로 시작해도 안전

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| `claude+issue-123` | `+`가 literal로 매칭됨 |
| `SP-123` (숫자만) | 기존과 동일하게 동작 |
| 프로세스 없음 (pgrep 실패) | `2>/dev/null`로 에러 무시, `grep -q` 실패 → 스킵 안 함 |

---

## DoD 5: launch_sdd_run 시 기존 worktree 잔류 감지 → 삭제 후 생성

### 구현 방법

**파일**: `sdd-orchestrator/src/sdd_orchestrator/tools/worktree.py` — `do_launch_sdd_run()` 함수

`asyncio.create_subprocess_exec` 호출 직전에 잔류 worktree 감지 및 삭제 로직 추가:

```python
async def do_launch_sdd_run(task_id: str) -> dict:
    # ... 기존 validation 로직 (parallel limit, duplicate, failures, open PR) ...

    try:
        from sdd_orchestrator.config import PROJECT_ROOT

        # ── 신규: 잔류 worktree 감지 → 삭제 ──
        _remove_stale_worktree(task_id, PROJECT_ROOT)

        proc = await asyncio.create_subprocess_exec(
            "claude", "--worktree", task_id, ...
        )
        # ... 기존 로직 ...
```

**신규 함수** `_remove_stale_worktree(task_id: str, project_root: Path) -> None`:

```python
def _remove_stale_worktree(task_id: str, project_root: Path) -> None:
    """잔류 worktree 감지 → 안전 체크 후 삭제. 재생성 충돌 방지."""
    import subprocess

    wt_dir = project_root / ".claude/worktrees" / task_id
    if not wt_dir.exists():
        return

    # 안전 체크
    if _has_uncommitted_changes(wt_dir):
        logger.warning("⚠️ 잔류 worktree %s에 uncommitted 변경 — 강제 삭제 스킵", task_id)
        # 삭제 못 하면 claude --worktree가 재사용하거나 에러 발생 → 호출자가 처리
        return

    try:
        # git worktree prune 먼저 (stale 레퍼런스 정리)
        subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True, timeout=5, cwd=str(project_root),
        )
        result = subprocess.run(
            ["git", "worktree", "remove", str(wt_dir), "--force"],
            capture_output=True, text=True, timeout=10,
            cwd=str(project_root),
        )
        if result.returncode == 0:
            logger.info("🗑️ 잔류 worktree 삭제 후 재생성: %s", task_id)
        else:
            logger.warning("잔류 worktree 삭제 실패 %s: %s", task_id, result.stderr.strip())
    except Exception:
        logger.warning("잔류 worktree 삭제 예외 %s", task_id, exc_info=True)
```

### 동작 정의

1. `do_launch_sdd_run` 호출 시 `.claude/worktrees/<task_id>/` 존재 여부 확인
2. 존재하면 uncommitted 변경 체크 → 없으면 `git worktree remove --force`
3. 삭제 성공 후 정상적으로 `claude --worktree` 실행
4. 삭제 실패 시 경고 로그만 출력, `claude --worktree` 실행은 계속 시도 (claude CLI가 자체 처리할 수 있음)

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| uncommitted 변경 있는 잔류 worktree | 경고 로그, 삭제 스킵 → claude CLI에 위임 |
| worktree 디렉토리는 있지만 git 레퍼런스 없음 | `git worktree prune` 먼저 실행하여 정리 |
| race condition (삭제 중 다른 프로세스가 생성) | `--force` 사용, 실패 시 경고만 |

---

## 영향 범위

| 모듈 | 영향 |
|------|------|
| `worktree.py` | 3개 함수 신규 (`_cleanup_worktree`, `_has_uncommitted_changes`, `_remove_stale_worktree`), 2개 함수 수정 (`_watch_process`, `do_launch_sdd_run`) |
| `sdd-sync.sh` | 고아 워크트리 정리 섹션 교체 (범용화), 기존 pgrep 패턴 2곳 수정 |
| `main.py` (`_heal_inconsistent_states`) | 변경 없음 — heal은 "빈 worktree(커밋 0개)" 전용으로 유지. `_watch_process`가 먼저 정리하므로 heal 도달 빈도 감소 |

---

## 테스트 전략

**파일**: `sdd-orchestrator/tests/test_worktree.py`

### 신규 테스트 케이스

```
class TestCleanupWorktree:
    test_cleanup_removes_worktree_on_process_exit
      - mock subprocess.run, wt_dir.exists() → True
      - _has_uncommitted_changes → False
      - git worktree remove 호출 확인

    test_cleanup_skips_when_uncommitted_changes
      - _has_uncommitted_changes → True
      - git worktree remove 호출 안 됨 확인

    test_cleanup_skips_when_dir_not_exists
      - wt_dir.exists() → False
      - subprocess.run 호출 안 됨 확인

    test_cleanup_logs_warning_on_remove_failure
      - subprocess.run returncode=1
      - 예외 없이 정상 리턴 확인

class TestRemoveStaleWorktree:
    test_removes_existing_stale_worktree
      - wt_dir.exists() → True, no uncommitted
      - git worktree prune + remove 호출 확인

    test_skips_when_no_worktree
      - wt_dir.exists() → False
      - subprocess 호출 없음

    test_skips_when_uncommitted_changes_exist
      - _has_uncommitted_changes → True
      - remove 호출 없음, 경고 로그 확인

class TestHasUncommittedChanges:
    test_returns_false_when_clean
      - git status --porcelain 출력 비어있음

    test_returns_true_when_modified
      - git status --porcelain 출력 있음 ("M file.py")

    test_returns_true_on_git_failure
      - subprocess 예외 → True 반환 (안전 기본값)

class TestWatchProcessCleanup:
    test_watch_calls_cleanup_on_success
      - exit_code=0 → _cleanup_worktree 호출 확인

    test_watch_calls_cleanup_on_failure
      - exit_code=1 → _cleanup_worktree 호출 확인

    test_watch_calls_cleanup_on_exception
      - proc.wait() 예외 → _cleanup_worktree 호출 확인

class TestLaunchWithStaleWorktree:
    test_launch_removes_stale_before_create
      - 잔류 worktree 존재 시 삭제 후 정상 launch 확인
```

### sdd-sync.sh 테스트

bash 스크립트는 단위 테스트 대상이 아님. **수동 검증** 항목:
- `claude+issue-123` 이름의 worktree 디렉토리를 만들고 sdd-sync 실행 → 삭제 확인
- uncommitted 변경이 있는 worktree → 스킵 확인
- claude 프로세스가 실행 중인 worktree → 스킵 확인

---

## Out of Scope

- `sdd-fix.sh` Phase 0의 좀비 프로세스 kill 로직 — 이 태스크는 **worktree 디렉토리 정리**에 집중. 프로세스 kill은 기존 sdd-fix.sh가 담당
- `_heal_inconsistent_states()` 수정 — heal의 "빈 worktree" 로직은 독립적 안전망으로 유지
- GitHub Actions (sentry-autofix) worktree 정리 — sdd-sync.sh의 범용 스캔이 `claude+issue-*` 패턴도 커버하므로 별도 처리 불필요
- worktree 이름 패턴 표준화 — 기존 4곳의 이름 패턴은 그대로 유지

---

## BLOCKER

없음. 외부 의존성 추가 없음, DB 스키마 변경 없음, 아키텍처 변경 없음.