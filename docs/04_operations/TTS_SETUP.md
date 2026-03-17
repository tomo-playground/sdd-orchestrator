# TTS 시스템 운영 가이드

## 1. 시스템 개요

Shorts Producer의 TTS는 **3엔진 분리 아키텍처**입니다. 역할에 따라 엔진이 구분됩니다.

| 엔진 | 역할 | 포트 | 프로세스 | 상태 |
|------|------|------|----------|------|
| **GPT-SoVITS v2** | 씬 TTS (일상 음성 생성) | :9880 | Audio Server subprocess (Python 3.12) | GPU 상주 |
| **Qwen3-TTS** | 보이스 디자인 전용 (voice preset 프리뷰, voice reference 생성) | :8001 | Audio Server (Python 3.13) | On-demand |
| **MusicGen** | BGM 생성 | :8001 | Audio Server (Python 3.13) | CPU 상주 |

> GPT-SoVITS는 Python 3.12 의존성으로 별도 venv를 사용하지만, Audio Server가 subprocess로 자동 관리합니다.

**아키텍처 흐름:**

```
Backend :8000 → audio_client.py
                ├─ synthesize_tts()          → GPT-SoVITS :9880 (씬 TTS, ref_audio 필수)
                ├─ synthesize_voice_design() → Qwen3-TTS :8001  (보이스 디자인 전용)
                └─ generate_music()          → MusicGen :8001   (BGM)
```

**핵심 규칙**: 씬 TTS에서 Qwen3가 호출되면 **버그**. 씬 TTS는 반드시 SoVITS만 사용.

### VRAM 사용량

| 모델 | VRAM | 상태 |
|------|------|------|
| SD WebUI (idle) | 8.5GB | 상주 |
| GPT-SoVITS | 1.1GB | 상주 |
| Qwen3-TTS | 3.5GB | on-demand (보이스 디자인 시만) |
| MusicGen | CPU | 상주 |
| **합계 (일상)** | **9.6GB / 16GB** | |

### 시스템 요구 사양

| 항목 | 최소 | 권장 |
|------|------|------|
| GPU | NVIDIA 8GB VRAM | NVIDIA 16GB VRAM |
| Python (Audio Server) | 3.13+ | 3.13+ |
| Python (GPT-SoVITS) | 3.12 | 3.12 |
| `transformers` | 4.57.3+ | 4.57.3+ |
| 메모리 | 16GB | 24GB 이상 |

---

## 2. 시스템 실행

### Audio Server (SoVITS + Qwen3-TTS + MusicGen)

```bash
./run_audio.sh start    # 포트 8001 (SoVITS subprocess 자동 기동 포함)
./run_audio.sh status
./run_audio.sh logs
./run_audio.sh stop
```

> GPT-SoVITS는 Audio Server의 subprocess로 자동 관리됩니다 (`sovits_process.py`).
> `run_audio.sh start` 시 SoVITS도 함께 기동, `stop` 시 함께 종료.
> 수동 기동 불필요.

### 헬스 체크

- Audio Server: `GET http://127.0.0.1:8001/health` — SoVITS, Qwen3-TTS, MusicGen 3개 모델 상태 반환

```json
{
  "status": "ok",
  "models": [
    {"name": "gpt-sovits", "loaded": true, "device": "cuda"},
    {"name": "qwen3-tts", "loaded": false, "device": "unknown"},
    {"name": "musicgen-small", "loaded": true, "device": "cpu"}
  ]
}
```

---

## 3. 엔진별 역할과 호출 경로

### 3.1 GPT-SoVITS — 씬 TTS (일상 음성)

캐릭터의 voice preset에서 ref_audio를 가져와 음색을 복제합니다.

**호출 경로:**
```
preview_tts.py / tts_prebuild.py
  → generate_tts_audio()          # tts_helpers.py 코어 함수
    → _resolve_voice_ref_audio()  # 캐릭터 → voice ref 해석
    → synthesize_tts()            # audio_client.py → SoVITS :9880
```

**Voice Reference 해석 우선순위** (`_resolve_voice_ref_audio`):
1. 감정별 voice_ref (`character_voice_ref` + scene_emotion)
2. default voice_ref (`character_voice_ref` latest)
3. voice preset 프리뷰 WAV (`character → voice_preset → audio_asset`)

`ref_audio_path`가 None이면 `synthesize_tts()`에서 즉시 에러 (Qwen3 fallback 없음).

### 3.2 Qwen3-TTS — 보이스 디자인 전용

텍스트 프롬프트로 새 음성을 생성합니다. 씬 TTS에서는 사용하지 않습니다.

**사용처:**
- Voice Preset 프리뷰 생성 (`/admin/voice-presets/preview`)
- 캐릭터 Voice Reference 생성 (`generate_voice_reference()`)

**호출 경로:**
```
voice_presets.py / voice_ref.py
  → synthesize_voice_design()  # audio_client.py → Qwen3 :8001
```

### 3.3 MusicGen — BGM

텍스트 프롬프트로 BGM을 생성합니다.

**호출 경로:**
```
audio_client.py → generate_music() → MusicGen :8001
```

---

## 4. 설정 (config.py SSOT)

### SoVITS 설정 (Audio Server config.py)

| 설정 | 기본값 | 환경 변수 | 설명 |
|------|--------|-----------|------|
| `SOVITS_ENABLED` | `true` | `SOVITS_ENABLED` | SoVITS subprocess 활성화 |
| `SOVITS_DIR` | `~/Workspace/GPT-SoVITS` | `SOVITS_DIR` | SoVITS 설치 경로 |
| `SOVITS_PORT` | `9880` | `SOVITS_PORT` | SoVITS 내부 포트 |
| `SOVITS_CONFIG` | `GPT_SoVITS/configs/tts_infer.yaml` | `SOVITS_CONFIG` | 추론 설정 파일 |
| `SOVITS_STARTUP_TIMEOUT` | `120` | `SOVITS_STARTUP_TIMEOUT` | 기동 대기 시간(초) |

### Backend 설정 (backend/config.py)

| 설정 | 기본값 | 환경 변수 |
|------|--------|-----------|
| `AUDIO_SERVER_URL` | `http://127.0.0.1:8001` | `AUDIO_SERVER_URL` |
| `DEFAULT_TTS_ENGINE` | `sovits` | `DEFAULT_TTS_ENGINE` |

### Qwen3-TTS 설정 (Audio Server)

| 설정 | 기본값 | 환경 변수 | 설명 |
|------|--------|-----------|------|
| `TTS_MODEL_NAME` | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | `TTS_MODEL_NAME` | HuggingFace 모델 ID |
| `TTS_DEVICE` | `"auto"` | `TTS_DEVICE` | CUDA > MPS > CPU 자동 감지 |
| `TTS_ATTN_IMPLEMENTATION` | `"sdpa"` | `TTS_ATTN_IMPLEMENTATION` | Attention 구현체 |
| `TTS_TEMPERATURE` | `0.7` | `TTS_TEMPERATURE` | 생성 다양성 |
| `TTS_TOP_P` | `0.8` | `TTS_TOP_P` | Nucleus sampling |
| `TTS_REPETITION_PENALTY` | `1.05` | `TTS_REPETITION_PENALTY` | 반복 억제 |
| `TTS_MAX_NEW_TOKENS` | `1024` | `TTS_MAX_NEW_TOKENS` | 최대 생성 토큰 수 |
| `TTS_DEFAULT_LANGUAGE` | `korean` | `TTS_DEFAULT_LANGUAGE` | 기본 언어 |

### Audio Server 공통

| 설정 | 기본값 | 환경 변수 | 설명 |
|------|--------|-----------|------|
| `MODEL_IDLE_TIMEOUT_SECONDS` | `0` (persistent) | `MODEL_IDLE_TIMEOUT_SECONDS` | 0=상주, >0=idle N초 후 언로드 |
| `CACHE_DIR` | `~/.cache/audio-server` | `CACHE_DIR` | 캐시 루트 디렉토리 |

### Post-Processing 설정

| 설정 | 기본값 | 환경 변수 | 설명 |
|------|--------|-----------|------|
| `TTS_AUDIO_TRIM_TOP_DB` | `60` | `TTS_AUDIO_TRIM_TOP_DB` | 무음 판정 dB |
| `TTS_AUDIO_FADE_MS` | `15` | `TTS_AUDIO_FADE_MS` | Fade in/out 밀리초 |
| `TTS_SILENCE_MAX_MS` | `800` | `TTS_SILENCE_MAX_MS` | 내부 무음 최대 허용 밀리초 |

---

## 5. Voice Design 모드

텍스트 프롬프트로 원하는 음성 스타일을 설계합니다. Qwen3-TTS의 `generate_voice_design` API를 사용합니다.

### 한국어 자동 번역

한국어 입력 시 Gemini Flash로 자동 영어 변환됩니다.

| 입력 | 변환 결과 |
|------|----------|
| `"차분한 40대 여성"` | `"A calm woman in her 40s"` |
| `"활기찬 20대 남성 아나운서"` | `"An energetic male announcer in his 20s"` |

### Context-Aware TTS (씬 감정 반영)

| Speaker 유형 | 동작 |
|-------------|------|
| **나레이터** | Voice Preset 기본 + 장면 감정 자동 반영 |
| **캐릭터** | Voice Preset + Gemini 감정 분석 → SoVITS ref_audio로 음색 복제 |

### Voice Design 우선순위

| 순위 | 소스 | 설명 |
|------|------|------|
| 1 | Per-scene `voice_design_prompt` | 사용자 직접 입력 |
| 2 | Context-Aware Auto-Generation | 시나리오 기반 자동 감정 생성 |
| 3 | Voice Preset | 캐릭터/나레이터 기본 목소리 |
| 4 | System Default | 기본값 |

---

## 6. 모델 로딩

### Audio Server (Qwen3-TTS + MusicGen)

`audio/main.py` lifespan에서 관리:
- **Persistent 모드** (`MODEL_IDLE_TIMEOUT_SECONDS=0`): MusicGen CPU 프리로드, Qwen3 on-demand
- **On-demand 모드**: 첫 요청 시 로드, idle timeout 후 자동 언로드

```python
# audio/services/tts_engine.py
model = Qwen3TTSModel.from_pretrained(
    TTS_MODEL_NAME,
    dtype=dtype,
    device_map=device,  # transformers 4.57.3+ 필수
    attn_implementation=TTS_ATTN_IMPLEMENTATION,
)
```

### GPT-SoVITS

별도 프로세스에서 자체 모델 로딩. `api_v2.py` 기동 시 자동 로드.

---

## 7. 트러블슈팅

### SoVITS 서버 미기동

**증상**: `GPT-SoVITS is not running` 에러 또는 SoVITS 연결 실패

**확인**: `curl http://127.0.0.1:8001/health` → `gpt-sovits.loaded` 확인

**대응**:
1. Audio Server 재시작: `./run_audio.sh stop && ./run_audio.sh start`
2. SoVITS 로그 확인: `cat ~/Workspace/GPT-SoVITS/logs/sovits.log`
3. `SOVITS_ENABLED=true` 환경 변수 확인

### Qwen3 모델 로드 실패 (meta tensor)

**증상**: `Cannot copy out of meta tensor; no data!`

**원인**: `device_map` 미지정 시 transformers 4.57.3+에서 메타 텐서 생성

**대응**: `from_pretrained(device_map=device)` 사용 (`.to(device)` 금지)

### 캐릭터에 Voice Reference 없음

**증상**: `ref_audio_path 필수` 에러

**대응**: 캐릭터에 voice preset 매핑 확인 → voice preset에 프리뷰 WAV 존재 확인

### TTS 캐시 초기화

```bash
rm -rf ~/.cache/shorts-producer/prompts/tts/ ~/.cache/audio-server/tts/
```

### 빈 스크립트 씬

**증상**: `Scene {i}: empty script, skipping TTS`

**대응**: 정상 동작. 스크립트 없는 씬은 무음 처리.

---

## 8. 관련 파일 목록

| 파일 | 역할 |
|------|------|
| `backend/config.py` | TTS/SoVITS/Audio 설정 SSOT |
| `backend/services/audio_client.py` | `synthesize_tts()` (SoVITS), `synthesize_voice_design()` (Qwen3), `generate_music()` |
| `backend/services/video/tts_helpers.py` | `generate_tts_audio()` 코어, `_resolve_voice_ref_audio()` |
| `backend/services/preview_tts.py` | TTS 프리뷰 |
| `backend/services/tts_prebuild.py` | TTS 사전 생성 |
| `backend/services/characters/voice_ref.py` | 캐릭터 Voice Reference 생성 (Qwen3) |
| `backend/routers/voice_presets.py` | Voice Preset 프리뷰 API (Qwen3) |
| `audio/main.py` | Audio Server 엔트리포인트 (3엔진 통합) |
| `audio/config.py` | Audio Server 설정 SSOT |
| `audio/services/tts_engine.py` | Qwen3-TTS 모델 로딩/합성 |
| `audio/services/music_engine.py` | MusicGen 모델 로딩/생성 |
| `audio/services/sovits_process.py` | SoVITS subprocess 라이프사이클 관리 |
| `audio/services/tts_postprocess.py` | TTS 6단계 후처리 파이프라인 |
| `audio/services/text_preprocess.py` | 한국어 숫자 전처리 |

---

**최종 업데이트**: 2026-03-17 (SoVITS subprocess 자동 관리, 설정값 소스 동기화)
