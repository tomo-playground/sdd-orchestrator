# SP-123 상세 설계: 태스크 상태 SSOT 통일 — state.db 단일화

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `.claude/commands/sdd-design.md` | spec.md status 읽기/쓰기 제거, state.db only |
| `.claude/commands/sdd-run.md` | spec.md status 읽기/쓰기 제거, state.db only |
| `.claude/scripts/sdd-sync.sh` | spec.md status 쓰기(`sed`) 제거 |
| `sdd-orchestrator/src/sdd_orchestrator/tools/design.py` | `_read_spec_status` fallback 제거 |
| `sdd-orchestrator/src/sdd_orchestrator/tools/task_utils.py` | `parse_spec_status` 함수 제거 |
| `docs/04_operations/ORCHESTRATOR_GUIDE.md` | 상태 확인 방법 문서화 |
| `docs/guides/SDD_WORKFLOW.md` | status 관리 방식 변경 반영 |

## 핵심 원칙

- **state.db가 유일한 SSOT** — 모든 상태 읽기/쓰기는 state.db
- **spec.md에서 status 필드 제거** — 혼란 원천 차단
- **sqlite3 CLI 의존** — sdd-design/sdd-run은 Bash로 sqlite3 호출
- **경로 규칙**: 항상 `/home/tomo/Workspace/shorts-producer/.sdd/state.db` 절대 경로 사용. `git worktree list` 방식은 cwd에 따라 sdd-orchestrator 루트를 반환하는 버그 있음

## DoD별 설계

### DoD-1: spec.md 템플릿에서 status 필드 제거

**구현 방법**:
- `sdd-orchestrator/src/sdd_orchestrator/tools/tasks.py`의 spec 생성 로직에서 `status:` 행 제거
- 기존 current/done/ 디렉토리의 spec.md에서 `status:` 행 일괄 제거 (sed 스크립트 1회 실행)

**before**: `- **status**: approved`
**after**: 행 자체 삭제

**엣지 케이스**: done/ 파일의 status 제거해도 이력에 영향 없음 (git log에 남아있음)
**Out of Scope**: spec.md의 다른 필드(branch, priority 등)는 유지

### DoD-2: sdd-design 명령 — state.db only

**구현 방법**: `.claude/commands/sdd-design.md` 수정

**Phase 5 (설계 완료)**:
- spec.md status 변경 제거
- state.db만 업데이트: `sqlite3 /home/tomo/Workspace/shorts-producer/.sdd/state.db "INSERT OR REPLACE ..."`

**Phase 6-A (승인)**:
- spec.md에 `approved_at` 기록은 유지 (메타데이터)
- spec.md `status:` 변경 제거
- state.db만 업데이트

**Phase 1 (로드 시 상태 확인)**:
- `sqlite3 ... "SELECT status FROM task_status WHERE task_id='SP-NNN';"` 로 조회
- 결과 없으면 `pending` 취급

### DoD-3: sdd-run 명령 — state.db only

**구현 방법**: `.claude/commands/sdd-run.md` 수정

**Step 2 (승인 확인)**: state.db에서 조회 (spec.md fallback 제거)
**Step 7 (실행 시)**: state.db만 `running`으로 업데이트. spec.md 수정 없음.

### DoD-4: sdd-sync.sh — spec.md status 쓰기 제거

**구현 방법**: `.claude/scripts/sdd-sync.sh`

**before**: `sed -i 's/^status:.*/status: done/' "$CURRENT_DIR/spec.md"` (77행)
**after**: 행 삭제. state.db UPDATE만 유지 (79행 이미 존재).

### DoD-5: 오케스트레이터 fallback 제거

**design.py**:
- `_read_spec_status()` 함수 제거
- `do_run_auto_design()`에서 `_read_spec_status` 호출 → `_state_store.get_task_status()` 직접 사용

**task_utils.py**:
- `parse_spec_status()` 함수 제거 (더 이상 호출하는 곳 없음)

**영향 범위**: design.py만. backlog.py, tasks.py, worktree.py는 이미 state.db only.

### DoD-6: 기존 spec.md status 일괄 제거

**1회성 스크립트**:
```bash
# current/ + done/ 모든 spec.md에서 status 행 제거
find .claude/tasks -name "spec.md" -exec sed -i '/^- \*\*status\*\*:/d; /^status:/d' {} +
```

git commit으로 기록.

### DoD-7: 문서 업데이트

**ORCHESTRATOR_GUIDE.md**:
- 상태 확인: `sqlite3 .sdd/state.db "SELECT task_id, status FROM task_status ORDER BY updated_at DESC;"`
- spec.md에는 status 없음 명시

**SDD_WORKFLOW.md**:
- 태스크 상태 관리 섹션에 state.db SSOT 명시
- spec.md는 스펙/설계 문서 전용, 상태 관리 아님

## 테스트 전략

1. sdd-orchestrator 단위 테스트: `test_design.py`에서 `_read_spec_status` 호출 제거 확인
2. sdd-orchestrator 단위 테스트: `test_task_utils.py` 제거 또는 `parse_spec_status` 테스트 제거
3. 통합 확인: 오케스트레이터 재시작 후 `scan_backlog` → state.db에서 상태 정상 조회
4. sdd-sync 수동 실행 → spec.md에 status 안 쓰는지 확인
