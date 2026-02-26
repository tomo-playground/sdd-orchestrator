# Stage Workflow (프리프로덕션 에셋 준비)

> **상태**: 미착수
> **우선순위**: Tier 2 (Phase 18 예정)
> **선행**: Phase 7-4 (Studio Vertical Architecture), Phase 14 (ControlNet & IP-Adapter)
> **관련**: [STUDIO_VERTICAL_ARCHITECTURE.md](STUDIO_VERTICAL_ARCHITECTURE.md), [CROSS_SCENE_CONSISTENCY.md](CROSS_SCENE_CONSISTENCY.md)

---

## 1. 배경 및 문제 정의

### 1-1. 왜 필요한가

현재 Studio는 3단계 워크플로우(Script → Edit → Publish)로 운영된다.
"Stage"는 씬 이미지 생성 전에 모든 에셋을 준비/확인하는 **프리프로덕션 단계**로,
4단계 워크플로우(Script → **Stage** → Direct → Publish)로 확장한다.

**네이밍 근거** — Film Production 메타포:

| 단계 | 메타포 | 역할 |
|------|--------|------|
| Script | 대본 | 스토리보드/씬 텍스트 생성 |
| **Stage** | 무대 세팅 | 배경, 캐릭터, 음성, BGM 에셋 준비 |
| Direct | 연출 | 씬별 이미지 생성 + 편집 (기존 Edit) |
| Publish | 배포 | 렌더링 + 출력 |

### 1-2. 해결하는 핵심 문제

| 문제 | 현재 상태 | Stage 도입 후 |
|------|----------|-------------|
| **복장 불일치** | 다른 캐릭터 씬 이미지를 환경 참조(Canny ControlNet)할 때 캐릭터 윤곽선이 간섭 | 순수 배경(`no_humans`) 이미지로 환경 참조 → 윤곽선 간섭 제거 |
| **Edit 탭 정보 과부하** | 에셋 준비와 씬 연출이 뒤섞여 있음 | 에셋 준비(Stage)와 씬 연출(Direct) 명확 분리 |
| **배경 일관성 부재** | 같은 장소의 씬들이 서로 다른 배경 구조를 가질 수 있음 | Location별 단일 배경 이미지를 씬들이 공유 |

---

## 2. Phase 구성

### Phase 1 (MVP): 배경 생성 + 씬 매핑

| # | 항목 | 설명 |
|---|------|------|
| 1 | Location별 배경 생성 | Writer Plan의 locations로부터 `no_humans` 배경 이미지 자동 생성 |
| 2 | 씬-배경 자동 매핑 | 같은 location의 씬에 동일 `background_id` 할당 |
| 3 | Readiness 대시보드 | 에셋 준비 상태 시각화 + Direct 진행 가드 |
| 4 | 배경 재생성/태그 편집 | 개별 location 배경 재생성, 태그 수정 후 반영 |
| 5 | 4단계 탭 UI | Script → Stage → Direct → Publish 탭 전환 |

### Phase 2: 에셋 확장

| # | 항목 | 설명 |
|---|------|------|
| 1 | TTS 음성 미리듣기 | Stage에서 씬별 TTS 프리뷰 재생 |
| 2 | 캐릭터 프리뷰 재생성 | Stage 내에서 캐릭터 프리뷰 확인/재생성 |
| 3 | Express 모드 호환 | `writer_plan.locations` 없을 때 `context_tags`에서 location 역추론 |
| 4 | 에셋 간 의존성 표시 | LoRA ↔ StyleProfile 관계 시각화 |
| 5 | 배경 이미지 캐싱 | `location + style_profile_id` 조합으로 중복 생성 방지 |

### Phase 3: 렌더링 연동

| # | 항목 | 설명 |
|---|------|------|
| 1 | 트랜지션 자동 선택 | 장소 변경 씬: slide, 같은 장소: fade |
| 2 | Ken Burns 교대 프리셋 | 같은 배경 연속 시 단조로움 방지 |
| 3 | Post 레이아웃 블러 프리컴퓨팅 | Stage에서 블러 배경 사전 생성 |
| 4 | ControlNet 자동 선택 | 실내: Canny(0.3-0.4), 실외: Depth(0.2-0.3) 자동 결정 |

---

## 3. 기술 설계

### 3-1. DB 스키마 변경

**마이그레이션 1개** — 기존 데이터 영향 없음 (모두 nullable 추가).

#### `backgrounds` 테이블 변경

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `storyboard_id` | `Integer FK` (nullable, CASCADE) | 스토리보드 전용 배경. NULL이면 공용(is_system) |
| `location_key` | `String(100)` nullable | Writer Plan의 location 식별자 |

#### `storyboards` 테이블 변경

| 컬럼 | 타입 | 허용 값 | 설명 |
|------|------|---------|------|
| `stage_status` | `String(20)` nullable | `pending`, `staging`, `staged`, `failed` | Stage 진행 상태 |

### 3-2. 데이터 흐름

```
Writer Plan (locations 이미 존재 — SSOT)
  ↓
Stage Service: locations 소비
  ↓
location별 Background 레코드 생성 (storyboard_id + location_key)
  ↓
compose_for_background()로 no_humans 이미지 생성
  ↓
Scene.background_id 자동 매핑
  ↓
기존 _resolve_background() → environment_reference_id 자동 전환 (변경 없음)
```

**핵심: 기존 인프라 재활용**

| 기존 인프라 | 역할 | 변경 필요 |
|------------|------|----------|
| `background_id` → `environment_reference_id` 전환 | `generation_prompt.py`에 이미 구현 | 없음 |
| Background 모델의 `tags`, `weight`, `image_asset_id` | 배경 메타데이터 저장 | 없음 |
| `useMaterialsCheck` 훅 + `MaterialsPopover` | 에셋 준비 상태 체크 | Stage 탭으로 확장 |
| `compose_for_reference()` | 참조 이미지 프롬프트 생성 | `compose_for_background()` 파생 |

### 3-3. Backend 신규

#### 서비스: `services/stage/background_generator.py`

| 함수 | 역할 |
|------|------|
| `generate_location_backgrounds()` | Writer Plan locations → 배경 이미지 배치 생성 |
| `assign_backgrounds_to_scenes()` | location_key 기준 씬-배경 자동 매핑 |
| `regenerate_background()` | 특정 location 배경 개별 재생성 |

- 비동기 Task (SD WebUI 호출 2-5분 소요)
- StyleContext 공유 (동일 체크포인트 + Style LoRA)

#### 프롬프트: `compose_for_background()` 신규 메서드

5-Layer Background Template:

| Layer | 내용 | 비고 |
|-------|------|------|
| L0 Quality | `masterpiece`, `best_quality`, `absurdres` | 기존 Quality Layer 재사용 |
| L1 Subject | `no_humans`, `scenery` | **항상 고정** — 인물 배제 |
| L2-L8 Character | 전부 스킵 | 캐릭터 관련 레이어 비활성화 |
| L9 Camera | `wide_shot` 기본값 | 배경 전체 포착 |
| L10 Environment | location + props 태그 | Writer Plan에서 추출 |
| L11 Atmosphere | mood + Style LoRA trigger | 화풍 일관성 유지 |

**프롬프트 품질 규칙**:

- Negative prompt 강화: 인물 배제(`1girl`, `1boy`, `person`) + 단순 배경 방지(`simple_background`, `white_background`)
- Danbooru 검증 태그만 사용: `warm_lighting` → `ceiling_light` + `lamp`, `indoor` → `indoors`
- 실내 배경: 소품 태그 2-4개 보강 필수 (`cafe`=134건으로 학습 데이터 부족)
- Canny weight 캘리브레이션: 실내 0.3-0.4, 실외 0.2-0.3

#### 라우터: `routers/stage.py`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/{storyboard_id}/stage/generate-backgrounds` | 배경 일괄 생성 시작 |
| GET | `/{storyboard_id}/stage/status` | 진행 상태 조회 |
| POST | `/{storyboard_id}/stage/assign-backgrounds` | 씬에 background_id 매핑 |
| POST | `/{storyboard_id}/stage/regenerate-background/{location_key}` | 개별 재생성 |

#### 기존 코드 수정

| 파일 | 변경 내용 |
|------|----------|
| `generation_controlnet.py` | `_apply_environment()`: Background 참조 시 `no_humans` 스킵 해제 조건 추가 |
| `storyboard/helpers.py` | `calculate_auto_pin_flags()`: `background_id` 존재 시 auto_pin 비활성화 |
| `agent/state.py` | `WriterPlan.locations`: `list[dict]` → `list[LocationPlan]` Pydantic 모델 |

### 3-4. Frontend 신규

#### 타입 변경

```typescript
// 기존
type StudioTab = "script" | "edit" | "publish";

// 변경
type StudioTab = "script" | "stage" | "direct" | "publish";
// edit → direct 리네이밍, stage 추가
```

localStorage 마이그레이션: `"edit"` → `"direct"` 자동 매핑.

#### 새 컴포넌트

| 컴포넌트 | 역할 |
|---------|------|
| `StageTab.tsx` | Stage 탭 메인 컴포넌트 (3-Column Layout) |
| `StageLocationCard.tsx` | 배경 카드 (이미지 프리뷰 + 태그 + 재생성) |
| `StageCharacterCard.tsx` | 캐릭터 에셋 카드 (Phase 2) |
| `StageVoiceCard.tsx` | 음성 에셋 카드 (Phase 2) |
| `StageBgmCard.tsx` | BGM 에셋 카드 (Phase 2) |
| `StageSceneMapping.tsx` | 씬-배경 매핑 시각화 |

#### 훅

| 훅 | 역할 |
|----|------|
| `useStageReadiness.ts` | 기존 스토어에서 에셋 준비 상태 파생 (새 스토어 불필요) |

#### 기존 컴포넌트 수정

| 컴포넌트 | 변경 내용 |
|---------|----------|
| `StudioWorkspaceTabs.tsx` | 3탭 → 4탭 확장 |
| `StudioWorkspace.tsx` | StageTab 분기 추가 |
| `PipelineStatusDots.tsx` | Stage 단계 추가 |
| `ScriptTab.tsx` | 완료 후 이동 대상: `"edit"` → `"stage"` |
| `MaterialsPopover.tsx` | Stage 탭 연결 또는 제거 (중복 방지) |

---

## 4. UI 레이아웃

### 4-1. 3-Column 구조

기존 `StudioThreeColumnLayout` 재활용.

| 영역 | 너비 | 내용 |
|------|------|------|
| Left | 280px | 씬-에셋 트리 뷰 + Readiness 게이지 + [Proceed to Direct] 버튼 |
| Center | flex-1 | 에셋 카테고리별 카드 그리드 (Locations → Characters → Voice & BGM 순서) |
| Right | 300px | 선택된 에셋 상세 편집 (태그, Canny weight, 매핑된 씬 체크리스트) |

### 4-2. 에셋 카드 상태

| 상태 | 테두리 색상 | 설명 |
|------|------------|------|
| Ready | `emerald` | 에셋 완성, 사용 가능 |
| Warning | `amber` | 불완전 (예: 태그 부족) |
| Missing | `dashed zinc` | 미생성 + Setup CTA 버튼 |
| Generating | `indigo` + `animate-pulse` | SD WebUI 생성 중 |

### 4-3. 단계 전환 규칙

| 전환 | 조건 | 동작 |
|------|------|------|
| Script → Stage | 스크립트 생성 완료 시 | 자동 전환 |
| Stage → Direct | [Proceed] 버튼 클릭 | Readiness < 100%면 경고 다이얼로그 (소프트 가드, 탭 잠금 안 함) |
| Stage 건너뛰기 | Express 모드 | Stage는 opt-in — Express 모드는 기존 파이프라인 유지 |

### 4-4. Readiness Gate 대시보드

| 요소 | 설명 |
|------|------|
| 전체 진행률 바 | N/M Ready (퍼센트 표시) |
| 카테고리별 상태 | Characters, Locations, Voices, BGM |
| Missing 항목 목록 | 미완성 에셋 하이라이트 |
| [Auto-Setup Missing] 버튼 | AI가 미완성 에셋 자동 처리 |

---

## 5. 추가 아이디어 (Phase 2-3)

### 5-1. 렌더링 품질 연동

| 아이디어 | Phase | 효과 |
|---------|-------|------|
| 실내/실외에 따라 Canny vs Depth 자동 선택 | 3 | 자연 배경에서 공간감 향상 |
| 같은 배경 연속 시 Ken Burns 교대 패턴 | 3 | 단조로움 방지 |
| 장소 변경 씬에서 dramatic 트랜지션 자동 선택 | 3 | Stage 메타데이터 활용 |
| Post 레이아웃 블러 배경 프리컴퓨팅 | 3 | 렌더링 성능 + 시각 통일성 |

### 5-2. 에셋 관리 고도화

| 아이디어 | Phase | 효과 |
|---------|-------|------|
| 에셋 A/B 비교 뷰 (재생성 전후) | 2 | 품질 판단 지원 |
| 일괄 재생성 (Batch Actions) | 2 | 효율성 |
| 씬 타임라인 미니맵 | 2 | 컨텍스트 전환 비용 감소 |

### 5-3. 인코딩 최적화

| 아이디어 | Phase | 효과 |
|---------|-------|------|
| 배경 일관성으로 CRF 비트레이트 5-15% 감소 | 자동 | 인코딩 효율 향상 |
| 트랜지션 블렌딩 구간 색감 안정화 | 자동 | xfade 품질 향상 |

---

## 6. DoD (Definition of Done) — Phase 1

| # | 항목 | 검증 기준 |
|---|------|----------|
| 1 | Location Auto-Generation | Writer Plan의 locations로부터 location별 `no_humans` 배경 이미지가 자동 생성되는가? |
| 2 | Scene-Background Mapping | 같은 location의 모든 씬에 동일 `background_id`가 자동 할당되는가? |
| 3 | Environment Reference Auto-Link | 할당된 `background_id`가 `environment_reference_id`로 자동 전환되어 Canny ControlNet에 적용되는가? |
| 4 | Costume Consistency | `no_humans` 배경 기반 Canny 적용 시 캐릭터 윤곽선 간섭 없이 복장이 일관되는가? |
| 5 | Background Regeneration | 특정 location의 배경을 개별 재생성할 수 있는가? |
| 6 | Tag Editing | 배경 태그를 수정하고 재생성에 반영할 수 있는가? |
| 7 | Readiness Dashboard | 에셋 준비 상태가 정확히 표시되고, Direct 진행 전 확인할 수 있는가? |
| 8 | Opt-in Compatibility | Express 모드 등 Stage를 건너뛴 경우 기존 파이프라인이 정상 동작하는가? |
| 9 | Style Consistency | 배경 이미지가 캐릭터 씬과 동일한 화풍(StyleProfile + LoRA)으로 생성되는가? |
| 10 | UI State Persistence | Stage 진행 중 새로고침해도 생성된 에셋과 상태가 복구되는가? |
| 11 | 4-Tab Navigation | Script → Stage → Direct → Publish 탭이 정상 동작하는가? |
| 12 | Backward Compatibility | 기존 스토리보드(Stage 미경험)가 Direct/Publish에서 정상 동작하는가? |

---

## 7. 의존성

| 의존성 | 상태 | 설명 |
|--------|------|------|
| `Background` 모델 (`tags`, `weight`, `image_asset_id`) | 완료 | `models/background.py` |
| `_resolve_background()` → `environment_reference_id` 전환 | 완료 | `generation_prompt.py` |
| `compose_for_reference()` 프롬프트 메서드 | 완료 | `v3_composition.py` |
| `useMaterialsCheck` 훅 + `MaterialsPopover` | 완료 | Frontend 에셋 체크 |
| `WriterPlan.locations` (Agent State) | 완료 | `agent/state.py` |
| `StudioThreeColumnLayout` | 완료 | 기존 레이아웃 컴포넌트 |
| Phase 14 (ControlNet & IP-Adapter) | 완료 | Canny/Depth ControlNet 인프라 |

---

## 8. 테스트 전략

| Phase | 테스트 범위 | 예상 수량 |
|-------|-----------|----------|
| 1 | `compose_for_background()` 프롬프트 생성 | ~8 |
| 1 | `generate_location_backgrounds()` 배치 생성 로직 | ~6 |
| 1 | `assign_backgrounds_to_scenes()` 매핑 로직 | ~6 |
| 1 | Stage API 엔드포인트 (정상/404/빈 locations) | ~8 |
| 1 | 4-Tab UI 전환 + localStorage 마이그레이션 | ~6 |
| 1 | Readiness 대시보드 상태 파생 | ~4 |
| 1 | Backward Compatibility (Stage 미경험 스토리보드) | ~4 |
| **합계** | | **~42** |

---

## 9. 스코프 외

| 항목 | 이유 |
|------|------|
| 실시간 배경 생성 (씬 추가 시 자동) | Phase 1은 수동 트리거. 자동화는 Phase 2 이후 |
| 배경 공유 라이브러리 | `is_system` 공용 배경 관리는 별도 기능 |
| 멀티 앵글 배경 (같은 장소, 다른 카메라) | Phase 3에서 Ken Burns 연동 시 검토 |
| 3D 배경 / Depth Map 생성 | 현재 Stable Diffusion 2D 파이프라인 범위 |

---

## 10. 관련 파일

### Backend

| 파일 | 상태 | 설명 |
|------|------|------|
| `services/stage/background_generator.py` | 신규 | 배경 생성 서비스 |
| `services/prompt/v3_composition.py` | 수정 | `compose_for_background()` 추가 |
| `routers/stage.py` | 신규 | Stage API 라우터 |
| `models/background.py` | 수정 | `storyboard_id`, `location_key` 추가 |
| `models/storyboard.py` | 수정 | `stage_status` 추가 |
| `services/generation_controlnet.py` | 수정 | `no_humans` 스킵 로직 수정 |
| `services/storyboard/helpers.py` | 수정 | auto_pin 로직 수정 |
| `services/agent/state.py` | 수정 | `WriterPlan.locations` 타입 강화 |

### Frontend

| 파일 | 상태 | 설명 |
|------|------|------|
| `app/components/studio/StageTab.tsx` | 신규 | Stage 탭 메인 컴포넌트 |
| `app/components/studio/StageLocationCard.tsx` | 신규 | 배경 카드 컴포넌트 |
| `app/hooks/useStageReadiness.ts` | 신규 | 에셋 Readiness 파생 훅 |
| `app/store/useUIStore.ts` | 수정 | `StudioTab` 타입 확장 |
| `app/components/studio/StudioWorkspaceTabs.tsx` | 수정 | 4탭 확장 |
| `app/components/studio/StudioWorkspace.tsx` | 수정 | StageTab 분기 추가 |
| `app/components/studio/PipelineStatusDots.tsx` | 수정 | Stage 단계 추가 |

### 문서

| 문서 | 업데이트 내용 |
|------|-------------|
| `docs/03_engineering/architecture/DB_SCHEMA.md` | backgrounds 스키마 변경, storyboards.stage_status |
| `docs/03_engineering/api/REST_API.md` | Stage API 4개 엔드포인트 추가 |
| `docs/01_product/ROADMAP.md` | Phase 18 Stage Workflow 추가 |
