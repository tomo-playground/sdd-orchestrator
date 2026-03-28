---
id: SP-095
priority: P2
scope: frontend
branch: feat/SP-095-scene-context-provider
created: 2026-03-26
status: done
approved_at: 2026-03-26
depends_on: SP-021, SP-094
label: feature
---

## 무엇을 (What)
기존 SceneContext.tsx 활성화 + TTS 4필드 추가. SceneProvider로 SceneCard 래핑 (기존 props 유지).

## 왜 (Why)
SceneCard props 40개 drilling 해소의 첫 단계. Context가 이미 구현되어 있으나 미사용 상태.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase C — SP-055a 항목

## 완료 기준 (DoD)
- [ ] SceneContext에 TTS 관련 4개 필드 추가 (ttsState, onTTSPreview, onTTSRegenerate, audioPlayer)
- [ ] ScenesTab에서 SceneProvider로 SceneCard 래핑
- [ ] SceneCard 내부에서 `useSceneContext()` 접근 가능
- [ ] **기존 SceneCard props 모두 유지** (호환성, 이 태스크에서 제거하지 않음)
- [ ] 기존 Direct 탭 모든 기능 동일 동작 (E2E 통과)
- [ ] 시각적 변경 없음 (VRT 차이 0)

## 힌트
- `SceneContext.tsx` — SceneDataContext 22필드, SceneCallbacksContext 17필드 이미 정의
- `ScenesTab.tsx` — SceneCard 호출부를 SceneProvider로 래핑
- `SceneCard.tsx` — useSceneContext() 접근 가능하도록 구조 변경

## 상세 설계 (How)
→ `design.md` 참조

**요약**:
1. `SceneContext.tsx` — `SceneDataContext`에 `ttsState` 1필드, `SceneCallbacksContext`에 `onTTSPreview`, `onTTSRegenerate`, `audioPlayer` 3필드 추가
2. `ScenesTab.tsx` — `SceneProvider` import + SceneCard를 `<SceneProvider value={data+callbacks}>` 로 래핑. 기존 props 제거 없음
3. `SceneCard.tsx` — `useSceneContext()` import + 접근 검증 1줄 추가 (선택적)
4. 테스트: Context 유닛 테스트 + ScenesTab 통합 테스트 + 기존 E2E/VRT 활용
