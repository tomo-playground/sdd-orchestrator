> **ARCHIVED (2026-03-17)**: 현재 코드와 불일치하여 아카이브됨. 현행 설계는 코드 및 CLAUDE.md를 참조.

# Shorts Producer -- Design Philosophy

> 이 문서는 Frontend/Backend 코드베이스 전체 분석과 제품/기술 관점을 종합하여 도출한 디자인 철학이다.
> 새로운 기능 개발, UI 리뷰, 디자인 결정 시 기준 문서로 활용한다.

---

## 포지셔닝

**"Shorts Producer는 AI가 초안을 만들고, 사람이 품질을 결정하는 영상 제작 워크스테이션이다."**

```
접근성 높음 ←──────────────────────────────────→ 제어력 높음

  Canva        Pika        CapCut      ★ Shorts Producer     Runway
  (템플릿)   (프롬프트→영상)  (편집 속도)  (AI 파이프라인 제어)  (프로 VFX)
```

| 경쟁 제품 | 핵심 가치 | 우리와의 차이 |
|-----------|-----------|--------------|
| CapCut | 템플릿 + 편집 속도 | 우리는 "편집"이 아닌 "콘텐츠 생성" 자체를 자동화 |
| Runway | 프로 정밀 제어 | 우리는 파이프라인 자동화(Autopilot)를 기본값으로 제공 |
| Pika | 접근성 우선 | 우리는 LoRA/IP-Adapter로 캐릭터 일관성을 해결 |
| Canva | 비전문가 친화 | 우리는 12-Layer 프롬프트로 세밀한 제어 가능 |

### 차별화 포인트
1. **캐릭터 일관성 엔진**: LoRA + IP-Adapter + ControlNet 조합. Pika/Runway에는 없는 기능.
2. **로컬 AI 주권**: SD WebUI + Qwen TTS를 로컬 구동. 클라우드 비용 통제.
3. **스토리보드-센트릭 워크플로우**: Gemini 기획 → WD14 검증 → SD 생성의 통합 오케스트레이션.
4. **프롬프트 엔지니어링 내재화**: 12-Layer Prompt Builder + Tag 시스템으로 "좋은 프롬프트"를 시스템이 보장.

### 대상 사용자
| 속성 | 프로파일 |
|------|----------|
| 페르소나 | 1인 크리에이터 또는 소규모 팀 (2~3인). 숏폼 콘텐츠를 정기적으로 생산 |
| 기술 수준 | 중급. SD WebUI, LoRA 용어를 이해하고 프롬프트를 직접 수정할 의지가 있음 |
| 사용 빈도 | 주 3~5회. 세션당 스토리보드 1~3개, 각 5~8씬 |
| 핵심 목표 | "주제를 넣으면 일관된 캐릭터/화풍의 숏폼 영상이 나온다" |
| 통점 | AI 결과 불확실성, 캐릭터 일관성 유지, 생성-검수-수정 루프의 수동 반복 |

---

## 5대 디자인 원칙

### 원칙 1. 점진적 공개 (Progressive Disclosure)

**정의**: 사용자가 필요할 때만 복잡성을 마주하게 한다. 기본 경로는 단순하고, 고급 옵션은 요청 시 드러난다.

**현재 적용 사례**:
- `StoryboardActionsBar`: Generate(단순) vs Auto Run(원클릭 전체) 2단계 CTA 분리
  - 파일: `/frontend/app/components/storyboard/StoryboardActionsBar.tsx`
- `PromptSetupPanel`: Global Settings가 Collapsible로 기본 접혀있음
  - 파일: `/frontend/app/components/setup/PromptSetupPanel.tsx` (L61-129)
- `RenderSettingsPanel`: Media Settings가 `<details>` 태그로 접힌 상태
  - 파일: `/frontend/app/components/video/RenderSettingsPanel.tsx` (L297)
- `SceneCard`: validate/debug 탭이 명시적 클릭 시에만 노출
  - 파일: `/frontend/app/components/storyboard/SceneCard.tsx` (L285-313)
- `GenerationSettings`: SD 파라미터(steps, cfg_scale, sampler 등)가 별도 영역

**Do**:
- 핵심 액션(Generate, Render)은 항상 보이게 유지한다
- 고급 설정(SD 파라미터, ControlNet, IP-Adapter)은 접을 수 있는 패널 안에 배치한다
- 빈 상태(Empty State)에서는 다음 단계로의 명확한 유도 CTA를 제공한다
  - 현재 좋은 사례: `ScenesTab`의 "No scenes yet. Generate a storyboard first." + "Go to Plan" 버튼

**Don't**:
- 하나의 화면에 모든 옵션을 평면적으로 나열하지 않는다
- 초보자에게 Danbooru 태그, LoRA weight, CFG Scale 같은 용어를 설명 없이 노출하지 않는다
- "숨겨진 기능"을 만들지 않는다 -- 접힌 패널이라도 헤더에 힌트를 준다

---

### 원칙 2. AI 협업 투명성 (Transparent AI Collaboration)

**정의**: AI가 무엇을 했는지, 왜 그렇게 했는지, 사용자가 어떻게 바꿀 수 있는지를 항상 보여준다. AI는 "마법 상자"가 아니라 "투명한 협업자"다.

**현재 적용 사례**:
- `AutoRunStatus`: Autopilot의 현재 단계(storyboard/image/validate/render)를 pill 배지로 시각화
  - 파일: `/frontend/app/components/storyboard/AutoRunStatus.tsx`
  - 각 단계가 `isActive`/`isDone` 상태로 색상 분리 (L42-53)
- `SceneCard` 품질 배지: Match Rate를 퍼센트로 표시 (Excellent/Good/Poor)
  - 파일: `/frontend/app/components/storyboard/SceneCard.tsx` (L126-130)
- `FixSuggestionsPanel`: 검증 실패 시 구체적 수정 제안과 원클릭 적용
- `DebugTabContent`: 최종 SD 페이로드(prompt, negative, steps 등)를 JSON으로 확인 가능
- `ValidationTabContent`: 이미지-프롬프트 태그 일치도를 시각적으로 검증

**Do**:
- AI가 생성한 모든 결과물에 "이유"를 함께 제공한다 (매치율, 누락 태그, 실패 원인)
- Autopilot 진행 상황을 실시간 로그와 스텝 인디케이터로 보여준다
- 사용자가 AI 결과를 부분적으로 수정할 수 있는 인라인 편집을 제공한다

**Don't**:
- "AI가 알아서 했습니다"로 끝내지 않는다 -- 반드시 검증/수정 경로를 함께 제공한다
- AI 오류를 숨기지 않는다 -- AutoRunStatus의 에러 상태와 Resume/Restart 옵션처럼 복구 경로를 제공한다
- 자동 생성 결과를 사용자 확인 없이 최종 결과로 확정하지 않는다

---

### 원칙 3. 선형 파이프라인, 자유로운 탐색 (Linear Pipeline, Free Navigation)

**정의**: 기본 워크플로우는 Plan -> Scenes -> Render -> Video의 선형 흐름이지만, 사용자는 언제든 이전 단계로 돌아가 수정할 수 있다. **탭 전환은 "맥락 전환"이 아닌 "관점 전환"이다** -- 같은 스토리보드를 기획(Plan), 시각화(Scenes), 출력(Render) 관점에서 바라보는 것이다.

**현재 적용 사례**:
- `TabBar`: 5개 탭(Plan/Scenes/Render/Video/Insights)에 진행 인디케이터(dot + connector line) 표시
  - 파일: `/frontend/app/components/studio/TabBar.tsx`
  - STEPS 배열로 선형 흐름을 시각화 (L14-19)
  - `done` 배열로 각 단계의 완료 여부를 점(filled dot)으로 표시 (L38)
  - 점선(dashed)/실선(solid) 커넥터로 미완료/완료 구간을 구분 (L85)
- `ScenesTab`: 빈 상태에서 "Go to Plan" 버튼으로 이전 단계 유도
  - 파일: `/frontend/app/components/studio/ScenesTab.tsx` (L163-174)
- `SceneFilmstrip`: 좌우 화살표 + 직접 클릭으로 씬 간 자유 탐색
  - 파일: `/frontend/app/components/storyboard/SceneFilmstrip.tsx`
- Tab badges: Scenes 탭에 씬 수, Video 탭에 영상 수를 배지로 표시하여 상태 인지 지원

**Do**:
- 현재 위치(어느 단계, 어느 씬)를 항상 명확히 표시한다
- 각 탭에서 이전/다음 단계로의 자연스러운 전환 경로를 제공한다
- 완료된 단계의 결과물 개수를 배지로 표시하여 진행 상황을 한눈에 보여준다

**Don't**:
- 특정 단계를 완료하지 않으면 다음 단계로 이동할 수 없게 잠그지 않는다 (탭은 항상 접근 가능)
- 단계를 뒤로 돌아갔을 때 이미 만든 결과물을 경고 없이 삭제하지 않는다
- 진행 상태를 숨기지 않는다 -- 사용자는 전체 파이프라인에서 자신의 위치를 알아야 한다

---

### 원칙 4. 밀도 있는 정보 표면 (Dense Information Surfaces)

**정의**: 숏폼 영상 제작은 많은 파라미터를 다룬다 (프롬프트, 태그, SD 설정, 레이아웃, 음성, BGM, 자막, 트랜지션...). 정보를 밀도 있게 배치하되, 시각적 계층으로 읽기 부담을 줄인다.

**현재 적용 사례**:
- `SceneCard` 2-column 그리드: 왼쪽 폼 필드 + 오른쪽 이미지 패널
  - 파일: `/frontend/app/components/storyboard/SceneCard.tsx` (L237: `grid gap-4 md:grid-cols-[1.2fr_1fr]`)
- `RenderSettingsPanel` 다층 정보 구조:
  - 1층: Layout 토글 + Render CTA (항상 노출)
  - 2층: Media Settings (details로 접기/펼치기)
  - 3층: Video Row (Scene Text + Font + 미리보기) 3-column 그리드
  - 4층: Audio (BGM + Volume + Ducking) 인라인 배치
  - 파일: `/frontend/app/components/video/RenderSettingsPanel.tsx`
- `StoryboardGeneratorPanel` 2-column: 왼쪽 Topic/Description + 오른쪽 Duration/Language/Structure
  - 파일: `/frontend/app/components/storyboard/StoryboardGeneratorPanel.tsx` (L151)
- 일관된 라벨 시스템:
  - `text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase` 패턴이 전역적으로 사용됨
  - 파일: `/frontend/app/components/ui/variants.ts` (LABEL_CLASSES)

**Do**:
- 관련 정보를 그리드로 묶어 시각적 블록을 형성한다
- 상위(Layout, Render) -> 하위(Font, BGM, Ken Burns) 순서로 계층을 구성한다
- 매우 작은 텍스트(9px-10px)라도 uppercase + tracking으로 가독성을 확보한다
- 숫자/상태값은 배지(pill)로 표현하여 본문과 시각적으로 분리한다

**Don't**:
- 한 섹션에 5개 이상의 독립 설정을 세로로 나열하지 않는다 -- 그리드로 묶는다
- 모든 설정을 같은 시각적 비중으로 처리하지 않는다 -- 핵심(Layout, Render)은 크게, 부가(Ducking, Volume)는 작게
- 라벨 없는 입력 필드를 만들지 않는다 -- 모든 컨트롤에 LABEL_CLASSES 스타일의 라벨을 붙인다

---

### 원칙 5. 일관된 수공예 (Consistent Craft)

**정의**: 디자인 시스템의 토큰과 패턴을 일관되게 적용하여, 사용자가 새로운 기능을 만나도 학습 비용이 없도록 한다.

**현재 적용 사례 -- 잘 하고 있는 것**:
- 공통 UI 토큰: `variants.ts`에서 `OVERLAY_CLASSES`, `CARD_CLASSES`, `LABEL_CLASSES`, `FOCUS_RING`, `DISABLED_CLASSES` 통합 관리
  - 파일: `/frontend/app/components/ui/variants.ts`
- `Button` 컴포넌트: 5가지 variant(primary/secondary/danger/ghost/gradient) + 3가지 size + loading 상태
  - 파일: `/frontend/app/components/ui/Button.tsx`
- `Modal` 컴포넌트: Compound component 패턴 (Modal.Header, Modal.Footer) + 크기/persistent 옵션
  - 파일: `/frontend/app/components/ui/Modal.tsx`
- `Toast` 피드백: success/error 2타입, 자동 소멸
- 색상 체계: zinc 그레이스케일 기반 + 상태별 semantic color (emerald=성공, amber=경고, rose=오류, indigo=강조)

**현재 비일관성 -- 개선이 필요한 것** (아래 "개선점" 섹션 참조):
- `Button` 컴포넌트가 존재하나, 대부분의 버튼이 인라인 Tailwind로 직접 스타일링됨
- 모달이 `Modal` compound component와 인라인 `fixed inset-0` 방식이 혼재
- border-radius 불일치: `rounded-full` / `rounded-2xl` / `rounded-3xl` / `rounded-xl` / `rounded-lg`가 문맥 규칙 없이 혼용

**Do**:
- 신규 버튼은 반드시 `Button` 컴포넌트를 사용한다
- 신규 모달은 반드시 `Modal` compound component를 사용한다
- border-radius 규칙: 카드=`rounded-3xl`, 인풋=`rounded-2xl`, 버튼=`rounded-full`(CTA) 또는 `rounded-lg`(내부), 배지=`rounded-full`
- 색상: primary 액션=zinc-900, secondary=zinc border, danger=rose, info=indigo

**Don't**:
- 동일한 역할의 UI 요소에 다른 스타일을 적용하지 않는다
- 공통 컴포넌트를 무시하고 인라인으로 중복 구현하지 않는다
- 새로운 색상을 임의로 도입하지 않는다 -- 기존 semantic color 체계를 따른다

---

## 기술 아키텍처 ↔ UX 연결

디자인 원칙이 기술 아키텍처에서 어떻게 구현되는지를 명시한다. 아키텍처 결정이 곧 UX 결정이다.

### Layered Architecture → 단계별 API 매핑

Backend의 Router → Service → Repository 계층이 Frontend의 탭 구조와 1:1로 대응한다.

| Frontend 탭 | Backend Service | API 엔드포인트 | UX 의미 |
|-------------|-----------------|---------------|---------|
| Plan | `storyboard.py` | `POST /storyboards/create` | 주제 입력 → AI 기획 |
| Scenes | `image_gen.py`, `prompt/` | `POST /images/generate` | 프롬프트 → 이미지 |
| Render | `video.py` | `POST /video/create` | 에셋 → 영상 |
| Video | (조회) | `GET /storyboards/{id}` | 결과물 확인 |

**설계 원칙**: 각 탭에서 호출하는 API는 해당 서비스 레이어에만 의존한다. 사용자가 탭을 전환할 때 "다른 서비스로 관점을 옮기는 것"이지 "데이터를 잃는 것"이 아니다.

### Zustand Flux → 탭-as-관점 전환

5개 슬라이스(plan, scenes, meta, output, context)가 탭과 독립적으로 상태를 유지한다.

```
Plan 탭에서 topic 입력 → planSlice 업데이트
  ↓ 탭 전환 (scenes)
Scenes 탭에서 planSlice.topic 그대로 참조 가능
  ↓ 탭 전환 (render)
Render 탭에서 scenesSlice.scenes 그대로 참조 가능
```

**핵심**: 탭 전환 시 상태가 리셋되지 않는다. 이것이 "관점 전환 ≠ 맥락 전환"의 기술적 보장이다.

### AI 파이프라인 → 비동기 상태 패턴

AI 작업(스토리보드 생성, 이미지 생성, 검증, 렌더링)은 모두 비동기다. 각 작업의 상태를 7단계로 정의한다.

| 상태 | UI 표현 | 사용자 액션 |
|------|---------|------------|
| `idle` | 기본 버튼 | 시작 가능 |
| `generating` | spinner + 진행 텍스트 | 대기 (취소 가능) |
| `validating` | amber 배지 "검증 중" | 대기 |
| `pass` | emerald 배지 (Match ≥80%) | 다음 단계 진행 |
| `fail` | rose 배지 + 수정 제안 | 수동 수정 또는 자동 재시도 |
| `auto-fixing` | spinner + "수정 적용 중" | 대기 |
| `rendering` | progress bar | 대기 (중단 가능) |

**설계 원칙**: 모든 비동기 상태는 시각적으로 구별되어야 한다 (원칙 2: AI 협업 투명성). `AutoRunStatus` 컴포넌트가 이 패턴의 현재 구현체다.

### Style Profile → 재현 가능한 품질

Style Profile + Tag System의 기술적 목적은 **같은 설정 = 같은 품질**의 재현성 보장이다.

```
Style Profile 선택
  → base_prompt, negative_prompt, SD 파라미터 자동 적용
  → LoRA weight, IP-Adapter 설정 자동 적용
  → 모든 씬에 동일한 화풍/캐릭터 적용
```

**UX 의미**: 사용자가 한 번 설정한 "화풍"을 매 세션마다 재설정할 필요가 없다. 이것은 원칙 1(점진적 공개)의 기술적 구현이다 -- 복잡한 SD 파라미터 조합을 "프로필 하나 선택"으로 추상화한다.

---

## 현재 잘 하고 있는 점

### 1. 선형 워크플로우의 시각적 표현이 탁월하다
`TabBar`의 dot 인디케이터 + dashed/solid connector가 전체 파이프라인의 진행 상황을 직관적으로 전달한다. 탭 배지(씬 수, 영상 수)도 컨텍스트를 놓치지 않게 돕는다.

**근거**: `/frontend/app/components/studio/TabBar.tsx` L67-91

### 2. Autopilot과 Manual의 이중 경로가 잘 설계되어 있다
"Generate" 버튼(단일 단계 실행)과 "Auto Run" 버튼(전체 파이프라인 실행)을 나란히 배치하여, 빠른 실행과 단계별 제어를 하나의 화면에서 선택할 수 있다. AutoRunStatus 컴포넌트로 진행 상태를 실시간으로 피드백한다.

**근거**: `/frontend/app/components/storyboard/StoryboardActionsBar.tsx`, `/frontend/app/components/storyboard/AutoRunStatus.tsx`

### 3. 빈 상태(Empty State) 처리가 일관적이다
씬 없음, 그룹 없음, 스토리보드 없음 등 각 빈 상태에서 적절한 메시지와 다음 액션 CTA를 제공한다.

**근거**:
- `ScenesTab` L163-174: "No scenes yet" + "Go to Plan"
- `StoryboardsSection` L242-276: `EmptyState` 컴포넌트 with 조건 분기
- `StyleProfileModal` L140-145: "등록된 스타일 프로필이 없습니다" + Manage 안내

### 4. Command Palette(Cmd+K)로 파워유저 접근성을 보장한다
프로젝트, 그룹, 스토리보드를 키보드만으로 빠르게 전환할 수 있다. 타입별 아이콘 + 서브라벨 + kbd 힌트까지 갖춘 완성도가 높다.

**근거**: `/frontend/app/components/ui/CommandPalette.tsx`

### 5. 품질 검증 루프가 워크플로우에 내장되어 있다
이미지 생성 후 Match Rate 배지, Validate 탭, Fix Suggestions, Gemini 자동 수정 제안까지 -- "생성 -> 검증 -> 수정" 사이클이 UI 안에 자연스럽게 녹아있다.

**근거**: `/frontend/app/components/storyboard/SceneCard.tsx` L126-130, L217-234

### 6. Context Breadcrumb 구조가 명확하다
Home에서는 `Project / Group`, Studio에서는 `Home > Project > Group > Storyboard Title` 브레드크럼이 현재 컨텍스트를 분명히 한다.

**근거**: `/frontend/app/components/context/ContextBar.tsx`

---

## 개선이 필요한 점

### 1. Button 컴포넌트 채택률이 낮다

**현황**: `Button` 컴포넌트(`/frontend/app/components/ui/Button.tsx`)가 variant, size, loading 상태를 잘 갖추고 있으나, 실제 사용처가 `Modal.Footer`와 `StoryboardsSection` 등 일부에 국한된다. 대부분의 버튼이 인라인 Tailwind로 직접 스타일링되어 있다.

**문제가 되는 코드 예시**:
- `StoryboardActionsBar.tsx` L42: `className="min-w-[120px] rounded-full border border-zinc-300 bg-white px-5 py-2 text-xs font-semibold tracking-[0.2em] text-zinc-700 uppercase shadow-sm ..."`
- `AutoRunStatus.tsx` L63: `className="rounded-full bg-zinc-900 px-4 py-1.5 text-[10px] font-semibold tracking-[0.2em] text-white uppercase ..."`
- `SceneCard.tsx` L195: `className="text-[10px] font-semibold tracking-[0.2em] text-rose-500 uppercase ..."`

**개선 방향**: 인라인 버튼을 단계적으로 `Button` 컴포넌트로 마이그레이션하고, `tracking-[0.2em] uppercase` 스타일의 "label-like" 버튼을 variant로 추가한다 (예: `variant="label"`).

### 2. 모달 구현 방식이 혼재한다

**현황**: 잘 설계된 `Modal` compound component가 존재하나, `StyleProfileModal`과 같은 주요 모달이 `<div className="fixed inset-0 z-[var(--z-modal)]">` 패턴으로 직접 구현되어 있다.

**문제가 되는 코드**:
- `StyleProfileModal.tsx` L114: 인라인 fixed overlay + 수동 z-index
- `ImagePreviewModal.tsx`, `VideoPreviewModal.tsx`: 별도 구현

**개선 방향**: 모든 모달을 `Modal` compound component로 통합한다. 이미지 미리보기 같은 특수 모달도 `Modal`을 래핑하여 확장한다.

### 3. PlanTab의 서브탭 구조가 직관적이지 않다

**현황**: Plan 탭 안에 "설정"과 "스토리" 서브탭이 있다. 설정(Style Profile, Prompt Setup)이 기본 탭인데, 사용자가 "Plan" 탭을 클릭했을 때 기대하는 것은 "스토리보드 생성"이지 "글로벌 설정"이 아니다.

**문제가 되는 코드**: `/frontend/app/components/studio/PlanTab.tsx` L206-238

**개선 방향**:
- "스토리" 서브탭을 기본값으로 변경하거나
- 설정은 별도 탭(또는 헤더 설정 아이콘)으로 분리하여, Plan 탭은 스토리보드 생성에만 집중하게 한다
- 설정이 미완료 시 인라인 배너로 안내한다 (현재 StyleProfileModal의 onboarding 패턴을 확장)

### 4. SceneCard의 prop 수가 과도하다

**현황**: `SceneCard`가 30개 이상의 props를 받는다. 이는 컴포넌트의 단일 책임 원칙 위반이자 유지보수 부담이다.

**문제가 되는 코드**: `/frontend/app/components/storyboard/SceneCard.tsx` L14-70 (type 정의만 57줄)

**개선 방향**:
- Context 또는 Zustand selector를 사용하여 "주입해야 하는 props"와 "컴포넌트가 직접 가져올 수 있는 상태"를 분리한다
- SceneCard를 더 작은 서브 컴포넌트로 분해하되, 이미 진행 중인 분해(SceneFormFields, SceneActionBar, GenerationSettings)를 더 적극적으로 확장한다

### 5. border-radius 규칙이 불명확하다

**현황**: `rounded-full`, `rounded-3xl`, `rounded-2xl`, `rounded-xl`, `rounded-lg`가 문맥 규칙 없이 혼용된다.

**예시**:
- 카드 컨테이너: `rounded-3xl` (SceneCard) vs `rounded-2xl` (OutputTab 메타데이터 카드) vs `rounded-2xl` (StoryboardCard)
- 입력 필드: `rounded-2xl` (StoryboardGeneratorPanel) vs `rounded-xl` (RenderSettingsPanel) vs `rounded-lg` (ContextBar 모달)
- 버튼: `rounded-full` (대부분 CTA) vs `rounded-lg` (SceneCard 내부 탭)

**개선 방향**: variants.ts에 radius 토큰을 명시적으로 정의한다.
```
RADIUS_CARD = "rounded-2xl"     // 모든 카드/패널
RADIUS_INPUT = "rounded-xl"     // 모든 입력 필드
RADIUS_BUTTON = "rounded-lg"    // 내부 버튼
RADIUS_PILL = "rounded-full"    // CTA, 배지, 필터 pill
RADIUS_PANEL = "rounded-3xl"    // 최상위 섹션 컨테이너
```

### 6. 국제화(i18n) 혼재

**현황**: UI 텍스트가 영어("Generate", "Auto Run", "Render")와 한국어("설정", "스토리", "스토리보드를 먼저 생성하세요")가 혼재되어 있다. 일부 도움말은 한국어이고 라벨은 영어다.

**예시**:
- `PlanTab.tsx` L216-217: 서브탭이 한국어 ("설정", "스토리")
- `RenderTab.tsx` L81-83: 한국어 에러 메시지 ("스토리보드를 먼저 생성하세요")
- `StoryboardGeneratorPanel.tsx` L91: 영어 헤더 ("Storyboard Generator")
- `StoryboardActionsBar.tsx`: 영어 버튼 ("Generate", "Auto Run", "Save")

**개선 방향**: 현재 단계에서 다국어를 도입하기보다, 먼저 "UI 기본 언어"를 하나로 통일한다 (대상 사용자가 한국어 사용자라면 한국어 우선, 또는 영어 UI + 한국어 콘텐츠 정책 수립).

---

## 디자인 토큰 현황

현재 프로젝트에서 사용 중인 핵심 디자인 토큰 정리이다.

### 색상 체계

| 역할 | Tailwind 클래스 | 용도 |
|------|-----------------|------|
| Primary | `bg-zinc-900` / `text-white` | CTA 버튼, 활성 탭, 선택된 필름스트립 |
| Secondary | `bg-white` + `border-zinc-200/300` | 보조 버튼, 카드 배경 |
| Success | `bg-emerald-100` / `text-emerald-700` | 완료 상태, OK 배지 |
| Warning | `bg-amber-100` / `text-amber-700` | 경고 배지, 50자 초과 |
| Error | `bg-rose-100` / `text-rose-700` | 에러 배지, 삭제 |
| Accent | `bg-indigo-50` / `text-indigo-600` | 스타일 프로필, 프리셋 |
| Muted | `text-zinc-400/500` | 라벨, 힌트, 비활성 |

### 타이포그래피 패턴

| 요소 | 스타일 |
|------|--------|
| 섹션 제목 | `text-lg font-semibold text-zinc-900` |
| 서브 제목 | `text-sm font-bold text-zinc-700/800` |
| 라벨 (상수) | `text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase` |
| 본문 | `text-sm text-zinc-600` |
| 힌트 | `text-[10px] text-zinc-400` |
| 배지 | `text-[10px] font-semibold tracking-[0.2em] uppercase` + 상태 색상 |
| 카운터 | `text-[10px] font-bold` + 임계값별 색상 변경 |

### 공간/레이아웃

| 요소 | 값 |
|------|-----|
| 최대 너비 | `max-w-5xl` (1024px) |
| 수평 패딩 | `px-6` |
| 섹션 간격 | `space-y-6` |
| 카드 내부 패딩 | `p-5` ~ `p-6` |
| 카드 그림자 | `shadow-xl shadow-slate-200/40` (섹션) / `shadow-sm` (카드 목록) |
| 카드 배경 | `bg-white/70` + `backdrop-blur` (글래스모피즘) |

---

## 향후 적용 방향

### 단기 (현재 코드 개선)
1. `Button` 컴포넌트 마이그레이션: 인라인 버튼을 단계적으로 교체
2. `Modal` compound component 통합: StyleProfileModal 등을 Modal 기반으로 리팩토링
3. border-radius 토큰을 variants.ts에 추가하고 문서화
4. UI 언어 정책 수립 (영어 UI + 한국어 콘텐츠, 또는 전면 한국어)

### 중기 (기능 개선)
1. PlanTab 서브탭 구조 재설계: "스토리" 기본 + 설정은 별도 경로
2. SceneCard props 경량화: Zustand selector 직접 참조 또는 SceneContext 도입
3. `TECH_DEBT.md`에 명시된 Common UI Toolkit 완성 (Badge, ConfirmDialog 등 전면 채택)

### 장기 (새 기능)
1. Character Builder UI: 이 디자인 원칙(점진적 공개, 밀도 있는 정보 표면)을 1차 적용 대상으로
2. Visual Tag Browser: 원칙 4(밀도 있는 정보 표면)의 고밀도 그리드 UI 실험장
3. Scene Builder UI: 원칙 3(선형 파이프라인)을 씬 단위 마이크로 파이프라인으로 확장

---

## 참고 프레임워크

| 출처 | 개념 | 적용 |
|------|------|------|
| Nielsen Norman Group | Progressive Disclosure | 원칙 1의 이론적 근거 |
| Nielsen Norman Group | Recognition over Recall | 원칙 5 -- 일관된 패턴으로 학습 비용 최소화 |
| Nielsen Norman Group | Direct Manipulation | Filmstrip에서 씬 직접 클릭, 인라인 태그 편집 |
| CapCut | Compositional Density | 원칙 4 -- 짧은 캔버스에 밀도 높은 정보 배치 |
| Canva | Brand Kit | Style Profile이 Canva Brand Kit의 역할을 함 (일관된 스타일 자동 적용) |
| Human-in-the-Loop | AI 협업 패턴 | 원칙 2 -- AI는 초안, 사람은 최종 결정 |

---

*최종 작성: 2026-02-03 | 기반 분석: frontend/ 전체 코드베이스*
