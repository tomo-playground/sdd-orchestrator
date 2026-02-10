# API Specification - Presets (Render / Voice / Music)

> REST_API.md에서 분할된 프리셋 API 명세입니다.

---

## Render Presets (렌더링 프리셋)

> v3.1: 렌더링 설정 (TTS, BGM, 레이아웃, Ken Burns 등)을 프리셋으로 관리.

### `GET /render-presets`
렌더링 프리셋 목록을 조회합니다 (글로벌 공통).

**Response:**
```json
[
  {
    "id": 1,
    "name": "기본 프리셋",
    "description": "표준 렌더링 설정",
    "is_system": true,
    "bgm_file": "bgm_chill.mp3",
    "bgm_volume": 0.25,
    "audio_ducking": true,
    "scene_text_font": "NanumGothic.ttf",
    "layout_style": "post",
    "frame_style": "overlay_minimal.png",
    "transition_type": null,
    "ken_burns_preset": "zoom_in_center",
    "ken_burns_intensity": 1.0,
    "speed_multiplier": 1.0,
    "created_at": "2026-02-01T12:00:00"
  }
]
```

### `GET /render-presets/{preset_id}`
렌더링 프리셋 상세 정보를 조회합니다.

**Response:** `GET /render-presets` 단일 항목과 동일

### `POST /render-presets`
렌더링 프리셋을 생성합니다. `is_system`은 항상 `false`로 설정됩니다.

**Request:** Response 필드 중 `id`, `is_system`, `created_at`을 제외한 모든 필드 (모두 optional, name만 required)

**Response:** (201 Created) `GET /render-presets` 단일 항목과 동일

### `PUT /render-presets/{preset_id}`
렌더링 프리셋을 수정합니다 (부분 업데이트 지원).

**Request:**
```json
{
  "name": "수정된 프리셋",
  "bgm_volume": 0.4
}
```

**Response:** `GET /render-presets` 단일 항목과 동일

### `DELETE /render-presets/{preset_id}`
렌더링 프리셋을 삭제합니다.

**Response:**
```json
{"status": "deleted", "id": 1}
```

---

## Voice Presets (음성 프리셋)

> v3.1: VoiceDesign 기반 음성 프리셋 관리. 생성/업로드/미리듣기 지원.

### `GET /voice-presets`
음성 프리셋 목록을 조회합니다.

**Query Parameters:**
- `project_id`: int (optional) - 지정 시 해당 프로젝트 전용 + 글로벌 프리셋 반환, 미지정 시 글로벌만

**Response:**
```json
[
  {
    "id": 1,
    "name": "차분한 여성",
    "description": "차분하고 부드러운 여성 목소리",
    "project_id": null,
    "source_type": "generated",
    "audio_url": "http://localhost:8000/storage/voice-presets/1/voice_1_abc123.wav",
    "voice_design_prompt": "calm, gentle female voice",
    "language": "korean",
    "sample_text": "안녕하세요, 이것은 테스트 음성입니다.",
    "is_system": false,
    "created_at": "2026-02-01T12:00:00"
  }
]
```

### `GET /voice-presets/{preset_id}`
음성 프리셋 상세 정보를 조회합니다.

**Response:** `GET /voice-presets` 단일 항목과 동일

### `POST /voice-presets`
음성 프리셋을 생성합니다 (source_type: `"generated"`).

**Request:**
```json
{
  "name": "차분한 여성",
  "description": "차분하고 부드러운 여성 목소리",
  "project_id": null,
  "source_type": "generated",
  "voice_design_prompt": "calm, gentle female voice",
  "language": "korean",
  "sample_text": "안녕하세요, 이것은 테스트 음성입니다."
}
```

**Response:** (201 Created) `GET /voice-presets` 단일 항목과 동일

### `PUT /voice-presets/{preset_id}`
음성 프리셋을 수정합니다 (name, description만 수정 가능).

**Request:**
```json
{
  "name": "차분한 여성 (수정)",
  "description": "수정된 설명"
}
```

**Response:** `GET /voice-presets` 단일 항목과 동일

### `DELETE /voice-presets/{preset_id}`
음성 프리셋을 삭제합니다. 연결된 MediaAsset과 Storage 파일도 함께 정리됩니다.

**Response:**
```json
{"status": "deleted", "id": 1}
```

### `POST /voice-presets/preview`
VoiceDesign 모델을 사용하여 미리듣기 음성을 생성합니다. 결과는 임시 MediaAsset으로 등록됩니다 (24시간 후 GC).

**Request:**
```json
{
  "voice_design_prompt": "calm, gentle female voice",
  "sample_text": "안녕하세요, 이것은 테스트 음성입니다.",
  "language": "korean"
}
```

**Response:**
```json
{
  "audio_url": "http://localhost:8000/storage/voice-presets/previews/voice_preview_abc123.wav",
  "temp_asset_id": 42
}
```

### `POST /voice-presets/upload`
음성 파일을 업로드하여 프리셋을 생성합니다 (source_type: `"uploaded"`).

**Request:** `multipart/form-data`
- `name`: string (required) - 프리셋 이름
- `file`: file (required) - 음성 파일 (wav, mp3, flac, ogg)
- `project_id`: int (optional)
- `description`: string (optional)
- `language`: string (default: `"korean"`)

**제한:**
- 허용 포맷: wav, mp3, flac, ogg
- 최대 파일 크기: config에서 관리 (`VOICE_PRESET_MAX_FILE_SIZE`)
- 최소/최대 오디오 길이: config에서 관리 (`VOICE_PRESET_MIN_DURATION`, `VOICE_PRESET_MAX_DURATION`)

**Response:** (201 Created) `GET /voice-presets` 단일 항목과 동일

### `POST /voice-presets/{preset_id}/attach-preview`
이전에 생성된 미리듣기 음성을 프리셋에 연결합니다. 임시 MediaAsset이 영구로 전환됩니다.

**Query Parameters:**
- `temp_asset_id`: int (required) - `/voice-presets/preview`에서 반환된 임시 에셋 ID

**Response:** `GET /voice-presets` 단일 항목과 동일

---

## Music Presets (음악 프리셋)

> v3.3: Stable Audio Open 기반 AI BGM 프리셋 관리. 프롬프트 -> 음악 생성/미리듣기/저장.

### `GET /music-presets`
음악 프리셋 목록을 조회합니다.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Lo-fi Chill",
    "description": "부드러운 로파이 배경음",
    "prompt": "ambient lo-fi hip hop, soft piano, chill beats",
    "duration": 30.0,
    "seed": 42,
    "audio_url": "http://localhost:8000/storage/music-presets/1/music_abc123.wav",
    "is_system": false,
    "created_at": "2026-02-07T12:00:00"
  }
]
```

### `GET /music-presets/{preset_id}`
음악 프리셋 상세 정보를 조회합니다.

**Response:** `GET /music-presets` 단일 항목과 동일

### `POST /music-presets`
음악 프리셋을 생성합니다 (메타데이터만, 음원은 preview + attach-preview로 연결).

**Request:**
```json
{
  "name": "Lo-fi Chill",
  "description": "부드러운 로파이 배경음",
  "prompt": "ambient lo-fi hip hop, soft piano, chill beats",
  "duration": 30.0,
  "seed": 42
}
```

**Response:** (201 Created) `GET /music-presets` 단일 항목과 동일

### `PUT /music-presets/{preset_id}`
음악 프리셋을 수정합니다.

**Request:**
```json
{
  "name": "수정된 이름",
  "description": "수정된 설명",
  "prompt": "new prompt",
  "duration": 20.0,
  "seed": 99
}
```

**Response:** `GET /music-presets` 단일 항목과 동일

### `DELETE /music-presets/{preset_id}`
음악 프리셋을 삭제합니다. 연결된 MediaAsset과 Storage 파일도 함께 정리됩니다.

**Response:**
```json
{"status": "deleted", "id": 1}
```

### `POST /music-presets/preview`
Stable Audio Open 모델을 사용하여 미리듣기 음악을 생성합니다. 결과는 임시 MediaAsset으로 등록됩니다.

**Request:**
```json
{
  "prompt": "ambient lo-fi hip hop, soft piano",
  "duration": 30.0,
  "seed": -1,
  "num_inference_steps": 100
}
```

**Response:**
```json
{
  "audio_url": "http://localhost:8000/storage/music-presets/previews/music_preview_abc123.wav",
  "temp_asset_id": 42,
  "seed": 1234567890
}
```

### `POST /music-presets/{preset_id}/attach-preview`
이전에 생성된 미리듣기 음악을 프리셋에 연결합니다. 임시 MediaAsset이 영구로 전환됩니다.

**Query Parameters:**
- `temp_asset_id`: int (required) - `/music-presets/preview`에서 반환된 임시 에셋 ID

**Response:** `GET /music-presets` 단일 항목과 동일

### `POST /music-presets/warmup`
SAO (Stable Audio Open) 모델을 수동으로 로딩합니다. 첫 preview 전에 호출하면 대기 시간을 줄일 수 있습니다.

**Response:**
```json
{"status": "ok", "message": "SAO model loaded"}
```

---

## 참고 문서

| 문서 | 경로 |
|------|------|
| Core API | [REST_API.md](./REST_API.md) |
| Domain API | [REST_API_DOMAIN.md](./REST_API_DOMAIN.md) |
| Creative Engine API | [REST_API_CREATIVE.md](./REST_API_CREATIVE.md) |
| Analytics & Admin API | [REST_API_ANALYTICS.md](./REST_API_ANALYTICS.md) |
