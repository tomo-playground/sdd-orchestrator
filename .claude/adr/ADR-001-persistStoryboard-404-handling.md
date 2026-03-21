# ADR-001: persistStoryboard 404 처리

- **Status**: Accepted (Supersedes previous 404→재생성 로직)
- **Date**: 2026-03-21 (소급 기록, 원결정 2026-03-20)
- **Relates**: INV-1, INV-2, INV-3

## Context

`persistStoryboard()`의 PUT 요청이 404를 반환할 때의 처리 방식이 여러 세션에서 충돌했다.

### 타임라인

1. **`5629d1f2` (Sonnet 세션)**: 404 → `storyboardId = null` 후 POST 재생성 (재귀 호출)
   - 의도: "DB에 아직 없는 경우" 자동 생성으로 UX 개선
2. **`5b180d72` (Opus 세션, PR #46)**: 칸반에서 soft delete 기능 추가
   - 문제: 1번 로직이 "삭제된 것"과 "아직 없는 것"을 구분하지 못함
3. **`71dbf6a0` (SP-039)**: Draft 부활 버그 발생 → 404 재생성 로직 제거

### 근본 원인

두 AI 세션이 **동일 함수의 다른 시나리오**를 각각 처리하면서, 상대방의 시나리오를 인지하지 못함.
- Session A: "404 = 아직 생성 안 됨 → 생성하자"
- Session B: "삭제 → soft delete" (404 가능성 미고려)

## Decision

1. **404 = 삭제된 것으로 간주** — 자동 재생성하지 않는다 (INV-1)
2. **autoSave는 UPDATE(PUT)만 수행** — CREATE(POST)를 호출하지 않는다 (INV-2)
3. **404 수신 시 스토어 전체 리셋** — stale 데이터 방치 금지 (INV-3)
4. **새 엔티티 생성은 사용자 명시적 액션으로만** — "새 영상" 버튼 → `ensureDraftStoryboard()`

## Consequences

### Positive
- 삭제된 엔티티가 부활하지 않음
- autoSave와 delete의 race condition 해소
- 엔티티 lifecycle이 명확해짐 (생성/수정/삭제 각각 별도 경로)

### Negative
- "DB에 아직 없는" 케이스를 자동 처리하지 못함 → Draft 선생성 패턴(ADR-002)으로 보완

### 관련 커밋
- `71dbf6a0`: 404 재생성 제거 + autoSave 삭제 방어 (#72)
- `c5b74b73`: CodeRabbit 리뷰 반영 — cancelPendingSave 범위 + 404 스토어 리셋 (#75)
