---
id: SP-005
priority: P1
scope: frontend
branch: feat/SP-005-kanban-card-default-tab
created: 2026-03-20
status: done
depends_on:
---

## 무엇을
칸반 카드 클릭 시 상태에 맞는 기본 탭으로 이동

## 왜
현재 UIStore의 activeTab 기본값이 "direct"이고, 카드 클릭 시 탭을 설정하지 않아
Draft 카드를 클릭해도 Direct 탭으로 이동 + "씬이 없습니다" 표시.
Draft → Script, in_prod → Stage, rendered → Direct, published → Publish로 이동해야 함.

## 완료 기준 (DoD)
- [ ] 칸반 카드 클릭 시 스토리보드 상태에 따라 적절한 탭 설정
  - draft → Script
  - in_prod → Stage
  - rendered → Direct
  - published → Publish
- [ ] UIStore activeTab 기본값 "direct" → "script"로 변경
- [ ] 기존 기능 regression 없음

## 제약
- 변경 파일 5개 이하
- Backend 변경 없음

## 힌트
- StudioKanbanView.tsx:24 — handleCardClick에서 router.push만 하고 탭 설정 안 함
- useUIStore.ts:81 — activeTab 기본값 "direct"
- KanbanColumn.tsx — status 정보 보유
