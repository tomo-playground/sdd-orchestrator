# ComfyUI 구축 매뉴얼

Shorts Producer 이미지 생성을 위한 ComfyUI 설정 가이드.
다른 환경에서 재설치 시 이 문서를 기준으로 구성합니다.

---

## 1. ComfyUI 설치 (로컬)

```bash
# ComfyUI 로컬 실행
./run_comfyui.sh
```

**포트:** `8188`

### 1.1 체크포인트 모델

**설치 경로:** `~/Workspace/sd-models/checkpoints/`

| 파일명 | 용도 | Base |
|--------|------|------|
| `noobaiXLNAIXL_vPred10Version.safetensors` | 전 화풍 통합 ← **주력** | SDXL (V-Pred) |

> **V-Pred 핵심 제약사항:**
> - Sampler: **dpmpp_2m + karras** (ComfyUI 기본)
> - CFG: **4~5.5** (7 이상 과포화/깨짐)
> - 해상도: **832x1216** (2:3, 총 픽셀 ~1M)
> - SD1.5 LoRA/Embedding 호환 불가

---

## 2. ControlNet 모델

**설치 경로:** `~/Workspace/sd-models/controlnet/`

| 파일명 | 모듈 | 용도 |
|--------|------|------|
| `openpose_pre` | `openpose_full` | 포즈 스켈레톤 제어 ← **필수** |
| `noob_sdxl_controlnet_canny` | `canny` | 외곽선 제어 |
| `noob-sdxl-controlnet-depth-midas-v1-1` | `depth_midas` | 깊이 제어 |
| `noob-sdxl-controlnet-softedge_hed` | `softedge_hed` | 부드러운 외곽선 |
| `noob-sdxl-controlnet-tile` | `tile_resample` | 타일 업스케일 |
| `noob-sdxl-controlnet-lineart_anime` | `lineart_anime` | 라인아트 |

### 2.1 ControlNet 동작 정책

| 포즈 분류 | ControlNet | 이유 |
|-----------|-----------|------|
| `standing`, `walking`, `running` 등 직립 포즈 | **ON** (weight 0.60~0.80) | 골격 정밀도 중요 |
| `sitting`, `chin_rest`, `seiza` 등 앉기 계열 | **OFF** | 하체 스켈레톤 왜곡 문제 |
| action 포즈 (`jumping`, `pointing`) | ON (weight 0.80) | 동작 정밀도 우선 |
| 감성/서정 mood 씬 | ON (weight 0.45) | SD 자유 구성 허용 |

---

## 3. IP-Adapter (캐릭터 일관성)

### 3.1 모델

**설치 경로:** `~/Workspace/sd-models/controlnet/`

| 파일명 | 용도 | 비고 |
|--------|------|------|
| `NOOB-IPA-MARK1.safetensors` | 전체 스타일 전이 ← **주력** | NoobAI-XL 전용 |
| `ip-adapter-plus-face_sdxl_vit-h.safetensors` | 얼굴 + 스타일 | SDXL 호환 |

### 3.2 CLIP Vision 모델 (필수)

**설치 경로:** `~/Workspace/sd-models/clip_vision/`

| 파일명 | 용도 |
|--------|------|
| `CLIP-ViT-bigG-14-laion2B-39B-b160k` | SDXL IP-Adapter용 CLIP Vision |

---

## 4. Negative Embeddings

**설치 경로:** `~/Workspace/sd-models/embeddings/`

| 파일명 | 유형 | 용도 |
|--------|------|------|
| `SmoothNoob_Negative.safetensors` | negative | 일반 품질 억제 |
| `SmoothNoob_Quality.safetensors` | **positive** | 품질 향상 |
| `SmoothNegative_Hands.safetensors` | negative | 손 품질 억제 |

---

## 5. LoRA 모델

**설치 경로:** `~/Workspace/sd-models/lora/`

> ComfyUI 워크플로우에 LoraLoader 노드가 포함되어 있으며,
> Backend가 `<lora:name:weight>` 태그를 파싱하여 자동 적용합니다.

---

## 6. Backend 연동

### 6.1 환경 변수

`backend/.env`:
```bash
SD_CLIENT_TYPE=comfy
COMFYUI_BASE_URL=http://127.0.0.1:8188
```

### 6.2 연결 확인

```bash
# ComfyUI 시스템 상태
curl http://localhost:8188/system_stats

# 체크포인트 목록
curl http://localhost:8188/object_info/CheckpointLoaderSimple | jq '.CheckpointLoaderSimple.input.required.ckpt_name[0]'

# LoRA 목록
curl http://localhost:8188/object_info/LoraLoader | jq '.LoraLoader.input.required.lora_name[0]'
```

---

## 7. 포즈 에셋

**위치:** `backend/assets/poses/`

현재 포함된 포즈 PNG 파일 (OpenPose 스켈레톤):
- standing: `standing_neutral`, `standing_waving`, `standing_arms_up`, `standing_arms_crossed`, `standing_hands_on_hips`, `standing_thumbs_up`, `standing_from_behind`, `standing_looking_up`
- sitting: `sitting_neutral`, `sitting_chin_rest`, `sitting_leaning`, `sitting_eating`
- action: `walking`, `running`, `jumping`, `kneeling_neutral`, `crouching_neutral`, `lying_neutral`
- misc: `profile_standing`, `leaning_wall`, `cooking`, `eating`, `holding_object`, `holding_umbrella`, `writing`, `pointing_forward`, `covering_face`, `looking_at_viewer_neutral`

---

## 8. 설치 확인 체크리스트

```
[ ] ComfyUI Docker 빌드 + 실행 (docker compose up -d comfyui)
[ ] noobaiXLNAIXL_vPred10Version 로드 확인
[ ] ComfyUI-Manager 커스텀 노드 확인
[ ] ControlNet 모델 인식 확인
[ ] NOOB-IPA-MARK1 + CLIP-ViT-bigG 설치 확인
[ ] SmoothNoob 임베딩 3종 확인
[ ] backend/.env SD_CLIENT_TYPE=comfy 설정 확인
[ ] /sd-status 커맨드로 최종 연결 상태 확인
```

---

## 9. 권장 설정 요약

| 항목 | 값 |
|------|-----|
| 체크포인트 | `noobaiXLNAIXL_vPred10Version` (SDXL V-Pred) |
| Sampler | `dpmpp_2m` + `karras` |
| CFG Scale | `5.5` |
| 해상도 | `832 x 1216` |
| Steps | `28` |
| IP-Adapter 모델 | `NOOB-IPA-MARK1` / `ip-adapter-plus-face_sdxl_vit-h` |
| IP-Adapter weight | 0.50 (씬) / 0.40 (레퍼런스) |
| ControlNet 모델 | `openpose_pre` (포즈) |
| ControlNet weight | 0.45~0.80 (씬 맥락에 따라 동적) |
| Negative Embeddings | SmoothNoob_Negative, SmoothNegative_Hands |
| Positive Embedding | SmoothNoob_Quality |

---

## 10. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 이미지 과포화/색번짐 | CFG 너무 높음 | CFG 5.5 이하 확인 (V-Pred은 7 이상 금지) |
| ControlNet 무반응 | 모델명 불일치 | `/object_info`로 실제 이름 확인 |
| IP-Adapter 에러 | CLIP Vision 미설치 | `clip_vision/` 디렉토리에 CLIP-ViT-bigG 확인 |
| Embedding 인식 안 됨 | 파일명 불일치 | `embeddings/` 내 SmoothNoob 파일명 확인 |
| VRAM OOM | SDXL은 더 많은 VRAM 필요 | VRAM 8GB 이상 권장 |
| prompt_outputs_failed_validation | LoRA 파일 없음 | `loras/` 디렉토리 확인, placeholder 바이패스 적용됨 |
| `system_stats` 응답 없음 | ComfyUI 미기동 | `docker compose logs comfyui` 확인 |

---

## 11. Forge 레거시 (비활성)

Forge 서비스(`sd-webui`)는 제거되었습니다. 레거시 Dockerfile은 `forge-docker/`에 보존.
Forge로 복원이 필요하면:

```bash
# .env 변경
SD_CLIENT_TYPE=forge
SD_BASE_URL=http://127.0.0.1:7860
```

---

**Last Updated:** 2026-03-25
