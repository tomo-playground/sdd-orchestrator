# Phase 30: 캐릭터 일관성 강화 (Character Consistency V2)

**상태**: 진행중 — A~N(11개) 완료, **O(Multi-Character Scene) 착수 대기**
**우선순위**: P0 (영상 품질 핵심)
**관련**: Phase 7-0 (ControlNet), Phase 8 (Multi-Style), CHARACTER_CONSISTENCY.md (V1), MULTI_CHARACTER.md
**최종 갱신**: 2026-03-14

---

## 현재 기술 스택 (레벨 3)

| 기술 | 상태 | 역할 | 비고 |
|------|------|------|------|
| txt2img + 12-Layer Prompt | ✅ 적용중 | 씬 이미지 생성 | `composition.py` |
| IP-Adapter Face (clip_face) | ✅ 적용중 | 참조 이미지 → 얼굴 고정 | weight 0.50 |
| IP-Adapter FaceID Plus v2 | ✅ 적용중 | 실사 얼굴 고정 (실사 시리즈용) | `faceid` 모델 선택 시 |
| ControlNet OpenPose | ✅ 적용중 | 포즈 골격 제어 | weight 0.8, Finalize 자동 할당 |
| ControlNet Depth/Canny | ✅ 적용중 | 배경/구도 제어 | `controlnet.py` CONTROLNET_MODELS |
| Phase 30-A/B 복장 enforce | ✅ 적용중 | Gemini 복장 지시 + 프롬프트 보강 | |
| Multi-Character (일반 프롬프트) | ⬜ 구현 95% | V-Pred txt2img 2인 생성 | 10/10 성공, BLOCKER 방어 미완 |
| ~~Regional Prompt (멀티 캐릭터)~~ | ❌ 폐기 | V-Pred 미호환 확인 | 일반 프롬프트로 대체 |
| 캐릭터 LoRA 트레이닝 | △ 부분 (2/13명) | 얼굴+복장 베이킹 | SDXL 전환 후 재검토 |

### 레벨 정의
- **레벨 2**: 프롬프트 + IP-Adapter
- **레벨 3 (현재)**: + ControlNet OpenPose + Depth/Canny + FaceID Plus v2 + 복장 enforce (A~N)
- **레벨 3.5 (O 완료 후)**: + Multi-Character Scene (V-Pred 일반 프롬프트)
- **레벨 4**: + 캐릭터 LoRA 트레이닝 (전원, SDXL 기반)
- ~~레벨 5: Regional Prompt 풀콤보~~ — V-Pred 미호환으로 폐기

### 미적용 기술 → 해결하는 문제 매핑
| 문제 | 해결 기술 | Sub-Phase | 상태 |
|------|----------|-----------|------|
| 대화 씬 멀티 캐릭터 불가 | V-Pred 일반 프롬프트 (txt2img) | **O** | 착수 대기 |
| 복장 드리프트 (프롬프트 한계) | 캐릭터 LoRA 트레이닝 | D | SDXL 전환 후 재검토 |
| 복장 드리프트 (Negative 부재) | Negative Prompt 복장 보호 | F | ✅ 완료 |
| ~~대화 씬 멀티 캐릭터~~ | ~~Pipeline Inpaint~~ | ~~G~~ | ❌ 폐기 → O로 대체 |

### 멀티캐릭터 생성 테스트 결과

#### SD 1.5 시대 테스트 (2026-03-07, 참고용)

`test_sdxl_compare/multi_char_test/` 디렉토리에서 3가지 접근법 비교:

| 접근법 | 방식 | 성공률 | 주요 문제 |
|--------|------|--------|----------|
| **Regional Prompter** | BREAK 토큰으로 좌/우 영역 분할 | ~20-30% | 512x768 세로 분할 → 256x768 너무 좁음, 복장 혼합 |
| **Regional + Dual IP-Adapter** | Regional + 캐릭터별 참조 이미지 | ~10% | IP-Adapter가 영역별이 아닌 전역 적용 → 한 캐릭터만 지배 |
| **Pipeline Inpaint** | Step1 txt2img(A) → Step2 img2img inpaint(B) | ~60% | 가장 유망하나 두 번째 캐릭터 크기 조절 필요 |

#### NoobAI-XL V-Pred 테스트 (2026-03-14, 현재 기준)

| 접근법 | 성공률 | 비고 |
|--------|--------|------|
| **일반 프롬프트 (txt2img)** | **10/10 (100%)** | LoRA 없이 프롬프트만으로 2인 동시 생성 |
| Regional Prompter | ❌ 미호환 | V-Pred 미지원 |
| Forge Couple | ❌ 미호환 | V-Pred 미지원 |
| MultiDiffusion | ❌ 미호환 | V-Pred 미지원 |

**결론**: V-Pred 전환으로 **일반 프롬프트 방식이 최적**. Regional/Inpaint 불필요.

#### 모델 비교 (2026-03-07 → 2026-03-14)

| 항목 | SD 1.5 + Phase 30 | NoobAI-XL V-Pred |
|------|-------------------|------------------|
| 얼굴 일관성 | ⭐⭐ (IP-Adapter 의존) | ⭐⭐⭐⭐⭐ (프롬프트만으로 동일인) |
| 복장 유지 | ⭐⭐⭐⭐ (enforce로 강제) | ⭐⭐⭐ (색상 명시해도 누락) |
| 프롬프트 준수 | ⭐⭐ | ⭐⭐⭐⭐ |
| **2인 동시 생성** | **0% (불가)** | **100% (10/10)** |
| 해상도 | 512x768 | 832x1216 |

---

## 문제 정의

### 현상
1. **복장 드리프트** — 같은 캐릭터가 씬마다 다른 옷을 입음 (교복 → 캐주얼 → 제복)
2. **얼굴 미세 변동** — 씬 간 얼굴 특징(눈 크기, 머리카락 디테일)이 미묘하게 달라짐

### 근본 원인 분석

| 원인 | 영향도 | 설명 |
|------|--------|------|
| IP-Adapter weight 0.35 | **Critical** | 업계 권장 0.5~0.7 대비 크게 낮아 프롬프트 드리프트 억제 불가 |
| 복장이 EXCLUSIVE_TAG_GROUPS 미포함 | **Critical** | 씬 태그가 캐릭터 DB 복장 태그를 덮어씀 |
| Gemini 복장 자유 생성 | **High** | 템플릿에 복장 고정 지시 부재 → 씬마다 다른 복장 태그 출력 |
| Character LoRA 미보유 (11/13명) | **High** | 텍스트 프롬프트만으로 SD 1.5 캐릭터 재현 한계 |
| Identity weight boost 1.15 | **Medium** | 미미한 수준, 다른 태그와의 경쟁에서 밀림 |
| 단일 IP-Adapter (얼굴만) | **Medium** | 복장/전신 참조 없음 |

---

## 구현 계획

### Sub-Phase A: Config 튜닝 (완료 — 03-07)

코드 변경 최소화, config 값 조정만으로 체감 개선.

| # | 항목 | 변경 | 근거 |
|---|------|------|------|
| A-1 | IP-Adapter weight 상향 | `0.35 → 0.50` | 업계 권장 0.5~0.7, 30-scene POC 재검증 필요 |
| A-2 | Identity weight boost 강화 | `1.15 → 1.25` | 캐릭터 identity 태그 우선순위 강화 |
| A-3 | Detail weight boost 강화 | `1.10 → 1.20` | 복장/액세서리 태그 유지력 향상 |
| A-4 | Clothing을 Exclusive Group 추가 | `EXCLUSIVE_TAG_GROUPS += {"clothing", "accessory"}` | 씬 태그의 복장 덮어쓰기 방지 |

**파일**: `config.py`, `config_prompt.py`
**검증**: 기존 스토리보드 3개(1분 상식, 꿈꾸는 모험, 감성 한 스푼) 비교 생성
**테스트**: 기존 composition 테스트 + 새 Exclusive Group 테스트 추가
**예상 소요**: 0.5일

---

### Sub-Phase B: Gemini 템플릿 복장 고정 (완료 — 03-07)

Gemini가 씬 생성 시 캐릭터 기본 복장을 유지하도록 지시 강화.

| # | 항목 | 설명 |
|---|------|------|
| B-1 | Cinematographer 템플릿 복장 고정 지시 | `CRITICAL: Maintain character's default outfit` 디렉티브 추가 |
| B-2 | Writer 템플릿 복장 변경 제한 | 의도적 복장 변경은 `[OUTFIT_CHANGE]` 명시 마커 필요 |
| B-3 | Finalize 복장 교정 로직 | 캐릭터 DB 복장 태그 vs 씬 복장 태그 비교 → 불일치 시 DB 태그로 교체 |
| B-4 | clothing_override 의도적 사용 구분 | Scene에 `clothing_override` 명시된 경우만 복장 변경 허용 |

**파일**: `templates/cinematographer.j2`, `templates/create_storyboard.j2`, `services/agent/nodes/finalize.py`
**검증**: Dialogue 구조 10씬 생성 → 복장 일관성 비교
**테스트**: Finalize 복장 교정 단위 테스트 8개
**예상 소요**: 2일

---

### Sub-Phase C: Dual IP-Adapter 활성화 (2주 내)

기존 구현된 Dual Unit을 활성화하고 복장 참조를 추가.

| # | 항목 | 설명 |
|---|------|------|
| C-1 | 캐릭터 레퍼런스 이미지 분리 | face_reference (얼굴 크롭) + body_reference (전신) 2종 관리 |
| C-2 | Dual IP-Adapter 활성화 | Unit 1: face (clip_face, 0.55) + Unit 2: body (clip, 0.35) |
| C-3 | 레퍼런스 이미지 자동 생성 | 캐릭터 생성 시 전신 레퍼런스 자동 생성 (기존 face만 → face+body) |
| C-4 | VRAM 프로파일링 | Dual Unit VRAM 사용량 측정, M4 Pro 24GB 한계 검증 |

**파일**: `config.py` (`IP_ADAPTER_DUAL_ENABLED`), `services/controlnet.py`, `services/character_consistency.py`, `services/characters/crud.py`
**검증**: VRAM 사용량 < 18GB 확인, 씬 생성 시간 < 2x 확인
**테스트**: Dual Unit 빌드 테스트, weight clamp 테스트
**예상 소요**: 3일

---

### Sub-Phase D: 주요 캐릭터 LoRA 트레이닝 (4주)

가장 효과적인 일관성 확보 방법. 얼굴+복장을 LoRA에 베이킹.

| # | 항목 | 설명 |
|---|------|------|
| D-1 | LoRA 트레이닝 파이프라인 구축 | Kohya_ss Dreambooth LoRA, rank 32, SD 1.5 |
| D-2 | 레퍼런스 이미지 생성 (캐릭터당 20장) | 다양한 표정/각도/포즈, 동일 복장 고정 |
| D-3 | P0 캐릭터 트레이닝 (5명) | 예민이, 건우, 하루 (1분 상식) + 시온, 수아 (꿈꾸는 모험) |
| D-4 | P1 캐릭터 트레이닝 (4명) | 소라, 하나 (감성 한 스푼) + 수빈, 지호 (잠자리 동화) |
| D-5 | P2 캐릭터 트레이닝 (2명) | 유나, 도윤 (실화 탐구) |
| D-6 | LoRA 품질 검증 자동화 | WD14 + 레퍼런스 비교 스코어링 |

**트레이닝 스펙**:
- 이미지: 캐릭터당 15~25장 (512x768, WD14 캡셔닝)
- 파라미터: rank 32, alpha 16, lr 1e-4, 3000~5000 steps
- weight: 0.6~0.7 (character LoRA)
- 검증: 5개 테스트 프롬프트로 일관성 스코어 측정

**우선순위 기준**:

| 우선순위 | 캐릭터 | 시리즈 | 영상 수 | 근거 |
|---------|--------|--------|---------|------|
| P0 | 예민이, 건우, 하루 | 1분 상식 | 66 | 최다 사용, ROI 최대 |
| P0 | 시온, 수아 | 꿈꾸는 모험 | 16 | 수채화 스타일 특화 |
| P1 | 소라, 하나 | 감성 한 스푼 | 0 (신규) | 초기 일관성 확보 |
| P1 | 수빈, 지호 | 잠자리 동화 | 8 | 그림책 스타일 특화 |
| P2 | 유나, 도윤 | 실화 탐구 | 3 | 실사 스타일, FaceID 우선 |

**예상 소요**: 4주 (파이프라인 구축 1주 + 트레이닝 3주)

---

### Sub-Phase E: 캐릭터 프롬프트 통합 — 레퍼런스↔씬 외형 일관성 (Phase 30-K)

**목표**: 레퍼런스 이미지 외형 = 씬 이미지 외형. 5개 분산 필드 → 2개로 통합, 캐릭터 페이지 1곳에서 관리.

**기존 문제**: `scene_positive/negative` + `reference_positive/negative` + `common_negative_prompts` 5필드를 따로 관리 → 동기화 실패 시 레퍼런스↔씬 외형 불일치.

**설계 원칙**:
- 캐릭터 외형 프롬프트 = **1세트** (positive_prompt / negative_prompt)
- 레퍼런스 배경(`white_background` 등) = 시스템 자동 (config.py 상수)
- 씬 컨텍스트 (배경, 포즈, 카메라) = Gemini/Cinematographer 자동

| # | 항목 | 설명 |
|---|------|------|
| K-1 | DB 필드 통합 | 5필드 → `positive_prompt` (Text) + `negative_prompt` (Text) |
| K-2 | 데이터 마이그레이션 | 5필드 내용 dedup 머지 → 2필드, 구 컬럼 삭제 |
| K-3 | PromptBuilder 통합 | scene/reference 양쪽 동일한 `positive_prompt` 사용 |
| K-4 | 네거티브 머지 단순화 | 4곳의 분산 머지 로직 → `character.negative_prompt` 1필드 |
| K-5 | Frontend UI 단순화 | 4개 입력 → 2개 입력 (캐릭터 프롬프트) |

**영향 파일**: `models/character.py`, `schemas.py`, `composition.py` (4곳), `generation_prompt.py`, `image_generation_core.py`, `controlnet.py`, `characters/reference.py`, `characters/crud.py`, `routers/prompt.py`, `script/gemini_generator.py`, `alembic/`, Frontend 13개 파일
**테스트**: 마이그레이션 테스트, 프롬프트 주입 테스트, 네거티브 머지 테스트
**예상 소요**: 1일

---

### Sub-Phase F: Negative Prompt 네이밍 개선 + 복장 보호 (즉시 — 1일)

**목적**: Negative Prompt 필드명 정리 + 데이터 정상화 + 복장 드리프트 방지

#### F-0. 프롬프트 필드 네이밍 리팩토링

현재 `custom_`, `reference_`, `recommended_` 접두어가 혼재하여 역할 구분이 어려움.

| 현재 필드명 | 변경 필드명 | 용도 |
|------------|-----------|------|
| `custom_base_prompt` | `scene_positive_prompt` | 씬 생성 긍정 프롬프트 |
| `custom_negative_prompt` | `scene_negative_prompt` | 씬 생성 부정 프롬프트 |
| `reference_base_prompt` | `reference_positive_prompt` | 레퍼런스 생성 긍정 프롬프트 |
| `reference_negative_prompt` | `reference_negative_prompt` | 유지 (이미 명확) |
| `recommended_negative` | `common_negative_prompts` | 씬+레퍼런스 공통 부정 프롬프트 (ARRAY) |

**영향 범위**: Backend 핵심 8개 + 테스트 6개 + Frontend 13개 + 문서 10개 = ~37개 파일
- `scripts/*.py` 25개는 일회성 마이그레이션 스크립트 → 리팩토링 제외 (Tech Lead 리뷰)

**3단계 분할 진행** (DBA + Tech Lead 리뷰 반영):

| Phase | 내용 | 커밋 |
|-------|------|------|
| Phase 1 | DB 마이그레이션 + ORM (`models/character.py`) + 스키마 (`schemas.py`) | 1 |
| Phase 2 | Backend 서비스 8개 + 테스트 6개 | 1 |
| Phase 3 | Frontend 13개 + 문서 10개 | 1 |
| Phase 4 | DB 데이터 보정 SQL | 1 |

#### F-1. DB 데이터 정상화

현재 `common_negative_prompts`(旧 `recommended_negative`) 데이터 문제:
- 예민이/하루/건우: 품질 태그(`lowres, bad_anatomy...`) 중복 저장 → config에서 자동 주입되므로 제거
- 미도리: 임베딩(`verybadimagenegative_v1.3`) 저장 → StyleProfile에서 관리하므로 제거
- 9명 캐릭터: 공통 Negative 자체가 없음 → 복장 보호 태그 추가

| # | 항목 | 설명 |
|---|------|------|
| F-1a | 품질 태그 중복 제거 | `common_negative_prompts`에서 `DEFAULT_SCENE_NEGATIVE_PROMPT`와 겹치는 태그 제거 |
| F-1b | 임베딩 분리 | `common_negative_prompts`에서 임베딩 제거 (StyleProfile.negative_embeddings에서 관리) |
| F-1c | 복장 보호 태그만 common에 추가 | 복장 억제 태그만 `common_negative_prompts`에 추가. 카메라/포즈 억제는 `reference_negative_prompt`에 유지 (Tech Lead 리뷰) |
| F-1d | 빈 캐릭터 기본 보호 | 하나, 소라 등 모든 Negative가 비어있는 캐릭터에 기본 복장 보호 태그 설정 |

**파일**: Alembic 마이그레이션 1개, Backend 핵심 8개 + 테스트 6개, Frontend 13개, 문서 10개, DB 보정 SQL
**테스트**: 기존 테스트 필드명 수정 + 전체 테스트 통과 확인
**예상 소요**: 1일

#### F-2. Preview → Reference 네이밍 통일 (Character 전용)

**문제**: Character의 `preview_image_asset_id`는 실제로 **IP-Adapter 참조 이미지**(얼굴 일관성용)인데 "preview"라는 이름 사용. LoRA/SDModel의 `preview_image_asset_id`는 진짜 썸네일이므로 혼란 발생.

**변경 대상 (Character만)**:

| 레이어 | 현재 | 변경 |
|--------|------|------|
| DB 컬럼 | `preview_image_asset_id` | `reference_image_asset_id` |
| FK 제약조건 | `fk_characters_preview_image_asset_id` | `fk_characters_reference_image_asset_id` |
| ORM relationship | `preview_image_asset` | `reference_image_asset` |
| ORM @property | `preview_image_url`, `preview_key` | `reference_image_url`, `reference_key` |
| Pydantic 스키마 | `preview_image_asset_id`, `preview_image_url`, `preview_key` | `reference_image_asset_id`, `reference_image_url`, `reference_key` |
| Backend 파일명 | `services/characters/preview.py` | `services/characters/reference.py` |
| Backend 파라미터 | `copy_preview` | `copy_reference` |
| API 응답 키 | `preview_url`, `preview_image_url` | `reference_url`, `reference_image_url` |
| Frontend 타입 | `preview_image_url`, `preview_image_asset_id` | `reference_image_url`, `reference_image_asset_id` |
| Frontend 필터 | `has_preview` | `has_reference` |

**변경 제외 (유지)**:

| 항목 | 이유 |
|------|------|
| `loras.preview_image_asset_id` | 진짜 프리뷰 썸네일 |
| `sd_models.preview_image_asset_id` | 진짜 프리뷰 썸네일 |
| `services/preview.py` (TTS) | 별개 파일 (TTS/타임라인 프리뷰) |
| `GenProgress.preview_image` | 생성 중 미리보기 (진짜 프리뷰) |
| `scripts/` 디렉토리 | 일회성 마이그레이션 스크립트 |
| 기존 Alembic 마이그레이션 | 히스토리 보존 |

**4-Phase 실행**:

| Phase | 내용 | 파일 수 |
|-------|------|---------|
| Phase 1 | DB 마이그레이션 (RENAME COLUMN + FK DROP/ADD + 인덱스 추가) + ORM + 스키마 | 3 |
| Phase 2 | Backend 서비스 (파일 리네이밍 포함) + 테스트 | ~15 |
| Phase 3 | Frontend 타입/컴포넌트/hooks + 테스트 | ~20 |
| Phase 4 | 문서 (DB_SCHEMA, SCHEMA_SUMMARY, CHARACTER_BUILDER 등) | ~7 |

**DBA 리뷰 결과**: PASS (BLOCKER 없음)
- RENAME COLUMN은 메타데이터 변경만, 데이터 복사 없음
- FK 제약조건은 DROP+ADD 방식 (PostgreSQL에 ALTER CONSTRAINT RENAME 없음)
- FK 인덱스 `ix_characters_reference_image_asset_id` 추가 권장

**Tech Lead 리뷰 결과**: APPROVE
- `controlnet.py:670`의 `_resolve_quality_tags_for_character` import 경로 동시 수정 필수
- API 응답 키도 Frontend와 통일하여 일괄 변경 (하위 호환 alias 없이)
- Frontend 타입에서 Character vs LoRA 필드명 분리 시 JSDoc 주석 권장

**예상 소요**: 1일

---

### ~~Sub-Phase G: 멀티캐릭터 Inpaint 파이프라인~~ (폐기 → O로 대체)

> **폐기 사유**: NoobAI-XL V-Pred 전환으로 일반 프롬프트 방식이 2인 생성 10/10 성공.
> Pipeline Inpaint(txt2img→img2img) 불필요. Sub-Phase O로 대체.

---

### Sub-Phase O: Multi-Character Scene (V-Pred 일반 프롬프트 방식)

**목표**: Dialogue 스토리보드에서 1-2개 씬에 2인 동시 출연 이미지 생성.
**전제**: V-Pred 2인 프롬프트 테스트 10/10 성공 (2026-03-14), LoRA 없이 프롬프트만으로 동작.
**방식**: Regional Prompter/Forge Couple/MultiDiffusion V-Pred 미호환 확인 → **일반 txt2img 프롬프트 방식 채택**.

#### 현황 분석 (구현 완성도)

| 영역 | 상태 | 비고 |
|------|------|------|
| DB `scene_mode` 필드 | ✅ 완성 | `models/scene.py` — "single" / "multi" |
| MultiCharacterComposer | ✅ 완성 | `prompt/multi_character.py` (290줄) — subject/tags/LoRA/framing |
| Generation Pipeline 분기 | ✅ 완성 | `image_generation_core.py` — character_b_id 있으면 자동 라우팅 |
| Gemini 템플릿 2인 지시 | ✅ 완성 | `create_storyboard_dialogue.j2` — is_multi_character_capable 조건부 |
| Character Actions 양쪽 할당 | ✅ 완성 | `action_resolver.py` — is_multi=True 시 A/B 모두 할당 |
| ControlNet/IP-Adapter multi 비활성화 | ❌ 미구현 | multi 씬에서 자동 비활성화 필요 |
| is_multi_character_capable 게이트 | ❌ **병목** | LoRA 기반 체크 → V-Pred에서 불필요 |
| LoRA multi 3필드 | ❌ **불필요** | SD 1.5 잔재, V-Pred에서 사용 안 함 |

#### O-1. LoRA multi 3필드 제거 + 게이트 단순화 + 프롬프트 구조 개선

**배경**: SD 1.5에서는 특정 LoRA만 2인 생성을 지원했으므로 LoRA별 게이트를 뒀으나, NoobAI-XL V-Pred는 LoRA 없이도 프롬프트만으로 2인 생성 10/10 성공. LoRA 기반 게이트가 실제 능력을 차단하는 병목이 됨.

**제거 대상 (LoRA 모델 3필드)**:

| 필드 | 용도 (SD 1.5) | V-Pred 이후 |
|------|--------------|------------|
| `is_multi_character_capable` | LoRA별 multi 지원 여부 게이트 | 불필요 — 모델 자체가 지원 |
| `multi_char_weight_scale` | 2인 씬 LoRA weight 축소 | `SCENE_CHARACTER_LORA_SCALE` 상수로 대체 완료 |
| `multi_char_trigger_prompt` | 멀티 전용 트리거 워드 | 사용 실적 0건 |

**게이트 변경**:

```python
# Before: LoRA 기반 체크 (병목)
def _check_multi_character_capable(char_id, char_b_id, db):
    # LoRA.is_multi_character_capable == True 체크
    # → 모든 LoRA가 False(기본값) → 항상 False 반환 → multi 씬 생성 불가

# After: Dialogue 구조 + 2캐릭터 존재 체크 (단순)
is_multi_character_capable = (
    structure in ("Dialogue", "Narrated Dialogue")
    and character_id is not None
    and character_b_id is not None
)
```

**프롬프트 구조 개선** (P0-1, P0-2 해결):

```python
# Before: 단순 나열 (태그 bleeding 위험)
"quality, 1boy, 1girl, [charA tags], [charB tags], [scene tags], <lora:...>"

# After: BREAK 토큰 캐릭터 분리 (EXP-1 검증 후 적용)
"quality, 1boy, 1girl, [scene tags], <lora:...> BREAK [charA tags] BREAK [charB tags]"
```

- Dedup 스코프를 BREAK 구간별로 분리 (양쪽 `school_uniform` 모두 유지)
- `_MULTI_BANNED_TAGS = {"solo"}` — 캐릭터 태그에서 자동 제거 (P0-4)
- `SCENE_CHARACTER_LORA_SCALE` 적용 + LoRA weight 합산 상한 1.5 (P0-5, P1-3)

**영향 파일** (8개):

| 파일 | 변경 |
|------|------|
| `models/lora.py` | 3필드 제거 |
| `schemas.py` | LoRA 스키마에서 3필드 제거 |
| `alembic/` | DROP COLUMN 마이그레이션 (ORM+참조코드 제거와 동시 커밋 — P0-6) |
| `gemini_generator.py` | `_check_multi_character_capable()` 제거 → 인라인 조건으로 교체 |
| `multi_character.py` | BREAK 구조, per-BREAK dedup, banned tags, `SCENE_CHARACTER_LORA_SCALE` 적용, weight 상한 |
| `create_storyboard_dialogue.j2` | `is_multi_character_capable` 조건 유지 (변수 소스만 변경) |
| `create_storyboard_narrated.j2` | 동일 |
| `tests/test_multi_character.py` | LoRA multi 필드 테스트 제거/수정, BREAK 구조 테스트 추가 |

#### O-2. Finalize BLOCKER 방어 — ControlNet/IP-Adapter multi 비활성화

**문제**: multi 씬에서 OpenPose(단일 skeleton)와 IP-Adapter(단일 reference)가 적용되면 이미지 왜곡.

| # | 항목 | 설명 |
|---|------|------|
| O-2a | `_auto_populate_scene_flags()` scene_mode 분기 | `scene_mode=multi` → `use_controlnet=False`, `use_ip_adapter=False`, `multi_gen_enabled=True` 자동 강제 (3후보 생성 → 사용자 선택) |
| O-2b | `scene_mode=multi` + `character_b_id=None` 검증 | character_b_id 없으면 `scene_mode=single`로 폴백 + 경고 로그 |
| O-2c | Dialogue 외 구조에서 multi 차단 | Monologue/Confession에서 scene_mode=multi 방지 |
| O-2d | multi 씬 상한 검증 | 스토리보드당 multi 씬 최대 2개 초과 시 경고 로그 |
| O-2e | speaker=Narrator + scene_mode=multi 보정 | Narrator 씬은 `no_humans` 주입인데 multi와 모순 → scene_mode=single 강제 | P1-2 |

**파일**: `services/agent/nodes/finalize.py`

#### O-3. Generation 경로 방어

| # | 항목 | 설명 | 이슈 |
|---|------|------|------|
| O-3a | `generation_controlnet.py` early return | `scene_mode=multi` 시 ControlNet/IP-Adapter 빌드 스킵 | |
| O-3b | `image_generation_core.py` char_b 미존재 로그 | `character_b_id` 있는데 DB에 없으면 경고 + single 폴백 | |
| O-3c | Interaction 태그 기본 주입 | `scene_mode=multi`면 `facing_another` 기본 주입 (Gemini 누락 방어) | |
| O-3d | Multi 씬 Negative subject 태그 필터 | positive에 `1girl` + negative에 `1girl` → 자동 제거 | P0-3 |
| O-3e | Multi 전용 Negative 상수 | `MULTI_CHAR_NEGATIVE_EXTRA = "solo, fused_body, merged_body"` 자동 주입 | P1-4 |
| O-3f | soft-deleted char_b 방어 | `prepare_prompt()` char_b 로딩에 `deleted_at.is_(None)` 필터 추가 | P1-1 |
| O-3g | char_a == char_b 방어 | `_resolve_effective_character_b_id()`에서 동일 ID 시 None 반환 + WARNING | |

**파일**: `generation_controlnet.py`, `generation_prompt.py`, `image_generation_core.py`, `multi_character.py`, `config.py`

#### O-4. TTS 안정화

| # | 항목 | 설명 |
|---|------|------|
| O-4a | TTS 캐시 키에 speaker 포함 | A/B 동일 스크립트 시 캐시 키 충돌 방지 |
| O-4b | Speaker B voice preset 검증 | `resolve_speaker_to_character()` 실패 시 명시적 경고 |

**파일**: `tts_helpers.py`
**비고**: Multi 씬은 "2인이 동시에 한 프레임에 등장"하는 이미지 생성. TTS는 기존과 동일하게 씬별 1명 speaker가 읽음 (speaker 필드 기준). 2인 동시 음성은 scope 외.

#### O-5. 테스트

| # | 항목 | 예상 수 | 이슈 |
|---|------|--------|------|
| O-5a | Finalize multi 씬 플래그 (비활성화, 상한, 폴백, Narrator 보정) | 8개 | P1-2 |
| O-5b | 게이트 단순화 (Dialogue+2캐릭터=True, Monologue=False, 1캐릭터=False) | 4개 | |
| O-5c | BREAK 구조 + per-BREAK dedup + banned tags + LoRA weight 상한 | 6개 | P0-1,2,4,5 P1-3 |
| O-5d | generation_controlnet early return | 3개 | |
| O-5e | Negative subject 필터 + multi 전용 negative | 4개 | P0-3 P1-4 |
| O-5f | char_b 방어 (soft-deleted, 미존재, 동일 ID) | 4개 | P1-1 |
| O-5g | TTS 캐시 키 speaker 포함 | 2개 | |
| O-5h | 기존 single 씬 리그레션 (ControlNet/IP-Adapter 무영향) | 3개 | |
| O-5i | LoRA multi 필드 제거 마이그레이션 | 2개 | P0-6 |
| | **합계** | **~36개** | |

#### O-6. 문서 업데이트

| 파일 | 변경 |
|------|------|
| `ROADMAP.md` | Phase 30-O 완료 기록 |
| `FEATURES/MULTI_CHARACTER.md` | V-Pred 기반 동작 방식 추가, LoRA 3필드 제거 반영 |
| `DB_SCHEMA.md` | LoRA 테이블 3필드 제거 반영 |
| `SCHEMA_SUMMARY.md` | 동기화 |

#### 실행 순서

```
Step 1  O-1 (게이트 단순화 + LoRA 3필드 제거)     ■■■■ — 핵심 병목 해소
Step 2  O-2 (Finalize BLOCKER 방어)               ■■■  — ControlNet/IP-Adapter 비활성화
Step 3  O-3 (Generation 경로 방어)                 ■■   — 폴백/로그 추가
Step 4  O-4 (TTS 안정화)                          ■    — 캐시 키 수정
Step 5  O-5 (테스트 22개)                          ■■■  — 통합 검증
Step 6  O-6 (문서)                                 ■    — 동기화
```

**예상 소요**: 1일
**선행 조건**: 없음 (기존 구현 95% 완성)

#### 사이드이펙트 분석 결과

**CRITICAL → O-1, O-2에서 해결**:
- C-1: ControlNet/IP-Adapter multi 비활성화 → O-2a
- C-2: is_multi_character_capable 게이트 병목 → O-1

**HIGH → O-3, O-4에서 해결**:
- H-1: TTS Speaker B preset 해석 → O-4b
- H-2: TTS 캐시 키 speaker 미포함 → O-4a
- H-3: Finalize scene_mode 검증 → O-2b
- H-4: char_b 미존재 침묵 폴백 → O-3b

**MEDIUM → Phase 30-O 이후 개선 (Backlog)**:
- M-1: Pre-validation multi 씬 미표시
- M-2: Frontend 재생성 시 character_b_id 누락
- M-3: Scene Text 2인 대사 speaker 구분
- M-4: Dialogue 외 구조 multi 차단 → O-2c에서 부분 해결

---

## 실행 순서 및 타임라인

```
Week 1     Sub-Phase A (Config 튜닝) ■■ 0.5일                    ✅ 완료
           Sub-Phase B (Gemini 템플릿) ■■■■ 2일                  ✅ 완료
           Sub-Phase F-0/F-1 (프롬프트 네이밍 + 데이터 보정) ■■ 1일  ✅ 완료
           Sub-Phase H~N (11개 Sub-Phase) ■■■■■■■■ 4일           ✅ 완료
           Sub-Phase O (Multi-Character Scene) ■■ 1일             ← 즉시 착수
Week 2-3   Sub-Phase C (Dual IP-Adapter) ■■■■■■ 3일              대기 (SDXL 재검토)
           Sub-Phase D (LoRA 트레이닝) ■■■■■■■■■■ 4주            대기 (SDXL 재검토)
```

## 성공 지표

| 지표 | A~N 완료 | O 완료 후 |
|------|---------|----------|
| 씬 간 얼굴 일관성 | 80% | 80% (single 씬 동일) |
| 씬 간 복장 일관성 | 80% | 80% (single 씬 동일) |
| 2인 동시 출연 성공률 | 0% | **>80%** (V-Pred 프롬프트) |
| Multi 씬 ControlNet 왜곡 | N/A | **0%** (자동 비활성화) |

## 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| V-Pred multi 프롬프트 캐릭터 혼합 | 2인의 외형이 섞임 | MultiCharacterComposer의 per-character flattening + wide_shot 강제 |
| ControlNet/IP-Adapter 비활성화 → 포즈/얼굴 제어 불가 | multi 씬 품질 하락 | V-Pred 프롬프트 준수율이 높아 보상 (10/10 테스트) |
| TTS 캐시 키 변경 → 기존 캐시 무효화 | TTS 재생성 필요 | speaker 추가는 기존 키와 다르므로 자연스럽게 재생성 |
| LoRA 3필드 DROP → 롤백 불가 | 데이터 영구 삭제 | 사용 실적 0건, DB 백업 후 진행 |

---

## Phase 30-O Known Issues (4-Agent Cross Analysis, 2026-03-14)

> Prompt Engineer / Backend Dev / Frontend Dev / QA Validator 4개 에이전트 병렬 분석 결과.
> 각 이슈는 O-1~O-6 작업 항목 또는 Backlog로 매핑.

### P0 — CRITICAL (구현 필수)

| ID | 이슈 | 원인 | 대응 |
|----|------|------|------|
| **P0-1** | 캐릭터 간 태그 Bleeding — BREAK 토큰 부재 | `compose()`에서 CharA/CharB 태그를 콤마로 단순 나열. SD가 hair/clothing 소유권 구분 불가 | **O-1에 O-1d 추가**: `[Quality, Subject, Scene] BREAK [CharA] BREAK [CharB]` 구조. V-Pred BREAK 호환 테스트 선행 |
| **P0-2** | Global Dedup이 캐릭터별 동일 태그 제거 | `school_uniform`이 A/B 양쪽에 있으면 B 쪽 제거됨 | **O-1에 추가**: Dedup 스코프를 BREAK 구간별로 분리. 캐릭터 Identity 태그(L1~L4)는 per-character dedup |
| **P0-3** | Negative 합산 시 상호 억제 | B의 `negative: 1girl`이 A(여성)를 억제 | **O-3에 추가**: Multi 씬 negative에서 subject 태그(`1girl`, `1boy`, `solo`) 자동 제거 |
| **P0-4** | `solo` 태그 잔류 | 캐릭터 DB tags/positive_prompt에 `solo` 포함 시 2인 씬에서 1인만 생성 | **O-3에 추가**: `_MULTI_BANNED_TAGS = {"solo"}` 정의, `_flatten_character()` 시 제거 |
| **P0-5** | SCENE_CHARACTER_LORA_SCALE 미적용 | `_inject_character_loras()`가 `multi_char_weight_scale`만 적용, `SCENE_CHARACTER_LORA_SCALE`(0.45) 누락 | **O-1에 포함**: 3필드 제거 시 `SCENE_CHARACTER_LORA_SCALE` 적용으로 교체 |
| **P0-6** | LoRA 3필드 DROP 마이그레이션 순서 | ORM 필드 제거 전 마이그레이션 실행 시 컬럼 미존재 에러, 역순도 동일 | **O-1**: ORM+참조코드 제거 → 마이그레이션 생성/적용 동시 커밋 |

### P1 — HIGH (Phase 30-O 내 해결)

| ID | 이슈 | 원인 | 대응 |
|----|------|------|------|
| **P1-1** | soft-deleted char_b의 negative 머지 | `prepare_prompt()` L475에서 char_b 로딩 시 `deleted_at` 필터 없음 | **O-3b 확장**: char_b 로딩에 `deleted_at.is_(None)` 필터 추가 |
| **P1-2** | scene_mode=multi + speaker=Narrator 모순 | Narrator 씬은 `no_humans` 주입인데 multi는 2인 요구 | **O-2c 확장**: Finalize에서 `speaker=Narrator` 씬의 scene_mode를 `single`로 강제 보정 |
| **P1-3** | 2x CharLoRA + StyleLoRA weight 합산 과다 | 0.7+0.7+0.76=2.16 → 이미지 불안정 | **O-1에 추가**: `_build_lora_string()` 후 총 weight 합산 상한(1.5) 초과 시 비례 축소 |
| **P1-4** | Multi 전용 Negative 미정의 | `solo`, `fused_body`, `merged_body` 등 2인 씬 전용 억제 태그 없음 | **O-3에 추가**: `config.py`에 `MULTI_CHAR_NEGATIVE_EXTRA` 상수 추가, 자동 주입 |
| **P1-5** | Post Type 얼굴 크롭이 1인만 기준 | `detect_face()` → `_pick_best_face()` → 가장 큰 얼굴 1개만 반환 | **Backlog**: `detect_face()` 다중 얼굴 감지 → 전체 bounding box 병합 |
| **P1-6** | Frontend scene_mode 전체 미사용 | 타입 정의만 있고, UI/로직 어디에서도 scene_mode 분기 없음 | **O-6 확장**: Frontend에 (1) SceneCard multi 배지, (2) speakerResolver multi 분기, (3) pre-flight scene_mode 검증 추가 |
| **P1-7** | Frontend 재생성 시 character_b_id 유실 가능 | `selectedCharacterBId=null` → `character_b_id: undefined` → single 폴백 | **O-6 확장**: 재생성 시 씬의 scene_mode=multi면 character_b_id 필수 검증 |

### P2 — MEDIUM (Phase 30-O 이후 Backlog)

| ID | 이슈 | 원인 | 대응 (Backlog) |
|----|------|------|---------------|
| P2-1 | 832x1216 세로 비율 2인 배치 어려움 | wide_shot + 세로 → 캐릭터 매우 작음 | `upper_body` 기본 framing 검토. 또는 multi 씬 전용 가로 비율(1216x832) 옵션 |
| P2-2 | CFG 4.5에서 2인 프롬프트 수렴 부족 | 낮은 CFG → 프롬프트 무시 경향 | Multi 씬 전용 `SD_MULTI_CHAR_CFG_SCALE=5.5` 옵션 검토 |
| P2-3 | 같은 성별 2인 → 쌍둥이 문제 | `2girls` 태그가 SD의 동일 외모 생성 유도 | 캐릭터별 구분 태그(의상/헤어스타일) weight 1.2~1.3 부스트 |
| P2-4 | LoRA 비대칭 (A만 있고 B 없음) | A의 LoRA 스타일이 B에도 전이 | 경고 로그 + 가이드 문서 |
| P2-5 | clothing_override가 multi 경로 미지원 | `MultiCharacterComposer.compose()`에 파라미터 없음 | `clothing_overrides: dict[int, list]` 파라미터 추가 |
| P2-6 | Negative 이중 적용 | `compose_scene_with_style()` + `prepare_prompt()` 양쪽에서 char negative 머지 | SSOT 원칙에 따라 한 곳으로 통일 |
| P2-7 | Pre-validation multi 씬 검증 없음 | `preview_validate.py`에서 scene_mode/char_b 미검증 | `_check_characters()`에 multi 씬 char_b 존재 확인 추가 |
| P2-8 | SceneItem 타입에 scene_mode 누락 | `scriptEditor/types.ts` — TS 접근 불가 | 타입 필드 추가 |
| P2-9 | speaker 변경 시 scene_mode 미동기화 | multi 씬 speaker를 Narrator로 변경해도 scene_mode=multi 유지 | `handleSpeakerChange`에서 Narrator 선택 시 scene_mode=single 보정 |
| P2-10 | Ken Burns 2인 씬 프레이밍 | pan_left/right로 한 캐릭터 이탈 | multi 씬 전용 pan 범위 제한 프리셋 |
| P2-11 | handleAddScene에서 scene_mode 미설정 | 수동 씬 추가 시 undefined | `scene_mode: "single"` 기본값 명시 |

### 실험 필요 항목

| ID | 실험 | 방법 | 판단 기준 |
|----|------|------|----------|
| **EXP-1** | V-Pred BREAK 토큰 호환성 | BREAK 포함/미포함 동일 프롬프트 10쌍 생성 비교 | 캐릭터 분리도 (hair/clothing 정확도) |
| **EXP-2** | CFG 4.5 vs 5.5 multi 씬 | 동일 프롬프트로 CFG 4.5/5.5 각 5쌍 비교 | 프롬프트 준수율 + 이미지 품질 |
| **EXP-3** | wide_shot vs upper_body 2인 배치 | 832x1216에서 각 framing 5쌍 비교 | 2인 모두 온전히 보이는 비율 |
| **EXP-4** | ADetailer 2인 얼굴 감지 | multi 씬 이미지에서 confidence=0.3으로 2인 감지 성공률 | 2인 모두 감지 비율 > 80% |
