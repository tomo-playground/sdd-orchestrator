# /sd-status Command

Stable Diffusion WebUI 상태를 확인하는 원자적 명령입니다.

## 사용법

```
/sd-status [check]
```

### Checks

| Check | 설명 |
|-------|------|
| (없음) | 전체 상태 조회 |
| `connection` | 연결 상태만 확인 |
| `models` | 로드된 모델/LoRA 목록 |
| `queue` | 현재 생성 큐 상태 |

## 실행 내용

### API 엔드포인트
```
Base URL: http://127.0.0.1:7860

GET /sdapi/v1/sd-models      # 모델 목록
GET /sdapi/v1/loras          # LoRA 목록
GET /sdapi/v1/progress       # 진행 상태
GET /sdapi/v1/options        # 현재 설정
```

### 연결 테스트
```bash
curl -s http://127.0.0.1:7860/sdapi/v1/sd-models | head -c 100
```

## 출력 형식

```markdown
## SD WebUI 상태

### 연결
✅ 연결됨 (http://127.0.0.1:7860)

### 현재 모델
- **Checkpoint**: animagine-xl.safetensors
- **VAE**: sdxl_vae.safetensors

### 로드된 LoRA
- eureka_v9.safetensors
- chibi-laugh.safetensors

### 큐 상태
- 대기: 0
- 진행중: 없음
```

## 에러 처리

```markdown
## SD WebUI 상태

### 연결
❌ 연결 실패

### 해결 방법
1. SD WebUI가 실행 중인지 확인
2. `--api` 옵션으로 시작했는지 확인
3. 포트 7860이 열려있는지 확인

```bash
# SD WebUI 시작 명령
./webui.sh --api --listen
```
```

## 관련 파일
- `backend/config.py` - SD_WEBUI_URL 설정
