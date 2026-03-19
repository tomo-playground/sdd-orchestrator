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

## 구현 계획 (Frontend Dev 리뷰)

### 수정 순서
| 순서 | 파일 | 변경 |
|------|------|------|
| 1 | `RenderSidePanel.tsx` L142-146 | disabledReason 인라인 배지 삭제 (6줄) |
| 2 | `RenderSidePanel.tsx` L97, L109 | disabled 스타일 조건 분기 (bg-zinc-300 text-zinc-400) |
| 3 | `PublishTab.tsx` L107-139 | `scenes.length > 0` 조건부 래핑 (TTS 섹션 숨김) |

### 참고
- usePublishRender.ts:76 canRender 로직 변경 불필요 (씬 0개 → false 정상)
- disabled:opacity-40 제거 → 조건부 클래스로 대체
- PublishTab.tsx L61-71 상단 배너는 유지 (SSOT)
- TTS 섹션 숨기면 PreRenderReport useEffect도 언마운트 → 불필요 API 호출 방지
