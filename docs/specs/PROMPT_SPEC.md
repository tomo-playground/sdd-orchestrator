# Prompt Design Specification

SD 이미지 생성을 위한 프롬프트 설계 규칙.

## 토큰 순서가 중요한 이유

Stable Diffusion은 프롬프트의 **앞쪽 토큰에 더 높은 가중치**를 부여합니다:
- 앞쪽 토큰: 이미지의 핵심 요소 결정
- 뒤쪽 토큰: 부가적 디테일로 처리
- 순서가 잘못되면 원하는 결과를 얻기 어려움

### 예시
```
# Good: 캐릭터가 중심
1girl, hatsune miku, blue hair, smile, standing, library

# Bad: 배경이 중심이 됨
library, standing, smile, blue hair, hatsune miku, 1girl
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
| 4 | **Appearance** | `blue twintails`, `blue eyes` |
| 5 | **Clothing** | `black dress`, `detached sleeves` |
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
1girl, hatsune miku,
blue twintails, blue eyes, hair ribbon,
black dress, detached sleeves, thighhighs,
smile, looking at viewer,
standing, singing,
close-up,
concert stage, night,
colorful lights,
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
standing, looking at viewer,
smile,
green hair, freckles,
classroom, daytime,
soft lighting,
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
masterpiece, best quality, amazing quality, highres, absurdres, 8k
ultra detailed, extremely detailed, intricate details
```

### Subject (우선순위 2)
이미지에 포함된 대상의 수와 구성.
```
1girl, 1boy, 2girls, solo, duo, couple, group, multiple girls
```

### Identity (우선순위 3)
캐릭터를 특정하는 이름이나 LoRA 트리거 워드.
```
hatsune miku, rem (re:zero), midoriya izuku
crimson_avenger_(elsword),
```

### Appearance (우선순위 4)
캐릭터의 외모 특징.
```
# Hair
long hair, short hair, twintails, ponytail, braids
blue hair, blonde hair, pink hair

# Eyes
blue eyes, red eyes, heterochromia

# Other
pale skin, dark skin, elf ears, horns, wings
```

### Clothing (우선순위 5)
의상과 액세서리.
```
school uniform, maid outfit, casual clothes, armor
white dress, black jacket, pleated skirt
glasses, ribbon, hat, boots
```

### Expression (우선순위 6)
표정과 감정 상태.
```
smile, happy, sad, crying, angry, surprised
shy, embarrassed, blush, confident, serious
open mouth, closed mouth, tongue out
```

### Gaze (우선순위 7)
시선 방향.
```
looking at viewer, looking away, looking up, looking down
looking to the side, looking back, eye contact
eyes closed, half-closed eyes, wink
```

### Pose (우선순위 8)
정적인 자세.
```
standing, sitting, kneeling, crouching, lying down
leaning, arms crossed, hands on hips, peace sign
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
close-up, portrait, bust shot, upper body
cowboy shot, full body, wide shot
from above, from below, from side, from behind
dutch angle, low angle, high angle, pov
```

### Location (우선순위 11)
장소와 배경.
```
# Indoor
indoors, library, cafe, classroom, bedroom, office

# Outdoor
outdoors, street, park, forest, beach, city

# Background type
simple background, white background, gradient background
detailed background, blurry background
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
natural light, sunlight, moonlight
backlighting, rim light, dramatic lighting
soft lighting, neon lights
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
watercolor, oil painting, digital art
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
1girl, hatsune miku, blue twintails, blue eyes,
black thighhighs, detached sleeves, <lora:miku:0.8>
```

### 2. Scene Prompt (씬별)
씬에 따라 변하는 요소.
```
smile, looking at viewer, standing, singing on stage,
concert hall, colorful lights, energetic
```

### 3. 병합 규칙
1. Base와 Scene 토큰 합치기
2. 중복 제거 (대소문자 무시)
3. Priority 순서로 정렬
4. Quality 태그 추가 (없으면)
5. LoRA는 맨 끝으로 이동

### 4. 최종 결과 예시
```
masterpiece, best quality,
1girl, hatsune miku,
blue twintails, blue eyes,
detached sleeves, black thighhighs,
smile, looking at viewer,
standing, singing,
concert hall, colorful lights,
energetic,
<lora:miku:0.8>
```

---

## 충돌 규칙

### Conflict (상호 배타적)
같은 카테고리 내에서 동시에 사용할 수 없는 태그.
```yaml
hair_length:
  - [long hair, short hair, medium hair]

hair_style:
  - [twintails, ponytail]  # 동시에 가능
  - [straight hair, curly hair, wavy hair]

gaze:
  - [looking at viewer, looking away, looking down]
  - [eyes closed, eyes open]

pose:
  - [standing, sitting, lying down, kneeling]
```

### Requires (필수 동반)
특정 태그가 있으면 함께 필요한 태그.
```yaml
twintails: [long hair]  # twintails → long hair 필요
ponytail: [long hair]   # ponytail → long hair 필요
glasses: [wearing glasses]  # 의미 명확화
```

---

## 필터링 규칙

### Scene-Specific Keywords
Base prompt에서 제거해야 하는 씬별 키워드.
```typescript
const SCENE_SPECIFIC_KEYWORDS = [
  // Poses
  "sitting", "standing", "walking", "lying",
  // Camera
  "close-up", "full body", "from above",
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
  "simple background",  # 씬에 따라 다름
]
```

---

## 구현 위치

| 기능 | 파일 | 함수/상수 |
|------|------|-----------|
| 토큰 우선순위 | `frontend/app/constants/index.ts` | `TOKEN_PRIORITY`, `TOKEN_PRIORITY_PATTERNS` |
| 우선순위 계산 | `frontend/app/constants/index.ts` | `getTokenPriority()` |
| 프롬프트 병합 | `frontend/app/utils/index.ts` | `mergePromptTokens()` |
| 프롬프트 빌드 | `frontend/app/page.tsx` | `buildPositivePrompt()` |
| 카테고리 우선순위 | `backend/services/keywords.py` | `CATEGORY_PRIORITY` |
| 백엔드 병합 | `backend/services/prompt.py` | `merge_prompt_tokens()` |
| **태그 분류 (15.7)** | `backend/services/tag_classifier.py` | `TagClassifier`, `classify_batch()` |
| **분류 API** | `backend/routers/tags.py` | `POST /tags/classify` |
| **프론트엔드 분류** | `frontend/app/hooks/useTagClassifier.ts` | `useTagClassifier()` |

---

## Dynamic Tag Classification (15.7)

태그 분류를 **하드코딩에서 DB 기반 동적 시스템**으로 전환.

### 왜 동적 분류가 필요한가?

| 기존 방식 | 문제점 |
|----------|--------|
| `CATEGORY_PATTERNS` 하드코딩 | 새 태그마다 코드 수정 필요 |
| Frontend `getTokenCategory()` | Backend와 동기화 어려움 |
| 정적 패턴 매칭 | Gemini가 생성하는 새 태그 미분류 |

### 분류 흐름

```
태그 입력 → DB 캐시 조회 → classification_rules 패턴 → Danbooru API → LLM Fallback
              ↓                    ↓                       ↓            ↓
          group 반환          group 반환              카테고리 추론   Gemini 분류
                                                      (General 세분화)
```

### DB 스키마

```sql
-- 분류 규칙 테이블 (CATEGORY_PATTERNS 대체)
CREATE TABLE classification_rules (
    id SERIAL PRIMARY KEY,
    rule_type VARCHAR(20) NOT NULL,  -- 'suffix', 'prefix', 'contains', 'exact'
    pattern VARCHAR(100) NOT NULL,
    target_group VARCHAR(50) NOT NULL,
    priority INT DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    UNIQUE(rule_type, pattern)
);

-- tags 테이블 확장
ALTER TABLE tags ADD COLUMN classification_source VARCHAR(20) DEFAULT 'pattern';
  -- 'pattern' | 'danbooru' | 'llm' | 'manual'
ALTER TABLE tags ADD COLUMN classification_confidence FLOAT DEFAULT 1.0;
```

### API

#### POST /tags/classify
태그 배치 분류 (최대 50개).

**Request**:
```json
{
  "tags": ["smile", "starry sky", "on bed", "unknown_tag"]
}
```

**Response**:
```json
{
  "results": {
    "smile": { "group": "expression", "confidence": 1.0, "source": "db" },
    "starry sky": { "group": "time_weather", "confidence": 1.0, "source": "db" },
    "on bed": { "group": "environment", "confidence": 1.0, "source": "db" },
    "unknown_tag": { "group": null, "confidence": 0.0, "source": "unknown" }
  },
  "classified": 3,
  "unknown": 1
}
```

### Frontend 통합

```typescript
// hooks/useTagClassifier.ts
const { classifyTags, getCachedCategory } = useTagClassifier();

// 컴포넌트에서 사용
useEffect(() => {
  classifyTags(tokens).then(setCategories);
}, [tokens]);

// 분류 결과 사용 (API 우선, 로컬 패턴 fallback)
const category = apiCategories[tag] || getTokenCategory(tag);
```

### 분류 우선순위

1. **DB 캐시**: `tags` 테이블의 `group_name` (confidence >= 0.8)
2. **패턴 규칙**: `classification_rules` 테이블
3. **Danbooru API**: Wiki 조회로 카테고리 추론 (미구현)
4. **LLM Fallback**: Gemini로 분류 후 DB 저장 (미구현)

### 마이그레이션

`CATEGORY_PATTERNS` → `classification_rules` 테이블:
```bash
curl -X POST http://localhost:8000/tags/migrate-patterns
# → 677개 규칙 이관
```

### 24개 카테고리 (Group)

| Priority | Group | SD Category | 예시 |
|:--------:|-------|-------------|------|
| 1 | quality | meta | masterpiece, best quality |
| 2 | subject | scene | 1girl, solo |
| 3 | identity | character | midoriya izuku |
| 4 | hair_color | character | blue hair |
| 4 | hair_length | character | long hair |
| 4 | hair_style | character | twintails |
| 4 | hair_accessory | character | ribbon |
| 4 | eye_color | character | blue eyes |
| 4 | skin_color | character | pale skin |
| 4 | body_feature | character | elf ears |
| 4 | appearance | character | freckles |
| 5 | clothing | character | school uniform |
| 6 | expression | scene | smile, blush |
| 7 | gaze | scene | looking at viewer |
| 8 | pose | scene | standing |
| 9 | action | scene | running |
| 10 | camera | scene | close-up |
| 11 | location_indoor | scene | classroom |
| 11 | location_outdoor | scene | forest |
| 12 | background_type | scene | simple background |
| 13 | time_weather | scene | night, rain |
| 14 | lighting | scene | backlighting |
| 15 | mood | scene | peaceful |
| 16 | style | meta | anime |
| 99 | lora | - | `<lora:...:0.7>` |

---

## 현재 이슈 (TODO)

### Issue #1: Backend 정렬 없음
- **문제**: `backend/services/prompt.py`의 `merge_prompt_tokens`가 정렬하지 않음
- **영향**: `/prompt/rewrite` API 결과가 정렬되지 않음
- **해결**: Backend에 `CATEGORY_PRIORITY` 기반 정렬 추가

### Issue #2: Frontend 정렬 우회
- **문제**: `buildScenePrompt`가 `buildPositivePrompt` 결과를 덮어씀
- **영향**: Frontend 정렬 로직이 무용지물
- **해결**: Backend 결과도 Frontend에서 재정렬

### Issue #3: Quality 태그 누락
- **문제**: Base prompt에 quality 태그가 없으면 최종에도 없음
- **해결**: 정렬 후 quality 태그 자동 추가

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
  "identity_tags": ["1girl", "solo"],
  "appearance_tags": [
    "long pink hair", "blue eyes", "pale skin",
    "twintails", "hair ribbon", "small breasts"
  ],
  "clothing_tags": ["school uniform", "pleated skirt", "thighhighs"],
  "loras": [],
  "negative_embedding": "easynegative"
}
```

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
  "identity_tags": ["1boy", "solo"],
  "appearance_tags": ["green hair", "freckles"],
  "clothing_tags": [],
  "loras": [
    {"name": "mha_midoriya-10", "weight": 0.7, "category": "character"}
  ],
  "trigger_words": ["midoriya_izuku"],
  "negative_embedding": "easynegative"
}
```

**특징**:
- Appearance 태그 최소화 (LoRA가 처리)
- LoRA 학습 특성과 충돌하는 태그 사용 금지
- 장면 복잡도에 따라 LoRA weight 자동 조절

### 스타일 LoRA만 사용하는 경우

스타일 LoRA (chibi, blindbox 등)만 사용하는 경우 **Standard 모드**로 처리합니다.

```json
{
  "name": "Chibi Girl",
  "prompt_mode": "standard",
  "identity_tags": ["1girl", "solo", "chibi"],
  "appearance_tags": ["blonde hair", "green eyes", "short hair"],
  "clothing_tags": ["dress", "bow"],
  "loras": [
    {"name": "chibi-laugh", "weight": 0.6, "category": "style"}
  ],
  "negative_embedding": "easynegative"
}
```

**이유**: 스타일 LoRA는 캐릭터 외모를 정의하지 않으므로, Appearance 태그로 상세 기술 필요

### DB 스키마

```sql
-- characters 테이블
ALTER TABLE characters ADD COLUMN prompt_mode VARCHAR(10) DEFAULT 'auto';
-- 'auto' | 'standard' | 'lora'
-- auto: LoRA 유무에 따라 자동 결정

-- loras 테이블 (기존)
-- category: 'character' | 'style' | 'concept'
```

### 프롬프트 조합 시 모드 적용

```python
def compose_prompt(character, scene) -> dict:
    mode = get_character_mode(character)

    if mode == "standard":
        # 표준 순서: Quality → Subject → Appearance → Scene
        return compose_standard_prompt(character, scene)
    else:
        # LoRA 순서: Quality → Subject → Trigger → Scene Core → Appearance
        complexity = detect_scene_complexity(scene)
        adjusted_weight = calculate_lora_weight(character.loras, complexity)
        return compose_lora_prompt(character, scene, adjusted_weight)
```

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2025-01-25 | 초기 문서 작성 |
| 2025-01-25 | Mode A (Standard) / Mode B (LoRA) 규칙 분리 |
| 2025-01-25 | Character Mode 설정 스펙 추가 |
| 2025-01-25 | LoRA 타입별 Weight 테이블 추가 (ChatGPT 피드백 반영) |
| 2025-01-25 | 트리거 태그 중복 제거 로직 추가 |
| 2026-01-25 | 15.7 Dynamic Tag Classification 시스템 추가 |
| 2026-01-25 | classification_rules 테이블 + /tags/classify API |
| 2026-01-25 | Frontend useTagClassifier 훅 통합 |
