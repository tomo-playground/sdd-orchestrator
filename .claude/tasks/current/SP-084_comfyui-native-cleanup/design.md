# SP-084 상세 설계: ComfyUI 네이티브 정리 (Forge 잔재 제거)

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `services/prompt/composition.py` | 수정 | SD_CLIENT_TYPE 분기 2곳 제거 |
| `services/characters/reference.py` | 수정 | SD_CLIENT_TYPE 분기 제거, _ensure_correct_checkpoint → payload 직접 전달 |
| `services/image_generation_core.py` | 수정 | _ensure_correct_checkpoint() 삭제, override_settings → 직접 필드 |
| `services/generation.py` | 수정 | override_settings 제거, Hi-Res Fix 페이로드 제거 |
| `services/controlnet.py` | 수정 | _resolve_model_name() 제거, SD_BASE_URL 직접 호출 2함수 제거, override_settings → sd_model_checkpoint |
| `services/generation_controlnet.py` | 수정 | check_controlnet_available → 비동기 대체, _FORGE_CN_SLOTS 패딩 삭제 |
| `services/sd_client/comfyui/__init__.py` | 수정 | weight emphasis 정규식 제거, _payload_to_variables 직접 필드 전환 |
| `services/sd_client/factory.py` | 수정 | Forge 분기 제거, ComfyUI 직접 반환 |
| `services/sd_client/forge.py` | **삭제** | ForgeClient 전체 삭제 |
| `config.py` | 수정 | SD_CLIENT_TYPE, SD_BASE_URL 조건부 로직, Forge URL 상수 제거 |
| `.env.example` | 수정 | SD_CLIENT_TYPE, SD_BASE_URL 제거 |
| `services/avatar.py` | 수정 | override_settings → clip_skip 직접 필드 |
| `services/image_cache.py` | 수정 | override_settings 추출 → clip_skip 직접 읽기 |
| `services/stage/background_generator.py` | 수정 | _ensure_correct_checkpoint → payload에 sd_model_checkpoint 추가 |
| `tests/test_sd_client.py` | 수정 | Forge 테스트 제거, SD_CLIENT_TYPE 테스트 업데이트 |
| `tests/test_composition.py` | 수정 | SD_CLIENT_TYPE regression 테스트 제거 |
| `tests/test_comfy_client.py` | 수정 | override_settings → 직접 필드 테스트로 전환 |
| `tests/test_image_generation_core.py` | 수정 | _ensure_correct_checkpoint 테스트 제거 |
| `tests/test_generation_pipeline.py` | 수정 | Hi-Res Fix 페이로드 테스트 제거 |
| `tests/test_pose_detection.py` | 수정 | _resolve_model_name mock 제거 |
| `tests/test_router_controlnet.py` | 수정 | check_controlnet_available mock 4건 → 비동기 대체 |
| `tests/test_image_cache.py` | 수정 | override_settings → clip_skip 필드 |
| `tests/test_comfy_client.py` | 수정 | TestForgeClientComfyWorkflowStrip 클래스 삭제 추가 |

**난이도: 상** (변경 파일 22개, Forge 인프라 전면 제거)

---

## Phase A: Forge 분기 제거

### DoD-A1: `composition.py`의 `SD_CLIENT_TYPE != "comfy"` 분기 2곳 제거

**구현 방법:**
- `composition.py:745` — `from config import SD_CLIENT_TYPE` import 삭제
- `composition.py:798-803` — `if SD_CLIENT_TYPE != "comfy":` 블록 전체 삭제 (scene-triggered LoRA 트리거 워드 주입)
- `composition.py:828-832` — `if SD_CLIENT_TYPE != "comfy":` 블록 전체 삭제 (style LoRA 트리거 워드 주입)
- LoRA `<lora:name:weight>` 태그 주입 (806-808행, 833행)은 유지 — ComfyUI 클라이언트가 파싱

**동작 정의:**
- Before: Forge일 때 LoRA 트리거 워드를 프롬프트 레이어에 주입, ComfyUI일 때 skip
- After: 항상 skip (ComfyUI는 LoRA 노드가 직접 적용하므로 트리거 워드 프롬프트 주입 불필요)

**엣지 케이스:**
- scene-triggered LoRA의 트리거 워드가 프롬프트에 없어도 ComfyUI LoRA 노드가 정상 적용 (현행 동작 유지)

**영향 범위:**
- `select_style_trigger_words()` 호출 제거됨 — 이 함수 자체는 다른 곳에서도 사용 가능하므로 삭제하지 않음

**테스트 전략:**
- `test_composition.py:2771-2789` — SD_CLIENT_TYPE regression 테스트 삭제 (분기 자체가 사라지므로)
- 기존 LoRA 주입 테스트 통과 확인 (`<lora:name:weight>` 태그가 레이어에 포함되는지)

**Out of Scope:**
- `select_style_trigger_words()` 함수 삭제 여부 (사용처 분석 별도)

---

### DoD-A2: `reference.py`의 `SD_CLIENT_TYPE` 분기 제거

**구현 방법:**
- `reference.py:131` — `from config import SD_CLIENT_TYPE` import 삭제
- `reference.py:142-187` — `if SD_CLIENT_TYPE == "comfy":` ... `else:` 분기 → ComfyUI 경로만 유지 (142-182행 코드 유지, else 블록 183-187행 삭제, if 조건문 자체 삭제)
- `reference.py:192-203` — `if SD_CLIENT_TYPE == "comfy":` ... `else:` 분기 → ComfyUI negative 유지, else 블록 삭제

**동작 정의:**
- Before: ComfyUI일 때 단순 프롬프트, Forge일 때 12-Layer 프롬프트
- After: 항상 ComfyUI 단순 프롬프트 사용 (weight emphasis 없이, 충돌 태그 제거, 간결한 negative)

**엣지 케이스:**
- `_resolve_quality_tags_for_character()` 호출 (190행)은 ComfyUI 경로 이후에도 유지됨 (quality_tags는 다른 용도로 사용될 수 있음)
- `_build_reference_negative()` 함수는 Forge 전용이므로 호출 제거

**영향 범위:**
- `_build_reference_negative()` — 호출 1곳 제거됨. wizard_preview_image (336행)에서도 사용 중이므로 함수 자체는 유지 (Phase A2에서는 regenerate_reference_image만 수정)

**테스트 전략:**
- regenerate_reference_image 테스트: ComfyUI 프롬프트 형식 검증 (weight emphasis 미포함, simple_background 포함)
- negative prompt에 ComfyUI 간결 형식 사용 확인

**Out of Scope:**
- wizard_preview_image (320-399행)의 Forge 프롬프트 경로 — 이 함수는 SD_CLIENT_TYPE 분기 없음 (항상 PromptBuilder 사용). 별도 검토 필요

---

### DoD-A3: `image_generation_core.py`의 `_ensure_correct_checkpoint()` 제거

**구현 방법:**
- `image_generation_core.py:29-46` — `_ensure_correct_checkpoint()` 함수 전체 삭제
- 모든 호출처에서 checkpoint를 payload의 `sd_model_checkpoint` 필드로 직접 전달:
  - `image_generation_core.py:134` → payload 구성 시 `"sd_model_checkpoint": style_ctx.sd_model_name` 추가 (183행 부근)
  - `reference.py:214-216` → 삭제, SceneGenerateRequest에 sd_model_checkpoint 전달하거나 payload에 직접 추가
  - `reference.py:339-341` → 삭제, 동일 처리
  - `background_generator.py:226-228` → 삭제, payload에 sd_model_checkpoint 추가
  - `background_generator.py:370-372` → 삭제, 동일 처리

**설계 핵심:** `_ensure_correct_checkpoint`는 Forge의 글로벌 모델 전환 API(`/sdapi/v1/options`)를 호출하는 함수. ComfyUI는 워크플로우별로 체크포인트를 지정하므로 글로벌 전환이 불필요. 대신 payload에 `sd_model_checkpoint` 필드를 직접 포함시켜 ComfyUI 클라이언트의 `_resolve_checkpoint(payload)`가 추출하도록 변경.

**동작 정의:**
- Before: 생성 전 글로벌 체크포인트 전환 → ComfyUI 클라이언트의 `_current_checkpoint`에 캐시 → txt2img에서 fallback 사용
- After: payload에 `sd_model_checkpoint` 직접 포함 → ComfyUI 클라이언트의 `_resolve_checkpoint(payload)`가 직접 추출 → 워크플로우에 주입

**엣지 케이스:**
- `sd_model_checkpoint`가 payload에 없으면 ComfyUI의 `_ensure_checkpoint()` fallback이 auto-detect — 기존 동작과 동일
- style_ctx가 None이거나 sd_model_name이 빈 문자열인 경우 → 필드 미추가, fallback 동작

**영향 범위:**
- ComfyUI 클라이언트의 `_resolve_checkpoint()` 수정 필요: `override_settings`에서 읽던 것을 `payload.get("sd_model_checkpoint", "")` 또는 `override_settings` fallback으로 변경
- `ComfyUIClient.get_options()`, `set_options()` — 더 이상 외부에서 호출하지 않지만, SDClientBase 인터페이스 유지 (다른 용도 가능)

**테스트 전략:**
- `test_image_generation_core.py:465-524` — `_ensure_correct_checkpoint` 테스트 3건 삭제
- 신규: payload에 `sd_model_checkpoint` 포함 시 ComfyUI 워크플로우에 체크포인트 반영 확인

**Out of Scope:**
- `ComfyUIClient.get_options()`/`set_options()` 삭제 — SDClientBase 인터페이스 유지

---

## Phase B: Forge 페이로드 정리

### DoD-B1: `generation.py`의 `override_settings` 제거

**구현 방법:**
- `generation.py:178-181` — `override_settings`와 `override_settings_restore_afterwards` 삭제
- 대체: `"clip_skip": max(1, int(req.clip_skip))` top-level 필드 추가
- `image_generation_core.py:183-186` — 동일 패턴 적용
- `avatar.py:115-116` — 동일 패턴 적용

**ComfyUI 클라이언트 대응:**
- `comfyui/__init__.py` `_payload_to_variables()`:
  - Before: `payload.get("override_settings", {}).get("CLIP_stop_at_last_layers", 2)`
  - After: `payload.get("clip_skip", 2)`
- `comfyui/__init__.py` `_resolve_checkpoint()`:
  - Before: `payload.get("override_settings", {}).get("sd_model_checkpoint", "")`
  - After: `payload.get("sd_model_checkpoint", "")`

**image_cache.py 대응:**
- `image_cache.py:42`:
  - Before: `payload.get("override_settings", {}).get("CLIP_stop_at_last_layers", SD_DEFAULT_CLIP_SKIP)`
  - After: `payload.get("clip_skip", SD_DEFAULT_CLIP_SKIP)`

**동작 정의:**
- Before: Forge 형식 `override_settings` dict에 CLIP skip/checkpoint 중첩
- After: top-level `clip_skip`, `sd_model_checkpoint` 필드로 플랫화

**엣지 케이스:**
- `_comfy_workflow` 필드처럼 ComfyUI-only 힌트 패턴과 동일한 접근

**테스트 전략:**
- `test_comfy_client.py:291-327` — override_settings 기반 테스트 → 직접 필드 기반으로 전환
- `test_image_cache.py:34` — override_settings → clip_skip 필드 사용

**controlnet.py:832 동시 처리 (필수):**
- `controlnet.py:832` — `payload["override_settings"] = {"sd_model_checkpoint": ...}` → `payload["sd_model_checkpoint"] = style_ctx.sd_model_name`
- Phase A3 (_ensure_correct_checkpoint 제거)과 B1 (override_settings 제거)과 이 변경은 **반드시 동시에** 이루어져야 함 — 하나만 변경하면 체크포인트 누락
- `_resolve_checkpoint()` 변경과 연동: `payload.get("sd_model_checkpoint", "")`로 통일

---

### DoD-B2: `generation.py`의 Hi-Res Fix 파라미터 제거

**구현 방법:**
- `generation.py:111-113` — `style_ctx.default_enable_hr` auto-enable 로직 삭제
- `generation.py:186-196` — `if req.enable_hr:` 블록 전체 삭제 (enable_hr, hr_scale, hr_upscaler, hr_second_pass_steps, hr_additional_modules)
- `generation.py:197-199` — `_build_adetailer_args` + `alwayson_scripts` 블록 삭제 (Forge 전용 확장)

**동작 정의:**
- Before: Forge Hi-Res Fix 파라미터를 페이로드에 추가, ADetailer 확장 포함
- After: 페이로드에 Hi-Res/ADetailer 관련 필드 없음. ComfyUI는 워크플로우 노드로 업스케일링 처리

**엣지 케이스:**
- `SceneGenerateRequest.enable_hr` 등 스키마 필드는 이번 Phase에서 유지 (스키마 변경은 별도 태스크)
- `_build_adetailer_args()` 함수 자체도 삭제 (generation.py 내부 함수, 외부 호출 없음)

**영향 범위:**
- `_adjust_parameters()` (generation.py:100-113) — Hi-Res auto-enable 로직 삭제 후 나머지 complexity boost 로직은 유지
- `schemas.py`의 `enable_hr`, `hr_scale` 등 필드 — 이번 Phase에서는 유지 (향후 정리)
- `reference.py`의 `enable_hr=enable_hr, hr_scale=...` 등 SceneGenerateRequest 생성 — 필드가 스키마에 남아있으므로 당장은 동작에 영향 없음 (payload에 반영되지 않을 뿐)

**테스트 전략:**
- `test_generation_pipeline.py:282-343` — Hi-Res Fix 테스트 4건 삭제
- 기존 페이로드 빌드 테스트에서 enable_hr/hr_scale 미포함 확인

**Out of Scope:**
- `schemas.py` Hi-Res 필드 제거 (스키마 변경 = 별도 태스크)
- `config.py` Hi-Res 상수 (`SD_HI_RES_SCALE` 등) — reference.py 등에서 아직 사용 중
- `StyleProfile.default_enable_hr` DB 컬럼 — DB 스키마 변경 불가
- `_build_adetailer_args` 관련 config 상수 (`ADETAILER_*`) — 함수 삭제로 미참조되지만, config.py 정리는 Phase C에서 일괄 처리

---

### DoD-B3: `controlnet.py`의 `_resolve_model_name()` 제거

**구현 방법:**
- `controlnet.py:202-221` — `_resolved_model_cache` dict + `_resolve_model_name()` 함수 삭제
- `controlnet.py:296` — `_resolve_model_name(CONTROLNET_MODELS.get(model, model))` → `CONTROLNET_MODELS.get(model, model)` (직접 사용)
- `controlnet.py:599` — `_resolve_model_name(raw_name)` → `raw_name` (직접 사용)

**동작 정의:**
- Before: Forge는 `name [hash]` 형식을 요구 → partial name에서 full name resolve
- After: ComfyUI는 모델 파일명 그대로 사용 → resolve 불필요

**엣지 케이스:**
- `CONTROLNET_MODELS` dict의 값이 ComfyUI에서도 유효한 모델명인지 확인 필요 → 현재 값(`"NOOB-IPA-MARK1"`, `"ip-adapter-plus-face_sdxl_vit-h"`)은 파일명 기반으로 ComfyUI 호환

**테스트 전략:**
- `test_pose_detection.py:171` — `_resolve_model_name` mock 제거

**Out of Scope:**
- ControlNet 파라미터 구조 전면 리팩토링 (Forge `alwayson_scripts` → ComfyUI 워크플로우 노드)

---

### DoD-B4: `controlnet.py`의 Forge alwayson_scripts ControlNet 파라미터 구조 정리

**구현 방법:**
- `controlnet.py:179-198` — `check_controlnet_available()`, `get_controlnet_models()` 삭제 (Forge REST API 직접 호출)
- `controlnet.py:290-306` — `build_controlnet_args()`에서 Forge 전용 필드 제거:
  - 제거: `pixel_perfect`, `processor_res`, `threshold_a`, `threshold_b` (Forge 전용)
  - 유지: `enabled`, `image`, `model`, `module`, `weight`, `control_mode`, `guidance_start`, `guidance_end`
- `controlnet.py:616-630` — `build_ip_adapter_args()` 동일 정리

**generation_controlnet.py 호출처 처리 (R1 리뷰 반영):**
- `generation_controlnet.py:40` — `check_controlnet_available()` 호출 → **항상 True 간주하고 게이트 로직 삭제** (ComfyUI 워크플로우가 ControlNet 가용성을 자체 처리)
- `generation_controlnet.py:53-56` — `_FORGE_CN_SLOTS = 3` + 패딩 루프 삭제 (Forge 전용 슬롯 패딩, ComfyUI 불필요)
- `generation_controlnet.py:56` — `alwayson_scripts` 패턴은 현재 유지 (ComfyUI 클라이언트가 무시, 별도 리팩토링 필요)

**동작 정의:**
- Before: Forge ControlNet extension 형식의 args dict (17+ 필드)
- After: 핵심 필드만 유지 (ComfyUI 워크플로우가 실제 ControlNet 처리)

**엣지 케이스:**
- `check_controlnet_available()` 삭제로 ControlNet 미설치 환경에서 에러 발생 가능 → ComfyUI에서는 워크플로우에 ControlNet 노드가 없으면 자동 skip되므로 문제 없음
- `get_controlnet_models()` — `_resolve_model_name`에서만 사용되므로 함께 삭제

**영향 범위:**
- `generation_controlnet.py` — `check_controlnet_available` import 제거, `_FORGE_CN_SLOTS` 삭제
- `build_controlnet_args()` 반환 구조 변경 → ComfyUI client는 이 args를 직접 사용하지 않고 워크플로우로 처리하므로 영향 제한적
- `alwayson_scripts` 패턴 (generation_controlnet.py, image_cache.py) — ComfyUI 클라이언트가 payload에서 무시하는 필드. 전면 리팩토링은 별도 태스크

**테스트 전략:**
- `test_router_controlnet.py` — `check_controlnet_available` mock 4건 삭제/수정
- ControlNet args 빌드 테스트에서 제거된 필드 미포함 확인

**참고 (R2):**
- `test_router_controlnet.py`의 mock 대상 `routers.controlnet.check_controlnet_available`은 현재 라우터에 존재하지 않음 (라우터는 이미 `sd.check_controlnet()` 사용). 테스트가 stale 상태이므로 삭제가 적절

**Out of Scope:**
- `build_combined_controlnet_args()` 구조 변경 — 현재는 호출 구조 유지
- `alwayson_scripts` → ComfyUI 워크플로우 노드 전면 전환 (별도 태스크)
- `image_cache.py:45-46`의 `alwayson_scripts` 기반 캐시 키 핑거프린트 — alwayson_scripts 전면 전환 후 별도 처리

---

## Phase C: 변환 레이어 간소화

### DoD-C1: `comfyui/__init__.py`의 weight emphasis 정규식 제거

**구현 방법:**
- `comfyui/__init__.py:285-286` — positive prompt weight emphasis strip 제거:
  ```python
  # 삭제: clean_prompt = re.sub(r"\(([^:()]+):[0-9.]+\)", r"\1", clean_prompt)
  ```
- `comfyui/__init__.py:298-299` — negative prompt 동일 제거

**동작 정의:**
- Before: `(tag:1.3)` → `tag` (weight 제거)
- After: `(tag:1.3)` 그대로 ComfyUI에 전달 — ComfyUI가 네이티브로 weight emphasis 처리

**엣지 케이스:**
- noobaiXL v-pred에서 heavy weight가 문제였던 이력이 있음 (코드 주석). 제거 후 regression 가능성 → 테스트 시 확인 필요
- 현재 reference.py의 ComfyUI 경로 (142-175행)에서 이미 weight emphasis를 strip하고 있음 → 이 코드는 프롬프트 빌드 단계에서 strip이므로 별개 (ComfyUI 클라이언트의 strip과 이중 strip 관계)

**사전 확인 필수 (R1/R2 리뷰 반영):**
- **확인 완료**: `composition.py`에서 `(tag:weight)` 형식을 실제 생성함 (647행, 720행, 1323행 — 3곳)
- **구현 전 ComfyUI 실 테스트 선행 필수**: weight emphasis `(tag:1.3)` 포함 프롬프트를 noobaiXL v-pred 모델에서 생성하여 grey output 발생 여부 확인
- DynamicThresholdingFull 노드가 워크플로우에 있으면 CFG Rescale로 보정됨
- 테스트 실패 시 → regex 유지 (C1 실행 보류, Out of Scope로 전환)

**테스트 전략:**
- ComfyUI _payload_to_variables 테스트: weight emphasis 포함 프롬프트가 그대로 전달되는지 확인
- Regression: weight emphasis `(tag:1.3)` 포함 프롬프트 케이스 추가

**Out of Scope:**
- reference.py:148의 ComfyUI 경로 내 weight strip — reference 생성 시 의도적 strip이므로 유지

---

### DoD-C2: `config.py`의 미사용 Forge 상수 제거

**구현 방법:**
- Forge 전용 URL 상수 제거 (ForgeClient 삭제 후 미사용):
  - `SD_TXT2IMG_URL` (174행)
  - `SD_MODELS_URL` (175행)
  - `SD_OPTIONS_URL` (176행)
  - `SD_LORAS_URL` (177행)
  - `SD_API_TIMEOUT` (252행)
  - `SD_PROGRESS_POLL_TIMEOUT` (253행)
  - `SD_MODEL_SWITCH_TIMEOUT` (254행)
- `SD_CFG_RESCALE` (189행) 사용처 확인:
  - `apply_sampler_to_payload()` (247행)에서 사용 → ComfyUI에서도 v-pred CFG Rescale이 필요할 수 있으므로 **유지 검토**
  - ComfyUI 워크플로우에 DynamicThresholdingFull 노드가 있으면 이 값이 적용됨 → **유지**
- Forge sampler/scheduler 분리 함수 (`split_sampler_scheduler`, `apply_sampler_to_payload`) — ComfyUI 클라이언트의 `_map_sampler_to_comfy`에서 사용하므로 **유지**

**삭제 확정 상수:**
- `SD_TXT2IMG_URL`, `SD_MODELS_URL`, `SD_OPTIONS_URL`, `SD_LORAS_URL`
- `SD_API_TIMEOUT`, `SD_PROGRESS_POLL_TIMEOUT`, `SD_MODEL_SWITCH_TIMEOUT`

**유지 상수:**
- `SD_BASE_URL` — scripts/ 폴더에서 아직 사용 중 (sync_webui_data.py, check_env.py 등). scripts는 이번 scope 밖
- `SD_TIMEOUT_SECONDS` — `generation.py`에서 사용 여부 확인 후 판단
- `SD_CFG_RESCALE` — v-pred CFG Rescale, ComfyUI에서도 유효
- `SD_HI_RES_*` — reference.py에서 사용 중, 스키마 정리 전까지 유지
- `_KNOWN_SCHEDULERS`, `split_sampler_scheduler`, `apply_sampler_to_payload` — ComfyUI 변환에 사용

**동작 정의:**
- Before: Forge REST API URL + timeout 상수 존재
- After: 미사용 URL/timeout 상수 제거, ComfyUI에서 사용하는 상수만 잔류

**테스트 전략:**
- 삭제된 상수 import 없음 확인 (grep)
- `test_sd_client.py:214` — `SD_BASE_URL` 미사용 assertion 업데이트

---

### DoD-C3: `SD_BASE_URL` 조건부 로깅 제거

**구현 방법:**
- `config.py:154-155` — `if SD_CLIENT_TYPE == "forge" and SD_BASE_URL == ...` 조건부 로깅 삭제

**동작 정의:**
- Before: Forge 선택 시 기본 URL 로깅
- After: 해당 로깅 삭제 (ComfyUI 로깅은 159행에서 이미 처리)

---

## Phase D: ForgeClient 제거

### DoD-D1: `services/sd_client/forge.py` 삭제

**구현 방법:**
- `forge.py` 파일 전체 삭제 (140행)

**동작 정의:**
- ForgeClient 클래스 완전 제거

**엣지 케이스:**
- `forge-docker/` 디렉토리는 보존 (rollback용, spec 명시)

---

### DoD-D2: `factory.py`에서 Forge 분기 제거

**구현 방법:**
- `factory.py:5` — `from config import SD_CLIENT_TYPE` import 삭제
- `factory.py:14-24` — if/elif/else 분기 → ComfyUI 직접 생성:
  ```python
  def get_sd_client() -> SDClientBase:
      global _client
      if _client is None:
          from services.sd_client.comfyui import ComfyUIClient
          _client = ComfyUIClient()
      return _client
  ```

**동작 정의:**
- Before: SD_CLIENT_TYPE으로 Forge/ComfyUI 분기
- After: 항상 ComfyUIClient 반환

**테스트 전략:**
- `test_sd_client.py:132-176` — SD_CLIENT_TYPE 테스트 삭제 (forge default 테스트, unknown type 테스트)
- 참고: `test_sd_client.py:142`의 `assert SD_CLIENT_TYPE == "forge"`는 기본값이 이미 `"comfy"`이므로 현재도 실패 중 — 삭제 우선
- `test_sd_client.py:180` — comfy 팩토리 테스트는 분기 없이 기본 동작으로 전환

---

### DoD-D3: `SD_CLIENT_TYPE` 환경변수 제거

**구현 방법:**
- `config.py:153` — `SD_CLIENT_TYPE = os.getenv(...)` 삭제
- `config.py:154-155` — Forge 조건부 로깅 삭제 (DoD-C3과 동일)
- `config.py:159` — `if SD_CLIENT_TYPE == "comfy":` → 무조건 실행으로 변경

**동작 정의:**
- SD_CLIENT_TYPE 환경변수 불필요, ComfyUI 고정

---

### DoD-D4: `.env.example`에서 `SD_CLIENT_TYPE`, `SD_BASE_URL` 제거

**구현 방법:**
- `.env.example:30` — `SD_CLIENT_TYPE=comfy` 행 삭제
- `.env.example:32` — `SD_BASE_URL=...` 행 삭제
- 주석 정리

**동작 정의:**
- .env.example에서 Forge 관련 설정 제거, ComfyUI 설정만 유지

---

## 공통: 테스트 & 린트

### 기존 테스트 regression 확인

**변경 테스트 파일 목록:**

| 테스트 파일 | 변경 내용 |
|------------|----------|
| `test_sd_client.py` | `TestForgeClient` 클래스 전체 삭제, SD_CLIENT_TYPE 테스트 삭제, forge factory 테스트 삭제, _ensure_correct_checkpoint 검증 삭제 |
| `test_composition.py` | SD_CLIENT_TYPE UnboundLocalError regression 테스트 삭제 |
| `test_comfy_client.py` | `_resolve_checkpoint` 테스트: override_settings → sd_model_checkpoint 직접 필드, `TestForgeClientComfyWorkflowStrip` 클래스 삭제 (ForgeClient import 제거) |
| `test_image_generation_core.py` | `_ensure_correct_checkpoint` 테스트 3건 삭제 |
| `test_generation_pipeline.py` | Hi-Res Fix payload 테스트 4건 삭제, ADetailer 테스트 삭제 |
| `test_pose_detection.py` | `_resolve_model_name` mock → 직접 사용으로 변경 |
| `test_image_cache.py` | `override_settings` → `clip_skip` 필드 |
| `test_router_controlnet.py` | `check_controlnet_available` mock 4건 삭제/수정 |

### Forge 잔존 주석 정리 (R1 리뷰 반영)
- `"(ignored by ForgeClient)"` 주석 제거: `controlnet.py:829`, `image_generation_core.py:190`, `schemas.py:695`
- Forge 관련 docstring/주석 일괄 정리

### 린트 통과
- ruff check + format 적용
- 삭제된 import 잔존 없음 확인 (SD_CLIENT_TYPE, _ensure_correct_checkpoint, _resolve_model_name, override_settings, check_controlnet_available 관련)

---

## 실행 순서 (의존성)

```
Phase D1 (forge.py 삭제) ← Phase D2 (factory 정리) ← Phase D3 (SD_CLIENT_TYPE 제거)
Phase A1 (composition 분기) — 독립
Phase A2 (reference 분기) — 독립
Phase A3 + B1 + controlnet.py:832 — 반드시 동시 처리 (checkpoint 전달 경로 통일)
Phase B2 (Hi-Res 제거) — 독립
Phase B3 (_resolve_model_name) — 독립
Phase B4 (ControlNet 정리 + generation_controlnet.py) ← Phase B3
Phase C1 (weight emphasis) — 독립 (사전 grep 확인 후)
Phase C2 (config 상수) ← Phase D1, D3 — forge.py/SD_CLIENT_TYPE 삭제 후 미사용 상수 확정
Phase C3 (로깅) ← Phase D3
Phase D4 (.env.example) — 독립
```

**권장 실행 순서:**
1. Phase A (A1, A2 병렬 → A3+B1 동시)
2. Phase B (B2 독립, B3 → B4+generation_controlnet.py)
3. Phase D (D1 → D2 → D3 → D4)
4. Phase C (C1 병렬, C2 → C3)
5. 테스트 업데이트 + Forge 잔존 주석 정리 + 린트
