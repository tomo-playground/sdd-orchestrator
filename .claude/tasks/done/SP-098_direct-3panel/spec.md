---
id: SP-098
priority: P2
scope: frontend
branch: feat/SP-098-direct-3panel
created: 2026-03-26
status: done
approved_at: 2026-03-26
depends_on: SP-096, SP-097
label: feature
---

## 무엇을 (What)
Direct 탭 2컬럼 → 3컬럼 레이아웃 통합 + feature flag.

## 왜 (Why)
씬 목록, 씬 카드, 속성 패널을 분리하여 작업 효율 향상. feature flag로 즉시 롤백 가능.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase C — SP-057 항목

## 완료 기준 (DoD)
- [ ] 3패널 레이아웃: 씬 목록(240px) | 씬 카드(flex-1) | 속성 패널(300px)
- [ ] feature flag `use3PanelLayout`로 2패널/3패널 전환 가능
- [ ] SceneCard에서 설정 영역 제거 → PropertyPanel로 이동
- [ ] 모바일(< 1024px): "데스크톱에서 이용하세요" 안내
- [ ] AppThreeColumnLayout.tsx 처리 결정 (재활용 또는 삭제)
- [ ] Direct 탭 E2E 전체 통과 (SP-094 시나리오)
- [ ] VRT 베이스라인 갱신

## 힌트
- `ScenesTab.tsx` — 2컬럼 → 3컬럼 레이아웃
- `variants.ts` — STUDIO_3COL_LAYOUT 상수
- feature flag: `use3PanelLayout`
- AS-IS: [SceneList 280px] [SceneCard flex-1]
- TO-BE: [SceneList 240px] [SceneCard flex-1] [PropertyPanel 300px]

## 상세 설계 (How)

설계 문서: `design.md` 참조.

### 변경 파일 (5개)

| 파일 | 변경 내용 |
|------|----------|
| `variants.ts` | `STUDIO_3COL_LAYOUT`, `RIGHT_PANEL_CLASSES` 상수 추가 |
| `useUIStore.ts` | `use3PanelLayout` feature flag + toggle 액션 |
| `ScenesTab.tsx` | flag 기반 2/3컬럼 전환, 모바일 안내, PropertyPanel 배치 |
| `SceneCard.tsx` | 3패널 모드 시 Tier 2~4 조건부 숨김 |
| `AppThreeColumnLayout.tsx` | 삭제 (import 0건, 미사용) |

### 핵심 결정

1. **AppThreeColumnLayout 삭제**: import 0건 확인. variants.ts 상수 + ScenesTab 직접 grid로 대체.
2. **feature flag 위치**: `useUIStore`에 `use3PanelLayout` (기본 false). localStorage 영속성 불필요.
3. **모바일 게이트**: Tailwind `lg:` (1024px) 브레이크포인트 활용, `lg:hidden` / `hidden lg:contents` 패턴.
4. **SceneCard 설정 숨김**: 3패널 모드에서 Tier 2~4 (Customize/Scene Tags/Advanced)를 숨기고 PropertyPanel이 대신 렌더링.
