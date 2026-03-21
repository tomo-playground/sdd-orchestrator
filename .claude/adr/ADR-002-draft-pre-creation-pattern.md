# ADR-002: Draft 선생성 패턴

- **Status**: Accepted
- **Date**: 2026-03-21 (소급 기록, 원결정 2026-03-14)
- **Relates**: ADR-001 (404 재생성 제거의 보완책)

## Context

ADR-001에서 404→자동 재생성을 금지함에 따라, "새 영상" 진입 시 DB에 storyboard가 없는 상태에서
첫 채팅 메시지가 소실되는 문제가 발생했다.

### 문제 시나리오
1. 사용자가 "새 영상" 클릭
2. storyboardId = null 상태에서 채팅 입력
3. AI 파이프라인이 storyboard 생성 시도 → 동시에 autoSave도 시도
4. Race condition → 첫 메시지 소실 또는 중복 생성

## Decision

**"새 영상" 클릭 시 즉시 Draft storyboard를 DB에 생성**한다 (`ensureDraftStoryboard()`).

1. 사용자가 "새 영상" 클릭 → 즉시 POST `/storyboards` (status: draft)
2. storyboardId가 확보된 상태에서 채팅 시작
3. autoSave는 이미 존재하는 storyboard에 PUT만 수행 (ADR-001 INV-2 준수)
4. 사용자가 채팅 없이 이탈하면 빈 Draft가 남음 → 칸반에서 삭제 가능

## Consequences

### Positive
- 첫 메시지 소실 버그 근본 해결
- autoSave가 항상 PUT만 사용 → ADR-001과 일관성
- storyboardId가 항상 존재 → null 체크 분기 감소

### Negative
- 빈 Draft가 생성될 수 있음 (사용자가 클릭만 하고 이탈)
- 향후 Draft 자동 정리 로직 필요할 수 있음

### 관련 커밋
- `024d0911`: draft 선생성 v2 (#68)
- `fec0444d`: 첫 구현 (#67)
