---
id: SP-006
priority: P2
scope: frontend
branch: feat/SP-006-publish-tab-draft-ux
created: 2026-03-20
status: pending
depends_on:
---

## 무엇을
Publish 탭 Draft 상태(씬 0개) UX 개선 — 비활성 시각 명확화

## 왜
씬 0개에서 Render 버튼이 disabled지만 시각적으로 활성처럼 보임 (opacity-40 단독).
TTS "Issues Found" 빨간 표시가 Draft에서 불필요한 불안감 유발.
경고 메시지 이중 표시 (배너 + 인라인).

## 완료 기준 (DoD)
- [ ] Render 버튼 disabled 스타일 강화 (bg-zinc-200 text-zinc-400 등 명시 배경색)
- [ ] 씬 0개일 때 TTS 확인 섹션 숨김 또는 축소 placeholder
- [ ] disabledReason 인라인 배지 제거 (배너로 충분)
- [ ] 기존 기능 regression 없음

## 제약
- 변경 파일 5개 이하
- Backend 변경 없음

## 힌트
- RenderSidePanel.tsx:107 — disabled={!canRender || isRendering}
- usePublishRender.ts:76-81 — canRender 로직
- PreRenderReport — TTS Issues Found 표시
- 경고 배너: PublishTab.tsx 상단
