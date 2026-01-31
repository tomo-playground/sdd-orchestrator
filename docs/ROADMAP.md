# Shorts Factory Master Roadmap (Strategic Fidelity Guard)

이 로드맵은 **안정성 → 리팩토링 → 안정성 → 신규 개발** 사이클을 따릅니다.
리팩토링 및 기능 추가 시 **영상 품질의 100% 일관성(Zero Variance)**을 유지하는 것을 최우선 목표로 합니다.

---

## 📦 Phase 1-4: Foundation & Refactoring - **ARCHIVED**

완료된 주요 성과 요약:
- Foundation, VRT Setup, Backend/Frontend Major Refactoring.
- 자세한 내용은 [Phase 1-4 아카이브](file:///Users/tomo/Workspace/shorts-producer/docs/archive/ROADMAP_PHASE_1_4.md)를 참조하세요.

---

## 🚀 Phase 5: 신규 개발 (High-End Production)
검증된 안정적인 기반 위에서 새로운 기능을 추가합니다.

### 5-1. 운영 효율화
| 작업 | 설명 | 상태 |
|------|------|------|
| Resume/Checkpoint | 중단된 작업 이어하기 | [x] |
| Storage Cleanup | outputs/ 자동 정리 로직 | [x] |
| Project DB (PostgreSQL) | 프로젝트 설정 및 히스토리 관리 (Phase 6-1 통합) | [x] |
| **Smart AutoRun** | Pre-flight 검증 + 선택적 실행 | [x] |

#### 5-1-2. Smart AutoRun System (🟢 완료 - 테스트 검증됨)
**목표**: 오토런 실행 전 사전 점검 및 필요한 단계만 선택적 실행

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | `runPreflight()` 함수 | 설정 검증 + 상태 분석 로직 | [x] |
| 2 | `PreflightModal` 컴포넌트 | 3섹션 UI (설정/파라미터/단계) | [x] |
| 3 | 필수/권장 검증 로직 | Topic, Character 등 필수 체크 | [x] |
| 4 | `useAutopilot` 확장 | 선택적 단계 실행 지원 | [x] |
| 5 | 진행 UI 개선 | 건너뜀/완료 상태 표시 | [x] |
| 6 | 브라우저 테스트 | Playwright 기반 E2E 검증 | [x] |

**Pre-flight 검증 항목**:
- 필수: Topic, Character
- 권장: Voice, BGM, ControlNet
- 정보: SD 파라미터, IP-Adapter

**실행 단계 최적화**:
- Storyboard: 씬 존재 시 건너뛰기
- Images: 이미지 없는 씬만 생성
- Validate: 미검증 이미지만 검증
- Render: 콘텐츠 변경 시만 재렌더

### 5-1-1. Security & Infrastructure (Hardcoding Removal)
| 작업 | 설명 | 상태 |
|------|------|------|
| **Secure Config** | `DATABASE_URL` 등 민감정보 .env 이동 | [x] |
| **Dynamic URLs** | API/SD URL 및 경로 하드코딩 제거 및 중앙화 | [x] |
| **Logic Sync** | 프론트/백엔드 로직 중복 제거 (Priority 중앙화) | [x] |
| **Frontend Config** | `next.config.ts` IP 등 하드코딩 제거 | [x] |

### 5-2. 영상 품질 강화 - **COMPLETE**
| 작업 | 설명 | 상태 |
|------|------|------|
| Pixel-based Subtitle Wrapping | 폰트 기반 자막 줄바꿈 및 동적 크기 조절 | [x] |
| Professional Audio Ducking | 내레이션-BGM 볼륨 자동 조절 (sidechaincompress) | [x] |
| Ken Burns Effect | 정지 이미지에 줌/팬 효과 (10개 프리셋, slow_zoom 제거됨) | [x] |
| **Random BGM** | `bgm_file: "random"` → Backend에서 랜덤 선택 | [x] |
| **Resolution Optimization** | 512x768 (2:3) 표준화 + Cowboy Shot 전략 (Post/Full 겸용) | [x] |
| **Full Layout Polishing** | 검은 여백 제거 (YouTube Shorts 스타일, Cover 스케일) | [x] |
| **Subtitle Animation** | Fade in/out (0.3초, 알파 채널 fade) | [x] |
| **Advanced Transitions** | 13개 씬 전환 효과 (fade, wipe, slide, circle, random) | [x] |
| **Dynamic Subtitle Position** | 이미지 복잡도 기반 자동 Y 위치 조정 (하단 분석) | [x] |
| **Overlay Animation** | 헤더/푸터 슬라이드 인 효과 (0.5초, 상하 분리) | [x] |
| **Ken Burns Vertical Presets** | Full Layout 최적화 프리셋 6종 (pan_up_vertical 등, Y축 2배 확장) | [x] |
| Character Consistency | → Phase 6 (LoRA 기반) → Phase 7 (IP-Adapter) | [-] |

### 5-3. 콘텐츠 확장
| 작업 | 설명 | 상태 |
|------|------|------|
| Preset System | 구조별 템플릿 및 샘플 토픽 시스템 | [x] |
| Sample Topics UI | Structure별 샘플 토픽 선택 UI | [x] |
| Japanese Language Course | 일본어 강좌 전용 템플릿 | [x] |
| Math Lesson Course | 초/중/고 수학 공식 강좌 템플릿 | [x] |

#### 5-4. Prompt Quality & Analytics (🟢 완료)
- 정량적 품질 지표 자동화 및 Gemini 프롬프트 검증 시스템 구축 완료.
- 상세 이력은 [Analytics 시스템 아카이브](file:///Users/tomo/Workspace/shorts-producer/docs/archive/ROADMAP_ANALYTICS_SYSTEM.md)를 참조하세요.

#### 5-4-3. 확장 기능 (v1.x Backlog)
| 작업 | 설명 | 상태 |
|------|------|------|
| VEO Clip | Video Generation 통합 | [ ] |

### 5-5. UI/UX 개선
| 작업 | 설명 | 상태 |
|------|------|------|
| SetupPanel 제거 | 간소화 진입점 제거, Custom Start로 통합 | [x] |
| SD 파라미터 Advanced 이동 | steps, cfg_scale 등 고급 설정화 | [x] |
| **Media Defaults** | BGM/Motion/Transition 기본값 Random 설정 | [x] |
| 간소화 진입점 재설계 | Phase 6 완료 후 Quick Start 재정의 | [ ] |
| **Render UX 개선** | 컴팩트 레이아웃 토글 + 단일 Render 버튼, Video+Audio→Media Settings 통합 | [x] |

### 5-6. UI Polish (완성도 향상)
| 작업 | 설명 | 상태 |
|------|------|------|
| **Loading/Error UI** | 스피너, 프로그레스 바, 에러 메시지 디자인 개선 | [x] |
| **Character Image Modal** | Manage > Characters 섬네일 클릭 시 확대 모달 | [x] |
| Setup Wizard | 초기 설정 및 에셋 상태 확인 UI | [ ] |

### 5-7. Quality Assurance (Test Coverage)
**Goal**: Core Rule #9, #10 (TDD)에 따라 테스트 커버리지 80% 달성.

| 작업 | 설명 | 상태 |
|------|------|------|
| **Backend API Test** | FastAPI 라우터 통합 테스트 (TestClient) | [x] |
| **Frontend Test Init** | Vitest + React Testing Library + Playwright VRT 환경 구축 | [x] |
| **Ken Burns Unit Test** | `services/motion.py` 27개 테스트 (TDD) | [x] |
| **Core Hooks Test** | `useAutopilot` 27개 테스트 (~95% 커버리지) | [x] |
| **CI Script** | 로컬 테스트 자동화 스크립트 (`./run_tests.sh`) | [x] |

**현재 테스트 현황** (2026-01-27):
- Backend: 335 passed, 5 skipped (generation_logs 17개 추가)
- Frontend: 67 passed (validation 30개, useAutopilot 27개, LoadingSpinner 3개, QualityDashboard 7개)
- **총 402개 테스트**
- 주요 테스트: VRT (36개), API (키워드/프리셋/IP-Adapter), 프롬프트 품질, Ken Burns (27개), BGM (9개)
- IP-Adapter 테스트 (16개): CLIP 모델 선택, Reference 이미지 로드, 페이로드 구성, 상수 검증
- **useAutopilot 테스트** (27개): 상태 관리, 로그, 취소/재개, 체크포인트, 진행률 계산, 통합 플로우
- **Validation 테스트** (48개):
  - Frontend (30개): 씬 검증, 수정 제안, 프롬프트 품질 체크
  - Backend (18개): 태그 비교, match rate 계산, skip 로직
- **Quality 테스트** (16개): batch-validate, summary, alerts API (empty/missing/threshold)
- **Prompt Validation 테스트** (14개): tag validation, auto-replace, Danbooru integration
- **Generation Logs 테스트** (17개): CRUD, pattern analysis, success combinations (3개 신규)

---

## 🎭 Phase 6: Character & Prompt System (v2.0)
다중 캐릭터 지원 및 프롬프트 빌더 시스템 구축.

**현재 사용 환경**:
- **Model**: `animagine-xl.safetensors` (SDXL anime)
- **LoRA**: `eureka_v9`, `chibi-laugh`
- **Negative Embeddings**: `verybadimagenegative_v1.3`, `easynegative`
- **Presets**: 9종 (Generic Girl/Boy, Eureka, Midoriya, Chibi, Blindbox 계열)

### 6-1. Data Foundation - **COMPLETE**
| 작업 | 설명 | 상태 |
|------|------|------|
| DB 스키마 설정 | PostgreSQL + SQLAlchemy + Alembic | [x] |
| 태그 마이그레이션 | 262개 태그 (identity, clothing, scene, meta) | [x] |
| Backend CRUD API | /tags, /loras, /characters, /sd-models 엔드포인트 | [x] |

### 6-2. Studio Integration - **COMPLETE**
| 작업 | 설명 | 상태 |
|------|------|------|
| Character Preset UI | 드롭다운 → Identity + Clothing + LoRA + Negative 자동 적용 | [x] |
| Multi-LoRA 지원 | 캐릭터당 여러 LoRA 조합 (eureka + chibi) | [x] |
| Style Profile 통합 | Character Preset으로 단일화, UI 제거 | [x] |

### 6-2.5. V3 Core Architecture Transition - **COMPLETE** (2026-01-28~30)
16커밋, 275파일 변경 (+12,980/-6,320줄). Storyboard-Centric + DB-Driven 아키텍처 전면 전환.

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | **Storyboard-Centric 전환** | Project → Storyboard → Scene → CharacterAction 계층 | [x] |
| 2 | **V3 Relational Tags** | character_tags, scene_tags, scene_character_actions 연관 테이블 | [x] |
| 3 | **Keywords 서비스 모듈화** | `keywords/` 패키지 8개 모듈 (core, db, db_cache, formatting, patterns, processing, suggestions, sync, validation) | [x] |
| 4 | **Prompt V3 서비스** | `prompt/` 패키지 + 12-Layer PromptBuilder (v3_composition, v3_service) | [x] |
| 5 | **4개 런타임 캐시** | TagCategory, TagAlias, TagRule, LoRATrigger (startup frozen 초기화) | [x] |
| 6 | **DB-Driven 완전 전환** | 하드코딩 충돌규칙/태그별칭/필터 → tag_rules, tag_aliases, tag_filters 테이블 | [x] |
| 7 | **Alembic V3 Baseline** | 15개 마이그레이션 → 1개 기준점 통합 (clean slate) | [x] |
| 8 | **Activity Logs 통합** | generation_logs → activity_logs 통합 (생성+즐겨찾기), project_name 제거 | [x] |
| 9 | **Frontend Gemini 제거** | Gemini 직접 호출 제거, Backend API 경유로 통일 | [x] |
| 10 | **FastAPI Lifespan** | `on_event("startup")` → `asynccontextmanager` lifespan 패턴 | [x] |
| 11 | **신규 라우터** | admin (DB 관리/캐시 리프레시), assets (미디어), keywords (태그 API) | [x] |
| 12 | **코드베이스 경량화** | 미사용 템플릿(일본어/수학)/프리셋 제거, Danbooru 태그 표준 전면 적용 | [x] |
| 13 | **모델 필드 재배치** | Character, LoRA, Tag, PromptHistory 등 논리적 그룹별 정렬 | [x] |

### 6-3. Scene Expression & Multi-Character (🟡 확장)

**8.x Gender System - ARCHIVED** (6개 완료):
Character gender 필드, LoRA gender_locked, Gender 기반 UI 잠금/필터링, Preview UI

**9.x Scene Expression System - ARCHIVED** (25개 완료):
- DB 태그 통합, 포즈/표정/구도 확장, Gemini 템플릿, Prompt Quality
- Prompt Sanity Check, Prompt Composition Mode A/B

| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 10 | Multi-Character 지원 | A, B, C... 다중 캐릭터 구조 (DB 스키마 완료, UI 대기) | [ ] |
| 11 | Scene Builder UI | 장면별 배경/시간/날씨 컨텍스트 태그 선택 (DB 스키마 완료, UI 대기) | [ ] |
| 12 | **Tag Autocomplete** | Danbooru 스타일 태그 자동완성 (Backend API + Frontend UI) | [x] |

### 6-4. Advanced Features (🔵 고급)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 13 | Civitai 연동 | LoRA 메타데이터 자동 가져오기 (MCP 활용) | [x] |
| 14 | Visual Tag Browser | 태그별 예시 이미지 표시 | [ ] |
| 15 | Tag Usage Analytics | 사용 빈도, 성공/실패 패턴 추적 (기본 구현: 9.1.1) | [~] |
| 15.1 | Batch Tag Approval | confidence >= 0.7 태그 일괄 승인 (미리보기 + 선택적 승인) | [x] |
| 15.2 | **Tag Categorization V2** | SD Priority 기반 분류체계 개편 (24개 카테고리, environment 세분화) | [x] |
| 15.3 | **Tag Conflict/Requires Rules** | 태그 충돌(57쌍)/의존성(29개) 규칙 + 검증 API | [x] |
| 15.4 | **LoRA Trigger Sync** | LoRA trigger words → tags 테이블 자동 동기화 API | [x] |
| 15.5 | **Tag Gap Analysis & Expansion** | CATEGORY_PATTERNS→DB 동기화 (515→924개, +409) | [x] |
| 15.6 | **Quality Evaluation System** | Mode A/B 비교 검증 시스템 | [x] |
| 15.6.1 | 표준 테스트 프롬프트 세트 | 6개 테스트 시나리오 정의 | [x] |
| 15.6.2 | evaluation_runs 테이블 | 결과 저장 스키마 + 마이그레이션 | [x] |
| 15.6.3 | /eval/run API | 테스트 실행 엔드포인트 | [x] |
| 15.6.4 | /eval/results, /eval/summary API | 결과 조회/비교 | [x] |
| 15.6.5 | 대시보드 시각화 | /manage Eval 탭 (Mode A vs B 차트) | [x] |
| **15.7** | **Dynamic Tag Classification** | 하드코딩 제거, DB+Danbooru+LLM 하이브리드 분류 | [x] |
| 15.7.1 | classification_rules 테이블 | 패턴 규칙 DB화 (CATEGORY_PATTERNS 이관) | [x] |
| 15.7.2 | /tags/classify API | 배치 분류 엔드포인트 (DB→Rules fallback) | [x] |
| 15.7.3 | Danbooru API 연동 | 태그 카테고리 조회 (General 세분화용 LLM 호출) | [x] |
| 15.7.4 | Frontend 통합 | useTagClassifier 훅 + API 호출 (로컬 패턴 fallback) | [x] |
| 15.7.5 | 승인 워크플로우 | LLM 분류 결과 검토/승인 UI | [x] |
| 15.7.6 | WD14 피드백 루프 | 생성 이미지 태그 vs 프롬프트 태그 비교 → 분류 정확도 검증 | [x] |
| 15.7.7 | **카테고리 한국어 설명** | CATEGORY_DESCRIPTIONS 상수, UI 메타정보 표시 | [x] |
| 15.7.8 | **분류 테스트 케이스** | 109개 회귀 방지 테스트 (clothing, hair, camera 등) | [x] |
| **15.8** | **Location Tag Priority & Conflict** | 장소 태그 우선순위 및 충돌 해결 시스템 | [x] |
| 15.8.1 | patterns.py 데이터 정합성 | Danbooru 미존재 태그 제거 (room, interior) | [x] |
| 15.8.2 | CATEGORY_PRIORITY 추가 | location_indoor_specific(11) > general(12) 우선순위 정의 | [x] |
| 15.8.3 | Two-Pass 필터링 로직 | 우선순위 기반 충돌 해결 (순서 무관, bedroom > indoors) | [x] |
| 15.8.4 | Gemini 템플릿 강화 | 금지 태그 명시 + 우선순위 규칙 (library OR cafe, NOT both) | [x] |
| 15.8.5 | DB 비활성 플래그 시스템 | is_active, deprecated_reason, replacement_tag_id 필드 추가 | [x] |
| 15.8.6 | Admin API 태그 관리 | /admin/tags/deprecated, deprecate, activate 엔드포인트 | [x] |
| 16 | Prompt History | 성공한 프롬프트 저장/재사용 | [x] |
| 16.1 | DB 모델 | `prompt_histories` 테이블 (JSONB: lora_settings, context_tags) | [x] |
| 16.2 | CRUD API | `/prompt-histories` 엔드포인트 (목록/상세/생성/수정/삭제) | [x] |
| 16.3 | 특수 API | toggle-favorite, apply (use_count++), update-score (WD14 연동) | [x] |
| 16.4 | /manage 탭 | Prompts 탭 UI (필터: 즐겨찾기/캐릭터/검색, 정렬: 최신/사용횟수/점수) | [x] |
| 16.5 | Save 버튼 | SceneCard에서 현재 프롬프트 저장 기능 | [x] |
| 16.6 | Apply 기능 | 저장된 프롬프트를 씬에 적용 (localStorage → 메인 페이지) | [x] |
| 16.7 | WD14 피드백 | 이미지 검증 시 match_rate 자동 업데이트 (avg_match_rate 누적) | [x] |
| 16.8 | Draft 영속성 | prompt_history_id 저장/복원 지원 | [x] |
| 17 | Feedback Loop | WD14 기반 태그 효과성 피드백 → **16.7에서 구현 완료** | [x] |
| 18 | Profile Export/Import | Style Profile 공유 | [ ] |
| 19 | Character Builder UI | 조합형 캐릭터 생성 (Gender + Appearance + LoRA) | [ ] |
| 20 | Scene Clothing Override | 장면별 의상 변경 기능 | [ ] |

#### 6-4.21. Generation Log Analytics (🟢 완료)
- 성공/실패 패턴 분석 및 데이터 기반 충돌 규칙 자동 제안 시스템. [상세 내용](file:///Users/tomo/Workspace/shorts-producer/docs/archive/ROADMAP_ANALYTICS_SYSTEM.md)

#### 6-4.22. Gemini Image Editing System (진행 중)
- Match Rate 낮은 씬에 대해 Gemini Nano Banana를 활용한 직접 이미지 편집. [상세 내용](file:///Users/tomo/Workspace/shorts-producer/docs/archive/ROADMAP_ANALYTICS_SYSTEM.md)

#### 6-4.30. Style Profile System (진행 중)

**목표**: Model + LoRAs + Embeddings를 세트로 관리하는 Profile 시스템 구축

**배경**:
- LoRA는 특정 모델에 종속적 (SD 1.5 ≠ SDXL)
- 화풍별로 Model/LoRA/Embeddings/Prompt가 세트로 구성되어야 함
- 애니메이션, 리얼리스틱, 일러스트 등 스타일별 일관된 설정 필요

**Phase 1: 핵심 구조 개편** (완료 ✅)

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | Manage > Style 탭 개편 | Profile 중심 계층 구조, Assets 하위 배치 | [x] |
| 2 | Profile 선택 플로우 | Studio 진입 시 Style Profile 선택 모달 | [x] |
| 3 | Output Tab 간소화 | ADVANCED → CURRENT STYLE 섹션 (읽기 전용) | [x] |
| 4 | Profile 세트 관리 | Model/LoRA/Embeddings 그룹 일관성 보장 | [x] |
| 5 | Frame Style 이동 | 채널 프로필 → RenderSettings (영상별 설정) | [x] |

**Phase 2: Civitai 간편 연계** (대기)

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 6 | Profile 생성 옵션 | From Scratch / From Template / From Civitai | [ ] |
| 7 | Civitai 검색 | 스타일 카테고리별 모델 검색 | [ ] |
| 8 | 자동 LoRA 추천 | 선택한 모델에 호환되는 LoRA 추천 | [ ] |
| 9 | 원클릭 다운로드 | Model + LoRA + Embeddings 세트 다운로드 | [ ] |

**Phase 3: 스마트 기능** (나중)

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 10 | 호환성 자동 체크 | SD 1.5 vs SDXL 자동 필터링 | [ ] |
| 11 | 커뮤니티 큐레이션 | 인기 조합 추천 (Most Used Combinations) | [ ] |
| 12 | Profile Import/Export | 프로필 공유 기능 | [ ] |
| 13 | 자동 업데이트 | Civitai 신버전 알림 | [ ] |

**아키텍처**:
```
Style Profile (세트)
├─ Model: anythingV3_fp16.safetensors
├─ LoRAs: [anime_face (0.8), anime_bg (0.6)]
├─ Embeddings: [anime_quality]
└─ Default Prompt: "anime style, vibrant colors"
```

#### 6-4.31. Asset Management & Storage Optimization - **IN PROGRESS**
**목표**: 객체 스토리지(MinIO) 기반의 3단계 계층 구조 및 중앙 집중식 에셋 관리 시스템 구축

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | **3단계 계층 모델링** | Project(채널) > Group(시리즈) > Storyboard(영상) DB 모델 확립 | [x] |
| 2 | **Media Asset Registry** | `media_assets` 테이블을 통한 모든 파일 메타데이터(크기, 타입, 경로) 추적 | [x] |
| 3 | **MinIO S3 통합** | 단일 버킷(`shorts-producer`) + Prefix 기반 경로 구조 및 Public 접근 정책 설정 | [x] |
| 4 | **Storage Driver (S3/Local)** | 코드 내 물리 경로 의존성 제거를 위한 추상화 드라이버(`StorageService`) | [x] |
| 5 | **FFmpeg 스마트 캐싱** | 렌더링 시 원격 에셋 자동 인출(fetch) 및 로컬 캐시 관리 | [x] |
| 6 | **서비스 레이어 통합** | `VideoBuilder`, `AvatarService`, `CleanupService` 통합 완료 | [x] |
| 7 | **Shared Assets 통합** | BGM, 폰트 등 정적 리소스의 중앙 스토리지 관리 | [ ] |

**아키텍처**:
- **Hierarchy**: `projects/{p_id}/groups/{g_id}/storyboards/{s_id}/{type}/{filename}`
- **Storage**: MinIO (S3 API) + Public Read Policy (Serving 최적화)
- **Logic**: DB 기반 존재 여부 확인 → 필요 시 원격 다운로드/캐싱 → 렌더링

---

---

## 🔮 Phase 7: ControlNet & Pose Control - **ARCHIVED** ✅
- ControlNet 포즈 제어, IP-Adapter 캐릭터 일관성 시스템 구축 완료.
- 자세한 내용은 [Phase 1-4 아카이브](file:///Users/tomo/Workspace/shorts-producer/docs/archive/ROADMAP_PHASE_1_4.md) 또는 관련 보고서를 참조하세요.

---

## 🔮 Phase 8: Multi-Style Architecture (Future)
**목표**: Anime, Realistic, 3D 등 다양한 화풍 지원을 위한 유연한 파이프라인 구축.

**점진적 진화 전략 (Gradual Evolution Strategy)**:

### 8-1. Hardcoding Removal (🟢 태그 시스템 완료)
- ✅ 태그 충돌규칙/별칭/필터 → DB 전환 완료 (6-2.5)
- ✅ `masterpiece`, `anime style` 등 화풍 종속 태그 Config 분리
- 상수/Config로 분리하여 `DEFAULT_QUALITY_TAGS`, `DEFAULT_STYLE_TAGS` 등 활용.

### 8-2. Config-based Switching (Mid-term)
- UI 변경 없이 `.env` 설정만으로 모델 스타일 전환 지원.
- 모델 타입(Anime/Realistic)에 따라 태그/파라미터(CFG, Sampler) 자동 분기 로직 구현.

### 8-3. Full Integration (Long-term)
- **UI**: 스타일 선택 드롭다운 (Anime / Realistic / 3D).
- **DB**: `StyleProfile`에 모델별 최적 파라미터(VAE, CFG, Clip Skip) 저장 스키마 확장.
- **Logic**: 실시간 모델 스위칭, ADetailer 자동화, VAE 교체 로직.

---

## 📋 Development Cycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   안정성      │ ──▶ │   리팩토링    │ ──▶ │   안정성      │ ──▶ │   신규 개발   │
│   구축       │     │   (VRT 통과)  │     │   검증       │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                     ◀──────────────────────────────────────────────────
                                    (반복)
```

---

## 🤖 Agent Evolution Guidelines

현재 에이전트 구성이 충분하지 않은 시점을 정의합니다.

### Test Engineer Agent 추가 시점

**트리거 조건** (하나 이상 충족 시 추가 검토):
| 조건 | 설명 | 현재 상태 |
|------|------|----------|
| Unit Test 구축 | Backend/Frontend unit test 30개 이상 | ❌ 미구축 |
| E2E Test 구축 | Playwright E2E 시나리오 10개 이상 | ❌ 미구축 |
| CI/CD 도입 | GitHub Actions 테스트 파이프라인 | ❌ 미구축 |
| 테스트 복잡도 | 테스트 파일 총 1,000줄 초과 | ❌ 해당없음 |

**역할 정의** (추가 시):
- 테스트 코드 작성/유지보수
- 테스트 커버리지 관리 (목표: 80%+)
- CI/CD 파이프라인 테스트 설정
- 테스트 관련 commands 관리 (`/test`, `/coverage`)

**현재 대안**:
- VRT: `/vrt` command + qa-validator
- 이미지 품질: qa-validator
- 수동 테스트: 일반 개발 과정에서 처리

### 기타 Agent 추가 고려

| Agent | 트리거 조건 | 현재 필요성 |
|-------|------------|------------|
| **DevOps Engineer** | Docker/K8s 배포, 모니터링 시스템 구축 시 | ❌ 불필요 |
| **Security Auditor** | 외부 사용자 접근, 인증 시스템 도입 시 | ❌ 불필요 |
| **Data Engineer** | 대용량 데이터 파이프라인, 분석 시스템 구축 시 | ❌ 불필요 |

### Claude Squad 도입 시점

**Claude Squad**: 여러 Claude Code 인스턴스를 병렬로 관리하는 도구 (tmux + git worktree 기반)

**트리거 조건** (하나 이상 충족 시 도입 검토):
| 조건 | 설명 | 현재 상태 |
|------|------|----------|
| 팀 확장 | 2명 이상 동시 개발 | ❌ 솔로 |
| 독립 작업 | Backend/Frontend 완전 분리 작업 필요 | ❌ 순차 진행 |
| 대규모 리팩토링 | 10+ 파일 동시 수정 필요 | ❌ 해당없음 |
| 긴급 핫픽스 | 메인 작업 중 별도 브랜치 작업 빈번 | ❌ 해당없음 |
| Phase 병렬화 | 의존성 없는 Phase 동시 진행 | ❌ 순차 의존성 |

**도입 시 이점**:
- 여러 작업 병렬 실행 (대기 시간 감소)
- git worktree로 브랜치 충돌 방지
- 백그라운드 자동 완료 (yolo 모드)

**현재 대안**:
- Sub Agents: 전문성 분리 (단일 세션 내)
- 순차 작업: 의존성 있는 Phase는 순서대로

**설치** (도입 시):
```bash
brew install claude-squad  # 명령어: cs
```

**참조**: https://github.com/smtg-ai/claude-squad

---

**Core Mandate**: "No changes in output without explicit intention."
(의도하지 않은 결과물의 변화는 허용하지 않는다.)

---

#### 6-4.29. Video Persistence & UI Tab Optimization - **COMPLETE** (2026-01-30)
스토리보드별 영상 독립 관리 및 '캐릭터 중심' 작업 흐름을 위한 UI 최적화.

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | **영상 영구 저장 (DB)** | Storyboard 모델에 `video_url`, `recent_videos_json` 추가 + Alembic 마이그레이션 | [x] |
| 2 | **스토리보드별 영상 로드** | 릴로드/탭 전환 시 해당 스토리보드에 귀속된 영상만 표시 (상태 꼬임 해결) | [x] |
| 3 | **UI 탭 순서 최적화** | Plan 서브탭 순서 변경 (캐릭터 → 스토리) + 캐릭터 탭 기본 활성화 | [x] |
| 4 | **Prompt Helper 복구** | page.tsx 사이드바 통합 및 텍스트 분할/복사 액션 연결 | [x] |

---

### 세션 이력
- **2026-01-28**: ROADMAP 다이어트 (1500줄→800줄), WD14 단일 검증 표준화, 코드베이스 경량화
- **2026-01-28~30**: V3 Core Architecture 전환 (16커밋, 275파일, +12,980/-6,320줄) → 6-2.5 기록
- **2026-01-30**: project_name 잔존 참조 정리 (스크립트 4개 + 프론트엔드 + 문서), 모델 필드 재배치, 로드맵 전면 정리
- **2026-01-30**: **영상 중복 표시 수정**, 탭 순서 변경 (캐릭터 우선), **프롬프트 헬퍼 복구**, DB 마이그레이션(v3.1)

---

#### 6-4.22. Gemini Image Editing System
Phase 1~1.7 완료 (MVP Pose + Expression/Gaze + 자동 제안). [실험 결과 상세](archive/ROADMAP_V3_EXPERIMENTS.md)
- 시각적 성공률 100%, 비용 $0.04/edit, WD14 평가 한계 확인

**Phase 2: 자동화 (다음 작업)**:
| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 22.13 | `auto_edit_with_gemini()` | 실패 태그 분석 → 편집 타입 자동 선택, 승인 없이 실행 | [ ] |
| 22.14 | 임계값 config | `GEMINI_AUTO_EDIT_THRESHOLD` 설정 | [ ] |
| 22.15 | Fallback 이력 추적 | activity_logs.gemini_edited 플래그 | [ ] |
| 22.16 | Analytics 대시보드 | Before/After Match Rate 시각화, 편집 타입별 성공률 | [ ] |

**Phase 3: 학습 기반 최적화 (장기)**:
| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 22.17 | 성공 패턴 추출 | `/activity-logs/success-patterns` 캐릭터별 조합 학습 | [ ] |
| 22.18 | Rule-based 사전 개선 | 위험 태그 자동 대체 엔진 (medium_shot → cowboy_shot) | [ ] |
| 22.19 | Gemini 의존도 감소 | 사전 개선으로 실패율 자체 감소 → 비용 90% 절감 | [ ] |

#### 6-4.23. Character Consistency System - **IN PROGRESS**
실험 90% 성공, Reference-only ControlNet 채택. [실험 결과 상세](archive/ROADMAP_V3_EXPERIMENTS.md)

**프로덕션 통합** (23.6~23.8 완료, 23.9 남음):
| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 23.6 | Character Prompt SSOT & Reference Fields | Custom Prompt + Reference Prompt 필드 | [x] |
| 23.7 | Backend API 확장 | `generate_with_character_preset()`, Reference-only 자동 적용 | [x] |
| 23.8 | Frontend UI | Preset 드롭다운, Reference On/Off, Weight 슬라이더 (0.5~1.0) | [x] |
| 23.9 | Multi-Character 시스템 | 장면 유형 자동 판단, LoRA weight 자동 조절 | [ ] |

**완료 (2026-01-30)**: 단일 캐릭터 IP-Adapter 자동 적용, character_id 추적 (Phase 6-4.26)

#### 6-4.24. Character Tag Auto-Suggestion - **COMPLETE**
- Base Prompt → DB 태그 매칭 → 카테고리별 자동 제안 (identity/clothing)
- `/characters/suggest-tags` API + Frontend onBlur 자동 제안 UI

#### 6-4.25. Tag DB Integrity Cleanup - **COMPLETE** (2026-01-30)
DB 정합성 점검에서 발견된 3건의 데이터/로직 오류 일괄 수정.

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | 공백 태그 4건 삭제 | 언더바 버전과 중복된 공백 형식 태그 제거 (미사용) | [x] |
| 2 | 자기참조 alias 2건 삭제 | source=target인 무의미한 tag_aliases 제거 | [x] |
| 3 | **category 정규화 (58건)** | 비표준 category를 character/scene/meta 3종으로 통일 | [x] |
| 4 | **subcategory 제거** | 73.6% 오분류 데이터 전체 NULL + 코드에서 우선순위 로직 제거 | [x] |

**근거**: subcategory가 `_map_db_category()` 1순위로 사용되나 정확도 20.2% (292건 중 59건만 정확).
`bare_arms`=indoor, `cloud`=indoor 등 오분류로 인해 프롬프트 레이어 배치 오류 발생.
`group_name`이 95%+ 정확도로 완전 대체 가능하므로 subcategory 의존성 제거.

#### 6-4.26. DB Schema Cleanup & Test Isolation - **COMPLETE** (2026-01-30)
불필요한 DB 컬럼 제거, character_id 활성화, 테스트 DB 격리 구현.

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | **character_id 활성화** | activity_logs에 character_id 자동 저장, IP-Adapter reference로 자동 설정 | [x] |
| 2 | **불필요 컬럼 제거 (7개)** | tags.subcategory, tag_rules category 필드, activity_logs favorite 필드 | [x] |
| 3 | **더미 데이터 정리** | activity_logs 184건, storyboards 150건 삭제 (테스트 잔여물) | [x] |
| 4 | **테스트 DB 격리** | SQLite in-memory DB 사용, 프로덕션 DB 보호, 10배 속도 향상 | [x] |

**영향**:
- Character Consistency 사용 시 character_id 자동 추적 (analytics 가능)
- DB 스키마가 실제 사용 패턴과 일치 (7개 미사용 컬럼 제거)
- 테스트가 프로덕션 DB를 오염시키지 않음 (0 쓰레기 데이터)
- 테스트 속도 10배 향상 (SQLite in-memory)

**파일**:
- `routers/activity_logs.py`, `services/generation.py` (character_id)
- `models/tag.py`, `models/activity_log.py` (컬럼 제거)
- `tests/conftest.py`, `tests/test_db_isolation.py` (DB 격리)

#### 6-4.27. Studio Tab-based Workflow - **COMPLETE** (2026-01-30)
2,751줄 모놀리식 page.tsx를 multi-route 4-tab 워크스페이스로 재구조화.

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| A | **Backend CRUD** | Scene 모델 11컬럼 확장, GET/PUT/DELETE 엔드포인트, Alembic 마이그레이션 | [x] |
| B | **Zustand + Routing** | 4슬라이스 스토어 (plan/scenes/output/meta), `/` `/studio` `/manage` 3-route | [x] |
| C | **Tab Components** | PlanTab, ScenesTab, OutputTab, InsightsTab 커넥터 + Action 파일 추출 | [x] |
| D | **Manage Cleanup** | Storyboards/Quality/Analytics/Characters 탭 제거 (Home/Studio로 이관) | [x] |

**Action 파일** (C3):
- `promptActions.ts` — buildPositivePrompt, buildScenePrompt, buildNegativePrompt
- `imageActions.ts` — generateSceneImageFor, generateSceneCandidates, handleEditWithGemini
- `sceneActions.ts` — validation, autofix, mark success/fail, save prompt
- `autopilotActions.ts` — runAutoRunFromStep 파이프라인

**결과**: 26 files changed, ~2,900 insertions, ~2,900 deletions (net 0 변경).
모놀리식 → 구조화, 모든 stub 콜백 실제 로직 연결, 8/8 backend 테스트 통과.

#### 6-4.28. Channel Profile & Branding System - **COMPLETE** (2026-01-30)
채널 아이덴티티 관리 및 영상 렌더링 통합 시스템.

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| A | **Channel Profile Store** | Zustand profileSlice: channelProfile, channelAvatarUrl, persist | [x] |
| B | **ChannelProfileModal** | 채널명, 아바타 선택, 프레임 스타일 설정 UI | [x] |
| C | **Global TabBar Integration** | 모든 탭에서 접근 가능한 채널 프로필 버튼 | [x] |
| D | **Onboarding Flow** | 첫 진입 시 자동 모달 표시 (1회만) | [x] |
| E | **Avatar Unification** | channelAvatarUrl 단일 소스, SNS/POST 아바타 일관성 | [x] |
| F | **DB Character Integration** | DB 캐릭터 목록 조회, 물리적 파일 제거 | [x] |
| G | **Video Metadata Separation** | 채널(고정) vs 영상(가변) 정보 분리 | [x] |
| H | **Rendering Integration** | SNS Overlay, Post Card에 채널 프로필 자동 적용 | [x] |

**아키텍처**:
```
채널 프로필 (고정 브랜딩)          영상 메타데이터 (스토리별)
├─ 채널명: "레즈바이트"            ├─ 캡션: "내가 좋아하는 게임"
├─ 아바타: Harukaze Doremi        └─ 좋아요: "10K"
└─ 프레임 스타일: Minimal
         ↓
    모든 영상에 자동 적용
```

**사용자 가치**:
- 채널 브랜딩 일관성 (YouTube 채널처럼)
- 한 번 설정 → 모든 영상 재사용
- SNS/POST 자동 오버레이

---
