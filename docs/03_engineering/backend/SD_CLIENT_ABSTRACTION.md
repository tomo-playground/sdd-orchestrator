# SD Client 추상화 — 기술 설계 상세

> 이 문서는 [COMFYUI_MIGRATION.md](../../01_product/FEATURES/COMFYUI_MIGRATION.md)의 기술 설계 상세(how)를 분리한 것.

---

## 파일별 SD WebUI 의존성 전수 목록

### `services/image_generation_core.py`

| 함수 | 분류 | 설명 |
|------|------|------|
| `_ensure_correct_checkpoint()` | **SD 의존** | GET/POST `/sdapi/v1/options` — 체크포인트 전환 |
| `generate_image_with_v3()` | **SD 의존** | POST `/sdapi/v1/txt2img` — 통합 이미지 생성 + 페이로드 구성 |
| `compose_scene_with_style()` | **부분 변경** | Sprint C에서 반환값 3-tuple → 4-tuple (LoRA 분리) |
| `resolve_style_loras_from_group()` | 순수 로직 | DB에서 Style LoRA 해석 |
| `_extract_loras_from_prompt()` | 순수 로직 | 정규식으로 프롬프트에서 LoRA 메타 추출 |

### `services/generation.py`

| 함수 | 분류 | 설명 |
|------|------|------|
| `_build_adetailer_args()` | **SD 페이로드** | ADetailer `alwayson_scripts` 구성 |
| `_build_payload()` | **SD 페이로드** | 기본 txt2img 페이로드 + Hi-Res + ADetailer |
| `_call_sd_api()` | **SD 의존** | 캐시 확인 + API 호출 |
| `_call_sd_api_raw()` | **SD 의존** | httpx.post(SD_TXT2IMG_URL) 직접 호출 |
| `_adjust_parameters()` | 순수 로직 | 복잡도 감지 → steps/cfg 조정 |
| `_generate_scene_image_with_db()` | 오케스트레이션 | 6단계 파이프라인 |

### `services/controlnet.py`

| 함수 | 분류 | 설명 |
|------|------|------|
| `check_controlnet_available()` | **SD 의존 (동기 requests)** | `/controlnet/version`, `/controlnet/model_list` |
| `get_controlnet_models()` | **SD 의존 (동기 requests)** | `/controlnet/model_list` |
| `_resolve_model_name()` | **SD 의존** | Forge 해시 포맷 모델명 resolve + 모듈 전역 캐시 |
| `generate_with_controlnet()` | **SD 의존 (동기 requests)** | ControlNet 페이로드 + txt2img 호출 |
| `create_pose_from_image()` | **SD 의존 (동기 requests)** | `/controlnet/detect` OpenPose 감지 |
| `generate_reference_for_character()` | **SD 의존 (비동기 httpx)** | 레퍼런스 이미지 생성 |
| `build_controlnet_args()` | **SD 페이로드** | ControlNet `alwayson_scripts` dict |
| `build_ip_adapter_args()` | **SD 페이로드** | IP-Adapter + NOOB-IPA 모듈 분기 |
| `build_reference_only_args()` | **SD 페이로드** | Reference-only ControlNet dict |
| `build_combined_controlnet_args()` | **SD 페이로드** | 결합 + 3슬롯 패딩 |
| `clamp_ip_adapter_weight()` ~ `_validate_reference_image()` | 순수 로직 | 6개 함수 (SD 무관) |

### `services/generation_controlnet.py`

| 함수 | 분류 | 설명 |
|------|------|------|
| `apply_controlnet()` | 오케스트레이션 | **async 전환 필요** |
| `_apply_pose_control()` ~ `classify_indoor_outdoor()` | 순수 로직 | 5개 함수 |
| `_apply_reference_adain_from_asset()` | **SD 페이로드** | Reference AdaIN dict 직접 구성 |

### `services/avatar.py`

| 함수 | 분류 | 설명 |
|------|------|------|
| `ensure_avatar_file()` | **SD 의존** | httpx.post + apply_sampler_to_payload() + override_settings. 비표준 `payload.pop("sampler_name")` 패턴 주의 |

### `services/lora_calibration.py`

| 함수 | 분류 | 설명 |
|------|------|------|
| `generate_test_image()` | **SD 의존** | httpx.post + build_controlnet_args() + 3슬롯 패딩 하드코딩 |

### `services/sd_progress_poller.py`

| 함수 | 분류 | 설명 |
|------|------|------|
| `poll_sd_progress()` | **SD 의존** | httpx.get(SD_PROGRESS_URL) — SD WebUI 전용 진행률 프로토콜 |

### `services/image_cache.py`

| 함수 | 분류 | 설명 |
|------|------|------|
| `image_cache_key()` | **SD 페이로드 의존** | `override_settings`, `alwayson_scripts` 구조에서 캐시 키 생성. DTO 전환 시 키 포맷 불가피하게 변경 — sampler_name (split 전 원본 vs split 후), scheduler (DTO에 없음), clip_skip (중첩 dict vs 최상위 필드) |

### `services/generation_style.py`

| 함수 | 분류 | 설명 |
|------|------|------|
| `_build_lora_parts()` | **LoRA 주입** | `<lora:name:weight>` 형식 생성 — Sprint C 영향 |

### `services/ip_adapter.py`

| 함수 | 분류 | 설명 |
|------|------|------|
| `build_dual_ip_adapter_args()` | **SD 페이로드** | `build_ip_adapter_args()` import — B-3 영향 |

### `routers/sd_models.py`

| 엔드포인트 | 분류 |
|-----------|------|
| `GET /sd/models`, `GET /sd/options`, `POST /sd/options`, `GET /sd/loras` | **SD 프록시** |
| DB CRUD 8개 엔드포인트 | 순수 로직 |

### `routers/controlnet.py`

| 엔드포인트 | 분류 |
|-----------|------|
| `GET /controlnet/status`, `POST /controlnet/detect-pose`, `GET /controlnet/ip-adapter/status` | **SD 의존 (동기 호출)** |
| 나머지 10+ 엔드포인트 | 순수 로직 |

### `scripts/` (5개 — Sprint A~E 범위 제외)

| 파일 | SD 의존 |
|------|---------|
| `test_sitting_quality.py` | `requests.post(SD_TXT2IMG_URL)` |
| `generate_sitting_pose_assets.py` | `SD_TXT2IMG_URL` + `/controlnet/detect` |
| `generate_character_previews.py` | `httpx.post(txt2img)` |
| `sync_webui_data.py` | `/sd-models`, `/loras`, `/embeddings` |
| `force_regenerate_thumbnails.py` | `httpx.post(txt2img)` |

---

## Forge 특화 지점 (전수 8곳)

| # | 위치 | 처리 내용 |
|---|------|----------|
| 1 | `config.py` `split_sampler_scheduler()` | A1111 → Forge sampler/scheduler 분리 |
| 2 | `config.py` `apply_sampler_to_payload()` | CFG Rescale phi 주입 |
| 3 | `generation_controlnet.py` | `_FORGE_CN_SLOTS = 3` 패딩 |
| 4 | `generation.py` `_build_payload()` | `hr_additional_modules: []` (Forge 필수) |
| 5 | `controlnet.py` `_resolve_model_name()` | Forge 해시 포맷 풀네임 resolve |
| 6 | `controlnet.py` `build_ip_adapter_args()` | NOOB-IPA 모듈 분기 |
| 7 | `controlnet.py` `generate_with_controlnet()` | 3슬롯 패딩 |
| 8 | `lora_calibration.py` | 3슬롯 패딩 하드코딩 |

---

## 동기/비동기 혼용 현황

| HTTP 클라이언트 | 파일 | 함수 |
|---------------|------|------|
| `requests` (동기) | `controlnet.py` | `check_controlnet_available()`, `get_controlnet_models()`, `generate_with_controlnet()`, `create_pose_from_image()` |
| `httpx` (비동기) | `generation.py`, `image_generation_core.py`, `controlnet.py`, `avatar.py`, `lora_calibration.py` | `_call_sd_api_raw()`, `generate_image_with_v3()`, `generate_reference_for_character()`, `ensure_avatar_file()`, `generate_test_image()` |

### async 전환 호출 체인

```
check_controlnet_available() [동기 → 비동기]
  ├─ apply_controlnet() [동기 → 비동기]
  │   └─ _generate_scene_image_with_db() [이미 async, await 추가만]
  ├─ routers/controlnet.py GET /status [이미 async def, await 추가]
  └─ routers/controlnet.py GET /ip-adapter/status [이미 async def, await 추가]

_resolve_model_name() [동기 → 비동기]
  ├─ build_controlnet_args() → WebUIClient 내부 이동으로 자동 해소
  └─ build_ip_adapter_args() → WebUIClient 내부 이동으로 자동 해소
```

---

## config.py SD 전용 설정 (전수)

| 카테고리 | 상수 수 | 주요 항목 |
|---------|--------|----------|
| SD URL/타임아웃 | 8개 | `SD_BASE_URL`, `SD_TXT2IMG_URL`, `SD_MODELS_URL`, `SD_OPTIONS_URL`, `SD_LORAS_URL`, `SD_TIMEOUT_SECONDS`, `SD_API_TIMEOUT`, `SD_MODEL_SWITCH_TIMEOUT` |
| 생성 기본값 | 7개 | `SD_DEFAULT_STEPS/CFG_SCALE/SAMPLER/WIDTH/HEIGHT/CLIP_SKIP`, `SD_CFG_RESCALE` |
| Sampler 유틸 | 2함수 | `split_sampler_scheduler()`, `apply_sampler_to_payload()` → **WebUIClient 이동** |
| ControlNet | 4개 | `CONTROLNET_API/GENERATE/DETECT_TIMEOUT`, `CONTROLNET_MODELS` dict |
| IP-Adapter | 6개 | `DEFAULT_IP_ADAPTER_GUIDANCE_*`, `IP_ADAPTER_MODELS` dict |
| ADetailer | 7개 | `ADETAILER_ENABLED/FACE_MODEL/HAND_MODEL/HAND_ENABLED/DENOISING_*/HIGH_ACCURACY_*` |
| Reference | 10개 | `REFERENCE_ADAIN_WEIGHT*`, `SD_REFERENCE_STEPS/CFG_SCALE/HR_UPSCALER/DENOISING/CONTROLNET_*/NUM_CANDIDATES` |
| Image Cache | 3개 | `SD_IMAGE_CACHE_ENABLED/DIR/MAX_SIZE_MB` |

**원칙**: 상수(값)는 config.py에 유지 (SSOT), 유틸리티 함수만 WebUIClient로 이동.

---

## WebUIClient 페이로드 변환 규칙

### GenerationParams → SD WebUI payload 매핑

| DTO 필드 | SD WebUI payload 키 | 비고 |
|---------|---------------------|------|
| `prompt` | `prompt` | WebUIClient가 LoRA 재주입 (`loras` → `<lora:name:weight>`) |
| `negative_prompt` | `negative_prompt` | |
| `steps` | `steps` | |
| `cfg_scale` | `cfg_scale` | |
| `width` | `width` | |
| `height` | `height` | |
| `seed` | `seed` | |
| `batch_size` | `batch_size` | |
| `sampler_name` | `sampler_name` + `scheduler` | `split_sampler_scheduler()` 적용 |
| `clip_skip` | `override_settings.CLIP_stop_at_last_layers` | |
| `cfg_rescale` | `extra_generation_params["CFG Rescale φ"]` | Forge 전용 |
| — | `override_settings_restore_afterwards: True` | Client 하드코딩 |
| `hires.*` | `enable_hr`, `hr_scale`, `hr_upscaler`, `hr_second_pass_steps`, `denoising_strength` | |
| — | `hr_additional_modules: []` | Forge 전용, Client 하드코딩 |
| `controlnet_units` + `ip_adapter_units` | `alwayson_scripts.controlnet.args` | 3슬롯 패딩 적용 |
| `adetailer_units` | `alwayson_scripts.ADetailer.args` | `ad_` prefix 변환 |
| `loras` | prompt에 `<lora:name:weight>` 재주입 | |

### ControlNetUnit type별 변환

| type | model | module | ComfyUI 대응 |
|------|-------|--------|-------------|
| `controlnet` | "openpose"/"depth"/etc | "None" | ControlNetApply 노드 |
| `reference_only` | "None" | "reference_only" | Reference-only 노드 |
| `reference_adain` | "None" | "reference_adain" | Reference AdaIN 노드 |

### IPAdapterUnit model 논리적 타입 → 실제 모델명

| 논리적 타입 | 실제 모델명 | resolve 경로 |
|------------|-----------|-------------|
| `"clip"` | `IP_ADAPTER_MODELS["clip"]` → `_resolve_model_name()` | Forge 해시 포함 풀네임 |
| `"clip_face"` | `IP_ADAPTER_MODELS["clip_face"]` → `_resolve_model_name()` | Forge 해시 포함 풀네임 |

---

## 6개 에이전트 크로스 리뷰 결과 요약

| 에이전트 | BLOCKER | WARNING | 핵심 |
|---------|---------|---------|------|
| DBA | 0 | 2 | DB 스키마 영향 없음. `activity_logs.sd_params` 키 호환 주의 |
| Frontend Dev | 0 | 1 | Frontend 수정 불필요. `/admin/sd/options` 프록시 형식 유지 |
| Security | 1 | 6 | DTO Field 검증, LoRA name 패턴, base64 크기 제한 |
| PM | 0 | 5 | 최상위 DoD, Phase 34 선행, 문서 분할, 일정 상향 |
| Backend Dev | 4 | 14 | scripts/ 누락, DTO 필드 불완전, async 추가 영향, LoRA 19곳 |
| QA | 3 | 4 | 테스트 ~100개 마이그레이션, 26개 신규, seed 비교 E2E |

**전체 BLOCKER 8건 해소 완료** — 계획서 2차 수정에 모두 반영.
