---
id: SP-029
priority: P2
scope: frontend
branch: feat/SP-029-script-canvas-split-view
created: 2026-03-21
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
Script Canvas 분할 뷰 — 좌 채팅 + 우 씬 프리뷰

## 왜
- 현재 Script 탭은 채팅 전용 — 생성된 씬을 확인하려면 Stage 탭으로 이동 필요
- 채팅하면서 실시간으로 씬 프리뷰를 보면 워크플로우 효율 향상
- ChatGPT Canvas 패턴 참고

## 완료 기준 (DoD)
- [ ] Script 탭 2-pane 레이아웃 (좌: 채팅, 우: 씬 프리뷰)
- [ ] 프리뷰 패널에 씬 카드 미니 버전 표시
- [ ] 분할 비율 조정 가능 (드래그 리사이즈)
- [ ] 모바일/좁은 화면에서 단일 패널 폴백
- [ ] 기존 기능 regression 없음

## 제약
- 건드리면 안 되는 것: 채팅 컴포넌트 내부 로직
- Stage 탭의 SceneCard와 중복 코드 최소화 (공유 컴포넌트)

## 힌트
- 명세: `docs/99_archive/features/SCRIPT_COLLABORATIVE_UX.md` §P2
- 관련 파일: `frontend/app/components/studio/ScriptTab.tsx`, `frontend/app/components/scene/SceneCard.tsx`
