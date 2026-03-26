---
id: SP-096
priority: P2
scope: frontend
branch: feat/SP-096-props-to-context
created: 2026-03-26
status: pending
depends_on: SP-095
label: feature
---

## 무엇을 (What)
SceneCard props 40개 → 5개로 축소. 서브컴포넌트 6개+ useSceneContext() 전환.

## 왜 (Why)
Props drilling 해소. ScenesTab의 13개+ action handler glue code를 SceneProvider 내부로 이동.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase C — SP-055b 항목

## 완료 기준 (DoD)
- [ ] SceneCard props: top-level 40개 → 5개 이하 (scene, sceneIndex + 최소 제어)
- [ ] 서브컴포넌트 6개 이상이 useSceneContext()로 데이터/콜백 소비
- [ ] ScenesTab의 action handler glue code가 SceneProvider 내부로 이동
- [ ] 기존 Direct 탭 모든 기능 동일 동작 (E2E 통과)
- [ ] 시각적 변경 없음 (VRT 차이 0)

## 힌트
- `SceneCard.tsx` — props 축소
- `SceneImagePanel.tsx`, `SceneActionBar.tsx`, `SceneEssentialFields.tsx`, `ScenePromptFields.tsx`, `SceneSettingsFields.tsx`, `SceneGeminiModals.tsx` — useSceneContext() 전환
- `ScenesTab.tsx` — 불필요 props 제거
