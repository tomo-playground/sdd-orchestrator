# SP-104 풀 설계: UI 라벨 한국어화

## 개요

영문 잔존 라벨을 한국어로 교체하고, Dev NavBar 항목을 제거한다.
로직 변경 없이 문자열 교체만 수행. key/URI 값은 유지.

---

## DoD-1: NavBar 한국어화 + Dev 제거

### 구현 방법
**파일**: `frontend/app/components/shell/ServiceShell.tsx`

1. `NAV_ITEMS` 배열의 `label` 변경:
   - `"Home"` → `"홈"`
   - `"Studio"` → `"스튜디오"`
   - `"Library"` → `"라이브러리"`
   - `"Settings"` → `"설정"`
2. `DEV_ITEM` 상수 정의 삭제
3. `NavBar` 컴포넌트에서 Dev 렌더링 블록 제거:
   - Separator `<div className="mx-1 h-4 w-px bg-zinc-200" />` 제거
   - Dev `<Link>` 블록 전체 제거
4. `Wrench` import 제거 (Dev 아이콘)

### 동작 정의
- **Before**: NavBar에 Home / Studio / Library / Settings / | / Dev (6개 요소)
- **After**: NavBar에 홈 / 스튜디오 / 라이브러리 / 설정 (4개 요소, separator + Dev 없음)
- `/dev` URL 직접 접근은 라우트 파일 유지로 정상 작동

### 엣지 케이스
- `isNavActive`에 `/dev` 분기가 없으므로(DEV_ITEM은 NAV_ITEMS 외부) 삭제 시 영향 없음
- `pathname.startsWith("/dev")` 조건도 Dev Link 내부에만 있으므로 블록 삭제로 해결

### 영향 범위
- `ServiceShell.tsx` 단일 파일
- E2E/VRT 테스트에서 NavBar 영문 매칭 부분 (DoD-11에서 처리)

### 테스트 전략
- VRT: NavBar 영역 스냅샷 갱신
- E2E: 한국어 라벨 매칭으로 변경 (DoD-11)

### Out of Scope
- `/dev` 라우트 페이지 삭제 (URL 직접 접근 유지)
- `(app)/dev/` 디렉토리 구조 변경

---

## DoD-2: Studio 탭 한국어화

### 구현 방법
**파일**: `frontend/app/components/studio/StudioWorkspaceTabs.tsx`

`TABS` 배열의 `label` 변경 (key 유지):
- `{ key: "script", label: "Script" }` → `{ key: "script", label: "대본" }`
- `{ key: "stage", label: "Stage" }` → `{ key: "stage", label: "준비" }`
- `{ key: "direct", label: "Direct" }` → `{ key: "direct", label: "이미지" }`
- `{ key: "publish", label: "Publish" }` → `{ key: "publish", label: "게시" }`

### 동작 정의
- **Before**: Script / Stage / Direct / Publish
- **After**: 대본 / 준비 / 이미지 / 게시
- `StudioTab` 타입 (`"script" | "stage" | "direct" | "publish"`)과 `activeTab` 로직 불변

### 엣지 케이스
- `useTabBadges`는 key 기반이므로 label 변경 영향 없음
- 다른 컴포넌트에서 `setActiveTab("script")` 등 key로 호출하므로 영향 없음

### 영향 범위
- `StudioWorkspaceTabs.tsx` 단일 파일
- E2E: `getByRole("button", { name: "Script", exact: true })` 등 매칭 (DoD-11)

### 테스트 전략
- VRT: Studio 탭 바 스냅샷 갱신
- E2E: 버튼 name 매칭 한국어로 변경 (DoD-11)

### Out of Scope
- `StudioTab` 타입 값 변경 (key는 영문 유지)
- 탭 전환 로직 수정

---

## DoD-3: Library 탭 한국어화

### 구현 방법
**파일**: `frontend/app/components/shell/LibraryShell.tsx`

`TABS` 배열의 `label` 변경 (href 유지):
- `"Characters"` → `"캐릭터"`
- `"Styles"` → `"화풍"`
- `"Voices"` → `"음성"`
- `"Music"` → `"BGM"`
- `"LoRAs"` → `"LoRAs"` (유지 -- spec DoD에 Phase D 제거 예정으로 유지 명시)

### 동작 정의
- **Before**: Characters / Styles / Voices / Music / LoRAs
- **After**: 캐릭터 / 화풍 / 음성 / BGM / LoRAs

### 엣지 케이스
- `SubNavShell`은 `tab.label`을 표시용으로만 사용 (href 기반 라우팅)
- LoRAs는 기술 용어로 한국어 대응어가 없어 유지

### 영향 범위
- `LibraryShell.tsx` 단일 파일

### 테스트 전략
- VRT: Library 서브 내비 스냅샷 갱신
- E2E: Library 탭 매칭이 있는 경우 변경 (현재 테스트에서 직접 매칭 없음)

### Out of Scope
- `SubNavShell.tsx` 컴포넌트 수정
- Library 하위 페이지 내 콘텐츠 한국어화

---

## DoD-4: Settings 탭 한국어화

### 구현 방법
**파일**: `frontend/app/components/shell/SettingsShell.tsx`

`TABS` 배열의 `label` 변경 (href 유지):
- `"Render Presets"` → `"렌더 설정"`
- `"YouTube"` → `"연동"`
- `"Trash"` → `"휴지통"`

### 동작 정의
- **Before**: Render Presets / YouTube / Trash
- **After**: 렌더 설정 / 연동 / 휴지통

### 엣지 케이스
- `qa-patrol.spec.ts`에서 `getByRole("link", { name: /Render Presets/i })` 매칭 존재 (DoD-11)

### 영향 범위
- `SettingsShell.tsx` 단일 파일
- E2E: Settings 접속 테스트의 링크 매칭 (DoD-11)

### 테스트 전략
- VRT: Settings 서브 내비 스냅샷 갱신
- E2E: 링크 name 한국어로 변경

### Out of Scope
- Settings 하위 페이지 내 콘텐츠 한국어화
- YouTube 연동 페이지 자체 한국어화

---

## DoD-5: PipelineStatusDots 한국어화

### 구현 방법
**파일**: `frontend/app/components/studio/PipelineStatusDots.tsx`

1. `STEPS` 배열의 `label` 변경:
   - `"Script"` → `"대본"`
   - `"Stage"` → `"준비"`
   - `"Images"` → `"이미지"`
   - `"Render"` → `"렌더"`
   - `"Video"` → `"영상"`
2. `tooltipText` 객체의 문자열 한국어화:
   - `"Script: not started"` → `"대본: 미시작"`
   - `"Script: {n} scenes"` → `"대본: {n}개 씬"`
   - `"Stage: backgrounds ready"` → `"준비: 배경 완료"`
   - `"Stage: generating..."` → `"준비: 생성 중..."`
   - `"Stage: generation failed"` → `"준비: 생성 실패"`
   - `"Stage: not started"` → `"준비: 미시작"`
   - `"Images: all {n} done"` → `"이미지: 전체 {n}개 완료"`
   - `"Images: {m}/{n}"` → `"이미지: {m}/{n}"`
   - `"Images: not started"` → `"이미지: 미시작"`
   - `"Render: {percent}%"` → `"렌더: {percent}%"`
   - `"Render: in progress"` → `"렌더: 진행 중"`
   - `"Render: complete"` → `"렌더: 완료"`
   - `"Render: not started"` → `"렌더: 미시작"`
   - `"Video: {n} rendered"` → `"영상: {n}개 완료"`
   - `"Video: not started"` → `"영상: 미시작"`

### 동작 정의
- **Before**: 영문 tooltip (Script: 3 scenes, Render: in progress 등)
- **After**: 한국어 tooltip (대본: 3개 씬, 렌더: 진행 중 등)
- dot 색상/애니메이션 로직 불변

### 엣지 케이스
- `status` 객체의 key는 영문 ID (`script`, `stage`, `images`, `render`, `video`)로 유지
- tooltip은 hover 시에만 표시 — 자동 테스트에서 직접 매칭하지 않음

### 영향 범위
- `PipelineStatusDots.tsx` 단일 파일

### 테스트 전략
- VRT: hover tooltip은 VRT에서 캡처 어려움 — 수동 확인 또는 별도 interaction VRT
- 빌드 에러 없음 확인

### Out of Scope
- PipelineStatusDots 로직 변경
- dot 색상/상태 매핑 변경

---

## DoD-6: PreflightModal STEP_LABELS 한국어화

### 구현 방법
**파일**: `frontend/app/components/common/PreflightModal.tsx`

`STEP_LABELS` 변경:
- `stage: "Stage"` → `stage: "준비"`
- `images: "Images"` → `images: "이미지"`
- `tts: "TTS"` → `tts: "TTS"` (기술 약어 유지)
- `render: "Render"` → `render: "렌더"`

### 동작 정의
- **Before**: 실행 단계 체크박스 라벨이 Stage / Images / TTS / Render
- **After**: 준비 / 이미지 / TTS / 렌더
- 모달 헤더/버튼(이미 한국어)과 설정 검증 섹션 라벨 불변

### 엣지 케이스
- `STEP_LABELS`는 `StepRow`의 `label` prop으로만 사용 — UI 표시 전용
- `AutoRunStepId` 타입과 `preflight.steps` key는 영문 유지

### 영향 범위
- `PreflightModal.tsx` 단일 파일

### 테스트 전략
- VRT: PreflightModal은 조건부 렌더링(isOpen) — mock 또는 직접 열기 필요
- 빌드 에러 없음 확인

### Out of Scope
- SettingRow label(Character, Topic 등)은 이번 scope 외
- PreflightModal 로직 변경

---

## DoD-7: ContinueWorkingSection STEP_META 한국어화

### 구현 방법
**파일**: `frontend/app/components/home/ContinueWorkingSection.tsx`

1. `STEP_META` label 변경:
   - `draft: { label: "Script", ... }` → `draft: { label: "대본", ... }`
   - `in_prod: { label: "Edit", ... }` → `in_prod: { label: "제작", ... }`
   - `rendered: { label: "Publish", ... }` → `rendered: { label: "게시", ... }`
   - `published: { label: "Done", ... }` → `published: { label: "완료", ... }`
2. 섹션 제목 한국어화:
   - `"Continue Working"` → `"이어서 작업"`

### 동작 정의
- **Before**: 진행 dot 아래 Script / Edit / Publish / Done 라벨, "Continue Working" 제목
- **After**: 대본 / 제작 / 게시 / 완료 라벨, "이어서 작업" 제목
- color 속성 불변

### 엣지 케이스
- `STEP_META[step].label`은 `title` 속성과 텍스트 표시에 사용
- Home 페이지 VRT/E2E에서 "Continue Working" 텍스트 매칭 존재 (DoD-11)

### 영향 범위
- `ContinueWorkingSection.tsx` 단일 파일
- `tests/vrt/home.spec.ts` 매칭 변경 (DoD-11)

### 테스트 전략
- VRT: Home 페이지 스냅샷 갱신
- E2E: "Continue Working" → "이어서 작업" 매칭 변경

### Out of Scope
- 카드 내 "Untitled" 텍스트 (데이터 의존)
- 시간 포맷 (formatRelativeTime)

---

## DoD-8: QuickStatsBar 카테고리 한국어화

### 구현 방법
**파일**: `frontend/app/components/home/QuickStatsBar.tsx`

`statItems` 배열의 `label` 변경:
- `"Characters"` → `"캐릭터"`
- `"Styles"` → `"화풍"`
- `"Voices"` → `"음성"`
- `"Music"` → `"BGM"`

### 동작 정의
- **Before**: 숫자 뒤 Characters / Styles / Voices / Music 텍스트
- **After**: 숫자 뒤 캐릭터 / 화풍 / 음성 / BGM 텍스트

### 엣지 케이스
- `id` 필드는 영문 유지 (key 용도)
- `href`는 라우트 경로로 영문 유지

### 영향 범위
- `QuickStatsBar.tsx` 단일 파일

### 테스트 전략
- VRT: Home 페이지 스냅샷 갱신
- 빌드 에러 없음 확인

### Out of Scope
- Stats API 응답 구조 변경
- 0 표시 시 빈 상태 UI

---

## DoD-9: AUTO_RUN_STEPS 한국어화

### 구현 방법
**파일**: `frontend/app/constants/index.ts`

`AUTO_RUN_STEPS` 배열의 `label` 변경 (일부 이미 한국어):
- `{ id: "stage", label: "배경·BGM" }` → 유지 (이미 한국어)
- `{ id: "images", label: "Images" }` → `{ id: "images", label: "이미지" }`
- `{ id: "tts", label: "TTS" }` → 유지 (기술 약어)
- `{ id: "render", label: "Render" }` → `{ id: "render", label: "렌더" }`

### 동작 정의
- **Before**: 배경·BGM / Images / TTS / Render
- **After**: 배경·BGM / 이미지 / TTS / 렌더
- `AutoRunStepId` 타입 및 autopilot 로직 불변

### 엣지 케이스
- `AUTO_RUN_STEPS`를 소비하는 컴포넌트들이 label만 표시용으로 사용하는지 확인 필요
- `as const` 타입이므로 label 타입이 리터럴로 추론됨 — 타입 매칭하는 곳이 없으면 안전

### 영향 범위
- `constants/index.ts` 단일 파일
- `AUTO_RUN_STEPS`를 import하는 컴포넌트 (표시용이므로 영향 없음)

### 테스트 전략
- 빌드 에러 없음 확인
- `AUTO_RUN_STEPS`를 소비하는 autopilot 관련 컴포넌트 동작 확인

### Out of Scope
- `AutoRunStepId` 타입 정의 변경
- autopilot 실행 로직

---

## DoD-10: MaterialsPopover 한국어화

### 구현 방법
**파일**: `frontend/app/components/studio/MaterialsPopover.tsx`

1. `MATERIALS` 배열의 `label` 변경:
   - `"Script"` → `"대본"`
   - `"Style"` → `"화풍"`
   - `"Characters"` → `"캐릭터"`
   - `"Voice"` → `"음성"`
   - `"Music"` → `"BGM"`
   - `"BG"` → `"배경"`
2. 팝오버 헤더 변경:
   - `"Materials"` → `"준비 상태"`
3. 상태 표시 텍스트 변경:
   - `"Ready"` → `"완료"`
   - `"Missing"` → `"미설정"`

### 동작 정의
- **Before**: Materials 헤더, Script/Style/Characters/Voice/Music/BG 라벨, Ready/Missing 상태
- **After**: 준비 상태 헤더, 대본/화풍/캐릭터/음성/BGM/배경 라벨, 완료/미설정 상태

### 엣지 케이스
- `MaterialKey` 타입 (`"script" | "style" | "characters" | "voice" | "music" | "background"`) 유지
- `MaterialAction` 타입 유지
- `icon` 단일 문자는 영문 약어(S, C, V, M, B) — 의미 전달용이므로 유지

### 영향 범위
- `MaterialsPopover.tsx` 단일 파일

### 테스트 전략
- VRT: Studio 에디터 뷰에서 popover 열기 스냅샷 (조건부 렌더링)
- 빌드 에러 없음 확인

### Out of Scope
- `useMaterialsCheck` hook 변경
- 아이콘 문자(S, C, V, M, B) 한국어화

---

## DoD-11: E2E 테스트 한국어 매칭 수정

### 구현 방법

#### 파일 1: `frontend/e2e/smoke.spec.ts`

| 줄 | Before | After |
|----|--------|-------|
| 8 | `{ name: /home/i }` | `{ name: /홈/i }` |
| 9 | `{ name: /studio/i }` | `{ name: /스튜디오/i }` |
| 10 | `{ name: /library/i }` | `{ name: /라이브러리/i }` |
| 11 | `{ name: /settings/i }` | `{ name: /설정/i }` |
| 24 | `{ name: "Script", exact: true }` | `{ name: "대본", exact: true }` |
| 37 | `{ name: "Stage", exact: true }` | `{ name: "준비", exact: true }` |
| 38 | `{ name: "Direct", exact: true }` | `{ name: "이미지", exact: true }` |
| 39 | `{ name: "Publish", exact: true }` | `{ name: "게시", exact: true }` |
| 42 | `{ name: "Stage", exact: true }` (click) | `{ name: "준비", exact: true }` |

#### 파일 2: `frontend/e2e/qa-patrol.spec.ts`

| 줄 | Before | After |
|----|--------|-------|
| 100 | `{ name: /home/i }` | `{ name: /홈/i }` |
| 101 | `{ name: /studio/i }` | `{ name: /스튜디오/i }` |
| 126 | `{ name: "Script", exact: true }` | `{ name: "대본", exact: true }` |
| 137 | `{ name: /Render Presets/i }` | `{ name: /렌더 설정/i }` |
| 138 | `{ name: /YouTube/i }` | `{ name: /연동/i }` |
| 213 | `TABS = ["Script", "Stage", "Direct", "Publish"]` | `TABS = ["대본", "준비", "이미지", "게시"]` |
| 223 | `{ name: tab, exact: true }` | 동일 (tab 변수가 한국어로 변경됨) |

#### 파일 3: `frontend/tests/vrt/studio-e2e.spec.ts`

| 줄 | Before | After |
|----|--------|-------|
| 25 | `{ name: "Script", exact: true }` | `{ name: "대본", exact: true }` |
| 33 | `{ name: "Script", exact: true }` | `{ name: "대본", exact: true }` |
| 34 | `{ name: "Stage", exact: true }` | `{ name: "준비", exact: true }` |
| 35 | `{ name: "Direct", exact: true }` | `{ name: "이미지", exact: true }` |
| 36 | `{ name: "Publish", exact: true }` | `{ name: "게시", exact: true }` |
| 39 | `{ name: "Stage", exact: true }` (click) | `{ name: "준비", exact: true }` (click) |
| 41 | `{ name: "Direct", exact: true }` (click) | `{ name: "이미지", exact: true }` (click) |
| 43 | `{ name: "Publish", exact: true }` (click) | `{ name: "게시", exact: true }` (click) |
| 45 | `{ name: "Script", exact: true }` (click) | `{ name: "대본", exact: true }` (click) |
| 85 | `{ name: "Home" }` (click) | `{ name: "홈" }` (click) |
| 87 | `{ name: "Script", exact: true }` | `{ name: "대본", exact: true }` |
| 96 | `{ name: "Script", exact: true }` | `{ name: "대본", exact: true }` |

#### 파일 4: `frontend/tests/vrt/home.spec.ts`

| 줄 | Before | After |
|----|--------|-------|
| 39 | `"Continue Working"` | `"이어서 작업"` |
| 46 | `"Continue Working"` | `"이어서 작업"` |
| 51 | `{ name: "Home" }` | `{ name: "홈" }` |
| 52 | `{ name: "Studio" }` | `{ name: "스튜디오" }` |
| 53 | `{ name: "Library" }` | `{ name: "라이브러리" }` |
| 54 | `{ name: "Settings" }` | `{ name: "설정" }` |

#### 파일 5: `frontend/tests/vrt/warning-toast-e2e.spec.ts`

| 줄 | Before | After |
|----|--------|-------|
| 87 | `{ name: "Script", exact: true }` | `{ name: "대본", exact: true }` |

### 동작 정의
- **Before**: 영문 라벨 기반 element 매칭
- **After**: 한국어 라벨 기반 element 매칭, 테스트 pass

### 엣지 케이스
- `{ exact: true }` 사용 시 정확한 한국어 문자열 필요
- regex 패턴(`/home/i`)은 한국어로 변경 시 case-insensitive 불필요하지만 일관성을 위해 유지 가능

### 영향 범위
- E2E 5개 파일

### 테스트 전략
- 변경 후 전체 E2E 스위트 실행으로 검증
- `npx playwright test` 통과 확인

### Out of Scope
- 테스트 로직 변경
- 새 테스트 케이스 추가

---

## DoD-12: VRT 베이스라인 갱신

### 구현 방법
UI 라벨 변경 완료 후 VRT 베이스라인 전체 갱신:
```bash
cd frontend && npx playwright test tests/vrt/ --update-snapshots
```

### 동작 정의
- **Before**: 영문 라벨 기준 스냅샷
- **After**: 한국어 라벨 기준 스냅샷
- 모든 VRT 테스트 pass

### 엣지 케이스
- 갱신 시 라벨 외 레이아웃 변경이 없는지 diff 확인
- Dev 항목 제거로 NavBar 너비가 줄어 레이아웃 미세 변경 가능 — 정상 변경으로 승인

### 영향 범위
- `tests/vrt/**/*.spec.ts-snapshots/` 디렉토리

### 테스트 전략
- 갱신 후 재실행하여 0 diff 확인

### Out of Scope
- VRT 테스트 시나리오 추가

---

## DoD-13: 빌드 에러 0개

### 구현 방법
모든 라벨 변경 완료 후 빌드 확인:
```bash
cd frontend && npm run build
```

### 동작 정의
- TypeScript 컴파일 에러 0개
- Next.js 빌드 성공

### 엣지 케이스
- `as const` 배열의 리터럴 타입이 변경되므로, label 리터럴 타입에 의존하는 코드가 있으면 컴파일 에러 발생 가능
- `AUTO_RUN_STEPS`의 `label` 타입: `"배경·BGM" | "Images" | "TTS" | "Render"` → `"배경·BGM" | "이미지" | "TTS" | "렌더"` — 리터럴 타입 직접 참조 코드가 없으면 안전

### 영향 범위
- 전체 프론트엔드

### 테스트 전략
- `npm run build` 성공
- `npx tsc --noEmit` 성공

### Out of Scope
- 빌드 최적화

---

## 변경 파일 총괄

| # | 파일 | 변경 내용 | 난이도 |
|---|------|----------|--------|
| 1 | `components/shell/ServiceShell.tsx` | NavBar 라벨 + Dev 제거 | 낮음 |
| 2 | `components/studio/StudioWorkspaceTabs.tsx` | Studio 탭 라벨 | 낮음 |
| 3 | `components/shell/LibraryShell.tsx` | Library 탭 라벨 | 낮음 |
| 4 | `components/shell/SettingsShell.tsx` | Settings 탭 라벨 | 낮음 |
| 5 | `components/studio/PipelineStatusDots.tsx` | STEPS + tooltip 한국어 | 중간 |
| 6 | `components/common/PreflightModal.tsx` | STEP_LABELS | 낮음 |
| 7 | `components/home/ContinueWorkingSection.tsx` | STEP_META + 섹션 제목 | 낮음 |
| 8 | `components/home/QuickStatsBar.tsx` | 카테고리 라벨 | 낮음 |
| 9 | `constants/index.ts` | AUTO_RUN_STEPS label | 낮음 |
| 10 | `components/studio/MaterialsPopover.tsx` | 항목 라벨 + 상태 텍스트 | 낮음 |
| 11 | `e2e/smoke.spec.ts` | NavBar + Studio 탭 매칭 | 낮음 |
| 12 | `e2e/qa-patrol.spec.ts` | NavBar + Studio 탭 + Settings 매칭 | 낮음 |
| 13 | `tests/vrt/studio-e2e.spec.ts` | Studio 탭 매칭 | 낮음 |
| 14 | `tests/vrt/home.spec.ts` | NavBar + Continue Working 매칭 | 낮음 |
| 15 | `tests/vrt/warning-toast-e2e.spec.ts` | Script 탭 매칭 | 낮음 |

**총 15개 파일, 난이도 전체 낮음~중간, 로직 변경 0건**

---

## 구현 순서

1. **소스 파일 변경** (DoD 1~10): 10개 파일 라벨 교체
2. **빌드 확인** (DoD-13): `npm run build` 성공
3. **E2E 테스트 매칭 수정** (DoD-11): 5개 테스트 파일
4. **VRT 베이스라인 갱신** (DoD-12): 스냅샷 업데이트
5. **전체 테스트 실행**: vitest + playwright 통과 확인
