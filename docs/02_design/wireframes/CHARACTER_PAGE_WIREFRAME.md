# Character Management Page - Wireframe & Design Spec

> 상태: 설계 완료 / 구현 미착수
> 작성일: 2026-02-11
> 관련: `docs/01_product/FEATURES/CHARACTER_PAGE.md`

---

## 1. 설계 배경

### 현재 문제점

1. **캐릭터 관리가 Home 페이지에 종속**: `CharactersSection`이 Home(/)의 스토리보드 목록 아래에 섹션으로 끼워져 있어, 캐릭터가 10개 이상일 때 스크롤이 길어진다.
2. **모달 기반 편집의 한계**: `CharacterEditModal`이 20KB 대형 모달로, 세로 스크롤이 길고 섹션 간 이동이 어렵다. 태그 편집, LoRA 설정, 레퍼런스 프롬프트 등 고급 기능을 모달 안에서 처리하면 작업 공간이 좁다.
3. **네비게이션 격차**: Home/Lab/Manage 3탭 중 캐릭터 전용 진입점이 없어, 캐릭터 작업 시 항상 Home을 경유해야 한다.

### 설계 원칙 적용

| 디자인 원칙 | 이 설계에서의 적용 |
|-------------|-------------------|
| 점진적 공개 | 목록 페이지는 카드 그리드로 단순하게, 상세 페이지에서 섹션별로 고급 기능 노출 |
| 밀도 있는 정보 표면 | 캐릭터 카드에 프리뷰+이름+태그요약+LoRA배지를 밀도 있게 배치 |
| 일관된 수공예 | Manage 페이지의 사이드바+콘텐츠 패턴, StoryboardCard 카드 스타일 재활용 |
| 선형 파이프라인 | 목록 -> 상세 -> 편집의 자연스러운 흐름 |

---

## 2. 네비게이션 변경

### Before

```
[Home]  [Lab]  [Manage]
  /      /lab   /manage
```

### After

```
[Home]  [Characters]  [Lab]  [Manage]
  /      /characters   /lab   /manage
```

### 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `components/shell/AppShell.tsx` | `NAV_ITEMS`에 Characters 항목 추가 (icon: `Users`) |
| `app/(app)/characters/page.tsx` | 신규: 캐릭터 목록 페이지 |
| `app/(app)/characters/[id]/page.tsx` | 신규: 캐릭터 상세/편집 페이지 |
| `app/(app)/page.tsx` | CharactersSection 축소 (최근 3개 미리보기 + "View All" 링크) |

### NAV_ITEMS 변경 다이어그램

```typescript
const NAV_ITEMS = [
  { href: "/",           label: "Home",       icon: Home,          exact: true  },
  { href: "/characters", label: "Characters", icon: Users,         exact: false },  // NEW
  { href: "/lab",        label: "Lab",        icon: FlaskConical,  exact: false },
  { href: "/manage",     label: "Manage",     icon: Settings,      exact: false },
] as const;
```

### AppShell Sidebar 조건 변경

```
// Before
showSidebar = !pathname.startsWith("/manage") && !pathname.startsWith("/lab");

// After
showSidebar = !pathname.startsWith("/manage")
           && !pathname.startsWith("/lab")
           && !pathname.startsWith("/characters");
```

캐릭터 페이지는 독립 레이아웃을 사용하므로 글로벌 사이드바(Project/Group)를 숨긴다. 캐릭터는 Global 엔티티(project_id가 nullable)이므로 프로젝트/그룹 컨텍스트 불필요.

---

## 3. 캐릭터 목록 페이지 (/characters)

### 3.1 와이어프레임

```
+------------------------------------------------------------------+
| [Home]  [*Characters*]  [Lab]  [Manage]              Cmd+K       |
+------------------------------------------------------------------+
|                                                                   |
|  Characters (12)                              [+ New Character]   |
|                                                                   |
|  [Search characters...]           [Filter: All / Has LoRA / ...]  |
|                                                                   |
|  +------------------+  +------------------+  +------------------+ |
|  | +-----+          |  | +-----+          |  | +-----+          | |
|  | |     | Sakura   |  | |     | Hinata   |  | |     | Miku     | |
|  | | IMG | Female   |  | | IMG | Female   |  | | IMG | Female   | |
|  | +-----+          |  | +-----+          |  | +-----+          | |
|  |                   |  |                   |  |                   |
|  | brown_hair,       |  | black_hair,       |  | twintails,       |
|  | school_uniform    |  | long_hair         |  | blue_hair        |
|  |                   |  |                   |  |                   |
|  | [LoRA] [IP-A]     |  | [LoRA]            |  | [LoRA] [Locked]  |
|  +------------------+  +------------------+  +------------------+ |
|                                                                   |
|  +------------------+  +------------------+  +------------------+ |
|  | +-----+          |  | +-----+          |  |     + + +        | |
|  | |     | Rem      |  | |     | Emilia   |  |                   | |
|  | | IMG | Female   |  | | IMG | Female   |  |  + New Character  | |
|  | +-----+          |  | +-----+          |  |                   | |
|  |                   |  |                   |  |  Click to create  | |
|  | blue_hair,        |  | silver_hair,      |  |  a new character  | |
|  | maid              |  | half_elf          |  |                   | |
|  |                   |  |                   |  |                   | |
|  | [LoRA] [Locked]   |  | [LoRA]            |  |                   | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                   |
+------------------------------------------------------------------+
```

### 3.2 빈 상태

```
+------------------------------------------------------------------+
| [Home]  [*Characters*]  [Lab]  [Manage]              Cmd+K       |
+------------------------------------------------------------------+
|                                                                   |
|  Characters                                                       |
|                                                                   |
|                                                                   |
|                       [person icon]                               |
|                                                                   |
|                   No characters yet                               |
|             Characters maintain visual consistency                 |
|               across all scenes in your shorts.                   |
|                                                                   |
|                   [+ New Character]                               |
|                                                                   |
|                                                                   |
+------------------------------------------------------------------+
```

### 3.3 캐릭터 카드 상세 레이아웃

```
+-------------------------------+
|  +--------+                   |
|  |        |  Name             |
|  | Preview|  Gender           |
|  | 80x80  |                   |
|  +--------+                   |
|                               |
|  tag1, tag2, tag3, ...        |  <-- Identity 태그 요약 (최대 5개, +N more)
|                               |
|  [LoRA badge]  [Locked badge] |  <-- 조건부 배지
|  [auto] or [lora] or [std]    |  <-- prompt_mode 배지
+-------------------------------+
```

### 3.4 카드 배지 규칙

| 조건 | 배지 | 색상 |
|------|------|------|
| `loras.length > 0` | `LoRA x{count}` | `bg-indigo-100 text-indigo-700` |
| `prompt_mode === "lora"` | `lora` | `bg-violet-100 text-violet-700` |
| `prompt_mode === "standard"` | `standard` | `bg-zinc-100 text-zinc-600` |
| `prompt_mode === "auto"` | `auto` | `bg-emerald-100 text-emerald-700` |
| `preview_image_url` 없음 | `No Image` | `bg-rose-100 text-rose-600` |

### 3.5 검색/필터

검색과 필터는 V1에서 선택적 구현. 최소한의 인터페이스:

- **검색**: `name`, `description` 텍스트 매칭 (프론트엔드 필터링, 캐릭터 수가 보통 20개 미만)
- **필터 옵션**:
  - All (기본)
  - Has LoRA (`loras.length > 0`)
  - Has Preview (`preview_image_url !== null`)

```
[Search characters...]  [All v]
                         ├─ All
                         ├─ Has LoRA
                         ├─ Has Preview
                         └─ Locked
```

---

## 4. 캐릭터 상세/편집 페이지 (/characters/[id])

### 4.1 레이아웃 전략: 사이드바 + 메인 콘텐츠

Manage 페이지의 `ManageSidebar + Content` 패턴을 재활용한다. 좌측에 캐릭터 프리뷰 + 기본 정보를 고정하고, 우측에 편집 섹션을 탭 또는 스크롤로 배치한다.

### 4.2 와이어프레임

```
+-------------------------------------------------------------------+
| [Home]  [*Characters*]  [Lab]  [Manage]               Cmd+K       |
+-------------------------------------------------------------------+
|              |                                                      |
|  <- Back     |  Basic Info                            [Save] [Del] |
|              |  -------------------------------------------------- |
|  +--------+  |  Name    [Sakura Haruno    ]                        |
|  |        |  |  Gender  [Female v]                                 |
|  | Preview |  |  Desc    [A cheerful ninja with pink hair...    ]  |
|  | Image   |  |  Mode   [Auto (Smart Compose) v]                  |
|  | 160x200 |  |                                                    |
|  |        |  |  ------------------------------------------------  |
|  +--------+  |                                                      |
|              |  IP-Adapter                                          |
|  [Locked]    |  -------------------------------------------------- |
|              |  Weight  [====O=========] 0.65                      |
|  [Generate]  |  Model   [clip_face v]                              |
|  [Enhance ]  |                                                      |
|  [Edit AI ]  |  ------------------------------------------------  |
|              |                                                      |
|  Voice       |  Identity Tags                    [Edit as Text]    |
|  [Preset v]  |  -------------------------------------------------- |
|              |  [pink_hair x] [green_eyes x] [forehead_mark x]    |
|              |  [+ Add tag________________]                        |
|              |                                                      |
|              |  Clothing Tags                    [Edit as Text]    |
|              |  -------------------------------------------------- |
|              |  [red_vest x] [black_shorts x] [headband x]        |
|              |  [+ Add tag________________]                        |
|              |                                                      |
|              |  ------------------------------------------------  |
|              |                                                      |
|              |  LoRAs                              [+ Add LoRA]    |
|              |  -------------------------------------------------- |
|              |  | sakura_haruno_v3 [character v] weight: [0.8]  x | |
|              |  | anime_style_v2   [style v]     weight: [0.3]  x | |
|              |                                                      |
|              |  ------------------------------------------------  |
|              |                                                      |
|              |  Scene Identity (Fixed Appearance)                   |
|              |  -------------------------------------------------- |
|              |  [masterpiece, best_quality, 1girl, pink_hair,   ]  |
|              |  [green_eyes, forehead_mark, ...                 ]  |
|              |                                                      |
|              |  Common Negative (Scene)                             |
|              |  -------------------------------------------------- |
|              |  [lowres, bad_anatomy, ...                        ]  |
|              |                                                      |
|              |  ------------------------------------------------  |
|              |                                                      |
|              |  Reference Image Generation          [IP-Adapter]   |
|              |  -------------------------------------------------- |
|              |  Reference Positive    |  Reference Negative         |
|              |  [...................] |  [....................]      |
|              |  [SET STUDIO SETUP]    |  [RESET TO DEFAULT]         |
|              |                                                      |
+-------------------------------------------------------------------+
```

### 4.3 좌측 사이드 패널 (Sticky)

```
+------------------+
|  <- Characters   |  <-- /characters 로 돌아가기
|                  |
|  +------------+  |
|  |            |  |
|  |  Preview   |  |
|  |  Image     |  |
|  |  160x200   |  |
|  |            |  |
|  +------------+  |
|                  |
|  [Locked/Unlock] |  <-- 프리뷰 잠금 토글
|                  |
|  [Generate    ]  |  <-- 레퍼런스 이미지 생성
|  [Enhance     ]  |  <-- 이미지 고화질화
|  [Edit w/ AI  ]  |  <-- Gemini 편집 (모달)
|                  |
|  ─────────────── |
|                  |
|  Voice Preset    |
|  [Default v   ]  |
|                  |
+------------------+
```

- 너비: `w-64` (256px)
- `position: sticky; top: var(--nav-height)`로 스크롤 시 고정
- 프리뷰 이미지 클릭 시 `ImagePreviewModal` 열기 (기존 컴포넌트 재활용)

### 4.4 우측 메인 콘텐츠 섹션

| 순서 | 섹션 | 기존 컴포넌트 | 재활용/신규 |
|------|------|-------------|-----------|
| 1 | Basic Info | `BasicInfoSection` (CharacterEditModal 내부) | 추출하여 독립 컴포넌트화 |
| 2 | IP-Adapter | `IpAdapterSection` (CharacterEditModal 내부) | 추출하여 독립 컴포넌트화 |
| 3 | Identity Tags | `CharacterTagsEditor` | **재활용** (기존 그대로) |
| 4 | Clothing Tags | `CharacterTagsEditor` | **재활용** (기존 그대로) |
| 5 | LoRAs | `LoRAsSection` (CharacterEditModal 내부) | 추출하여 독립 컴포넌트화 |
| 6 | Scene Identity | `SceneIdentitySection` (CharacterEditModal 내부) | 추출하여 독립 컴포넌트화 |
| 7 | Reference Prompts | `ReferencePromptsPanel` | **재활용** (기존 그대로) |

### 4.5 신규 캐릭터 생성 (/characters/new)

`/characters/new` 경로로 진입하면 빈 폼의 편집 페이지가 표시된다. `[id]` 동적 라우트에서 `id === "new"`를 분기 처리한다.

- 좌측 패널의 프리뷰 이미지: "No image" 플레이스홀더
- Generate/Enhance/Edit 버튼: disabled (저장 후 활성화)
- 하단 Save 버튼: "Create Character"로 텍스트 변경
- 저장 성공 시 `/characters/{newId}`로 리다이렉트

---

## 5. Home 페이지 변경

### 5.1 현재 Home

```
+-------------------------------+
| Storyboards (5)  [+ New]      |
| [card] [card] [card]          |
| [card] [card]                 |
|                               |
| ─────────────────────────     |
|                               |
| Characters (12)  [+ New]      |
| [card] [card] [card]          |
| [card] [card] [card]          |
| [card] [card] [card]          |
| [card] [card] [card]          |
|                               |
| Footer                        |
+-------------------------------+
```

### 5.2 변경 후 Home

```
+--------------------------------------+
| Storyboards (5)           [+ New]    |
| [card] [card] [card]                 |
| [card] [card]                        |
|                                      |
| ─────────────────────────            |
|                                      |
| Characters (12)       [View All ->]  |
| [mini-card] [mini-card] [mini-card]  |
|                                      |
| Footer                               |
+--------------------------------------+
```

### 5.3 미니 캐릭터 카드

Home 페이지에서는 최근 수정된 캐릭터 3개만 미니 카드로 표시한다.

```
+-----------------------------+
| [40x40 img]  Sakura         |
|              pink_hair, ... |
+-----------------------------+
```

- 카드 클릭: `/characters/{id}` 상세 페이지로 이동
- "View All ->" 링크: `/characters` 목록 페이지로 이동
- 캐릭터가 0개일 때: "No characters yet" + `/characters` 링크

---

## 6. 컴포넌트 재활용/신규 판단

### 6.1 재활용 (변경 없이 그대로 사용)

| 컴포넌트 | 파일 | 비고 |
|----------|------|------|
| `CharacterTagsEditor` | `manage/CharacterTagsEditor.tsx` | 태그 편집 UI 그대로 |
| `ReferencePromptsPanel` | `manage/ReferencePromptsPanel.tsx` | 레퍼런스 프롬프트 |
| `GeminiPreviewEditModal` | `manage/GeminiPreviewEditModal.tsx` | AI 편집 모달 |
| `ImagePreviewModal` | `components/ui/ImagePreviewModal.tsx` | 이미지 확대 |
| `Button` | `components/ui/Button.tsx` | 모든 CTA 버튼 |
| `Badge` | `components/ui/Badge.tsx` | 상태 배지 |
| `ConfirmDialog` | `components/ui/ConfirmDialog.tsx` | 삭제 확인 |
| `LoadingSpinner` | `components/ui/LoadingSpinner.tsx` | 로딩 상태 |

### 6.2 추출 (CharacterEditModal에서 독립 컴포넌트로 분리)

| 현재 위치 | 신규 파일 | 비고 |
|----------|----------|------|
| `CharacterEditModal` 내부 `BasicInfoSection` | `characters/sections/BasicInfoSection.tsx` | 이름/성별/설명 폼 |
| `CharacterEditModal` 내부 `IpAdapterSection` | `characters/sections/IpAdapterSection.tsx` | IP-Adapter 가중치/모델 |
| `CharacterEditModal` 내부 `LoRAsSection` | `characters/sections/LoRAsSection.tsx` | LoRA 다중선택/가중치 |
| `CharacterEditModal` 내부 `SceneIdentitySection` | `characters/sections/SceneIdentitySection.tsx` | 커스텀 프롬프트 |
| `CharacterEditModal` 내부 `PromptModeSection` | `characters/sections/PromptModeSection.tsx` | 프롬프트 모드 선택 |
| `CharacterEditModal` 내부 `VoicePresetSection` | `characters/sections/VoicePresetSection.tsx` | 보이스 프리셋 |
| `manage/PreviewImageSection` | `characters/sections/PreviewImageSection.tsx` | 프리뷰 이미지 관리 |

### 6.3 신규 생성

| 컴포넌트 | 파일 | 역할 |
|----------|------|------|
| `CharactersPage` | `app/(app)/characters/page.tsx` | 목록 페이지 |
| `CharacterDetailPage` | `app/(app)/characters/[id]/page.tsx` | 상세/편집 페이지 |
| `CharacterCard` | `app/(app)/characters/CharacterCard.tsx` | 목록 카드 |
| `CharacterSidePanel` | `app/(app)/characters/CharacterSidePanel.tsx` | 좌측 프리뷰+액션 패널 |
| `CharacterMiniCard` | `app/components/home/CharacterMiniCard.tsx` | Home 미니 카드 |
| `useCharacterDetail` | `app/(app)/characters/hooks/useCharacterDetail.ts` | 단일 캐릭터 fetch/save hook |

### 6.4 수정 필요

| 컴포넌트 | 변경 내용 |
|----------|----------|
| `AppShell.tsx` | NAV_ITEMS에 Characters 추가, showSidebar 조건 변경 |
| `CharactersSection.tsx` | 최근 3개 미니카드 + "View All" 링크로 축소 |
| `useCharacterForm.ts` | 모달/페이지 양쪽에서 사용 가능하도록 `onClose` 옵셔널화 |
| `CharacterEditModal.tsx` | 추출된 섹션 import 경로 변경 (호환성 유지) |
| `CharacterSelector.tsx` | 선택 시 `/characters/{id}` 링크 추가 (선택적) |

---

## 7. 모달 -> 페이지 전환 UX 고려사항

### 7.1 장점

| 항목 | 모달 (현재) | 페이지 (제안) |
|------|-----------|-------------|
| 작업 공간 | 90vh, max-w-2xl (640px) | 전체 화면 (1024px+) |
| URL | 없음 (상태 손실 가능) | `/characters/3` (북마크/공유 가능) |
| 뒤로가기 | ESC로 닫기 | 브라우저 뒤로가기 자연스럽게 동작 |
| 멀티태스킹 | 배경 페이지 가려짐 | 탭으로 목록과 상세를 왔다갔다 가능 |
| 스크롤 | 모달 내부 스크롤 (awkward) | 페이지 전체 스크롤 (자연스러움) |
| 접근성 | focus trap 필요 | 표준 페이지 내비게이션 |

### 7.2 전환 전략

1. **점진적 전환**: 기존 `CharacterEditModal`을 즉시 제거하지 않는다.
   - Phase 1: `/characters` 목록 + `/characters/[id]` 상세 페이지 구축
   - Phase 2: Home 페이지의 CharactersSection에서 카드 클릭 시 `/characters/[id]`로 이동 (모달 대신)
   - Phase 3: 다른 곳(CharacterSelector 등)에서의 "Quick Edit" 용도로 모달은 경량 버전으로 유지 (기본 정보 + 태그만)

2. **데이터 손실 방지**: 편집 중 페이지 이탈 시 `beforeunload` 이벤트 또는 Next.js route change intercept로 "저장하지 않은 변경사항이 있습니다" 경고 표시.

3. **자동 저장 검토**: 페이지 기반이므로 디바운스 자동 저장(2초 지연)을 검토. 단, V1에서는 명시적 Save 버튼을 유지하고, 자동 저장은 향후 개선 사항으로 남긴다.

4. **Quick Create 유지**: Home 페이지와 `/characters` 목록에서 "+ New Character" 클릭 시 `/characters/new`로 이동. 간단한 생성이 필요한 경우(Lab의 CharacterPicker 등)를 위해 경량 모달 옵션도 고려.

### 7.3 기존 참조 유지

다른 컴포넌트에서 캐릭터를 참조하는 곳의 변경 최소화:

| 컴포넌트 | 현재 동작 | 변경 후 |
|----------|----------|--------|
| `CharacterSelector` (setup/) | 드롭다운으로 선택 | 변경 없음. 선택 옆에 "Edit" 아이콘 추가 시 `/characters/{id}` 링크 |
| `CharacterPicker` (lab/) | Speaker A/B 드롭다운 | 변경 없음 |
| `SceneCharacterActions` (storyboard/) | 씬 내 캐릭터 액션 | 변경 없음 |

---

## 8. 파일 구조 (최종)

```
frontend/app/(app)/characters/
  page.tsx                        # 목록 페이지
  [id]/
    page.tsx                      # 상세/편집 페이지 (id="new"이면 생성 모드)
  CharacterCard.tsx               # 목록용 카드 컴포넌트
  CharacterSidePanel.tsx          # 좌측 프리뷰+액션 패널
  hooks/
    useCharacterDetail.ts         # 단일 캐릭터 CRUD hook
  sections/                       # CharacterEditModal에서 추출한 섹션들
    BasicInfoSection.tsx
    IpAdapterSection.tsx
    PromptModeSection.tsx
    LoRAsSection.tsx
    SceneIdentitySection.tsx
    VoicePresetSection.tsx
    PreviewImageSection.tsx       # manage/PreviewImageSection.tsx 이동

frontend/app/components/home/
  CharactersSection.tsx           # 수정: 미니카드 3개 + "View All" 링크
  CharacterMiniCard.tsx           # 신규: Home용 미니 카드
```

---

## 9. 반응형 고려사항

### Desktop (lg 이상, 1024px+)

- 목록: 3열 그리드 (`grid-cols-3`)
- 상세: 좌측 사이드패널(w-64) + 우측 콘텐츠

### Tablet (md, 768px~1023px)

- 목록: 2열 그리드 (`grid-cols-2`)
- 상세: 사이드패널 상단 고정 (horizontal layout) + 아래 콘텐츠 스크롤

### Mobile (sm 이하, ~767px)

- 목록: 1열 (`grid-cols-1`)
- 상세: 사이드패널 숨김, 프리뷰 이미지를 콘텐츠 상단에 인라인 배치

```
Desktop                   Tablet/Mobile
+------+----------+      +------------------+
| Side | Content  |      | [img] Name       |
| Panel|          |      | [Locked] [Gen]   |
|      |          |      +------------------+
|      |          |      | Content sections |
|      |          |      | (full width)     |
+------+----------+      +------------------+
```

---

## 10. 접근성 체크리스트

| 항목 | 구현 방법 |
|------|----------|
| 키보드 내비게이션 | 카드 그리드에서 Tab으로 이동, Enter로 상세 진입 |
| 카드 role | `role="link"` 또는 `<a>` 래핑 (Next.js `Link`) |
| 이미지 alt 텍스트 | `alt="{character.name} preview"` |
| 폼 라벨 연결 | 모든 input에 `id` + `<label htmlFor>` |
| 포커스 관리 | 상세 페이지 진입 시 제목(h1)에 포커스 |
| 색상 대비 | 배지 텍스트: WCAG AA 기준 충족 (현재 디자인 토큰 준수) |
| 삭제 확인 | `ConfirmDialog` 재활용 (포커스 트랩 내장) |

---

## 11. Backend 의존성

### 선행 작업: `services/characters/` 패키지 분리

Backend 캐릭터 관리 코드 리팩토링이 병행 진행 중. **API 인터페이스(URL, Request/Response 스키마)는 변경 없음** — 내부 구조만 정리.

| 결정 | 내용 |
|------|------|
| 전략 | (B) 현재 API 기준으로 프론트엔드 구현. Backend는 내부 구조만 변경 (API 호환 유지) |
| Frontend 영향 | 없음. `useCharacters` hook이 호출하는 엔드포인트 URL/스키마 동일 |
| 순서 | Backend 리팩토링 → Frontend 페이지 구현 (권장). 단, 병렬 진행도 가능 |

---

## 12. 모달 정리 전략

### CharacterEditModal 최종 상태

| Phase | `CharacterEditModal` (564줄) 상태 |
|-------|----------------------------------|
| Phase 1 완료 | 섹션 7개를 `characters/sections/`로 추출. 모달은 추출된 섹션을 import하여 동작 유지 (~200줄) |
| Phase 2 완료 | Home/목록 카드 클릭 → `/characters/[id]` 페이지로 이동. 모달 호출 경로 제거 |
| 최종 | **경량 QuickEditModal 유지** (기본 정보 + 태그만, ~100줄). 용도: Lab CharacterPicker 등에서 간단 편집 |

### `shared/CharacterEditModal.tsx` (re-export) 처리

- Phase 1: `characters/sections/` 추출 후 re-export 경로를 새 위치로 변경
- Phase 2: QuickEditModal로 교체하거나, 더 이상 import하는 곳이 없으면 삭제

---

## 13. 구현 우선순위 (PM 리뷰 반영)

> S-1 반영: Phase 1+2 통합 — 목록만 만들면 카드 클릭 시 갈 곳이 없으므로 함께 구현

| Phase | 범위 | DoD |
|-------|------|-----|
| **Phase 1** | 목록 + 상세/편집 페이지 + 네비게이션 변경 | `/characters` 카드 표시 + `/characters/[id]` 전 섹션 렌더링 + Save 영속 + 새로고침 복구 |
| **Phase 2** | Home 축소 + 기존 모달 정리 | 미니카드 3개 + "View All" 동작 + QuickEditModal 경량화 |
| **Phase 3** | 반응형 + 접근성 | 태블릿/모바일 레이아웃 + 키보드 내비게이션 + ARIA |

---

*이 문서는 구현 전 설계 리뷰 용도입니다. 코드 구현은 이 와이어프레임이 승인된 후 별도로 진행합니다.*
