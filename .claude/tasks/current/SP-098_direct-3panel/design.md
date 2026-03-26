# SP-098 설계

## 구현 방법

### 1. `frontend/app/components/ui/variants.ts` — 레이아웃 상수 추가

```ts
/** 3-column grid: left scene list + center editor + right property panel (Direct tab). */
export const STUDIO_3COL_LAYOUT =
  "grid grid-cols-[240px_1fr_300px] gap-0 h-full min-h-[600px] overflow-hidden";

/** Right property panel container. */
export const RIGHT_PANEL_CLASSES =
  "flex flex-col border-l border-zinc-200 bg-zinc-50/50 overflow-y-auto scrollbar-hide";
```

- `STUDIO_2COL_LAYOUT`은 유지 (feature flag OFF 시 기존 2컬럼 사용)
- `LEFT_PANEL_CLASSES`의 width를 grid 외부에서 제어하므로 변경 불필요

### 2. `frontend/app/store/useUIStore.ts` — feature flag 추가

`UIState`에 `use3PanelLayout: boolean` 추가 (기본값 `false`).

```ts
// UIState interface에 추가
use3PanelLayout: boolean;
toggle3PanelLayout: () => void;

// initialState에 추가
use3PanelLayout: false,

// actions에 추가
toggle3PanelLayout: () => set((s) => ({ use3PanelLayout: !s.use3PanelLayout })),
```

- localStorage 영속성 불필요 (개발/롤백 목적의 세션 플래그)
- 향후 안정화 후 `true` 기본값 전환 → 최종 2컬럼 코드 제거

### 3. `frontend/app/components/studio/ScenesTab.tsx` — 3컬럼 레이아웃 통합

**변경 핵심**: feature flag에 따라 2컬럼/3컬럼 전환.

```
AS-IS: [SceneList 280px] [SceneCard flex-1]
TO-BE: [SceneList 240px] [SceneCard flex-1] [PropertyPanel 300px]
```

**(a) import 추가**
- `STUDIO_3COL_LAYOUT`, `RIGHT_PANEL_CLASSES` (variants.ts)
- `ScenePropertyPanel` (SP-097에서 생성된 컴포넌트)

**(b) feature flag 읽기**
```ts
const use3Panel = useUIStore((s) => s.use3PanelLayout);
```

**(c) 레이아웃 grid 전환**
```tsx
<div className={use3Panel ? STUDIO_3COL_LAYOUT : STUDIO_2COL_LAYOUT}>
  {/* Left Panel — 기존과 동일 */}
  <aside className={LEFT_PANEL_CLASSES}>...</aside>

  {/* Center Panel — 기존과 동일 */}
  <main className={CENTER_PANEL_CLASSES}>...</main>

  {/* Right Panel — 3패널 모드에서만 표시 */}
  {use3Panel && (
    <aside className={RIGHT_PANEL_CLASSES}>
      {currentScene && <ScenePropertyPanel />}
    </aside>
  )}
</div>
```

**(d) 모바일 안내 (< 1024px)**
- 최상단에 반응형 게이트 추가:
```tsx
<div className="flex h-full items-center justify-center lg:hidden">
  <p className="text-sm text-zinc-500">데스크톱에서 이용하세요</p>
</div>
<div className="hidden lg:contents">
  {/* 기존 3컬럼/2컬럼 레이아웃 */}
</div>
```
- `lg:` = 1024px 브레이크포인트 (Tailwind 기본)

**(e) SceneCard 설정 영역 조건부 숨김**
- 3패널 모드에서 SceneCard의 Tier 2~4 (Customize, Scene Tags, Advanced)는 PropertyPanel로 이동됨
- SceneCard에 `compact` prop (또는 useUIStore의 `use3PanelLayout` 직접 참조)으로 Tier 2~4 섹션 숨김
- SP-097에서 ScenePropertyPanel이 이 섹션들을 독립 렌더링하므로 중복 표시 방지

### 4. `AppThreeColumnLayout.tsx` — 처리 결정: 미사용 삭제

- 현재 import 0건 (Grep 확인 완료)
- SP-098은 `variants.ts` 상수 + ScenesTab 직접 grid로 구현하므로 이 컴포넌트 불필요
- 이 파일 삭제 (Phase A ghost component 정리 대상이기도 함)

### 5. 변경 파일 요약

| 파일 | 변경 | 줄 수 |
|------|------|------|
| `variants.ts` | `STUDIO_3COL_LAYOUT`, `RIGHT_PANEL_CLASSES` 상수 추가 | +6 |
| `useUIStore.ts` | `use3PanelLayout`, `toggle3PanelLayout` 추가 | +6 |
| `ScenesTab.tsx` | 3컬럼 레이아웃 전환 로직, 모바일 안내, PropertyPanel 배치 | ~+20, ~-0 |
| `SceneCard.tsx` | 3패널 모드 시 Tier 2~4 숨김 조건 (1줄 조건문 추가) | +3 |
| `AppThreeColumnLayout.tsx` | 삭제 | -39 |

---

## 테스트 전략

### 1. 유닛 테스트 (Vitest)

**(a) `useUIStore` feature flag 테스트**
- `use3PanelLayout` 기본값 `false` 확인
- `toggle3PanelLayout()` 호출 시 `true` ↔ `false` 토글 확인
- `resetUI()` 호출 시 `false`로 복원 확인

**(b) variants.ts 상수 테스트**
- `STUDIO_3COL_LAYOUT`에 `grid-cols-[240px_1fr_300px]` 포함 확인
- 기존 `STUDIO_2COL_LAYOUT`에 `grid-cols-[280px_1fr]` 유지 확인

### 2. 컴포넌트 테스트 (Vitest + React Testing Library)

**(a) `ScenesTab` 레이아웃 전환**
- `use3PanelLayout=false`: 2컬럼 grid 클래스 적용, PropertyPanel 미렌더링
- `use3PanelLayout=true`: 3컬럼 grid 클래스 적용, PropertyPanel 렌더링
- 씬 0개 시: EmptyState 표시 (flag 무관)

**(b) 모바일 안내**
- viewport < 1024px 시 "데스크톱에서 이용하세요" 텍스트 표시
- viewport >= 1024px 시 레이아웃 정상 표시

### 3. E2E 테스트 (Playwright)

- 기존 `studio-e2e.spec.ts` 전체 통과 확인 (회귀 방지)
- Direct 탭 진입 시 2컬럼 레이아웃 정상 (기본 flag=false)
- flag 활성화 후 3컬럼 레이아웃 전환 확인
- 3컬럼 모드에서 씬 선택 → PropertyPanel 내용 변경 확인

### 4. VRT (Playwright)

- `studio.vrt.spec.ts` 기존 스냅샷: flag=false이므로 차이 0 기대
- 3패널 모드 VRT 케이스 추가: `studio-direct-3panel.png` 베이스라인 신규 생성
- 모바일 뷰포트 VRT: `studio-direct-mobile-notice.png` 베이스라인 신규 생성
