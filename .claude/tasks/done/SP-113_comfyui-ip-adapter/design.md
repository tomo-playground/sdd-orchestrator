# SP-113 상세 설계: ComfyUI IP-Adapter 워크플로우 노드 통합

## 아키텍처 결정

**Fat Template + Link Re-routing** 방식 채택.

- 워크플로우 JSON에 IP-Adapter 노드를 포함한 상태로 유지 (Fat Template)
- IP-Adapter 미사용 시 sampler의 `model` 입력 연결만 변경 (Re-routing)
- ComfyUI는 output에서 역추적하여 실행할 노드만 결정 → 연결 안 된 노드는 로드/실행 안 함
- VRAM 오버헤드 0, 단일 파일 관리, 코드 복잡도 최소

### 기각된 대안

| 방식 | 기각 사유 |
|------|----------|
| weight=0 bypass | CLIP Vision 모델 로드됨 (2-3GB VRAM 낭비) |
| 워크플로우 2벌 | DRY 위반, LoRA/checkpoint 변경 시 양쪽 수정 필요 |
| 동적 노드 주입 | 노드 생성 + 연결 코드 복잡, 유지보수 어려움 |
| 노드 삭제(Pruning) | 과잉 엔지니어링, 연결 변경만으로 충분 |

---

## DoD 1: scene_single.json에 IP-Adapter 노드 추가

### 구현 방법

`scene_single.json`에 3개 노드 추가:

```
12_ip_loader  (IPAdapterUnifiedLoader)  — model, clip_vision, ipadapter 로드
13_ip_image   (LoadImage)               — 레퍼런스 이미지 파일 참조
14_ip_apply   (IPAdapterAdvanced)       — model에 IP-Adapter 적용
```

**노드 체인 (IP-Adapter 활성화 시)**:
```
5_dynthres → 12_ip_loader → 14_ip_apply → 9_sampler
                              ↑
                         13_ip_image
```

**노드 체인 (IP-Adapter 비활성화 시 — Link Re-routing)**:
```
5_dynthres → 9_sampler  (12, 13, 14 노드는 orphaned → 실행 안 됨)
```

### 추가할 노드 정의

```json
"12_ip_loader": {
  "class_type": "IPAdapterUnifiedLoader",
  "inputs": {
    "model": ["5_dynthres", 0],
    "preset": "PLUS (high strength)"
  }
},
"13_ip_image": {
  "class_type": "LoadImage",
  "inputs": {
    "image": "{{ip_adapter_image}}"
  }
},
"14_ip_apply": {
  "class_type": "IPAdapterAdvanced",
  "inputs": {
    "model": ["12_ip_loader", 0],
    "ipadapter": ["12_ip_loader", 1],
    "image": ["13_ip_image", 0],
    "weight": "{{ip_adapter_weight}}",
    "weight_type": "linear",
    "start_at": 0.0,
    "end_at": "{{ip_adapter_end_at}}",
    "combine_embeds": "concat",
    "embeds_scaling": "K+mean(V) w/ C penalty"
  }
}
```

**9_sampler 변경**:
```json
"model": ["14_ip_apply", 0]  // 기존: ["5_dynthres", 0]
```

### 변수 목록 (variables 배열에 추가)

```
ip_adapter_image    — ComfyUI input 폴더의 레퍼런스 이미지 파일명
ip_adapter_weight   — float, 기본 0.5 (v-pred 안전 범위)
ip_adapter_end_at   — float, 기본 0.7
```

### v-pred 안전 파라미터

| 파라미터 | 값 | 이유 |
|---------|-----|------|
| weight | 0.5 | 0.7+ → DynamicThresholding과 충돌 → 흰 이미지 |
| weight_type | "linear" | v-pred와 가장 안정적 |
| start_at | 0.0 | 처음부터 적용 |
| end_at | 0.7 | 후반 30%는 모델 자체 디테일 처리 |

### 엣지 케이스

- `ip_adapter_image` placeholder 미치환 시 → LoadImage 노드 에러 → ComfyUI queue error 반환 → 백엔드 502
- 레퍼런스 이미지가 없는 캐릭터 → IP-Adapter 비활성화 (Re-routing)

### 테스트 전략

- `test_workflow_ip_adapter_nodes_exist`: scene_single.json에 12, 13, 14 노드 존재 확인
- `test_workflow_ip_adapter_chain`: 14_ip_apply → 9_sampler 연결 확인

---

## DoD 2: ComfyUI 클라이언트에서 IP-Adapter 변수 주입

### 구현 방법

**파일**: `backend/services/sd_client/comfyui/__init__.py`

`txt2img()` 메서드에 IP-Adapter 처리 추가:

```python
# 시그니처 변경 없음
async def txt2img(self, payload: dict, timeout: float | None = None) -> SDTxt2ImgResult:
```

**추가 로직 (inject_variables 전)**:

```python
ip_adapter = payload.pop("_ip_adapter", None)
if ip_adapter and ip_adapter.get("image_b64"):
    # 1. 레퍼런스 이미지 업로드
    filename = await self._upload_image(
        ip_adapter["image_b64"],
        f"ip_ref_{ip_adapter.get('name', 'char')}.png"
    )
    variables["ip_adapter_image"] = filename
    variables["ip_adapter_weight"] = ip_adapter.get("weight", 0.5)
    variables["ip_adapter_end_at"] = ip_adapter.get("end_at", 0.7)
else:
    # Link Re-routing: sampler를 dynthres에 직접 연결
    self._bypass_ip_adapter(workflow)
```

**새 메서드**:

```python
@staticmethod
def _bypass_ip_adapter(workflow: dict) -> None:
    """IP-Adapter 미사용 시 sampler model 연결을 dynthres로 우회."""
    sampler = workflow.get("9_sampler")
    if sampler and sampler["inputs"].get("model", [None])[0] == "14_ip_apply":
        sampler["inputs"]["model"] = ["5_dynthres", 0]
```

### 동작 정의

- **Before**: `payload["_ip_adapter"]` 존재 + `image_b64` 있음 → 이미지 업로드 + 변수 주입 → IP-Adapter 적용
- **Before**: `payload["_ip_adapter"]` 없음 또는 `image_b64` 없음 → `_bypass_ip_adapter()` → sampler가 dynthres 직결
- **After**: ComfyUI에 최종 워크플로우 전달 → IP-Adapter 노드 실행 또는 orphaned

### 엣지 케이스

- 이미지 업로드 실패 → IP-Adapter 비활성화 (bypass) + 경고 로그
- `_ip_adapter` 키는 있지만 `image_b64`가 빈 문자열 → bypass
- 기존 `_upload_image` 메서드 재사용 (3회 재시도 로직 포함)

### 영향 범위

- `_payload_to_variables`는 수정 없음 (ip_adapter 변수는 직접 variables에 추가)
- 기존 LoRA/checkpoint 처리와 독립적
- `_uploaded_poses` 캐시와 유사하게 `_uploaded_ip_refs` 캐시 추가 가능 (선택)

### 테스트 전략

- `test_txt2img_with_ip_adapter`: `_ip_adapter` payload 전달 시 variables에 ip_adapter_image 포함 확인
- `test_txt2img_without_ip_adapter`: `_ip_adapter` 없을 때 sampler model이 5_dynthres로 연결 확인
- `test_bypass_ip_adapter`: `_bypass_ip_adapter()` 단위 테스트
- `test_ip_adapter_upload_failure`: 업로드 실패 시 bypass 처리 확인

---

## DoD 3: generation_controlnet.py에서 ComfyUI 형식으로 변환

### 구현 방법

**파일**: `backend/services/generation_controlnet.py`

`_apply_ip_adapter()` 수정 — SD WebUI `alwayson_scripts` 형식 대신 `payload["_ip_adapter"]` dict 생성:

```python
def _apply_ip_adapter(ctx: GenerationContext, strategy: ConsistencyStrategy,
                      controlnet_args_list: list, db) -> None:
    if not strategy.ip_adapter_enabled or not strategy.ip_adapter_reference:
        return

    ref_image = _load_reference_image(strategy.ip_adapter_reference, db=db)
    if not ref_image:
        return

    # ComfyUI: payload에 _ip_adapter dict 추가 (alwayson_scripts 아닌)
    ctx._ip_adapter_payload = {
        "image_b64": ref_image,
        "name": strategy.ip_adapter_reference,
        "weight": strategy.ip_adapter_weight,
        "end_at": strategy.ip_adapter_guidance_end or 0.7,
    }
    ctx.ip_adapter_used = strategy.ip_adapter_reference
```

`apply_controlnet()` 수정 — 마지막에 `_ip_adapter` payload 주입:

```python
def apply_controlnet(payload: dict, ctx: GenerationContext, db) -> None:
    # ... 기존 로직 ...

    # ComfyUI: IP-Adapter payload 주입
    if hasattr(ctx, "_ip_adapter_payload") and ctx._ip_adapter_payload:
        payload["_ip_adapter"] = ctx._ip_adapter_payload
```

### 동작 정의

- **Before**: `alwayson_scripts.controlnet.args`에 IP-Adapter arg 추가 → ComfyUI에서 무시됨
- **After**: `payload["_ip_adapter"]`에 dict 추가 → ComfyUI 클라이언트가 노드 변수로 주입

### Reference Only 처리

- Reference Only는 IP-Adapter로 대체 (IP-Adapter가 상위 호환)
- `_apply_reference_only()` → `alwayson_scripts`에 추가하는 기존 코드 유지 (ComfyUI에서 무시됨, 제거는 별도 정리)
- IP-Adapter 비활성화 + Reference Only 활성화 → IP-Adapter의 style transfer 모드로 처리 (v2)

### 엣지 케이스

- 캐릭터에 레퍼런스 이미지 없음 → `_ip_adapter_payload` 미생성 → bypass
- 2P 모드 → `_apply_2p_pose`에서 early return, IP-Adapter 미적용 (현재와 동일)

### Out of Scope

- `alwayson_scripts` 기반 기존 코드 삭제 (별도 정리 태스크)
- Environment Reference (배경 IP-Adapter) — v2
- 2P + IP-Adapter 동시 적용 — v2

### 테스트 전략

- `test_apply_ip_adapter_creates_payload`: strategy.ip_adapter_enabled=True 시 payload["_ip_adapter"] 생성 확인
- `test_apply_ip_adapter_disabled`: strategy.ip_adapter_enabled=False 시 payload에 _ip_adapter 없음 확인
- `test_apply_controlnet_injects_ip_adapter`: apply_controlnet 호출 후 payload에 _ip_adapter 존재 확인

---

## DoD 4: scene_2p.json에도 동일 적용

### 구현 방법

`scene_2p.json`에 동일한 3개 노드 (12_ip_loader, 13_ip_image, 14_ip_apply) 추가.

**차이점**: 2P에서는 ControlNet Pose가 conditioning을 수정하고, IP-Adapter는 model을 수정하므로 충돌 없이 병렬 적용 가능.

```
5_dynthres → 12_ip_loader → 14_ip_apply → 9_sampler
                              ↑                ↑
                         13_ip_image      7_cn_apply (ControlNet Pose)
```

`_bypass_ip_adapter()`는 `9_sampler` 노드의 `model` 입력만 변경하므로 scene_2p에도 동일하게 동작.

### 테스트 전략

- `test_scene_2p_ip_adapter_nodes`: scene_2p.json에 12, 13, 14 노드 존재 확인

---

## DoD 5: 통합 테스트

### 테스트 전략

| 테스트 | 입력 | 기대 결과 |
|--------|------|----------|
| IP-Adapter ON | `_ip_adapter={image_b64, weight=0.5}` | 이미지 업로드됨, variables에 ip_adapter_image 포함, sampler→14_ip_apply 연결 |
| IP-Adapter OFF | `_ip_adapter` 없음 | sampler→5_dynthres 연결 (bypass), CLIP Vision 미로드 |
| 업로드 실패 | `_upload_image` raise | bypass + 경고 로그, 정상 이미지 생성 |
| weight 범위 | weight=1.5 (과도) | clamp 0.0~1.0 적용 |
| 기존 테스트 | 전체 test suite | 모두 통과 |

---

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `services/sd_client/comfyui/workflows/scene_single.json` | IP-Adapter 노드 3개 추가, sampler 연결 변경 |
| `services/sd_client/comfyui/workflows/scene_2p.json` | IP-Adapter 노드 3개 추가, sampler 연결 변경 |
| `services/sd_client/comfyui/__init__.py` | `txt2img()` IP-Adapter 처리, `_bypass_ip_adapter()` 추가 |
| `services/generation_controlnet.py` | `_apply_ip_adapter()` ComfyUI 형식 변환, `apply_controlnet()` payload 주입 |
| `tests/test_comfy_client.py` | IP-Adapter bypass/주입 테스트 추가 |
| `tests/test_generation_controlnet.py` | IP-Adapter payload 생성 테스트 추가 |

---

## 설계 리뷰 결과 (난이도: 중 — Gemini 2라운드)

### Gemini 자문 (2라운드, Score 9/10)
- R1: Fat Template + Pruning 제안 → VRAM 오버헤드 문제로 재검토
- R2: Link Re-routing 최종 합의 — ComfyUI 역추적 실행 엔진 활용, 노드 삭제 불필요

### 핵심 합의 사항
- weight=0 bypass 불가 (CLIP Vision 로드됨) → Link Re-routing 필수
- Reference Only → IP-Adapter로 통합 (v2에서 style transfer 모드)
- v-pred 안전 기본값: weight 0.5, end_at 0.7, weight_type linear
