# API Specification (v3.5)

프론트엔드와 백엔드 간 데이터 통신을 위한 API 명세서입니다.

## 변경 이력

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v3.5 | 2026-02-07 | Creative Engine API 추가 (`/lab/creative/sessions`, `/lab/creative/agent-presets`) - AI 멀티 에이전트 토론 기반 창작 |
| v3.4 | 2026-02-07 | Video 비동기 렌더링 API 추가 (`/video/create-async`, `/video/progress/{task_id}`), Style Profile Ownership 설계 노트 |
| v3.3 | 2026-02-07 | Music Presets API 추가 (Stable Audio Open AI BGM), `render_presets` 응답에 `bgm_mode`/`music_preset_id` 추가 |
| v3.2 | 2026-02-06 | `render_presets` 응답에서 `voice_preset_id` 제거, `projects`/`effective-config` 응답에서 `character_id` 제거 |
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
8. [Voice Presets](#-voice-presets-음성-프리셋) - 음성 프리셋
9. [Music Presets](#-music-presets-음악-프리셋) - 음악 프리셋 (NEW)
10. [Creative Engine](#-creative-engine-ai-창작-엔진) - AI 멀티 에이전트 토론 (NEW)
11. [공통 사항](#-공통-사항) - 에러 처리 및 상태 코드

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
  "character_id": 1,
  "style_profile_id": 1,
  "caption": "좋아요 6만개\n15분 전",
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

### `POST /video/create-async`
비동기 영상 생성 (SSE 진행률 스트리밍). 요청 body는 `/video/create`와 동일합니다.

**Request:** `VideoRequest` (`POST /video/create`와 동일)

**Response (202 Accepted):**
```json
{
  "task_id": "abc123def456"
}
```

> 반환된 `task_id`로 `/video/progress/{task_id}`를 구독하여 진행 상황을 확인합니다.

### `GET /video/progress/{task_id}`
SSE(Server-Sent Events) 스트림으로 렌더링 진행 상황을 실시간 전달합니다.

**Response:** `text/event-stream`

**Event Payload (`RenderProgressEvent`):**
```json
{
  "task_id": "abc123def456",
  "stage": "process_scenes",
  "percent": 25,
  "stage_detail": "Scene 3/10 TTS",
  "encode_percent": 0,
  "current_scene": 3,
  "total_scenes": 10,
  "video_url": null,
  "media_asset_id": null,
  "render_history_id": null,
  "error": null
}
```

**Stages (순서):**
`queued` -> `setup_avatars` -> `process_scenes` -> `calculate_durations` -> `prepare_bgm` -> `build_filters` -> `encode` -> `upload` -> `completed`

**완료/실패 이벤트:**
- `completed` 이벤트: `video_url`, `media_asset_id`, `render_history_id` 포함
- `failed` 이벤트: `error` 메시지 포함

**Keep-alive:** 15초 주기 comment (`": keep-alive\n\n"`)

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

## Storage (저장소 및 에셋 관리)

에셋 파일의 물리적 저장 및 DB 메타데이터 관리를 담당합니다.

### `GET /storage/assets`
등록된 미디어 에셋 목록을 조회합니다 (owner_type: scene, character 등).

### `DELETE /storage/assets/{asset_id}`
에셋과 물리적 파일을 삭제합니다.


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

> **Style Profile Ownership**: Style Profile은 Group-level 설정 (`GroupConfig.style_profile_id`).
> Storyboard에서는 읽기 전용으로 표시만 하며, 변경은 GroupConfig를 통해서만 가능.
> Backend 이미지 생성 시 `resolve_effective_config(group.project, group)`로 cascade 조회.

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
    "style_profile_id": 1,
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
  "style_profile_id": 1
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
  "style_profile_id": 1,
  "render_preset": { "id": 1, "name": "기본 프리셋", "..." : "..." },
  "sources": {
    "render_preset_id": "project",
    "style_profile_id": "project"
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
    "style_profile_id": null,
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
  "style_profile_id": null
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
  "style_profile_id": 1,
  "narrator_voice_preset_id": 1,
  "render_preset": { "id": 2, "name": "그룹 프리셋", "..." : "..." },
  "sources": {
    "render_preset_id": "group",
    "style_profile_id": "project",
    "narrator_voice_preset_id": "group"
  }
}
```

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

> v3.3: Stable Audio Open 기반 AI BGM 프리셋 관리. 프롬프트 → 음악 생성/미리듣기/저장.

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

## Creative Engine (AI 창작 엔진)

> v3.5: AI 멀티 에이전트 토론 기반 창작 시스템. 여러 AI 에이전트가 토론(debate)을 통해 시나리오 등의 창작물을 생성합니다.
> 라우터 prefix: `/lab/creative`

### Sessions (창작 세션)

#### `POST /lab/creative/sessions`
새 창작 세션을 생성합니다.

**Request:**
```json
{
  "task_type": "scenario",
  "objective": "카페에서 벌어지는 로맨스 에피소드",
  "evaluation_criteria": {"originality": 0.3, "coherence": 0.4, "emotion": 0.3},
  "character_id": 1,
  "context": {"genre": "romance", "mood": "warm"},
  "agent_config": [
    {"preset_id": 1, "role_override": "romantic scenario expert"},
    {"preset_id": 2, "role_override": null}
  ],
  "max_rounds": 3
}
```

- `task_type`: `"scenario"` (default) - 창작 과제 유형
- `evaluation_criteria`: 평가 기준 가중치 (optional)
- `agent_config`: 에이전트 프리셋 구성 (optional, 미지정 시 시스템 기본값)
- `max_rounds`: 최대 토론 라운드 수 (default: `3`)

**Response:** `CreativeSessionResponse`

#### `GET /lab/creative/sessions`
세션 목록을 조회합니다.

**Query Parameters:**
- `task_type`: string (optional) - 과제 유형 필터
- `limit`: int (optional) - 최대 반환 개수
- `offset`: int (optional) - 페이지 오프셋

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "task_type": "scenario",
      "objective": "카페에서 벌어지는 로맨스 에피소드",
      "status": "in_progress",
      "current_round": 2,
      "max_rounds": 3,
      "created_at": "2026-02-07T12:00:00",
      "updated_at": "2026-02-07T12:05:00"
    }
  ],
  "total": 1
}
```

#### `GET /lab/creative/sessions/{id}`
세션 상세 정보를 조회합니다.

**Response:** `CreativeSessionResponse`

#### `POST /lab/creative/sessions/{id}/run-round`
단일 토론 라운드를 실행합니다. 각 에이전트가 순서대로 의견을 제시합니다.

**Request:**
```json
{
  "feedback": "더 극적인 전개를 추가해주세요"
}
```

- `feedback`: string (optional) - 사용자 피드백 (다음 라운드에 반영)

**Response:** `CreativeSessionResponse`

#### `POST /lab/creative/sessions/{id}/run-debate`
전체 토론 루프를 실행합니다. `max_rounds`까지 자동으로 라운드를 반복합니다.

**Response:** `CreativeSessionResponse`

#### `POST /lab/creative/sessions/{id}/finalize`
토론을 종료하고 선택된 결과물을 확정합니다.

**Request:**
```json
{
  "selected_output": {
    "title": "카페 로맨스",
    "scenes": [
      {"script": "두 사람이 같은 책을 집어드는 순간...", "image_prompt": "..."}
    ]
  },
  "reason": "에이전트 2의 제안이 감성적 흐름이 가장 자연스러움"
}
```

- `selected_output`: dict (required) - 최종 선택된 창작 결과물
- `reason`: string (optional) - 선택 이유

**Response:** `CreativeSessionResponse`

#### `POST /lab/creative/sessions/{id}/send-to-studio`
확정된 창작 결과물을 Studio 스토리보드로 내보냅니다.

**Request:**
```json
{
  "storyboard_id": null,
  "group_id": 1
}
```

- `storyboard_id`: int (optional) - 기존 스토리보드에 덮어쓰기, null이면 신규 생성
- `group_id`: int (default: `1`) - 스토리보드가 속할 그룹

**Response:**
```json
{
  "storyboard_id": 42,
  "scenes_created": 5
}
```

#### `GET /lab/creative/sessions/{id}/timeline`
세션의 전체 트레이스 타임라인을 조회합니다. 디버깅 및 토론 과정 시각화에 사용됩니다.

**Response:**
```json
{
  "session": { "...": "CreativeSessionResponse" },
  "rounds": [
    {
      "round_number": 1,
      "started_at": "2026-02-07T12:01:00",
      "completed_at": "2026-02-07T12:02:30"
    }
  ],
  "traces": [
    {
      "id": 1,
      "round_number": 1,
      "agent_preset_id": 1,
      "agent_role": "romantic scenario expert",
      "input_prompt": "...",
      "output_text": "...",
      "model_provider": "gemini",
      "model_name": "gemini-2.0-flash",
      "tokens_used": 1250,
      "latency_ms": 3200,
      "created_at": "2026-02-07T12:01:15"
    }
  ]
}
```

#### `DELETE /lab/creative/sessions/{id}`
세션을 소프트 삭제합니다.

**Response:**
```json
{"ok": true}
```

### Agent Presets (에이전트 프리셋)

#### `GET /lab/creative/agent-presets`
활성 에이전트 프리셋 목록을 조회합니다.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Creative Writer",
    "role_description": "감성적이고 문학적인 시나리오를 작성하는 에이전트",
    "system_prompt": "You are a creative writer specializing in emotional storytelling...",
    "model_provider": "gemini",
    "model_name": "gemini-2.0-flash",
    "temperature": 0.9,
    "is_system": true,
    "created_at": "2026-02-07T12:00:00"
  }
]
```

#### `POST /lab/creative/agent-presets`
에이전트 프리셋을 생성합니다.

**Request:**
```json
{
  "name": "Drama Critic",
  "role_description": "극적 구조와 갈등 요소를 분석하는 비평가 에이전트",
  "system_prompt": "You are a drama critic who analyzes narrative structure...",
  "model_provider": "gemini",
  "model_name": "gemini-2.0-flash",
  "temperature": 0.7
}
```

- `model_provider`: string (optional, default: `"gemini"`)
- `model_name`: string (optional, default: config에서 관리)
- `temperature`: float (optional, default: `0.9`)

**Response:** (200 OK) `GET /lab/creative/agent-presets` 단일 항목과 동일

#### `PUT /lab/creative/agent-presets/{id}`
에이전트 프리셋을 수정합니다 (비시스템 프리셋만 수정 가능).

**Request:**
```json
{
  "name": "Updated Critic",
  "role_description": "수정된 역할 설명",
  "system_prompt": "Updated system prompt...",
  "model_provider": "gemini",
  "model_name": "gemini-2.0-flash",
  "temperature": 0.8
}
```

**Response:** `GET /lab/creative/agent-presets` 단일 항목과 동일

> **주의**: `is_system: true`인 시스템 프리셋은 수정 불가 (400 Bad Request).

#### `DELETE /lab/creative/agent-presets/{id}`
에이전트 프리셋을 삭제합니다 (비시스템 프리셋만 삭제 가능).

**Response:**
```json
{"ok": true}
```

> **주의**: `is_system: true`인 시스템 프리셋은 삭제 불가 (400 Bad Request).

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

**Last Updated:** 2026-02-07
**API Version:** v3.5
**Backend Version:** FastAPI 0.109+
**Database:** PostgreSQL 14+ (v3.10)
