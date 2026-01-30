# Prompt Design Specification (v3.0)

SD 이미지 생성을 위한 프롬프트 설계 규칙.

## 📝 변경 이력

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v3.0 | 2026-01-30 | V3 12-Layer PromptBuilder, DB-driven 충돌 규칙, Character V3 relational tags |
| v2.0 | 2026-01-25 | Dynamic Tag Classification, Character Mode |
| v1.0 | 2025-01-25 | 초기 문서: Standard/LoRA Mode, Priority Order |

---

## 🏷️ Danbooru 스타일 정규화

시스템은 Stable Diffusion의 표준인 Danbooru 스타일의 태그 형식을 준수합니다.

### 1. 정규화 규칙 (Normalization)
모든 입력된 태그는 다음의 `normalize_prompt_token` 프로세스를 거칩니다:
- **소문자화**: 모든 대문자를 소문자로 변환
- **언더스코어 변환**: 공백(` `)을 언더스코어(`_`)로 변환 (`blue eyes` → `blue_eyes`)
- **특수문자 처리**: 앞뒤 공백 제거 및 중복 구분자 정리

### 2. 가중치 표현 (Emphasis)
- **NAI/Danbooru 스타일**: `(tag:1.1)` 형식을 사용하여 강조를 표현합니다.
- **중첩**: 가급적 중첩보다는 수치형 가중치를 권장합니다.

## 토큰 순서가 중요한 이유

Stable Diffusion은 프롬프트의 **앞쪽 토큰에 더 높은 가중치**를 부여합니다:
- 앞쪽 토큰: 이미지의 핵심 요소 결정
- 뒤쪽 토큰: 부가적 디테일로 처리
- 순서가 잘못되면 원하는 결과를 얻기 어려움

### 예시
```
# Good: 캐릭터가 중심
1girl, hatsune_miku, blue_hair, smile, standing, library

# Bad: 배경이 중심이 됨
library, standing, smile, blue_hair, hatsune_miku, 1girl
```

---

## 프롬프트 모드

LoRA 사용 여부에 따라 **다른 규칙**을 적용합니다.

### 왜 모드를 구분하는가?

| 상황 | 문제 | 해결 |
|------|------|------|
| **LoRA 사용** | LoRA 학습 편향이 장면 표현을 방해 | 장면 태그 우선, LoRA weight 조절 |
| **LoRA 미사용** | 캐릭터 특징을 프롬프트로 정의해야 함 | 표준 순서로 캐릭터 우선 기술 |

---

## Mode A: Standard (LoRA 미사용)

캐릭터를 프롬프트 태그로만 정의하는 경우.

### 특징
- 캐릭터 외모를 상세히 기술해야 함
- 장면 태그가 정상 작동
- 일관성 유지가 어려움 (씬마다 캐릭터 변동 가능)

### Priority Order

| Priority | Category | Examples |
|:--------:|:---------|:---------|
| 1 | **Quality** | `masterpiece`, `best quality` |
| 2 | **Subject** | `1girl`, `solo` |
| 3 | **Identity** | `hatsune miku` (태그만) |
| 4 | **Appearance** | `blue_twintails`, `blue_eyes` |
| 5 | **Clothing** | `black_dress`, `detached_sleeves` |
| 6 | **Expression** | `smile`, `blush` |
| 7 | **Gaze** | `looking at viewer` |
| 8 | **Pose** | `standing`, `sitting` |
| 9 | **Action** | `singing`, `dancing` |
| 10 | **Camera** | `close-up`, `full body` |
| 11 | **Location** | `concert stage`, `library` |
| 12 | **Time/Weather** | `night`, `sunset` |
| 13 | **Lighting** | `colorful lights`, `spotlight` |
| 14 | **Mood** | `energetic`, `peaceful` |
| 15 | **Style** | `anime`, `digital art` |

### 예시
```
masterpiece, best quality,
1girl, hatsune_miku,
blue_twintails, blue_eyes, hair_ribbon,
black_dress, detached_sleeves, thighhighs,
smile, looking_at_viewer,
standing, singing,
close-up,
concert_stage, night,
colorful_lights,
energetic
```

---

## Mode B: LoRA Mode (LoRA 사용)

캐릭터 LoRA를 사용하여 일관성을 유지하는 경우.

### 특징
- LoRA가 캐릭터 외모를 정의 → Appearance 태그 최소화
- **장면 태그가 LoRA 학습 편향에 의해 무시될 수 있음**
- 장면 표현을 위해 특별한 처리 필요

### 핵심 원칙

> **"장면이 복잡할수록 LoRA를 약하게"**

| 장면 복잡도 | LoRA Weight | 장면 태그 강조 |
|------------|:-----------:|:-------------:|
| 단순 (기본 포즈) | 0.7~0.8 | 없음 |
| 보통 (다른 포즈) | 0.5~0.6 | `(tag:1.1)` |
| 복잡 (액션/특수 구도) | 0.3~0.4 | `(tag:1.2~1.3)` |

### Priority Order (변경됨!)

| Priority | Category | 변경점 |
|:--------:|:---------|:-------|
| 1 | **Quality** | 동일 |
| 2 | **Subject** | 동일 |
| 3 | **Trigger** | LoRA 트리거 워드 (앞쪽 배치) |
| 4 | **Scene Core** | ⬆️ **Pose/Action/Camera 우선!** |
| 5 | **Expression/Gaze** | 장면 연출 요소 |
| 6 | **Appearance** | ⬇️ LoRA가 처리하므로 보조적 |
| 7 | **Location** | 배경 |
| 8 | **Time/Lighting/Mood** | 분위기 |
| 9 | **Style** | 스타일 |
| 99 | **LoRA Tag** | `<lora:name:weight>` 맨 끝 |

### 기본 구조
```
[Quality] [Subject] [Trigger] [Scene Core] [Expression] [Appearance] [Location] [Atmosphere] [LoRA]
```

### 예시: 단순 장면
```
masterpiece, best quality,
1boy, midoriya_izuku,
standing, looking_at_viewer,
smile,
green_hair, freckles,
classroom, daytime,
soft_lighting,
<lora:mha_midoriya:0.7>
```

### 예시: 복잡한 장면
```
masterpiece, best quality,
1boy, midoriya_izuku,
(sitting:1.2), (cooking:1.2), (close-up:1.1),
focused expression, looking down,
green hair,
(kitchen:1.1), warm lighting,
cozy atmosphere,
<lora:mha_midoriya:0.4>
```

### BREAK 활용 (권장)
캐릭터와 장면을 분리하여 LoRA 편향 최소화:
```
masterpiece, best quality,
1boy, midoriya_izuku, green hair, freckles,
<lora:mha_midoriya:0.5>
BREAK
(sitting:1.2), (cooking:1.2),
focused expression, looking down,
kitchen, close-up,
warm lighting, cozy
```

---

## Mode 비교 요약

| 항목 | Standard Mode | LoRA Mode |
|------|---------------|-----------|
| **캐릭터 정의** | 프롬프트로 상세 기술 | LoRA + 트리거 워드 |
| **Appearance 위치** | 앞쪽 (Priority 4) | 뒤쪽 (Priority 6) |
| **Scene Core 위치** | 중간 (Priority 8-10) | 앞쪽 (Priority 4) |
| **장면 태그 강조** | 불필요 | 필요 `(tag:1.2)` |
| **BREAK 사용** | 선택적 | 권장 |
| **일관성** | 낮음 | 높음 |
| **장면 표현력** | 높음 | 조절 필요 |

---

## V3: 12-Layer Prompt Builder

> v3.0 신규. `backend/services/prompt/v3_composition.py`의 `V3PromptBuilder` 참조.

V3에서는 태그를 **12개 시맨틱 레이어**에 배치하여 순서를 결정합니다.
각 태그의 `default_layer` 값 (tags 테이블)이 배치 기준입니다.

### 레이어 정의

| Layer | 이름 | 역할 | 예시 |
|:-----:|------|------|------|
| 0 | **Quality** | 품질 | `masterpiece`, `best_quality` |
| 1 | **Subject** | 인원 | `1girl`, `solo` |
| 2 | **Identity** | 캐릭터 LoRA + 트리거 | `midoriya_izuku`, `<lora:...>` |
| 3 | **Body** | 신체 특징 | `long_hair`, `blue_eyes` |
| 4 | **Main Cloth** | 주요 의상 | `school_uniform`, `dress` |
| 5 | **Detail Cloth** | 의상 디테일 | `pleated_skirt`, `ribbon` |
| 6 | **Accessory** | 악세서리 | `glasses`, `hat` |
| 7 | **Expression** | 표정 (1.1x 부스트) | `smile`, `blush` |
| 8 | **Action** | 행동 (1.1x 부스트) | `sitting`, `running` |
| 9 | **Camera** | 카메라 앵글 | `close-up`, `from_above` |
| 10 | **Environment** | 배경/장소 | `classroom`, `night` |
| 11 | **Atmosphere** | 분위기 + 스타일 LoRA | `soft_lighting`, `anime` |

### 특수 처리

- **BREAK 삽입**: Layer 6 이후 (캐릭터 LoRA 사용 시) → LoRA 편향 분리
- **Expression/Action 부스트**: Layer 7, 8의 태그에 자동 `(tag:1.1)` 적용
- **Quality 자동 추가**: Layer 0이 비어있으면 `masterpiece, best_quality` 삽입
- **LoRA 트리거 자동 감지**: `LoRATriggerCache`로 씬 태그에서 LoRA 자동 활성화

### 사용 예시

```python
from services.prompt.v3_composition import V3PromptBuilder

builder = V3PromptBuilder(db)
prompt = builder.compose_for_character(
    character_id=1,
    scene_tags=["sitting", "classroom", "smile", "close-up"],
    style_loras=[{"name": "chibi-laugh", "weight": 0.6}]
)
# → "masterpiece, best_quality, 1boy, midoriya_izuku, <lora:mha_midoriya:0.7>,
#    green_hair, freckles, BREAK, (smile:1.1), (sitting:1.1), close-up,
#    classroom, chibi, <lora:chibi-laugh:0.6>"
```

---

## LoRA Weight 가이드

### 장면 복잡도 판단 기준

```python
SCENE_COMPLEXITY = {
    "simple": {
        "poses": ["standing", "sitting", "portrait"],
        "actions": [],
        "camera": ["close-up", "upper body", "full body"],
        "emphasis": 1.0,
    },
    "moderate": {
        "poses": ["kneeling", "leaning", "arms crossed"],
        "actions": ["reading", "writing", "holding"],
        "camera": ["from side", "from behind"],
        "emphasis": 1.1,
    },
    "complex": {
        "poses": ["lying down", "crouching", "jumping"],
        "actions": ["running", "dancing", "cooking", "fighting"],
        "camera": ["from above", "from below", "dutch angle"],
        "emphasis": 1.2,
    },
}
```

### LoRA 타입별 Weight 테이블

> ChatGPT 피드백 + 캘리브레이션 결과 반영 (2026-01-25)

```python
LORA_WEIGHTS = {
    "style": {
        "simple": 0.6,
        "moderate": 0.5,
        "complex": 0.4,
    },
    "character": {
        "simple": 0.6,
        "moderate": 0.5,
        "complex": 0.4,
    },
    "concept": {
        "simple": 0.5,
        "moderate": 0.4,
        "complex": 0.3,
    },
}

def calculate_lora_weight(lora: dict, complexity: str) -> float:
    """LoRA 타입과 장면 복잡도에 따른 weight 계산"""
    lora_type = lora.get("category", "character")
    base = LORA_WEIGHTS.get(lora_type, LORA_WEIGHTS["character"]).get(complexity, 0.5)

    # DB의 optimal_weight가 있으면 우선 사용 (캘리브레이션 결과)
    if lora.get("optimal_weight"):
        return min(lora["optimal_weight"], base)  # 둘 중 낮은 값

    return base
```

### 트리거 태그 중복 제거

LoRA가 이미 정의하는 외모 태그는 프롬프트에서 제거:

```python
def filter_redundant_triggers(prompt_tags: list[str], lora_defined_tags: list[str]) -> list[str]:
    """LoRA가 정의하는 외모 태그 제거"""
    lora_set = {t.lower().replace("_", " ") for t in lora_defined_tags}

    return [
        tag for tag in prompt_tags
        if tag.lower().replace("_", " ") not in lora_set
    ]

# 예시: eureka LoRA가 "aqua hair, purple eyes" 정의
# 프롬프트에서 "aqua hair", "aqua_hair" 자동 제거
```

### Weight 조절 규칙

| LoRA Weight | 사용 상황 | 예시 |
|:-----------:|----------|------|
| 0.7~0.8 | 기본 포즈, LoRA 학습 데이터와 유사 | standing, looking at viewer |
| 0.5~0.6 | 약간 다른 포즈/표정 | sitting, different expression |
| 0.3~0.4 | 복잡한 액션/특수 구도 | cooking, running, from above |
| 0.2 | 극단적 장면, 캐릭터 힌트만 필요 | fighting, complex action |

---

## Category Definitions

### Quality (우선순위 1)
이미지 품질을 결정하는 태그. 항상 맨 앞에 배치.
```
masterpiece, best_quality, amazing_quality, highres, absurdres, 8k
ultra_detailed, extremely_detailed, intricate_details
```

### Subject (우선순위 2)
이미지에 포함된 대상의 수와 구성.
```
1girl, 1boy, 2girls, solo, duo, couple, group, multiple girls
```

### Identity (우선순위 3)
캐릭터를 특정하는 이름이나 LoRA 트리거 워드.
```
hatsune_miku, rem_(re:zero), midoriya_izuku
crimson_avenger_(elsword)
```

### Appearance (우선순위 4)
캐릭터의 외모 특징.
```
# Hair
long_hair, short_hair, twintails, ponytail, braids
blue_hair, blonde_hair, pink_hair

# Eyes
blue_eyes, red_eyes, heterochromia

# Other
pale_skin, dark_skin, elf_ears, horns, wings
```

### Clothing (우선순위 5)
의상과 액세서리.
```
school_uniform, maid_outfit, casual_clothes, armor
white_dress, black_jacket, pleated_skirt
glasses, ribbon, hat, boots
```

### Expression (우선순위 6)
표정과 감정 상태.
```
smile, happy, sad, crying, angry, surprised
shy, embarrassed, blush, confident, serious
open_mouth, closed_mouth, tongue_out
```

### Gaze (우선순위 7)
시선 방향.
```
looking_at_viewer, looking_away, looking_up, looking_down
looking_to_the_side, looking_back, eye_contact
eyes_closed, half-closed_eyes, wink
```

### Pose (우선순위 8)
정적인 자세.
```
standing, sitting, kneeling, crouching, lying_down
leaning, arms_crossed, hands_on_hips, peace_sign
```

### Action (우선순위 9)
동적인 행동.
```
walking, running, jumping, dancing
reading, writing, eating, drinking, cooking
waving, pointing, hugging
```

### Camera (우선순위 10)
촬영 구도와 앵글.
```
close-up, portrait, bust_shot, upper_body
cowboy_shot, full_body, wide_shot
from_above, from_below, from_side, from_behind
dutch_angle, low_angle, high_angle, pov
```

### Location (우선순위 11)
장소와 배경.
```
# Indoor
indoors, library, cafe, classroom, bedroom, office

# Outdoor
outdoors, street, park, forest, beach, city

# Background type
simple_background, white_background, gradient_background
detailed_background, blurry_background
```

### Time/Weather (우선순위 12)
시간대와 날씨.
```
day, night, sunset, sunrise, dusk, dawn
sunny, cloudy, rainy, snowy
```

### Lighting (우선순위 13)
조명 효과.
```
natural_light, sunlight, moonlight
backlighting, rim_light, dramatic_lighting
soft_lighting, neon_lights
```

### Mood (우선순위 14)
전체적인 분위기.
```
romantic, melancholic, peaceful, dramatic
mysterious, ethereal, cozy, lonely
```

### Style (우선순위 15)
아트 스타일.
```
anime, realistic, semi-realistic
watercolor, oil_painting, digital_art
```

### LoRA (우선순위 99)
LoRA 태그는 항상 맨 마지막에 배치.
```
<lora:character_lora:0.7>
<lora:style_lora:0.5>
```

---

## 프롬프트 조합 규칙

### 1. Base Prompt (캐릭터 기본)
캐릭터의 고정 속성. 씬마다 변하지 않는 요소.
```
1girl, hatsune_miku, blue_twintails, blue_eyes,
black_thighhighs, detached_sleeves, <lora:miku:0.8>
```

### 2. Scene Prompt (씬별)
씬에 따라 변하는 요소.
```
smile, looking_at_viewer, standing, singing_on_stage,
concert_hall, colorful_lights, energetic
```

### 3. 병합 규칙
1. Base와 Scene 토큰 합치기
2. 중복 제거 (대소문자 무시)
3. Priority 순서로 정렬
4. Quality 태그 추가 (없으면)
5. LoRA는 맨 끝으로 이동

### 4. 최종 결과 예시
```
masterpiece, best_quality,
1girl, hatsune_miku,
blue_twintails, blue_eyes,
detached_sleeves, black_thighhighs,
smile, looking_at_viewer,
standing, singing,
concert_hall, colorful_lights,
energetic,
<lora:miku:0.8>
```

---

## 충돌 규칙

> v3.0: 하드코딩 → DB `tag_rules` + `tag_aliases` + `tag_filters` 테이블로 이관 완료.
> `/admin/migrate-tag-rules`, `/admin/migrate-category-rules` 엔드포인트로 마이그레이션.

### Conflict (상호 배타적)

**태그 레벨** (`tag_rules.source_tag_id` ↔ `target_tag_id`):
```yaml
expression: [crying ↔ laughing, sad ↔ happy, angry ↔ smile]
gaze: [looking_down ↔ looking_up, looking_away ↔ looking_at_viewer]
pose: [sitting ↔ standing, lying ↔ standing, lying ↔ sitting]
```

**카테고리 레벨** (`tag_rules.source_category` ↔ `target_category`):
```yaml
hair_length ↔ hair_length    # Only one hair length
location_indoor ↔ location_outdoor  # Cannot be both
camera ↔ camera              # Only one camera angle
```

### Requires (필수 동반)
```yaml
twintails: [long_hair]
ponytail: [long_hair]
```

### Tag Aliases (`tag_aliases` 테이블)
위험/비표준 태그의 자동 치환:
```yaml
"medium shot" → "cowboy_shot"
"close up" → "close-up"
"unreal engine" → NULL  # 삭제
```

### Tag Filters (`tag_filters` 테이블)
프롬프트에서 무시/스킵할 태그:
```yaml
ignore: ["rating:general", "commentary"]  # 완전 무시
skip: ["simple_background"]               # 조건부 스킵
```

---

## 필터링 규칙

### Scene-Specific Keywords
Base prompt에서 제거해야 하는 씬별 키워드.
```typescript
const SCENE_SPECIFIC_KEYWORDS = [
  // Poses
  "sitting", "standing", "walking", "lying_down",
  // Camera
  "close-up", "full_body", "from_above",
  // Locations
  "library", "cafe", "bedroom", "outdoors",
  // Time/Weather
  "night", "sunset", "rain",
];
```

### Skip Tags
프롬프트에 포함하지 않는 태그.
```python
SKIP_TAGS = [
  # NSFW/Sensitive
  "breasts", "thighs", "cleavage",
  # Meta tags
  "highres", "absurdres",  # 별도 추가
  # Useless
  "simple_background",  # 씬에 따라 다름
]
```

---

## 구현 위치

### V3 Prompt Engine (Backend)

| 기능 | 파일 | 함수/클래스 |
|------|------|-----------|
| **12-Layer Builder** | `backend/services/prompt/v3_composition.py` | `V3PromptBuilder` |
| **V3 Service** | `backend/services/prompt/v3_service.py` | V3 서비스 인터페이스 |
| 프롬프트 정규화 | `backend/services/prompt/prompt.py` | `normalize_and_fix_tags()` |
| 프롬프트 조합 | `backend/services/prompt/prompt_composition.py` | `compose_prompt()` |
| 프롬프트 검증 | `backend/services/prompt/prompt_validation.py` | 태그 유효성 검사 |
| 카테고리 우선순위 | `backend/services/keywords/patterns.py` | `CATEGORY_PRIORITY` |
| 태그 DB 처리 | `backend/services/keywords/db.py` | `load_tags_from_db` |
| 프로세싱 | `backend/services/keywords/processing.py` | `expand_synonyms`, `filter_prompt_tokens` |
| 충돌/의존성 검증 | `backend/services/keywords/validation.py` | `validate_prompt_tags` |
| 동기화 로직 | `backend/services/keywords/sync.py` | `sync_lora_triggers_to_tags` |
| 태그 분류 | `backend/services/tag_classifier.py` | `TagClassifier` |

### V3 Runtime Caches

| 캐시 | 파일 | 역할 |
|------|------|------|
| `TagCategoryCache` | `backend/services/keywords/db_cache.py` | 태그 카테고리 매핑 |
| `TagAliasCache` | `backend/services/keywords/db_cache.py` | 태그 치환 규칙 |
| `TagRuleCache` | `backend/services/keywords/db_cache.py` | 충돌/의존성 규칙 |
| `LoRATriggerCache` | `backend/services/keywords/db_cache.py` | LoRA 트리거 → LoRA명 매핑 |
| `TagFilterCache` | `backend/services/keywords/core.py` | 무시/스킵 태그 |

### Frontend

| 기능 | 파일 | 함수/상수 |
|------|------|-----------|
| 토큰 우선순위 | `frontend/app/constants/index.ts` | `TOKEN_PRIORITY` |
| 프롬프트 병합 | `frontend/app/utils/index.ts` | `mergePromptTokens()` |
| 프롬프트 빌드 | `frontend/app/page.tsx` | `buildPositivePrompt()` |
| 태그 분류 훅 | `frontend/app/hooks/useTagClassifier.ts` | `useTagClassifier()` |

---

## Dynamic Tag Classification

태그 분류를 DB 기반 동적 시스템으로 전환 완료. 분류 흐름:

```
태그 입력 → DB 캐시 (TagCategoryCache) → classification_rules 패턴 → Danbooru API → LLM Fallback
```

> DB 스키마: `docs/specs/DB_SCHEMA.md` 참조
> API: `POST /tags/classify` (`docs/specs/API_SPEC.md` 참조)

### 24개 카테고리 (Group)

| Priority | Group | SD Category | 예시 |
|:--------:|-------|-------------|------|
| 1 | quality | meta | masterpiece, best_quality |
| 2 | subject | scene | 1girl, solo |
| 3 | identity | character | midoriya_izuku |
| 4 | hair_color | character | blue_hair |
| 4 | hair_length | character | long_hair |
| 4 | hair_style | character | twintails |
| 4 | hair_accessory | character | ribbon |
| 4 | eye_color | character | blue_eyes |
| 4 | skin_color | character | pale_skin |
| 4 | body_feature | character | elf_ears |
| 4 | appearance | character | freckles |
| 5 | clothing | character | school_uniform |
| 6 | expression | scene | smile, blush |
| 7 | gaze | scene | looking_at_viewer |
| 8 | pose | scene | standing |
| 9 | action | scene | running |
| 10 | camera | scene | close-up |
| 11 | location_indoor | scene | classroom |
| 11 | location_outdoor | scene | forest |
| 12 | background_type | scene | simple_background |
| 13 | time_weather | scene | night, rain |
| 14 | lighting | scene | backlighting |
| 15 | mood | scene | peaceful |
| 16 | style | meta | anime |
| 99 | lora | - | `<lora:...:0.7>` |

---

## 현재 이슈 (TODO)

### ~~Issue #1: Backend 정렬 없음~~ → V3 해결
- V3 `V3PromptBuilder`가 12-Layer 기반으로 자동 정렬

### ~~Issue #2: Frontend 정렬 우회~~ → V3 해결
- V3 PromptBuilder가 Backend에서 최종 순서 확정

### ~~Issue #3: Quality 태그 누락~~ → V3 해결
- V3 PromptBuilder가 Layer 0 비어있으면 자동 `masterpiece, best_quality` 삽입

---

---

## Character Mode 설정

캐릭터/Actor 생성 시 LoRA 사용 여부에 따라 모드를 설정합니다.

### 모드 자동 감지

```python
def get_character_mode(character) -> str:
    """LoRA 유무에 따라 모드 자동 결정"""
    if character.loras and len(character.loras) > 0:
        # 캐릭터 LoRA가 있으면 LoRA 모드
        has_character_lora = any(
            lora.category == "character" for lora in character.loras
        )
        return "lora" if has_character_lora else "standard"
    return "standard"
```

### Mode A: Standard (LoRA 없음)

**사용 케이스**: 일반/제네릭 캐릭터, 특정 IP 없는 오리지널 캐릭터

```json
{
  "name": "Generic Anime Girl",
  "prompt_mode": "standard",
  "tags": [
    {"tag_id": 1, "name": "1girl", "is_permanent": true},
    {"tag_id": 2, "name": "long_hair", "is_permanent": true},
    {"tag_id": 3, "name": "pink_hair", "is_permanent": true},
    {"tag_id": 4, "name": "blue_eyes", "is_permanent": true},
    {"tag_id": 10, "name": "school_uniform", "is_permanent": false},
    {"tag_id": 11, "name": "pleated_skirt", "is_permanent": false}
  ],
  "loras": []
}
```

- `is_permanent: true` = Identity 태그 (외모), `false` = Clothing 태그

**특징**:
- Appearance 태그 상세 기술 필수 (LoRA가 없으므로)
- 장면 표현 제약 없음
- 씬마다 캐릭터 외모 변동 가능 (일관성 낮음)

### Mode B: LoRA (캐릭터 LoRA 사용)

**사용 케이스**: 특정 IP 캐릭터, 일관성 중요한 시리즈물

```json
{
  "name": "Midoriya Izuku",
  "prompt_mode": "lora",
  "tags": [
    {"tag_id": 1, "name": "1boy", "is_permanent": true},
    {"tag_id": 5, "name": "green_hair", "is_permanent": true},
    {"tag_id": 6, "name": "freckles", "is_permanent": true}
  ],
  "loras": [
    {"lora_id": 5, "weight": 0.7, "name": "mha_midoriya-10", "lora_type": "character"}
  ]
}
```

**특징**:
- Appearance 태그 최소화 (LoRA가 처리)
- LoRA 학습 특성과 충돌하는 태그 사용 금지
- V3 PromptBuilder가 BREAK 자동 삽입 (Layer 6 이후)

### 스타일 LoRA만 사용하는 경우

스타일 LoRA (chibi, blindbox 등)만 사용하는 경우 **Standard 모드**로 처리합니다.

```json
{
  "name": "Chibi Girl",
  "prompt_mode": "standard",
  "tags": [
    {"tag_id": 1, "name": "1girl", "is_permanent": true},
    {"tag_id": 7, "name": "blonde_hair", "is_permanent": true},
    {"tag_id": 8, "name": "short_hair", "is_permanent": true},
    {"tag_id": 12, "name": "dress", "is_permanent": false}
  ],
  "loras": [
    {"lora_id": 3, "weight": 0.6, "name": "chibi-laugh", "lora_type": "style"}
  ]
}
```

**이유**: 스타일 LoRA는 캐릭터 외모를 정의하지 않으므로, Appearance 태그로 상세 기술 필요

### V3 데이터 구조

```
characters 테이블 → character_tags 연결 테이블 → tags 테이블
  prompt_mode          is_permanent, weight       default_layer (0-11)
```

- `prompt_mode`: `auto` | `standard` | `lora` (auto = LoRA 유무에 따라 자동 결정)
- `character_tags.is_permanent`: identity (true) vs clothing (false)
- `tags.default_layer`: 12-Layer 시스템 내 위치 결정

### 프롬프트 조합 시 모드 적용

> V3에서는 `V3PromptBuilder.compose_for_character()`가 모드 감지 + 12-Layer 배치 + BREAK 삽입을 자동 처리합니다.
> 상세: "V3: 12-Layer Prompt Builder" 섹션 참조

---

## 변경 이력

> 상세 이력은 문서 상단 변경 이력 테이블 참조
