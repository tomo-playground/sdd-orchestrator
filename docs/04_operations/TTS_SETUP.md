# TTS 시스템 운영 가이드 (Qwen3-TTS)

## 1. 시스템 개요

Shorts Producer는 **Qwen3-TTS** 단일 엔진으로 음성을 생성합니다. 기존 Edge-TTS 및 Google Cloud TTS는 제거되었으며, 모든 TTS 요청은 Qwen3-TTS로 처리됩니다.

| 항목 | 값 |
|------|-----|
| 모델 | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` |
| 디바이스 | auto (MPS/CPU 자동 감지) |
| 모델 로딩 | 서버 lifespan에서 프리로딩 |
| 출력 형식 | MP3 (soundfile 기록) |

**아키텍처 흐름:**

```
VideoBuilder.build()
  └─ process_scenes()
       └─ generate_tts(scene_i)
            ├─ get_qwen_model()        # 글로벌 싱글톤
            └─ voice design            # 텍스트 프롬프트로 음성 생성
```

### 시스템 요구 사양

| 항목 | 최소 | 권장 |
|------|------|------|
| 하드웨어 | Intel Mac / Linux | Apple Silicon (M1/M2/M3/M4) |
| 메모리 | 16GB | 24GB 이상 |
| 저장 공간 | 5GB (모델 가중치) | 10GB |

### 의존성 설치

```bash
brew install sox
cd backend && uv pip install qwen-tts torch torchaudio transformers accelerate soundfile
```

---

## 2. 설정 (config.py SSOT)

모든 TTS 설정은 `backend/config.py`에서 관리합니다. 환경 변수로 오버라이드 가능합니다.

| 설정 | 기본값 | 환경 변수 | 설명 |
|------|--------|-----------|------|
| `TTS_MODEL_NAME` | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | `TTS_MODEL_NAME` | HuggingFace 모델 ID |
| `TTS_DEVICE` | `"auto"` | `TTS_DEVICE` | `"auto"` / `"mps"` / `"cpu"` |
| `TTS_ATTN_IMPLEMENTATION` | `"sdpa"` | `TTS_ATTN_IMPLEMENTATION` | Attention 구현체 (sdpa 권장) |
| `TTS_TEMPERATURE` | `0.7` | `TTS_TEMPERATURE` | 생성 다양성 (낮을수록 일관된 음성) |
| `TTS_TOP_P` | `0.9` | `TTS_TOP_P` | Nucleus sampling 임계값 |
| `TTS_REPETITION_PENALTY` | `1.1` | `TTS_REPETITION_PENALTY` | 반복 억제 (1.0 = 비활성) |

**디바이스 자동 감지 로직** (`services/video/scene_processing.py`):

```python
if device == "auto":
    device = "mps" if torch.backends.mps.is_available() else "cpu"
```

- Apple Silicon Mac: MPS 사용 (bfloat16)
- 그 외: CPU 사용 (float32)

---

## 3. Voice Design 모드

텍스트 프롬프트로 원하는 음성 스타일을 설계합니다. Qwen3-TTS의 `generate_voice_design` API를 사용합니다.

### 사용법

`voice_design_prompt` 필드에 음성 스타일 설명을 입력합니다.

```json
{
  "voice_design_prompt": "A calm woman in her 40s with a warm, soothing tone"
}
```

### 한국어 자동 번역

한국어 입력 시 Gemini Flash(`GEMINI_TEXT_MODEL`)로 자동 영어 변환됩니다. 번역 결과는 인메모리 딕셔너리에 캐시됩니다.

| 입력 | 변환 결과 |
|------|----------|
| `"차분한 40대 여성"` | `"A calm woman in her 40s"` |
| `"활기찬 20대 남성 아나운서"` | `"An energetic male announcer in his 20s"` |

**번역 실패 시**: 원본 한국어 프롬프트를 그대로 Qwen3-TTS에 전달합니다.

### 관련 코드

- 번역 함수: `_translate_voice_prompt()` in `services/video/scene_processing.py`
- 캐시: `_VOICE_PROMPT_CACHE` (프로세스 메모리, 재시작 시 초기화)
- 한글 감지: `[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]` 정규식

---

---

## 4. 음성 일관성 유지

현재 시스템은 **Voice Design** 프롬프트를 기반으로 일관된 목소리를 생성합니다.

### 동작 원리

`voice_design_prompt`와 `voice_seed`(프리셋 지정 또는 해시 기반)를 사용하여 모든 씬에서 동일한 음성 특성을 유지합니다. 사양 문제로 인해 참조 음성 기반의 Cloning 기능은 지원하지 않습니다.

### 우선순위

음성 설정은 다음 순서로 결정됩니다 (높은 것이 우선):

| 순위 | 소스 | 설명 |
|------|------|------|
| 1 | Per-scene `voice_design_prompt` | 개별 씬에 직접 지정된 음성 디자인 |
| 2 | Global `voice_design_prompt` | VideoRequest 레벨 음성 디자인 |
| 3 | System Default | 기본 설정값 |

---

## 6. RenderPreset TTS 필드

`render_presets` 테이블에 TTS 설정이 저장됩니다.

### DB 컬럼

| 컬럼 | 타입 | 제약 조건 | 설명 |
|------|------|----------|------|
| `tts_engine` | `String(20)` | CHECK: `'qwen'` 또는 NULL | TTS 엔진 (현재 qwen만 허용) |
| `voice_design_prompt` | `Text` | nullable | 음성 스타일 설명 텍스트 |
| `voice_ref_audio_url` | `Text` | nullable | (Deprecated) 참조 음성 URL |

### 마이그레이션

- 파일: `alembic/versions/e6f7a8b9c0d1_render_preset_tts_columns.py`
- CHECK constraint: `ck_render_presets_tts_engine`
- 시스템 프리셋 자동 설정: `UPDATE render_presets SET tts_engine = 'qwen' WHERE is_system = true`

### Pydantic 스키마

`RenderPresetCreate`, `RenderPresetUpdate`, `RenderPresetRead` 모두 다음 필드를 포함합니다:

```python
tts_engine: str | None = None
voice_design_prompt: str | None = None
```

---

## 7. Frontend UI

### RenderSettingsPanel

`frontend/app/components/video/RenderSettingsPanel.tsx`의 **AI Voice Style** 섹션에서 설정합니다.

| UI 요소 | 필드 | 설명 |
|---------|------|------|
| 목소리 스타일 입력 | `voiceDesignPrompt` | 텍스트로 음성 스타일 설명 |
| 배속 슬라이더 | `speedMultiplier` | TTS 포함 전체 배속 조절 |

### RenderPresetsTab

`frontend/app/manage/tabs/RenderPresetsTab.tsx`에서 프리셋으로 저장/불러오기가 가능합니다.

---

## 8. 후방 호환성

### Edge-TTS 마이그레이션

Edge-TTS는 완전히 제거되었으며, 기존 데이터는 자동으로 Qwen으로 변환됩니다.

**Backend (schemas.py)** - `VideoRequest`의 `model_validator`가 요청 시점에 자동 변환:

```python
@model_validator(mode="before")
@classmethod
def _migrate_edge_to_qwen(cls, values):
    if isinstance(values, dict) and values.get("tts_engine") == "edge":
        values["tts_engine"] = "qwen"
    return values
```

**Frontend (Zustand persist merge)** - localStorage에 저장된 `ttsEngine: "edge"` 값은 Zustand의 persist merge 단계에서 `"qwen"`으로 변환됩니다.

**TTSEngine Enum**:

```python
class TTSEngine(str, Enum):
    EDGE = "edge"    # 후방 호환용 (실제 사용 불가)
    QWEN = "qwen"    # 유일한 활성 엔진
```

---

## 9. 모델 로딩

### Lifespan 프리로딩

서버 시작 시 `main.py`의 lifespan에서 모델을 미리 로드합니다.

```python
# main.py lifespan()
try:
    from services.video.scene_processing import get_qwen_model
    get_qwen_model()
except Exception as e:
    logger.warning(f"[TTS] Qwen preload failed (will retry on first request): {e}")
```

### 글로벌 싱글톤

`get_qwen_model()` 함수는 모델을 글로벌 변수 `_QWEN_MODEL`에 캐시합니다. 한 번 로드되면 프로세스 종료까지 유지됩니다.

---

## 10. 트러블슈팅

### 모델 로드 실패

**증상**: 서버 시작 시 `[TTS] Qwen preload failed` 로그

**원인**: 모델 파일 미다운로드, 메모리 부족, 의존성 미설치

**대응**:
- 서버는 정상 기동됨 (non-blocking 프리로딩)
- 첫 TTS 요청 시 `get_qwen_model()`이 재시도
- 모델 다운로드 확인: `python -c "from qwen_tts import Qwen3TTSModel"`

### TTS 생성 실패

**증상**: `TTS generation error (Qwen)` 로그

**대응**:
- `generate_tts()`가 `(False, 0.0)` 반환
- 해당 씬은 `anullsrc` (FFmpeg 무음 소스)로 대체
- 영상 렌더링은 정상 진행됨

### 한국어 번역 실패

**증상**: `[TTS] Voice prompt translation failed` 로그

**원인**: Gemini API 키 미설정, API 할당량 초과, 네트워크 오류

**대응**: 원본 한국어 프롬프트가 그대로 Qwen3-TTS에 전달됩니다.

### 렌더링 속도 저하

**증상**: 8씬 이상 스토리보드에서 렌더링이 느림

**원인**: TTS 생성이 CPU-heavy 작업

**대응**:
- MPS 디바이스 사용 권장 (Apple Silicon)
- `TTS_DEVICE=mps` 환경 변수 설정
- 씬 수를 줄이거나 배속을 높여 대응

### MPS 가속 미작동

**증상**: `torch.backends.mps.is_available()`이 `False` 반환

**원인**: macOS 버전이 낮거나 PyTorch 설치 문제

**대응**: CPU 모드로 자동 전환되지만 속도가 느려질 수 있습니다.

### 빈 스크립트 씬

**증상**: `Scene {i}: empty script, skipping TTS` 로그

**대응**: 정상 동작. 스크립트가 비어 있는 씬은 TTS를 건너뛰고 무음 처리됩니다.

### 수동 검증

```bash
cd backend && uv run python verify_qwen.py
```

성공 시 `test_qwen_out.mp3` 파일이 생성됩니다.

---

## 11. 환경 변수 요약

`.env` 파일에 추가할 수 있는 TTS 관련 환경 변수:

```bash
# TTS 모델 (기본값 사용 권장)
TTS_MODEL_NAME=Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign

# 디바이스 설정 (auto 권장)
TTS_DEVICE=auto

# Attention 구현체 (sdpa 권장, eager보다 2-3x 빠름)
TTS_ATTN_IMPLEMENTATION=sdpa

# 생성 파라미터 (음성 품질/일관성 조절)
TTS_TEMPERATURE=0.7         # 낮을수록 일관된 음성 (0.5~1.0)
TTS_TOP_P=0.9               # Nucleus sampling (0.8~1.0)
TTS_REPETITION_PENALTY=1.1  # 반복 억제 (1.0~1.3)

# Gemini API (한국어 번역에 필요)
GEMINI_API_KEY=your_api_key_here
```

---

## 12. 관련 파일 목록

| 파일 | 역할 |
|------|------|
| `backend/config.py` | TTS 설정 SSOT |
| `backend/main.py` | Lifespan 모델 프리로딩 |
| `backend/services/video/scene_processing.py` | TTS 생성 핵심 로직 |
| `backend/services/video/builder.py` | VideoBuilder 파이프라인 |
| `backend/services/video/utils.py` | `clean_script_for_tts()` 텍스트 정제 |
| `backend/schemas.py` | `TTSEngine`, `VideoRequest`, `VideoScene` 스키마 |
| `backend/models/render_preset.py` | RenderPreset TTS 컬럼 정의 |
| `backend/alembic/versions/e6f7a8b9c0d1_*` | TTS 컬럼 마이그레이션 |
| `frontend/.../RenderSettingsPanel.tsx` | AI Voice Style UI |
| `frontend/.../RenderPresetsTab.tsx` | 프리셋 관리 UI |

---

**최종 업데이트**: 2026-02-02
