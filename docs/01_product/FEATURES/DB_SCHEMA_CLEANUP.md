# DB Schema Cleanup — 미사용 컬럼/테이블 감사 및 정리

> **상태: 대기 (분석 완료, 실행 대기)**
> 2026-02-27 | DBA + Backend Dev + Tech Lead + PM 4인 크로스 리뷰
> 분석 기준: DB 실데이터 조회 + ORM/서비스/라우터 코드 교차 검증

## 배경

DB Schema v3.30 기준, 전체 테이블/컬럼의 실제 사용 현황을 DB 데이터 + 코드 참조 양면에서 감사.
"컬럼이 정의되었지만 값이 한 번도 들어오지 않았다면 미구현이거나 불필요"를 기본 원칙으로 판정.

---

## 요약 대시보드

| 판정 | 건수 | 정의 |
|------|------|------|
| **FIX FIRST** | 5건 | 코드 구현 완료인데 데이터 누락 — 버그 또는 데이터 시딩 누락 |
| **DROP OK** | 3건 | 로드맵/PRD에 없고, 다른 방식으로 대체 가능 |
| **KEEP** | 8건 | 로드맵/FEATURES에 관련 기능 존재, 향후 반드시 필요 |
| **DEFER** | 3건 | SDXL 전환 시점까지 유보 후 재평가 |
| **DOC FIX** | 4건 | DB_SCHEMA.md 문서와 실제 스키마 불일치 |
| **INFRA** | 2건 | 인프라 정리 (checkpoint GC, pg_stat) |

---

## Phase 1: FIX FIRST (버그/데이터 시딩 — 즉시)

코드가 구현 완료인데 데이터만 없는 항목. DROP이 아니라 **수정/실행**이 필요.

### 1-1. `activity_logs` Gemini 편집 추적 — INSERT 누락 (BUG)

| 컬럼 | 데이터 | 현상 |
|------|--------|------|
| `gemini_cost_usd` | 0/529 | 대시보드(`settings.py`)에서 읽지만 INSERT 시 기록 안 함 |
| `original_match_rate` | 0/529 | 편집 개선도 통계가 항상 0 |
| `final_match_rate` | 0/529 | 위와 동일 |
| `gemini_edited` | 529행 전부 false | 재시도 횟수 체크 무효화 -> 무한 재시도 가능 |

**영향**: 비용 한도 체크(`scene.py:208-223`)가 실질적으로 무효화. 분석 대시보드 데이터 공백.
**담당**: Backend Dev
**액션**: Auto Edit 성공 시 ActivityLog에 gemini 관련 필드 기록 로직 추가
**관련**: PROJECT_GROUP.md 2-4 "분석 대시보드", SERVICE_ADMIN_SEPARATION.md

### 1-2. `tags.valence` — 데이터 시딩 누락

| 컬럼 | 데이터 | 현상 |
|------|--------|------|
| `valence` | 0/9,513 | Valence 충돌 감지 시스템 구현 완료(e114cec), 데이터만 없음 |

**영향**: Expression-Mood 교차 충돌 감지가 동작하지 않음 (L7 <-> L11 체크 무효)
**담당**: Backend Dev / Prompt Engineer
**액션**: `POST /admin/tags/classify-valence` 일괄 실행 또는 스크립트로 expression/mood 태그에 valence 부여
**관련**: ROADMAP.md 02-27 완료 항목 "Expression-Mood Valence 충돌 감지 시스템"

### 1-3. `scene_quality_scores.identity_score/identity_tags_detected` — 파이프라인 연결 누락

| 컬럼 | 데이터 | 현상 |
|------|--------|------|
| `identity_score` | 0/408 | identity_score 서비스 존재, 저장 경로 미연결 |
| `identity_tags_detected` | 0/408 | 위와 동일 |

**영향**: Cross-Scene Consistency(Phase 16-D 완료) 캐시가 동작하지 않음
**담당**: Backend Dev
**액션**: WD14 batch_validate 흐름에서 identity 캐시 저장 경로 점검
**관련**: CROSS_SCENE_CONSISTENCY.md Phase 16-D

### 1-4. `storyboards.base_seed` — 할당 로직 점검

| 컬럼 | 데이터 | 현상 |
|------|--------|------|
| `base_seed` | 0/125 | Seed Anchoring(Phase 4-1 완료) 핵심인데 한 건도 없음 |

**영향**: Seed Anchoring이 실질적으로 비활성 상태
**담당**: Backend Dev
**액션**: 스토리보드 생성/저장 시 base_seed 자동 할당 로직 점검
**관련**: CHARACTER_CONSISTENCY.md Phase 4-1

### 1-5. `media_assets.checksum` — 쓰기 로직 누락

| 컬럼 | 데이터 | 현상 |
|------|--------|------|
| `checksum` | 4/1,966 | SHA-256 해시 기록 로직 미구현 |

**영향**: 에셋 중복 감지(deduplication) 불가
**담당**: Backend Dev
**액션**: media_assets 저장 시 checksum 계산 로직 보완
**관련**: PRD "에셋 관리 및 데이터 영속화", PROJECT_GROUP.md 2-4 "Production Scale"

---

## Phase 2: DROP OK (안전하게 삭제 가능 — 다음 스프린트)

로드맵/PRD/FEATURES 어디에서도 활용 계획이 없고, 다른 방식으로 대체 가능한 항목.

### 2-1. `characters.reference_source_type` — DROP

| 현황 | 근거 |
|------|------|
| 0/11 = 100% NULL | 어떤 명세에서도 활용 계획 없음 |
| 대체 가능 | `reference_images` JSONB 존재 여부로 추론 가능 |

### 2-2. `scenes.multi_gen_enabled` — DROP

| 현황 | 근거 |
|------|------|
| 254행 중 1행만 true | **WRITE_ONLY** — `generation.py`에서 batch_size 항상 1 고정 |
| 대체 가능 | 캐릭터 프리뷰 multi-gen은 API 파라미터로 제어 |
| 명세 없음 | 로드맵/FEATURES에 이 컬럼에 의존하는 기능 계획 없음 |

### 2-3. `scenes.last_seed` — DROP (조건부)

| 현황 | 근거 |
|------|------|
| 9/1,157 = 거의 미사용 | 쓰기 1곳(`generation.py`), **읽기 코드 0곳** |
| 대체 가능 | Seed Anchoring은 `base_seed + order * offset`으로 결정론적 계산 |
| 참고 | 향후 "동일 이미지 재생성" 기능 시 유용할 수 있으므로 `activity_logs`로 이동 검토 |

**DBA 액션**: 3건 DROP Alembic 마이그레이션 생성

---

## Phase 3: KEEP (향후 기능에 필요 — 유지)

100% NULL이지만 로드맵/FEATURES에 관련 기능이 명확히 존재하는 항목.

| # | 컬럼 | 데이터 | 유지 근거 |
|---|------|--------|----------|
| 1 | `characters.ip_adapter_guidance_start/end` | 0/11 | SDXL 전환 시 필수 튜닝 파라미터 (CHARACTER_CONSISTENCY.md 미착수) |
| 2 | `scenes.clothing_tags` | 0/1,157 | SCENE_CLOTHING_OVERRIDE.md 완료 기능. 사용자 미사용일 뿐 |
| 3 | `loras.gender_locked` | 1/12 | CHARACTER_BUILDER.md Character Wizard LoRA 필터 핵심 |
| 4 | `tags.thumbnail_asset_id` | 0/9,513 | VISUAL_TAG_BROWSER.md Phase 15-B. 배치 수집 미실행 |
| 5 | `loras.preview_image_asset_id` | 0/12 | media_asset_id 원칙 준수. LoRA 관리 UI에서 사용 |
| 6 | `scenes.width/height` | 전부 512x768 | SDXL 전환 시 해상도 변경 필수 (512x768 -> 1024x1536) |
| 7 | `scenes.scene_mode` | 전부 "single" | MULTI_CHARACTER.md 핵심 분기. 인프라 완성 |
| 8 | `scenes.use_reference_only` 등 3컬럼 | 전부 기본값 | SDXL 전환까지 DEFER. 현재는 config.py 상수로 충분 |

---

## Phase 4: DOC FIX (문서 불일치 — 즉시)

DB_SCHEMA.md와 실제 스키마가 일치하지 않는 항목. 코드 변경 없이 문서만 수정.

| # | 항목 | 현상 | 수정 내용 |
|---|------|------|----------|
| 1 | `is_permanent` Known Issue | **이미 해결됨** — weight boost에만 사용, 레이어 강제 배치 아님 | "해결됨" 표기 + 현재 동작 설명 |
| 2 | `lora_type=style` Known Issue | **이미 해결됨** — `LAYER_ATMOSPHERE`에 정상 배치 | "해결됨" 표기 |
| 3 | `characters.prompt_mode` | **이미 DROP됨** — 마이그레이션 완료 | 문서에서 삭제 |
| 4 | `embeddings` 테이블 "미구현" 표기 | **구현 완료** — 4행 데이터, CRUD + StyleContext 활성 | "구현 완료, 현재 4건" |

**담당**: DBA
**액션**: DB_SCHEMA.md 4건 일괄 수정

---

## Phase 5: INFRA (인프라 정리)

### 5-1. LangGraph Checkpoint GC — HIGH

| 테이블 | 행수 | 크기 |
|--------|------|------|
| `checkpoint_writes` | 12,978 | 11MB |
| `checkpoints` | 277 | 7.6MB |
| `checkpoint_blobs` | 3,670 | 6.2MB |
| **합계** | **16,925** | **~25MB** |

**현상**: LangGraph PostgresSaver가 실행마다 누적. GC 정책 없어 선형 증가.
**담당**: Backend Dev / DBA
**액션**: 7일+ 데이터 자동 정리 배치 작업 도입 (cron 또는 startup hook)

### 5-2. pg_stat 통계 미갱신 — LOW

**현상**: `pg_stat_user_tables`의 row_count가 부정확 (projects 0건으로 표시되나 실제 2건)
**액션**: `ANALYZE` 실행으로 통계 갱신

---

## 실행 계획

### Sprint A: FIX FIRST + DOC FIX (1주)

| 담당 | 작업 | 건수 | 예상 공수 |
|------|------|------|----------|
| Backend Dev | 1-1 activity_logs INSERT 수정 | 1건 | 3h |
| Backend Dev | 1-2 valence 일괄 시딩 실행 | 1건 | 1h |
| Backend Dev | 1-3 identity_score 저장 경로 점검 | 1건 | 2h |
| Backend Dev | 1-4 base_seed 할당 로직 점검 | 1건 | 2h |
| Backend Dev | 1-5 checksum 쓰기 로직 보완 | 1건 | 2h |
| DBA | Phase 4 DB_SCHEMA.md 문서 수정 4건 | 4건 | 1h |
| DBA | 5-2 ANALYZE 실행 | 1건 | 10min |

### Sprint B: DROP + INFRA (1주)

| 담당 | 작업 | 건수 | 예상 공수 |
|------|------|------|----------|
| DBA | 2-1~2-3 DROP 마이그레이션 생성 | 3건 | 2h |
| Backend Dev | 5-1 Checkpoint GC 배치 구현 | 1건 | 3h |

---

## DoD (Definition of Done)

- [ ] FIX FIRST 5건: 각 컬럼에 정상 데이터 확인 (1건 이상 NOT NULL)
- [ ] DROP 3건: Alembic 마이그레이션 적용 + 스키마 검증
- [ ] DOC FIX 4건: DB_SCHEMA.md 갱신 + 버전 v3.31
- [ ] INFRA: checkpoint 테이블 크기 50% 감소 확인
- [ ] 전체 테스트 PASS 유지

---

## 참조 문서

| 문서 | 관련 |
|------|------|
| CHARACTER_CONSISTENCY.md | ip_adapter_guidance, base_seed, SDXL 전환 |
| SCENE_CLOTHING_OVERRIDE.md | clothing_tags 기능 |
| VISUAL_TAG_BROWSER.md | thumbnail_asset_id |
| CHARACTER_BUILDER.md | gender_locked |
| MULTI_CHARACTER.md | scene_mode |
| CROSS_SCENE_CONSISTENCY.md | identity_score |
| PROJECT_GROUP.md | checksum, 분석 대시보드 |
| SERVICE_ADMIN_SEPARATION.md | activity_logs 확장 |

---

**Last Updated:** 2026-02-27
