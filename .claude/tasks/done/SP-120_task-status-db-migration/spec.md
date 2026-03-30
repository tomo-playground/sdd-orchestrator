# SP-120: 태스크 상태를 spec.md에서 state.db로 분리

branch: feat/SP-120_task-status-db-migration
status: running | approved_at: 2026-03-30
priority: P1
scope: infra

## 배경

현재 태스크 상태(`status: approved/running/done`)를 git-tracked 파일인 spec.md에서 관리한다.
오케스트레이터가 브랜치를 오가거나, 워크트리에서 PR 머지 후 main pull 시
spec.md의 status 값이 덮어씌워지거나 충돌하여 완료된 태스크가 미완료로 보고되는 문제 발생.

### 근본 원인
- `_update_spec_status()`가 spec.md를 로컬 수정 (커밋 없음)
- git 브랜치 전환/머지 시 로컬 수정이 유실 또는 충돌
- `scan_backlog` → LLM이 꼬인 status를 읽고 잘못된 메시지 전송

## DoD (Definition of Done)

1. 태스크 상태(`pending/approved/running/done`)를 `state.db`에서 관리
2. spec.md에서 `status:` 필드 제거 (스펙 정의만 유지)
3. `_update_spec_status()` → state.db UPDATE로 전환
4. `parse_backlog()` / `_enrich_from_specs()` → state.db에서 status 조회
5. `_heal_inconsistent_states()` → state.db 기반으로 동작
6. `scan_backlog` MCP 도구 결과에 정확한 status 반영
7. 기존 테스트 통과 + 브랜치 전환 시 status 유지 검증
