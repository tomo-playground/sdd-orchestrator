# TTS 시스템 운영 가이드

## 1. 시스템 개요

Shorts Producer의 TTS는 **2엔진 분리 아키텍처**입니다. 역할에 따라 엔진이 구분됩니다.

| 엔진 | 역할 | 포트 | 프로세스 | 상태 |
|------|------|------|----------|------|
| **Qwen3-TTS** | 씬 TTS + 보이스 디자인 (voice preset 프리뷰, voice reference 생성) | :8001 | Audio Server (Python 3.13) | On-demand / Persistent |
| **MusicGen** | BGM 생성 | :8001 | Audio Server (Python 3.13) | CPU 상주 |

**아키텍처 흐름:**

```
Backend :8000 → audio_client.py
                ├─ synthesize_tts()             → Qwen3-TTS :8001 (씬 TTS)
                ├─ synthesize_voice_design()     → Qwen3-TTS :8001 (보이스 디자인)
                └─ generate_music()             → MusicGen :8001   (BGM)
```

### VRAM 사용량

| 모델 | VRAM | 상태 |
|------|------|------|
| SD WebUI (idle) | 8.5GB | 상주 |
| Qwen3-TTS | 3.5GB | on-demand / persistent |
| MusicGen | CPU | 상주 |
| **합계 (일상)** | **8.5GB / 16GB** (TTS idle 시) | |

### 시스템 요구 사양

| 항목 | 최소 | 권장 |
|------|------|------|
| GPU | NVIDIA 8GB VRAM | NVIDIA 16GB VRAM |
| Python (Audio Server) | 3.13+ | 3.13+ |
| `transformers` | 4.57.3+ | 4.57.3+ |
| 메모리 | 16GB | 24GB 이상 |

---

## 2. 시스템 실행

### Audio Server (Qwen3-TTS + MusicGen)

```bash
./run_audio.sh start    # 포트 8001
./run_audio.sh status
./run_audio.sh logs
./run_audio.sh stop
```

### 헬스 체크

- Audio Server: `GET http://127.0.0.1:8001/health` — Qwen3-TTS, MusicGen 2개 모델 상태 반환

```json
{
  "status": "ok",
  "models": [
    {"name": "qwen3-tts", "loaded": true, "device": "cuda"},
    {"name": "musicgen-small", "loaded": true, "device": "cpu"}
  ]
}
```

---

## 3. 엔진별 역할과 호출 경로

### 3.1 Qwen3-TTS — 씬 TTS + 보이스 디자인

Qwen3-TTS는 유일한 TTS 엔진으로, 씬 음성 생성과 보이스 디자인 모두 담당합니다.

**씬 TTS 호출 경로:**
```
preview_tts.py / tts_prebuild.py
  → generate_tts_audio()          # tts_helpers.py 코어 함수
    → synthesize_tts()            # audio_client.py → Qwen3-TTS :8001
```

**보이스 디자인 호출 경로:**
```
voice_presets.py / voice_ref.py
  → synthesize_voice_design()  # audio_client.py → Qwen3-TTS :8001
```

**사용처:**
- 씬 TTS 생성 (preview, prebuild, render)
- Voice Preset 프리뷰 생성 (`/admin/voice-presets/preview`)
- 캐릭터 Voice Reference 생성 (`generate_voice_reference()`)

### 3.2 MusicGen — BGM

텍스트 프롬프트로 BGM을 생성합니다.

**호출 경로:**
```
audio_client.py → generate_music() → MusicGen :8001
```

---

## 4. 설정 (config.py SSOT)

### Backend 설정 (backend/config.py)

| 설정 | 기본값 | 환경 변수 |
|------|--------|-----------|
| `AUDIO_SERVER_URL` | `http://127.0.0.1:8001` | `AUDIO_SERVER_URL` |
| `DEFAULT_TTS_ENGINE` | `qwen3` | `DEFAULT_TTS_ENGINE` |

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
| **캐릭터** | Voice Preset + Gemini 감정 분석 → Qwen3-TTS 음성 생성 |

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
- **Persistent 모드** (`MODEL_IDLE_TIMEOUT_SECONDS=0`): MusicGen CPU 프리로드, Qwen3-TTS GPU 상주
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

---

## 7. 트러블슈팅

### Qwen3 모델 로드 실패 (meta tensor)

**증상**: `Cannot copy out of meta tensor; no data!`

**원인**: `device_map` 미지정 시 transformers 4.57.3+에서 메타 텐서 생성

**대응**: `from_pretrained(device_map=device)` 사용 (`.to(device)` 금지)

### TTS 캐시 초기화

```bash
rm -rf ~/.cache/shorts-producer/prompts/tts/ ~/.cache/audio-server/tts/
```

### 빈 스크립트 씬

**증상**: `Scene {i}: empty script, skipping TTS`

**대응**: 정상 동작. 스크립트 없는 씬은 무음 처리.

### TTS 503 에러 (모델 로드 중)

**증상**: Audio Server 기동 직후 TTS 요청 시 503 응답

**대응**: 정상 동작. 모델 로드 완료 대기 후 자동 재시도 (Backend `audio_client.py` 내장)

---

## 8. 관련 파일 목록

| 파일 | 역할 |
|------|------|
| `backend/config.py` | TTS/Audio 설정 SSOT |
| `backend/services/audio_client.py` | `synthesize_tts()` (Qwen3), `synthesize_voice_design()` (Qwen3), `generate_music()` |
| `backend/services/video/tts_helpers.py` | `generate_tts_audio()` 코어 |
| `backend/services/preview_tts.py` | TTS 프리뷰 |
| `backend/services/tts_prebuild.py` | TTS 사전 생성 |
| `backend/services/characters/voice_ref.py` | 캐릭터 Voice Reference 생성 (Qwen3) |
| `backend/routers/voice_presets.py` | Voice Preset 프리뷰 API (Qwen3) |
| `audio/main.py` | Audio Server 엔트리포인트 (2엔진 통합) |
| `audio/config.py` | Audio Server 설정 SSOT |
| `audio/services/tts_engine.py` | Qwen3-TTS 모델 로딩/합성 |
| `audio/services/music_engine.py` | MusicGen 모델 로딩/생성 |
| `audio/services/tts_postprocess.py` | TTS 6단계 후처리 파이프라인 |
| `audio/services/text_preprocess.py` | 한국어 숫자 전처리 |

---

**최종 업데이트**: 2026-03-17 (SoVITS 완전 제거, Qwen3-TTS 유일 엔진 전환)
