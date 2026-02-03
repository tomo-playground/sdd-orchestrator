# WD14 Tagger 구축 가이드

Shorts Producer는 생성된 이미지의 품질 검수 및 프롬프트 일치도 계산을 위해 **WD14 (Waifu Diffusion 14) Tagger**를 사용합니다.

## 1. 모델 개요

- **모델명**: `wd-v1-4-vit-tagger-v2`
- **형식**: ONNX (Open Neural Network Exchange)
- **용도**: 이미지 분석을 통해 6,000여 개의 Danbooru 태그를 확률로 추출

## 2. 수동 설치 방법

서버 실행 시 모델이 없으면 에러가 발생하므로, 아래 단계에 따라 모델 파일을 배치해야 합니다.

### 1) 디렉토리 생성
```bash
mkdir -p backend/models/wd14
```

### 2) 모델 파일 다운로드
HuggingFace 등에서 아래 파일들을 다운로드하여 `backend/models/wd14/` 경로에 저장합니다.

- **ONNX 모델**: [model.onnx](https://huggingface.co/SmilingWolf/wd-v1-4-vit-tagger-v2/blob/main/model.onnx)
- **태그 파일**: [selected_tags.csv](https://huggingface.co/SmilingWolf/wd-v1-4-vit-tagger-v2/blob/main/selected_tags.csv)

### 3) 최종 파일 구조
```text
backend/models/wd14/
├── model.onnx
└── selected_tags.csv
```

## 3. 설정 및 검증

### config.py 설정
`backend/config.py` 또는 `.env`에서 경로를 조절할 수 있습니다.
- `WD14_MODEL_DIR`: 모델이 위치한 디렉토리 경로 (기본값: `models/wd14`)
- `WD14_THRESHOLD`: 태그 감지 임계값 (기본값: `0.35`)

### 수동 검증 스크립트
설치가 완료되면 아래 명령어로 정상 작동 여부를 확인할 수 있습니다.
```bash
cd backend
uv run python -c "from services.validation import load_wd14_model; load_wd14_model(); print('✅ WD14 Model Loaded successfully')"
```

## 4. 트러블슈팅

### ONNX Runtime 에러
- **증상**: `onnxruntime` 관련 에러 발생
- **해결**: Apple Silicon Mac의 경우 `onnxruntime-silicon` 또는 최신 `onnxruntime`이 설치되어 있는지 확인하세요.
  ```bash
  pip install onnxruntime
  ```

### 모델 파일 누락
- **증상**: `FileNotFoundError: WD14 model files not found.`
- **해결**: `selected_tags.csv` 파일 이름이 정확한지, 파일이 `models/wd14` 경로 안에 있는지 다시 확인하세요.
