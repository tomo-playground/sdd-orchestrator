# SP-130: design 상태 태스크 자동 승인 재평가 루프

- **branch**: feat/SP-130_design-auto-approve-loop
- **priority**: P1
- **scope**: sdd-orchestrator

## 배경

오케스트레이터의 `auto_design_task()`는 design.md를 **새로 생성할 때만** `can_auto_approve()`를 호출한다. 이미 design.md가 존재하는 태스크는 `status=design`에서 영원히 멈추는 구조적 버그가 있다.

**재현 시나리오:**
1. auto_design이 design.md 생성 + `can_auto_approve` 호출
2. 승인 실패 (또는 git push 실패 등)
3. 다음 사이클에서 design.md 존재 → `auto_design_task` 스킵
4. `_auto_launch_approved`는 `approved`만 픽업
5. 태스크가 `design` 상태에서 영원히 대기

**실제 발생:** SP-127, SP-129가 design 상태로 수시간 대기 (2026-03-31)

## DoD

- [x] `_auto_launch_approved()` 직전 또는 직후에 `design` 상태 태스크를 재평가하는 로직 추가
- [x] `can_auto_approve(design_content)` 통과 시 `approved`로 자동 전환
- [x] 실패 시 로그 남기고 다음 사이클에서 재시도 (무한 루프 방지: 최대 3회 후 알림)
