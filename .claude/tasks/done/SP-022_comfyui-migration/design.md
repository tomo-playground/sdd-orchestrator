# SP-022 상세 설계: ComfyUI 마이그레이션

> 작성: 2026-03-24 | 상태: design
> 의존: SP-077 (SDClientBase ABC + ForgeClient + factory) 완료 후 착수

## 현황 분석

### SP-077이 제공하는 기반

SP-077 완료 시 `backend/services/sd_client/` 패키지가 존재하며:

| 파일 | 내용 |
|------|------|
| `__init__.py` | `SDClientBase` ABC (9개 추상 메서드) |
| `types.py` | `SDTxt2ImgResult`, `SDProgressResult` dataclass |
| `forge.py` | `ForgeClient(SDClientBase)` — 기존 SD WebUI 호출 래핑 |
| `factory.py` | `get_sd_client()` 싱글턴 팩토리, `SD_CLIENT_TYPE` 분기 |

팩토리의 `SD_CLIENT_TYPE == "comfy"` 분기에 `NotImplementedError("ComfyUI client: SP-022")` 플레이스홀더가 존재.

### SDClientBase 인터페이스 (9개 메서드)

```python
class SDClientBase(ABC):
    async def txt2img(self, payload: dict, timeout: float | None = None) -> SDTxt2ImgResult
    async def get_options() -> dict
    async def set_options(options: dict, timeout: float | None = None) -> dict
    async def get_models() -> list[dict]
    async def get_loras() -> list[dict]
    async def get_progress() -> SDProgressResult
    async def controlnet_detect(payload: dict) -> dict
    async def check_controlnet() -> bool
    async def get_controlnet_models() -> list[str]
```

### 기존 ComfyUI 코드 (`comfyui/`)

프로젝트 루트에 실험용 코드가 존재:
- `comfyui/workflow_runner.py` — **동기** urllib 기반 (queue_prompt → poll history → download)
- `comfyui/generate_reference.py` — 캐릭터 레퍼런스 생성 스크립트
- `comfyui/workflows/reference.json` — 검증 완료된 워크플로우 (DynamicThresholding 포함)

이 코드는 `backend/services/sd_client/comfy.py`로 통합하면서 **비동기 httpx/websocket**으로 전환해야 한다.

### ComfyUI API 프로토콜

ComfyUI는 SD WebUI와 완전히 다른 API 체계:

| 기능 | SD WebUI (Forge) | ComfyUI |
|------|-----------------|---------|
| 이미지 생성 | `POST /sdapi/v1/txt2img` (payload → base64) | `POST /prompt` (workflow JSON → prompt_id) |
| 결과 수집 | 동기 응답 body에 base64 | `GET /history/{prompt_id}` → 파일명 → `GET /view?filename=` |
| 진행률 | `GET /sdapi/v1/progress` | WebSocket `/ws` (JSON 메시지) |
| 옵션 관리 | `GET/POST /sdapi/v1/options` | 워크플로우 노드에 체크포인트 직접 지정 |
| 모델 목록 | `GET /sdapi/v1/sd-models` | `GET /object_info/CheckpointLoaderSimple` |
| LoRA 목록 | `GET /sdapi/v1/loras` | `GET /object_info/LoraLoader` |
| ControlNet | Extension API | 커스텀 노드 (워크플로우에 포함) |

**핵심 차이**: ComfyUI는 "워크플로우 JSON을 큐에 넣고 → 결과를 폴링"하는 비동기 모델.

---

## 설계

### Phase A 범위 재정의 (SP-022 vs SP-077)

SP-022의 Phase A("SD Client 추상화")는 SP-077로 완전히 이관되었다.
**SP-022는 Phase B~E에 집중**: ComfyUIClient 구현 + 워크플로우 관리 + 레퍼런스/씬 전환.

---

### DoD Phase B: 워크플로우 관리

#### B-1: `comfyui/workflows/` 디렉토리 + reference.json

**구현 방법:**
- 기존 `comfyui/workflows/reference.json`을 `backend/services/sd_client/comfyui/workflows/`로 이동
- 워크플로우 JSON의 `{{variable}}` 플레이스홀더 패턴 유지
- `_meta` 키에 변수 문서화 유지 (런타임에 제거)

**동작 정의:**
- `load_workflow("reference")` → JSON 파일 로드 → `_meta` 추출 (output_node ID 포함) → `_meta` 제거 → `(workflow_dict, output_node_id)` 튜플 반환 **[R1-3 반영]**
- `inject_variables(workflow, {"positive": "...", "seed": 42})` → 플레이스홀더 치환

**엣지 케이스:**
- 숫자 타입 변수: JSON에서 `"{{seed}}"` (문자열 위치)와 `{{seed}}` (숫자 위치) 모두 처리해야 함
  - 기존 `workflow_runner.py`의 패턴 재사용: 따옴표 포함/미포함 모두 치환
- 존재하지 않는 워크플로우 요청 시 `FileNotFoundError` (명확한 에러 메시지)
- 미치환 변수 잔존 검증: `inject_variables` 후 `{{` 패턴 잔존 시 warning 로그
- **[R1-3 반영]** `_meta.output_node` 미정의 시 자동 탐색: SaveImage class_type을 가진 노드 ID를 fallback으로 사용

**영향 범위:** 신규 파일 — 기존 코드 무영향

**테스트 전략:**
- `test_load_workflow()` — JSON 로드 + `_meta` 제거 확인
- `test_inject_variables_string()` — 문자열 치환
- `test_inject_variables_number()` — 숫자 치환 (따옴표 제거)
- `test_inject_variables_missing_placeholder()` — 잔존 변수 warning
- `test_workflow_not_found()` — FileNotFoundError

**Out of Scope:** scene_single.json, scene_multi.json (Phase D에서 추가)

---

#### B-2: `comfyui/workflow_runner.py` → `services/sd_client/comfyui/workflow_runner.py`

**구현 방법:**
- 기존 동기 urllib → **비동기 httpx** 전환
- `queue_prompt(workflow)` → `async def queue_prompt(workflow) -> str` (prompt_id 반환)
- `wait_for_result(prompt_id)` → `async def wait_for_result(prompt_id) -> list[bytes]`
  - httpx로 `/history/{prompt_id}` 폴링
  - `/view?filename=` 로 이미지 다운로드
- `run_workflow(name, variables)` → `async def run_workflow(name, variables) -> list[bytes]`

**동작 정의:**
- Before: `urllib.request.urlopen()` 동기 블로킹
- After: `httpx.AsyncClient` 비동기, 이벤트 루프 미차단

**엣지 케이스:**
- ComfyUI 에러 응답: `{"error": "..."}` → `RuntimeError` raise
- 실행 에러 (status_str == "error"): 노드 에러 상세 로그 + raise
- 타임아웃: `COMFYUI_EXECUTION_TIMEOUT` + `COMFYUI_QUEUE_TIMEOUT` 기반 (3단 분리, R1-4 반영)
- ComfyUI 미기동: 연결 실패 시 `httpx.ConnectError` → 상위에서 처리
- **[R2-1 반영] 재시도**: `queue_prompt()`에 지수 백오프 retry (최대 3회, 1s/2s/4s). 연결 실패(ConnectError)는 즉시 raise
- **[R1-5 반영] 적응형 폴링**: `/history` 폴링 간격 0.5s → 1.5배 증가 → max 5s

**영향 범위:** 기존 `comfyui/workflow_runner.py`는 스크립트 용도로 유지. 신규 패키지 내에 비동기 버전 생성.

**테스트 전략:**
- `test_queue_prompt()` — httpx mock → prompt_id 반환
- `test_wait_for_result_success()` — history mock → 이미지 바이트 반환
- `test_wait_for_result_error()` — status_str=error → RuntimeError
- `test_wait_for_result_timeout()` — 타임아웃 → TimeoutError
- `test_run_workflow_integration()` — load → inject → queue → wait 체인

**Out of Scope:** WebSocket 실시간 진행률 (Phase E 이후)

---

### DoD Phase B (cont.): `ComfyUIClient(SDClientBase)`

#### B-3: `services/sd_client/comfyui/__init__.py` — ComfyUIClient 구현

**구현 방법:**

```python
class ComfyUIClient(SDClientBase):
    def __init__(self, base_url: str | None = None):
        self._base_url = (base_url or COMFYUI_BASE_URL).rstrip("/")
        # [R1-1 반영] 인스턴스 레벨 연결 풀 — 매 요청마다 생성하지 않음
        self._http_client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=COMFYUI_NETWORK_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def close(self):
        """Shutdown 시 연결 풀 정리. main.py lifespan에서 호출."""
        await self._http_client.aclose()

    async def txt2img(self, payload: dict, timeout: float | None = None) -> SDTxt2ImgResult:
        """SD WebUI payload → ComfyUI 워크플로우 변환 → 실행 → SDTxt2ImgResult."""
        # 1. payload에서 워크플로우 타입 결정 (reference / scene_single / default)
        # 2. payload → 워크플로우 변수 매핑
        # 3. run_workflow() 실행
        # 4. bytes → base64 변환 → SDTxt2ImgResult
```

**payload → 워크플로우 변수 매핑 전략:**

SP-077의 `ForgeClient.txt2img()`는 SD WebUI 형식 payload dict를 그대로 전달한다.
ComfyUIClient는 **동일한 payload dict**를 받아서 워크플로우 변수로 변환해야 한다.

| SD WebUI payload 키 | ComfyUI 워크플로우 변수 | 비고 |
|---------------------|----------------------|------|
| `prompt` | `{{positive}}` | |
| `negative_prompt` | `{{negative}}` | |
| `steps` | KSampler.steps | 워크플로우 JSON 노드 직접 수정 |
| `cfg_scale` | KSampler.cfg | |
| `width` | EmptyLatentImage.width | |
| `height` | EmptyLatentImage.height | |
| `seed` | KSampler.seed | -1 → 랜덤 생성 |
| `override_settings.sd_model_checkpoint` | CheckpointLoaderSimple.ckpt_name | |
| `alwayson_scripts.controlnet` | Phase D에서 워크플로우 노드로 변환 | |

**워크플로우 선택 로직:**
- `payload.get("_comfy_workflow")` 명시적 지정 시 해당 워크플로우 사용
- 그 외: `"default"` 워크플로우 (기본 txt2img)
- Phase C 레퍼런스: `"reference"` 워크플로우

**9개 ABC 메서드 매핑:**

| 메서드 | ComfyUI 구현 |
|--------|-------------|
| `txt2img` | 워크플로우 변환 + `run_workflow()` |
| `get_options` | `{"sd_model_checkpoint": self._current_checkpoint}` (내부 상태 반환) |
| `set_options` | 워크플로우 내 체크포인트 노드 변경 (실제 전환은 생성 시 발생) |
| `get_models` | `GET /object_info/CheckpointLoaderSimple` → input choices 파싱 |
| `get_loras` | `GET /object_info/LoraLoader` → input choices 파싱 |
| `get_progress` | `GET /prompt` → queue 상태 기반 근사 진행률 |
| `controlnet_detect` | `NotImplementedError` (ComfyUI는 감지를 워크플로우 내에서 처리) |
| `check_controlnet` | `GET /object_info` → ControlNet 관련 노드 존재 확인 |
| `get_controlnet_models` | `GET /object_info/ControlNetLoader` → input choices 파싱 |

**동작 정의:**
- `txt2img()`: payload dict → 워크플로우 변수 추출 → `inject_variables()` → `queue_prompt()` → `wait_for_result()` → bytes → base64 → `SDTxt2ImgResult`
- `get_models()`: ComfyUI의 `/object_info/CheckpointLoaderSimple`에서 `input.required.ckpt_name[0]` (선택지 리스트) 파싱 → ForgeClient와 호환되는 `[{"title": "name.safetensors", "model_name": "name"}]` 형식 변환

**엣지 케이스:**
- `controlnet_detect()` — ComfyUI에서 지원 불가 → `NotImplementedError("ComfyUI uses workflow nodes for detection")`
- 체크포인트 전환 — SD WebUI처럼 글로벌 전환이 아니라 워크플로우별 지정이므로, `set_options()`는 내부 상태만 업데이트하고 다음 `txt2img()` 호출 시 적용
- LoRA 주입 — SD WebUI의 `<lora:name:weight>` 프롬프트 삽입 대신 워크플로우의 LoraLoader 노드 사용
  - Phase B에서는 `<lora:>` 태그가 프롬프트에 포함된 상태로 올 수 있음 → 파싱 후 LoraLoader 노드 동적 추가 또는 프롬프트에서 제거 필요
  - 초기 구현: 프롬프트에서 `<lora:>` 태그 제거 + LoraLoader 노드 체이닝

**영향 범위:**
- `factory.py`의 `"comfy"` 분기 → `ComfyUIClient()` 인스턴스 반환으로 변경
- `config.py` — `COMFYUI_BASE_URL`, `COMFYUI_TIMEOUT_SECONDS` 추가

**테스트 전략:**
- `test_comfy_client_txt2img()` — workflow_runner mock → SDTxt2ImgResult 반환
- `test_comfy_client_get_models()` — object_info mock → 모델 리스트
- `test_comfy_client_get_loras()` — object_info mock → LoRA 리스트
- `test_comfy_client_controlnet_detect_raises()` — NotImplementedError
- `test_payload_to_workflow_variables()` — SD WebUI payload → 워크플로우 변수 변환
- `test_lora_tag_extraction()` — `<lora:name:0.7>` 파싱 + 제거

**Out of Scope:** WebSocket 진행률, 배치 생성, Regional Prompting

---

### DoD Phase C: 레퍼런스 생성 전환

#### C-1: 캐릭터 레퍼런스 생성을 ComfyUI로 전환

**구현 방법:**
- `services/controlnet.py`의 `generate_reference_for_character()` 수정
  - `SD_CLIENT_TYPE == "comfy"` 시: `reference.json` 워크플로우 사용
  - `SD_CLIENT_TYPE == "forge"` 시: 기존 ForgeClient 동작 유지
- ComfyUI 레퍼런스 워크플로우:
  - CheckpointLoaderSimple → LoraLoader (스타일) → DynamicThresholdingFull → CLIPTextEncode(+/-) → KSampler → VAEDecode → SaveImage
  - DynamicThresholding 필수 (mimic_scale=5.0, NoobAI v-pred 안정화)

**payload 변환 상세:**

현재 `generate_reference_for_character()`는 다음 payload를 구성:
```python
payload = {
    "prompt": full_prompt,
    "negative_prompt": ...,
    "steps": steps,
    "width": SD_DEFAULT_WIDTH,
    "height": SD_DEFAULT_WIDTH,  # 정사각형
    "cfg_scale": cfg_scale,
    "seed": seed,
}
apply_sampler_to_payload(payload, sampler_name)
```

이 payload가 `get_sd_client().txt2img(payload)`로 전달되면:
- ForgeClient: 그대로 SD WebUI에 POST
- ComfyUIClient: `reference.json` 워크플로우의 변수로 매핑

ComfyUIClient 내부에서 `_comfy_workflow` 힌트 또는 용도 감지:
- **방안 A**: `payload["_comfy_workflow"] = "reference"` 명시적 힌트
- **방안 B**: payload 패턴으로 자동 감지 (정사각형 + ControlNet 없음 → reference)

**결정: 방안 A 채택** — 명시적이고 확장 가능. ForgeClient는 `_comfy_workflow` 키를 무시.

**추가 워크플로우 변수:**
- `{{checkpoint}}`: StyleProfile의 `sd_model_name` 또는 기본 체크포인트
- `{{lora_name}}`: 스타일 LoRA 파일명 (프롬프트에서 `<lora:>` 파싱)
- `{{lora_strength}}`: LoRA 가중치

**동작 정의:**
- ComfyUI로 전환 시에도 동일한 프롬프트 조합 파이프라인 사용 (compose_for_reference 등)
- 이미지 품질 비교: 동일 seed로 ForgeUI와 ComfyUI 결과 비교 (수동 검증)

**엣지 케이스:**
- DynamicThresholding 커스텀 노드 미설치: `queue_prompt()` 시 에러 → 명확한 에러 메시지 ("sd-dynamic-thresholding node required")
- 스타일 LoRA 없는 캐릭터: LoraLoader 노드 스킵 필요 → 워크플로우 분기 또는 strength=0
  - **결정**: strength=0으로 비활성화 (워크플로우 구조 유지)
- save_node ID 변경: `reference.json`에서는 `"9_save"` → 워크플로우별 save_node 설정

**영향 범위:**
- `services/controlnet.py` — `generate_reference_for_character()` 내부 (호출부 변경 불필요)
- `services/characters/reference.py` — 간접 호출 (변경 불필요, `generate_reference_for_character` 호출)

**테스트 전략:**
- `test_reference_generation_comfy()` — ComfyUIClient mock → 레퍼런스 이미지 생성 확인
- `test_reference_generation_forge_unchanged()` — ForgeClient 동작 회귀 테스트
- `test_reference_dynamic_thresholding_error()` — 노드 미설치 에러 핸들링
- 수동 검증: 실제 ComfyUI 서버로 캐릭터 5명 레퍼런스 생성 → 기존 결과 대비 품질 비교

**Out of Scope:** Hi-Res Fix 적용 (Phase D 이후), 멀티 캐릭터 레퍼런스

---

### DoD Phase D: 씬 이미지 전환

#### D-1: 1인 씬 이미지를 ComfyUI로 전환

**구현 방법:**
- `services/sd_client/comfyui/workflows/scene_single.json` 워크플로우 생성
  - CheckpointLoader → LoraLoader(스타일) → [LoraLoader(캐릭터)] → CLIPTextEncode → KSampler → VAEDecode → SaveImage
  - DynamicThresholding 포함
- `ComfyUIClient.txt2img()` — `_comfy_workflow == "scene_single"` 또는 기본 워크플로우로 처리

**워크플로우 설계:**
- reference.json과 유사하나 이미지 크기가 832x1216 (세로형)
- LoRA 체이닝: 스타일 LoRA + 캐릭터 LoRA 순차 적용
  - 프롬프트에서 `<lora:name:weight>` 파싱 → LoraLoader 노드 동적 추가
  - 최대 3개 LoRA 지원 (스타일 1 + 캐릭터 1 + 추가 1)

**동작 정의:**
- `_generate_scene_image_with_db()` → `_call_sd_api_raw()` → `get_sd_client().txt2img(payload)` 체인이 SP-077에서 이미 구성됨
- ComfyUIClient가 payload를 받아서 적절한 워크플로우로 변환

**엣지 케이스:**
- ADetailer (얼굴 보정): ComfyUI에서는 Impact Pack의 FaceDetailer 노드
  - 초기 구현: ADetailer 스킵 (Phase E 이후)
  - 기존 `_build_adetailer_args()` → ComfyUI에서는 무시
- Hi-Res Fix: ComfyUI에서는 별도 KSampler (img2img) 노드
  - 초기 구현: Hi-Res Fix 스킵
- `override_settings`: ComfyUI에서는 무의미 → 워크플로우 노드로 대체 완료

**영향 범위:**
- `services/generation.py` — 변경 불필요 (SP-077에서 이미 `get_sd_client().txt2img()` 사용)
- `services/image_generation_core.py` — 변경 불필요

**테스트 전략:**
- `test_scene_single_comfy()` — 기본 씬 생성 mock 테스트
- `test_lora_chain_in_workflow()` — 복수 LoRA 노드 동적 생성 확인
- `test_adetailer_skipped_in_comfy()` — ADetailer 관련 payload 무시 확인

**Out of Scope:** 2인 씬 Regional Prompting (SP-023), ADetailer, Hi-Res Fix

---

#### D-2: ControlNet 워크플로우 검증

**구현 방법:**
- ComfyUI에서 ControlNet은 워크플로우 노드로 처리
- `generation_controlnet.py`의 `apply_controlnet()`이 생성하는 `alwayson_scripts.controlnet` payload를 ComfyUIClient가 해석
- **전환 전략**: `alwayson_scripts.controlnet.args` 배열에서 enabled=True인 유닛을 추출 → ComfyUI ControlNetApply 노드로 변환

| SD WebUI ControlNet payload | ComfyUI 노드 |
|---|---|
| `{"model": "openpose_pre", "image": base64, "weight": 0.8}` | ControlNetLoader + ControlNetApply |
| `{"module": "reference_only", "image": base64}` | 제거 (ComfyUI에서는 IP-Adapter로 대체) |

**동작 정의:**
- ControlNet 페이로드가 없으면 기본 워크플로우 사용
- ControlNet 페이로드가 있으면 `scene_single_cn.json` 변형 워크플로우 사용 (또는 동적 노드 삽입)

**결정 [R1-2 반영 — 변경]**: ~~동적 노드 삽입 방식~~ → **Fat Template + Bypass 전략** 채택
- `scene_single.json`에 ControlNetApply + IPAdapter 노드를 미리 포함 (Fat Template)
- 미사용 시 `strength=0` / `weight=0`으로 비활성화 (워크플로우 구조 유지)
- ~~`_inject_controlnet_nodes()`~~ → `workflow_loader.py`의 `apply_bypass()` 함수로 대체

**엣지 케이스:**
- ControlNet 모델 이름 차이: Forge `openpose_pre [hash]` vs ComfyUI `control_v11p_sd15_openpose.safetensors`
  - 매핑 테이블 필요: `COMFYUI_CN_MODEL_MAP`
- 이미지 입력 형식: SD WebUI는 base64, ComfyUI는 LoadImage 노드 또는 base64 직접 입력
  - ComfyUI의 ControlNetApplyAdvanced 노드는 이미지 텐서 입력 → base64를 임시 파일로 저장 후 LoadImage 노드 사용

**영향 범위:** ComfyUIClient 내부만 변경

**테스트 전략:**
- `test_inject_controlnet_nodes()` — 워크플로우에 CN 노드 삽입 확인
- `test_controlnet_model_mapping()` — Forge 이름 → ComfyUI 이름 변환

**Out of Scope:** IP-Adapter 워크플로우 (별도 설계 필요)

---

#### D-3: IP-Adapter 워크플로우 검증

**구현 방법:**
- ComfyUI에서 IP-Adapter는 `IPAdapter` 커스텀 노드 사용
- `alwayson_scripts.controlnet.args`의 IP-Adapter 유닛을 감지 → ComfyUI IPAdapter 노드로 변환

| SD WebUI IP-Adapter payload | ComfyUI 노드 |
|---|---|
| `{"module": "ip-adapter_clip_sdxl_plus_vith", "model": "NOOB-IPA-MARK1"}` | IPAdapterModelLoader + IPAdapter |

**결정**: Phase D-3에서는 IP-Adapter 기본 동작만 구현.
FaceID 및 2-Step 파이프라인은 SP-023 이후.

**엣지 케이스:**
- NOOB-IPA-MARK1 모델명 → ComfyUI에서의 모델명 매핑
- IP-Adapter weight/guidance 파라미터 → ComfyUI 노드의 weight/start_at/end_at 매핑

**테스트 전략:**
- `test_inject_ip_adapter_nodes()` — 워크플로우에 IPA 노드 삽입 확인
- 수동 검증: 동일 레퍼런스 이미지로 IP-Adapter 결과 비교

**Out of Scope:** FaceID, Regional Prompting (SP-023)

---

### DoD Phase E: 정리

#### E-1: config.py 설정 추가

**구현 방법:**
```python
# ComfyUI [R1-4 반영 — 3단 타임아웃 분리]
COMFYUI_BASE_URL = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
COMFYUI_NETWORK_TIMEOUT = float(os.getenv("COMFYUI_NETWORK_TIMEOUT", "10"))        # 개별 HTTP 요청
COMFYUI_EXECUTION_TIMEOUT = float(os.getenv("COMFYUI_EXECUTION_TIMEOUT", "180"))    # 이미지 생성 대기
COMFYUI_QUEUE_TIMEOUT = float(os.getenv("COMFYUI_QUEUE_TIMEOUT", "300"))            # 큐 대기 포함 총 대기
```

**동작 정의:** `SD_CLIENT_TYPE = "comfy"` 시 ComfyUI 설정 사용, `"forge"` 시 기존 설정 사용.

**영향 범위:** `config.py` 4줄 추가

**테스트 전략:** 환경변수 기본값 확인

---

#### E-2: ForgeUI 의존성 유지 (fallback)

**구현 방법:**
- `config.py`의 `SD_CLIENT_TYPE` 기본값은 `"forge"` 유지
- ComfyUI 안정화 확인 후 기본값을 `"comfy"`로 전환 (별도 PR)
- ForgeUI 코드 제거는 하지 않음 (스위치로 선택 가능)

**동작 정의:** ForgeUI와 ComfyUI 중 하나만 활성. 동시 사용 없음.

**테스트 전략:**
- `SD_CLIENT_TYPE=forge` 시 기존 전체 테스트 통과
- `SD_CLIENT_TYPE=comfy` 시 신규 ComfyUI 테스트 통과

---

#### E-3: 기존 테스트 통과 + 린트

**구현 방법:**
- `pytest backend/tests/ -x` 전체 실행
- ForgeClient 기반 기존 테스트 → 모두 통과 (SD_CLIENT_TYPE 기본값 forge)
- ComfyUIClient 전용 테스트 → 별도 테스트 파일

**테스트 전략:**
- 기존 테스트 100% 통과 (회귀 없음)
- 신규 테스트: `tests/test_comfy_client.py` (15~20개)

---

## 신규 파일 구조

```
backend/services/sd_client/
├── __init__.py          # SDClientBase ABC (SP-077 제공)
├── types.py             # SDTxt2ImgResult, SDProgressResult (SP-077 제공)
├── forge.py             # ForgeClient (SP-077 제공)
├── factory.py           # get_sd_client() + close_sd_client() (SP-077 제공, comfy 분기 SP-022 완성)
└── comfyui/             # [SP-022 신규]
    ├── __init__.py      # ComfyUIClient(SDClientBase) — 인스턴스 레벨 httpx pool [R1-1]
    ├── workflow_runner.py  # 비동기 queue(+retry) → adaptive poll → download [R2-1, R1-5]
    ├── workflow_loader.py  # JSON 로드 + output_node 추출 + 변수 치환 + bypass 적용 [R1-3, R1-2]
    ├── payload_converter.py  # SD WebUI payload → 워크플로우 변수 변환
    └── workflows/        # 워크플로우 JSON (Fat Template)
        ├── reference.json     # 캐릭터 레퍼런스 (LoRA 1슬롯, 검증 완료)
        └── scene_single.json  # 1인 씬 (LoRA 3슬롯 + CN + IPA Fat Template) [R1-2]
```

> **[R1-2 반영] `node_injector.py` 삭제**. 동적 노드 삽입 대신 Fat Template + Bypass 전략.
```

## 구현 순서 (안전한 단계)

1. **Step 1**: config.py 설정 추가 (E-1)
2. **Step 2**: `comfyui/` 패키지 기본 구조 생성 (workflow_loader, workflow_runner)
3. **Step 3**: ComfyUIClient 기본 구현 (txt2img + get_models + get_loras)
4. **Step 4**: factory.py comfy 분기 연결
5. **Step 5**: payload_converter — SD WebUI payload → 워크플로우 변수
6. **Step 6**: reference.json 워크플로우 통합 + 레퍼런스 생성 전환 (Phase C)
7. **Step 7**: scene_single.json + LoRA 동적 주입 (Phase D-1)
8. **Step 8**: node_injector — ControlNet/IP-Adapter 노드 삽입 (Phase D-2, D-3)
9. **Step 9**: 전체 테스트 + 린트 (Phase E)

## 변경 파일 요약 (예상 15개)

| 파일 | 유형 |
|------|------|
| `config.py` | 수정 — ComfyUI 설정 3줄 |
| `services/sd_client/factory.py` | 수정 — comfy 분기 1곳 (SP-077 완료본) |
| `services/sd_client/comfyui/__init__.py` | 신규 — ComfyUIClient |
| `services/sd_client/comfyui/workflow_runner.py` | 신규 — 비동기 워크플로우 실행 |
| `services/sd_client/comfyui/workflow_loader.py` | 신규 — JSON 로드 + 변수 치환 |
| `services/sd_client/comfyui/payload_converter.py` | 신규 — payload 변환 |
| ~~`services/sd_client/comfyui/node_injector.py`~~ | **삭제** — Fat Template + Bypass로 대체 [R1-2] |
| `services/sd_client/comfyui/workflows/reference.json` | 이동 — 기존 검증 완료 워크플로우 |
| `services/sd_client/comfyui/workflows/scene_single.json` | 신규 — 씬 워크플로우 |
| `tests/test_comfy_client.py` | 신규 — ComfyUIClient 테스트 |
| `tests/test_workflow_loader.py` | 신규 — 워크플로우 로더 테스트 |
| `tests/test_workflow_runner.py` | 신규 — 워크플로우 러너 테스트 |
| `tests/test_payload_converter.py` | 신규 — payload 변환 테스트 |
| ~~`tests/test_node_injector.py`~~ | **삭제** — [R1-2] |
| 문서 업데이트 | 수정 — SD_CLIENT_ABSTRACTION.md 등 |

## 리스크 및 완화

| 리스크 | 심각도 | 완화 |
|--------|--------|------|
| LoRA `<lora:>` 태그 파싱 실패 | 높 | 정규식 + 단위 테스트 5개, ForgeClient 동작 비교 |
| ComfyUI 커스텀 노드 미설치 | 높 | 스타트업 시 `/object_info` 체크 + 명확한 에러 메시지 |
| 워크플로우 변수 미치환 잔존 | 중 | `inject_variables` 후 `{{` 패턴 검증 |
| ControlNet 모델명 매핑 누락 | 중 | COMFYUI_CN_MODEL_MAP에 fallback (이름 그대로 시도) |
| 이미지 품질 차이 | 중 | 수동 A/B 비교 (동일 seed, 동일 프롬프트) |
| ComfyUI 서버 다운 시 fallback | 낮 | SD_CLIENT_TYPE 스위치로 즉시 ForgeUI 복귀 |

## Performance Engineer 리뷰 포인트

ComfyUI는 새로운 외부 API 연동이므로 확인 필요 (**리뷰 반영 완료**):
- **[반영] 3단 타임아웃**: NETWORK(10s) / EXECUTION(180s) / QUEUE(300s) 분리
- **[반영] httpx 연결 풀**: `ComfyUIClient` 인스턴스 레벨 연결 풀 (limits 설정)
- **[반영] 적응형 폴링**: 0.5s → 1.5배 증가 → max 5s (지수 백오프)
- **[반영] 재시도**: `queue_prompt()` 지수 백오프 retry (최대 3회)
- **[반영] 라이프사이클**: `close_sd_client()` → `main.py` lifespan shutdown에서 호출

---

## 설계 리뷰 결과 (난이도: 상)

> 리뷰어: Tech Lead + Performance Engineer
> 일시: 2026-03-24
> 라운드: 3회 (구조 결함 → 부작용 → 정합성)

### Gemini 자문 (3라운드, Consensus 9/10)

Gemini brainstorm에서 도출된 핵심 합의:

1. **httpx 연결 풀**: 매 요청마다 `async with httpx.AsyncClient()` 생성은 소켓 고갈 + 핸드셰이크 오버헤드 유발. 인스턴스 레벨 연결 풀로 전환 필수.
2. **node_injector.py 폐기**: 동적 노드 삽입(DAG 직접 조작)은 최악의 안티패턴. **Fat Template + Bypass/Strength=0** 전략으로 대체 강력 권고.
3. **타임아웃 3단 분리**: NETWORK(10s) / QUEUE_WAIT(300s) / EXECUTION(120s) 분리. 현재 TIMEOUT_SECONDS(120)과 MAX_WAIT_SEC(120) 이중 정의는 혼란 유발.
4. **적응형 폴링**: 고정 1초 대신 지수 백오프(1s → 1.5s → 2.25s, max 5s) 도입으로 ComfyUI 부하 경감.
5. **ControlNet 이미지 전달**: base64 → 임시 파일 대신 ComfyUI `/upload/image` API 활용으로 파일 생명주기를 ComfyUI에 위임.
6. **스타트업 Health Check**: `/object_info`로 필수 커스텀 노드(DynamicThresholding 등) 설치 검증 필수.

---

### Round 1: 구조적 결함, 누락, 아키텍처 위반

| # | 심각도 | 영역 | 이슈 | 근거 | 조치 |
|---|--------|------|------|------|------|
| R1-1 | **BLOCKER** | Performance | httpx 연결 풀 미사용. "생성마다 `async with httpx.AsyncClient()` 생성"은 ComfyUI 폴링(수십 회 GET)에서 소켓 고갈 위험 | 기존 코드에서 `httpx.AsyncClient`를 매번 생성하는 패턴이 15곳 존재 (ForgeClient 동일). ComfyUI는 queue+poll+download 최소 3회 호출이므로 더 심각 | `ComfyUIClient.__init__()`에서 `httpx.AsyncClient(limits=..., base_url=...)` 생성, `aclose()` 메서드로 라이프사이클 관리. `main.py` lifespan에서 shutdown 시 close. ForgeClient도 향후 동일 적용 권장 |
| R1-2 | **BLOCKER** | Architecture | `node_injector.py` — ControlNet/LoRA 노드 동적 삽입은 DAG 무결성 파괴 위험. 노드 ID 충돌, model/clip 연결 체이닝 오류 디버깅 불가 | ComfyUI 워크플로우는 `[node_id, output_index]` 참조 그래프. 동적 삽입 시 기존 연결 재배선 필요. 누락 시 silent failure | **Fat Template + Bypass 전략**으로 전환. 워크플로우 JSON에 LoraLoader/ControlNetApply/IPAdapter 노드를 미리 포함하고, 미사용 시 `strength=0`으로 비활성화. `node_injector.py` 파일 자체 삭제 |
| R1-3 | **BLOCKER** | Architecture | save_node ID 불일치 버그. `workflow_runner.py` 기본값 `"8_save"`, 실제 `reference.json` SaveImage 노드 ID `"9_save"`. `generate_reference.py`에서 save_node 미지정 → 결과 수신 실패 | 코드 확인: `run_workflow("reference", ...)` 호출 시 `save_node` 파라미터 없음 → 기본값 `"8_save"` → `reference.json`의 `"9_save"` 미매칭 → TimeoutError 발생 | 워크플로우 `_meta`에 `"output_node"` 키 추가. `load_workflow()` 반환 시 output_node ID 함께 반환. 하드코딩 제거 |
| R1-4 | **WARNING** | Performance | 타임아웃 의미론 혼란. `COMFYUI_TIMEOUT_SECONDS`(HTTP 요청)과 `COMFYUI_MAX_WAIT_SEC`(폴링 대기) 둘 다 120초. ComfyUI 큐 대기 시 120초 부족 | ComfyUI 단일 큐: 앞선 생성 대기 필요. LoRA+DynThres 워크플로우 소요 20-40초 x 큐 깊이 | 3단 분리: `COMFYUI_NETWORK_TIMEOUT=10`, `COMFYUI_EXECUTION_TIMEOUT=180`, `COMFYUI_QUEUE_TIMEOUT=300`. 폴링 총 시간 = execution + queue |
| R1-5 | **WARNING** | Performance | 폴링 간격 고정 1초. 이미지 생성 20-40초 소요 → 20-40회 불필요한 /history 호출 | Gemini 자문: 지수 백오프 권고 | 적응형 폴링: 초기 0.5s → 1.5배 증가 → max 5s. 평균 호출 횟수 20회 → 8회로 감소 |
| R1-6 | **WARNING** | Architecture | `controlnet_detect()` → `NotImplementedError` 설계. ABC 계약 위반. 클라이언트 코드에서 `get_sd_client().controlnet_detect()` 호출 시 런타임 에러 | `controlnet.py:393`에서 detect 호출 존재. ComfyUI 전환 시 이 경로가 깨짐 | ABC에 `@property supports_controlnet_detect -> bool` 추가. 호출부에서 분기. 또는 ComfyUI용 대체 구현 (워크플로우 기반 detection 또는 별도 preprocessor) |
| R1-7 | **WARNING** | Security | ControlNet base64 → 임시 파일 → LoadImage 경로. 임시 파일 정리 전략 없음 | 디스크 누수 위험. 대량 생성 시 /tmp 가득 참 | Gemini 권고 채택: ComfyUI `/upload/image` API 사용. 파일 생명주기를 ComfyUI에 위임. 불가 시 `tempfile.NamedTemporaryFile(delete=True)` + `try...finally` |
| R1-8 | **INFO** | Architecture | `payload_converter.py` 단독 파일 필요성. SD WebUI payload → 워크플로우 변수 변환은 `ComfyUIClient.txt2img()` 내부 private 메서드로 충분 | 파일 5개 → 4개로 축소 가능 | `payload_converter.py`를 `ComfyUIClient._convert_payload()` private 메서드로 흡수 검토. 규모가 크면 유지해도 무방 |

---

### Round 2: R1 반영 후 부작용 검증, 엣지 케이스

| # | 심각도 | 영역 | 이슈 | 근거 | 조치 |
|---|--------|------|------|------|------|
| R2-1 | **BLOCKER** | Performance | 재시도(retry) 정책 완전 누락. `queue_prompt()` 네트워크 에러, `/history` 일시 장애 시 단순 실패. 기존 프로젝트에서 `audio_client.py`(503 retry), `youtube/upload.py`(exponential backoff) 등 retry 패턴 존재 | ComfyUI 서버 재시작 중, VRAM OOM 후 복구 등 일시 장애 빈번 | `queue_prompt()`에 지수 백오프 retry (최대 3회, 1s/2s/4s). `/history` 폴링은 이미 루프이므로 개별 실패 무시 (현행 유지). 연결 실패(ConnectError)는 즉시 raise (서버 다운 판정) |
| R2-2 | **WARNING** | Architecture | Fat Template + Bypass 전환 시 LoRA 체이닝 구조 변경. reference.json은 LoRA 1개 고정이지만, scene_single은 LoRA 0~3개 가변. Bypass 시 model/clip 연결 재배선 필요 | LoRA strength=0은 ComfyUI에서 모델을 통과시키지만 VRAM은 소비. 다수 LoRA 0-strength는 비효율 | 2가지 템플릿 전략: (1) `reference.json` — LoRA 1개 (현행 유지), (2) `scene_with_lora.json` — LoRA 최대 3슬롯 포함 Fat Template. 미사용 슬롯은 더미 LoRA + strength=0 또는 ComfyUI `SetNode` bypass |
| R2-3 | **WARNING** | Architecture | 스타트업 Health Check 미설계. `_meta.required_nodes` 검증 + ComfyUI 연결 확인이 `lifespan()`에 없음 | DynamicThresholdingFull 미설치 시 워크플로우 silent failure → prompt_id 반환되지만 실행 에러 | `lifespan()`에서 `SD_CLIENT_TYPE == "comfy"` 시 (1) ComfyUI 연결 확인, (2) `/object_info`에서 필수 노드 존재 검증 (DynamicThresholdingFull, LoraLoader, KSampler). 실패 시 WARNING 로그 (startup 차단 안 함) |
| R2-4 | **WARNING** | Performance | `ComfyUIClient` httpx 라이프사이클이 `lifespan()`과 정합 안 됨. 현재 `get_sd_client()`는 팩토리 싱글턴이지만 `aclose()` 호출 시점 불명확 | `main.py` lifespan shutdown에서 `get_sd_client()`의 `close()`를 호출해야 함. SP-077 팩토리에 `close_sd_client()` 함수 필요 | SP-077 설계에 `close_sd_client()` 추가 요청. SP-022에서 `ComfyUIClient.close()` → `self._http_client.aclose()` 구현. `main.py` shutdown에서 호출 |
| R2-5 | **WARNING** | Architecture | `_comfy_workflow` 힌트 키가 ForgeClient에서 무시되지만, payload에 잔존. `ForgeClient.txt2img()`가 SD WebUI에 그대로 POST하면 알 수 없는 키로 에러 가능 | SD WebUI `/sdapi/v1/txt2img`는 미지 키를 무시하므로 실제 에러는 아니지만 설계 청결성 문제 | `ForgeClient.txt2img()`에서 `payload.pop("_comfy_workflow", None)` 명시적 제거. 또는 payload 변환 계층에서 클라이언트별 키 분리 |
| R2-6 | **INFO** | Testing | ComfyUI 동시성(큐잉) 테스트 부재. 동시 2-3 요청 시 큐 대기 시나리오 미검증 | 실제 운영에서 레퍼런스 일괄 재생성 시 복수 요청 동시 발생 | 통합 테스트(mock)에서 큐 시뮬레이션: 첫 요청 즉시 실행, 두 번째 요청 큐 대기 → 타임아웃 내 완료 확인 |

---

### Round 3: 최종 정합성, 테스트 전략 완전성

| # | 심각도 | 영역 | 이슈 | 근거 | 조치 |
|---|--------|------|------|------|------|
| R3-1 | **WARNING** | Testing | 테스트 파일 4개 분산 (test_comfy_client, test_workflow_loader, test_workflow_runner, test_payload_converter, test_node_injector). R1-2에서 node_injector 폐기했으므로 테스트 구조 재설계 필요 | node_injector.py 삭제 → test_node_injector.py도 삭제. Fat Template bypass 테스트를 workflow_loader 테스트로 통합 | 테스트 파일 3개로 정리: (1) `test_workflow_loader.py` — JSON 로드 + 변수 치환 + bypass 적용, (2) `test_workflow_runner.py` — 비동기 queue/poll/download + retry + adaptive polling, (3) `test_comfy_client.py` — txt2img 통합 + get_models + payload 변환 |
| R3-2 | **WARNING** | Architecture | `workflow_loader.py`와 `workflow_runner.py` 책임 경계 불명확. loader는 JSON + 변수 치환, runner는 API 실행. 하지만 bypass 적용은 어디에? | Fat Template 전환 시 bypass 로직은 변수 치환 단계에서 수행 (payload에 ControlNet 없으면 해당 노드 strength=0) | `workflow_loader.py` 책임: (1) JSON 로드, (2) `_meta` 제거 + output_node 추출, (3) 변수 치환, (4) bypass 적용. `workflow_runner.py` 책임: (1) queue, (2) poll, (3) download. 명확히 분리 |
| R3-3 | **WARNING** | Docs | `SD_CLIENT_ABSTRACTION.md` 문서 업데이트 범위 불명확. SP-077과 SP-022의 문서 영역 경계 미정의 | SP-077이 SDClientBase 아키텍처 문서, SP-022가 ComfyUI 특화 섹션 추가 | SP-022에서 추가할 문서: (1) ComfyUI 워크플로우 관리 패턴, (2) Fat Template + Bypass 전략, (3) 타임아웃 3단 분리 설명, (4) 배포 시 ComfyUI 커스텀 노드 요구사항 |
| R3-4 | **INFO** | Architecture | 구현 순서에서 E-1(config)이 Step 1이지만, R1-4에서 타임아웃 체계가 변경됨. config 설계를 먼저 확정해야 후속 구현에 일관성 유지 | 설계 변경사항이 구현 순서에 미반영 | Step 1을 config 설계 확정으로 유지하되, 변경된 3단 타임아웃 반영: `COMFYUI_BASE_URL`, `COMFYUI_NETWORK_TIMEOUT(10)`, `COMFYUI_EXECUTION_TIMEOUT(180)`, `COMFYUI_QUEUE_TIMEOUT(300)` |
| R3-5 | **INFO** | Testing | 수동 검증 항목(캐릭터 5명 레퍼런스 비교)을 자동화 가능. 동일 seed + 동일 프롬프트 → SSIM 기반 유사도 비교 | SDD 원칙: 수동 항목 0개 목표 | 자동 비교 테스트는 ComfyUI 서버 의존이므로 CI에서는 skip. 로컬 통합 테스트 마커(`@pytest.mark.comfyui`)로 분리 |

---

### BLOCKER 종합 (반영 필수)

| # | BLOCKER | 반영 상태 |
|---|---------|----------|
| R1-1 | httpx 인스턴스 레벨 연결 풀 | **반영 완료** — B-3 ComfyUIClient `__init__` + `close()` 수정됨 |
| R1-2 | node_injector.py 폐기 → Fat Template + Bypass | **반영 완료** — 파일 구조 수정, Phase D ControlNet 전략 변경됨 |
| R1-3 | save_node ID 불일치 버그 수정 | **반영 완료** — B-1 load_workflow 동작 정의 + reference.json _meta.output_node 추가 |
| R2-1 | retry 정책 추가 (queue_prompt 지수 백오프) | **반영 완료** — B-2 엣지 케이스에 retry + adaptive polling 추가 |

### WARNING 종합 (반영 권고)

총 10건. 주요: 타임아웃 3단 분리(R1-4), 적응형 폴링(R1-5), ControlNet detect 대안(R1-6), 임시 파일 정리(R1-7), 스타트업 Health Check(R2-3), httpx 라이프사이클(R2-4), `_comfy_workflow` 키 정리(R2-5), 테스트 구조 재설계(R3-1), loader/runner 책임 분리(R3-2), 문서 범위(R3-3).

### 수정된 파일 구조 (BLOCKER 반영)

```
backend/services/sd_client/comfyui/
├── __init__.py          # ComfyUIClient(SDClientBase) — 인스턴스 레벨 httpx pool
├── workflow_runner.py   # 비동기 queue(+retry) → adaptive poll → download
├── workflow_loader.py   # JSON 로드 + output_node 추출 + 변수 치환 + bypass 적용
├── payload_converter.py # SD WebUI payload → 워크플로우 변수 (또는 __init__.py에 흡수)
├── [삭제] node_injector.py  # Fat Template + Bypass로 대체
└── workflows/
    ├── reference.json       # 캐릭터 레퍼런스 (LoRA 1슬롯)
    └── scene_single.json    # 1인 씬 (LoRA 3슬롯 + ControlNet + IPAdapter Fat Template)
```

### 수정된 config 설계 (R1-4 반영)

```python
# ComfyUI
COMFYUI_BASE_URL = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
COMFYUI_NETWORK_TIMEOUT = float(os.getenv("COMFYUI_NETWORK_TIMEOUT", "10"))
COMFYUI_EXECUTION_TIMEOUT = float(os.getenv("COMFYUI_EXECUTION_TIMEOUT", "180"))
COMFYUI_QUEUE_TIMEOUT = float(os.getenv("COMFYUI_QUEUE_TIMEOUT", "300"))
```
