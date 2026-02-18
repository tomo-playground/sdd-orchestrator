# Character Builder Wizard

> 상태: 완료 (Phase 7-1 #8, Phase A-C 완료 2026-02-13) | 출처: 7-1 #8 | 최종 갱신: 2026-02-18

## 배경

현재 캐릭터 생성(`/characters/new`)은 8개 섹션이 한 화면에 펼쳐진 플랫 폼.
초보 사용자에게 진입 장벽이 높고, 태그/LoRA 선택이 비직관적.

**현행 Pain Points**:
1. **태그 선택**: 텍스트 검색만 지원, 카테고리 브라우징 없음, 인기 태그 추천 없음
2. **LoRA 선택**: `<select>` 드롭다운, 썸네일/메타데이터 없음
3. **정보 과부하**: 8개 섹션 (Basic/Identity/Tags/LoRA/PromptMode/IP-Adapter/Voice/Reference) 동시 노출
4. **프리뷰 불가**: Save 전까지 Generate 버튼 비활성화 → 결과 확인 불가

## 외부 사례 분석

6개 서비스의 캐릭터 생성 UX를 분석하여 설계에 반영.

| 서비스 | 핵심 패턴 | 채택 여부 |
|--------|----------|----------|
| **NovelAI** | Danbooru 태그 + weight 조정, Preset 저장/재사용 | 태그 체계 동일 → **태그 칩 그리드 + weight** 채택 |
| **Civitai** | 카드 그리드 + 다층 필터 (Type/Base/인기순) | **LoRA 카드 그리드 + 필터** 채택 |
| **VRoid Studio** | 카테고리 탭 → 프리셋 선택 → 슬라이더 미세 조정 | **카테고리별 Collapsible + 인기순 정렬** 채택 |
| **Pixai.art** | Thematic Generator (테마 클릭 → 자동 로드) | **Quick Start 템플릿** 채택 (Phase A) |
| **Character.ai** | 최소 3필드 + 점진적 노출 | **3-step 최소 흐름 + Skip** 채택 |
| **Artbreeder** | 시각적 탐색 (이미지 기반 검색) | 비채택 (SD 태그 기반과 상이) |

**도출 원칙**:
- **Progressive Disclosure**: 핵심 옵션만 먼저 노출, 고급 설정은 Full Editor로 (Character.ai)
- **Preset-First**: 빈 폼이 아닌 추천 조합에서 시작 (Pixai, VRoid)
- **Visual Selection**: 텍스트 검색보다 칩/카드 기반 시각적 선택 (Civitai, VRoid)
- **On-demand Preview**: 실시간 불가(SD 10-30s) → 버튼 클릭 시 생성 + SSE 진행률 (NovelAI)

## 목표

- **Quick Start 템플릿**으로 추천 조합에서 시작, 수정만으로 캐릭터 완성
- **3-step 위저드**로 핵심만 순차 안내 (기본정보 → 외형 → LoRA+프리뷰)
- **비주얼 태그 선택**: 카테고리별 칩 그리드 + 인기순 강조
- **LoRA 카드 브라우저**: 썸네일 + 메타데이터 + 인라인 weight 슬라이더
- **즉시 프리뷰**: Save 없이 임시 프롬프트로 SD 이미지 생성
- **기존 Full Editor 병행**: 위저드는 생성 진입점, 편집은 기존 `/characters/[id]` 유지

## 설계 원칙

- **Preset-First, Customize-Second**: 빈 폼 대신 추천 조합에서 시작 (Pixai)
- **Simple by default, Powerful when needed**: 위저드는 핵심만, 고급 설정은 Full Editor로 (Character.ai)
- **기존 인프라 재사용**: `/tags/search`, `/tags/groups`, `/loras` API 활용
- **기존 편집 페이지 무변경**: `/characters/[id]` Full Editor는 그대로 유지

## 라우팅 전략

**현행**: `/characters/new` → `[id]/page.tsx`가 `id === "new"` 캐치 → 플랫 폼 렌더링.

**변경**: `/characters/new/page.tsx` 신규 생성 → Next.js 정적 경로 우선순위에 의해 `[id]` 대신 위저드 렌더링.

| 경로 | 핸들러 | 역할 |
|------|--------|------|
| `/characters/new` | `new/page.tsx` (신규) | 위저드 UI |
| `/characters/new?mode=full` | `new/page.tsx` | "Skip" → Full Editor 폼 표시 |
| `/characters/{id}` | `[id]/page.tsx` (기존) | 편집 전용 (변경 없음) |

**`[id]/page.tsx` 변경점**: `isNew = rawId === "new"` 분기 제거. 순수 편집 전용으로 단순화.

## 진입점

| 위치 | 동작 |
|------|------|
| Library Characters 탭 `+ New Character` | `/characters/new` → 위저드 표시 |
| Home 칸반 "New Shorts" → Script 탭 → 캐릭터 미선택 시 | Library로 유도 |
| 위저드 상단 "Skip → Full Editor" 링크 | `?mode=full` 쿼리 파라미터로 전환 |

## 위저드 단계

### Step 1: Quick Start + Basic Info

**Quick Start 템플릿 카드** (Pixai Thematic Generator 참고):

상단에 3-4개 추천 템플릿 카드를 가로 나열. 클릭 시 이름 외 모든 필드(gender, tags, lora) 자동 채움.

| 템플릿 | Gender | 자동 채움 태그 | LoRA |
|--------|--------|---------------|------|
| Anime Girl | female | `1girl`, `long_hair`, `brown_hair`, `blue_eyes`, `school_uniform` | 기본 character LoRA |
| Anime Boy | male | `1boy`, `short_hair`, `black_hair`, `brown_eyes` | 기본 character LoRA |
| Fantasy | female | `1girl`, `elf_ears`, `long_hair`, `white_hair`, `dress` | - |
| Blank | - | 없음 | 없음 |

- 템플릿 데이터: Frontend 상수 (3-4개 고정, DB 불필요)
- 템플릿 선택 = Step 2/3 초기값 자동 세팅 → 사용자는 수정만
- "Blank" = 기존 빈 폼 시작 (기본 동작)

**Gender 선택 시 자동 주입** (Character.ai "기본값으로 시작" 패턴):
- Female → `1girl` + identity tag `a_cute_girl` 자동 추가
- Male → `1boy` + identity tag `a_cute_boy` 자동 추가
- 기존 캐릭터 시스템의 identity tag 체계와 연동

**입력 필드**:

| 필드 | UI | 필수 | 기본값 |
|------|-----|------|--------|
| Name | 텍스트 입력 (debounced 중복 체크) | Y | - |
| Gender | 2-버튼 토글 (Female / Male) | Y | Female |
| Description | textarea (2줄, 선택) | N | - |

### Step 2: Appearance (외형 태그)

**카테고리별 칩 그리드** (VRoid 카테고리 탭 패턴):

| 카테고리 | group_name | 선택 방식 | 예시 |
|----------|------------|-----------|------|
| Hair Color | `hair_color` | 단일 선택 | `brown_hair`, `blonde_hair` |
| Hair Style | `hair_style` | 단일 선택 | `ponytail`, `twintails` |
| Hair Length | `hair_length` | 단일 선택 | `long_hair`, `short_hair` |
| Eye Color | `eye_color` | 단일 선택 | `blue_eyes`, `red_eyes` |
| Body/Feature | `body_feature` | 다중 선택 | `cat_ears`, `elf_ears` |
| Clothing | `clothing` | 다중 선택 (최대 5) | `school_uniform`, `dress` |

**인기순 강조** (Civitai 인기순 정렬 패턴):
- 각 카테고리 내에서 `wd14_count` 상위 5개 태그를 "Popular" 행으로 먼저 표시
- Popular 행 아래 구분선, 나머지 태그는 알파벳순
- 인기 태그에 `wd14_count` 기반 미니 바 또는 뱃지 ("12K")

**데이터 소스**:
- 초기 로드: `GET /tags/groups` → `{category, group_name, count}[]`
- 각 group: `GET /tags?group_name=hair_color` → priority, name 정렬
- 검색: `GET /tags/search?q=brown&limit=20` → starts_with 우선 정렬

**참고 — 태그 분류 체계**:
- `category`: 대분류 (`appearance`, `expression` 등) — 위저드에서 직접 사용하지 않음
- `group_name`: 세분류 (`hair_color`, `eye_color` 등) — **칩 그리드의 기준**
- `is_permanent`: Identity(true) vs Clothing(false) — Save 시 `CharacterTagLink`에 설정

**UX**:
- 각 카테고리는 Collapsible 섹션 (첫 3개 기본 열림)
- 칩 클릭 = 선택/해제 토글
- Hair Color 칩에 색상 dot 표시 (CSS `bg-amber-600` 등)
- Eye Color 칩에 색상 dot 표시
- 카테고리 우측에 선택 개수 뱃지 ("2/20")
- 하단 검색 입력: `GET /tags/search` 활용 (기존 `CharacterTagsEditor` 패턴 재사용)
- 템플릿에서 자동 채워진 태그는 pre-selected 상태로 표시 → 사용자가 변경 가능

### Step 3: LoRA & Preview

**LoRA 카드 그리드** (Civitai 카드 + Pixai 인라인 슬라이더):

```
┌──────────────────┐  ┌──────────────────┐
│ [썸네일 이미지]    │  │ [썸네일 이미지]    │
│                  │  │                  │
├──────────────────┤  ├──────────────────┤
│ Display Name     │  │ Display Name     │
│ [character] 뱃지  │  │ [style] 뱃지     │
│ trigger: flat... │  │ trigger: anime.. │
│ ──── 0.7 ─────── │  │ ──── 0.8 ─────── │
│ [+ Add]  [Added] │  │ [+ Add]          │
└──────────────────┘  └──────────────────┘
```

**카드 필드**:

| 필드 | 출처 | 비고 |
|------|------|------|
| 썸네일 | `lora.preview_image_url` | 없으면 이니셜 플레이스홀더 |
| Display Name | `lora.display_name` | 제목 |
| Type 뱃지 | `lora.lora_type` | `character` (보라), `style` (파랑) |
| Trigger Words | `lora.trigger_words` | 말줄임 1줄 |
| Weight 슬라이더 | `lora.default_weight` | 선택 시 활성화 (0.1-1.0, step 0.05) |

**필터** (Civitai 다층 필터 패턴):
- Type: All / Character / Style (pill 토글)
- Gender: Step 1 Gender 연동 → `gender_locked` 불일치 LoRA 숨김
- 검색: display_name 텍스트 필터

**프리뷰 생성** (NovelAI on-demand 패턴):
- "Generate Preview" 버튼 → `POST /characters/preview` (신규 API)
- 선택된 태그 + LoRA로 V3 12-Layer 프롬프트 조합 → SD 이미지 생성
- SSE 진행률 바 (기존 `generate-async` 패턴): 프롬프트 조합(10%) → 이미지 생성(50-90%) → 완료(100%)
- 결과 이미지 → 좌측 Sticky Preview에 표시
- Save 전까지 임시 이미지 (MediaAsset 미생성)
- 재생성 가능: seed 변경 또는 태그/LoRA 수정 후 다시 클릭

### 완료 → Save

**2-step Save 흐름** (현행 API 제약: `CharacterCreate`에 `preview_image_asset_id` 없음):

```
1. POST /characters (name, gender, tags, loras)  →  character_id 반환
2. POST /characters/{id}/assign-preview           →  위저드 프리뷰 이미지 연결
   (프리뷰 미생성 시: regenerate-reference 또는 스킵)
```

**UX 흐름**:
- "Create Character" 클릭 → `POST /characters` → character_id 취득
- 프리뷰 이미 생성: `POST /characters/{id}/assign-preview` (base64 전달) → 자동 연결
- 프리뷰 미생성: "프리뷰 이미지를 생성할까요?" 확인 → `regenerate-reference` 호출 또는 스킵
- 성공 → `/characters/{id}` Full Editor로 리다이렉트 + 토스트 "캐릭터 생성 완료"

## 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│  Character Builder                 [Skip → Full Editor] │
├────────────┬────────────────────────────────────────────┤
│            │  ① Basic · ② Appearance · ③ LoRA+Preview  │
│  Preview   │────────────────────────────────────────────│
│  (sticky)  │                                            │
│            │  Quick Start Templates (Step 1)             │
│  280px     │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐         │
│            │  │Girl │ │ Boy │ │Fant.│ │Blank│         │
│ ┌────────┐ │  └─────┘ └─────┘ └─────┘ └─────┘         │
│ │  이미지  │ │                                            │
│ │ 200x280 │ │  Name: [____________]                      │
│ │         │ │  Gender: [Female] [Male]                   │
│ └────────┘ │  Description: [__________]                  │
│            │                                            │
│ Tags:      │────────────────────────────────────────────│
│ brown_hair │  [← Back]                   [Next Step →]  │
│ blue_eyes  │                                            │
│ school_... │                                            │
│            │                                            │
│ LoRA:      │                                            │
│ eureka 0.7 │                                            │
├────────────┴────────────────────────────────────────────┤
│  Step 1 of 3                          [Generate Preview] │
└─────────────────────────────────────────────────────────┘
```

**좌측 Preview 패널** (Sticky, 280px):
- 프리뷰 이미지 (생성 전: Gender 기반 실루엣 플레이스홀더)
- 선택된 태그 요약 (Identity / Clothing 구분 칩)
- 선택된 LoRA 목록 (이름 + weight)
- "Generate Preview" 버튼 (Step 3에서 활성화, 다른 Step에서도 접근 가능)

## 신규 API (Backend 2건)

### 1. `POST /characters/preview` — 임시 프리뷰 생성

DB 저장 없이 프롬프트 조합 + SD 이미지 생성만 수행.

```python
# Request
class CharacterPreviewRequest(BaseModel):
    gender: str                          # "female" | "male"
    tag_ids: list[int]                   # 선택된 태그 ID 목록
    loras: list[CharacterLoRA] | None    # LoRA 설정
    custom_base_prompt: str | None       # 추가 프롬프트 (선택)

# Response
class CharacterPreviewResponse(BaseModel):
    image: str              # Base64 이미지
    used_prompt: str        # 실제 사용된 프롬프트
    seed: int
```

**구현**: `preview.py`의 `regenerate_reference`에서 프롬프트 조합 + SD 호출 로직을 추출.
`character_id` 없이 `tag_ids` → Tag 조회 → V3 12-Layer 조합 → SD 호출 → base64 반환.

### 2. `POST /characters/{id}/assign-preview` — 프리뷰 이미지 연결

위저드에서 생성한 임시 이미지를 저장된 캐릭터에 연결.

```python
# Request
class AssignPreviewRequest(BaseModel):
    image_base64: str       # Base64 인코딩된 이미지

# Response
class AssignPreviewResponse(BaseModel):
    preview_image_url: str  # 저장된 이미지 URL
    asset_id: int           # media_assets.id
```

**구현**: 기존 `_save_preview_asset(db, character_id, image_bytes)` 재사용.

## 위저드 상태 관리

**Local React State** (Zustand 불필요 — 위저드는 단일 페이지 단발성 흐름):

```typescript
interface WizardState {
  step: 1 | 2 | 3;
  // Step 1
  name: string;
  gender: "female" | "male";
  description: string;
  templateId: string | null;        // 선택된 Quick Start 템플릿
  // Step 2
  selectedTags: { tagId: number; isPermanent: boolean }[];
  // Step 3
  selectedLoras: { loraId: number; weight: number }[];
  // Preview
  previewImage: string | null;      // base64
  previewSeed: number | null;
  isGenerating: boolean;
}
```

**이탈 방어**: `beforeunload` 가드 (step > 1이거나 입력값 존재 시 경고)

## 컴포넌트 구조

```
frontend/app/(app)/characters/
├── [id]/page.tsx                  # 기존 Full Editor (isNew 분기 제거)
├── new/
│   └── page.tsx                   # 진입점: mode=full → 기존 폼, 기본 → 위저드
└── builder/
    ├── CharacterWizard.tsx        # 위저드 컨테이너 (3-step 상태 관리)
    ├── WizardPreviewPanel.tsx     # 좌측 프리뷰 패널
    ├── wizardTemplates.ts         # Quick Start 템플릿 상수 정의
    ├── steps/
    │   ├── BasicInfoStep.tsx      # Step 1 (Quick Start + Name/Gender)
    │   ├── AppearanceStep.tsx     # Step 2 (태그 카테고리 그리드)
    │   └── LoraPreviewStep.tsx    # Step 3 (LoRA 카드 + 프리뷰)
    └── components/
        ├── TemplateCard.tsx       # Quick Start 템플릿 카드
        ├── TagCategoryGrid.tsx    # 카테고리별 칩 그리드 (인기순 강조)
        ├── LoraCard.tsx           # LoRA 선택 카드 (인라인 슬라이더)
        └── WizardNavBar.tsx       # 하단 네비게이션 (Back/Next/Create)
```

**예상 파일 크기**: 각 컴포넌트 100-200줄 (CLAUDE.md 가이드라인 준수)

**기존 코드 변경점**:

| 파일 | 변경 |
|------|------|
| `[id]/page.tsx` | `isNew = rawId === "new"` 분기 제거, 순수 편집 전용으로 단순화 |
| `CharactersContent` | `+ New Character` 링크 유지 (`/characters/new`) |
| `useCharacterForm.ts` | 변경 없음 (Full Editor에서만 사용) |
| `backend/routers/characters.py` | `preview`, `assign-preview` 2개 엔드포인트 추가 |
| `backend/services/characters/preview.py` | 프롬프트 조합 로직 추출 (공통 함수화) |

## 수락 기준 (DoD)

| # | 기준 | 출처 |
|---|------|------|
| 1 | `/characters/new` → 3-step 위저드 표시, "Skip → Full Editor" 전환 가능 | Character.ai |
| 2 | Quick Start 템플릿 카드 클릭 → gender/tags/lora 자동 채움, 수정 가능 | Pixai |
| 3 | Step 1: Name 중복 체크 + Gender 선택 시 identity tag 자동 주입 | Character.ai |
| 4 | Step 2: group_name 기반 카테고리 칩 그리드 + 인기순(wd14_count) 상위 5개 강조 | Civitai, VRoid |
| 5 | Step 3: LoRA 카드 그리드 (썸네일 + 메타 + 인라인 weight), gender_locked 필터 | Civitai |
| 6 | Step 3: "Generate Preview" → 임시 프롬프트로 SD 이미지 생성 + SSE 진행률 | NovelAI |
| 7 | "Create Character" → `POST /characters` + assign-preview → Full Editor 리다이렉트 | - |
| 8 | 기존 Full Editor (`/characters/[id]`) 동작에 영향 없음 | - |
| 9 | 빌드 PASS + ESLint PASS | - |

## Phase 계획

| Phase | 작업 | 핵심 | 난이도 |
|-------|------|------|--------|
| A | **위저드 골격 + Quick Start + Step 1-2 + Save** | 라우팅 전환, 템플릿 카드, Gender→identity tag 자동 주입, 카테고리 칩 그리드(인기순 강조), 프리뷰 없이 Save→Full Editor | 반나절 |
| B | **Step 3 LoRA 카드 + 필터링** | 카드 그리드 (썸네일+뱃지+trigger+인라인 weight), Type/Gender 필터, 검색 | 2시간 |
| C | **Preview API + SSE 프리뷰** | `POST /characters/preview` (Backend), `POST /characters/{id}/assign-preview` (Backend), SSE 진행률, Preview 패널 연동 | 반나절 |

## 스코프 외 (향후)

| 항목 | 연계 | 참고 사례 |
|------|------|----------|
| AI 캐릭터 생성 (텍스트 설명 → 자동 태그 추출) | Phase 9 Agentic Pipeline | NovelAI Vibe Transfer |
| 템플릿 DB 관리 (사용자 정의 템플릿 CRUD) | Feature Backlog | Pixai Thematic Generator 확장 |
| 태그별 예시 이미지 썸네일 | Feature Backlog (Visual Tag Browser) | Civitai 카드 썸네일 |
| 참조 이미지 업로드 → 태그 자동 추출 | Phase 9 | NovelAI Vibe Transfer, IP-Adapter |
| Voice Preset 위저드 연동 | Full Editor에서만 설정 | - |
