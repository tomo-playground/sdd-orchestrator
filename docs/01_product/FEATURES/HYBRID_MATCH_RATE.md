# Hybrid Match Rate (WD14 + Gemini Vision)

> 상태: 완료 (Phase 33, 22/22)
> 우선순위: P1
> 선행 관계: ✅ Phase 16 (WD14 Smart Validation) 완료

---

## 배경

### 현재 한계

| 문제 | 설명 |
|------|------|
| **하드코딩 의존** | `WD14_UNMATCHABLE_TAGS` (42개 태그)를 수동 등록 — 프롬프트에 새 태그 추가될 때마다 누락 |
| **낮은 매치레이트** | 실제 씬에서 4~8% — camera, lighting, mood, location 태그가 모두 missing 처리 |
| **반쪽 평가** | `adjusted_match_rate`는 감지 불가 태그를 제외하지만, 그 태그들의 이행도는 아예 평가하지 않음 |
| **지표 무의미** | 매치레이트가 항상 낮아서 품질 판단 기준으로 사용 불가 |

### 업계 접근법 비교

| 방법 | 원리 | 장단점 |
|------|------|--------|
| **CLIPScore** | CLIP 임베딩 코사인 유사도 | 간단하나 "bag of words" 문제, 구성 요소 구분 불가 |
| **TIFA** | LLM → 질문 분해 → VQA 답변 | 태그별 분석 가능, 구현 복잡 |
| **VQAScore** | VQA 모델 "Does this show X?" → P(Yes) | SOTA 정확도, 대형 GPU 필요 (FlanT5-XXL ~22GB) |
| **멀티모달 LLM** | Gemini/GPT-4o에 이미지+프롬프트 전송 | 유연, 모든 태그 커버, API 비용 발생 |

### 설계 결정

**WD14 + Gemini 하이브리드 채택 이유:**
- WD14: 시각적 태그(인물, 의상, 표정) 감지에 이미 검증됨 — 무료, 빠름
- Gemini: 비시각적 태그(카메라, 조명, 분위기, 배경) 평가 — 이미 API 사용 중
- 태그의 `group_name` DB 메타데이터로 라우팅 — 하드코딩 제거
- 비용: 씬당 ~$0.0002 (월 ~500원 수준)

---

## 목표

1. **하드코딩 제거**: `WD14_UNMATCHABLE_TAGS` 대신 `group_name` 기반 자동 라우팅
2. **100% 태그 커버리지**: WD14 감지 불가 태그도 Gemini로 평가
3. **통합 매치레이트**: WD14 + Gemini 결과를 합산한 단일 지표
4. **태그별 평가 결과**: 어떤 태그가 맞고 틀렸는지 + 평가 방법(wd14/gemini) 표시
5. **기존 호환**: 현재 API 스키마/DB 스키마 최소 변경
6. **UX 무지연**: Gemini 평가는 비동기 처리, 이미지 생성 흐름에 지연 없음

---

## 아키텍처

### DB group_name → 평가 방법 매핑 (SSOT)

DB `tags` 테이블의 45개 `group_name`을 3개 평가 카테고리로 분류:

#### WD14_DETECTABLE_GROUPS (27개) — 시각적 특징, 로컬 모델

기존 22개 + 레거시 미분류 5개 추가:

```python
# 기존 22개 유지
"subject", "hair_color", "hair_length", "hair_style", "hair_accessory",
"eye_color", "expression", "gaze", "pose", "appearance", "body_type",
"body_feature", "skin_color",
"clothing_top", "clothing_bottom", "clothing_outfit", "clothing_detail",
"legwear", "footwear", "accessory",
"action_body", "action_hand", "action_daily",

# 신규 추가 (레거시 미분류 그룹 — WD14로 감지 가능)
"clothing",      # 935개 — 세분화 이전 레거시 의상 태그
"action",        # 229개 — 세분화 이전 레거시 액션 태그
"gesture",       #  35개 — 손동작/제스처 (시각적)
"eye_detail",    #   3개 — 눈 디테일 (시각적)
"identity",      #  57개 — 캐릭터 정체성 (hair/eye 기반, WD14 감지 가능)
```

#### GEMINI_DETECTABLE_GROUPS (11개) — 구도/분위기/환경, Gemini Vision

```python
GEMINI_DETECTABLE_GROUPS: frozenset[str] = frozenset({
    "camera",                  #  59개 — cowboy_shot, close-up, from_above
    "lighting",                #  68개 — sidelighting, soft_shadow
    "mood",                    #  86개 — peaceful, romantic, melancholy
    "environment",             # 224개 — 환경 전반
    "location_outdoor",        #  84개 — park, street, beach
    "location_indoor",         #  26개 — indoors
    "location_indoor_specific",#  44개 — classroom, library, cafe
    "location_indoor_general", #   1개 — indoors 일반
    "time_weather",            #  74개 — rain, sunset, night_sky
    "time_of_day",             #   2개 — morning, night
    "weather",                 #   5개 — rain, snow, cloudy
})
```

#### SKIPPABLE_GROUPS (7개) — 평가 불필요, 분모 제외

```python
SKIPPABLE_GROUPS: frozenset[str] = frozenset({
    "quality",            #  32개 — masterpiece, best_quality
    "skip",               #  39개 — 명시적 스킵 태그
    "style",              #  60개 — flat_color, cel_shading (렌더링 스타일)
    "danbooru_validated",  #   4개 — 메타 태그
    "background_type",    #  18개 — simple_background, white_background
    "particle",           #   7개 — 파티클 효과 (감지 어려움)
    None,                 # DB 미등록 태그 (LoRA 트리거 등)
})
```

### 태그 라우팅 흐름

```
프롬프트 토큰: "(blue_hair:1.2), cowboy_shot, masterpiece, hrkzdrm_cs"
                 │
                 ├─ 1. _strip_weight() → "blue_hair"
                 │
                 ├─ 2. TagCategoryCache.get_category("blue_hair")
                 │     → group_name = "hair_color"
                 │
                 ├─ 3. 라우팅:
                 │     ├─ "hair_color" ∈ WD14_DETECTABLE_GROUPS  → WD14 평가
                 │     ├─ "cowboy_shot" → "camera" ∈ GEMINI_DETECTABLE_GROUPS → Gemini 평가
                 │     ├─ "masterpiece" → "quality" ∈ SKIPPABLE_GROUPS → skipped
                 │     └─ "hrkzdrm_cs" → None (DB 미등록) ∈ SKIPPABLE_GROUPS → skipped
                 │
                 └─ match_rate = (WD14 matched + Gemini matched) / (WD14 total + Gemini total)
```

### Gemini Vision 평가 프롬프트

```
이미지와 Danbooru 태그 목록이 주어집니다.
각 태그가 이미지에 시각적으로 반영되었는지 판별하세요.

태그는 Danbooru 형식(언더바 구분)입니다:
- cowboy_shot: 허리~무릎 사이 프레이밍
- sidelighting: 측면 조명
- outdoors: 실외 배경

태그 목록: cowboy_shot, sidelighting, outdoors

각 태그에 대해 JSON으로 응답:
[
  {"tag": "cowboy_shot", "present": true, "confidence": 0.9},
  {"tag": "sidelighting", "present": true, "confidence": 0.7},
  {"tag": "outdoors", "present": false, "confidence": 0.8}
]
```

### 데이터 흐름 (2-Phase 비동기)

```
이미지 생성 완료
  │
  ├─ Phase 1: WD14 평가 (즉시, 동기)
  │   ├─ classify_prompt_tokens() → wd14_tokens, gemini_tokens, skipped
  │   ├─ compare_prompt_to_tags(wd14_tokens, wd14_tags)
  │   ├─ wd14_match_rate 계산 → 즉시 UI 반영
  │   └─ SSE/응답으로 wd14_match_rate 반환
  │
  └─ Phase 2: Gemini 평가 (비동기, 백그라운드)
      ├─ gemini_tokens가 0개면 스킵
      ├─ evaluate_tags_with_gemini(image, gemini_tokens)
      ├─ 통합 match_rate = (wd14_matched + gemini_matched) / total
      └─ DB 업데이트 + Frontend 폴링/SSE로 최종 매치레이트 갱신
```

**UX 흐름**:
1. 이미지 생성 직후 → WD14 매치레이트 **즉시** 표시 (기존과 동일 속도)
2. 1~2초 후 → Gemini 결과 도착 → **통합** 매치레이트로 갱신
3. Gemini 실패 시 → WD14 매치레이트만 표시 (degradation)

---

## Phase 33: Hybrid Match Rate

### Sprint A: 그룹 매핑 정비 (P0)

- [ ] A-1: `WD14_DETECTABLE_GROUPS` 확장 — 레거시 미분류 5개 추가 (`clothing`, `action`, `gesture`, `eye_detail`, `identity`)
- [ ] A-2: `GEMINI_DETECTABLE_GROUPS` 상수 정의 (`config.py`) — DB 실제 group_name 기반 11개
- [ ] A-3: `SKIPPABLE_GROUPS` 상수 정의 — quality, skip, style 등 7개
- [ ] A-4: `WD14_UNMATCHABLE_TAGS` 제거 — 그룹 기반 라우팅으로 완전 대체
- [ ] A-5: `classify_prompt_tokens()` 함수 — `_strip_weight()` 전처리 + group_name 기반 3그룹 분류

### Sprint B: Gemini Vision 평가 엔진 (P0)

- [ ] B-1: `evaluate_tags_with_gemini()` 함수 — 이미지(base64) + 태그 목록 → 태그별 present/confidence 반환
- [ ] B-2: Gemini 프롬프트 템플릿 작성 (`templates/validate_image_tags.j2`) — Danbooru 태그 설명 포함
- [ ] B-3: LLM Provider 연동 — `services/llm/` 패키지 활용, safety settings + fallback 적용
- [ ] B-4: 결과 파싱 + 에러 처리 — JSON 파싱 실패 시 해당 태그 전체 skipped 처리 (graceful degradation)

### Sprint C: 통합 매치레이트 (P0)

- [ ] C-1: `validate_scene_image()` 리팩토링 — WD14 즉시 반환 + Gemini 비동기 호출
- [ ] C-2: `compare_prompt_to_tags()` 수정 — wd14_tokens만 비교 (gemini_tokens 제외)
- [ ] C-3: `compute_adjusted_match_rate()` deprecated — 하이브리드 통합 매치레이트가 대체
- [ ] C-4: Gemini 결과 도착 시 DB 업데이트 (`scene_quality_scores.match_rate` 갱신)
- [ ] C-5: API 응답 스키마 확장 — `evaluation_details: [{tag, method, present, confidence}]` 필드 추가

### Sprint D: DB + Frontend (P1)

- [ ] D-1: `scene_quality_scores` 테이블에 `evaluation_details` JSONB 컬럼 추가 (Alembic 마이그레이션)
- [ ] D-2: Frontend — Gemini 결과 폴링/SSE 수신 후 매치레이트 실시간 갱신
- [ ] D-3: Frontend `SceneInsightsContent` — 매치레이트 색상 기준 조정 (하이브리드 기준)
- [ ] D-4: Frontend 매치레이트 상세 팝업 — 태그별 매칭 결과 + 평가 방법(WD14/Gemini) 뱃지 표시

### Sprint E: 최적화 + 테스트 (P2)

- [ ] E-1: Gemini 호출 최적화 — gemini_tokens 0개면 스킵
- [ ] E-2: 배치 평가 시 Gemini 호출 병합 — 같은 이미지의 여러 씬 태그를 한 번에 전송
- [ ] E-3: 단위 테스트 — classify_prompt_tokens, evaluate_tags_with_gemini, 통합 match_rate
- [ ] E-4: 통합 테스트 — 실제 이미지 + 프롬프트 E2E 검증

---

## 수락 기준

| # | 기준 |
|---|------|
| 1 | `WD14_UNMATCHABLE_TAGS` 완전 제거 — 그룹 기반 라우팅으로 대체 |
| 2 | DB 45개 group_name 전체가 WD14/Gemini/Skippable 중 하나에 매핑 (누락 0) |
| 3 | camera, lighting, mood, location 태그가 Gemini로 평가됨 |
| 4 | 통합 매치레이트가 실제 이미지 품질 반영 (기존 4~8% → 50~90%) |
| 5 | Gemini 평가 실패 시 WD14 매치레이트만 표시 (graceful degradation) |
| 6 | 이미지 생성→WD14 표시 지연 없음 (Gemini는 비동기) |
| 7 | 씬당 Gemini API 비용 $0.001 이하 |

---

## 구현 영향 범위

### Backend

| 파일 | 변경 |
|------|------|
| `config.py` | `GEMINI_DETECTABLE_GROUPS`, `SKIPPABLE_GROUPS` 추가. `WD14_DETECTABLE_GROUPS` 확장. `WD14_UNMATCHABLE_TAGS` 제거 |
| `services/validation.py` | `classify_prompt_tokens()` 신규, `validate_scene_image()` 리팩토링, `evaluate_tags_with_gemini()` 신규, `compute_adjusted_match_rate()` deprecated |
| `templates/validate_image_tags.j2` | Gemini 프롬프트 템플릿 신규 |
| `schemas.py` | `SceneValidationResponse`에 `evaluation_details` 필드 추가 |
| `models/scene_quality.py` | `evaluation_details` JSONB 컬럼 추가 |
| `alembic/versions/` | 마이그레이션 1건 |

### Frontend

| 파일 | 변경 |
|------|------|
| `components/studio/SceneInsightsContent.tsx` | 매치레이트 색상 기준 조정, 비동기 갱신 |
| `types/index.ts` | `ImageValidation` 타입에 `evaluation_details` 추가 |
| `store/actions/imageProcessing.ts` | Gemini 결과 폴링/수신 로직 |

---

## 테스트 계획

| 범위 | 항목 | 예상 수 |
|------|------|---------|
| 그룹 매핑 | 45개 group_name 전수 매핑 검증, 누락 감지 | 5 |
| 태그 라우팅 | classify_prompt_tokens — 가중치 태그, DB 미등록, 경계 케이스 | 8 |
| Gemini 평가 | API 호출 mock, JSON 파싱, 에러/타임아웃 처리 | 6 |
| 통합 매치레이트 | WD14+Gemini 합산, Gemini 실패 시 fallback | 6 |
| DB 저장 | evaluation_details JSONB 저장/조회 | 3 |
| E2E | 실제 이미지 + 프롬프트 → 매치레이트 반환 | 2 |
| **합계** | | **~30** |

---

## 작업 순서

```
Sprint A (그룹 매핑) ─── Sprint B (Gemini 엔진)
         │                        │
         └──── 독립 개발 가능 ────┘
                      │
              Sprint C (통합 + 비동기)
                      │
              Sprint D (DB + Frontend)
                      │
              Sprint E (최적화 + 테스트)
```

Sprint A, B는 병렬 개발 가능. C는 A+B 완료 후 통합.
