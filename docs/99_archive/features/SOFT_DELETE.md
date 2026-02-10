# Soft Delete

> 상태: **완료** (Phase 6-7 #4-6) | 설계 문서: [SOFT_DELETE.md](../../03_engineering/backend/SOFT_DELETE.md)

## 구현 완료 사항

- `SoftDeleteMixin` (`deleted_at` 컬럼) + Alembic 마이그레이션 적용
- 적용 모델: **Storyboard**, **Character**, **Scene**
- Backend: trash/restore/permanent-delete 엔드포인트 구현
- Frontend: Manage > Trash 탭 구현 (복원/영구삭제 UI)
- 모든 GET/PUT/PATCH 쿼리에 `deleted_at.is_(None)` 필터 적용

## 배경

현재 모든 삭제가 Hard Delete로 동작하여 데이터가 영구 손실됨.
Storyboard 삭제 시 Scene, Tags, Assets까지 CASCADE로 일괄 삭제되어 복구 불가.

## 목표

- 사용자 작업물(Storyboard, Character, PromptHistory)의 실수 삭제 복구 지원
- 삭제 이력 추적 가능
- 30일 보관 후 자동 영구 삭제

## 범위

### 1차 적용 대상

| 모델 | 이유 |
|------|------|
| **Storyboard** | 가장 큰 작업 단위, CASCADE 연쇄 삭제 방지 |
| **Character** | LoRA/Tag 연관, Reference 이미지 보유 |
| **PromptHistory** | 사용 이력 보존 가치 |

### 적용 제외

Tag, LoRA, SDModel, Embedding, StyleProfile, ActivityLog — 관리자 데이터로 삭제 빈도 낮음.

## 사용자 시나리오

### 삭제

1. 사용자가 Storyboard/Character/PromptHistory 삭제 클릭
2. 항목이 휴지통으로 이동 (목록에서 사라짐)
3. Toast: "휴지통으로 이동됨 (30일 후 자동 삭제)"

### 복원

1. Manage > Trash 탭 진입
2. 삭제된 항목 목록 확인 (삭제일, 남은 보관일 표시)
3. 복원 버튼 클릭 → 원래 목록에 복귀

### 영구 삭제

1. Trash 탭에서 영구 삭제 클릭
2. 확인 모달: "이 작업은 되돌릴 수 없습니다"
3. 확인 시 DB + Assets 완전 삭제

## UI 요구사항

| 위치 | 변경 |
|------|------|
| Studio 삭제 버튼 | 동작만 변경 (hard → soft), UI 동일 |
| Manage > Trash 탭 | 신규. 삭제된 항목 목록, 복원/영구삭제 버튼 |

## 수락 기준

| # | 기준 | 상태 |
|---|------|------|
| 1 | 삭제된 항목이 기본 목록에 표시되지 않음 | [x] |
| 2 | Trash에서 삭제된 항목 조회 가능 | [x] |
| 3 | 복원 시 원래 상태로 완전 복귀 (하위 Scene 포함) | [x] |
| 4 | 영구 삭제 시 기존 cleanup 로직 정상 동작 | [x] |
| 5 | 30일 경과 항목 자동 영구 삭제 | [ ] |
| 6 | 기존 테스트 전체 통과 + 신규 테스트 추가 | [x] |
