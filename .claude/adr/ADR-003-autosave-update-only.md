# ADR-003: autoSave UPDATE-only 설계

- **Status**: Accepted
- **Date**: 2026-03-21 (소급 기록, 원결정 2026-03-20)
- **Relates**: INV-2, ADR-001, ADR-002

## Context

autoSave는 2초 debounce로 스토리보드를 자동 저장하는 메커니즘이다.
여러 세션에 걸쳐 autoSave 관련 버그가 반복 발생했다:

| 커밋 | 버그 |
|------|------|
| `6f4591bd` | 이미지 생성 중 autoSave race → image_asset_id null 덮어쓰기 |
| `eb01eaf8` | Casting SSOT race → Speaker B 매핑 소실 |
| `47dfa8dc` | 그룹/프로젝트 전환 시 Network Error |
| `30628f2a` | 무한 재시도 → 서버 부하 |
| `71dbf6a0` | 404→재생성 → Draft 부활 (ADR-001) |

### 근본 패턴

autoSave가 **너무 많은 책임**을 가지고 있었다:
- 기존 데이터 저장 (UPDATE) ← 본연의 역할
- 새 엔티티 생성 (CREATE) ← 부작용
- 에러 복구 (재시도/재생성) ← 위험한 자율 판단

## Decision

autoSave의 책임을 **UPDATE만**으로 엄격히 제한한다 (INV-2).

1. **UPDATE만**: `PUT /storyboards/{id}` — 기존 storyboard 저장
2. **CREATE 금지**: POST 호출 절대 금지. 새 생성은 사용자 액션 전용 (ADR-002)
3. **storyboardId null이면 스킵**: 저장 대상이 없으면 아무 것도 하지 않음
4. **실패 시 3회 재시도 후 중단**: 무한 재시도 금지, 사용자에게 알림
5. **404 수신 시 스토어 리셋**: 저장 대상이 삭제됨 → 스토어 정리 (INV-3)

## Consequences

### Positive
- autoSave의 side effect 제거 → 예측 가능한 동작
- race condition 공격 표면 축소
- 엔티티 lifecycle 명확화 (생성 = 사용자, 저장 = autoSave, 삭제 = 사용자)

### Negative
- autoSave가 "영리하게" 에러를 복구하지 못함
- 사용자가 명시적으로 재생성해야 하는 경우 발생 가능

### 관련 커밋
- `71dbf6a0`: autoSave storyboardId null 가드 추가 (#72)
- `30628f2a`: 3회 연속 실패 시 일시 중단
- `c5b74b73`: cancelPendingSave 범위 제한 (#75)
