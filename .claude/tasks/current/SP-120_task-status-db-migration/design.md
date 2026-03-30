# SP-120: Design — 태스크 상태를 spec.md에서 state.db로 분리

## 현황 요약

### 문제
spec.md의 `status:` 필드가 git-tracked 파일이라 브랜치 전환/머지 시 덮어쓰기/유실 발생.
오케스트레이터가 꼬인 status를 읽고 LLM이 잘못된 메시지 전송.

### 현재 구조
- **status 읽기**: 8곳 (backlog.py 2, task_utils.py 1, tasks.py 2, design.py 1, main.py 2)
- **status 쓰기**: 6곳 (worktree.py 4, design.py 2, tasks.py 1, sdd-sync.sh 1)
- **파싱 로직**: 4가지 (regex, manual split, line iteration, frontmatter)
- **이중 SSOT**: spec.md (상태) vs state.db (run 추적) — 불일치 가능

## 설계

### 핵심 변경: task_status 테이블 신설

```sql
CREATE TABLE IF NOT EXISTS task_status (
    task_id   TEXT PRIMARY KEY,          -- SP-NNN
    status    TEXT NOT NULL DEFAULT 'pending',  -- pending/design/approved/running/done
    updated_at TEXT NOT NULL             -- ISO 8601 UTC
);
```

state.db에 추가. git 영향 없음.

### 상태 읽기/쓰기 단일화

**신규 함수** (`state.py`):

```python
def get_task_status(self, task_id: str) -> str:
    """task_status 테이블에서 status 조회. 없으면 'pending'."""

def set_task_status(self, task_id: str, status: str) -> None:
    """task_status UPSERT. updated_at 자동 갱신."""

def get_all_task_statuses(self) -> dict[str, str]:
    """전체 태스크 상태 맵 반환. {task_id: status}"""
```

### 변경 지점 (파일별)

#### 1. state.py — 스키마 + API 추가
- `_init_db()`: `task_status` 테이블 CREATE
- `get_task_status()`, `set_task_status()`, `get_all_task_statuses()` 추가

#### 2. backlog.py — 읽기 경로 전환
- `parse_backlog()`: `state_store` 파라미터 추가 (선택적, DI)
- `_enrich_from_specs()`: `parse_spec_status()` → `state_store.get_task_status()`
- `_discover_current_tasks()`: spec.md 수동 파싱에서 status 부분 제거, state.db 조회로 전환
- spec.md에서는 priority, scope, depends_on 등 **스펙 메타데이터만** 파싱

#### 3. worktree.py — 쓰기 경로 전환
- `_update_spec_status()` 삭제
- 4개 호출 지점 → `_state_store.set_task_status(task_id, status)` 직접 호출
- spec.md 파일 수정 완전 제거

#### 4. design.py — 쓰기 경로 전환
- `_update_spec_status()` 삭제
- `auto_design_task()` → `state_store.set_task_status(task_id, "design"/"approved")`

#### 5. tasks.py — 읽기/쓰기 전환
- `do_read_task()`: `parse_spec_status()` → `state_store.get_task_status()`
- `do_approve_design()`: spec.md 수정 → `state_store.set_task_status(task_id, "approved")`
- spec.md에는 status 라인 더 이상 안 씀

#### 6. main.py — 읽기/쓰기 전환
- `_heal_inconsistent_states()`: spec.md 파싱 → `self.state.get_task_status()`
- `_gather_daily_summary()`: spec.md 파싱 → `self.state.get_all_task_statuses()`

#### 7. sdd-sync.sh — done 전이
- `sed -i 's/^status:.*/status: done/'` 제거
- 대신: `sqlite3 .sdd/state.db "UPDATE task_status SET status='done' WHERE task_id='SP-NNN'"`
- 또는: sdd-sync 후 오케스트레이터가 done/ 감지 시 자동 set_task_status

#### 8. task_utils.py — 정리
- `parse_spec_status()`: deprecated 또는 삭제
- `update_spec_status()`: 삭제

### spec.md에서 status 필드 처리

**제거 방식**: spec.md에서 `status:` 라인 완전 제거.
- spec.md는 스펙 정의(배경, DoD, scope, depends_on, branch)만 유지
- 상태는 state.db가 SSOT
- 기존 done/ 태스크의 status 라인은 히스토리 보존 (수정 안 함)

### 마이그레이션 (기존 데이터)

startup 시 1회 실행:
1. `current/` 디렉토리의 모든 spec.md에서 status 파싱
2. `task_status` 테이블에 UPSERT (없는 경우만)
3. 이후 spec.md의 status 라인은 무시

```python
def _migrate_spec_status_to_db(self) -> None:
    """One-time: seed task_status from current/ spec files."""
    for spec in TASKS_CURRENT_DIR.glob("SP-*_*/spec.md"):
        task_id = spec.parent.name.split("_")[0]
        existing = self.get_task_status(task_id)
        if existing != "pending":  # 이미 DB에 있으면 skip
            continue
        content = spec.read_text(encoding="utf-8")
        status = parse_spec_status(content)  # 최초 1회만 사용
        self.set_task_status(task_id, status)
```

### 영향 범위 체크리스트

| 파일 | 변경 | 크기 |
|------|------|------|
| `state.py` | 테이블 + 3 메서드 추가 | S |
| `backlog.py` | status 소스 전환 | M |
| `worktree.py` | `_update_spec_status()` 삭제 → DB 호출 | S |
| `design.py` | `_update_spec_status()` 삭제 → DB 호출 | S |
| `tasks.py` | read/approve 전환 | S |
| `main.py` | heal/summary 전환 | M |
| `task_utils.py` | parse/update 함수 삭제 | S |
| `sdd-sync.sh` | sed 제거, sqlite3 또는 파일 감지 | S |
| `tests/test_backlog.py` | state_store mock 추가 | M |

### 리스크

- **sdd-sync.sh에서 sqlite3 직접 호출**: shell → DB 의존성 추가. 대안으로 오케스트레이터가 done/ 감지 시 자동 전이하는 방식이 더 깔끔함.
- **외부 도구가 spec.md status를 기대하는 경우**: 현재 없음 (LLM만 scan_backlog 사용).
