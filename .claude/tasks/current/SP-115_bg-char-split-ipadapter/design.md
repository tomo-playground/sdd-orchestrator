# SP-115 상세 설계: 배경/캐릭터 분리 IP-Adapter 파이프라인

## 아키텍처 결정

**듀얼 IP-Adapter 체이닝 + attn_mask** 방식 채택.

배경 IP-Adapter와 캐릭터 IP-Adapter를 체이닝하되, 각각 attn_mask로 영역을 분리.
같은 IPAdapterModelLoader/CLIPVisionLoader 노드를 공유하여 VRAM 절약.

```
5_dynthres → 15_bg_ip_apply (배경 마스크) → 14_ip_apply (인물 마스크) → 9_sampler
                ↑                                    ↑
          16_bg_ref_image                      13_ip_image
          15b_bg_mask                          13b_char_mask
```

### bypass 시나리오 (Static Graph + weight=0)

**Link Re-routing 폐기** — 체인 구조를 고정하고, bypass 대상의 weight를 0.0으로 주입.
weight=0인 IPAdapterAdvanced는 pass-through로 동작 (모델 변조 없이 그대로 통과).
복잡한 JSON link 조작 로직이 완전히 사라진다.

| 시나리오 | char_weight | bg_weight | 체인 |
|---------|------------|-----------|------|
| 둘 다 활성 | 0.6 | 0.3 | dynthres → bg(0.3) → char(0.6) → sampler |
| 캐릭터만 | 0.6 | **0.0** | dynthres → bg(pass) → char(0.6) → sampler |
| 배경만 | **0.0** | 0.3 | dynthres → bg(0.3) → char(pass) → sampler |
| 둘 다 비활성 | **0.0** | **0.0** | dynthres → bg(pass) → char(pass) → sampler |

**기존 `_bypass_ip_adapter()` 삭제** — weight=0 주입으로 완전 대체.

---

## DoD 1: scene_single.json 워크플로우 변경

### 구현 방법

기존 IP-Adapter 노드(12_ip_model, 12b_clip_vision, 13_ip_image, 14_ip_apply)를 유지하고, 배경 전용 노드 4개 추가:

```json
"15_bg_ref_image": {
  "class_type": "LoadImage",
  "inputs": { "image": "{{bg_ref_image}}" }
},
"15b_bg_mask_image": {
  "class_type": "LoadImage",
  "inputs": { "image": "{{bg_mask}}" }
},
"15c_bg_mask": {
  "class_type": "ImageToMask",
  "inputs": { "image": ["15b_bg_mask_image", 0], "channel": "red" }
},
"15_bg_ip_apply": {
  "class_type": "IPAdapterAdvanced",
  "inputs": {
    "model": ["5_dynthres", 0],
    "ipadapter": ["12_ip_model", 0],
    "clip_vision": ["12b_clip_vision", 0],
    "image": ["15_bg_ref_image", 0],
    "attn_mask": ["15c_bg_mask", 0],
    "weight": "{{bg_ip_adapter_weight}}",
    "weight_type": "linear",
    "start_at": 0.0,
    "end_at": "{{bg_ip_adapter_end_at}}",
    "combine_embeds": "concat",
    "embeds_scaling": "V only"
  }
}
```

기존 `14_ip_apply` 변경:
- `model`: `["5_dynthres", 0]` → `["15_bg_ip_apply", 0]` (체이닝)
- `attn_mask`: 추가 — `["13b_char_mask", 0]`

캐릭터 마스크 노드 추가:
```json
"13b_char_mask_image": {
  "class_type": "LoadImage",
  "inputs": { "image": "{{char_mask}}" }
},
"13b_char_mask": {
  "class_type": "ImageToMask",
  "inputs": { "image": ["13b_char_mask_image", 0], "channel": "red" }
}
```

variables 배열에 추가: `bg_ref_image`, `bg_mask`, `char_mask`, `bg_ip_adapter_weight`, `bg_ip_adapter_end_at`

### 테스트 전략

- `test_workflow_bg_ip_adapter_nodes_exist`: 15_bg_ip_apply 등 노드 존재 확인
- `test_workflow_bg_char_chain`: 15_bg_ip_apply → 14_ip_apply → 9_sampler 체인 확인
- `test_workflow_attn_mask_connected`: 14_ip_apply에 attn_mask 입력 확인

---

## DoD 2: ComfyUI 클라이언트 변경

### 구현 방법

**파일**: `backend/services/sd_client/comfyui/__init__.py`

`txt2img()` 메서드 변경:

```python
ip_adapter = payload.get("_ip_adapter")
payload.pop("_ip_adapter", None)

# 배경 IP-Adapter
bg_ref = ip_adapter.get("bg_image_b64") if ip_adapter else None
# 캐릭터 IP-Adapter
char_ref = ip_adapter.get("image_b64") if ip_adapter else None

if char_ref:
    # 캐릭터 레퍼런스 업로드 + 변수 주입 (기존 로직)
    ...
    # 캐릭터 마스크 업로드
    char_mask_b64 = self._generate_character_mask(payload.get("width", 832), payload.get("height", 1216))
    char_mask_filename = await self._upload_image(char_mask_b64, "mask_character.png")
    variables["char_mask"] = char_mask_filename
else:
    self._bypass_char_ip_adapter(workflow, has_bg=bool(bg_ref))

if bg_ref:
    # 배경 레퍼런스 업로드 + 변수 주입
    bg_filename = await self._upload_image(bg_ref, f"bg_ref_{bg_hash}.png")
    variables["bg_ref_image"] = bg_filename
    variables["bg_ip_adapter_weight"] = min(float(ip_adapter.get("bg_weight", 0.3)), 0.3)
    variables["bg_ip_adapter_end_at"] = min(float(ip_adapter.get("bg_end_at", 0.7)), 0.7)
    # 배경 마스크 업로드
    bg_mask_b64 = self._generate_background_mask(payload.get("width", 832), payload.get("height", 1216))
    bg_mask_filename = await self._upload_image(bg_mask_b64, "mask_background.png")
    variables["bg_mask"] = bg_mask_filename
else:
    self._bypass_bg_ip_adapter(workflow, has_char=bool(char_ref))
```

**새 메서드**:

```python
@staticmethod
def _generate_character_mask(width: int, height: int) -> str:
    """인물 영역 타원 마스크 생성 (base64). 중앙 타원 + feather."""

@staticmethod
def _generate_background_mask(width: int, height: int) -> str:
    """배경 영역 마스크 생성 (인물 마스크 반전)."""
```

### bypass 로직 (weight=0 방식)

**기존 `_bypass_ip_adapter()` 삭제**. Link Re-routing 불필요.

weight=0으로 bypass:
```python
# 캐릭터 IP-Adapter 없으면 weight=0
if not char_ref:
    variables["ip_adapter_weight"] = 0.0
    variables["ip_adapter_end_at"] = 0.0

# 배경 IP-Adapter 없으면 weight=0
if not bg_ref:
    variables["bg_ip_adapter_weight"] = 0.0
    variables["bg_ip_adapter_end_at"] = 0.0
```

마스크/레퍼런스 이미지 변수는 placeholder로 채움 (노드 validation 통과용).

### 마스크 캐싱

마스크는 해상도별로 고정이므로, `_mask_cache: dict[tuple[int,int], tuple[str,str]]`로 캐시.
초기 구현은 b64 업로드 방식, 고정 타원 확정 후 ComfyUI input 상주 방식으로 전환 가능.

### 테스트 전략

- `test_txt2img_with_bg_and_char`: 둘 다 활성 → 변수에 양쪽 weight/image 주입 확인
- `test_txt2img_char_only`: 캐릭터만 → bg_weight=0.0 주입 확인
- `test_txt2img_bg_only`: 배경만 → ip_adapter_weight=0.0 주입 확인
- `test_txt2img_no_ip_adapter`: 둘 다 없음 → 양쪽 weight=0.0
- `test_mask_generation`: 832x1216 → 인물 타원 + 배경 반전 마스크 생성 확인
- `test_mask_caching`: 동일 해상도 2회 호출 → 캐시 히트

---

## DoD 3: generation_controlnet.py 변경

### 구현 방법

**파일**: `backend/services/generation_controlnet.py`

`_apply_ip_adapter()` 수정 — 배경 레퍼런스도 payload에 포함:

```python
def _apply_ip_adapter(ctx, strategy, args, db):
    # 기존: 캐릭터 레퍼런스 로드 + ctx._ip_adapter_payload 빌드
    ...
    ctx._ip_adapter_payload = {
        "image_b64": ref_image,
        "name": strategy.ip_adapter_reference,
        "weight": effective_weight,
        "end_at": end_at,
    }

    # SP-115 신규: 배경 레퍼런스 추가
    bg_image_b64 = _load_bg_reference(ctx.request, db)
    if bg_image_b64:
        ctx._ip_adapter_payload["bg_image_b64"] = bg_image_b64
        ctx._ip_adapter_payload["bg_weight"] = DEFAULT_BG_IP_ADAPTER_WEIGHT
        ctx._ip_adapter_payload["bg_end_at"] = DEFAULT_BG_IP_ADAPTER_END_AT
```

**새 함수**:

```python
def _load_bg_reference(req: SceneGenerateRequest, db) -> str | None:
    """배경 레퍼런스 이미지 로드 (environment_reference_id → MediaAsset → base64)."""
    if not req.environment_reference_id:
        return None
    from models.media_asset import MediaAsset
    asset = db.query(MediaAsset).filter(MediaAsset.id == req.environment_reference_id).first()
    if not asset:
        return None
    return _load_asset_as_b64(asset)
```

### 캐릭터 없이 배경만 있는 경우

`_apply_ip_adapter()`가 캐릭터 IP-Adapter 비활성이면 return하지만, 배경은 독립적으로 활성화 가능해야 한다. `apply_controlnet()` 마지막에 배경 전용 처리 추가:

```python
def apply_controlnet(payload, ctx, db):
    ...
    # 기존: 캐릭터 IP-Adapter
    if ctx._ip_adapter_payload:
        payload["_ip_adapter"] = ctx._ip_adapter_payload

    # SP-115: 캐릭터 IP-Adapter 없어도 배경만 적용 가능
    elif not ctx._ip_adapter_payload:
        bg_b64 = _load_bg_reference(ctx.request, db)
        if bg_b64:
            payload["_ip_adapter"] = {
                "bg_image_b64": bg_b64,
                "bg_weight": DEFAULT_BG_IP_ADAPTER_WEIGHT,
                "bg_end_at": DEFAULT_BG_IP_ADAPTER_END_AT,
            }
```

### 테스트 전략

- `test_ip_adapter_with_bg_reference`: environment_reference_id 있을 때 bg_image_b64 포함 확인
- `test_ip_adapter_without_bg`: environment_reference_id 없으면 bg 키 없음
- `test_bg_only_no_char`: 캐릭터 IP-Adapter 없이 배경만 있을 때 payload 생성

---

## DoD 4: 배경 레퍼런스 소스

### 결정

**`environment_reference_id` (MediaAsset) 재활용**.

기존 `_apply_environment()` (AdaIN 방식)와 독립적. config에 `BG_IP_ADAPTER_ENABLED` 플래그 추가.

### config.py 추가

```python
BG_IP_ADAPTER_ENABLED = True  # 배경 IP-Adapter (environment_reference_id 사용)
DEFAULT_BG_IP_ADAPTER_WEIGHT = 0.3
DEFAULT_BG_IP_ADAPTER_END_AT = 0.7
```

### Out of Scope

- `ENVIRONMENT_REFERENCE_ENABLED` (기존 AdaIN)과의 상호작용 정리는 별도 태스크
- 이전 씬 이미지 자동 참조 (Option B)
- Group 레벨 배경 설정 (Option C)

---

## DoD 5: 테스트

### 테스트 목록

| 테스트 | 입력 | 기대 결과 |
|--------|------|----------|
| 배경+캐릭터 활성 | char_b64 + bg_b64 | 워크플로우에 두 IP-Adapter 체인, 각각 마스크 적용 |
| 캐릭터만 활성 | char_b64, bg 없음 | bg bypass, char에 attn_mask 적용 |
| 배경만 활성 | bg_b64, char 없음 | char bypass, bg에 attn_mask 적용 |
| 둘 다 비활성 | 없음 | sampler→dynthres (기존) |
| 마스크 생성 | width=832, height=1216 | 인물: 중앙 타원, 배경: 반전 |
| 기존 테스트 | 전체 suite | 모두 통과 |

---

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `workflows/scene_single.json` | 배경 IP-Adapter 4노드 추가, 캐릭터 마스크 2노드 추가, 체이닝 변경 |
| `workflows/scene_2p.json` | 동일 변경 |
| `sd_client/comfyui/__init__.py` | 배경 처리, 마스크 생성/업로드, bypass 분리, 마스크 캐싱 |
| `generation_controlnet.py` | _load_bg_reference(), 배경 payload 주입 |
| `config.py` | BG_IP_ADAPTER_ENABLED, DEFAULT_BG_IP_ADAPTER_WEIGHT/END_AT |
| `tests/test_comfy_client.py` | 배경 IP-Adapter 관련 테스트 추가 |
| `tests/test_generation_controlnet.py` | 배경 레퍼런스 테스트 추가 |

---

## 설계 리뷰 결과 (난이도: 중 — Gemini 2라운드, Score 8/10)

### Gemini 자문 (2라운드, 1라운드에서 합의)

- R1: **Link Re-routing 폐기, weight=0 bypass 채택** — 경우의 수가 늘어도 체인 구조 고정, 코드 복잡도 대폭 감소 → **반영 완료**
- R1: ip_model/clip_vision 노드 공유 — ComfyUI 내부 캐싱으로 충돌 없음, VRAM 절약 → **확인**
- R1: 마스크 상주 vs 업로드 — 초기 b64 업로드, 확정 후 상주 전환 2단계 전략 → **채택**
- R2: 합의 확인 (추가 피드백 없음)

### 핵심 변경사항 (Gemini 반영)

1. `_bypass_ip_adapter()` 메서드 **삭제** → weight=0 주입으로 완전 대체
2. 워크플로우 체인 **고정** (Static Graph) — sampler는 항상 `14_ip_apply` 참조
3. 마스크 초기 구현은 b64 업로드, 캐싱 적용
