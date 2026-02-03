# SD WebUI 구축 매뉴얼

Shorts Producer의 이미지 생성을 위한 Stable Diffusion WebUI 설정 가이드.

---

## 1. 기본 설치

### 1.1 SD WebUI 설치

```bash
# Clone
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui

# 실행 (첫 실행 시 자동 설치)
./webui.sh --api --listen
```

**필수 옵션:**
- `--api`: API 모드 활성화 (Backend 연동 필수)
- `--listen`: 외부 접근 허용 (다른 PC에서 접근 시)

### 1.2 체크포인트 모델

**권장 모델:** Anime 스타일
- `anythingV3_fp16.safetensors` (SD1.5 기반)
- `animagine-xl.safetensors` (SDXL 기반)

**설치 경로:** `models/Stable-diffusion/`

---

## 2. ControlNet 확장

### 2.1 설치

1. SD WebUI → Extensions → Install from URL
2. URL: `https://github.com/Mikubill/sd-webui-controlnet.git`
3. Install → Restart UI

### 2.2 ControlNet 모델

**다운로드:** https://huggingface.co/lllyasviel/ControlNet-v1-1/tree/main

**필수 모델:**
| 모델 | 용도 |
|------|------|
| `control_v11p_sd15_openpose` | 포즈 제어 |
| `control_v11f1p_sd15_depth` | 깊이 제어 |

**설치 경로:** `extensions/sd-webui-controlnet/models/` (A1111 루트 기준)


---

## 3. IP-Adapter 설정 (캐릭터 일관성)

### 3.1 IP-Adapter 모델 다운로드

**다운로드:** https://huggingface.co/h94/IP-Adapter/tree/main/models

| 모델 | 용도 | 크기 |
|------|------|------|
| `ip-adapter-plus_sd15.safetensors` | **애니메이션 (권장)** | ~98MB |
| `ip-adapter-plus-face_sd15.safetensors` | 얼굴 + 스타일 | ~98MB |
| `ip-adapter-faceid-plusv2_sd15.safetensors` | 실사 얼굴 전용 | ~150MB |

**설치 경로:** `extensions/sd-webui-controlnet/models/`

### 3.2 CLIP Vision 모델 (필수)

IP-Adapter CLIP 모델 사용 시 필요.

**다운로드:** https://huggingface.co/h94/IP-Adapter/tree/main/models/image_encoder

- `model.safetensors` → `clip_vision_g.safetensors`로 이름 변경

**설치 경로:** `extensions/sd-webui-controlnet/models/`

### 3.3 InsightFace (FaceID 전용)

> **참고:** 애니메이션 캐릭터는 CLIP 모델 사용 권장. FaceID는 실사 얼굴 전용.

```bash
pip install insightface onnxruntime
```

**buffalo_l 모델:**
1. 다운로드: https://github.com/deepinsight/insightface/releases
2. 설치 경로: `~/.insightface/models/buffalo_l/`

---

## 4. Negative Embeddings

### 4.1 권장 임베딩

| 임베딩 | 설명 |
|--------|------|
| `easynegative` | 일반적인 품질 개선 |
| `verybadimagenegative_v1.3` | 저품질 이미지 방지 |

**다운로드:** Civitai에서 검색

**설치 경로:** `embeddings/`

---

## 5. LoRA 모델 (선택)

### 5.1 캐릭터 LoRA

프로젝트에서 사용 중인 LoRA:
- `eureka_v9` - 커스텀 캐릭터
- `chibi-laugh` - 치비 스타일

**설치 경로:** `models/Lora/`

---

## 6. Backend 연동

### 6.1 환경 변수 설정

`backend/.env`:
```bash
# SD WebUI URL (기본값: localhost)
SD_BASE_URL=http://192.168.x.x:7860
```

### 6.2 연결 확인

```bash
# SD WebUI 상태 확인
curl http://192.168.x.x:7860/sdapi/v1/sd-models

# ControlNet 모델 확인
curl http://192.168.x.x:7860/controlnet/model_list
```

---

## 7. 트러블슈팅

### 7.1 IP-Adapter 관련

| 에러 | 원인 | 해결 |
|------|------|------|
| `face_embed` 없음 | 애니메이션 이미지에 FaceID 사용 | CLIP 모델 사용 (`ip-adapter-plus_sd15`) |
| `HeaderTooLarge` | 모델 파일 손상 | 다시 다운로드 |
| ControlNet 무반응 | 모델/모듈 불일치 | 아래 조합 참조 |

**올바른 모델-모듈 조합:**

| 모델 | 모듈 | 용도 |
|------|------|------|
| `ip-adapter-plus_sd15` | `ip-adapter_clip_sd15` | 애니메이션 |
| `ip-adapter-faceid-plusv2_sd15` | `ip-adapter_face_id_plus` | 실사 |

### 7.2 VRAM 부족

```bash
# 낮은 VRAM 옵션
./webui.sh --api --medvram
# 또는
./webui.sh --api --lowvram
```

### 7.3 SDXL 사용 시

SDXL 모델 사용 시 IP-Adapter도 SDXL 버전 필요:
- `ip-adapter-plus_sdxl_vit-h.safetensors`

---

## 8. 권장 설정 요약

| 항목 | 권장값 |
|------|--------|
| 체크포인트 | `anythingV3_fp16.safetensors` (SD1.5) |
| IP-Adapter | `ip-adapter-plus_sd15.safetensors` |
| IP-Adapter 모듈 | `ip-adapter_clip_sd15` |
| IP-Adapter Weight | 0.7 ~ 0.8 |
| ControlNet | `control_v11p_sd15_openpose` |
| Negative Embedding | `easynegative` |

---

**Last Updated:** 2026-01-27
