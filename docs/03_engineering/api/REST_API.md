# API Specification (v3.1)

프론트엔드와 백엔드 간 데이터 통신을 위한 API 명세서입니다.

## 변경 이력

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v3.1 | 2026-02-02 | `render_presets`, `voice_presets`, `projects`, `groups` API 추가, 문서 분할 (Core / Domain / Analytics) |
| v3.0 | 2026-01-30 | V3 아키텍처: Storyboard-Centric 전환, generation-logs->activity-logs, Characters V3 relational tags, Admin/Assets 라우터 추가 |
| v2.2 | 2026-01-28 | Keywords Service 리팩토링 및 패키지 구조 반영, Character DB 필드 확장 반영 |
| v2.1 | 2026-01-27 | Characters API, Quality API, Evaluation API 추가 |

## v3.1 주요 변경

- **Projects/Groups API** (`/projects`, `/groups`): 프로젝트-그룹 계층 구조, Cascading Config 지원
- **Render Presets API** (`/render-presets`): 렌더링 프리셋 CRUD (TTS, BGM, 레이아웃 등 일괄 관리)
- **Voice Presets API** (`/voice-presets`): 음성 프리셋 CRUD, VoiceDesign 미리듣기, 음성 파일 업로드
- **문서 분할**: REST_API.md (Core) + REST_API_DOMAIN.md + REST_API_ANALYTICS.md

---

## 목차

### Core API (이 문서)
1. [Storyboard](#-storyboard) - AI 스토리보드 생성
2. [Scene](#-scene-이미지-생성검증) - 이미지 생성 및 검증
3. [Video](#-video-영상-렌더링) - 영상 렌더링
4. [Presets](#-presets-프리셋-템플릿) - 스토리보드 프리셋
5. [Storage](#-storage-저장소-관리) - 저장소 관리
6. [Projects & Groups](#-projects--groups) - 프로젝트/그룹 관리 (NEW)
7. [Render Presets](#-render-presets-렌더링-프리셋) - 렌더링 프리셋 (NEW)
8. [Voice Presets](#-voice-presets-음성-프리셋) - 음성 프리셋 (NEW)
9. [공통 사항](#-공통-사항) - 에러 처리 및 상태 코드

### Domain API -> [REST_API_DOMAIN.md](./REST_API_DOMAIN.md)
- Tags & Classification, Keywords, ControlNet & IP-Adapter, LoRA Management
- Avatar, Assets, Prompt, Stable Diffusion, Characters

### Analytics & Admin API -> [REST_API_ANALYTICS.md](./REST_API_ANALYTICS.md)
- Quality, Activity Logs, Evaluation, Admin

---

## Storyboard

> v3.0: Storyboard -> Scene -> CharacterAction 계층 구조. 라우터 prefix: `/storyboards`

### `POST /storyboards/create`
AI (Gemini)를 사용하여 스토리보드를 생성합니다.

**Request:**
```json
{
  "topic": "string",
  "duration": 10,
  "style": "Anime",
  "language": "Korean",
  "structure": "Monologue",
  "actor_a_gender": "female"
}
```

**Response:**
```json
{
  "scenes": [
    {
      "scene_id": 1,
      "script": "나레이션 텍스트",
      "speaker": "Narrator",
      "duration": 3.0,
      "image_prompt": "1girl, coffee shop...",
      "image_prompt_ko": "커피숍에 있는 여자..."
    }
  ]
}
```

### `POST /storyboards`
스토리보드와 씬을 DB에 저장합니다 (V3 데이터 영속화).

**Request:**
```json
{
  "title": "커피숍 일상",
  "description": "카페에서의 하루",
  "default_character_id": 1,
  "default_style_profile_id": 1,
  "default_caption": "좋아요 6만개\n15분 전",
  "scenes": [
    {
      "scene_id": 1,
      "script": "나레이션 텍스트",
      "image_url": "/outputs/images/scene_001.png",
      "width": 512,
      "height": 768,
      "tags": [{"tag_id": 10, "weight": 1.0}],
      "character_actions": [
        {"character_id": 1, "tag_id": 5, "weight": 1.0}
      ]
    }
  ]
}
```

**Response:**
```json
{"status": "success", "storyboard_id": 1}
```

### `PUT /storyboards/{storyboard_id}`
기존 스토리보드를 업데이트합니다 (씬 전체 교체).

**Request:** `POST /storyboards`와 동일 형식

**Response:** Storyboard 전체 객체 (id, title, description, scenes, video_url, recent_videos, created_at, updated_at 포함)

> **동작**: 기존 씬을 모두 삭제 후 새 씬으로 교체 (orphaned media_assets 자동 정리).
> Title은 200자로 자동 truncate됩니다.

### `GET /storyboards`
저장된 스토리보드 목록을 조회합니다.

**Response:**
```json
[
  {
    "id": 1,
    "title": "커피숍 일상",
    "description": "카페에서의 하루",
    "created_at": "2026-01-30T12:00:00",
    "updated_at": "2026-01-30T12:00:00"
  }
]
```

---

## Scene (이미지 생성/검증)

### `POST /scene/generate`
Stable Diffusion을 사용하여 씬 이미지를 생성합니다.

**Request:**
```json
{
  "prompt": "1girl, coffee shop, anime style",
  "negative_prompt": "bad quality, blurry",
  "steps": 24,
  "cfg_scale": 7.0,
  "sampler_name": "DPM++ 2M Karras",
  "seed": -1,
  "width": 512,
  "height": 512,
  "clip_skip": 2,
  "enable_hr": false,
  "hr_scale": 1.5,
  "hr_upscaler": "Latent",
  "hr_second_pass_steps": 10,
  "denoising_strength": 0.25
}
```

**Response:**
```json
{
  "image": "base64_encoded_string..."
}
```

### `POST /image/store`
생성된 이미지를 서버에 저장합니다.

**Request:**
```json
{
  "image_b64": "data:image/png;base64,..."
}
```

**Response:**
```json
{
  "url": "http://localhost:8000/outputs/images/stored/scene_abc123.png"
}
```

### `POST /scene/validate_image`
이미지 품질 및 프롬프트 일치도를 검증합니다.

**Request:**
```json
{
  "image_b64": "data:image/png;base64,...",
  "prompt": "1girl, coffee shop",
  "mode": "wd14"
}
```
- `mode`: `"wd14"` | `"gemini"` | `"both"`

**Response:**
```json
{
  "valid": true,
  "tags": ["1girl", "coffee", "indoor"],
  "score": 0.85
}
```

---

## Video (영상 렌더링)

### `POST /video/create`
씬들을 조합하여 최종 비디오를 생성합니다.

**Request:**
```json
{
  "scenes": [
    {
      "image_url": "http://localhost:8000/outputs/images/stored/scene_001.png",
      "script": "나레이션 텍스트",
      "speaker": "Narrator",
      "duration": 3.0
    }
  ],
  "bgm_file": "bgm_chill.mp3 | random",
  "width": 1080,
  "height": 1080,
  "layout_style": "post",
  "ken_burns_preset": "zoom_in_center",
  "ken_burns_intensity": 1.0,
  "narrator_voice": "ko-KR-SunHiNeural",
  "speed_multiplier": 1.0,
  "include_scene_text": true,
  "scene_text_font": "NanumGothic.ttf",
  "overlay_settings": {
    "channel_name": "daily_shorts",
    "avatar_key": "daily_shorts",
    "likes_count": "12.5k",
    "posted_time": "2분 전",
    "caption": "Amazing video! #shorts",
    "frame_style": "overlay_minimal.png",
    "avatar_file": null
  },
  "post_card_settings": {
    "channel_name": "creator",
    "avatar_key": "creator",
    "caption": "Check out this video!"
  },
  "audio_ducking": true,
  "bgm_volume": 0.25,
  "ducking_threshold": 0.01
}
```

- `layout_style`: `"post"` | `"full"` (default: `"post"`)
- `bgm_file`: BGM 파일명 또는 `"random"` (backend에서 랜덤 선택)
- `ken_burns_preset`: Ken Burns 효과 프리셋 (default: `"none"`)
  - **기본**: `"none"`, `"zoom_in_center"`, `"zoom_out_center"`
  - **패닝**: `"pan_left"`, `"pan_right"`, `"pan_up"`, `"pan_down"`
  - **줌+패닝**: `"zoom_pan_left"`, `"zoom_pan_right"`
  - **세로 영상 최적화** (9:16 Full Layout):
    - `"pan_up_vertical"`, `"pan_down_vertical"`
    - `"zoom_in_bottom"`, `"zoom_in_top"`
    - `"pan_zoom_up"`, `"pan_zoom_down"`
  - **랜덤**: `"random"`
- `ken_burns_intensity`: 효과 강도 0.5~2.0 (default: `1.0`)

**Response:**
```json
{
  "video_url": "http://localhost:8000/outputs/videos/my_shorts_20240115_143022.mp4"
}
```

### `POST /video/delete`
비디오 파일을 삭제합니다. Request: `{"filename": "my_shorts_20240115_143022.mp4"}` / Response: `{"ok": true, "deleted": true}`

### `GET /video/exists`
비디오 파일 존재 여부를 확인합니다. Query: `filename` (required) / Response: `{"exists": true}`

---

## Presets (프리셋 템플릿)

### `GET /presets`
사용 가능한 모든 스토리보드 프리셋 목록을 조회합니다.

**Response:**
```json
{
  "presets": [
    {
      "id": "monologue",
      "name": "Monologue",
      "name_ko": "독백",
      "description": "Single narrator storytelling",
      "sample_topics": ["topic1", "topic2"],
      "default_duration": 10,
      "default_style": "Anime",
      "default_language": "Korean"
    }
  ]
}
```

### `GET /presets/{preset_id}`
특정 프리셋의 상세 정보를 조회합니다. `GET /presets` 항목에 `structure`, `template`, `extra_fields` 추가.

### `GET /presets/{preset_id}/topics`
프리셋의 샘플 토픽 목록을 조회합니다. `{"topics": ["topic1", "topic2", ...]}`

---

## Storage (저장소 관리)

### `GET /storage/stats`
저장소 사용량 통계를 조회합니다.

**Response:**
```json
{
  "videos": { "count": 15, "size_mb": 234.5 },
  "images": { "count": 120, "size_mb": 45.2 },
  "cache": { "count": 50, "size_mb": 12.3 },
  "avatars": { "count": 10, "size_mb": 2.1 },
  "candidates": { "count": 30, "size_mb": 8.7 },
  "total_mb": 302.8
}
```

### `POST /storage/cleanup`
저장소 정리를 실행합니다.

**Request:**
```json
{
  "cleanup_videos": true,
  "video_max_age_days": 7,
  "cleanup_cache": true,
  "cache_max_age_seconds": null,
  "cleanup_test_folders": true,
  "cleanup_candidates": false,
  "dry_run": false
}
```

**Response:**
```json
{
  "deleted_count": 25,
  "freed_mb": 150.3,
  "details": {
    "videos": 5,
    "cache": 15,
    "test_folders": 5
  }
}
```

### `POST /storage/cleanup/preview`
정리될 파일 목록을 미리 확인합니다. `/storage/cleanup`과 동일 파라미터 (Query Parameters), dry_run=true로 동작.

---

## Projects & Groups

> v3.1: 프로젝트-그룹 계층 구조. Cascading Config 지원 (Project < Group < Storyboard).

### Projects (`/projects`)

#### `GET /projects`
프로젝트 목록을 조회합니다.

**Response:**
```json
[
  {
    "id": 1,
    "name": "일상 쇼츠",
    "description": "일상 테마 쇼츠 시리즈",
    "handle": "daily_shorts",
    "avatar_url": null,
    "avatar_key": "daily_shorts",
    "render_preset_id": 1,
    "default_character_id": 1,
    "default_style_profile_id": 1,
    "created_at": "2026-02-01T12:00:00"
  }
]
```

#### `POST /projects`
프로젝트를 생성합니다.

**Request:**
```json
{
  "name": "일상 쇼츠",
  "description": "일상 테마 쇼츠 시리즈",
  "handle": "daily_shorts",
  "avatar_key": "daily_shorts",
  "render_preset_id": 1,
  "default_character_id": 1,
  "default_style_profile_id": 1
}
```

**Response:** (201 Created) `GET /projects` 단일 항목과 동일

#### `GET /projects/{project_id}`
프로젝트 상세 정보를 조회합니다 (groups 포함).

**Response:** `GET /projects` 단일 항목과 동일 (groups join loaded)

#### `PUT /projects/{project_id}`
프로젝트를 수정합니다 (부분 업데이트 지원).

**Request:**
```json
{
  "name": "일상 쇼츠 (수정)",
  "render_preset_id": 2
}
```

**Response:** `GET /projects` 단일 항목과 동일

#### `DELETE /projects/{project_id}`
프로젝트를 삭제합니다.

**Response:**
```json
{"status": "deleted", "id": 1}
```

> **주의**: 하위 그룹이 존재하면 409 Conflict 반환.

#### `GET /projects/{project_id}/effective-config`
Cascading Config를 조회합니다 (Project 레벨 resolve).

**Response:**
```json
{
  "render_preset_id": 1,
  "default_character_id": 1,
  "default_style_profile_id": 1,
  "render_preset": { "id": 1, "name": "기본 프리셋", "..." : "..." },
  "sources": {
    "render_preset_id": "project",
    "default_character_id": "project"
  }
}
```

### Groups (`/groups`)

#### `GET /groups`
그룹 목록을 조회합니다.

**Query Parameters:**
- `project_id`: int (optional) - 특정 프로젝트의 그룹만 필터

**Response:**
```json
[
  {
    "id": 1,
    "project_id": 1,
    "name": "시즌 1",
    "description": "첫 번째 시즌",
    "render_preset_id": null,
    "default_character_id": null,
    "default_style_profile_id": null,
    "render_preset": null,
    "created_at": "2026-02-01T12:00:00"
  }
]
```

#### `POST /groups`
그룹을 생성합니다.

**Request:**
```json
{
  "project_id": 1,
  "name": "시즌 1",
  "description": "첫 번째 시즌",
  "render_preset_id": null,
  "default_character_id": null,
  "default_style_profile_id": null
}
```

**Response:** (201 Created) `GET /groups` 단일 항목과 동일

#### `GET /groups/{group_id}`
그룹 상세 정보를 조회합니다 (render_preset join loaded).

**Response:** `GET /groups` 단일 항목과 동일

#### `PUT /groups/{group_id}`
그룹을 수정합니다 (부분 업데이트 지원).

**Request:**
```json
{
  "name": "시즌 1 (수정)",
  "render_preset_id": 2
}
```

**Response:** `GET /groups` 단일 항목과 동일

#### `DELETE /groups/{group_id}`
그룹을 삭제합니다.

**Response:**
```json
{"status": "deleted", "id": 1}
```

> **주의**: 하위 스토리보드가 존재하면 409 Conflict 반환.

#### `GET /groups/{group_id}/effective-config`
Cascading Config를 조회합니다 (Project < Group 레벨 resolve).

**Response:**
```json
{
  "render_preset_id": 2,
  "default_character_id": 1,
  "default_style_profile_id": 1,
  "render_preset": { "id": 2, "name": "그룹 프리셋", "..." : "..." },
  "sources": {
    "render_preset_id": "group",
    "default_character_id": "project"
  }
}
```

---

## Render Presets (렌더링 프리셋)

> v3.1: 렌더링 설정 (TTS, BGM, 레이아웃, Ken Burns 등)을 프리셋으로 관리.

### `GET /render-presets`
렌더링 프리셋 목록을 조회합니다.

**Query Parameters:**
- `project_id`: int (optional) - 지정 시 해당 프로젝트 전용 + 글로벌 프리셋 반환, 미지정 시 글로벌만

**Response:**
```json
[
  {
    "id": 1,
    "name": "기본 프리셋",
    "description": "표준 렌더링 설정",
    "is_system": true,
    "project_id": null,
    "narrator_voice": "ko-KR-SunHiNeural",
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
    "tts_engine": "edge",
    "voice_design_prompt": null,
    "voice_ref_audio_url": null,
    "voice_preset_id": null,
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

## 공통 사항

### Base URL
- Development: `http://localhost:8000`
- Static Files: `/outputs/` (videos, images), `/assets/` (audio, fonts)

### Error Response
```json
{
  "detail": "Error message here"
}
```

### HTTP Status Codes
| Code | Description |
|------|-------------|
| 200 | 성공 |
| 201 | 리소스 생성 성공 |
| 400 | 잘못된 요청 (Invalid input) |
| 404 | 리소스 없음 |
| 409 | 충돌 (Conflict) - 하위 리소스 존재 시 삭제 불가 등 |
| 500 | 서버 내부 오류 |
| 502 | 외부 서비스 연결 오류 (SD WebUI 등) |

### Danbooru 태그 표준 (중요)

**모든 태그는 언더바(_) 형식을 사용합니다. 공백 형식 절대 금지.**
- 올바른 예: `["brown_hair", "looking_at_viewer", "cowboy_shot"]`
- 잘못된 예: `["brown hair", "looking at viewer"]`
- 적용 범위: DB 저장, API 요청/응답, 프롬프트 생성, WD14 검증
- 예외: 하이픈 태그 유지 (`close-up`), 복합어는 언더바 연결 (`light_brown_hair`)

---

## 참고 문서

| 문서 | 경로 |
|------|------|
| Domain API | [REST_API_DOMAIN.md](./REST_API_DOMAIN.md) |
| Analytics & Admin API | [REST_API_ANALYTICS.md](./REST_API_ANALYTICS.md) |
| 프롬프트 설계 | `docs/03_engineering/backend/PROMPT_SPEC_V2.md` |
| 제품 스펙 | `docs/01_product/PRD.md` |
| 로드맵 | `docs/01_product/ROADMAP.md` |
| 개발 가이드 | `docs/guides/CONTRIBUTING.md` |

---

**Last Updated:** 2026-02-02
**API Version:** v3.1
**Backend Version:** FastAPI 0.109+
**Database:** PostgreSQL 14+ (v3.1)
