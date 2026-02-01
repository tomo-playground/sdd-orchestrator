# Prompt Pipeline Spec v1.2

> 프롬프트 구성부터 이미지 생성까지, 결과에 영향을 미치는 **전체** 파이프라인을 정의합니다.
> 12-Layer 구조 상세는 `PROMPT_SPEC.md` 참조.

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
     hiResEnabled                    (Hi-Res 설정)
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
   POST /scene/generate ─────────→ Generation Orchestrator (Section 7-9)
                                     ├─ Complexity 자동 조정 (steps/cfg)
                                     ├─ Auto IP-Adapter 활성화
                                     ├─ LoRA weight override (IP-Adapter 시)
                                     ├─ SD Payload 구성
                                     ├─ ControlNet 스택 (최대 3유닛)
                                     │   ├─ OpenPose (포즈)
                                     │   ├─ Reference-Only (캐릭터)
                                     │   └─ Canny (배경)
                                     └─ IP-Adapter (캐릭터 유사도)
                                                                  ─→ txt2img API
```

## 2. 입력 재료 (Ingredients)

### 2.1 Frontend에서 전송하는 것

| 파라미터 | 출처 | 예시 |
|----------|------|------|
| `tokens` | `scene.image_prompt` comma split | `["expressionless", "standing", "office"]` |
| `character_id` | `storyboard.default_character_id` **(필수)** | `12` |
| `base_prompt` | `character.custom_base_prompt` | `"anime_style"` |
| `context_tags` | `scene.context_tags` (Gemini) | `{expression:[], gaze:"looking_at_viewer", pose:["standing"]}` |
| `loras` | `character.loras[]` | `[{name:"flat_color", weight:1.0}]` |
| `use_break` | 상수 `true` | `true` |

**코드 위치**: `frontend/app/store/actions/promptActions.ts` `buildScenePrompt()`

### 2.2 Backend가 DB에서 로드하는 것 (character_id 기반)

| 데이터 | DB 테이블 | V3 사용처 |
|--------|-----------|-----------|
| `character.tags[]` | character_tags JOIN tags | `is_permanent` → L2, 아니면 `default_layer` |
| `character.custom_base_prompt` | characters | comma split → L2 (IDENTITY) |
| `character.loras[]` | characters.loras (JSON) → loras 테이블 | trigger words → L2, `<lora:>` → L2 |
| `character.gender` | characters | male → gender enhancement → L1 |
| `tag.default_layer` | tags | scene tag 레이어 배치 기준 |

**코드 위치**: `backend/services/prompt/v3_composition.py` `compose_for_character()`

## 3. 변환 단계 (Stages)

### Stage 1: Token Merge (Router)

**파일**: `backend/routers/prompt.py` L172-178

```
all_tokens = base_prompt_tokens + context_tags_tokens + scene_tokens
```

| 순서 | 소스 | 변환 |
|------|------|------|
| 1 | `base_prompt` | `split_prompt_tokens()` → comma split + trim |
| 2 | `context_tags` | `_collect_context_tags()` → dict → flat list |
| 3 | `tokens` | 그대로 append |

`_collect_context_tags` 변환 규칙:
- `expression`, `pose`, `action`, `environment`, `mood` → list → extend
- `gaze`, `camera` → string → append

### Stage 2: Character DB Load

**파일**: `v3_composition.py` L51-77

1. `Character` ORM 로드 (tags relationship eager load)
2. `character.tags[]` → `char_tags_data[]` 변환:
   - `is_permanent=true` → `layer=LAYER_IDENTITY(2)`
   - `is_permanent=false` → `layer=tag.default_layer`
   - `weight` 적용: `weight != 1.0`이면 `(tag:weight)` 형식
3. `character.custom_base_prompt` → comma split → `LAYER_IDENTITY(2)` 배치
   - `restricted` 키워드 필터: background, kitchen, room 등 배경 태그 제외

### Stage 3: Scene Tag Classification

**파일**: `v3_composition.py` L80, L93-96

1. `get_tag_info(scene_tags)` → DB `tags` 테이블에서 `default_layer` 조회
2. 각 scene tag → `tag_info[norm_tag]["layer"]`에 배치
3. **Fallback**: DB에 없는 태그 → `LAYER_SUBJECT(1)`

정규화: `tag.lower().replace(" ", "_").strip()`

### Stage 4: LoRA Injection

**파일**: `v3_composition.py` L98-143

```
Character LoRAs (character.loras[])
  → trigger words → LAYER_IDENTITY(2)
  → <lora:name:weight> → LAYER_IDENTITY(2)

Scene-triggered LoRAs (LoRATriggerCache)
  → _get_lora_info()로 lora_type 조회
  → character → LAYER_IDENTITY(2)
  → style → LAYER_ATMOSPHERE(11)

Style LoRAs (API loras param)
  → trigger words → LAYER_ATMOSPHERE(11)
  → <lora:name:weight> → LAYER_ATMOSPHERE(11)
```

가중치 결정: `lora.optimal_weight` → `lora.default_weight` → 기본값 `0.7`

### Stage 5: Gender Enhancement

**파일**: `v3_composition.py` `_apply_gender_enhancement()`

조건: `character.gender == "male"` AND scene_tags에 female indicator 없음

```
LAYER_SUBJECT(1) += [(1boy:1.3), (male_focus:1.2), (bishounen:1.1)]
```

### Stage 6: Conflict Resolution

**파일**: `v3_composition.py` L148-156

- **위치 충돌** (`_resolve_location_conflicts`): L10에서 indoor/outdoor 혼재 시 처리
- **카메라 충돌** (`_resolve_camera_conflicts`): L9에서 다중 프레이밍 태그 시 첫 번째만 유지

### Stage 7: Quality Guarantee

**파일**: `v3_composition.py` L158-164

L0(QUALITY)에 `masterpiece`/`best_quality`가 없으면 강제 삽입.
가중치 괄호를 벗겨서 비교: `(masterpiece:1.2)` → `masterpiece`

### Stage 8: Flatten + Dedup

**파일**: `v3_composition.py` `_flatten_layers()`, `_dedup_key()`

1. **글로벌 중복 제거**: `global_seen` set (레이어 간 공유)
2. **dedup 키 정규화**: `(1boy:1.3)` → `1boy` (가중치 무시 비교)
3. **가중치 부스트**: L7(Expression), L8(Action) → 자동 `(tag:1.1)`
4. **BREAK 삽입**: L6(Accessory) 뒤, LoRA 있을 때만
5. **최종 join**: `", ".join(final_tokens)`

## 4. 12-Layer 배치 결과 (예시)

캐릭터: Flat Color Boy (ID=12), 씬: 사무실에서 무표정으로 머리 정리

```
L0  QUALITY      masterpiece, best_quality
L1  SUBJECT      (1boy:1.3), (male_focus:1.2), (bishounen:1.1)
L2  IDENTITY     anime_style, blue_shirt, solo, flat color, <lora:flat_color:1.0>
L3  BODY         (비어있음)
L4  MAIN_CLOTH   (비어있음 - blue_shirt가 permanent라 L2에 배치됨)
L5  DETAIL_CLOTH (비어있음)
L6  ACCESSORY    (비어있음) → BREAK 삽입 지점
L7  EXPRESSION   (expressionless:1.1), (looking_at_viewer:1.1)
L8  ACTION       (standing:1.1), (adjusting_hair:1.1)
L9  CAMERA       upper_body
L10 ENVIRONMENT  office, indoors
L11 ATMOSPHERE   day, melancholic
```

## 5. 알려진 문제 (Known Issues)

### ~~Issue 1: 이중 주입~~ (v1.2에서 해결)

Frontend에서 `base_prompt`/`loras` 전송을 제거. Backend DB가 character data의 SSOT.

### ~~Issue 2: `is_permanent` 의미 혼용~~ (v1.2에서 해결)

`is_permanent`은 포함 보장만 담당, 레이어는 항상 `tag.default_layer` 사용하도록 변경.

### ~~Issue 3: Style LoRA 배치 미구현~~ (v1.2 + v1.3에서 해결)

`lora_type == "style"`인 LoRA는 `LAYER_ATMOSPHERE(11)`에 배치. trigger words도 동일 레이어.
v1.2: Character LoRAs(`character.loras[]`)만 적용. v1.3: Scene-triggered LoRAs도 `_get_lora_info()`로 `lora_type` 조회하여 올바른 레이어에 배치.

### ~~Issue 4: 무효 태그 미검증~~ (v1.2에서 해결)

`v3_composition.py`에 `_resolve_aliases()` 추가. `TagAliasCache`를 통해 `compose_for_character()`와 `compose()` 모두에서 scene tag 분배 전 별칭 해소 수행.

## 6. Negative Prompt 파이프라인

Negative prompt는 V3 엔진을 거치지 않음. Frontend에서 로컬 처리:

**파일**: `frontend/app/store/actions/promptActions.ts` `buildNegativePrompt()`

```
result = character.custom_negative_prompt + scene.negative_prompt
       → deduplicatePromptTokens()
```

| 소스 | 예시 |
|------|------|
| `character.custom_negative_prompt` | `"easynegative"` |
| `scene.negative_prompt` | `"lowres, bad_anatomy, ..."` |

## 7. SD 파라미터 파이프라인

**파일**: `frontend/app/store/actions/imageActions.ts` `generateSceneImageFor()`

### 7.1 기본 SD 파라미터

| 파라미터 | 소스 | Frontend 기본값 | Schema 기본값 |
|----------|------|----------------|---------------|
| `steps` | `scene.steps` | 27 | 24 |
| `cfg_scale` | `scene.cfg_scale` | 7 | 7.0 |
| `sampler_name` | `scene.sampler_name` | `"DPM++ 2M Karras"` | `"DPM++ 2M Karras"` |
| `seed` | `scene.seed` | -1 | -1 |
| `clip_skip` | `scene.clip_skip` | 2 | 2 |
| `width` | 하드코딩 | 512 | 512 |
| `height` | 하드코딩 | 768 | 768 |

### 7.2 Complexity-Based 자동 조정

**파일**: `services/generation.py` L200-215

Backend가 프롬프트 복잡도에 따라 steps/cfg_scale을 자동 상향:

| 복잡도 | steps | cfg_scale |
|--------|-------|-----------|
| `complex` | `max(steps, 28)` | `max(cfg, 8.0)` |
| `moderate` | `max(steps, 25)` | `max(cfg, 7.5)` |
| `simple` | 변경 없음 | 변경 없음 |

### 7.3 Hi-Res Upscaling

**조건**: `planSlice.hiResEnabled === true` (기본값 `false`)

| 파라미터 | Frontend 값 | Schema 기본값 |
|----------|------------|---------------|
| `enable_hr` | `true` | `false` |
| `hr_scale` | `1.5` (하드코딩) | `1.5` |
| `hr_upscaler` | `"R-ESRGAN 4x+ Anime6B"` (하드코딩) | `"Latent"` |
| `hr_second_pass_steps` | `10` (하드코딩) | `10` |
| `denoising_strength` | `0.35` (하드코딩) | `0.25` |

## 8. ControlNet 파이프라인

**파일**: `services/generation.py` L261-358, `services/controlnet.py`

ControlNet은 최대 **3개 유닛**이 스택 가능. `alwayson_scripts.controlnet.args[]`에 추가.

### 8.1 Unit 1: OpenPose

**조건**: `use_controlnet === true` (기본값 `true`)

| 파라미터 | 소스 | 기본값 |
|----------|------|--------|
| `use_controlnet` | `planSlice.useControlnet` | `true` |
| `controlnet_weight` | `planSlice.controlnetWeight` | `0.8` |
| `controlnet_pose` | 자동 감지 또는 수동 지정 | `null` (auto) |

**포즈 자동 감지**: `detect_pose_from_prompt(prompt)` — 프롬프트 태그에서 포즈를 추출.

**포즈 이미지 로드**: `shared/poses/{pose_name}.png` (S3/Local Storage)

등록된 포즈 (18종): `standing`, `waving`, `arms_up`, `arms_crossed`, `hands_on_hips`,
`looking_at_viewer`, `from_behind`, `sitting`, `chin_rest`, `leaning`,
`walking`, `running`, `jumping`, `lying`, `kneeling`, `crouching`,
`pointing_forward`, `covering_face`

**SD WebUI 설정**:
```
model: "control_v11p_sd15_openpose [cab727d4]"
module: "openpose"
weight: controlnet_weight (FE default: 0.8)
control_mode: "Balanced"
pixel_perfect: true
guidance: 0.0 ~ 1.0
```

### 8.2 Unit 2: Reference-Only

**조건**: `character_id` 존재 AND `use_reference_only === true` (기본값 `true`)

| 파라미터 | 소스 | 기본값 |
|----------|------|--------|
| `use_reference_only` | Schema 기본값 (FE 미전송) | `true` |
| `reference_only_weight` | Schema 기본값 (FE 미전송) | `0.5` |

**참조 이미지**: `character.preview_image_url` (캐릭터 미리보기 이미지)

**SD WebUI 설정**:
```
model: "None" (reference_only는 모델 불필요)
module: "reference_only"
weight: 0.5
control_mode: "Balanced"
guidance: 0.0 ~ 0.75 (후반 25%는 프롬프트 우선)
```

### 8.3 Unit 3: Environment Pinning (Canny)

**조건**: `environment_reference_id` 존재 (기본값 `null`, FE 미전송)

| 파라미터 | 소스 | 기본값 |
|----------|------|--------|
| `environment_reference_id` | `scene.environment_reference_id` | `null` |
| `environment_reference_weight` | Schema 기본값 | `0.3` |

**SD WebUI 설정**:
```
model: "control_v11p_sd15_canny [d14c016b]"
module: "canny"
weight: 0.3
control_mode: "My prompt is more important"
guidance: 0.0 ~ 1.0
```

## 9. IP-Adapter 파이프라인

**파일**: `services/generation.py` L160-171, `services/controlnet.py` L453-499

### 9.1 활성화 경로

IP-Adapter는 **두 가지 경로**로 활성화:

**경로 A (Frontend 수동)**:
```
planSlice.useIpAdapter = true
planSlice.ipAdapterReference = "Flat Color Boy"
planSlice.ipAdapterWeight = 0.75
```

**경로 B (Backend 자동)**: `character_id` 존재 + 캐릭터에 preview image 있으면 자동 활성화
```python
# generation.py L160-171
if character_id and not request.use_ip_adapter:
    character_obj = db.query(Character)...
    if character_obj.preview_image_url:
        request.use_ip_adapter = True
        request.ip_adapter_reference = character_obj.name
        request.ip_adapter_weight = character_obj.ip_adapter_weight or 0.75
```

### 9.2 LoRA 가중치 오버라이드

**파일**: `services/generation.py` L217-234

IP-Adapter 활성 시, 프롬프트 내 **모든 LoRA 가중치가 `0.6`으로 강제 조정**:
```
<lora:flat_color:1.0> → <lora:flat_color:0.6>
```

### 9.3 SD WebUI 설정

| 파라미터 | 값 |
|----------|----|
| model | `"ip-adapter-plus-face_sd15 [7f7a633a]"` (clip_face) |
| module | `"ip-adapter_clip_sd15"` |
| weight | FE 전송값 또는 DB `character.ip_adapter_weight` |
| resize_mode | `"Crop and Resize"` |
| processor_res | `512` |
| control_mode | `"Balanced"` |

**모델 레지스트리** (`services/controlnet.py`):

| Key | Model |
|-----|-------|
| `faceid` | `ip-adapter-faceid-plusv2_sd15 [6e14fc1a]` |
| `clip` | `ip-adapter-plus_sd15 [836b5c2e]` |
| `clip_face` | `ip-adapter-plus-face_sd15 [7f7a633a]` (기본값) |

## 10. 알려진 문제 추가 (Image Generation)

### Issue 5: IP-Adapter 모델 미적용

**현상**: `character.ip_adapter_model` (DB: `"clip"`, `"clip_face"`, `"faceid"`)이 `build_ip_adapter_args()`에 전달되지 않음.

### ~~Issue 5: IP-Adapter 모델 미적용~~ (v1.2에서 해결)

`generation.py`에서 `character_obj.ip_adapter_model`을 `build_ip_adapter_args(model=...)` 에 전달.

### ~~Issue 6: IP-Adapter 자동 활성화로 LoRA 가중치 강제 변경~~ (v1.2에서 해결)

`generation.py` LoRA 가중치 로직 변경: 0.6 강제 → `min(calibrated_weight, 0.6)` 캡. V3 캘리브레이션 결과가 0.6 이하면 그대로 유지, 초과 시에만 0.6으로 제한.

### ~~Issue 7: Hi-Res 기본값 불일치~~ (v1.2에서 해결)

Backend schema 기본값을 Frontend에 맞춤: `hr_upscaler="R-ESRGAN 4x+ Anime6B"`, `denoising_strength=0.35`.

## 11. 캐시 의존성

### Compose 파이프라인 직접 사용

| 캐시 | 사용 위치 | 용도 |
|------|-----------|------|
| `LoRATriggerCache` | `v3_composition.py` Stage 4 | scene tag → LoRA 자동 감지 |
| `TagAliasCache` | `v3_composition.py` `_resolve_aliases()` | scene tag 별칭 해소 (v1.2 추가) |

### Compose 파이프라인 미사용 (다른 서브시스템에서 사용)

| 캐시 | 실제 사용처 | 비고 |
|------|-------------|------|
| `TagCategoryCache` | `keywords/` 패키지, 태그 분류 | compose는 `Tag.default_layer` DB 직접 조회 |
| `TagRuleCache` | `/prompt/validate-tags` | compose 충돌 해결은 hardcoded frozenset 사용 |

갱신: `POST /admin/refresh-caches` (전체 캐시 리로드)

## 12. 코드 위치 맵

### Prompt Compose

| 단계 | 파일 | 함수 |
|------|------|------|
| Frontend compose 호출 | `store/actions/promptActions.ts` | `buildScenePrompt()` |
| Frontend negative | `store/actions/promptActions.ts` | `buildNegativePrompt()` |
| Frontend preview | `components/prompt/ComposedPromptPreview.tsx` | debounced compose |
| Router | `routers/prompt.py` | `compose_prompt()` |
| Token merge | `routers/prompt.py` | L172-178 |
| context_tags flatten | `routers/prompt.py` | `_collect_context_tags()` |
| V3 Service | `services/prompt/v3_service.py` | `generate_prompt_for_scene()` |
| V3 Builder (character) | `services/prompt/v3_composition.py` | `compose_for_character()` |
| V3 Builder (generic) | `services/prompt/v3_composition.py` | `compose()` |
| Tag info lookup | `services/prompt/v3_composition.py` | `get_tag_info()` |
| Gender enhancement | `services/prompt/v3_composition.py` | `_apply_gender_enhancement()` |
| Location conflicts | `services/prompt/v3_composition.py` | `_resolve_location_conflicts()` |
| Camera conflicts | `services/prompt/v3_composition.py` | `_resolve_camera_conflicts()` |
| Flatten + dedup | `services/prompt/v3_composition.py` | `_flatten_layers()` |

### Image Generation

| 단계 | 파일 | 함수 |
|------|------|------|
| Frontend payload 구성 | `store/actions/imageActions.ts` | `generateSceneImageFor()` |
| Backend generate route | `routers/scene.py` | `POST /scene/generate` |
| Generation orchestrator | `services/generation.py` | `generate_scene_image()` |
| Complexity adjustment | `services/generation.py` | L200-215 |
| LoRA weight override | `services/generation.py` | L217-234 |
| SD payload build | `services/generation.py` | L237-259 |
| ControlNet build | `services/generation.py` | L261-358 |
| IP-Adapter build | `services/controlnet.py` | `build_ip_adapter_args()` |
| OpenPose build | `services/controlnet.py` | `build_controlnet_args()` |
| Pose detection | `services/controlnet.py` | `detect_pose_from_prompt()` |
| Pose image load | `services/controlnet.py` | `load_pose_reference()` |
| Reference image load | `services/controlnet.py` | `load_reference_image()` |

### Config 상수

| 상수 | 파일 | 값 |
|------|------|----|
| `SD_BASE_URL` | `config.py` | `env or "http://127.0.0.1:7860"` |
| `SD_TIMEOUT_SECONDS` | `config.py` | `env or 600` |
| `DEFAULT_CHARACTER_PRESET` | `config.py` | `{"weight": 0.75, "model": "clip_face"}` (DB 미설정 시 폴백) |
| `CONTROLNET_MODELS` | `services/controlnet.py` | openpose, depth, canny, reference |
| `IP_ADAPTER_MODELS` | `services/controlnet.py` | faceid, clip, clip_face |

## 13. 관련 테스트

### Prompt Compose

| 테스트 파일 | 커버리지 |
|-------------|----------|
| `tests/test_prompt_compose_error.py` | compose API 에러 처리 |
| `tests/test_prompt_quality.py` | 프롬프트 품질 검증 |
| `tests/test_prompt_fixes.py` | 프롬프트 버그 수정 검증 |
| `tests/test_style_lora_integration.py` | Style LoRA 통합 |
| `tests/api/test_prompt.py` | `/prompt/*` API 엔드포인트 |
| `scripts/test_compose_api.py` | compose API 수동 테스트 |
| `scripts/test_compose_comprehensive.py` | compose 종합 시나리오 |
| `scripts/test_v3_prompt.py` | V3 프롬프트 단위 테스트 |
| `scripts/test_v3_prompts.py` | V3 다중 프롬프트 시나리오 |

### Image Generation

| 테스트 파일 | 커버리지 |
|-------------|----------|
| `tests/api/test_controlnet.py` | ControlNet API |
| `tests/test_scene_generation_with_style_profile.py` | StyleProfile 적용 생성 |
| `scripts/test_v3_db_generation.py` | V3 DB 기반 생성 E2E |

### Tag System

| 테스트 파일 | 커버리지 |
|-------------|----------|
| `tests/test_tag_normalization.py` | 태그 정규화 |
| `tests/test_keyword_categories.py` | 키워드 카테고리 분류 |
| `tests/test_filter_prompt_tokens_effectiveness.py` | 태그 필터링/유효성 |
| `tests/api/test_keywords.py` | `/keywords/*` API |

### V3 Composition 테스트 (v1.3 추가)

| 테스트 파일 | 커버리지 |
|-------------|----------|
| `tests/test_v3_composition.py` | `_flatten_layers` dedup/BREAK, `_dedup_key` 정규화, Gender enhancement |
| `tests/test_generation_pipeline.py` | IP-Adapter 자동 활성화, LoRA 0.6 캡, Complexity 조정, Hi-Res payload |

## Changelog

| 버전 | 날짜 | 내용 |
|------|------|------|
| v1.3 | 2026-02-01 | **Scene-triggered LoRA L11 분리 버그 수정**: `LoRATriggerCache`로 발견된 LoRA의 `lora_type`을 DB에서 조회하여 style→L11, character→L2로 올바르게 배치. `_get_lora_info()` 메서드 추가, `_lora_weight_cache` → `_lora_info_cache`로 통합 |
| v1.2 | 2026-02-01 | **character_id 필수화**: schema required, FE 가드, dead else 분기 제거. **이중 주입 해결**: FE에서 base_prompt/loras 전송 제거 (DB SSOT). **Style LoRA L11 분리**: lora_type=style → LAYER_ATMOSPHERE. **IP-Adapter model 전달**: character.ip_adapter_model 반영. **Hi-Res 기본값 통일**. **별칭 해소**: `TagAliasCache`를 V3 compose에 통합 (`_resolve_aliases()`). **LoRA 가중치 캡**: IP-Adapter 활성 시 0.6 강제 → `min(calibrated, 0.6)` 캡. Dead code: `_resolve_lora_placeholders`, `CHARACTER_PRESETS`, `get_character_preset`, `/ip-adapter/presets` 엔드포인트 제거. **Known Issues 7건 모두 해결** |
| v1.1 | 2026-02-01 | ControlNet(3유닛), IP-Adapter, Hi-Res, Complexity 자동조정, LoRA weight override 추가. Known Issues 5-7 추가. 코드 위치 맵/테스트 맵 확장 |
| v1.0 | 2026-02-01 | 초기 작성. Prompt compose 파이프라인 전체 흐름 문서화, Known Issues 4건 기록 |
