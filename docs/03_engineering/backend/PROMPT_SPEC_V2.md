# Prompt System Specification (v4.4)

**최종 업데이트**: 2026-02-19

SD 이미지 생성을 위한 프롬프트 설계 규칙 + 파이프라인 전체 흐름. 기존 `PROMPT_SPEC_V2.md` + `PROMPT_PIPELINE.md`를 통합한 단일 문서.

## 변경 이력

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v4.4 | 2026-02-10 | Background Scene Trigger Word Strip: Narrator(no_humans) 씬에서 스타일 LoRA 트리거 워드 제거 |
| v4.3 | 2026-02-06 | image_prompt_ko Identity Exclusion: 캐릭터 외모 묘사 제외, 행동/감정/상황만 기술 |
| v4.2 | 2026-02-06 | Style LoRA Unification: StyleProfile이 A/B/Narrator 모든 씬에 동일 style 적용, 중복 LoRA 제거 |
| v4.1 | 2026-02-02 | POC 30-scene 검증 기반 최적화: BREAK 제거, IP-Adapter 0.35/clip_face, steps 27, CFG 오버라이드 제거 |
| v4.0 | 2026-02-01 | PROMPT_SPEC_V2 + PROMPT_PIPELINE 통합, Known Issue #8 추가 |
| v3.0 | 2026-01-30 | V3 12-Layer PromptBuilder, DB-driven 충돌 규칙 |
| v1.3 | 2026-02-01 | Scene-triggered LoRA L11 분리, LoRATriggerCache 통합 |

---

## 1. 파이프라인 개요

```
[Frontend Studio]                    [Backend]                         [SD WebUI]

 Storyboard Load ──┐
   GET /storyboards/{id}             → scenes[], character_id
   GET /characters/{id}              → tags, loras, gender, base_prompt
                   │
 Zustand Store ────┤
   planSlice:      │
     selectedCharacterId             (DB character_id)
     basePromptA                     (character.custom_base_prompt)
     characterLoras                  (character.loras[])
     useControlnet / weight          (ControlNet 설정)
     useIpAdapter / weight / ref     (IP-Adapter 설정)
   scenesSlice:    │
     scene.image_prompt              (Gemini 생성 프롬프트)
     scene.context_tags              (Gemini 생성 컨텍스트)
     scene.sd_params                 (steps, cfg, sampler, seed, clip_skip)
                   │
 ① Compose ────────┘
   POST /prompt/compose ─────────→ V3 Engine (Section 3)
                                     ├─ Token Merge
                                     ├─ Character DB Load
                                     ├─ 12-Layer Distribution
                                     ├─ LoRA Injection
                                     ├─ Gender Enhancement
                                     ├─ Conflict Resolution
                                     ├─ Quality Guarantee
                                     └─ Flatten + Dedup
                                  ←── composed prompt
                   │
 ② Generate ───────┘
   POST /scene/generate ─────────→ Generation Orchestrator (Section 5)
                                     ├─ Complexity 자동 조정
                                     ├─ Auto IP-Adapter 활성화
                                     ├─ LoRA weight override
                                     ├─ SD Payload 구성
                                     ├─ ControlNet 스택 (최대 3유닛)
                                     └─ IP-Adapter
                                                                  ─→ txt2img API
```

---

## 2. 핵심 규칙

### 2.1 Danbooru 정규화

모든 태그는 `normalize_prompt_token` 처리:
- **소문자화** + **공백→언더스코어** (`blue eyes` → `blue_eyes`)
- **가중치**: `(tag:1.1)` NAI/Danbooru 형식
- **LoRA 트리거 워드**: Civitai 원본 형식 유지 (예외)

### 2.2 토큰 순서

SD는 **앞쪽 토큰에 높은 가중치** 부여 → 12-Layer 시스템이 자동 정렬.

### 2.3 프롬프트 모드

| 모드 | 조건 | 특징 |
|------|------|------|
| **Standard** | LoRA 없음 또는 Style LoRA만 | Appearance 태그 상세 기술 필요, 일관성 낮음 |
| **LoRA** | Character LoRA 존재 | LoRA가 외모 처리, 장면 태그 우선 |

V3 `compose_for_character()`가 모드 자동 감지 + 12-Layer 배치 처리. 단일 컨텍스트 (BREAK 미사용).

---

## 3. 12-Layer Prompt Builder

`backend/services/prompt/v3_composition.py` → `V3PromptBuilder`

### 3.1 레이어 정의

| Layer | 이름 | 역할 | 예시 |
|:-----:|------|------|------|
| 0 | **Quality** | 품질 (자동 보장) | `masterpiece`, `best_quality` |
| 1 | **Subject** | 인원 + Gender | `1girl`, `(1boy:1.3)` |
| 2 | **Identity** | 캐릭터 LoRA/트리거/DNA | `midoriya_izuku`, `<lora:...>` |
| 3 | **Body** | 신체 특징 | `long_hair`, `blue_eyes` |
| 4 | **Main Cloth** | 주요 의상 | `school_uniform` |
| 5 | **Detail Cloth** | 의상 디테일 | `pleated_skirt`, `ribbon` |
| 6 | **Accessory** | 악세서리 | `glasses`, `hat` |
| 7 | **Expression** | 표정 (자동 1.1x) | `smile`, `blush` |
| 8 | **Action** | 행동 (자동 1.1x) | `sitting`, `running` |
| 9 | **Camera** | 카메라 앵글 | `close-up`, `from_above` |
| 10 | **Environment** | 배경/장소 | `classroom`, `night` |
| 11 | **Atmosphere** | 분위기 + Style LoRA | `soft_lighting`, `<lora:chibi:0.6>` |

### 3.2 특수 처리

- **단일 컨텍스트**: BREAK 미사용 (POC 30-scene 검증: 단일 컨텍스트 + IP-Adapter 0.35가 최적)
- **Expression/Action 부스트**: L7, L8 태그에 자동 `(tag:1.1)`
- **Quality 자동 추가**: L0 비어있으면 `masterpiece, best_quality` 삽입
- **Location 충돌**: indoor/outdoor 혼재 시 다수 그룹만 유지
- **Camera 충돌**: wide/mid/close 프레이밍 충돌 시 첫 번째만 유지
- **LoRA 트리거 자동 감지**: `LoRATriggerCache`로 씬 태그에서 LoRA 활성화

### 3.3 중복 제거

| 범위 | 처리 | 방식 |
|------|------|------|
| 글로벌 (inter-layer) | O | `global_seen` set (v1.3에서 글로벌로 변경) |
| dedup 키 | `(1boy:1.3)` → `1boy` | 가중치 무시 비교 |

### 3.4 LoRA 주입 규칙

| LoRA 유형 | 주입 위치 | Trigger 위치 | 활성화 |
|-----------|----------|-------------|--------|
| Character LoRA | L2 (Identity) | L2 | 자동 (캐릭터 연결) |
| Style LoRA | L11 (Atmosphere) | L11 | `style_loras` 파라미터 |
| Scene LoRA | L11 (Atmosphere) | L11 | `LoRATriggerCache` 자동 |

가중치 결정: `lora.optimal_weight` → `lora.default_weight` → 기본값 `0.7`

#### Style LoRA Unification (v4.2)

**목적**: A, B, Narrator 모든 씬이 동일한 스타일을 유지하도록 StyleProfile이 단일 스타일 소스 역할.

| Speaker | Character LoRAs | Style LoRAs |
|---------|-----------------|-------------|
| A | character만 사용 | StyleProfile.loras |
| B | character만 사용 | StyleProfile.loras |
| Narrator | 없음 (배경씬) | StyleProfile.loras |

**처리 규칙**:
1. **Frontend**: `resolveCharacterLorasForSpeaker()`가 character LoRA만 반환 (style 필터링)
2. **Backend**: `compose()`에서 style_loras 이름으로 중복 체크, StyleProfile 가중치 우선
3. **Dedup**: 동일 LoRA가 character_loras와 style_loras 양쪽에 있으면 style_loras 가중치 사용

#### Background Scene Filtering (v4.4)

**목적**: Narrator/배경 씬(`no_humans`)에서 캐릭터 생성을 방지하면서 스타일 일관성 유지.

**감지**: `_is_background_scene()` — 태그 목록에 `no_humans` 포함 시 활성화.

| 항목 | 처리 |
|------|------|
| Character LoRAs (L1-L8) | **전체 제거** — `_strip_character_layers()` |
| Character 트리거 워드 | **제거** (Layer 1-8 clear) |
| Character 카메라 태그 | **제거** (cowboy_shot, close-up 등) |
| Style LoRA 태그 (`<lora:...>`) | **유지** — L11 Atmosphere |
| Style LoRA 트리거 워드 | **제거** — SD 모델이 캐릭터 생성으로 편향될 수 있음 |

**근거**: 스타일 LoRA 트리거 워드(예: `flat color`)는 Danbooru에서 캐릭터 일러스트와 연관되어 있어, `no_humans` 씬에서도 사람이 생성되는 부작용 발생. LoRA 모델 자체가 스타일을 적용하므로 트리거 워드 없이도 효과 유지.

**예시** (Before → After):
```
Before: masterpiece, living_room, no_humans, flat color, <lora:flat_color:0.4>
After:  masterpiece, living_room, no_humans, <lora:flat_color:0.4>
```

### 3.5 예시 출력

캐릭터: Flat Color Boy (ID=12), 씬: 사무실에서 무표정으로 머리 정리

```
L0  QUALITY      masterpiece, best_quality
L1  SUBJECT      (1boy:1.3), (male_focus:1.2), (bishounen:1.1)
L2  IDENTITY     anime_style, blue_shirt, solo, flat color, <lora:flat_color:1.0>
L7  EXPRESSION   (expressionless:1.1), (looking_at_viewer:1.1)
L8  ACTION       (standing:1.1), (adjusting_hair:1.1)
L9  CAMERA       upper_body
L10 ENVIRONMENT  office, indoors
L11 ATMOSPHERE   day, melancholic
```

---

## 4. 변환 단계 (Compose Pipeline)

### Stage 1: Token Merge (Router)

`routers/prompt.py`: `all_tokens = base_prompt + context_tags + scene_tokens`

### Stage 2: Character DB Load

`v3_composition.py` `compose_for_character()`:
1. Character ORM 로드 (tags eager load)
2. `character.tags[]` → `char_tags_data[]`: `is_permanent=true` → L2, 아니면 `tag.default_layer`
3. `character.custom_base_prompt` → comma split → L2 (restricted 태그 필터링)

### Stage 3: Scene Tag Classification

`get_tag_info(scene_tags)` → DB `tags.default_layer` 조회. Fallback: DB에 없는 태그 → L1.

### Stage 4: LoRA Injection

Character LoRAs → L2, Style LoRAs → L11, Scene-triggered → `_get_lora_info()` 조회 후 type별 배치.

**Style LoRA Unification** (v4.2):
1. `style_lora_names` set 수집 (StyleProfile 우선)
2. character_loras 주입 시 style_lora_names와 중복 체크 → 중복 시 skip
3. Scene-triggered LoRA도 동일하게 중복 체크
4. style_loras 주입 (L11) - 항상 모든 씬에 적용

### Stage 5: Gender Enhancement

`character.gender == "male"` AND no female indicator → L1에 `(1boy:1.3), (male_focus:1.2)` 추가.

### Stage 6-8: Conflict Resolution → Quality Guarantee → Flatten + Dedup

충돌 해결 → 품질 보장 → 글로벌 dedup → BREAK 삽입 → `", ".join()`.

---

## 5. Generation Pipeline

`services/generation.py` → `generate_scene_image()`

### 5.1 SD 파라미터

| 파라미터 | 기본값 | Complexity 조정 |
|----------|--------|----------------|
| `steps` | 27 | complex: max(28), moderate: max(25) |
| `cfg_scale` | 7.0 | - (고정, POC 검증) |
| `sampler_name` | DPM++ 2M Karras | - |
| `width × height` | 512 × 768 | - |
| `clip_skip` | 2 | - |

### 5.2 Hi-Res Upscaling

| 파라미터 | 값 |
|----------|----|
| `hr_scale` | 1.5 |
| `hr_upscaler` | R-ESRGAN 4x+ Anime6B |
| `denoising_strength` | 0.35 |

### 5.3 ControlNet (최대 3유닛)

**Unit 1: OpenPose** — `use_controlnet=true`, weight=0.8, 포즈 자동 감지
**Unit 2: Reference-Only** — `use_reference_only=true`, weight=0.5, 캐릭터 미리보기
**Unit 3: Canny (Environment Pinning)** — `environment_reference_id` 존재 시, weight=0.3

### 5.4 IP-Adapter

**활성화 경로**:
- A (수동): Frontend에서 `useIpAdapter=true`
- B (자동): `character_id` 존재 + preview image 있으면 자동 활성화

**LoRA 가중치 캡**: IP-Adapter 활성 시 모든 LoRA → `min(calibrated, 0.6)`

| 파라미터 | 값 |
|----------|----|
| model | `ip-adapter-plus-face_sd15` (기본: clip_face) |
| weight | DB `character.ip_adapter_weight` or **0.35** (POC 30-scene 검증) |

---

## 6. LoRA Weight 가이드

### 장면 복잡도별

| 복잡도 | LoRA Weight | 태그 강조 | 예시 |
|--------|:-----------:|:---------:|------|
| 단순 | 0.6~0.8 | 없음 | standing, looking_at_viewer |
| 보통 | 0.5~0.6 | `(tag:1.1)` | sitting, different expression |
| 복잡 | 0.3~0.4 | `(tag:1.2)` | cooking, running, from_above |

### 단일 컨텍스트 (v4.1)

> BREAK 미사용. POC 30-scene 실험에서 단일 컨텍스트 + IP-Adapter clip_face 0.35가 최적.
> BREAK 사용 시 L7-L11 태그(포즈/환경)의 어텐션이 약화되어 레퍼런스 이미지 고정 현상 발생.

```
masterpiece, best quality, 1boy, midoriya_izuku, green hair, <lora:mha_midoriya:0.5>,
(sitting:1.1), (cooking:1.1), focused expression, kitchen, close-up, warm lighting
```

---

## 7. 충돌 & 필터 규칙

> v3.0: 전부 DB `tag_rules` + `tag_aliases` + `tag_filters` 테이블로 이관 완료.

### Conflict (상호 배타)

```yaml
expression: [crying ↔ laughing, sad ↔ happy, angry ↔ smile]
gaze:       [looking_down ↔ looking_up, looking_away ↔ looking_at_viewer]
pose:       [sitting ↔ standing, lying ↔ standing]
category:   [hair_length ↔ hair_length, location_indoor ↔ location_outdoor, camera ↔ camera]
```

### Aliases

`"medium shot" → "cowboy_shot"`, `"close up" → "close-up"`, `"unreal engine" → NULL`

### Tag Filters (Restricted)

`custom_base_prompt`에서 씬 프롬프트로 유입 차단하는 태그:

```yaml
restricted:
  # 현재 등록된 13개
  - background, kitchen, room, outdoors, indoors, scenery
  - nature, mountain, street, office, bedroom, bathroom, garden
```

**Known Issue #8**: 아래 레퍼런스 전용 태그가 restricted 미등록 → 씬 오염 발생 (Section 9 참조)

---

## 8. 24개 태그 카테고리

| Priority | Group | SD Category | 12-Layer |
|:--------:|-------|-------------|:--------:|
| 1 | quality | meta | L0 |
| 2 | subject | scene | L1 |
| 3 | identity | character | L2 |
| 4 | hair_color, hair_length, hair_style, eye_color, skin_color, body_feature, appearance | character | L3 |
| 5 | clothing, hair_accessory | character | L4-L6 |
| 6 | expression | scene | L7 |
| 7 | gaze | scene | L7 |
| 8 | pose | scene | L8 |
| 9 | action | scene | L8 |
| 10 | camera | scene | L9 |
| 11 | location_indoor, location_outdoor | scene | L10 |
| 12 | background_type | scene | L10 |
| 13 | time_weather | scene | L10 |
| 14 | lighting | scene | L11 |
| 15 | mood | scene | L11 |
| 16 | style | meta | L11 |
| 99 | lora | - | L2/L11 |

분류 흐름: `태그 입력 → TagCategoryCache → classification_rules 패턴 → Danbooru API → LLM Fallback`

---

## 9. Known Issues

### ~~Issue 1-7~~ (해결 완료)

이중 주입, is_permanent 혼용, Style LoRA 배치, 무효 태그 검증, IP-Adapter 모델, LoRA 가중치 캡, Hi-Res 기본값 — 모두 v1.2~v1.3에서 해결.

### **Issue 8: 레퍼런스 프롬프트 씬 오염 (CRITICAL)**

**현상**: `custom_base_prompt`에 레퍼런스 전용 태그 포함 시, 모든 씬이 정자세 + 흰 배경으로 생성.

**오염 경로**:
```
Character.custom_base_prompt
  "white_background, standing, full_body, front_view..."
       ↓
v3_composition.py Stage 2: TagFilterCache.is_restricted() → False
       ↓
LAYER_IDENTITY (L2)에 추가 → 모든 씬에 포함
```

**원인**: `tag_filters` restricted 목록에 아래 태그 미등록:

| 분류 | 누락 태그 |
|------|----------|
| 배경 | `white_background`, `simple_background`, `plain_background`, `solid_background` |
| 포즈/구도 | `standing`, `full_body`, `front_view`, `facing_viewer`, `straight_on` |
| 시선 | `looking_at_viewer` |
| 기타 | `portrait`, `solo` |

**출처**: `config.py` `DEFAULT_REFERENCE_BASE_PROMPT` 태그가 캐릭터 `custom_base_prompt`에 유입.

**수정 방향**: restricted 태그 확장 + `custom_base_prompt` 입력 검증.

---

## 10. Gemini 템플릿 규칙

### 10.1 image_prompt_ko Identity Exclusion (v4.3)

**원칙**: `image_prompt_ko`에 캐릭터 외모/의상을 묘사하지 않는다. Character Identity Injection이 `image_prompt`에 태그를 자동 주입하므로, 한국어 설명은 **행동·감정·상황·환경만** 기술한다.

| 필드 | 역할 | 캐릭터 외모 포함 |
|------|------|:---------------:|
| `image_prompt` | SD 프롬프트 (영문 태그) | O (Identity/Costume/LoRA 태그 필수) |
| `image_prompt_ko` | 씬 한국어 설명 (사용자 표시용) | X (행동/감정/상황만) |

**예시**:
```
✅ GOOD: "미소 지으며 밖에서 서 있다. 놀란 표정."
✅ GOOD: "밤에 부엌에서 땀 흘리며 서 있는 모습"
❌ BAD:  "플랫 컬러 스타일의 갈색 머리 소녀가 흰 셔츠를 입고 미소 지으며 서 있다."
```

**적용 범위**: 3개 Gemini 템플릿 전체
- `create_storyboard.j2` (Monologue)
- `create_storyboard_dialogue.j2` (Dialogue)
- `create_storyboard_narrated.j2` (Narrated Dialogue)

---

## 11. Negative Prompt

V3 엔진 미사용. Frontend에서 로컬 처리:

```
character.custom_negative_prompt + scene.negative_prompt → deduplicatePromptTokens()
```

---

## 12. 캐시 의존성

### Compose 파이프라인

| 캐시 | 파일 | 용도 |
|------|------|------|
| `LoRATriggerCache` | `keywords/db_cache.py` | scene tag → LoRA 자동 감지 |
| `TagAliasCache` | `keywords/db_cache.py` | scene tag 별칭 해소 |
| `TagFilterCache` | `keywords/db_cache.py` | restricted 태그 필터링 (`is_restricted()`) |

> `keywords/core.py`에도 동명 `TagFilterCache`가 있으나, V3 compose는 `db_cache.py` 버전 사용.

### 기타 (다른 서브시스템)

| 캐시 | 파일 | 사용처 |
|------|------|--------|
| `TagCategoryCache` | `keywords/db_cache.py` | `keywords/` 패키지, 태그 분류 |
| `TagRuleCache` | `keywords/db_cache.py` | `/prompt/validate-tags` |

갱신: `POST /admin/refresh-caches`

---

## 13. 코드 위치 맵

### Prompt Compose

| 단계 | 파일 | 함수 |
|------|------|------|
| FE compose 호출 | `store/actions/promptActions.ts` | `buildScenePrompt()` |
| FE negative | `store/actions/promptActions.ts` | `buildNegativePrompt()` |
| Router | `routers/prompt.py` | `compose_prompt()` |
| V3 Service | `services/prompt/v3_service.py` | `generate_prompt_for_scene()` |
| V3 Builder | `services/prompt/v3_composition.py` | `compose_for_character()` |
| Tag info | `services/prompt/v3_composition.py` | `get_tag_info()` |
| Flatten | `services/prompt/v3_composition.py` | `_flatten_layers()` |

### Image Generation

| 단계 | 파일 | 함수 |
|------|------|------|
| FE payload | `store/actions/imageActions.ts` | `generateSceneImageFor()` |
| Orchestrator | `services/generation.py` | `generate_scene_image()` |
| Prompt prep | `services/generation.py` | `_prepare_prompt()` |
| Param adjust | `services/generation.py` | `_adjust_parameters()` |
| Payload build | `services/generation.py` | `_build_payload()` |
| ControlNet | `services/generation.py` | `_apply_controlnet()` |
| SD API call | `services/generation.py` | `_call_sd_api()` |

### 관련 테스트

| 파일 | 커버리지 |
|------|----------|
| `tests/test_v3_composition.py` | flatten/dedup, gender enhancement |
| `tests/test_generation_pipeline.py` | IP-Adapter, LoRA cap, complexity |
| `tests/test_prompt_quality.py` | 프롬프트 품질 검증 |
| `tests/test_style_lora_integration.py` | Style LoRA 통합 |
| `tests/api/test_prompt.py` | `/prompt/*` API |
| `tests/api/test_controlnet.py` | ControlNet API |
