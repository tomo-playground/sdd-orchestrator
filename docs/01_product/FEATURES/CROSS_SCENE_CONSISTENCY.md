# Cross-Scene Consistency (씬 간 캐릭터 시각적 일관성)

> 상태: **Backend 완료 (D-1~D-3)**, Frontend 미착수 (D-4) — Phase 16-D
> 선행: Phase 16-A (Critical Failure Detection ✅), 16-B (Adjusted Match Rate ✅), 16-C (Auto-Regen + Identity Ranking ✅)
> 관련: [CHARACTER_CONSISTENCY.md](CHARACTER_CONSISTENCY.md)

---

## 1. 배경 및 문제 정의

### 1-1. 현재 한계

Phase 16-A~C는 **개별 씬 단위** WD14 검증 인프라를 구축했다:

| 완료 인프라 | 역할 |
|------------|------|
| `compute_identity_score()` | 단일 씬 ↔ 캐릭터 DB identity 태그 일치도 |
| `compute_adjusted_match_rate()` | WD14 감지 불가 그룹 제외한 보정 match rate |
| Auto-Regen + Identity Ranking | Critical Failure 시 자동 재생성 + identity 기반 후보 선택 |

그러나 **스토리보드 전체에 걸친 시각적 일관성**은 측정하지 않는다:

| 문제 | 예시 |
|------|------|
| **씬 간 머리색 변경** | Scene 1: `black_hair` → Scene 3: `brown_hair` (같은 캐릭터) |
| **씬 간 눈색 변경** | Scene 2: `blue_eyes` → Scene 5: `green_eyes` |
| **씬 간 체형 변경** | Scene 1: `long_hair` → Scene 4: `short_hair` |
| **drift 비가시성** | 개별 match rate는 높은데 씬 간 불일치 발생 (각 씬이 DB와는 부분 일치) |

### 1-2. 해결 방향

캐릭터의 DB identity 태그를 **baseline**으로, 각 씬에서 WD14가 감지한 태그를 **signature**로 추출하여 그룹별 drift를 시각화한다.

---

## 2. 용어 정의

| 용어 | 설명 |
|------|------|
| **CharacterSignature** | WD14 감지 결과에서 `IDENTITY_SCORE_GROUPS` (7개 그룹) 태그만 추출한 per-scene-per-character 시그니처 |
| **Baseline** | 캐릭터 DB에 등록된 identity 태그 (`character_tags` → `IDENTITY_SCORE_GROUPS` 필터) |
| **Drift** | Baseline과 Signature 간 불일치. 그룹 단위로 측정 (match/mismatch/missing/extra) |
| **Drift Score** | 0.0(완전 일치) ~ 1.0(완전 불일치). 그룹별 가중치 적용 가중 평균 |
| **Identity Score** | 기존 `compute_identity_score()` 반환값 (0.0~1.0). Drift Score = 1 - Identity Score |

---

## 3. 목표

- 스토리보드 전체 씬에 걸친 캐릭터 시각적 일관성을 **정량적으로 측정**
- 어떤 씬에서 어떤 그룹(머리색, 눈색 등)이 drift했는지 **히트맵으로 시각화**
- 기존 WD14 인프라(`identity_score.py`, `validation.py`, `scene_quality_scores`) **최대 재사용**

---

## 4. 설계 원칙

| 원칙 | 설명 |
|------|------|
| **On-demand 계산** | 신규 테이블 없음. `scene_quality_scores`에 2개 컬럼 추가만으로 캐시 |
| **WD14 재실행 스킵** | `identity_tags_detected`가 이미 캐시되어 있으면 WD14 재실행하지 않음 |
| **그룹별 가중치** | 시각적 영향력에 따라 hair_color(1.0) > eye_color(0.8) > ... > skin_color(0.3) |
| **기존 함수 재사용** | `extract_character_identity_tags()`, `compute_identity_score()`, `load_character_identity_tags()` 활용 |

---

## 5. Phase 분해

### Phase D-1: Signature 추출 + DB 확장

| # | 항목 | 설명 |
|---|------|------|
| 1 | `scene_quality_scores`에 `identity_score` 컬럼 추가 | `Float`, nullable. 기존 `compute_identity_score()` 결과 저장 |
| 2 | `scene_quality_scores`에 `identity_tags_detected` 컬럼 추가 | `JSONB`, nullable. WD14가 감지한 identity 태그를 그룹별로 저장 |
| 3 | Alembic 마이그레이션 생성 | `ALTER TABLE scene_quality_scores ADD COLUMN ...` × 2 |
| 4 | `extract_identity_signature()` 함수 구현 | WD14 결과 → `{group_name: [detected_tags]}` dict 추출 |
| 5 | 기존 batch_validate 흐름에 identity 캐시 저장 통합 | validate 시 identity_score + identity_tags_detected 자동 저장 |

**`identity_tags_detected` JSONB 구조**:

```json
{
  "hair_color": ["black_hair"],
  "eye_color": ["blue_eyes"],
  "hair_length": ["long_hair"],
  "hair_style": ["ponytail"],
  "skin_color": [],
  "body_feature": [],
  "appearance": ["1girl"]
}
```

**DB 스키마 변경**:

```python
# models/scene_quality.py — 추가 컬럼
identity_score: Mapped[float | None] = mapped_column(Float)
identity_tags_detected: Mapped[dict | None] = mapped_column(JSONB)
```

### Phase D-2: Drift 알고리즘

| # | 항목 | 설명 |
|---|------|------|
| 1 | `IDENTITY_GROUP_WEIGHTS` 상수 정의 | `config.py`에 7개 그룹별 가중치 dict |
| 2 | `compute_group_drift()` 함수 구현 | 단일 그룹의 baseline vs detected 비교 → match/mismatch/missing/extra |
| 3 | `compute_scene_drift()` 함수 구현 | 전체 그룹 drift 계산 → 가중 drift score |
| 4 | `compute_storyboard_consistency()` 함수 구현 | 전체 씬 × 전체 캐릭터 drift 매트릭스 반환 |
| 5 | 단위 테스트 작성 | drift 계산 edge case (빈 태그, 단일 씬, 다중 캐릭터) |

**그룹별 가중치**:

```python
# config.py
IDENTITY_GROUP_WEIGHTS: dict[str, float] = {
    "hair_color": 1.0,    # 가장 눈에 띄는 변화
    "eye_color": 0.8,     # 클로즈업에서 중요
    "hair_length": 0.7,   # 구조적 변화
    "hair_style": 0.7,    # 구조적 변화
    "appearance": 0.5,    # 전반적 외형
    "body_feature": 0.4,  # 미세 특징
    "skin_color": 0.3,    # 조명 영향 큼 → 낮은 가중치
}
```

**Drift 결과 타입**:

```python
class GroupDrift(TypedDict):
    group: str
    baseline_tags: list[str]   # DB에 등록된 태그
    detected_tags: list[str]   # WD14가 감지한 태그
    status: str                # "match" | "mismatch" | "missing" | "extra" | "no_data"
    weight: float              # 그룹 가중치

class SceneDrift(TypedDict):
    scene_id: int
    scene_order: int
    character_id: int
    identity_score: float      # 0.0~1.0 (기존)
    drift_score: float         # 0.0~1.0 (1 - identity_score, 가중)
    groups: list[GroupDrift]

class ConsistencyResult(TypedDict):
    storyboard_id: int
    overall_consistency: float  # 전체 평균 (1 - avg drift)
    scenes: list[SceneDrift]
```

### Phase D-3: API

| # | 항목 | 설명 |
|---|------|------|
| 1 | `GET /quality/consistency/{storyboard_id}` 엔드포인트 | ConsistencyResult 반환 |
| 2 | 캐시 활용 로직 | `identity_tags_detected`가 있으면 WD14 재실행 스킵 |
| 3 | `response_model` 정의 | Pydantic 스키마 (`ConsistencyResponse`) |
| 4 | 에러 처리 | 스토리보드 없음 (404), 씬 없음 (빈 결과), WD14 실패 (partial 결과) |

**API 응답 예시**:

```json
{
  "storyboard_id": 42,
  "overall_consistency": 0.85,
  "scenes": [
    {
      "scene_id": 101,
      "scene_order": 1,
      "character_id": 5,
      "identity_score": 1.0,
      "drift_score": 0.0,
      "groups": [
        {"group": "hair_color", "baseline_tags": ["black_hair"], "detected_tags": ["black_hair"], "status": "match", "weight": 1.0},
        {"group": "eye_color", "baseline_tags": ["blue_eyes"], "detected_tags": ["blue_eyes"], "status": "match", "weight": 0.8}
      ]
    },
    {
      "scene_id": 102,
      "scene_order": 2,
      "character_id": 5,
      "identity_score": 0.71,
      "drift_score": 0.29,
      "groups": [
        {"group": "hair_color", "baseline_tags": ["black_hair"], "detected_tags": ["brown_hair"], "status": "mismatch", "weight": 1.0},
        {"group": "eye_color", "baseline_tags": ["blue_eyes"], "detected_tags": ["blue_eyes"], "status": "match", "weight": 0.8}
      ]
    }
  ]
}
```

### Phase D-4: Frontend (ConsistencyPanel + DriftHeatmap)

| # | 항목 | 설명 |
|---|------|------|
| 1 | `ConsistencyPanel` 컴포넌트 | Studio QA 탭 내 일관성 대시보드 |
| 2 | `DriftHeatmap` 컴포넌트 | 씬(행) × 그룹(열) 매트릭스, 셀 색상으로 drift 표시 |
| 3 | Overall Consistency 표시 | 상단 요약 (전체 일관성 %, 경고 씬 수) |
| 4 | 씬 클릭 → 상세 drill-down | 해당 씬의 baseline vs detected 태그 비교 |

**DriftHeatmap 셀 색상**:

| 색상 | 상태 | 설명 |
|------|------|------|
| Green | `match` | Baseline과 일치 |
| Red | `mismatch` | Baseline과 불일치 (다른 태그 감지) |
| Amber | `missing` | Baseline에 있으나 감지되지 않음 |
| Gray | `no_data` | WD14 미실행 또는 해당 그룹 태그 없음 |

---

## 6. 의존성

| 의존성 | 상태 | 설명 |
|--------|------|------|
| `identity_score.py` | ✅ 완료 | `extract_character_identity_tags()`, `compute_identity_score()`, `load_character_identity_tags()` |
| `validation.py` | ✅ 완료 | WD14 추론 + 태그 매칭 |
| `quality.py` | ✅ 완료 | `batch_validate_scenes()`, `get_quality_summary()` |
| `scene_quality_scores` 테이블 | ✅ 완료 | match_rate, matched_tags, missing_tags, extra_tags 저장 중 |
| `IDENTITY_SCORE_GROUPS` | ✅ 완료 | 7개 그룹 (`config.py`) |
| `routers/quality.py` | ✅ 완료 | `/quality/batch-validate`, `/quality/summary`, `/quality/alerts` |

---

## 7. 테스트 전략

| Phase | 테스트 | 수량 |
|-------|--------|------|
| D-1 | `identity_tags_detected` JSONB 저장/조회, 마이그레이션 검증 | ~6 |
| D-2 | `compute_group_drift()`, `compute_scene_drift()`, `compute_storyboard_consistency()` 단위 테스트 | ~12 |
| D-3 | API 엔드포인트 (정상/404/빈 씬/캐시 히트) | ~6 |
| D-4 | DriftHeatmap 렌더링, 셀 색상 매핑, drill-down 인터랙션 | ~8 |
| **합계** | | **~32** |

---

## 8. 스코프 외

| 항목 | 이유 |
|------|------|
| 자동 재생성 트리거 | Phase 16-C Auto-Regen은 단일 씬 단위. 크로스씬 drift 기반 재생성은 별도 Phase |
| 의류(clothing) 그룹 drift | Scene Clothing Override가 씬별 의류 변경을 허용하므로 identity drift 대상 아님 |
| 실시간 검증 | 이미지 생성 직후 자동 consistency 체크는 별도 Phase. 현재는 on-demand API |
| 멀티 캐릭터 씬 대응 | 1씬 1캐릭터만 지원. 1씬 다중 캐릭터 매칭은 향후 확장 |
