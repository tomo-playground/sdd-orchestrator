---
id: SP-007
priority: P1
scope: frontend
branch: feat/SP-007-storyboard-delete-ui
created: 2026-03-20
status: pending
depends_on:
---

## 무엇을
칸반 카드에 스토리보드 삭제(soft delete) 기능 추가

## 왜
Backend에 soft delete + restore + permanent delete API가 모두 구현돼 있지만,
프론트엔드에서 삭제할 방법이 없음. 테스트용 Draft 스토리보드가 쌓여서 정리 불가.

## 완료 기준 (DoD)
- [ ] 칸반 카드에 삭제 메뉴 (우클릭 또는 ⋯ 버튼)
- [ ] 삭제 확인 다이얼로그 (confirm)
- [ ] `DELETE /api/v1/storyboards/{id}` 호출 (soft delete)
- [ ] 삭제 후 칸반 목록에서 제거 + 토스트
- [ ] 기존 기능 regression 없음

## 제약
- 변경 파일 5개 이하
- Backend 변경 없음 (API 이미 존재)
- restore UI는 이 태스크 범위 밖

## 힌트
- Backend: `DELETE /api/v1/storyboards/{id}` → soft delete (routers/storyboard.py:101)
- KanbanCard.tsx — 현재 onClick만 있음
- Groups/Projects 삭제 UI 참고: PersistentContextBar.tsx:42-67
