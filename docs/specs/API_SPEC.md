# API Specification (v2.0)

프론트엔드와 백엔드 간 데이터 통신을 위한 API 명세서입니다.

---

## 🎬 Storyboard

### `POST /storyboard/create`
AI를 사용하여 스토리보드를 생성합니다.

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

---

## 🖼️ Scene (이미지 생성/검증)

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

## 🚀 Video (영상 렌더링)

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
  "project_name": "my_shorts",
  "bgm_file": "bgm_chill.mp3 | random",
  "width": 1080,
  "height": 1080,
  "layout_style": "post",
  "ken_burns_preset": "zoom_in_center",
  "ken_burns_intensity": 1.0,
  "narrator_voice": "ko-KR-SunHiNeural",
  "speed_multiplier": 1.0,
  "include_subtitles": true,
  "subtitle_font": "NanumGothic.ttf",
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
  - `"none"`, `"slow_zoom"`, `"zoom_in_center"`, `"zoom_out_center"`
  - `"pan_left"`, `"pan_right"`, `"pan_up"`, `"pan_down"`
  - `"zoom_pan_left"`, `"zoom_pan_right"`, `"random"`
- `ken_burns_intensity`: 효과 강도 0.5~2.0 (default: `1.0`)

**Response:**
```json
{
  "video_url": "http://localhost:8000/outputs/videos/my_shorts_20240115_143022.mp4"
}
```

### `POST /video/delete`
비디오 파일을 삭제합니다.

**Request:**
```json
{
  "filename": "my_shorts_20240115_143022.mp4"
}
```

**Response:**
```json
{
  "ok": true,
  "deleted": true
}
```

### `GET /video/exists`
비디오 파일 존재 여부를 확인합니다.

**Query Parameters:**
- `filename`: 확인할 파일명 (required)

**Response:**
```json
{
  "exists": true
}
```

---

## 📋 Presets (프리셋 템플릿)

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
특정 프리셋의 상세 정보를 조회합니다.

**Response:**
```json
{
  "id": "monologue",
  "name": "Monologue",
  "name_ko": "독백",
  "description": "Single narrator storytelling",
  "structure": "Monologue",
  "template": "create_storyboard.j2",
  "sample_topics": ["topic1", "topic2"],
  "default_duration": 10,
  "default_style": "Anime",
  "default_language": "Korean",
  "extra_fields": {}
}
```

### `GET /presets/{preset_id}/topics`
프리셋의 샘플 토픽 목록을 조회합니다.

**Response:**
```json
{
  "topics": ["오늘의 커피 한 잔", "비 오는 날의 감성", "..."]
}
```

---

## 🗑️ Storage (저장소 관리)

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
정리될 파일 목록을 미리 확인합니다 (dry_run 모드).

**Query Parameters:**
- `cleanup_videos`: bool (default: true)
- `video_max_age_days`: int (default: 7)
- `cleanup_cache`: bool (default: true)
- `cleanup_test_folders`: bool (default: true)
- `cleanup_candidates`: bool (default: false)

**Response:** `/storage/cleanup`과 동일 (dry_run=true)

---

## 🏷️ Tags & Classification (태그 분류 시스템)

### `POST /tags/classify`
태그를 DB → Rule → Danbooru → LLM 순으로 자동 분류합니다.

**Request:**
```json
{
  "tags": ["smile", "starry sky", "unknown_tag"]
}
```

**Response:**
```json
{
  "results": {
    "smile": { "group": "expression", "confidence": 1.0, "source": "db" },
    "starry sky": { "group": "time_weather", "confidence": 1.0, "source": "rule" },
    "unknown_tag": { "group": null, "confidence": 0.0, "source": "unknown" }
  },
  "classified": 2,
  "unknown": 1
}
```

### `GET /tags/pending`
분류 승인이 필요한 태그 목록을 조회합니다.

**Query Parameters:**
- `source`: "danbooru", "llm", "unknown" (optional)
- `max_confidence`: float (default: 0.9)

**Response:**
```json
{
  "tags": [
    {
      "id": 123,
      "name": "some_tag",
      "category": "scene",
      "group_name": "action",
      "classification_source": "danbooru",
      "classification_confidence": 0.6
    }
  ],
  "total": 1
}
```

### `POST /tags/approve-classification`
태그 분류를 승인하거나 수정합니다.

**Request:**
```json
{
  "tag_id": 123,
  "group_name": "pose",
  "category": "scene"
}
```

**Response:**
```json
{
  "ok": true,
  "tag": "some_tag",
  "group_name": "pose",
  "category": "scene"
}
```

### `POST /tags/migrate-patterns`
`CATEGORY_PATTERNS` 코드를 DB 규칙으로 마이그레이션합니다.

**Response:**
```json
{
  "ok": true,
  "rules_created": 677
}
```

---

## 🧠 Keywords (키워드 관리)

### `GET /keywords/suggestions`
새로운 키워드 제안 목록을 조회합니다.

**Query Parameters:**
- `min_count`: int (default: 3) - 최소 등장 횟수
- `limit`: int (default: 50) - 최대 반환 개수

**Response:**
```json
{
  "min_count": 3,
  "limit": 50,
  "suggestions": [
    { "tag": "coffee", "count": 15 },
    { "tag": "sunset", "count": 8 }
  ]
}
```

### `GET /keywords/categories`
키워드 카테고리 목록을 조회합니다.

**Response:**
```json
{
  "categories": {
    "character": ["1girl", "1boy", "couple"],
    "location": ["indoor", "outdoor", "cafe"],
    "style": ["anime", "realistic", "watercolor"]
  }
}
```

### `GET /keywords/rules`
태그 충돌/의존성 규칙 요약을 조회합니다.

**Response:**
```json
{
  "conflict_pairs_count": 57,
  "required_rules_count": 29
}
```

### `POST /keywords/validate`
태그 리스트의 충돌 및 의존성을 검증합니다.

**Request:**
```json
["long hair", "short hair", "twintails"]
```

**Response:**
```json
{
  "conflicts": [
    { "tags": ["long hair", "short hair"], "reason": "hair_length conflict" }
  ],
  "missing_dependencies": [
    { "tag": "twintails", "missing": "long hair" }
  ]
}
```

### `POST /keywords/approve`
제안된 키워드를 승인하여 카테고리에 추가합니다.

**Request:**
```json
{
  "tag": "coffee shop",
  "category": "location"
}
```

**Response:**
```json
{
  "ok": true,
  "tag": "coffee_shop",
  "category": "location"
}
```

### `POST /keywords/batch-approve`
태그를 일괄 승인합니다.

**Request:**
```json
{
  "tags": ["tag1", "tag2"],
  "min_confidence": 0.7
}
```

**Response:**
```json
{
  "ok": true,
  "approved_count": 2,
  "approved": ["tag1", "tag2"]
}
```

### `POST /keywords/sync-lora-triggers`
LoRA 트리거 워드를 태그 DB와 동기화합니다.

**Response:**
```json
{
  "summary": { "added_count": 5, "updated_count": 2 }
}
```

---

## 🤖 ControlNet & IP-Adapter

### `GET /controlnet/status`
ControlNet 사용 가능 여부와 모델 목록을 조회합니다.

**Response:**
```json
{
  "available": true,
          "models": ["control_v11p_sd15_openpose", "ip-adapter-plus-face_sd15"],  "pose_references": ["standing", "sitting"]
}
```

### `POST /controlnet/detect-pose`
이미지에서 포즈를 추출합니다.

**Request:**
```json
{
  "image_b64": "data:image/png;base64,..."
}
```

**Response:**
```json
{
  "pose_image": "data:image/png;base64,...",
  "success": true
}
```

### `POST /controlnet/suggest-pose`
태그를 기반으로 적절한 포즈 레퍼런스를 제안합니다.

**Request:**
```json
["standing", "waving"]
```

**Response:**
```json
{
  "suggested_pose": "waving",
  "available": true,
  "image_b64": "..."
}
```

### `GET /controlnet/ip-adapter/references`
IP-Adapter용 저장된 참조 이미지 목록을 조회합니다.

**Response:**
```json
{
  "references": ["char_a", "char_b"]
}
```

### `POST /controlnet/ip-adapter/reference`
캐릭터 참조 이미지를 등록합니다.

**Request:**
```json
{
  "character_key": "char_a",
  "image_b64": "..."
}
```

**Response:**
```json
{
  "success": true,
  "filename": "char_a.png"
}
```

---

## 🧬 LoRA Management

### `GET /loras`
등록된 LoRA 목록을 조회합니다.

**Response:**
```json
[
  {
    "id": 1,
    "name": "detail_slider",
    "optimal_weight": 0.5,
    "calibration_score": 85
  }
]
```

### `GET /loras/search-civitai`
Civitai에서 LoRA를 검색합니다.

**Query Parameters:**
- `query`: 검색어

**Response:**
```json
{
  "results": [
    {
      "civitai_id": 12345,
      "name": "Anime Lineart",
      "creator": "User1",
      "preview_image": "https://..."
    }
  ]
}
```

### `POST /loras/import-civitai/{civitai_id}`
Civitai 메타데이터를 사용하여 LoRA를 등록합니다.

**Response:**
```json
{
  "id": 2,
  "name": "anime_lineart",
  "trigger_words": ["lineart"]
}
```

### `POST /loras/{lora_id}/calibrate`
LoRA의 최적 가중치(optimal weight)를 자동으로 보정합니다.

**Response:**
```json
{
  "lora_name": "anime_lineart",
  "optimal_weight": 0.6,
  "calibration_score": 92,
  "lora_type": "style"
}
```

---

## 👤 Avatar (아바타 관리)

### `POST /avatar/regenerate`
아바타 이미지를 재생성합니다.

**Request:**
```json
{
  "avatar_key": "daily_shorts"
}
```

**Response:**
```json
{
  "filename": "avatar_daily_shorts.png"
}
```

### `POST /avatar/resolve`
아바타 파일 존재 여부를 확인합니다.

**Request:**
```json
{
  "avatar_key": "daily_shorts"
}
```

**Response:**
```json
{
  "filename": "avatar_daily_shorts.png"
}
```
- 존재하지 않으면 `filename: null`

---

## 🎵 Assets (에셋 관리)

### `GET /audio/list`
사용 가능한 BGM 파일 목록을 조회합니다.

**Response:**
```json
{
  "audios": [
    { "name": "bgm_chill.mp3", "url": "http://localhost:8000/assets/audio/bgm_chill.mp3" },
    { "name": "bgm_upbeat.mp3", "url": "http://localhost:8000/assets/audio/bgm_upbeat.mp3" }
  ]
}
```

### `GET /fonts/list`
사용 가능한 폰트 파일 목록을 조회합니다.

**Response:**
```json
{
  "fonts": ["NanumGothic.ttf", "NanumMyeongjo.ttf", "Pretendard.otf"]
}
```

### `GET /fonts/file/{filename}`
폰트 파일을 다운로드합니다 (브라우저 미리보기용).

**Response:** Font file (binary)

---

## ✏️ Prompt (프롬프트 처리)

### `POST /prompt/rewrite`
프롬프트를 스타일에 맞게 재작성합니다.

**Request:**
```json
{
  "base_prompt": "1girl, long hair",
  "scene_prompt": "drinking coffee at cafe",
  "style": "Anime",
  "mode": "compose"
}
```

**Response:**
```json
{
  "prompt": "1girl, long hair, drinking coffee, cafe interior, anime style, detailed"
}
```

### `POST /prompt/split`
예시 프롬프트를 분석하여 base/scene으로 분리합니다.

**Request:**
```json
{
  "example_prompt": "1girl, long hair, cafe, drinking coffee, anime style",
  "style": "Anime"
}
```

**Response:**
```json
{
  "base_prompt": "1girl, long hair, anime style",
  "scene_elements": ["cafe", "drinking coffee"]
}
```

---

## 🎨 Stable Diffusion (SD WebUI 프록시)

### `GET /sd/models`
사용 가능한 SD 모델 목록을 조회합니다.

**Response:**
```json
{
  "models": [
    { "title": "v1-5-pruned.safetensors", "model_name": "v1-5-pruned" },
    { "title": "animagine-xl.safetensors", "model_name": "animagine-xl" }
  ]
}
```

### `GET /sd/options`
현재 SD WebUI 설정을 조회합니다.

**Response:**
```json
{
  "options": { "sd_model_checkpoint": "animagine-xl.safetensors", "...": "..." },
  "model": "animagine-xl.safetensors"
}
```

### `POST /sd/options`
SD WebUI 모델을 변경합니다.

**Request:**
```json
{
  "sd_model_checkpoint": "animagine-xl.safetensors"
}
```

**Response:**
```json
{
  "ok": true,
  "model": "animagine-xl.safetensors"
}
```

### `GET /sd/loras`
사용 가능한 LoRA 목록을 조회합니다.

**Response:**
```json
{
  "loras": [
    { "name": "add_detail", "alias": "add_detail" },
    { "name": "anime_style", "alias": "anime_style" }
  ]
}
```

---

## 📌 공통 사항

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
| 400 | 잘못된 요청 (Invalid input) |
| 404 | 리소스 없음 |
| 500 | 서버 내부 오류 |
| 502 | 외부 서비스 연결 오류 (SD WebUI 등) |