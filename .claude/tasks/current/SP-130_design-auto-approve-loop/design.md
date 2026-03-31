# SP-130: design 상태 태스크 자동 승인 재평가 — 상세 설계

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `sdd-orchestrator/src/sdd_orchestrator/main.py` | `_auto_approve_design_tasks()` 메서드 추가 + `_run_cycle`에서 호출 |

## DoD-1: design 상태 태스크 재평가 로직

### 구현 방법

`OrchestratorDaemon`에 `_auto_approve_design_tasks()` 메서드를 추가한다.
`_run_cycle()`에서 `_auto_launch_approved()` 직전에 호출하여, design → approved 전환 후 같은 사이클에서 바로 launch까지 이어지게 한다.

```python
async def _auto_approve_design_tasks(self) -> None:
    """design 상태 태스크를 can_auto_approve()로 재평가 → approved 전환."""
```

### 동작 정의

**Before**: design 상태 태스크가 다음 사이클에서도 design으로 남음
**After**:
1. `parse_backlog()`에서 `spec_status == "design"` 태스크 필터
2. 각 태스크의 `design.md` 읽기
3. `can_auto_approve(design_content)` 호출
4. 통과 → `state.set_task_status(task_id, "approved")` + 로그
5. 실패 → 실패 횟수 카운트 (메모리 dict), 로그

### 무한 루프 방지

- 클래스 인스턴스 변수 `_approve_fail_count: dict[str, int]` 사용
- 실패 시 카운트 증가, 3회 초과 시 `notify_human(level="warning")` 호출 + 해당 태스크 재시도 중단
- 승인 성공 시 카운트 제거

### 엣지 케이스

| 상황 | 처리 |
|------|------|
| design.md 파일 없음 | 스킵 + warning 로그 |
| design.md 빈 파일 | can_auto_approve 실패 → 카운트 증가 |
| ENABLE_AUTO_RUN=0 | 승인 전환은 실행 (launch만 비활성화이므로) |

### 영향 범위

- `_auto_launch_approved()`와 순서 의존: 반드시 먼저 호출해야 같은 사이클에서 launch 가능
- `can_auto_approve` 규칙은 기존 그대로 사용 (변경 없음)

### 테스트 전략

- design 상태 태스크 + 승인 가능 design.md → approved 전환 확인
- BLOCKER 포함 design.md → design 유지 확인
- 3회 실패 후 알림 발송 + 재시도 중단 확인

### Out of Scope

- `can_auto_approve` 규칙 변경
- design.md 자동 수정/보완
- Lead Agent LLM 판단 로직 변경
