# Tag Group 세분화 명세

**Phase**: Feature Backlog P1
**목표**: 거대 그룹 3개(clothing 118, action 55, time_weather 38)를 의미 단위 소그룹으로 분리하여 프롬프트 레이어 정확도, WD14 검증 정밀도, UI 탐색성 향상.

---

## 1. 현재 → 변경 매핑

### 1-1. clothing (118개 → 7개 소그룹)

| 새 group_name | 설명 | 태그 수 | Layer | category | priority |
|---------------|------|--------|-------|----------|----------|
| **clothing_top** | 상의 | 19 | 4 (MAIN_CLOTH) | character | 5 |
| **clothing_bottom** | 하의 | 11 | 4 (MAIN_CLOTH) | character | 5 |
| **clothing_outfit** | 원피스/세트/유니폼/수영복/에이프런 | 19 | 4 (MAIN_CLOTH) | character | 5 |
| **clothing_detail** | 소매/칼라/오픈 상태/후드 | 20 | 5 (DETAIL_CLOTH) | character | 5 |
| **legwear** | 양말/스타킹/가터 | 12 | 5 (DETAIL_CLOTH) | character | 5 |
| **footwear** | 신발 | 13 | 5 (DETAIL_CLOTH) | character | 5 |
| **accessory** | 모자/안경/장갑/가방/장신구 | 24 | 6 (ACCESSORY) | character | 5 |

**태그 배분 상세**:

```
clothing_top (19):
  shirt, t-shirt, blouse, sweater, hoodie, jacket, coat, blazer,
  cardigan, vest, tank_top, crop_top, tube_top, camisole,
  black_tank_top, white_tank_top,
  green_hoodie, black_hoodie, white_hoodie

clothing_bottom (11):
  skirt, miniskirt, long_skirt, pleated_skirt, pants, jeans, shorts,
  leggings, white_shorts, black_shorts, denim_shorts

clothing_outfit (19):
  dress, sundress, wedding_dress, evening_dress,
  uniform, school_uniform, sailor_uniform, maid_outfit,
  suit, tuxedo, kimono, yukata, chinese_clothes,
  swimsuit, one-piece_swimsuit, bikini, school_swimsuit,
  apron, overalls

clothing_detail (20):
  sleeveless, short_sleeves, long_sleeves, wide_sleeves, puffy_sleeves,
  off_shoulder, off-shoulder, bare_shoulders,
  collar, tie, necktie, bowtie, bow, button, zipper, pocket, belt,
  ribbon, lace, frills,
  open_clothes, open_jacket, open_shirt,
  hood, hood_up, hood_down,
  plaid, striped

legwear (12):
  socks, thighhighs, kneehighs, pantyhose, stockings, fishnet,
  bare_legs, black_thighhighs, white_thighhighs,
  thigh_strap, garter, garter_belt

footwear (13):
  barefoot, shoes, boots, sneakers, sandals, high_heels, loafers,
  slippers, mary_janes,
  footwear, brown_footwear, black_footwear, white_footwear

accessory (24):
  glasses, sunglasses, hat, cap, beret,
  gloves, scarf, bag, backpack, purse,
  earrings, necklace, bracelet, ring, choker, jewelry
```

**변경 사항 (리뷰 반영)**:
- `apron`(271K posts), `overalls`(28K) → clothing_detail에서 **clothing_outfit으로 이동** (독립 의상 아이템)
- `striped` Danbooru DEPRECATED(0 posts) → 향후 `striped_clothes`(321K)로 교체 검토. 현재는 기존 유지.
- `plaid` → 향후 `plaid_clothes`(172K)로 교체 검토. 현재는 기존 유지.

### 1-2. action (55개 → 3개 소그룹)

| 새 group_name | 설명 | 태그 수 | Layer | category | priority |
|---------------|------|--------|-------|----------|----------|
| **action_body** | 이동/운동/전투 | 13 | 8 (ACTION) | scene | 9 |
| **action_hand** | holding 계열 + 제스처/인터랙션 | 20 | 8 (ACTION) | scene | 9 |
| **action_daily** | 일상 활동/오락/휴식/신체 관리 | 22 | 8 (ACTION) | scene | 9 |

**태그 배분 상세**:

```
action_body (13):
  walking, running, jumping, flying, swimming, diving,
  dancing, stretching, bending, turning,
  fighting, kicking, punching

action_hand (20):
  holding, holding_bag, holding_book, holding_cup, holding_phone,
  holding_umbrella, holding_weapon, holding_food, holding_flower,
  holding_hands, holding_sword, holding_gun, holding_knife,
  grabbing, reaching, pointing, waving, hugging, embracing, carrying

action_daily (22):
  reading, writing, drawing, typing, using_phone,
  eating, drinking, cooking, baking,
  singing, playing_instrument, playing_guitar, playing_piano,
  gaming, playing_game,
  sleeping, napping, resting,
  bathing, showering, dressing, undressing
```

**변경 사항 (리뷰 반영)**:
- `bathing`, `showering`, `dressing`, `undressing` → action_body에서 **action_daily로 이동** (일상 위생/착탈의 행위, Danbooru 분류 기준)

### 1-3. time_weather (38개 → 3개 소그룹)

| 새 group_name | 설명 | 태그 수 | Layer | category | priority |
|---------------|------|--------|-------|----------|----------|
| **time_of_day** | 시간대 | 15 | 10 (ENVIRONMENT) | scene | 13 |
| **weather** | 날씨 현상 | 14 | 10 (ENVIRONMENT) | scene | 13 |
| **particle** | 입자/시각 효과 | 9 | 10 (ENVIRONMENT) | scene | 13 |

**태그 배분 상세**:

```
time_of_day (15):
  day, daytime, morning, afternoon,
  night, nighttime, midnight, evening,
  sunset, sunrise, dusk, dawn, twilight,
  golden_hour, blue_hour

weather (14):
  sunny, cloudy, overcast,
  rainy, rain, snowy, snow,
  foggy, fog, misty,
  stormy, thunder, lightning, windy

particle (9):
  falling_leaves, falling_petals, cherry_blossoms,
  floating_particles, dust_particles, fireflies,
  bubbles, sparkles, confetti
```

---

## 2. group_name 총 목록 (27개 → 37개)

| # | group_name | category | priority | Layer | 변경 |
|---|-----------|----------|----------|-------|------|
| 1 | quality | quality | 1 | 0 | - |
| 2 | subject | scene | 2 | 1 | - |
| 3 | identity | character | 3 | 2 | - |
| 4 | hair_color | character | 4 | 2 | - |
| 5 | hair_length | character | 4 | 2 | - |
| 6 | hair_style | character | 4 | 2 | - |
| 7 | hair_accessory | character | 4 | 6 | - |
| 8 | eye_color | character | 4 | 2 | - |
| 9 | skin_color | character | 4 | 3 | - |
| 10 | body_feature | character | 4 | 3 | - |
| 11 | appearance | character | 4 | 3 | - |
| 12 | body_type | character | 4 | 3 | - |
| 13 | **clothing_top** | character | 5 | 4 | **NEW** |
| 14 | **clothing_bottom** | character | 5 | 4 | **NEW** |
| 15 | **clothing_outfit** | character | 5 | 4 | **NEW** |
| 16 | **clothing_detail** | character | 5 | 5 | **NEW** |
| 17 | **legwear** | character | 5 | 5 | **NEW** |
| 18 | **footwear** | character | 5 | 5 | **NEW** |
| 19 | **accessory** | character | 5 | 6 | **NEW** |
| 20 | expression | scene | 6 | 7 | - |
| 21 | gaze | scene | 7 | 7 | - |
| 22 | pose | scene | 8 | 8 | - |
| 23 | **action_body** | scene | 9 | 8 | **NEW** |
| 24 | **action_hand** | scene | 9 | 8 | **NEW** |
| 25 | **action_daily** | scene | 9 | 8 | **NEW** |
| 26 | camera | scene | 10 | 9 | - |
| 27 | location_indoor_specific | scene | 11 | 10 | - |
| 28 | location_outdoor | scene | 11 | 10 | - |
| 29 | environment | scene | 11 | 10 | - |
| 30 | location_indoor_general | scene | 12 | 10 | - |
| 31 | background_type | scene | 12 | 10 | - |
| 32 | **time_of_day** | scene | 13 | 10 | **NEW** |
| 33 | **weather** | scene | 13 | 10 | **NEW** |
| 34 | **particle** | scene | 13 | 10 | **NEW** |
| 35 | lighting | scene | 14 | 11 | - |
| 36 | mood | scene | 15 | 11 | - |
| 37 | style | scene | 16 | 11 | - |

**삭제되는 group_name**: `clothing`, `action`, `time_weather` (3개)
**추가되는 group_name**: 13개
**순증**: +10개 (27 → 37)

---

## 3. 12-Layer 시스템 영향

12-Layer 번호 자체는 변경 없음. 세분화는 같은 레이어 내에서 group_name만 분리.

| Layer | 기존 group_name | 변경 후 |
|-------|----------------|--------|
| 4 (MAIN_CLOTH) | clothing | clothing_top, clothing_bottom, clothing_outfit |
| 5 (DETAIL_CLOTH) | *(비어 있음)* | clothing_detail, legwear, footwear |
| 6 (ACCESSORY) | hair_accessory | hair_accessory, **accessory** |
| 8 (ACTION) | pose, action | pose, action_body, action_hand, action_daily |
| 10 (ENVIRONMENT) | time_weather + 기타 | time_of_day, weather, particle + 기타 |

**핵심 개선**: Layer 5 (DETAIL_CLOTH)가 기존에는 비활용 상태였으나, clothing_detail/legwear/footwear가 배치되면서 레이어 시스템 활용도 상승.

---

## 4. Clothing Override 호환성

`_apply_clothing_override()`는 Layer 4, 5, 6을 모두 클리어 후 override 태그를 Layer 4에 배치.

**변경 영향 없음**: 새 소그룹들이 Layer 4/5/6에 분산되므로 override 시 모두 정리되는 기존 동작이 정확히 맞음. 오히려 기존보다 정밀해짐 (Layer 5가 실제 사용되므로).

---

## 5. context_tags 키 호환성 (BLOCKER 해결)

### 문제

Gemini Cinematographer 템플릿이 `context_tags.action`이라는 **단일 키**로 action 태그를 반환. `action_resolver.py`가 `context_tags.get("action")`으로 조회. action을 3분할하면 키 불일치 발생.

### 해결: context_tags 키는 기존 유지 + DB group_name만 세분화

```python
# action_resolver.py
_ACTION_DB_GROUPS = frozenset({
    "expression", "gaze", "pose",
    "action_body", "action_hand", "action_daily",
})
_CONTEXT_TAG_KEYS = frozenset({"expression", "gaze", "pose", "action"})

# context_tags 조회는 _CONTEXT_TAG_KEYS로 (Gemini 응답 키)
for cat in _CONTEXT_TAG_KEYS:
    value = context_tags.get(cat)

# DB 필터는 _ACTION_DB_GROUPS로 (세분화된 group_name)
.filter(Tag.group_name.in_(_ACTION_DB_GROUPS))
```

**원칙**: Gemini 템플릿/context_tags 인터페이스는 변경하지 않는다. DB group_name과 Gemini 키 사이에 매핑 레이어를 둔다.

**영향 파일**:
- `action_resolver.py` — 키 조회와 DB 필터 분리
- `_context_tag_utils.py` — `_CATEGORY_FIELDS` 업데이트 불필요 (context_tags 키 유지)
- `types/index.ts` — `SceneContextTags.action` 타입 변경 불필요

---

## 6. WD14 Detectable Groups 업데이트

```python
# 기존
WD14_DETECTABLE_GROUPS = frozenset({
    ..., "clothing", "action", "gesture", ...
})

# 변경
WD14_DETECTABLE_GROUPS = frozenset({
    ...,
    # clothing 계열
    "clothing_top", "clothing_bottom", "clothing_outfit",
    "clothing_detail", "legwear", "footwear", "accessory",
    # action 계열
    "action_body", "action_hand", "action_daily",
    ...
})
```

> - `time_weather`는 기존에도 WD14_DETECTABLE_GROUPS에 포함되지 않았으므로 `time_of_day`, `weather`, `particle`도 미포함.
> - 기존 `"gesture"` 유령 그룹(CATEGORY_PATTERNS에 미존재) 이번에 함께 제거.

---

## 7. DB 잔류 태그 처리 전략 (BLOCKER 해결)

### 문제

`sync_category_patterns_to_tags()`는 CATEGORY_PATTERNS에 명시된 태그(118+55+38개)만 업데이트. WD14/LLM/Danbooru로 분류된 나머지 태그(clothing ~1,150개, action ~168개, time_weather ~36개)는 구 group_name 유지.

### 해결: 3단계 재분류

```
Step 1: sync_category_patterns_to_tags(update_existing=True)
        → CATEGORY_PATTERNS 명시 태그 업데이트 (211개)

Step 2: 패턴 매칭 기반 일괄 재분류 스크립트
        → CATEGORY_PATTERNS의 패턴(suffix/prefix)으로 잔류 태그를 소그룹에 매핑
        → 예: *_dress → clothing_outfit, holding_* → action_hand
        → 매칭 불가 태그는 상위 소그룹 기본값 배정:
          clothing → clothing_detail (가장 범용)
          action → action_daily (가장 범용)
          time_weather → weather (가장 범용)

Step 3: classification_rules.target_group 업데이트
        → "clothing" → 해당 규칙의 pattern에 맞는 소그룹
        → "action" → 동일
        → "time_weather" → 동일
```

### 검증 쿼리

```sql
-- 재분류 후 구 그룹명 잔류 확인 (0건이어야 함)
SELECT group_name, COUNT(*) FROM tags
WHERE group_name IN ('clothing', 'action', 'time_weather')
GROUP BY group_name;
```

---

## 8. 후방 호환성 전략

### 8.1 DB 마이그레이션

Alembic 마이그레이션 **불필요**. `group_name`은 `String(50)`, nullable, 인덱스 없음. sync 함수 + 재분류 스크립트로 충분.

`group_name`을 저장하는 테이블은 `tags` 단일 테이블. `character_tags`, `scene_tags` 등은 `tag_id` FK 참조이므로 JOIN 시 자동 반영.

### 8.2 LLM 분류기 호환

`_VALID_GROUPS`는 `GROUP_NAME_TO_LAYER.keys()`에서 자동 생성되므로 patterns.py 수정만으로 자동 반영. `_GROUP_EXAMPLES`만 새 그룹별 예시 추가 필요.

### 8.3 캐시 갱신 절차

```
1. patterns.py 배포 (CATEGORY_PATTERNS, GROUP_NAME_TO_LAYER, CATEGORY_PRIORITY)
2. sync.py GROUP_TO_DB_CATEGORY 업데이트
3. sync_category_patterns_to_tags(update_existing=True) 실행
4. 잔류 태그 재분류 스크립트 실행
5. classification_rules.target_group 업데이트
6. /admin/refresh-caches API 호출 (TagCategoryCache 리프레시)
7. 서버 재시작 (functools.cache 무효화 — _tag_to_layer_map, _tag_to_group_map)
8. 검증: 구 그룹명 잔류 0건 확인
```

### 8.4 Frontend 하드코딩 업데이트

| 파일 | 현재 | 변경 |
|------|------|------|
| `useTags.ts` SCENE_TAG_GROUPS | `"action"` | `"action_body", "action_hand", "action_daily"` |
| `SceneContextTags.tsx` GROUP_LABELS | `action: "Action"` | action 3종 label/icon (서브그룹 접이식) |
| `useTagBrowser.ts` TAG_BROWSER_GROUPS | `"clothing"` | `"clothing_top", "clothing_outfit"` 등 대표 |
| `wizardTemplates.ts` WIZARD_CATEGORIES | `clothing` 1개 | groupNames 배열화 (Outfit/Details/Accessory 3그룹) |
| `TagCard.tsx` getCardGroupColor | clothing/action case | 신규 group별 색상 |
| `TagSuggestionDropdown.tsx` getGroupColor | 동일 | 동일 |
| `TagsTab.tsx` SCENE_TAG_GROUPS | `"action"` | action 3종 + 하드코딩 "7 Categories" 동적화 |
| **`ComposedPromptPreview.tsx`** | CATEGORY_COLORS/LABELS에 clothing/action/time_weather | **13개 신규 그룹 색상/라벨 추가** |
| **`AnalyticsDashboard.tsx`** | categoryColors에 clothing | **소그룹별 색상 추가** |
| **`types/index.ts`** | SceneContextTags.action | **변경 불필요** (context_tags 키 유지) |
| **테스트 fixtures** | manage.ts MOCK_TAG_GROUPS | **신규 그룹 반영** |

### 8.5 색상 매핑 전략

같은 계열의 명도/채도 변형으로 시각적 연관성 유지:

```
clothing 계열 (pink):
  clothing_top: pink-100, clothing_bottom: pink-150,
  clothing_outfit: pink-200, clothing_detail: rose-100,
  legwear: rose-150, footwear: rose-200, accessory: fuchsia-100

action 계열 (orange):
  action_body: orange-100, action_hand: amber-100, action_daily: yellow-100

time_weather 계열 (sky):
  time_of_day: sky-100, weather: blue-100, particle: cyan-100
```

> 색상 매핑 4곳 분산 → **공통 유틸 `tagGroupColors.ts` 추출** 권장 (Code Modularization 원칙).

### 8.6 Frontend UI 그룹핑 전략

**Scene Editor (action 3분할)**: 독립 탭이 아닌 **1개 "Action" 아래 서브그룹 접이식**. 탭 수 7개 유지, 내부에서 body/hand/daily 3섹션 펼침.

**Character Wizard (clothing 7분할)**: 7개 독립 카테고리가 아닌 **논리 그룹 3개로 묶기**.
```
Outfit (clothing_top + clothing_bottom + clothing_outfit) — maxSelect: 3
Details (clothing_detail + legwear + footwear) — collapsed
Accessories (accessory) — collapsed
```
→ `WIZARD_CATEGORIES`의 `groupName: string` → `groupNames: string[]` 배열 확장 필요.

---

## 9. 구현 순서

| Step | 작업 | 영향 범위 |
|------|------|----------|
| **1** | `patterns.py` — CATEGORY_PATTERNS 분리 + CATEGORY_PRIORITY + GROUP_NAME_TO_LAYER 업데이트 | Backend SSOT |
| **2** | `sync.py` — GROUP_TO_DB_CATEGORY 딕셔너리에 13개 신규 그룹 추가 | DB sync |
| **3** | `config.py` — WD14_DETECTABLE_GROUPS 업데이트 + gesture 유령 그룹 제거 | WD14 검증 |
| **4** | `tag_classifier_llm.py` — _GROUP_EXAMPLES 신규 그룹 예시 추가 | LLM 분류 |
| **5** | `danbooru.py` — CATEGORY_PATTERNS exact match 우선 + suffix fallback | Danbooru 연동 |
| **6** | `action_resolver.py` — _CONTEXT_TAG_KEYS / _ACTION_DB_GROUPS 분리 | CharacterAction |
| **7** | 기타 Backend 하드코딩 업데이트: | |
| | - `prompt.py` SCENE_CATEGORIES (action 3종 + time_weather 3종) | 씬 복잡도 |
| | - `suggestions.py` category 문자열 비교 | 태그 제안 |
| | - `db.py` _DB_GROUP_TO_GEMINI_CATEGORY 레거시 매핑 | Gemini 포맷 |
| | - `admin.py` valid_groups + `tag_thumbnail.py` visual_groups | 썸네일 |
| **8** | Frontend 11개 파일 하드코딩 업데이트 | UI |
| **9** | DB sync + 잔류 태그 재분류 + classification_rules 업데이트 + 캐시 리프레시 + 서버 재시작 | 배포 |
| **10** | 테스트 (기존 테스트 수정 + 신규 테스트) | 검증 |

---

## 10. 네이밍 규칙

- **clothing 계열**: `clothing_` prefix (clothing_top, clothing_bottom, clothing_outfit, clothing_detail). 단, legwear/footwear/accessory는 독립 그룹명 — Layer가 다르므로.
- **action 계열**: `action_` prefix (action_body, action_hand, action_daily).
- **time_weather 계열**: prefix 없음 (time_of_day, weather, particle) — 완전히 독립적 개념.

---

## 11. 성공 기준

- [ ] `CATEGORY_PATTERNS`에서 clothing/action/time_weather 키 완전 제거
- [ ] DB tags 테이블의 **모든** 해당 태그 group_name이 새 소그룹으로 업데이트 (잔류 0건)
- [ ] `classification_rules.target_group`에 구 그룹명 잔류 0건
- [ ] 12-Layer 프롬프트 출력 레이어 배치가 정확
- [ ] WD14 match rate 수치 변동 없음 (모든 새 소그룹이 DETECTABLE에 포함)
- [ ] LLM 분류기가 새 그룹으로 정확히 분류
- [ ] context_tags `"action"` 키 호환성 유지 (Gemini 템플릿 변경 없음)
- [ ] Frontend UI에서 새 그룹별 필터/색상 정상 표시
- [ ] 기존 테스트 전체 통과
- [ ] 서버 재시작 후 functools.cache 정상 갱신 확인
