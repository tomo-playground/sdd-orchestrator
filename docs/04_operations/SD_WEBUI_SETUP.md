# SD WebUI 구축 매뉴얼

Shorts Producer 이미지 생성을 위한 Stable Diffusion WebUI 설정 가이드.
다른 환경에서 재설치 시 이 문서를 기준으로 구성합니다.

---

## 1. SD WebUI 설치

### 1.1 설치

```bash
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui

# 첫 실행 시 의존성 자동 설치
./webui.sh --api --listen
```

**필수 실행 옵션:**

| 옵션 | 설명 |
|------|------|
| `--api` | REST API 활성화 (Backend 연동 필수) |
| `--listen` | 외부 IP 접근 허용 (분리 PC 구성 시) |
| `--medvram` | VRAM 8GB 이하 권장 |
| `--xformers` | 속도 최적화 (설치된 경우) |

### 1.2 체크포인트 모델

**설치 경로:** `models/Stable-diffusion/`

| 파일명 | 용도 | 비고 |
|--------|------|------|
| `anyloraCheckpoint_bakedvaeBlessedFp16.safetensors` | 애니메이션 전용 ← **주력** | 플랫/신카이/지브리/그림책 화풍 |
| `realisticVisionV60B1_v51HyperVAE.safetensors` | 실사 전용 | 실화 탐구 시리즈 |

> **StyleProfile → 체크포인트 매핑** (`backend/config.py` 참조)
> - Flat Color Anime / Makoto Shinkai / Studio Ghibli / Children Picture Book → `anyloraCheckpoint`
> - Realistic → `realisticVisionV60B1`

---

## 2. ControlNet 확장

### 2.1 설치

1. SD WebUI → **Extensions** → Install from URL
2. URL: `https://github.com/Mikubill/sd-webui-controlnet.git`
3. Install → Restart UI

### 2.2 ControlNet 모델

**다운로드:** https://huggingface.co/lllyasviel/ControlNet-v1-1/tree/main

**설치 경로:** `extensions/sd-webui-controlnet/models/`

| 파일명 | 모듈 | 용도 |
|--------|------|------|
| `control_v11p_sd15_openpose.pth` | `openpose_full` | 포즈 스켈레톤 제어 ← **필수** |
| `control_v11f1p_sd15_depth.pth` | `depth_midas` | 깊이 제어 (선택) |

> **주의:** `openpose_full` 모듈 사용 시 손/얼굴 스켈레톤도 인식됨. `openpose`(기본)보다 더 정밀.

### 2.3 ControlNet 동작 정책 (Phase 30-N 이후)

| 포즈 분류 | ControlNet | 이유 |
|-----------|-----------|------|
| `standing`, `walking`, `running` 등 직립 포즈 | **ON** (weight 0.60~0.80) | 골격 정밀도 중요 |
| `sitting`, `chin_rest`, `seiza` 등 앉기 계열 | **OFF** | 하체 스켈레톤 왜곡 문제 |
| action 포즈 (`jumping`, `pointing`) | ON (weight 0.80) | 동작 정밀도 우선 |
| 감성/서정 mood 씬 | ON (weight 0.45) | SD 자유 구성 허용 |

> 자동 할당 로직: `backend/services/agent/nodes/finalize.py` `_resolve_controlnet_weight()`

---

## 3. IP-Adapter (캐릭터 얼굴 일관성)

### 3.1 모델 다운로드

**다운로드:** https://huggingface.co/h94/IP-Adapter/tree/main/models

**설치 경로:** `extensions/sd-webui-controlnet/models/`

| 파일명 | 용도 | 비고 |
|--------|------|------|
| `ip-adapter-plus-face_sd15.safetensors` | 얼굴 + 스타일 ← **현재 사용** | 애니 캐릭터 최적 |
| `ip-adapter-plus_sd15.safetensors` | 전체 스타일 전이 | 참고용 |
| `ip-adapter-faceid-plusv2_sd15.safetensors` | 실사 얼굴 전용 | FaceID 필요 |

**현재 적용 weight:** `0.50` (씬 생성), `0.40` (레퍼런스 생성)
→ `backend/config.py` `DEFAULT_IP_ADAPTER_WEIGHT`, `REFERENCE_LORA_SCALE` 참조

### 3.2 CLIP Vision 모델 (필수)

**다운로드:** https://huggingface.co/h94/IP-Adapter/tree/main/models/image_encoder

- `model.safetensors` 다운로드 → **`clip_vision_g.safetensors`** 으로 이름 변경
- **설치 경로:** `extensions/sd-webui-controlnet/models/`

### 3.3 FaceID LoRA (선택)

실사 얼굴 일관성 강화 시:
```bash
pip install insightface onnxruntime
```
- `ip-adapter-faceid-plusv2_sd15_lora.safetensors` → `models/Lora/`
- buffalo_l 모델: https://github.com/deepinsight/insightface/releases → `~/.insightface/models/buffalo_l/`

> **현재 프로젝트:** 애니메이션 캐릭터 위주이므로 FaceID 미사용. CLIP 모델만 설치.

---

## 4. Negative Embeddings

**설치 경로:** `embeddings/`

| 파일명 | 다운로드 | 용도 |
|--------|---------|------|
| `EasyNegative.safetensors` | Civitai | 일반 품질 개선 |
| `verybadimagenegative_v1.3.pt` | Civitai | 저품질 방지 |
| `(painting by bad-artist).pt` | Civitai | 아티스트 스타일 억제 |

> DB에 등록된 6개 임베딩이 전 StyleProfile 네거티브에 자동 적용됨.
> 파일명이 정확히 일치해야 SD가 인식함.

---

## 5. LoRA 모델

**설치 경로:** `models/Lora/`

### 5.1 Style LoRA (StyleProfile 연동, 필수)

| 파일명 | StyleProfile | weight | Trigger |
|--------|-------------|--------|---------|
| `flat_color.safetensors` | Flat Color Anime | 0.40 | `flat color` |
| `ghibli_style_offset.safetensors` | Studio Ghibli | 0.70 | `ghibli style` |
| `makoto_shinkai_(your_name_+_substyles)_style_lora.safetensors` | Makoto Shinkai | 1.00 | `shinkai makoto` |
| `J_huiben.safetensors` | Children Picture Book | 0.80 | `J_huiben` |

### 5.2 Detail LoRA (전 StyleProfile 보조)

| 파일명 | weight | 역할 |
|--------|--------|------|
| `add_detail.safetensors` | 0.25~0.40 | 디테일 강화 (프로필별 상이) |

### 5.3 Character LoRA (캐릭터별, 선택)

| 파일명 | 캐릭터 | 씬 weight | 레퍼런스 weight | Trigger |
|--------|--------|-----------|---------------|---------|
| `Usagi_Drop_-_Nitani_Yukari.safetensors` | 유카리 (id:19) | 0.32 | 0.28 | `udyukari` |
| `mha_midoriya-10.safetensors` | 미도리 (id:3) | 0.70 | 0.40 | `Midoriya_Izuku` |

> weight가 낮은 이유: Character LoRA weight가 높으면 의상 색상 태그를 무시하는 문제 발생
> 상세: `docs/03_engineering/backend/LORA_SELECTION_GUIDE.md`

### 5.4 미사용 LoRA (DB 등록됨, 파일만 있으면 됨)

`blindbox_v1_mix`, `chibi-laugh`, `Gentle_Cubism_Light`, `harukaze-doremi-casual`, `eureka_v9`

---

## 6. Backend 연동

### 6.1 환경 변수

`backend/.env`:
```bash
SD_BASE_URL=http://127.0.0.1:7860   # 로컬 동일 PC
# SD_BASE_URL=http://192.168.x.x:7860  # 별도 PC
```

### 6.2 SD WebUI 실행 명령 (권장)

```bash
# 기본 (로컬, VRAM 여유)
./webui.sh --api

# 별도 PC에서 접근 허용
./webui.sh --api --listen

# VRAM 8GB 이하
./webui.sh --api --listen --medvram

# VRAM 4GB 이하
./webui.sh --api --listen --lowvram
```

### 6.3 연결 확인

```bash
# 체크포인트 목록
curl http://localhost:7860/sdapi/v1/sd-models

# ControlNet 모델 목록
curl http://localhost:7860/controlnet/model_list

# ControlNet 모듈 목록
curl http://localhost:7860/controlnet/module_list
```

---

## 7. 포즈 에셋

**위치:** `backend/assets/poses/`

현재 포함된 포즈 PNG 파일 (OpenPose 스켈레톤):
- standing: `standing_neutral`, `standing_waving`, `standing_arms_up`, `standing_arms_crossed`, `standing_hands_on_hips`, `standing_thumbs_up`, `standing_from_behind`, `standing_looking_up`
- sitting: `sitting_neutral`, `sitting_chin_rest`, `sitting_leaning`, `sitting_eating`
- action: `walking`, `running`, `jumping`, `kneeling_neutral`, `crouching_neutral`, `lying_neutral`
- misc: `profile_standing`, `leaning_wall`, `cooking`, `eating`, `holding_object`, `holding_umbrella`, `writing`, `pointing_forward`, `covering_face`, `looking_at_viewer_neutral`

> **sitting 계열 에셋 추가 시:** `scripts/generate_sitting_pose_assets.py` 실행
> 생성 후 `controlnet.py` 주석 해제 + `SITTING_EXCLUDED_POSES`에서 해당 포즈 제거

---

## 8. 설치 확인 체크리스트

```
[ ] SD WebUI 실행 + /sdapi/v1/sd-models 응답 확인
[ ] anyloraCheckpoint_bakedvaeBlessedFp16 로드 확인
[ ] realisticVisionV60B1 로드 확인 (실사 시리즈용)
[ ] ControlNet 확장 설치 + control_v11p_sd15_openpose 인식 확인
[ ] ip-adapter-plus-face_sd15 + clip_vision_g 설치 확인
[ ] EasyNegative / verybadimagenegative_v1.3 임베딩 확인
[ ] Style LoRA 4종 설치 확인 (flat_color, ghibli, shinkai, J_huiben)
[ ] add_detail LoRA 설치 확인
[ ] Character LoRA 2종 설치 확인 (Yukari, Midoriya) ← 선택
[ ] backend/.env SD_BASE_URL 설정 확인
[ ] /sd-status 커맨드로 최종 연결 상태 확인
```

---

## 9. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| IP-Adapter `face_embed` 에러 | 애니 이미지에 FaceID 사용 | `ip-adapter-plus-face_sd15` + `ip-adapter_clip_sd15` 조합으로 변경 |
| ControlNet 무반응 | 모델/모듈 불일치 | `openpose_full` 모듈 + `control_v11p_sd15_openpose` 모델 확인 |
| Embedding 인식 안 됨 | 파일명 불일치 | `(painting by bad-artist).pt` — 괄호 포함 정확히 일치해야 함 |
| VRAM OOM | 해상도 / 배치 크기 | `--medvram` 추가, 해상도 512×768으로 낮춤 |
| 모델 로드 느림 | HDD 사용 | SSD에 `models/` 디렉토리 위치 권장 |
| `clip_vision_g` 못 찾음 | 파일명 오류 | `model.safetensors` → 반드시 `clip_vision_g.safetensors`로 이름 변경 |

---

## 10. 권장 설정 요약

| 항목 | 값 |
|------|-----|
| 주력 체크포인트 | `anyloraCheckpoint_bakedvaeBlessedFp16` (SD1.5) |
| 실사 체크포인트 | `realisticVisionV60B1_v51HyperVAE` (SD1.5) |
| IP-Adapter 모델 | `ip-adapter-plus-face_sd15` |
| IP-Adapter 모듈 | `ip-adapter_clip_sd15` |
| IP-Adapter weight | 0.50 (씬) / 0.40 (레퍼런스) |
| ControlNet 모델 | `control_v11p_sd15_openpose` |
| ControlNet 모듈 | `openpose_full` |
| ControlNet weight | 0.45~0.80 (씬 맥락에 따라 동적) |
| Negative Embeddings | EasyNegative, verybadimagenegative_v1.3, painting by bad-artist |

---

**Last Updated:** 2026-03-09
