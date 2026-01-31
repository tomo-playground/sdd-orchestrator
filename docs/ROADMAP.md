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

### 5-2. 영상 품질 강화
| 작업 | 설명 | 상태 |
|------|------|------|
| Pixel-based Scene Text Wrapping | 폰트 기반 씬 텍스트 줄바꿈 및 동적 크기 조절 | [x] |
| Professional Audio Ducking | 내레이션-BGM 볼륨 자동 조절 (sidechaincompress) | [x] |
| Ken Burns Effect | 정지 이미지에 줌/팬 효과 (10개 프리셋, slow_zoom 제거됨) | [x] |
| **Random BGM** | `bgm_file: "random"` → Backend에서 랜덤 선택 | [x] |
| **Resolution Optimization** | 512x768 (2:3) 표준화 + Cowboy Shot 전략 (Post/Full 겸용) | [x] |
| **Full Layout Polishing** | 검은 여백 제거 (YouTube Shorts 스타일, Cover 스케일) | [x] |
| **Scene Text Animation** | Fade in/out (0.3초, 알파 채널 fade) | [x] |
| **Advanced Transitions** | 13개 씬 전환 효과 (fade, wipe, slide, circle, random) | [x] |
| **Dynamic Scene Text Position** | 이미지 복잡도 기반 자동 Y 위치 조정 (하단 분석) | [x] |
| **Overlay Animation** | 헤더/푸터 슬라이드 인 효과 (0.5초, 상하 분리) | [x] |
| **Ken Burns Vertical Presets** | Full Layout 최적화 프리셋 6종 (pan_up_vertical 등, Y축 2배 확장) | [x] |
| **Ken Burns + Scene Text Sync** | Full: 켄번 효과 **후** 합성 (자막 선명+고정), Post: 카드에 직접 렌더링 | [x] |
| **Post Layout Scene Text Fix** | compose_post_frame에 scene_text_area 렌더링 코드 추가 (2026-01-31) | [x] |
| **Full Layout Improvements** | 씬 텍스트 크기/위치 최적화 + 크롭 위치 명시 (4개 작업) | [x] |
| Character Consistency | → Phase 6 (LoRA 기반) → Phase 7 (IP-Adapter) | [-] |

#### 5-2.8. Full Layout Improvements (완료)
**목표**: YouTube Shorts 표준 부합 및 전신 샷 최적화 (씬 텍스트 가독성 + 크롭 안정성)

**이미지 해상도**: 512x768 유지 (VRAM 8GB 환경 고려)

| # | 작업 | 파일 | 변경 내용 | 상태 |
|---|------|------|----------|------|
| 1 | 씬 텍스트 크기 증가 | `backend/constants/layout.py:31-32` | `SCENE_TEXT_FONT_RATIO: 0.034→0.042` (65px→81px)<br>`SCENE_TEXT_MIN_FONT_RATIO: 0.026→0.032` (50px→61px) | [x] |
| 2 | 씬 텍스트 위치 하향 | `backend/constants/layout.py:34-35` | `SCENE_TEXT_Y_SINGLE_LINE_RATIO: 0.72→0.85`<br>`SCENE_TEXT_Y_MULTI_LINE_RATIO: 0.70→0.82` | [x] |
| 3 | 크롭 위치 명시 | `backend/services/video.py:705-711` | FFmpeg crop 필터에 Y축 위치 추가<br>`crop=w:h:0:(ih-oh)*0.3` | [x] |
| 4 | Layout 상수 추가 | `backend/constants/layout.py` | `CROP_Y_RATIO: float = 0.3` 추가 | [x] |

**예상 소요 시간**: 40분 (수정 18분 + 테스트 22분)

**DoD**:
- [ ] 4개 파일 수정 완료 (~8줄)
- [ ] 테스트 영상 생성
- [ ] 자막 하단 15-18% 위치 확인
- [ ] 전신 샷 머리 보존 확인
- [ ] 자막 크기 81px 확인

**검증 계획**:
1. Visual Test: 자막 크기/위치 시각적 확인
2. VRT: 크롭 위치 변경 전후 비교
3. Full Render: 실제 스토리보드 렌더링 테스트

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
<!-- (생략) -->

#### 6-4.31. Asset Management & Storage Optimization - **COMPLETE** (2026-01-31)
**목표**: 객체 스토리지(MinIO) 기반의 3단계 계층 구조 및 중앙 집중식 에셋 관리 시스템 구축
(상세 내용은 위와 동일)

---

#### 6-4.32. Data-Driven Pose Expansion - **COMPLETE** (2026-01-31)
**목표**: DB 사용 데이터를 분석하여 누락된 핵심 포즈를 보강하고 감지 로직 고도화.

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | **Pose Audit** | 924개 태그 분석 및 핵심 포즈 32종 정의 | [x] |
| 2 | **Gemini Pose Expansion** | "pointing forward", "covering face" 등 신규 포즈 생성 및 라이브러리 확장 | [x] |
| 3 | **Detection Logic** | WD14 결과와의 매칭 로직 고도화 | [x] |

---

#### 6-4.23. Character Consistency System - **COMPLETE** (2026-01-31)
**목표**: V3 12-Layer Prompt Engine, Dual ControlNet, IP-Adapter를 결합하여 캐릭터와 배경의 영속성을 보장.

**프로덕션 통합 완료**:
| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | **Character Prompt SSOT** | Custom Prompt + Reference Prompt DB화 | [x] |
| 2 | **Automated IP-Adapter** | 캐릭터 선택 시 IP-Adapter + Reference 자동 적용 | [x] |
| 3 | **Dual ControlNet** | OpenPose(Balanced) + Reference Only 동시 적용 파이프라인 | [x] |
| 4 | **Environment Pinning** | 배경 고정(Canny ControlNet) 및 충돌 자동 감지/해제 | [x] |
| 5 | **Frontend UI Integration** | Auto-Unpin Toast 알림, Hires. fix 옵션 통합 | [x] |
| 6 | **Latent Upscaler Fix** | Hires fix 흐림 해결 (Latent → R-ESRGAN 4x+ Anime6B) | [x] |

---

#### 6-4.36. Deep Optimization & Cleanup - **COMPLETE** (2026-01-31)
**목표**: 코드베이스 다이어트 및 M4 Pro 하드웨어 최적화.

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | **Dead Code Removal** | Legacy `generation.py` 로직 및 `prompt_composition.py` 삭제 | [x] |
| 2 | **M4 Pro Optimization** | OpenPose Control Mode 'Balanced'로 상향 (안정성 확보) | [x] |
| 3 | **Batch Tools** | 관리자용 Character Reference 일괄 재생성 도구 (UI/API) | [x] |
| 4 | **Remnant Cleanup** | 테스트 잔유물 스크립트(test_render.py 등) 및 임시 결과 이미지 대규모 정리 | [x] |
| 5 | **Refactoring Preparation** | `ManagePage.tsx` 분할을 위한 구조 검토 | [x] |

### 6-4.37. Stability & Polish - **COMPLETE** (2026-01-31)
**목표**: 운영 중 발견된 크리티컬 버그 수정 및 UI/UX 개선.

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | **UI Polish** | 헤더 제목 말줄임표 처리, 불필요한 레이아웃 여백 제거 | [x] |
| 2 | **DB Stability** | Storyboard Title 길이 제한(200자), Boolean 타입 캐스팅 오류 수정 | [x] |
| 3 | **Prompt Engine Fix** | `compose_prompt_tokens` 로직 구현 및 500 에러 해결 | [x] |
| 4 | **Modal Bug Fix** | ImagePreviewModal 닫기 버튼 오작동 수정 (src null 동기화) | [x] |
| 5 | **Warning Cleanup** | ControlNet `lowvram` → `low_vram` 파라미터 최신화 | [x] |
| 6 | **UI/UX Quick Wins** | 버튼 입체감(Shadow/Hover), 모달 블러 효과, 헤더 간소화 적용 | [x] |

---

#### 6-4.38. ManagePage Refactoring - **COMPLETE** (2026-01-31)
**목표**: 유지보수성 향상을 위해 거대 컴포넌트를 모듈화.

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | **ManagePage Modularization** | 2,600줄 → 6개 탭 컴포넌트 분리 (Settings/Assets/Tags/Style/Prompts/Eval) | [x] |
| 2 | **Component Isolation** | 각 탭의 독립적 데이터 페칭 및 상태 관리 구현 | [x] |
| 3 | **Hook Optimization** | `useTags`, `useCharacters` 등 기존 훅 재사용 및 최적화 | [x] |

---

### 6-5. Upcoming Refactoring (Technical Debt)
| 작업 | 설명 | 상태 |
|---|------|------|
| **Hook Extraction** | `useManageState` 등 커스텀 훅 분리 (부분 완료) | [ ] |
| **Common UI Toolkit** | 버튼, 인풋 등 공통 컴포넌트 라이브러리화 | [ ] |
| **Inter-Layer Dedup** | V3 Prompt 12-Layer 간 중복 태그 제거 (nice-to-have, 아래 상세) | [ ] |

#### 6-5.1. Inter-Layer Prompt Deduplication (Nice-to-Have)
**현황 분석** (`backend/services/prompt/v3_composition.py`):

| 범위 | 중복 제거 | 구현 방식 |
|------|----------|----------|
| 레이어 내부 (intra-layer) | O | `_flatten_layers`에서 `seen` set (case-insensitive) |
| LoRA trigger 주입 시 | O | `if trigger not in layers[LAYER_*]` 가드 |
| 레이어 간 (inter-layer) | **X** | `seen` set이 레이어별로 초기화되어, 동일 태그가 다른 레이어에 존재하면 둘 다 출력 |

**예시**: Layer 2 (Identity)에 `brown_hair`, Layer 5 (Clothing)에도 `brown_hair`가 있으면 최종 프롬프트에 2번 등장.

**개선 시 고려사항**:
- 레이어 간 중복은 **의도적 설계일 수 있음** (레이어 우선순위에 따른 강조 효과)
- 제거 시 **레이어 우선순위 전략** 필요: 낮은 번호(상위 레이어)의 태그를 보존하고 하위 레이어에서 제거
- SD 프롬프트에서 동일 태그의 반복이 가중치에 미치는 영향 검증 필요
- `BREAK` 구분자 전후의 중복은 SD 엔진 특성상 별도 처리가 필요할 수 있음

---

## 🔮 Phase 7: ControlNet & Pose Control - **ARCHIVED** ✅
- ControlNet 포즈 제어, IP-Adapter 캐릭터 일관성 시스템 구축 완료.
- 자세한 내용은 [Phase 1-4 아카이브](file:///Users/tomo/Workspace/shorts-producer/docs/archive/ROADMAP_PHASE_1_4.md) 또는 관련 보고서를 참조하세요.

---

## 🔮 Phase 8: Multi-Style Architecture (Future)
**목표**: Anime, Realistic, 3D 등 다양한 화풍 지원을 위한 유연한 파이프라인 구축.
(상세 내용은 위와 동일)

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
