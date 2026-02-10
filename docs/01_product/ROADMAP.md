# Shorts Factory Master Roadmap

**원칙**: 안정성 → 리팩토링 → 안정성 → 신규 개발 사이클. 영상 품질 100% 일관성(Zero Variance) 유지.

---

## Phase 1-4: Foundation & Refactoring - ARCHIVED

완료. [Phase 1-4 아카이브](../99_archive/ROADMAP_PHASE_1_4.md) 참조.

---

## Phase 5: High-End Production - ARCHIVED

검증된 안정적인 기반 위에 프로덕션 기능을 구축. **전체 완료**.

| 섹션 | 핵심 성과 | 상태 |
|------|----------|------|
| 5-1. 운영 효율화 | Resume/Checkpoint, Smart AutoRun, Secure Config | [x] |
| 5-2. 영상 품질 강화 | Ken Burns, Scene Text Animation, 13개 전환 효과, Full/Post Layout | [x] |
| 5-3. 콘텐츠 확장 | Preset System, Sample Topics, 일본어/수학 템플릿 | [x] |
| 5-4. Prompt Analytics | 정량적 품질 지표, Gemini 프롬프트 검증 | [x] |
| 5-5. UI/UX 개선 | SD 파라미터 Advanced 이동, Media Defaults, Render UX | [x] |
| 5-6. UI Polish | Loading/Error UI, Character Image Modal | [x] |
| 5-7. QA | Backend 335 + Frontend 67 = **총 402개** 테스트 | [x] |

미완료 항목은 Feature Backlog 또는 Phase 7-1로 이동.

---

## Phase 6: Character & Prompt System (v2.0)

다중 캐릭터 지원 및 프롬프트 빌더 시스템 구축.

**환경**: animagine-xl (SDXL), eureka_v9/chibi-laugh LoRA, 9종 Preset

### 6-1 ~ 6-4: Core Architecture - COMPLETE

| 섹션 | 핵심 성과 | 상태 |
|------|----------|------|
| 6-1. Data Foundation | PostgreSQL + Alembic, 262개 태그 마이그레이션, CRUD API | [x] |
| 6-2. Studio Integration | Character Preset UI, Multi-LoRA, Style Profile 통합 | [x] |
| 6-2.5. V3 Architecture | Storyboard-Centric 전환, 12-Layer PromptBuilder, 4개 런타임 캐시 | [x] |
| 6-3. Scene Expression | Gender System, Pose/Expression 확장, Tag Autocomplete | [x] |
| 6-4. Advanced Features | Civitai 연동, Tag Analytics, Evaluation System, ControlNet/IP-Adapter | [x] |

**6-4 세부 완료 항목**:
- 6-4.21 Generation Log Analytics
- 6-4.22 Gemini Image Editing (Auto Edit + 자연어 편집 + Preview Lock)
- 6-4.23 Environment Pinning (자동 핀 + 27개 TDD 테스트)
- 6-4.30 Style Profile System (Manage 탭 + 선택 모달 + Output 간소화)
- 6-4.31 Asset Management (MediaAsset 3단계 계층 + MinIO)
- 6-4.32 Pose Expansion (924개 태그 분석, 32종 핵심 포즈)
- 6-4.23 Character Consistency (IP-Adapter + Dual ControlNet)
- 6-4.36 Deep Optimization (Dead Code 제거, M4 Pro 최적화)
- 6-4.37 Stability & Polish (DB/UI 버그 수정)
- 6-4.38 ManagePage Refactoring (2,600줄 → 6개 탭)
- 6-4.39 Character Tag Fix (V3 태그 프리뷰/디버그 통합)

---

### 6-5. Stability & Integrity (P0/P1 Critical Fixes)

**목표**: 데이터 손실 위험 제거, 런타임 크래시 해결, 핵심 로직 정합성 확보.

**8개 에이전트 도메인 분석 기반** (2026-02-01):
- Backend(38건), Frontend(28건), Prompt Eng(22건), QA(24건), DBA(28건), FFmpeg(20건), UI/UX(28건), Storyboard(17건)
- 총 ~205건 → 중복 통합 후 ~155건 → P0(9) + P1(16) = **25건**

#### Batch A: DB Integrity (DBA)
| # | 작업 | 우선순위 | 상태 |
|---|------|---------|------|
| 1 | 6개 테이블 `*_asset_id` FK 추가 + scenes CASCADE 정책 | P0 | [x] |
| 2 | `media_assets` 복합 인덱스 `(owner_type, owner_id)` | P0 | [x] |
| 3 | 고아 레코드 정리 (media_assets 40건 + scene_quality_scores 787건) | P0 | [x] |
| 4 | `scene_character_actions` 인덱스 + `tag_rules` FK | P1 | [x] |
| 5 | `tag_effectiveness` 테이블 생성 (DB_SCHEMA.md 문서화 완료) | P1 | [x] |

#### Batch B: Backend Fixes (Backend)
| # | 작업 | 우선순위 | 상태 |
|---|------|---------|------|
| 1 | `generation.py` DB session leak 수정 (`next()` → DI) | P0 | [x] |
| 2 | `evaluation.py` legacy `identity_tags`/`clothing_tags` 제거 | P0 | [x] |
| 3 | `MediaAsset.local_path` 속성 추가 | P0 | [x] |
| 4 | `storyboard_routes.py` N+1 쿼리 해결 (eager load) | P1 | [x] |
| 5 | `LoRATriggerCache` admin/refresh-caches 등록 | P1 | [x] |

#### Batch C: FFmpeg Fixes (FFmpeg)
| # | 작업 | 우선순위 | 상태 |
|---|------|---------|------|
| 1 | zoompan FPS(25) vs output FPS 불일치 수정 | P1 | [x] |
| 2 | CRF 값 + 인코딩 상수 `config.py` 이관 (SSOT) | P1 | [x] |
| 3 | FFmpeg process timeout 설정 | P1 | [x] |
| 4 | `-movflags +faststart` 추가 (웹 스트리밍 최적화) | P1 | [x] |

#### Batch D: Prompt & Storyboard (Prompt Eng + Storyboard)
| # | 작업 | 우선순위 | 상태 |
|---|------|---------|------|
| 1 | Gemini JSON 파싱 강화 (마크다운 코드블록 제거) | P0 | [x] |
| 2 | `TagRuleCache` 충돌 규칙 V3 compose 연동 | P1 | [x] |
| 3 | `restricted_tags` DB 이관 (하드코딩 제거) | P1 | [x] |
| 4 | DB-missing 태그 패턴 기반 fallback (전부 LAYER_SUBJECT 방지) | P1 | [x] |
| 5 | `scene_tags` vs `context_tags` 필드명 통일 | P1 | [x] |
| 6 | `_DB_GROUP_TO_GEMINI_CATEGORY` 매핑 12-Layer 정렬 | P1 | [x] |

#### Batch E: Frontend & Docs (Frontend + PM)
| # | 작업 | 우선순위 | 상태 |
|---|------|---------|------|
| 1 | `API_BASE` 중복 해소 (단일 env 변수) | P1 | [x] |
| 2 | `useTags` hook 카테고리 의존성 수정 | P1 | [x] |
| 3 | `validation.py` SessionLocal → DI 전환 | P0 | [x] |
| 4 | `CLAUDE.md` 버전 정보 현행화 (Next.js 15, React 19, Zustand 5) | P1 | [x] |

**DoD**: DB session leak 0건, FK/인덱스 마이그레이션 적용, 고아 정리 완료, 기존 테스트 전량 통과.

---

### 6-6. Code Health & Testing

**목표**: 대형 파일 분리, 테스트 커버리지 확대, 아키텍처 정비.
**선행**: Phase 6-5 완료.

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| 1 | `video.py` 987줄 → `services/video/` 패키지 6모듈 (max 329줄) | 코드 분리 | [x] |
| 2 | `SceneCard.tsx` 894줄 → 383줄 + 5개 서브컴포넌트 | 코드 분리 | [x] |
| 3 | `CharacterEditModal.tsx` 950줄 → 400줄 + 1 hook + 4개 서브컴포넌트 | 코드 분리 | [x] |
| 4 | `studio/page.tsx` 594줄 → 201줄 + 2 hooks + 1 store action | 코드 분리 | [x] |
| 5 | `generation.py` 300줄 함수 → 6개 helper 추출 (orchestrator ~20줄) | 코드 분리 | [x] |
| 6 | Router/Service 레이어 분리 (storyboard: 364줄→54줄 router + 497줄 service) | 아키텍처 | [x] |
| 7 | 라우터 테스트 추가 (20/24 커버리지, 288개 테스트) | 테스트 | [x] |
| 8 | `evaluation.py` 단위 테스트 작성 (47개) | 테스트 | [x] |
| 9 | `TEST_STRATEGY.md` 수치 갱신 (948개 테스트) | 테스트 | [x] |
| 10 | Error Boundary 구현 (app/error, global-error, studio/error) | 아키텍처 | [x] |
| 11 | 비동기 Gemini API 전환 + 재시도/폴백 (storyboard, imagen_edit, gemini_imagen) | 아키텍처 | [x] |
| 12 | `image_storage_key` 정규화 + `activity_logs.py` 수정 | 데이터 정합성 | [x] |

**진척**: 12/12 완료 (100%), 테스트 786개 통과
**DoD**: 400줄 초과 코드 파일 0건, 라우터 테스트 커버리지 20/24+.

---

### 6-7. Infrastructure & DX

**목표**: CI 파이프라인, Soft Delete, Common UI Toolkit, 개발 도구 정비.
**선행**: Phase 6-6 완료 (테스트 기반 갖춤).

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| 1 | CI 파이프라인 (GitHub Actions: lint + test) | 인프라 | [x] |
| 2 | VRT Baseline System | 인프라 | [ ] |
| 3 | 고아 media_assets GC 시스템 | 인프라 | [x] |
| 4 | SoftDeleteMixin + Alembic 마이그레이션. [기능 명세](../99_archive/features/SOFT_DELETE.md) · [기술 설계](../03_engineering/backend/SOFT_DELETE.md) | Soft Delete | [x] |
| 5 | Backend trash/restore/permanent 엔드포인트 | Soft Delete | [x] |
| 6 | Frontend Trash 탭 (Manage) | Soft Delete | [x] |
| 7 | Common UI Toolkit v1 (Button, Modal, ConfirmDialog). [상세](FEATURES/TECH_DEBT.md) | UI | [x] |
| 8 | z-index 통합 관리 (Tailwind 설정) | UI | [x] |
| 9 | Hook Extraction (5개 탭 커스텀 Hook 분리) | Frontend | [x] |
| 10 | WD14 Feedback Loop (`tag_effectiveness` 자동 업데이트) | 프롬프트 | [ ] |
| 11 | Batch Generation API (다수 씬 병렬 생성) | Backend | [x] |
| 12 | WD14 Validate 매칭 정확도 개선 (부분문자열 오탐 제거, 복합태그 분해, 동의어, skipped/partial 응답) | 프롬프트 | [x] |

| 13 | Character Voice Preset (캐릭터 대표 목소리) | Voice | [x] |
| 14 | Storyboard Narrator Voice (스토리보드 나레이터 목소리) | Voice | [x] |
| 15 | TTS 파이프라인 speaker→voice 자동 resolve | Voice | [x] |
| 16 | DB Schema Cleanup: 네이밍(`default_` 제거) + 타입(`Integer→Boolean`, `Text→JSONB`). [명세](../99_archive/features/SCHEMA_CLEANUP.md) | DB | [x] |

**DoD**: PR마다 CI 자동 테스트, Soft Delete 3개 모델 적용, 공통 컴포넌트 4개+.

---

### 6-8. Local AI Engine & Performance

**목표**: M4 Pro 하드웨어를 활용한 로컬 엔진 전환 및 성능 최적화.

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| 1 | Qwen3-TTS 로컬 엔진 설치 및 기본 통합 (MPS 가속) | 인프라 | [x] |
| 2 | TTS 전용 스키마 확장 (Voice Design, Cloning 지원) | API | [x] |
| 3 | M4 Pro 최적화 (Flash Attention / MLX 연동) | 인프라 | [x] |
| 4 | 로컬 엔진 UI 연동 (목소리 설계 프롬프트 입력) | UX | [x] |
| 5 | Voice Preset CRUD API + 음성 업로드/프리뷰 | API | [x] |
| 6 | Render Preset에 `voice_preset_id` FK 연동 | DB | [x] |

| 7 | Stable Audio Open AI BGM 엔진 (MPS 로컬 실행) | 인프라 | [x] |
| 8 | `music_presets` 테이블 + CRUD API (8 엔드포인트) | API | [x] |
| 9 | Music Presets 미리듣기 (생성 + Play/Stop) | UX | [x] |
| 10 | `render_presets` BGM 모드 (`bgm_mode`, `music_preset_id`) + VideoBuilder 연동 | 렌더링 | [x] |
| 11 | Frontend Music Presets 관리 탭 + BGM AI 모드 토글 | UX | [x] |

**6-8 세부 완료 항목**:
- `voice_presets` 테이블: VoiceDesign 전용 (Clone/Upload 제거, `voice_seed` 추가)
- `render_presets`에 TTS 설정 통합: `tts_engine`, `voice_design_prompt`, `voice_preset_id`
- Voice Preview API (`POST /voice-presets/preview`): seed 기반 재현성 보장
- TTS 캐시 시스템 (`TTS_CACHE_DIR`) + timeout 설정
- Caption 해시태그 추출 기능 추가
- (2026-02-07) Stable Audio Open AI BGM: `music_presets` 테이블 + Alembic 마이그레이션, CRUD API 8개, 프리셋 미리듣기, `render_presets`에 `bgm_mode`/`music_preset_id` 추가, VideoBuilder `effects.py` BGM 모드 분기 (file/ai), Frontend Music Presets 관리 탭 + BGM AI 모드 토글, 시스템 프리셋 10개 시딩, 테스트 22개 추가
- (2026-02-08) TTS 품질 강화: Context-Aware Voice Design, 후처리 개선 (무음 압축, 환각 감지/제거), 최소 duration 검증 + seed 변형 자동 재생성, 짧은 대본 반복 발음 방지 (최소 10자 규칙), MPS 최적화

---

## Phase 7-1: UX & Feature Expansion

**목표**: 사용자 경험 개선 및 핵심 신규 기능 추가.
**선행**: Phase 6-7 완료 (CI, Soft Delete, UI Toolkit).

| # | 작업 | 분류 | 참조 | 상태 |
|---|------|------|------|------|
| 1 | Quick Start Flow: +New Story Lazy Creation (첫 Save/Generate 시 DB 저장), PlanTab 설정/스토리 재설계, 인라인 StyleProfile 셀렉터 | UX | [명세](FEATURES/UX_IMPROVEMENTS.md) | [x] |
| 2 | Setup Wizard (첫 실행 가이드) | UX | [명세](FEATURES/UX_IMPROVEMENTS.md) | [ ] |
| 3 | 접근성 기본 (ARIA, focus trap, keyboard) | UX | - | [ ] |
| 4 | 이미지 생성 Progress (WebSocket/SSE) | 기능 | - | [ ] |
| 5 | Multi-Character UI (DB 스키마 완료) | 기능 | [명세](FEATURES/MULTI_CHARACTER.md) | [ ] |
| 6 | Scene Builder UI (배경/시간/날씨) | 기능 | [명세](FEATURES/SCENE_BUILDER_UI.md) | [ ] |
| 7 | Structure별 전용 Gemini 템플릿 (5종) | 기능 | - | [ ] |
| 8 | Character Builder 위저드 | 기능 | [명세](FEATURES/CHARACTER_BUILDER.md) | [ ] |
| 9 | OutputTab 채널/영상 분리 | UX | [설계](../02_design/UI_PROPOSAL.md) | [x] |
| 10 | Creative Lab & Engine (Tag Lab + Scene Lab + Multi-Agent Creative) | 기능 | [API](../03_engineering/api/REST_API_CREATIVE.md) | [x] |
| 11 | Studio UI Polish (Video탭 통합, Global 접기, Save 이동, 캐릭터 프리뷰 확대) | UX | - | [x] |
| 12 | 씬 텍스트 하단 배치 + 드롭섀도우 + Color Grade | 영상 품질 | - | [x] |
| 13 | Gemini 스크립트 길이 제한 강화 (30자/Korean) | 품질 | - | [x] |
| 14 | Character Identity Injection (Gemini 스토리보드에 캐릭터 태그/LoRA 주입 + 오토파일럿 overlay 수정) | 품질 | - | [x] |
| 15 | 좌측 사이드바 네비게이션 + 컨텍스트 전환 버그 수정 (Phase A 버그 6건 + Phase B 사이드바 완료. Phase C ContextBar 정리 보류) | UX | [명세](../99_archive/features/SIDEBAR_NAVIGATION.md) | [x] |
| 16 | Insights 탭 Studio → Manage 이동 (QualityDashboard + AnalyticsDashboard, 스토리보드 셀렉터) | UX | - | [x] |
| 17 | YouTube Shorts Upload (OAuth + per-project credential + upload modal) | 기능 | [명세](FEATURES/YOUTUBE_UPLOAD.md) | [x] |
| 18 | Dialogue & Narrated Dialogue 구조 (2-character + 3-speaker Narrator) | 기능 | - | [x] |
| 19 | 렌더링 진행률 SSE 스트리밍 (실시간 % 표시) | UX | - | [x] |
| 20 | Style LoRA Unification + Embedding trigger words 프롬프트 주입 | 품질 | - | [x] |
| 21 | Narrator Scene 스타일 적용 (image_prompt 백엔드 주입 + ControlNet/IP-Adapter 자동 비활성) | 품질 | - | [x] |
| 22 | image_url 정합성 강화 (JSONB 저장 방어, base64 전송 방지, stale ID 방어) | 안정성 | - | [x] |
| 23 | Background Scene 태그 필터링 (no_humans 감지 → 캐릭터 레이어 제거) + LoRA Weight Cap 통합 (0.76) | 품질 | - | [x] |
| 24 | Creative Lab V2: 쇼츠 멀티에이전트 시나리오 생성기 (9-Agent Pipeline + Studio 연동) | 기능 | [명세](../99_archive/features/CREATIVE_LAB_V2.md) | [x] |

---

## Phase 7-0: ControlNet & Pose Control - ARCHIVED

완료. ControlNet 포즈 제어, IP-Adapter 캐릭터 일관성 시스템 구축.
- 2026-02-02: thumbs_up 포즈 추가 (28번째 포즈, 포즈 에셋 + synonyms)

---

## Phase 7-2: Project/Group System

**목표**: 채널(Project) + 시리즈(Group) 계층 구조 구현. 설정 상속, 서사 톤 자동 주입, 데이터 기반 태그 추천.
**선행**: Phase 6-7 일부 (DB 마이그레이션 인프라). Phase 0은 6-7과 병렬 가능.

| Phase | 핵심 | 상태 |
|-------|------|------|
| Phase 0: Foundation | DB 마이그레이션, CRUD API, FK 연결 | [x] |
| Phase 1: Core | FK 강화, 캐릭터 프로젝트 스코핑, 렌더 프리셋 분리, 설정 상속 엔진, 그룹 편집 UI | [x] |
| Phase 1.5: UX 정리 | Channel Profile → Project 통합, 캐릭터 글로벌화, +New Storyboard 그룹 내부 이동, Studio UX Polish | [x] |
| Phase 1.7: Group Defaults | 그룹 cascade 확장 (language, structure, duration, narrator_voice), Manage 그룹 기본값 편집 UI. [명세](../99_archive/features/GROUP_DEFAULTS.md) | [x] |
| Phase 2: Differentiation | Channel DNA (톤/세계관 주입), Tag Intelligence, Series Intelligence | [ ] |
| Phase 3: Advanced | 배치 렌더링, 브랜딩, 분석 대시보드 | [ ] |

**Phase 1.5 세부 완료 항목** (2026-02-02):
- Channel Profile → Project 통합 (profileSlice 삭제, avatar_key DB 이관)
- 캐릭터 글로벌화 (project_id nullable, 전역 유니크)
- ProjectDropdown 아바타/편집 UI, ProjectFormModal 캐릭터 셀렉터
- `page.tsx` God Component 분리 (545줄 → 107줄 + StoryboardsSection + CharactersSection)
- OutputTab 채널 프로필 섹션 제거, Current Style 섹션 제거
- TabBar 프로젝트 정보 중복 제거
- PromptSetupPanel Global/Actor A 탭 → 별도 카드 분리
- Actor A Advanced Settings (SD Parameters) 제거 (Style Profile로 통합)
- StoryboardActionsBar Reset 버튼 제거
- StoryboardGeneratorPanel Visual Style 필드 제거, Language select 전환
- ContextBar breadcrumb chevron 아이콘, Home 아이콘 전환
- Manage > Assets 표시명 개선 (확장자 제거, flex wrap)

상세: [기능 명세](FEATURES/PROJECT_GROUP.md)

---

## Phase 8: Multi-Style Architecture (Future)

**목표**: Anime, Realistic, 3D 등 다양한 화풍 지원을 위한 유연한 파이프라인 구축.

---

## Feature Backlog

Phase 8 이후 또는 우선순위 미정 항목.

| 기능 | 참조 |
|------|------|
| VEO Clip (Video Generation 통합) | [명세](FEATURES/VEO_CLIP.md) |
| Visual Tag Browser (태그별 예시 이미지) | [명세](FEATURES/VISUAL_TAG_BROWSER.md) |
| Profile Export/Import (Style Profile 공유) | [명세](FEATURES/PROFILE_EXPORT_IMPORT.md) |
| Scene Clothing Override (장면별 의상 변경) | [명세](FEATURES/SCENE_CLOTHING_OVERRIDE.md) |
| Scene 단위 자연어 이미지 편집 | [명세](FEATURES/SCENE_IMAGE_EDIT.md) |
| ~~AI BGM Generation~~ | ~~[명세](../99_archive/features/AI_BGM.md)~~ → 6-8 #7-11로 이동 (완료) |
| Storyboard Version History | - |
| LoRA Calibration Automation | - |
| Real-time Prompt Preview (12-Layer) | - |
| 씬 순서 드래그 앤 드롭 | - |
| Studio 초기 로딩 최적화 (useEffect 워터폴 제거, API 병렬화) | - |
| Backend response_model 전면 적용 (125개 엔드포인트 중 핵심 경로 우선, dict 타입 구체화) | - |
| ~~YouTube Shorts Upload~~ | ~~[명세](FEATURES/YOUTUBE_UPLOAD.md)~~ → 7-1 #17로 이동 (완료) |

---

## Development Cycle

```
Phase 6-5 (Stability) → 6-6 (Code Health) → 6-7 (Infra/DX) → 6-8 (Local AI) → 7-0 (ControlNet) → 7-1 (UX/Feature)
     P0/P1 Fixes          Refactoring          CI + Soft Delete    TTS/Voice/BGM     Pose Control      New Features
                                                                                                       + Creative Lab
                                                                                                            ↓
                                                          7-2 (Project/Group) → 8 (Multi-Style)
                                                           Cascading Config          Future
```

**현재 진행 상태** (2026-02-10):
- Phase 6-5 ~ 6-8: **완료** (6-8: AI BGM + TTS 품질 강화)
- Phase 7-0 (ControlNet): **완료** (ARCHIVED)
- Phase 6-7: **14/16** 완료 (잔여: #2 VRT, #10 WD14 Feedback)
- Phase 7-1: **17/24** 완료 (잔여: #2 Wizard, #3 접근성, #4 생성 Progress, #5 Multi-Char UI, #6 Scene Builder, #7 템플릿, #8 Char Builder)
- Phase 7-2: Phase 1.7 **완료**, Phase 2-3 대기
- **Backend 테스트**: 1,291개 수집

### 잔여 작업 우선순위 (재정리 2026-02-10)

**Tier 1 — 높은 임팩트 (중형, 3-5일)**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| 1 | 7-1 #7 | Structure별 전용 Gemini 템플릿 (5종) | 콘텐츠 품질 직결 |
| 2 | 7-1 #4 | 이미지 생성 Progress (SSE/WebSocket) | 렌더링 SSE 완료, 생성은 미구현 |
| 3 | 6-7 #10 | WD14 Feedback Loop (tag_effectiveness 자동 업데이트) | 프롬프트 자동 개선 루프 |
| 4 | 7-1 #5 | Multi-Character UI (Studio 스토리보드 생성기) | DB/Creative Lab 준비 완료, Studio UI만 구현 |

**Tier 2 — 확장 기능 (대형, 1주+)**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| 5 | 7-1 #6 | Scene Builder UI (배경/시간/날씨) | 씬 표현력 확장 |
| 6 | 7-1 #8 | Character Builder 위저드 | 캐릭터 생성 UX 개선 |
| 7 | 7-2 P2 | Channel DNA + Tag Intelligence | 프로젝트 차별화 |

**Tier 3 — 후순위**
| 순위 | 출처 | 작업 | 근거 |
|------|------|------|------|
| 8 | 6-7 #2 | VRT Baseline System | CI 존재, 추가 안정성 |
| 9 | 7-1 #2 | Setup Wizard (첫 실행 가이드) | 현재 단일 사용자 |
| 10 | 7-1 #3 | 접근성 기본 (ARIA, focus trap, keyboard) | 중요하나 긴급하지 않음 |
| 11 | 7-2 P3 | 배치 렌더링, 브랜딩, 분석 대시보드 | 장기 |

**7-1 최근 완료 (2026-02-05 ~ 02-09)**:
- Creative Lab & Engine: evaluation 시스템 → Lab 전환, Tag/Scene Lab, Multi-Agent Creative Engine (Director/Writer/Reviewer), Lab V3 통합 (`image_generation_core.py`)
- Dialogue(2-char) + Narrated Dialogue(3-speaker) 구조 추가, Narrator 씬 전용 처리
- 렌더링 SSE 진행률, Style LoRA 통합, image_url 정합성 강화
- TTS 품질: Context-Aware Voice, 환각 감지/제거, 반복 방지, 자동 재생성
- (2026-02-09) Background Scene 태그 필터링: `no_humans` 감지 → CHARACTER_ONLY_LAYERS(1-8) 제거 + 캐릭터 카메라 태그 필터. LoRA Weight Cap `STYLE_LORA_WEIGHT_CAP=0.76` 무조건 적용으로 통합
- (2026-02-09) Creative Lab V2 MVP: 9-Agent 시스템, Phase 1 Concept Debate + Phase 2 Production Pipeline, 6 Jinja2 Templates, Frontend V1/V2 모드 전환
- (2026-02-10) Creative Lab V2 Phase 3: Multi-Character Dialogue (character_ids 매핑, CharacterPicker 컴포넌트), Sound Designer 에이전트 (BGM 추천), Copyright Reviewer 에이전트, send-to-studio 서비스 추출 (creative_studio.py), QC feedback retry 개선, SSOT presets API 연동, 단위 테스트 14개
- (2026-02-10) 모듈화 위반 전면 리팩토링 (TDD 22건): `split_prompt_tokens` SSOT 통합, `resolve_style_loras` config cascade 통합, `creative_studio._build_scene` V3 composition 파이프라인 적용 (style_loras + negative_prompt), `lab.py` V3 이중 호출 제거, `controlnet.py` 태그 underscore 포맷 수정, 모놀로그 캐릭터 링크 누락 수정, V3 `_distribute_tags` LoRA 이중 주입 방지
- (2026-02-10) `compose_scene_with_style` SSOT 추출: Creative Lab/Studio Direct 프롬프트 파이프라인 단일화 (StyleProfile → V3 composition). `generate_image_with_v3`도 통합. `prompt_pre_composed` 경로 LoRA 이중 적용 버그 수정 (`skip_loras=True` + defense-in-depth 중복 방어)
