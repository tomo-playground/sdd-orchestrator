# Phase 30: 캐릭터 일관성 강화 (Character Consistency V2)

**상태**: 진행중 (Sub-Phase A, B 완료)
**우선순위**: P0 (영상 품질 핵심)
**관련**: Phase 7-0 (ControlNet), Phase 8 (Multi-Style), CHARACTER_CONSISTENCY.md (V1)
**최종 갱신**: 2026-03-07

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
| Regional Prompt (멀티 캐릭터) | ❌ 미적용 | 화면 영역 분할 (A/B 대화) | |
| 캐릭터 LoRA 트레이닝 | △ 부분 (2/13명) | 얼굴+복장 베이킹 | 유카리, 미도리만 |

### 레벨 정의
- **레벨 2**: 프롬프트 + IP-Adapter
- **레벨 3 (현재)**: + ControlNet OpenPose + Depth/Canny + FaceID Plus v2
- **레벨 3.5**: + Regional Prompt (멀티 캐릭터)
- **레벨 4**: + 캐릭터 LoRA 트레이닝 (전원)
- **레벨 5**: LoRA + IP-Adapter + ControlNet + Regional (풀콤보)

### 미적용 기술 → 해결하는 문제 매핑
| 문제 | 해결 기술 | Sub-Phase |
|------|----------|-----------|
| 대화 씬 멀티 캐릭터 불가 | Pipeline Inpaint (txt2img → img2img) | G |
| 복장 드리프트 (프롬프트 한계) | 캐릭터 LoRA 트레이닝 | D |
| 복장 드리프트 (Negative 부재) | Negative Prompt 복장 보호 | F |

### 멀티캐릭터 생성 테스트 결과 (2026-03-07)

`test_sdxl_compare/multi_char_test/` 디렉토리에서 3가지 접근법 비교:

| 접근법 | 방식 | 성공률 | 주요 문제 |
|--------|------|--------|----------|
| **Regional Prompter** | BREAK 토큰으로 좌/우 영역 분할 | ~20-30% | 512x768 세로 분할 → 256x768 너무 좁음, 복장 혼합 |
| **Regional + Dual IP-Adapter** | Regional + 캐릭터별 참조 이미지 | ~10% | IP-Adapter가 영역별이 아닌 전역 적용 → 한 캐릭터만 지배 |
| **Pipeline Inpaint** | Step1 txt2img(A) → Step2 img2img inpaint(B) | ~60% | 가장 유망하나 두 번째 캐릭터 크기 조절 필요 |

**결론**: Pipeline Inpaint 방식이 현 SD WebUI 환경에서 가장 현실적. Regional Prompter는 세로 이미지에서 근본적 한계.

### NoobAI-XL 테스트 결과 (2026-03-07)
"월요일의 예민이" 8씬 시나리오 V1/V2 비교 테스트 (`test_sdxl_compare/`):

| 항목 | SD 1.5 + Phase 30 | NoobAI-XL |
|------|-------------------|-----------|
| 얼굴 일관성 | ⭐⭐ (IP-Adapter 의존) | ⭐⭐⭐⭐⭐ (프롬프트만으로 동일인) |
| 복장 유지 | ⭐⭐⭐⭐ (enforce로 강제) | ⭐⭐⭐ (색상 명시해도 누락) |
| 프롬프트 준수 | ⭐⭐ | ⭐⭐⭐⭐ |
| 속도 | ⭐⭐⭐⭐⭐ (14초) | ⭐⭐ (60초) |

**결론**: SD 1.5 + Phase 30-A/B + IP-Adapter가 현시점 더 안정적. SDXL 전환은 복장 제어 문제 해결 후 재검토.

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

### Sub-Phase E: Outfit Profile 시스템 (6주 후)

캐릭터별 복장 세트를 DB에서 관리하여 의도적 의상 변경만 허용.

| # | 항목 | 설명 |
|---|------|------|
| E-1 | OutfitProfile 모델 추가 | Character 1:N OutfitProfile (name, clothing_tags JSONB, reference media_asset_id, is_default) |
| E-2 | 기본 복장 자동 주입 | 스토리보드 생성 시 캐릭터 default outfit의 clothing_tags를 Exclusive하게 주입 |
| E-3 | 씬별 의상 변경 UI | Scene 편집에서 의도적 outfit 선택 가능 (드롭다운) |
| E-4 | Gemini 복장 변경 마커 | `[OUTFIT: 여름 사복]` 마커로 의도적 변경 지시 |

**파일**: `models/character.py` (신규 모델), `schemas.py`, `services/prompt/composition.py`, Frontend 캐릭터 편집 페이지
**테스트**: OutfitProfile CRUD 테스트, 프롬프트 주입 테스트, 마이그레이션 테스트
**예상 소요**: 1주

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

---

### Sub-Phase G: 멀티캐릭터 Inpaint 파이프라인 (4주 후)

Pipeline 방식(txt2img → img2img inpaint)으로 2인 동시 출연 구현.

| # | 항목 | 설명 |
|---|------|------|
| G-1 | Inpaint 영역 자동 계산 | 포즈 데이터 기반 캐릭터 B의 마스크 영역 자동 생성 (좌/우 반분할 기본) |
| G-2 | Pipeline Step 1: 캐릭터 A 단독 생성 | 기존 txt2img 파이프라인으로 A 생성 (전체 프레임, B 위치는 빈 공간) |
| G-3 | Pipeline Step 2: 캐릭터 B Inpaint | Step 1 결과에 img2img inpaint로 B 추가 (마스크 영역, denoising 0.75~0.85) |
| G-4 | IP-Adapter 단계별 적용 | Step 1: A의 참조 이미지, Step 2: B의 참조 이미지로 교체 |
| G-5 | Inpaint 품질 튜닝 | denoising strength, mask blur, inpaint padding 최적값 탐색 |
| G-6 | scene_mode=multi 자동 연동 | 기존 `scene_mode` 필드 활용 — multi 씬에서 자동으로 Pipeline 방식 실행 |

**파일**: `services/generation.py` (신규 inpaint 경로), `services/controlnet.py` (마스크 빌드), `services/generation_controlnet.py` (Step별 IP-Adapter 교체)
**검증**: 대화 씬 10개 생성 → 2인 동시 출연 성공률 > 70% 목표
**테스트**: Inpaint 마스크 계산 테스트, Pipeline 2-step 통합 테스트
**예상 소요**: 1주
**선행 조건**: Sub-Phase C (Dual IP-Adapter) 완료

---

## 실행 순서 및 타임라인

```
Week 1     Sub-Phase A (Config 튜닝) ■■ 0.5일                    ✅ 완료
           Sub-Phase B (Gemini 템플릿) ■■■■ 2일                  ✅ 완료
           Sub-Phase F (네이밍 개선 + 복장 보호) ■■ 1일             ← 즉시 착수
Week 2-3   Sub-Phase C (Dual IP-Adapter) ■■■■■■ 3일
           Sub-Phase D-1~D-2 (파이프라인 + 이미지 준비) ■■■■■■■■■■ 5일
Week 3-6   Sub-Phase D-3~D-6 (LoRA 트레이닝 + 검증) ■■■■■■■■■■■■■■■ 3주
Week 4-5   Sub-Phase G (멀티캐릭터 Inpaint) ■■■■■■■■■■ 1주        (C 완료 후)
Week 6-7   Sub-Phase E (Outfit Profile) ■■■■■■■■■■ 1주
```

## 성공 지표

| 지표 | 현재 | A+B 후 | F+C 후 | 전체 완료 |
|------|------|--------|--------|----------|
| 씬 간 얼굴 일관성 | ~60% | 75% | 80% | 95% |
| 씬 간 복장 일관성 | ~30% | 70% | 80% | 95% |
| IP-Adapter weight | 0.50 | 0.50 | 0.55+0.35 | 0.55+0.35 |
| Character LoRA 보유율 | 2/13 | 2/13 | 2/13 | 13/13 |
| 2인 동시 출연 성공률 | 0% | 0% | 0% | >70% |

## 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| IP-Adapter weight 상향 → 프롬프트 무시 | 창의성 저하 | A/B 테스트로 최적값 탐색 (0.45~0.55 범위) |
| Dual IP-Adapter VRAM 초과 | M4 Pro 24GB 한계 | 단일 Unit fallback, 해상도 하향 검토 |
| LoRA 트레이닝 과적합 | 표정/포즈 다양성 저하 | rank 32 + 다양한 학습 이미지 + early stopping |
| Clothing Exclusive 부작용 | 의도적 의상 변경 불가 | clothing_override 메커니즘 보존 (B-4) |
| SDXL 전환 시 LoRA 무효화 | 재트레이닝 비용 | 현 SD 1.5 기반 우선, SDXL은 별도 Phase |
| Pipeline Inpaint 경계 부자연스러움 | 2인 씬 품질 저하 | mask blur + inpaint padding 튜닝, denoising 0.75~0.85 |
| Regional Prompter 세로 이미지 한계 | 512x768 좌우 분할 너무 좁음 | Pipeline Inpaint 방식으로 대체 (테스트 완료) |
