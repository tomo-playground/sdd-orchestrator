# SD WebUI 구축 매뉴얼

Shorts Producer 이미지 생성을 위한 Stable Diffusion WebUI (Forge) 설정 가이드.
다른 환경에서 재설치 시 이 문서를 기준으로 구성합니다.

---

## 1. Forge 설치 (Docker)

```bash
cd /path/to/shorts-producer
docker compose build sd-webui
docker compose up -d sd-webui
```

**Dockerfile:** `forge-docker/Dockerfile`
**docker-compose.yml** 서비스: `sd-webui`

**필수 실행 옵션** (환경변수 `COMMANDLINE_ARGS`):

| 옵션 | 설명 |
|------|------|
| `--api` | REST API 활성화 (Backend 연동 필수) |
| `--listen` | 외부 IP 접근 허용 |
| `--opt-sdp-attention` | SDP Attention 최적화 |
| `--cuda-malloc` | CUDA 메모리 최적화 |

### 1.1 체크포인트 모델

**설치 경로:** `~/Workspace/sd-models/checkpoints/`

| 파일명 | 용도 | Base |
|--------|------|------|
| `noobaiXLNAIXL_vPred10Version.safetensors` | 전 화풍 통합 ← **주력** | SDXL (V-Pred) |

> **V-Pred 핵심 제약사항:**
> - Sampler: **Euler만** (DPM++, DDIM 등 비정상 출력)
> - CFG: **4~5** (7 이상 과포화/깨짐)
> - CFG Rescale: **0.2** (회색톤 방지 필수)
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

> Backend 매핑: `backend/services/controlnet.py` → `CONTROLNET_MODELS` dict

### 2.1 ControlNet 동작 정책

| 포즈 분류 | ControlNet | 이유 |
|-----------|-----------|------|
| `standing`, `walking`, `running` 등 직립 포즈 | **ON** (weight 0.60~0.80) | 골격 정밀도 중요 |
| `sitting`, `chin_rest`, `seiza` 등 앉기 계열 | **OFF** | 하체 스켈레톤 왜곡 문제 |
| action 포즈 (`jumping`, `pointing`) | ON (weight 0.80) | 동작 정밀도 우선 |
| 감성/서정 mood 씬 | ON (weight 0.45) | SD 자유 구성 허용 |

> 자동 할당 로직: `backend/services/agent/nodes/finalize.py` `_resolve_controlnet_weight()`

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

> Backend 매핑: `backend/services/controlnet.py` → `IP_ADAPTER_MODELS` dict
> **현재 적용 weight:** `0.50` (씬 생성), `0.40` (레퍼런스 생성)

---

## 4. Negative Embeddings

**설치 경로:** `~/Workspace/sd-models/embeddings/`

| 파일명 | 유형 | 용도 |
|--------|------|------|
| `SmoothNoob_Negative.safetensors` | negative | 일반 품질 억제 |
| `SmoothNoob_Quality.safetensors` | **positive** | 품질 향상 |
| `SmoothNegative_Hands.safetensors` | negative | 손 품질 억제 |

> DB에 등록된 3개 임베딩이 StyleProfile에 자동 적용됨.

---

## 5. CFG Rescale 확장 (V-Pred 필수)

**설치:** Dockerfile에 자동 포함

```dockerfile
# forge-docker/Dockerfile
clone_repo https://github.com/Seshelle/CFG_Rescale_webui.git extensions/CFG_Rescale_webui
```

**적용:** `backend/config.py` → `SD_CFG_RESCALE = 0.2`
`apply_sampler_to_payload()`에서 `extra_generation_params["CFG Rescale φ"]`로 자동 주입.

> **미적용 시** V-Pred 출력이 회색으로 나옴. 전환 성패 좌우.

---

## 6. LoRA 모델

**설치 경로:** `~/Workspace/sd-models/lora/`

> **현재 상태:** SD1.5 LoRA 13개는 `is_active=false`로 비활성화됨.
> SDXL LoRA 재학습(Step 21) 완료 전까지 LoRA 없이 운영.

---

## 7. Backend 연동

### 7.1 환경 변수

`backend/.env`:
```bash
SD_BASE_URL=http://127.0.0.1:7860
```

### 7.2 연결 확인

```bash
# 체크포인트 목록
curl http://localhost:7860/sdapi/v1/sd-models

# 현재 모델 확인
curl http://localhost:7860/sdapi/v1/options | jq '.sd_model_checkpoint'

# ControlNet 모델 목록
curl http://localhost:7860/controlnet/model_list

# IP-Adapter 모듈 목록
curl http://localhost:7860/controlnet/module_list
```

---

## 8. 포즈 에셋

**위치:** `backend/assets/poses/`

현재 포함된 포즈 PNG 파일 (OpenPose 스켈레톤):
- standing: `standing_neutral`, `standing_waving`, `standing_arms_up`, `standing_arms_crossed`, `standing_hands_on_hips`, `standing_thumbs_up`, `standing_from_behind`, `standing_looking_up`
- sitting: `sitting_neutral`, `sitting_chin_rest`, `sitting_leaning`, `sitting_eating`
- action: `walking`, `running`, `jumping`, `kneeling_neutral`, `crouching_neutral`, `lying_neutral`
- misc: `profile_standing`, `leaning_wall`, `cooking`, `eating`, `holding_object`, `holding_umbrella`, `writing`, `pointing_forward`, `covering_face`, `looking_at_viewer_neutral`

> **sitting 계열 에셋 추가 시:** `scripts/generate_sitting_pose_assets.py` 실행

---

## 9. 설치 확인 체크리스트

```
[ ] Forge Docker 빌드 + 실행 (docker compose up -d sd-webui)
[ ] noobaiXLNAIXL_vPred10Version 로드 확인
[ ] CFG Rescale 확장 활성화 확인
[ ] ControlNet openpose_pre 인식 확인
[ ] NOOB-IPA-MARK1 + CLIP-ViT-bigG 설치 확인
[ ] SmoothNoob 임베딩 3종 확인
[ ] backend/.env SD_BASE_URL 설정 확인
[ ] /sd-status 커맨드로 최종 연결 상태 확인
```

---

## 10. 권장 설정 요약

| 항목 | 값 |
|------|-----|
| 체크포인트 | `noobaiXLNAIXL_vPred10Version` (SDXL V-Pred) |
| Sampler | `Euler` |
| CFG Scale | `4.5` |
| CFG Rescale | `0.2` |
| 해상도 | `832 x 1216` |
| Steps | `28` |
| IP-Adapter 모델 | `NOOB-IPA-MARK1` / `ip-adapter-plus-face_sdxl_vit-h` |
| IP-Adapter weight | 0.50 (씬) / 0.40 (레퍼런스) |
| ControlNet 모델 | `openpose_pre` (포즈) |
| ControlNet weight | 0.45~0.80 (씬 맥락에 따라 동적) |
| Negative Embeddings | SmoothNoob_Negative, SmoothNegative_Hands |
| Positive Embedding | SmoothNoob_Quality |

---

## 11. Rollback 절차 (V-Pred → SD1.5 복원)

전환 실패 또는 품질 문제 시 SD1.5로 복원하는 절차.

### 11.1 코드 복원

```bash
# 마이그레이션 커밋 되돌리기
git revert <migration-commit-sha>
```

### 11.2 DB 복원

```bash
cd backend
source .venv/bin/activate

# Alembic downgrade (1단계 롤백)
alembic downgrade -1
```

이 명령으로 복원되는 항목:
- `loras.is_active` 컬럼 제거
- `sd_models`: NoobAI-XL 레코드 삭제, SD1.5 모델 재활성화
- `embeddings`: SmoothNoob 3종 삭제, SD1.5 임베딩 재활성화
- `style_profiles`: SD1.5 파라미터 복원 (sampler, cfg, sd_model_id, embeddings, loras)
- `loras`: 13개 LoRA 재활성화

### 11.3 SD 모델 파일 복원

```bash
# SD1.5 모델 백업에서 복원
cp ~/Workspace/sd-models-backup-sd15/checkpoints/* ~/Workspace/sd-models/checkpoints/
cp ~/Workspace/sd-models-backup-sd15/controlnet/* ~/Workspace/sd-models/controlnet/
cp ~/Workspace/sd-models-backup-sd15/embeddings/* ~/Workspace/sd-models/embeddings/
cp ~/Workspace/sd-models-backup-sd15/lora/* ~/Workspace/sd-models/lora/
```

> **주의:** `sd-models-backup-sd15/` 디렉토리는 Step 22 (최종 삭제) 전까지 보존.

### 11.4 Docker 재빌드

```bash
docker compose build sd-webui
docker compose up -d sd-webui
```

### 11.5 확인

```bash
# SD1.5 모델 로드 확인
curl http://localhost:7860/sdapi/v1/options | jq '.sd_model_checkpoint'
# 기대값: "anyloraCheckpoint_bakedvaeBlessedFp16.safetensors"

# Backend 테스트
cd backend && source .venv/bin/activate
python -m pytest tests/ -q
```

---

## 12. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 이미지가 회색으로 나옴 | CFG Rescale 미적용 | Forge 설정에서 CFG Rescale 확장 확인, `SD_CFG_RESCALE=0.2` |
| 이미지 과포화/색번짐 | CFG 너무 높음 | `SD_DEFAULT_CFG_SCALE=4.5` 확인 (V-Pred은 7 이상 금지) |
| ControlNet 무반응 | SDXL 모델명 불일치 | `controlnet/model_list`로 실제 이름 확인 후 `CONTROLNET_MODELS` 수정 |
| IP-Adapter 에러 | CLIP Vision 미설치 | `clip_vision/` 디렉토리에 CLIP-ViT-bigG 확인 |
| Embedding 인식 안 됨 | 파일명 불일치 | `embeddings/` 내 SmoothNoob 파일명 정확히 확인 |
| VRAM OOM | SDXL은 더 많은 VRAM 필요 | `--opt-sdp-attention` 확인, VRAM 8GB 이상 권장 |
| `<lora:xxx>` SD 에러 | SD1.5 LoRA 참조 | `is_active=false` 필터 확인, DB에서 비활성 LoRA 조회 차단 |

---

**Last Updated:** 2026-03-14
