# SP-023 상세 설계: 2P ControlNet Pose + BREAK 파이프라인

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `services/sd_client/comfyui/workflows/scene_2p.json` | **신규** | 2P 워크플로우 (ControlNet Pose + BREAK) |
| `services/sd_client/comfyui/__init__.py` | 수정 | pose 이미지 업로드 (캐시) + 워크플로우 변수 주입 |
| `services/generation.py` | 수정 | 2P 자동 감지 → workflow 선택 |
| `services/generation_controlnet.py` | 수정 | multi-char 스킵 → 2P pose 적용 |
| `services/controlnet.py` | 수정 | 2P pose 매핑 + 로딩 |
| `config.py` | 수정 | 2P 상수 추가 |

---

## B-1. `scene_2p.json` ComfyUI 워크플로우

### 구현 방법
`scene_single.json`을 확장. ControlNet 3노드 추가 (ControlNetLoader → LoadImage → ControlNetApply).

**노드 그래프:**
```
1_checkpoint → 2_lora_style → 3_lora_char → 4_lora_extra → 5_dynthres
                                                              ↓ (model)
                                                          9_sampler
                                                              ↑
                                        7_cn_apply (positive) ↑
                                           ↑         ↑       ↑
                                    6_positive  5a_cn_loader   ↑
                                                5b_cn_image    ↑
                                                          7_negative
                                                          8_latent
                                                              ↓
                                                          10_decode → 11_save
```

**추가 변수:**
- `{{pose_image}}` — ComfyUI input 폴더의 파일명 (캐시된 정적 파일)
- `{{controlnet_strength}}` — ControlNet 강도 (기본 0.7)

**DynamicThresholding 파라미터** (PoC 검증 완료, 2P+ControlNet 최적화):
- `mimic_scale`: 5.0, `mimic_scale_min`: 3.0
- `scaling_startpoint`: "MEAN", `variability_measure`: "AD"
- scene_single과 다름 — 하드코딩 유지 (ControlNet + BREAK 조합 전용)

### 동작 정의
- before: 2P 씬 → `scene_single.json` 사용, ControlNet 무시됨
- after: 2P 씬 → `scene_2p.json` 사용, pose 이미지로 위치 제어

### 엣지 케이스
- pose 이미지 없이 `scene_2p` 호출 → `{{pose_image}}` 미치환 → 워크플로우 경고 로그
- LoRA 3슬롯 부족 시 → 기존 bypass 로직 그대로 적용

### 테스트 전략
- `scene_2p.json` 로드 → 필수 노드 존재 확인 (ControlNetLoader, LoadImage, ControlNetApply)
- `inject_variables` → `{{pose_image}}`, `{{controlnet_strength}}` 치환 확인

### Out of Scope
- `scene_single.json` 수정 금지
- DynamicThresholding 파라미터를 변수화하지 않음 (2P 전용 고정값)

---

## B-2. ComfyUI client 포즈 이미지 업로드 (캐시 방식)

### 구현 방법
정적 포즈 6종 → 최초 1회 업로드 + 인메모리 캐시. 매 생성마다 재업로드하지 않음.

**신규 메서드:**
```python
async def _upload_image(self, image_b64: str, filename: str) -> str:
    """base64 이미지를 ComfyUI /upload/image로 전송. 업로드된 파일명 반환.
    총 3회 시도 (초기 1 + retry 2, delays: 1s, 2s). ConnectError는 즉시 전파."""

async def _ensure_pose_uploaded(self, pose_name: str, pose_b64: str) -> str:
    """포즈 이미지 캐시 확인 → 미업로드 시 1회 업로드. 캐시된 파일명 반환."""
```

**인메모리 캐시 (인스턴스 변수):**
```python
class ComfyUIClient:
    def __init__(self, ...):
        ...
        self._uploaded_poses: dict[str, str] = {}  # pose_name → comfy_filename
```

**`txt2img` 수정:**
```python
# pop(): base64 대용량 데이터 제거 목적 (_comfy_workflow는 작은 문자열이므로 get 유지)
pose_b64 = payload.pop("_pose_image_b64", None)
pose_name = payload.pop("_pose_name", None)
if pose_b64 and pose_name:
    filename = await self._ensure_pose_uploaded(pose_name, pose_b64)
    variables["pose_image"] = filename
    variables["controlnet_strength"] = payload.pop("_controlnet_strength", 0.7)
```

### 동작 정의
- 첫 요청: `/upload/image` API 호출 (3회 재시도) → `2p_{pose_name}.png` 저장 → 캐시
- 이후 요청: 캐시 hit → 업로드 스킵, 파일명만 반환
- ComfyUI 재시작: 파일은 input 폴더에 유지, 캐시만 재구축 필요 (업로드 시 overwrite=true)

### 엣지 케이스
- ComfyUI 다운 (`ConnectError`) → 재시도 없이 즉시 실패 (기존 `queue_prompt` 패턴 동일)
- ComfyUI 일시 오류 (5xx 등) → 총 3회 시도 (초기 1 + retry 2, delays: 1s, 2s)
- 동시 요청 시 같은 pose → 중복 업로드 발생 (idempotent, 동일 파일명 → 무해)
- ComfyUI input 폴더 소실 (Docker volume 미마운트 등) → `txt2img` 실패 시 무조건 `_uploaded_poses.pop(pose_name)` (단순성 우선, 불필요 재업로드 허용) → 다음 요청에서 자동 재업로드
- 앱 서버 재시작 → 캐시 초기화 → 첫 요청에서 자동 재업로드

### 영향 범위
- 기존 `scene_single` 경로: `_pose_image_b64` 없으므로 변경 없음

### 테스트 전략
- `_ensure_pose_uploaded` 2회 호출 → `_upload_image` 1회만 호출 확인 (캐시)
- `_pose_image_b64` 없는 payload → 기존 동작 변경 없음 확인

### Out of Scope
- ComfyUI input 폴더 자동 정리 (ComfyUI 자체 관리)
- 동적 포즈 생성 (런타임 DWPose)

---

## B-3. DWPose 2P 포즈 라이브러리

### 구현 방법
기존 1P 포즈 패턴(`POSE_MAPPING` + `shared/poses/`) 동일 구조.

**`controlnet.py` 추가:**
```python
POSE_2P_MAPPING: dict[str, str] = {
    "walking_together": "2p_walking_together.png",
    "standing_side_by_side": "2p_standing_side_by_side.png",
    "facing_each_other": "2p_facing_each_other.png",
    "sitting_together": "2p_sitting_together.png",
    "hand_holding": "2p_hand_holding.png",
    "back_to_back": "2p_back_to_back.png",
}

def load_2p_pose_reference(pose_name: str) -> str | None:
    """2P 포즈 이미지 로드. shared/poses/2p/{filename} 경로."""
```

**`config.py` 추가:**
```python
CONTROLNET_2P_STRENGTH: float = 0.7
CONTROLNET_2P_DEFAULT_POSE: str = "standing_side_by_side"
```

### 동작 정의
- before: 2P 포즈 에셋 없음, ControlNet 사용 불가
- after: 6종 2P 포즈 에셋 + 매핑 테이블로 자동 선택

### 엣지 케이스
- 에셋 파일 미존재 → `None` 반환 → ControlNet 미적용 + 경고
- 1P 포즈 이름으로 2P 함수 호출 → 매핑 miss → `None` (1P/2P 매핑 분리)

### 테스트 전략
- `POSE_2P_MAPPING` 키 전체 → `load_2p_pose_reference` 호출 → storage mock 검증
- 존재하지 않는 키 → `None` 반환

### Out of Scope
- 포즈 에셋 자체 생성 (수동 큐레이션 → sync_poses 스크립트로 업로드)
- 런타임 DWPose 추출

---

## C-1. `generation.py` 2P 자동 감지

### 구현 방법
`_build_payload` 내 `_comfy_workflow` 결정 로직 수정.

```python
# before
"_comfy_workflow": req.comfy_workflow or "scene_single",

# after
"_comfy_workflow": req.comfy_workflow or ("scene_2p" if req.character_b_id else "scene_single"),
```

### 동작 정의
- `character_b_id` 있음 → `scene_2p` 워크플로우 자동 선택
- `comfy_workflow` 명시 → 명시값 우선 (기존과 동일)
- `character_b_id` 없음 → `scene_single` (기존과 동일)

### 엣지 케이스
- `comfy_workflow="scene_single"` + `character_b_id` → 명시값 우선 (사용자 오버라이드 존중)

### 테스트 전략
- `character_b_id=123` → payload `_comfy_workflow == "scene_2p"` 확인
- `character_b_id=None` → `"scene_single"` 확인
- `comfy_workflow="custom"` + `character_b_id=123` → `"custom"` 확인

### Out of Scope
- Frontend에서 `comfy_workflow` UI 노출

---

## C-2. `generation_controlnet.py` 2P Pose 적용

### 구현 방법
`apply_controlnet`의 multi-char 조기 리턴을 2P 전용 분기로 교체.

```python
def apply_controlnet(payload, ctx, db):
    req = ctx.request
    if getattr(ctx, "character_b_id", None):
        _apply_2p_pose(req, ctx, payload, db)
        return  # 2P: pose만 적용, reference/environment/ip-adapter 스킵
    # ... 기존 1P 로직 그대로
```

**신규 함수:**
```python
def _apply_2p_pose(req, ctx, payload, db) -> None:
    """2P씬 전용 ControlNet Pose 적용. payload에 _pose_image_b64, _pose_name, _controlnet_strength 설정."""
```

**포즈 자동 선택 우선순위:**
1. `req.controlnet_pose` 명시 → `POSE_2P_MAPPING`에서 조회
2. scene_id → `SceneCharacterAction` → 2P 포즈 힌트
3. prompt 키워드 → `detect_2p_pose_from_prompt()`
4. 기본값: `CONTROLNET_2P_DEFAULT_POSE`

### 동작 정의
- before: `character_b_id` → ControlNet 전체 스킵, 로그만
- after: `character_b_id` → 2P 포즈 선택 → payload에 pose 데이터 설정 → ComfyUI workflow가 처리

### 엣지 케이스
- 포즈 에셋 없음 → 경고 로그 + ControlNet 미적용 (pose_image 변수 미주입 → 워크플로우 경고)
- 1P 포즈 이름 전달 → `POSE_2P_MAPPING` miss → 기본값 fallback

### 영향 범위
- 기존 1P 경로: `character_b_id` 없으면 기존 로직 그대로 → regression 없음
- `alwayson_scripts` 사용하지 않음 (ComfyUI 워크플로우 노드 방식)

### 테스트 전략
- `character_b_id` 있음 → `_apply_2p_pose` 호출 확인 + payload에 `_pose_image_b64` 존재
- `character_b_id` 없음 → 기존 `_apply_pose_control` 등 호출 (regression)
- 포즈 에셋 없음 → payload에 `_pose_image_b64` 없음 + 경고 로그

### Out of Scope
- 2P에서 IP-Adapter / Reference-Only / Environment 적용 (향후 태스크)

---

## C-3. `comfyui/__init__.py` pose 처리 통합

B-2와 동일 범위. `txt2img` 내에서 `_pose_image_b64` 감지 → `_ensure_pose_uploaded` → 변수 주입.
별도 설계 불필요 (B-2 참조).

---

## C-4/C-5. 검증

### C-4. 일관성 수동 검증
- 동일 2P 캐릭터 5씬 생성 (seed 고정)
- 기준: 4/5 이상에서 캐릭터 구분 + 위치 고정
- 자동화 불가 — 수동 육안 확인

### C-5. 1P Regression
- 기존 1P 생성 테스트 전체 통과
- `scene_single.json` 미수정 확인
- `character_b_id=None` 경로 변경 없음 확인

---

## 호출 흐름도 (2P 씬)

```
SceneGenerateRequest (character_b_id=123)
  ↓
_prepare_prompt → MultiCharacterComposer.compose()
  → quality, subject, scene BREAK charA BREAK charB
  → _enforce_wide_framing (이미 존재)
  ↓
_build_payload
  → _comfy_workflow = "scene_2p"              ← C-1
  ↓
apply_controlnet
  → _apply_2p_pose(req, ctx, payload, db)     ← C-2
  → 포즈 선택 → load_2p_pose_reference()     ← B-3
  → payload["_pose_image_b64"] = base64
  → payload["_pose_name"] = "walking_together"
  → payload["_controlnet_strength"] = 0.7
  ↓
ComfyUIClient.txt2img(payload)
  → _ensure_pose_uploaded(name, b64) → filename  ← B-2 (캐시)
  → variables["pose_image"] = filename
  → load_workflow("scene_2p")                     ← B-1
  → inject_variables(workflow, variables)
  → run_workflow → image
```

---

## Gemini 자문 결과 (2라운드, 합의 8/10)

반영된 피드백:
- **R1**: 매 요청 업로드 → 인메모리 캐시 + 1회 업로드로 변경 (성능 + 동시성 해결)
- **R2**: 파일명 충돌 → 정적 파일명 `2p_{pose_name}.png` + idempotent 업로드
- 참고: DynamicThresholding 파라미터 중앙화는 현재 스코프 외 (2개 워크플로우만 존재, 향후 검토)
