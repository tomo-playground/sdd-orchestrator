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
| 4 | SoftDeleteMixin + Alembic 마이그레이션. [기능 명세](FEATURES/SOFT_DELETE.md) · [기술 설계](../03_engineering/backend/SOFT_DELETE.md) | Soft Delete | [x] |
| 5 | Backend trash/restore/permanent 엔드포인트 | Soft Delete | [x] |
| 6 | Frontend Trash 탭 (Manage) | Soft Delete | [x] |
| 7 | Common UI Toolkit v1 (Button, Modal, ConfirmDialog). [상세](FEATURES/TECH_DEBT.md) | UI | [x] |
| 8 | z-index 통합 관리 (Tailwind 설정) | UI | [ ] |
| 9 | Hook Extraction (`useManageState` 등) | Frontend | [ ] |
| 10 | WD14 Feedback Loop (`tag_effectiveness` 자동 업데이트) | 프롬프트 | [ ] |
| 11 | Batch Generation API (다수 씬 병렬 생성) | Backend | [ ] |
| 12 | WD14 Validate 매칭 정확도 개선 (부분문자열 오탐 제거, 복합태그 분해, 동의어, skipped/partial 응답) | 프롬프트 | [x] |

| 13 | Character Voice Preset (캐릭터 대표 목소리) | Voice | [x] |
| 14 | Storyboard Narrator Voice (스토리보드 나레이터 목소리) | Voice | [x] |
| 15 | TTS 파이프라인 speaker→voice 자동 resolve | Voice | [x] |
| 16 | DB Schema Cleanup: 네이밍(`default_` 제거) + 타입(`Integer→Boolean`, `Text→JSONB`). [명세](FEATURES/SCHEMA_CLEANUP.md) | DB | [x] |

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

**6-8 세부 완료 항목**:
- `voice_presets` 테이블: VoiceDesign 전용 (Clone/Upload 제거, `voice_seed` 추가)
- `render_presets`에 TTS 설정 통합: `tts_engine`, `voice_design_prompt`, `voice_preset_id`
- Voice Preview API (`POST /voice-presets/preview`): seed 기반 재현성 보장
- TTS 캐시 시스템 (`TTS_CACHE_DIR`) + timeout 설정
- Caption 해시태그 추출 기능 추가

---

## Phase 7-1: UX & Feature Expansion

**목표**: 사용자 경험 개선 및 핵심 신규 기능 추가.
**선행**: Phase 6-7 완료 (CI, Soft Delete, UI Toolkit).

| # | 작업 | 분류 | 참조 | 상태 |
|---|------|------|------|------|
| 1 | Quick Start Flow: +New Story 즉시 DB 저장, PlanTab 설정/스토리 재설계, 인라인 StyleProfile 셀렉터 | UX | [명세](FEATURES/UX_IMPROVEMENTS.md) | [x] |
| 2 | Setup Wizard (첫 실행 가이드) | UX | [명세](FEATURES/UX_IMPROVEMENTS.md) | [ ] |
| 3 | 접근성 기본 (ARIA, focus trap, keyboard) | UX | - | [ ] |
| 4 | WebSocket Progress (생성/렌더링 진행률) | 기능 | - | [ ] |
| 5 | Multi-Character UI (DB 스키마 완료) | 기능 | [명세](FEATURES/MULTI_CHARACTER.md) | [ ] |
| 6 | Scene Builder UI (배경/시간/날씨) | 기능 | [명세](FEATURES/SCENE_BUILDER_UI.md) | [ ] |
| 7 | Structure별 전용 Gemini 템플릿 (5종) | 기능 | - | [ ] |
| 8 | Character Builder 위저드 | 기능 | [명세](FEATURES/CHARACTER_BUILDER.md) | [ ] |
| 9 | OutputTab 채널/영상 분리 | UX | [설계](../02_design/UI_PROPOSAL.md) | [x] |
| 10 | Automated Evaluation Runner | 품질 | - | [ ] |
| 11 | Studio UI Polish (Video탭 통합, Global 접기, Save 이동, 캐릭터 프리뷰 확대) | UX | - | [x] |
| 12 | 씬 텍스트 하단 배치 + 드롭섀도우 + Color Grade | 영상 품질 | - | [x] |
| 13 | Gemini 스크립트 길이 제한 강화 (30자/Korean) | 품질 | - | [x] |
| 14 | Character Identity Injection (Gemini 스토리보드에 캐릭터 태그/LoRA 주입 + 오토파일럿 overlay 수정) | 품질 | - | [x] |
| 15 | 좌측 사이드바 네비게이션 + 컨텍스트 전환 버그 수정 (P0: 그룹/프로젝트 전환 시 stale state 6건) | UX | [명세](FEATURES/SIDEBAR_NAVIGATION.md) | [ ] |

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
| Phase 1: Core | FK 강화, 캐릭터 프로젝트 스코핑, 렌더 프리셋 분리, 설정 상속 엔진, 그룹 편집 UI 완료 | [x] |
| Phase 1.5: UX 정리 | Channel Profile → Project 통합, 캐릭터 글로벌화, +New Storyboard 그룹 내부 이동, Studio UX Polish | [x] |
| Phase 1.7: Group Defaults | 그룹 cascade 확장 (language, structure, duration, narrator_voice), Manage 그룹 기본값 편집 UI. [명세](FEATURES/GROUP_DEFAULTS.md) | [ ] |
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
| Storyboard Version History | - |
| LoRA Calibration Automation | - |
| Real-time Prompt Preview (12-Layer) | - |
| 씬 순서 드래그 앤 드롭 | - |

---

## Development Cycle

```
Phase 6-5 (Stability) → 6-6 (Code Health) → 6-7 (Infra/DX) → 6-8 (Local AI) → 7-0 (ControlNet) → 7-1 (UX/Feature)
     P0/P1 Fixes          Refactoring          CI + Soft Delete      TTS/Voice       Pose Control      New Features
                                                                                                            ↓
                                                          7-2 (Project/Group) → 8 (Multi-Style)
                                                           Cascading Config          Future
```

**현재 진행 상태** (2026-02-04):
- Phase 6-5 ~ 6-8: **완료**
- Phase 7-0 (ControlNet): **완료** (ARCHIVED)
- Phase 6-7: 12/16 완료 (#1 CI, #3 GC, #4-6 Soft Delete, #7 UI Toolkit, #12 WD14 매칭, #13-15 Voice, #16 Schema Cleanup)
- Phase 7-2: Phase 1.5 **완료**, Phase 2 대기
- Phase 7-1: 6/14 완료 (#1 Quick Start, #9 OutputTab, #11 Studio UI, #12 씬 텍스트, #13 스크립트 길이, #14 Character Identity)
