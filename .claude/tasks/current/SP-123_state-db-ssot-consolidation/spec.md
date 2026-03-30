# SP-123: 태스크 상태 SSOT 통일 — state.db 단일화

- **status**: pending
- **branch**: feat/SP-123_state-db-ssot-consolidation
- **priority**: P1
- **scope**: sdd-orchestrator, .claude/commands, .claude/scripts
- **assignee**: AI
- **created**: 2026-03-31
- **depends_on**: SP-120

## 배경

SP-120에서 state.db를 도입했지만, spec.md의 status 필드가 여전히 존재하여 dual-write 상태.
오케스트레이터는 state.db만 업데이트하므로 spec.md가 stale해지고, Claude 명령은 spec.md를 읽어서 판단 오류 발생 가능.

### 현재 상태 (이원화)

| 컴포넌트 | 읽기 | 쓰기 |
|---------|------|------|
| 오케스트레이터 | state.db | state.db만 |
| sdd-design | spec.md | spec.md + state.db (임시 dual-write) |
| sdd-run | state.db → spec.md fallback | spec.md + state.db (임시 dual-write) |
| sdd-sync.sh | spec.md (branch) | state.db + 파일 이동 |

## 목표

**state.db를 유일한 SSOT로.** spec.md에서 status 필드 제거.

## DoD (Definition of Done)

- [ ] spec.md 템플릿에서 `status:` 필드 제거 (sdd-run, sdd-design, tasks.py의 spec 생성 로직)
- [ ] sdd-design 명령: state.db만 읽기/쓰기. spec.md status 조작 제거
- [ ] sdd-run 명령: state.db만 읽기/쓰기. spec.md status 조작 제거
- [ ] sdd-sync.sh: spec.md status 쓰기 제거 (state.db만 업데이트)
- [ ] sdd-fix.sh: spec.md status 참조가 있으면 제거
- [ ] 오케스트레이터: `_read_spec_status` fallback 제거 (state.db only)
- [ ] 기존 spec.md의 status 필드 일괄 제거 (current/ + done/ 모두)
- [ ] 상태 확인 CLI 방법 문서화: `sqlite3 .sdd/state.db "SELECT * FROM task_status WHERE task_id='SP-NNN';"`
- [ ] ORCHESTRATOR_GUIDE.md 업데이트

## 수정 대상 파일

- `.claude/commands/sdd-design.md`
- `.claude/commands/sdd-run.md`
- `.claude/scripts/sdd-sync.sh`
- `sdd-orchestrator/src/sdd_orchestrator/tools/design.py`
- `sdd-orchestrator/src/sdd_orchestrator/tools/backlog.py`
- `sdd-orchestrator/src/sdd_orchestrator/tools/task_utils.py`
- `sdd-orchestrator/src/sdd_orchestrator/tools/tasks.py`
- `docs/04_operations/ORCHESTRATOR_GUIDE.md`
- `docs/guides/SDD_WORKFLOW.md`
