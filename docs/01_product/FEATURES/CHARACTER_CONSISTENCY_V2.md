# Phase 30: 캐릭터 일관성 강화 (Character Consistency V2)

**상태**: 계획
**우선순위**: P0 (영상 품질 핵심)
**관련**: Phase 7-0 (ControlNet), Phase 8 (Multi-Style), CHARACTER_CONSISTENCY.md (V1)
**최종 갱신**: 2026-03-07

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

### Sub-Phase B: Gemini 템플릿 복장 고정 (1주 내)

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

## 실행 순서 및 타임라인

```
Week 1     Sub-Phase A (Config 튜닝) ■■ 0.5일
           Sub-Phase B (Gemini 템플릿) ■■■■ 2일
Week 2-3   Sub-Phase C (Dual IP-Adapter) ■■■■■■ 3일
           Sub-Phase D-1~D-2 (파이프라인 + 이미지 준비) ■■■■■■■■■■ 5일
Week 3-6   Sub-Phase D-3~D-6 (LoRA 트레이닝 + 검증) ■■■■■■■■■■■■■■■ 3주
Week 6-7   Sub-Phase E (Outfit Profile) ■■■■■■■■■■ 1주
```

## 성공 지표

| 지표 | 현재 | 목표 (A+B 후) | 목표 (전체 완료) |
|------|------|--------------|----------------|
| 씬 간 얼굴 일관성 (주관 평가) | ~60% | 75% | 95% |
| 씬 간 복장 일관성 (주관 평가) | ~30% | 70% | 95% |
| IP-Adapter weight | 0.35 | 0.50 | 0.55 (face) + 0.35 (body) |
| Character LoRA 보유율 | 2/13 (15%) | 2/13 (15%) | 13/13 (100%) |

## 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| IP-Adapter weight 상향 → 프롬프트 무시 | 창의성 저하 | A/B 테스트로 최적값 탐색 (0.45~0.55 범위) |
| Dual IP-Adapter VRAM 초과 | M4 Pro 24GB 한계 | 단일 Unit fallback, 해상도 하향 검토 |
| LoRA 트레이닝 과적합 | 표정/포즈 다양성 저하 | rank 32 + 다양한 학습 이미지 + early stopping |
| Clothing Exclusive 부작용 | 의도적 의상 변경 불가 | clothing_override 메커니즘 보존 (B-4) |
| SDXL 전환 시 LoRA 무효화 | 재트레이닝 비용 | 현 SD 1.5 기반 우선, SDXL은 별도 Phase |
