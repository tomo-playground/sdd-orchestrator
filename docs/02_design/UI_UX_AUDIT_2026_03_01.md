# Shorts Producer Frontend UI/UX 감사 보고서

**감사일**: 2026-03-01
**감사 범위**: `frontend/app/` 전체 (페이지, 컴포넌트, 스토어, 훅)
**감사자**: UI/UX Engineer Agent

---

## 요약

전체 42개 이슈를 발견했으며, 우선순위별 분포는 다음과 같다:

| 우선순위 | 건수 | 설명 |
|----------|------|------|
| **P0 (Critical)** | 4 | 즉시 수정 필요 - 사용성/접근성 심각 이슈 |
| **P1 (High)** | 12 | 다음 스프린트 내 수정 - UX 품질 저하 |
| **P2 (Medium)** | 16 | 점진적 개선 - 일관성/코드 품질 |
| **P3 (Nice-to-have)** | 10 | 장기 개선 - 디자인 세련화 |

---

## 1. P0 (Critical) - 즉시 수정 필요

### P0-1. ShowcaseSection 커스텀 모달 - 접근성 위반

**파일**: `/frontend/app/components/home/ShowcaseSection.tsx:167-228`

ShowcaseSection의 비디오 프리뷰 모달이 공통 `Modal` 컴포넌트를 사용하지 않고 인라인 `<div>` 오버레이로 구현되어 있다. 이로 인해:

- **포커스 트랩 없음**: Tab 키로 모달 뒤 요소에 접근 가능
- **ARIA 속성 누락**: `role="dialog"`, `aria-modal="true"` 없음
- **ESC 키 미지원**: 키보드로 모달 닫기 불가
- **body scroll 잠금 없음**: 배경이 스크롤됨
- **z-index 불일치**: `z-50` 하드코딩 (디자인 시스템은 `--z-modal: 1000`)

```tsx
// 문제 코드 (ShowcaseSection.tsx:169)
<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
     onClick={() => setSelectedVideo(null)}>
```

**동일 이슈**: `/frontend/app/(service)/library/characters/[id]/GeminiEditModal.tsx:47`도 같은 패턴으로 `z-50` 하드코딩 + 접근성 속성 누락.

**해결**: 공통 `Modal` 컴포넌트로 교체. 이미 `useFocusTrap`, ESC 핸들링, body scroll 잠금이 구현되어 있다.

---

### P0-2. Studio 페이지 - 과도한 useEffect 체인 (5개)

**파일**: `/frontend/app/(service)/studio/page.tsx:53-143`

`StudioContent` 컴포넌트에 5개의 `useEffect`가 연쇄적으로 동작하며, 그 중 2개는 eslint-disable로 종속성 경고를 억제하고 있다.

```tsx
// page.tsx:107-112
useEffect(() => {
  if (!isAutoRunningRef.current) {
    autopilot.reset();
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [storyboardId]);
```

- `storyboardId` 변경 시 autopilot 리셋, pendingAutoRun 처리, activeTab 변경이 동시에 발생
- 의존성 누락으로 **stale closure** 위험
- React 19 Strict Mode에서 이중 실행 시 경합 조건 가능

**해결**: `useStudioLifecycle` 커스텀 훅으로 추출하고, 상태 전환 로직을 명시적으로 관리.

---

### P0-3. 네트워크 에러 시 사용자 피드백 부재 (fetch 직접 사용)

**파일**: `/frontend/app/components/home/ShowcaseSection.tsx:31-41`

`fetch` API를 직접 사용하면서 에러 시 빈 배열로 조용히 실패한다. 사용자에게 어떤 피드백도 없다.

```tsx
} catch {
  setItems([]);   // 에러를 완전히 삼킴
  setTotal(0);
}
```

**영향 범위 확인**: 컴포넌트 내 직접 axios/fetch 호출 16곳 중 에러 토스트 없이 `catch` 블록에서 조용히 실패하는 곳이 다수 존재.

**해결**: 공통 API 래퍼 도입 또는 최소한 `showToast` 에러 피드백 추가.

---

### P0-4. SceneCard props 과다 전달 (27개 props)

**파일**: `/frontend/app/components/storyboard/SceneCard.tsx:22-68`

SceneCard가 27개의 props를 받고 있어 유지보수성과 재사용성이 극도로 낮다.

```tsx
type SceneCardProps = {
  scene, sceneIndex, imageValidationResult, qualityScore,
  sceneMenuOpen, onSceneMenuToggle, onSceneMenuClose,
  validatingSceneId, loraTriggerWords, characterLoras,
  tagsByGroup, sceneTagGroups, isExclusiveGroup,
  onUpdateScene, onRemoveScene, onSpeakerChange,
  onImageUpload, onGenerateImage, onEditWithGemini,
  onSuggestEditWithGemini, onValidateImage, onApplyMissingTags,
  onImagePreview, onPinToggle, pinnedSceneOrder,
  onSavePrompt, onMarkSuccess, onMarkFail, // ... 더 있음
};
```

**해결**: Context 또는 Compound Component 패턴으로 props 그룹화. `SceneContext` Provider를 만들어 scene 데이터와 액션을 트리로 전달.

---

## 2. P1 (High) - 다음 스프린트 내 수정

### P1-1. SettingsShell / LibraryShell 코드 중복

**파일**:
- `/frontend/app/components/shell/LibraryShell.tsx`
- `/frontend/app/components/shell/SettingsShell.tsx`

두 컴포넌트가 구조적으로 동일하다 (탭 바 + 콘텐츠 영역). 탭 아이템 배열만 다르고 렌더링 로직이 100% 동일하다.

```tsx
// LibraryShell.tsx:31-58 vs SettingsShell.tsx:26-58 - 완전 동일 구조
<div className="flex flex-col gap-0">
  <div className="border-b border-zinc-100 bg-white/90 px-8 py-3 backdrop-blur-md">
    <nav className="flex items-center gap-1">
      {TABS.map(tab => { /* 동일 */ })}
    </nav>
  </div>
  <div className="flex-1 overflow-y-auto">{children}</div>
</div>
```

**해결**: `SubNavShell` 공통 컴포넌트를 만들어 `tabs` prop만 받도록 리팩터링.

---

### P1-2. 인라인 버튼 스타일 - Button 컴포넌트 미사용

**파일 (예시)**:
- `/frontend/app/components/home/HomeVideoFeed.tsx:31-33` - 인라인 `<button>` 스타일
- `/frontend/app/components/home/ShowcaseSection.tsx:81-89` - 인라인 `<button>` 스타일
- `/frontend/app/components/studio/StageTab.tsx:196-213` - 토글 체크박스 인라인 스타일

`Button` 컴포넌트가 8가지 variant를 지원하지만, 25개 이상의 파일에서 인라인 `className`으로 버튼을 스타일링하고 있다. (Grep 결과: 48곳에서 `rounded.*bg.*px.*py.*text.*font.*hover` 패턴 발견)

**문제점**:
- hover/active/focus 상태가 일관되지 않음
- `FOCUS_RING`과 `DISABLED_CLASSES` 토큰이 누락됨
- 디자인 시스템의 SSOT가 훼손됨

**해결**: 인라인 버튼 스타일을 `Button` 컴포넌트 사용으로 교체. 필요시 `ButtonVariant`를 추가.

---

### P1-3. truncate 유틸리티 함수 중복 정의

**파일**:
- `/frontend/app/components/video/RenderSettingsPanel.tsx:41`
- `/frontend/app/components/video/BgmSection.tsx:11`

동일한 `truncate` 헬퍼 함수가 두 파일에 복사되어 있다.

```tsx
const truncate = (str: string | undefined, maxLen: number) =>
  str && str.length > maxLen ? str.slice(0, maxLen - 1) + "\u2026" : str || "";
```

**해결**: `utils/format.ts`로 추출.

---

### P1-4. Studio 페이지 과부하 - 단일 파일 340줄

**파일**: `/frontend/app/(service)/studio/page.tsx` (340줄)

단일 `StudioContent` 함수가 모든 Studio 로직을 담고 있다:
- 초기화 (5개 훅 사용)
- Autopilot 제어
- Keyboard shortcuts
- Preflight 체크
- Dirty state guard
- 5개 모달 렌더링

CLAUDE.md 권장 기준 (컴포넌트 150줄, 최대 200줄) 초과.

**해결**: 모달 그룹을 `StudioModals` 컴포넌트로, Autopilot 로직을 `useStudioAutopilot` 훅으로 분리.

---

### P1-5. 영문/한국어 혼용 - 일관성 없는 라벨링

**파일** (다수):

| 위치 | 영문 | 한국어 |
|------|------|--------|
| StageTab.tsx:156-159 | "Stage -- Pre-production" | 없음 |
| SceneListPanel.tsx:43 | 없음 | "개 씬 / 총 X초" |
| StudioKanbanView.tsx:71 | 없음 | "영상 목록" |
| EmptyState 사용처 | "No Scenes Yet" | 없음 |
| PersistentContextBar.tsx:93-98 | "Autopilot running" | 없음 |
| SceneListPanel.tsx:77 | 없음 | "씬 추가" |
| error.tsx:23 | 없음 | "문제가 발생했습니다" |
| global-error.tsx:14 | "Critical Error" | 없음 |

UI 텍스트가 영문과 한국어가 혼재되어 있어 사용자 경험이 단절된다.

**해결**: i18n 시스템 도입 또는 단기적으로 모든 사용자 대면 텍스트를 한국어로 통일.

---

### P1-6. ScenesTab - 과도한 useShallow 중첩

**파일**: `/frontend/app/components/studio/ScenesTab.tsx:41-79`

3개의 `useShallow` 셀렉터가 연속으로 사용되어 있으며, 총 16개의 스토어 필드를 개별적으로 추출한다.

```tsx
const { scenes, currentSceneIndex } = useStoryboardStore(useShallow(...));
const { sceneMenuOpen, validatingSceneId, ... } = useStoryboardStore(useShallow(...));
const { loraTriggerWords, characterLoras, ... } = useStoryboardStore(useShallow(...));
```

**문제점**:
- 매 렌더마다 3번의 shallow comparison 수행
- 관련 없는 스토어 변경에도 리렌더 가능성

**해결**: `selectors/` 디렉토리에 `selectScenesTabData` 단일 셀렉터를 만들어 한 번에 추출.

---

### P1-7. global-error.tsx 언어 불일치

**파일**: `/frontend/app/global-error.tsx:13-17`

`<html lang="en">`으로 되어 있으나 프로젝트는 한국어 기반이다. `layout.tsx`는 `<html lang="ko">`를 사용한다.

**해결**: `<html lang="ko">`로 수정하고 텍스트를 한국어로 변경.

---

### P1-8. error.tsx와 global-error.tsx 디자인 불일치

**파일**:
- `/frontend/app/error.tsx` - 밝은 배경 가정 (text-red-400, text-zinc-400)
- `/frontend/app/global-error.tsx` - 어두운 배경 (bg-zinc-900, text-white)

에러 페이지 간 완전히 다른 디자인 언어를 사용한다.

**해결**: 동일한 디자인 토큰 적용.

---

### P1-9. RenderMediaPanelProps - 18개 setter props

**파일**: `/frontend/app/components/video/RenderSettingsPanel.tsx:46-79`

`RenderMediaPanelProps` 타입이 18개의 개별 값/setter 쌍을 props로 받는다.

**해결**: `RenderMediaConfig` 객체 + 단일 `onChange` 콜백 패턴으로 전환.

---

### P1-10. ConnectionGuard - localStorage 의존 캐릭터 프리뷰

**파일**: `/frontend/app/components/shell/ConnectionGuard.tsx:15-25`

`character_previews` 키로 localStorage에서 직접 JSON 파싱하여 이미지를 표시한다. 이 localStorage 키의 생산자가 명확하지 않고, 스키마 검증이 없다.

```tsx
function getRandomPreview(): CachedPreview | null {
  try {
    const raw = localStorage.getItem("character_previews");
    if (!raw) return null;
    const previews: CachedPreview[] = JSON.parse(raw); // 스키마 검증 없음
```

**해결**: localStorage 캐시에 버전 관리 추가하거나, Zustand persist로 통합.

---

### P1-11. SceneGeminiModals 파일 크기 초과

**파일**: `/frontend/app/components/storyboard/SceneGeminiModals.tsx` (373줄)

CLAUDE.md 권장 기준 (300줄 권장, 400줄 최대) 경계 수준.

**해결**: 개별 모달(EditModal, SuggestionsModal)을 별도 파일로 분리.

---

### P1-12. StudioWorkspace - ScriptTab 항상 마운트

**파일**: `/frontend/app/components/studio/StudioWorkspace.tsx:15-17`

```tsx
<div className={`h-full w-full ${activeTab !== "script" ? "hidden" : ""}`}>
  <ScriptTab />
</div>
```

ScriptTab은 `hidden`으로 숨겨질 뿐 항상 마운트된다. ScriptTab 내부의 `useChatScriptEditor` 훅과 WebSocket 연결 등이 불필요하게 활성 상태를 유지할 수 있다.

다른 3개 탭(Stage, Direct, Publish)은 조건부 렌더링을 사용한다:
```tsx
{activeTab === "stage" && <StageTab />}
```

**해결**: ScriptTab도 조건부 렌더링으로 전환하거나, 항상 마운트가 필요한 이유(채팅 히스토리 보존)를 주석으로 명시.

---

## 3. P2 (Medium) - 점진적 개선

### P2-1. z-index 관리 불일치

**파일**:
- `globals.css:16-30` - CSS 변수로 z-index 체계 정의 (`--z-modal: 1000` 등)
- `ShowcaseSection.tsx:169` - `z-50` 하드코딩
- `GeminiEditModal.tsx:47` - `z-50` 하드코딩
- `ConnectionGuard.tsx:45` - `z-[3000]` 하드코딩

**해결**: 모든 z-index를 CSS 변수(`--z-*`)로 통일.

---

### P2-2. 컴포넌트 내 직접 API 호출 (16곳)

**파일**: 컴포넌트 디렉토리 내 16개 파일에서 `axios` 직접 import.

`StageTab.tsx`, `PublishMetaPanel.tsx`, `StageLocationsSection.tsx` 등에서 컴포넌트 내부에 직접 `axios.post/get` 호출이 있다.

**문제점**:
- API 엔드포인트가 컴포넌트에 하드코딩
- 에러 처리 패턴이 파일마다 다름
- 테스트 시 모킹이 어려움

**해결**: `services/` 또는 `api/` 레이어를 만들어 API 호출을 중앙화.

---

### P2-3. console.log/warn/error 잔존 (9곳)

**파일**: 컴포넌트 내 8개 파일에서 `console.log/warn/error` 호출 발견.

- `SceneCard.tsx:132` - `console.error("Auto-suggest failed:", error)`
- `StyleProfileModal.tsx` - 2곳
- `QualityDashboard.tsx` - 1곳

**해결**: 프로덕션 빌드에서 제거하거나 에러 리포팅 서비스로 대체.

---

### P2-4. EmptyState 컴포넌트 - 일관되지 않은 사용

**파일**: EmptyState 사용처 vs 인라인 빈 상태 UI

EmptyState 컴포넌트가 존재하지만 다수의 위치에서 인라인으로 빈 상태를 구현:

- `HomeVideoFeed.tsx:20-40` - 인라인 빈 상태
- `StudioKanbanView.tsx:33-60` - 인라인 빈 상태 (2곳)
- `ShowcaseSection.tsx:73-91` - 인라인 빈 상태
- `SceneListPanel.tsx:49-54` - 인라인 빈 상태

**해결**: 모든 빈 상태 UI를 `EmptyState` 컴포넌트로 통일.

---

### P2-5. Skeleton 로딩 패턴 불일치

**파일**:
- `studio/page.tsx:169-197` - 인라인 Skeleton 조합
- `library/characters/page.tsx:84-89` - `SkeletonGrid` 사용
- `StudioKanbanView.tsx:82-85` - `LoadingSpinner` 사용
- `ShowcaseSection.tsx:66-70` - `Loader2` 아이콘 사용

페이지마다 로딩 UI가 다르다. 일부는 Skeleton, 일부는 Spinner, 일부는 Lucide 아이콘.

**해결**: 페이지 수준 로딩 패턴 통일 - 첫 로딩은 Skeleton, 부분 갱신은 Spinner.

---

### P2-6. SceneCard 내 이모지 사용

**파일**: `/frontend/app/components/storyboard/SceneCard.tsx:263-275`

```tsx
<Button variant="success" size="sm">👍 Success</Button>
<Button variant="danger" size="sm">👎 Fail</Button>
```

CLAUDE.md 규칙: "Only use emojis if the user explicitly requests it". 버튼 레이블에 이모지 사용은 접근성과 일관성 면에서 문제.

**해결**: Lucide 아이콘(ThumbsUp/ThumbsDown)으로 교체.

---

### P2-7. text-[11px] / text-[12px] 과도한 사용

Grep 결과: **141개 파일에서 675곳**에 `text-[11px]` 또는 `text-[12px]` 사용.

CLAUDE.md 규칙에서 허용하지만 과도하게 사용되고 있다. 특히:
- `text-[11px]`은 배지/타임스탬프에 적합하나, 본문 라벨에도 사용됨
- `text-[12px]`은 라벨용이지만 설명문에도 사용됨

**해결**: `text-xs` (13px)를 기본으로 하고, `text-[11px]`/`text-[12px]`는 보조 정보에만 한정.

---

### P2-8. SceneImagePanel 파일 크기 초과

**파일**: `/frontend/app/components/storyboard/SceneImagePanel.tsx` (324줄)

CLAUDE.md 권장 기준(300줄) 약간 초과. `ValidationOverlay`와 `GenProgressOverlay` 서브 컴포넌트가 같은 파일에 포함되어 있다.

**해결**: 오버레이 컴포넌트를 별도 파일로 분리.

---

### P2-9. PersistentContextBar - 과도한 책임

**파일**: `/frontend/app/components/context/PersistentContextBar.tsx` (208줄)

단일 컴포넌트가 다음을 모두 관리:
- 프로젝트/그룹/스토리보드 breadcrumb
- 프로젝트 삭제/편집
- 그룹 삭제/편집
- SetupWizard 트리거
- GroupConfigEditor 모달

**해결**: 모달 렌더링을 부모로 올리거나, `ContextBarModals` 서브 컴포넌트로 분리.

---

### P2-10. ServiceShell - Skip to content 링크 영문

**파일**: `/frontend/app/components/shell/ServiceShell.tsx:92-97`

```tsx
<a href="#main-content" className="sr-only focus:not-sr-only ...">
  Skip to main content
</a>
```

접근성 링크가 영문으로 되어 있다. 한국어 사용자에게는 "본문으로 건너뛰기"가 적절하다.

**해결**: 한국어로 변경.

---

### P2-11. 반응형 브레이크포인트 불일치

**파일**:
- `STUDIO_2COL_LAYOUT`: 항상 2열 (브레이크포인트 없음)
- `PUBLISH_2COL_LAYOUT`: `md` 브레이크포인트에서 2열
- `PAGE_2COL_LAYOUT`: `xl` 브레이크포인트에서 2열

Studio의 2열 레이아웃(`grid-cols-[280px_1fr]`)이 모바일에서도 고정된다. 작은 화면에서 SceneListPanel이 너무 좁아져 사용 불가.

**해결**: `STUDIO_2COL_LAYOUT`에 `md:` 브레이크포인트 추가.

---

### P2-12. StoryboardStore persist - Set 타입 필터 누락

**파일**: `/frontend/app/store/useRenderStore.ts:168`

```tsx
if (value instanceof Set) continue;
```

`Set` 타입은 JSON 직렬화가 안 되어 특별 처리하고 있지만, `Map` 등 다른 비직렬화 타입에 대한 방어가 없다.

**해결**: `superjson` 도입 또는 직렬화 가능 여부를 일괄 검사.

---

### P2-13. Toast 중복 타이머 관리

**파일**: `/frontend/app/store/useUIStore.ts:124-148` + `/frontend/app/components/ui/Toast.tsx:19-26`

Toast auto-dismiss가 두 곳에서 이중으로 관리된다:
1. `useUIStore.showToast()`: 3000ms 후 자동 삭제
2. `SingleToast` 컴포넌트: 3000ms 후 애니메이션 + `onClose` 호출

두 타이머가 동시에 작동하여 toast가 예상보다 빨리 사라지거나 double-removal이 발생할 수 있다.

**해결**: 타이머를 한 곳(스토어 또는 컴포넌트)으로 통일.

---

### P2-14. useStoryboardStore - pre-hydration cleanup SSR 안전성

**파일**: `/frontend/app/store/useStoryboardStore.ts:169-174`

```tsx
if (typeof window !== "undefined") {
  const params = new URLSearchParams(window.location.search);
  if (params.get("new") === "true") {
    localStorage.removeItem(STORYBOARD_STORE_KEY);
  }
}
```

모듈 최상위에서 실행되어 import 시점에 side effect가 발생한다. 동일 패턴이 `useRenderStore.ts:124-129`에도 있다.

**해결**: `useEffect` 또는 Zustand `onRehydrateStorage` 콜백 내부로 이동.

---

### P2-15. 키보드 단축키 충돌 가능성

**파일**: `/frontend/app/(service)/studio/page.tsx:146-166`

```tsx
useKeyboardShortcuts([
  { key: "s", metaKey: true, ctrlKey: true, action: handleSave },
  { key: "Enter", metaKey: true, action: preflight },
]);
```

`Cmd+S`가 저장, `Cmd+Enter`가 AutoRun이지만, 이 단축키가 활성화되는 조건(scenes.length > 0)이 명확히 UI에 표시되지 않는다. 또한 `CommandPalette`의 `Cmd+K`와 충돌 검사가 없다.

**해결**: 단축키 레지스트리를 중앙화하고, 충돌 감지 로직 추가. 또한 `?` 키로 단축키 목록을 표시하는 도움말 추가.

---

### P2-16. ConfirmDialog - inputField 모드에서 Enter 키 미지원

**파일**: `/frontend/app/components/ui/ConfirmDialog.tsx:63-76`

```tsx
<input
  type="text"
  className="..."
  placeholder={inputField.placeholder}
  value={inputValue ?? ""}
  onChange={(e) => onInputChange?.(e.target.value)}
  autoFocus
/>
```

inputField 모드에서 Enter 키로 확인하는 `onKeyDown` 핸들러가 없다.

**해결**: `onKeyDown` 핸들러에 Enter 키 처리 추가.

---

## 4. P3 (Nice-to-have) - 장기 개선

### P3-1. 디자인 토큰 - 색상 체계 비공식화

`variants.ts`에 시맨틱 색상 토큰이 정의되어 있지만 CSS 변수가 아닌 Tailwind 클래스 문자열로 관리된다. 다크 모드 지원이 어려운 구조.

**해결**: CSS 변수 기반 색상 체계로 전환.

---

### P3-2. Footer 컴포넌트 부재 (일부 페이지만)

`HomeVideoFeed`에만 `Footer` 컴포넌트가 있고, Library/Settings/Studio에는 없다.

---

### P3-3. 반응형 NavBar - 모바일 대응 없음

**파일**: `/frontend/app/components/shell/ServiceShell.tsx:48-83`

NavBar가 수평 탭으로만 구현되어 있고 모바일 뷰에서 축소/햄버거 메뉴 등이 없다. `max-w-[1440px]`로 제한되어 있어 대형 모니터에서 양쪽 여백이 크다.

---

### P3-4. 다크 모드 미지원

`globals.css`에 다크 모드 관련 설정이 없으며, 모든 색상이 라이트 모드 전용이다.

---

### P3-5. SceneListPanel - 드래그앤드롭 접근성

**파일**: `/frontend/app/components/storyboard/SceneListPanel.tsx:111-123`

HTML5 DnD API를 사용하지만 키보드 전용 사용자를 위한 대안(위/아래 화살표로 순서 변경)이 없다.

---

### P3-6. 애니메이션 일관성

일부 컴포넌트는 `transition` 클래스를 사용하고, Toast는 `transition-all duration-300`을 사용한다. `framer-motion` 등 애니메이션 라이브러리 없이 CSS 전환만 사용 중이어서 복잡한 전환 효과가 어렵다.

---

### P3-7. Storyboard/Render Store 크기

- `useStoryboardStore.ts`: 305줄 (권장 300줄 경계)
- `useRenderStore.ts`: 186줄 (양호)

StoryboardStore는 이미 actions/ 디렉토리로 액션을 분리했지만, 타입 정의가 스토어 파일에 남아 있다.

**해결**: `types/storyboard.ts`로 타입 분리.

---

### P3-8. CommandPalette - 검색 결과 부족 시 안내 없음

**파일**: `/frontend/app/components/ui/CommandPalette.tsx`

검색 결과가 0건일 때 "결과 없음" 메시지가 있는지 확인 필요. 빈 목록이 그대로 표시되면 사용자 혼란.

---

### P3-9. ServiceShell - 키보드 단축키 힌트 표시 조건

**파일**: `/frontend/app/components/shell/ServiceShell.tsx:103-105`

```tsx
<kbd className="hidden rounded border ... sm:inline-block">
  <span className="text-zinc-300">&#x2318;</span>K
</kbd>
```

`hidden sm:inline-block`으로 모바일에서 숨기지만, 터치 디바이스에서는 단축키 자체가 의미 없으므로 `@media (hover: hover)` 조건이 더 적절하다.

---

### P3-10. LoadingSpinner border 스타일 불일치

**파일**: `/frontend/app/components/ui/LoadingSpinner.tsx:15-17`

```tsx
sm: "h-4 w-4 border-2",
md: "h-6 w-6 border-2",
lg: "h-10 w-10 border-3",
```

`border-3`은 Tailwind 기본값에 없어 커스텀 정의 필요. `border-[3px]`로 명시하거나 `border-4`를 사용하는 것이 안전.

---

## 5. 아키텍처 관찰 사항 (이슈 아님, 참고용)

### 잘 된 점

1. **디자인 토큰 중앙화**: `variants.ts`에 레이아웃, 색상, 인터랙션 토큰이 잘 정리되어 있다.
2. **z-index 체계**: CSS 변수(`--z-*`)로 계층 구조가 정의되어 있다 (일부 하드코딩 제외).
3. **Modal 컴포넌트 완성도**: Focus trap, ESC 핸들링, body scroll 잠금, portal 렌더링이 모두 구현.
4. **Button 컴포넌트**: 8가지 variant, 3가지 size, loading 상태 지원.
5. **ConfirmDialog + useConfirm**: Promise 기반 확인 다이얼로그 - 유연하고 재사용 가능.
6. **Zustand 4-Store 분리**: 관심사 분리가 잘 되어 있다 (Context, Storyboard, Render, UI).
7. **autoSave 효과**: Debounced 저장 + AutoRun/Generation 중 스킵 로직이 잘 구현.
8. **ConnectionGuard**: 백엔드 연결 끊김 시 전체 화면 오버레이로 명확한 피드백.
9. **접근성 기본**: `role="dialog"`, `aria-modal`, `aria-live`, skip link, focus-visible 구현.
10. **Skeleton 컴포넌트**: 로딩 상태용 skeleton UI가 잘 구현.

### 전반적 구조 평가

- **디자인 시스템 성숙도**: 60% - 토큰은 정의되었으나 일관된 적용이 부족
- **접근성 커버리지**: 50% - 기본 구현은 있으나 커스텀 모달/위젯에 누락
- **반응형 대응**: 40% - 일부 페이지만 반응형, Studio는 데스크톱 전용
- **코드 재사용성**: 55% - 공통 컴포넌트는 있으나 인라인 스타일이 여전히 많음

---

## 6. 우선 실행 로드맵 제안

### Phase 1 (이번 스프린트)
- P0-1: ShowcaseSection/GeminiEditModal 모달 접근성 수정
- P0-3: 에러 피드백 부재 수정
- P1-7: global-error.tsx 언어 수정
- P1-5: 에러 페이지 텍스트 한국어 통일

### Phase 2 (다음 스프린트)
- P0-4: SceneCard props 리팩터링 (SceneContext 도입)
- P1-1: SubNavShell 공통화
- P1-2: 인라인 버튼 -> Button 컴포넌트 전환 (상위 10곳)
- P1-4: Studio 페이지 분리

### Phase 3 (분기 내)
- P0-2: Studio useEffect 정리
- P1-6: ScenesTab 셀렉터 최적화
- P2-2: API 레이어 중앙화
- P2-11: Studio 반응형 대응

---

*이 보고서는 코드 정적 분석 기반이며, 실제 브라우저 테스트(Playwright)를 통한 시각적 검증은 포함되지 않았다. 추가 Playwright 기반 VRT 및 접근성 자동 테스트를 권장한다.*
