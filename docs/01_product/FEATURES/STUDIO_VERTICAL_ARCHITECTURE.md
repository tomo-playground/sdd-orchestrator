# Studio Coordinator + Vertical Architecture

> 상태: 완료 (Phase 7-4, ARCHIVED 2026-02-11)

## 배경

현재 `/storyboards`, `/studio`, `/lab?tab=creative` 3개 페이지의 경계가 애매하다.

- `/storyboards`: 스토리보드 목록 갤러리 → 클릭 시 Studio로 이동 (중간 단계)
- `/studio` PlanTab: 주제/구조/캐릭터 입력 → Gemini 대본 생성
- `/lab?tab=creative`: 주제/구조/캐릭터 입력 → 9-Agent 자동 대본 생성 → "Send to Studio"

"새 쇼츠를 만들려면 어디로 가야 하지?" 라는 사용자 혼란이 존재.
Studio가 대본 기획부터 이미지 생성, 렌더링, 출력까지 모두 담당하는 과부하 상태.
`useStudioStore`가 51개 TRANSIENT_KEYS + 5개 slice(474줄)를 관리하는 God Store.

## 목표

- **Studio = 코디네이터** (지휘자): 재료 확인 → 이미지 생성 → 렌더 → 출력
- **버티컬 = 전문가**: 각 도메인(대본, 캐릭터, 음성, 음악, 배경)에서 깊은 작업
- 모든 버티컬은 AI 에이전트 방식으로 진화 (대본이 첫 시험대상)

## 선행 조건

- Phase 7-3 #1, #2 완료 (Voices/Music 독립 페이지 패턴 확립) ✅
- Characters 독립 페이지 완료 (7-1 #25) ✅
- Creative Lab V2 MVP 완료 (9-Agent 파이프라인) ✅

---

## 1. 전체 구조

```
┌──────────────────────────────────────────────────┐
│  Studio 코디네이터 (/studio)                       │
│  Materials Check → Scenes(이미지) → Render → Output │
└────────────┬─────────────────────────────────────┘
             │ 각 버티컬의 결과물을 ID로 참조
   ┌─────────┼──────┬──────────┬──────────┐
   ▼         ▼      ▼          ▼          ▼
 Script   Characters Voices   Music    Backgrounds
 /scripts /characters /voices  /music   /backgrounds
 (신규)   (완료)      (완료)   (완료)   (완료)
```

### 역할 분담

| 역할 | Studio 코디네이터 | 버티컬 페이지 |
|------|------------------|-------------|
| 깊이 | 얕고 넓음 (전체 상태 파악) | 깊고 좁음 (도메인 전문) |
| 행동 | 조합, 순서 제어, 렌더 | 생성, 편집, 고도화 |
| 비유 | 영화 감독 | 각 파트 전문가 |
| 데이터 | ID 참조로 재료 연결 | 자기 도메인 데이터 소유 |

---

## 2. Script 버티컬 (`/scripts`)

### 2-1. 흡수 대상

| 기존 위치 | 기능 | Script 버티컬로 이동 |
|-----------|------|-------------------|
| `/storyboards` | 스토리보드 목록/검색/삭제 | ✅ 좌측 패널 목록 |
| Studio PlanTab | Topic, Structure, Language, Duration, Characters | ✅ 공통 입력 |
| Studio PlanTab | Base Prompt, ControlNet, IP-Adapter, Prompt Mode | ❌ Studio Scenes에 잔류 (이미지 관심사) |
| Lab Creative 탭 | 9-Agent Pipeline (Debate + Pipeline + QC) | ✅ AI Agent 모드 |

### 2-2. 두 가지 모드

```
┌─────────────────────────────────────────────────────────────┐
│ Script: "검사의 하루"                                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ── 공통 입력 ──────────────────────────────────────────    │
│  Topic / Structure / Language / Duration / Characters        │
│                                                              │
│  ── Mode ────────────────────────────────────────────────   │
│  ┌── Manual ──────────┐  ┌── AI Agent ────────────────────┐ │
│  │ Gemini 1회 호출     │  │ Director Mode, Rounds, Refs    │ │
│  │ [Generate ▶]       │  │ Concept Debate → Pipeline → QC │ │
│  └────────────────────┘  │ [Start Agent ▶]                │ │
│                          └────────────────────────────────┘ │
│                                                              │
│  ── 결과: 씬 목록 (텍스트 편집 + 읽기전용 이미지 썸네일) ── │
│                                              [→ Studio]      │
└──────────────────────────────────────────────────────────────┘
```

**Manual 모드**: 기존 PlanTab의 Gemini 1회 호출 → 빠른 대본 생성
**AI Agent 모드**: 기존 Creative Lab → Concept Debate → 5-Step Pipeline + QC Review

### 2-3. 라우팅

| URL | 기능 |
|-----|------|
| `/scripts` | 스토리보드 목록 (기존 `/storyboards` 대체) |
| `/scripts?new=true` | 새 대본 생성 |
| `/scripts?id=123` | 기존 대본 편집 |
| `/scripts?id=123&mode=agent` | AI Agent 모드로 진입 |

### 2-4. 수락 기준 (Script 버티컬)

| # | 기준 |
|---|------|
| 1 | `/scripts` 접근 시 전체 스토리보드 목록 표시 (검색/필터 동작) |
| 2 | Manual 모드: 공통 입력 → Gemini 생성 → 씬 목록 표시 |
| 3 | AI Agent 모드: Concept Debate → Pipeline → QC Review 전체 플로우 동작 |
| 4 | 씬 텍스트(script) 인라인 편집 가능 |
| 5 | 이미지 썸네일은 읽기전용 표시 (편집은 Studio에서) |
| 6 | `[→ Studio]` 클릭 시 `/studio?storyboard=ID`로 이동 |
| 7 | 기존 `/storyboards` URL이 `/scripts`로 리다이렉트 |

---

## 3. Studio 코디네이터 리팩토링

### 3-1. 기존 4탭 → 단일 스크롤 페이지

| 기존 | 변경 후 |
|------|---------|
| PlanTab | 제거 → Script 버티컬로 이동 |
| ScenesTab | Studio에 잔류 (이미지 생성/편집) |
| RenderTab | Studio에 잔류 |
| OutputTab | Studio에 잔류 |

### 3-2. Studio 미선택 상태 (칸반 뷰)

```
┌──────────────────────────────────────────────────────────┐
│ Studio                                    [+ New Shorts] │
├──────────────┬──────────────┬──────────────┬─────────────┤
│ 📝 Draft      │ 🎬 In Prod    │ ✅ Rendered   │ 📤 Published │
│ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │             │
│ │검사의하루 │ │ │마법소녀   │ │ │고양이카페 │ │             │
│ │ 8 scenes │ │ │ 5/8 img  │ │ │ done     │ │             │
│ └──────────┘ │ └──────────┘ │ └──────────┘ │             │
└──────────────┴──────────────┴──────────────┴─────────────┘
```

- 기존 `/storyboards` 갤러리 역할을 겸함
- `[+ New Shorts]` → `/scripts?new=true`로 이동
- 카드 클릭 → 타임라인 뷰로 전환

### 3-3. Studio 선택 상태 (타임라인 뷰)

```
┌─────────────────────────────────────────────────────────────┐
│ Studio: "검사의 하루"                    [Autopilot ▶] [Save]│
├─────────────────────────────────────────────────────────────┤
│  Pipeline: Script(✅) ─ Images(●3/8) ─ Render(○) ─ Video(○) │
│  ████████████░░░░░░░░░░░░  38%                               │
├─────────────────────────────────────────────────────────────┤
│  ── Materials Check ────────────────────────────────────    │
│  📝Script ✅  👤Chars ✅  🎤Voice ✅  🎵Music ⚠  🖼BG ✅     │
│  [Open→]     [Open→]     [Open→]    [Open→]    [Open→]     │
├─────────────────────────────────────────────────────────────┤
│  ── Image Settings ─────────────────────────────────────    │
│  Base Prompt / Neg Prompt / ControlNet / IP-Adapter         │
│  (기존 PlanTab의 이미지 관련 설정이 여기로 이동)             │
├─────────────────────────────────────────────────────────────┤
│  ── Scenes ─────────────────────────────────────────────    │
│  (기존 ScenesTab: 씬별 이미지 생성/편집/검증)               │
├─────────────────────────────────────────────────────────────┤
│  ── Render ─────────────────────────────────────────────    │
│  (기존 RenderTab: 레이아웃, 전환, Ken Burns, 속도)           │
├─────────────────────────────────────────────────────────────┤
│  ── Output ─────────────────────────────────────────────    │
│  (기존 OutputTab: 비디오 프리뷰, 다운로드)                   │
└─────────────────────────────────────────────────────────────┘
```

### 3-4. 수락 기준 (Studio 코디네이터)

| # | 기준 |
|---|------|
| 1 | 미선택 시 칸반 뷰 표시 (Draft/InProd/Rendered/Published) |
| 2 | 카드 클릭 시 타임라인 뷰로 전환 |
| 3 | Materials Check에서 각 버티컬 준비 상태 표시 |
| 4 | `[Open →]` 클릭 시 해당 버티컬로 딥링크 (`?storyboard=ID` 전달) |
| 5 | PlanTab 완전 제거, storyboard 미선택 시 `/scripts`로 리다이렉트 |
| 6 | Scenes/Render/Output 기존 기능 100% 유지 |
| 7 | Autopilot이 Scenes → Render → Output 범위에서 동작 |

---

## 4. 네비게이션 변경

### 기존

```
[Home] [Stories] [Characters] [Voices] [Music] [Backgrounds] | [Studio] | [Lab] [Manage]
```

### 변경 후

```
[Studio] | [Script] [Characters] [Voices] [Music] [Backgrounds] | [Lab] [Manage]
```

| 변경 | 설명 |
|------|------|
| Home 제거 | Studio 칸반 뷰가 대체 |
| Stories → Script | 리네이밍 + 기능 확장 |
| Studio 최좌측 | 코디네이터가 앱의 중심 |
| Lab creative 탭 제거 | Script 버티컬로 이동 (Lab = tag-lab + scene-lab + analytics만 유지) |

---

## 5. 컨텍스트 유지 (버티컬 간 맥락 단절 방지)

### 5-1. 영속적 컨텍스트 바

```
┌──────────────────────────────────────────────────────────────┐
│ [Studio] [Script] [Characters] ...                    Manage │ ← 네비
├──────────────────────────────────────────────────────────────┤
│ 📁 MyProject > Episode1 > "검사의 하루"                 [✕]  │ ← 컨텍스트 바
├──────────────────────────────────────────────────────────────┤
│ (현재 페이지 콘텐츠)                                          │
└──────────────────────────────────────────────────────────────┘
```

- 모든 페이지에서 현재 작업 중인 스토리보드 정보 표시
- 클릭 시 Studio 타임라인으로 복귀
- `[✕]` 클릭 시 맥락 해제 → 독립 모드

### 5-2. URL 기반 맥락 전달

각 버티컬에서 `?storyboard=ID` 쿼리 파라미터로 맥락 유지.

| URL | 의미 |
|-----|------|
| `/scripts?storyboard=123` | 스토리보드 123의 대본 편집 |
| `/characters?storyboard=123` | 스토리보드 123에 사용된 캐릭터 하이라이트 |
| `/voices?storyboard=123` | 스토리보드 123의 보이스 설정 |
| `/characters` | 맥락 없는 독립 캐릭터 관리 |

---

## 6. Zustand Store 분할

### 기존: God Store

```
useStudioStore (모든 것 포함)
  ├── planSlice      (~30 필드)
  ├── scenesSlice    (~15 필드)
  ├── outputSlice    (~30 필드)
  ├── metaSlice      (~15 필드)
  └── contextSlice   (~15 필드)
```

### 변경 후: 4개 스토어

| 스토어 | 범위 | 출처 |
|--------|------|------|
| `useContextStore` | 프로젝트/그룹, 스타일 프로필 (앱 전역) | contextSlice |
| `useUIStore` | Toast, 모달, 프리뷰 (앱 전역) | metaSlice 일부 |
| `useStoryboardStore` | 씬, 이미지, 스토리보드 메타 (Studio 전용) | planSlice + scenesSlice |
| `useRenderStore` | 렌더 설정, 출력 (Studio 전용) | outputSlice |

### 호환 레이어

전환 기간 동안 기존 `useStudioStore` 인터페이스를 유지하는 adapter 제공.
기존 `useStudioStore((s) => s.projectId)` 호출이 깨지지 않도록 위임.

---

## 7. Backend 변경

### 7-1. 라우터 이동

| 기존 | 변경 후 | 설명 |
|------|---------|------|
| `POST /storyboards/create` | `POST /scripts/generate` | Gemini 대본 생성 |
| `/lab/creative/sessions/*` | `/scripts/sessions/*` | Creative 세션 전체 |
| `/scene/generate` | `/images/generate` | 이미지 생성 (향후) |

기존 URL은 deprecated redirect로 전이 기간 유지.

### 7-2. 서비스 분해

`services/storyboard.py` (1,182줄 God Service) 분해:

| 신규 모듈 | 출처 | 내용 |
|-----------|------|------|
| `services/script/gemini_generator.py` | create_storyboard() | Gemini 대본 생성 (~300줄) |
| `services/script/tag_pipeline.py` | normalize/validate | 태그 파이프라인 (~100줄) |
| `services/storyboard/crud.py` | save/update/delete | 순수 CRUD (~400줄) |
| `services/storyboard/scene_builder.py` | create_scenes | 씬 빌드 (~250줄) |

### 7-3. AI 에이전트 공통 프로토콜

모든 버티컬 에이전트가 따르는 공통 상태 머신:

```
created → running → review → completed → exported
                  ↘ failed → running (retry)
```

`BaseAgentSession` (상태 전이 + BackgroundTasks + SSE) + `BaseQCAgent` 추출.
현재 Creative 세션이 이 패턴을 이미 구현 중이므로 추상화 추출.

---

## 8. 데이터 모델

### 테이블 분리 안 함

Storyboard/Scene 테이블 구조 유지. 이유:
- Scene은 원자 단위 (script + image_prompt + character_actions 포함)
- 분리 시 JOIN 폭발
- Storyboard = 코디네이션의 데이터 표현

### 버티컬 간 참조 원칙: Reference by ID

```
Script 버티컬 → storyboard_id
Characters   → character_id (scene_character_actions)
Voices       → voice_preset_id (render_preset)
Music        → music_preset_id (render_preset)
Backgrounds  → environment_reference_id (scene)
```

Store에는 ID만 저장, 실제 데이터는 필요 시 API에서 resolve.

---

## 마이그레이션 전략: 점진적 (Strangler Fig)

중복 허용 기간을 두고 안전하게 전환. 각 Phase 완료 시 앱이 동작하는 상태 유지.

### Phase 간 의존성

```
Phase A (기반) ──블로커──→ Phase B (Script) ──→ Phase D (정리)
     │                                              ↑
     └──→ Phase C (Studio 코디네이터) ──────────────┘
```

- **A 완료 없이 B/C 착수 금지** (이중 리팩토링 방지)
- B와 C는 병렬 가능하나, C-3(PlanTab 제거)은 B 완료 후 수행
- D는 B+C 모두 완료 후 정리

### Phase A: 기반 준비

| # | 작업 | 분류 |
|---|------|------|
| A-1 | `useUIStore` 추출 (toast, modal → 앱 전역) | 리팩토링 |
| A-2 | `useContextStore` 추출 (contextSlice → 앱 전역) | 리팩토링 |
| A-3 | 영속적 컨텍스트 바 구현 (AppShell 레벨) | UX |
| A-4 | 호환 레이어: 기존 `useStudioStore` 구독 코드가 깨지지 않도록 adapter 유지 | 리팩토링 |

### Phase B: Script 버티컬 구축

| # | 작업 | 분류 |
|---|------|------|
| B-1 | `/scripts` 페이지 생성 (목록 + 검색 + 필터) | UX |
| B-2 | `/scripts` Manual 모드 (PlanTab 대본 관심사 이동) | 기능 |
| B-3 | `/scripts` AI Agent 모드 (Creative Lab 흡수) | 기능 |
| B-4 | Backend `services/storyboard.py` 분해 (6단계: CRUD→Helper→Serializer→SceneBuilder→Speaker→Gemini) | 리팩토링 |
| B-5 | Backend `/scripts/generate` 라우터 추가 (기존 `/storyboards/create` deprecated redirect) | API |
| B-6 | Backend Materials Check API (`GET /storyboards/{id}/materials`) | API |

### Phase C: Studio 코디네이터 전환

| # | 작업 | 분류 |
|---|------|------|
| C-1 | Studio 칸반 뷰 (미선택 상태, 상태는 기존 스키마에서 런타임 파생) | UX |
| C-2 | Studio 타임라인 뷰 + Materials Check + Pipeline Progress | UX |
| C-3 | Studio PlanTab 제거, Image Settings를 Scenes 영역으로 이동 (B 완료 후) | 리팩토링 |
| C-4 | `useStoryboardStore` + `useRenderStore` 분리 | 리팩토링 |
| C-5 | Autopilot 범위 조정 (Scenes → Render → Output) | 기능 |

### Phase D: 정리

| # | 작업 | 분류 |
|---|------|------|
| D-1 | 네비게이션 최종 정리 (Home 제거, Script 추가) | UX |
| D-2 | Lab creative 탭 제거 + `/scripts/sessions/*` 라우터 통합 (Creative 세션 이관) | 정리 |
| D-3 | `/storyboards` → `/scripts` 리다이렉트 | 정리 |
| D-4 | deprecated API/호환 레이어 제거 | 정리 |
| D-5 | localStorage 마이그레이션 (기존 키 → 신규 키) | 정리 |

---

## 칸반 상태 파생 (DBA 검증 완료: 신규 컬럼 불필요)

기존 스키마에서 런타임 계산으로 해결:

```
Draft:      scenes에 image_asset_id가 NULL인 씬만 존재
In Prod:    일부 씬 image_asset_id 존재 (부분 완료)
Rendered:   render_history 레코드 존재
Published:  render_history.youtube_video_id IS NOT NULL
```

## 리스크

| 리스크 | 영향 | 완화 |
|--------|------|------|
| Autopilot 파이프라인 단절 | 대본 생성이 외부 버티컬로 이동 → 기존 Plan→Scenes 자동전환 불가 | 1) `/scripts` 완료 후 `[→ Studio]` → `/studio?storyboard=ID&autorun=scenes` (자동 시작) 2) Studio Materials Check에서 Script 미완료 시 `/scripts` 딥링크 3) 호환 기간: PlanTab에 "Deprecated" 배너 표시 |
| God Store 분할 시 상태 동기화 버그 | 수십 곳에서 `useStudioStore` 구독 중 | 호환 레이어(adapter) 유지하며 점진 전환. Phase A 완료 전 B/C 착수 금지 |
| localStorage 마이그레이션 | 기존 사용자의 draft 데이터 유실 가능 | `migrateDraft` 유사 마이그레이션 로직 추가 |
| Backend God Service 분해 | `create_storyboard()` 의존성 체인 복잡 | 6단계 순서: CRUD → Helper → Serializer → SceneBuilder → Speaker → Gemini |
| Creative 세션 통합 복잡도 | Creative 세션은 storyboard와 M:N 관계 | Phase B에서는 `/scripts/generate`만 이동, Creative 세션은 Phase D-2에서 통합 |

---

## 관련 문서

- 기존 패턴: [CHARACTER_PAGE.md](CHARACTER_PAGE.md) (독립 페이지 분리 레퍼런스)
- 로드맵: Phase 7-4 (ROADMAP.md)
- DB 스키마: `docs/03_engineering/architecture/DB_SCHEMA.md`
- API 명세: `docs/03_engineering/api/REST_API.md` (Phase B-5에서 업데이트 필요)
- PRD: `docs/01_product/PRD.md` (§3 핵심 기능 현행화 필요)

## 구현 시 추가 업데이트 필요 문서

| 시점 | 문서 | 내용 |
|------|------|------|
| Phase B-5 | REST_API.md | `/scripts/generate`, `/scripts/sessions/*` 경로 추가 |
| Phase B-6 | REST_API.md | `GET /storyboards/{id}/materials` 추가 |
| Phase C-3 | REST_API.md | `/storyboards/create` deprecated 표시 |
| Phase D 완료 | PRD.md | §3 워크플로우 업데이트 (Studio 코디네이터 반영) |
