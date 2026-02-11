# Phase 6: Character & Prompt System (v2.0) - Archive

다중 캐릭터 지원 및 프롬프트 빌더 시스템 구축. **전체 완료**.

**환경**: animagine-xl (SDXL), eureka_v9/chibi-laugh LoRA, 9종 Preset

---

## 6-1 ~ 6-4: Core Architecture

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

## 6-5. Stability & Integrity (P0/P1 Critical Fixes)

**목표**: 데이터 손실 위험 제거, 런타임 크래시 해결, 핵심 로직 정합성 확보.

**8개 에이전트 도메인 분석 기반** (2026-02-01):
- Backend(38건), Frontend(28건), Prompt Eng(22건), QA(24건), DBA(28건), FFmpeg(20건), UI/UX(28건), Storyboard(17건)
- 총 ~205건 → 중복 통합 후 ~155건 → P0(9) + P1(16) = **25건**

### Batch A: DB Integrity (DBA)
| # | 작업 | 우선순위 | 상태 |
|---|------|---------|------|
| 1 | 6개 테이블 `*_asset_id` FK 추가 + scenes CASCADE 정책 | P0 | [x] |
| 2 | `media_assets` 복합 인덱스 `(owner_type, owner_id)` | P0 | [x] |
| 3 | 고아 레코드 정리 (media_assets 40건 + scene_quality_scores 787건) | P0 | [x] |
| 4 | `scene_character_actions` 인덱스 + `tag_rules` FK | P1 | [x] |
| 5 | `tag_effectiveness` 테이블 생성 (DB_SCHEMA.md 문서화 완료) | P1 | [x] |

### Batch B: Backend Fixes (Backend)
| # | 작업 | 우선순위 | 상태 |
|---|------|---------|------|
| 1 | `generation.py` DB session leak 수정 (`next()` → DI) | P0 | [x] |
| 2 | `evaluation.py` legacy `identity_tags`/`clothing_tags` 제거 | P0 | [x] |
| 3 | `MediaAsset.local_path` 속성 추가 | P0 | [x] |
| 4 | `storyboard_routes.py` N+1 쿼리 해결 (eager load) | P1 | [x] |
| 5 | `LoRATriggerCache` admin/refresh-caches 등록 | P1 | [x] |

### Batch C: FFmpeg Fixes (FFmpeg)
| # | 작업 | 우선순위 | 상태 |
|---|------|---------|------|
| 1 | zoompan FPS(25) vs output FPS 불일치 수정 | P1 | [x] |
| 2 | CRF 값 + 인코딩 상수 `config.py` 이관 (SSOT) | P1 | [x] |
| 3 | FFmpeg process timeout 설정 | P1 | [x] |
| 4 | `-movflags +faststart` 추가 (웹 스트리밍 최적화) | P1 | [x] |

### Batch D: Prompt & Storyboard (Prompt Eng + Storyboard)
| # | 작업 | 우선순위 | 상태 |
|---|------|---------|------|
| 1 | Gemini JSON 파싱 강화 (마크다운 코드블록 제거) | P0 | [x] |
| 2 | `TagRuleCache` 충돌 규칙 V3 compose 연동 | P1 | [x] |
| 3 | `restricted_tags` DB 이관 (하드코딩 제거) | P1 | [x] |
| 4 | DB-missing 태그 패턴 기반 fallback (전부 LAYER_SUBJECT 방지) | P1 | [x] |
| 5 | `scene_tags` vs `context_tags` 필드명 통일 | P1 | [x] |
| 6 | `_DB_GROUP_TO_GEMINI_CATEGORY` 매핑 12-Layer 정렬 | P1 | [x] |

### Batch E: Frontend & Docs (Frontend + PM)
| # | 작업 | 우선순위 | 상태 |
|---|------|---------|------|
| 1 | `API_BASE` 중복 해소 (단일 env 변수) | P1 | [x] |
| 2 | `useTags` hook 카테고리 의존성 수정 | P1 | [x] |
| 3 | `validation.py` SessionLocal → DI 전환 | P0 | [x] |
| 4 | `CLAUDE.md` 버전 정보 현행화 (Next.js 15, React 19, Zustand 5) | P1 | [x] |

**DoD**: DB session leak 0건, FK/인덱스 마이그레이션 적용, 고아 정리 완료, 기존 테스트 전량 통과.

---

## 6-6. Code Health & Testing

**목표**: 대형 파일 분리, 테스트 커버리지 확대, 아키텍처 정비.

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

## 6-7. Infrastructure & DX

**목표**: CI 파이프라인, Soft Delete, Common UI Toolkit, 개발 도구 정비.

| # | 작업 | 분류 | 상태 |
|---|------|------|------|
| 1 | CI 파이프라인 (GitHub Actions: lint + test) | 인프라 | [x] |
| 2 | VRT Baseline System | 인프라 | [ ] (→ Tier 3 #8) |
| 3 | 고아 media_assets GC 시스템 | 인프라 | [x] |
| 4 | SoftDeleteMixin + Alembic 마이그레이션. [기능 명세](../99_archive/features/SOFT_DELETE.md) · [기술 설계](../03_engineering/backend/SOFT_DELETE.md) | Soft Delete | [x] |
| 5 | Backend trash/restore/permanent 엔드포인트 | Soft Delete | [x] |
| 6 | Frontend Trash 탭 (Manage) | Soft Delete | [x] |
| 7 | Common UI Toolkit v1 (Button, Modal, ConfirmDialog). [상세](FEATURES/TECH_DEBT.md) | UI | [x] |
| 8 | z-index 통합 관리 (Tailwind 설정) | UI | [x] |
| 9 | Hook Extraction (5개 탭 커스텀 Hook 분리) | Frontend | [x] |
| 10 | WD14 Feedback Loop (`tag_effectiveness` 자동 업데이트) | 프롬프트 | [x] (Phase 1 완료) |
| 11 | Batch Generation API (다수 씬 병렬 생성) | Backend | [x] |
| 12 | WD14 Validate 매칭 정확도 개선 (부분문자열 오탐 제거, 복합태그 분해, 동의어, skipped/partial 응답) | 프롬프트 | [x] |
| 13 | Character Voice Preset (캐릭터 대표 목소리) | Voice | [x] |
| 14 | Storyboard Narrator Voice (스토리보드 나레이터 목소리) | Voice | [x] |
| 15 | TTS 파이프라인 speaker→voice 자동 resolve | Voice | [x] |
| 16 | DB Schema Cleanup: 네이밍(`default_` 제거) + 타입(`Integer→Boolean`, `Text→JSONB`). [명세](../99_archive/features/SCHEMA_CLEANUP.md) | DB | [x] |

**진척**: 14/14 완료 (2건 Tier 재분류). **DoD**: PR마다 CI 자동 테스트, Soft Delete 3개 모델 적용, 공통 컴포넌트 4개+.

---

## 6-8. Local AI Engine & Performance

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
