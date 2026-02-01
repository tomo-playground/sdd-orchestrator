# API Specification (v3.0)

프론트엔드와 백엔드 간 데이터 통신을 위한 API 명세서입니다.

## 📝 변경 이력

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v3.0 | 2026-01-30 | V3 아키텍처: Storyboard-Centric 전환, generation-logs→activity-logs, Characters V3 relational tags, Admin/Assets 라우터 추가 |
| v2.2 | 2026-01-28 | Keywords Service 리팩토링 및 패키지 구조 반영, Character DB 필드 확장 반영 |
| v2.1 | 2026-01-27 | Characters API, Quality API, Evaluation API 추가 |

## 🚀 v3.0 주요 변경

- **Storyboard-Centric 전환**: Storyboard → Scene → CharacterAction 계층 구조
- **Activity Logs** (`/activity-logs`): generation-logs → activity-logs 통합 (생성+즐겨찾기)
- **Characters V3**: identity_tags/clothing_tags 배열 → V3 relational tags (character_tags 테이블)
- **Admin API** (`/admin`): DB 관리, 캐시 리프레시
- **Assets API** (`/assets`): 오버레이 프레임 관리

---

## 📑 목차

1. [🎬 Storyboard](#-storyboard) - AI 스토리보드 생성
2. [🖼️ Scene](#️-scene-이미지-생성검증) - 이미지 생성 및 검증
3. [🚀 Video](#-video-영상-렌더링) - 영상 렌더링
4. [📋 Presets](#-presets-프리셋-템플릿) - 스토리보드 프리셋
5. [🗑️ Storage](#️-storage-저장소-관리) - 저장소 관리
6. [🏷️ Tags & Classification](#️-tags--classification-태그-분류-시스템) - 태그 분류
7. [🧠 Keywords](#-keywords-키워드-관리) - 키워드 관리
8. [🤖 ControlNet & IP-Adapter](#-controlnet--ip-adapter) - ControlNet
9. [🧬 LoRA Management](#-lora-management) - LoRA 관리
10. [👤 Avatar](#-avatar-아바타-관리) - 아바타 관리
11. [🎵 Assets](#-assets-에셋-관리) - 에셋 관리
12. [✏️ Prompt](#️-prompt-프롬프트-처리) - 프롬프트 처리
13. [🎨 Stable Diffusion](#-stable-diffusion-sd-webui-프록시) - SD WebUI 프록시
14. [👥 Characters](#-characters-캐릭터-관리) - 캐릭터 관리 (New in v2.1)
15. [📊 Quality](#-quality-품질-검증-자동화) - 품질 검증
16. [📈 Activity Logs](#-activity-logs-활동-로그-분석) - 활동 로그 분석
17. [🧪 Evaluation](#-evaluation-프롬프트-모드-비교) - 프롬프트 모드 비교
18. [🔧 Admin](#-admin-관리) - DB 관리 및 캐시
19. [📌 공통 사항](#-공통-사항) - 에러 처리 및 상태 코드

---

## 🎬 Storyboard

> v3.0: Storyboard → Scene → CharacterAction 계층 구조. 라우터 prefix: `/storyboards`

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

**Request:**
```json
{
  "title": "커피숍 일상 (수정)",
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
{
  "id": 1,
  "title": "커피숍 일상 (수정)",
  "description": "카페에서의 하루",
  "default_character_id": 1,
  "default_style_profile_id": 1,
  "video_url": null,
  "recent_videos": [],
  "created_at": "2026-01-30T12:00:00",
  "updated_at": "2026-01-31T15:30:00",
  "scenes": [...]
}
```

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

**Response:** (v3.1: object array 형식)
```json
{
  "fonts": [
    {"name": "NanumGothic.ttf"},
    {"name": "NanumMyeongjo.ttf"},
    {"name": "Pretendard.otf"}
  ]
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

## 👥 Characters (캐릭터 관리)

### `GET /characters`
등록된 캐릭터 목록을 조회합니다.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Midoriya Izuku",
    "description": "Hero Academia protagonist",
    "gender": "male",
    "tags": [
      {"tag_id": 1, "name": "1boy", "is_permanent": true, "weight": 1.0},
      {"tag_id": 2, "name": "green_hair", "is_permanent": true, "weight": 1.0}
    ],
    "loras": [{"lora_id": 5, "weight": 0.7}],
    "custom_base_prompt": "1boy, midoriya_izuku, green_hair, freckles",
    "custom_negative_prompt": "EasyNegative",
    "prompt_mode": "lora",
    "ip_adapter_weight": 0.5,
    "ip_adapter_model": "ip-adapter-plus_sd15",
    "preview_image_url": "/assets/references/Midoriya.png"
  }
]
```

### `GET /characters/{character_id}`
특정 캐릭터의 정보를 조회합니다 (V3 relational tags + LoRA 메타데이터 포함).

**Response:** `GET /characters` 단일 항목과 동일

### `GET /characters/{character_id}/full`
`GET /{character_id}`의 별칭 (프론트엔드 호환성 유지).

### `POST /characters`
새 캐릭터를 생성합니다.

**Request:**
```json
{
  "name": "New Character",
  "description": "Character description",
  "gender": "female",
  "tags": [
    {"tag_id": 1, "weight": 1.0, "is_permanent": true},
    {"tag_id": 15, "weight": 1.0, "is_permanent": false}
  ],
  "loras": [{"lora_id": 5, "weight": 0.7}],
  "custom_base_prompt": "1girl, long_hair",
  "custom_negative_prompt": "EasyNegative",
  "prompt_mode": "auto",
  "ip_adapter_weight": 0.5
}
```

- `tags[].is_permanent`: `true` = identity 태그, `false` = clothing 태그
- Legacy `identity_tags`/`clothing_tags` (Integer 배열)도 호환 지원

**Response:** (201 Created) - `GET /characters/{id}` 형식과 동일

### `PUT /characters/{character_id}`
캐릭터 정보를 수정합니다 (부분 업데이트 지원).

**Request:**
```json
{
  "name": "Updated Name",
  "tags": [
    {"tag_id": 1, "weight": 1.0, "is_permanent": true},
    {"tag_id": 20, "weight": 0.8, "is_permanent": false}
  ],
  "custom_base_prompt": "1girl, updated_prompt",
  "prompt_mode": "standard"
}
```

- `tags` 전달 시 기존 태그 전체 교체 (DELETE + INSERT)

**Response:** `GET /characters/{id}` 형식과 동일

### `DELETE /characters/{character_id}`
캐릭터를 삭제합니다.

**Response:**
```json
{
  "ok": true,
  "deleted_id": 10
}
```

### `POST /characters/{character_id}/regenerate-reference`
캐릭터의 참조 이미지를 재생성합니다.

**Response:**
```json
{
  "success": true,
  "image_path": "/assets/references/Character_Name.png",
  "timestamp": "2026-01-27T12:34:56"
}
```

### `POST /characters/suggest-tags`
Base Prompt에서 태그를 자동 추출하여 카테고리별로 제안합니다 (Phase 6-4.24).

**Request:**
```json
{
  "base_prompt": "1girl, brown_hair, school_uniform, solo"
}
```

**Response:**
```json
{
  "identity": [
    {"tag_id": 1, "name": "1girl", "group_name": "subject"},
    {"tag_id": 5, "name": "brown_hair", "group_name": "hair_color"},
    {"tag_id": 8, "name": "solo", "group_name": "subject"}
  ],
  "clothing": [
    {"tag_id": 15, "name": "school_uniform", "group_name": "clothing"}
  ],
  "style": [],
  "expression": []
}
```

---

## 📊 Quality (품질 검증 자동화)

### `POST /quality/batch-validate`
프로젝트의 모든 씬을 배치로 검증하고 품질 점수를 저장합니다 (Phase 5-4-1).

**Request:**
```json
{
  "scenes": [
    {
      "scene_id": 1,
      "image_url": "/outputs/images/scene_1.png",
      "prompt": "1girl, coffee_shop, sitting"
    },
    {
      "scene_id": 2,
      "image_url": "/outputs/images/scene_2.png",
      "prompt": "1girl, park, walking"
    }
  ]
}
```

**Response:**
```json
{
  "total": 10,
  "validated": 9,
  "average_match_rate": 0.82,
  "scores": [
    {
      "scene_id": 1,
      "match_rate": 0.85,
      "matched_tags": ["1girl", "sitting", "indoors"],
      "missing_tags": ["coffee_shop"],
      "status": "excellent"
    },
    {
      "scene_id": 2,
      "match_rate": 0.78,
      "matched_tags": ["1girl", "walking", "outdoors"],
      "missing_tags": [],
      "status": "good"
    }
  ]
}
```

### `GET /quality/summary`
프로젝트의 품질 요약 통계를 조회합니다.

**Response:**
```json
{
  "total_scenes": 10,
  "average_match_rate": 0.82,
  "excellent_count": 6,
  "good_count": 2,
  "poor_count": 2,
  "scores": [
    {"scene_id": 1, "match_rate": 0.85, "status": "excellent"},
    {"scene_id": 2, "match_rate": 0.78, "status": "good"}
  ]
}
```

### `GET /quality/alerts`
품질 기준 미달 씬 목록을 조회합니다.

**Query Parameters:**
- `threshold`: 경고 기준 Match Rate (default: 0.7)

**Response:**
```json
{
  "total_alerts": 2,
  "threshold": 0.7,
  "alerts": [
    {
      "scene_id": 5,
      "match_rate": 0.55,
      "missing_tags": ["classroom", "sitting"],
      "status": "poor"
    },
    {
      "scene_id": 8,
      "match_rate": 0.62,
      "missing_tags": ["park"],
      "status": "poor"
    }
  ]
}
```

---

## 📈 Activity Logs (활동 로그 분석)

> v3.0: `generation-logs` → `activity-logs`로 통합 (생성 이력 + 즐겨찾기)

### `POST /activity-logs`
이미지 생성 메타데이터를 로깅합니다.

**Request:**
```json
{
  "scene_id": 1,
  "prompt": "1girl, smiling, classroom, ...",
  "tags_used": ["1girl", "smiling", "classroom"],
  "sd_params": { "steps": 20, "cfg_scale": 7, "sampler": "DPM++ 2M Karras" },
  "match_rate": 0.85,
  "seed": 12345,
  "status": "success",
  "image_url": "/outputs/images/scene_0.png"
}
```

**Response:**
```json
{ "id": 1, "scene_id": 1, "status": "success", "match_rate": 0.85 }
```

### `GET /activity-logs`
활동 로그 목록을 조회합니다.

**Query Parameters:**
- `status`: `success`, `fail`
- `limit`: 최대 반환 개수 (default: 100)

### `PATCH /activity-logs/{id}/status`
로그 상태를 수정합니다 (UI에서 마킹).

### `DELETE /activity-logs/{id}`
활동 로그를 삭제합니다.

### `GET /activity-logs/analyze/patterns`
태그 패턴 성공/실패 통계를 제공합니다.

### `GET /activity-logs/suggest-conflict-rules`
패턴 분석 기반 충돌 규칙을 제안합니다.

### `POST /activity-logs/apply-conflict-rules`
제안된 충돌 규칙을 DB에 적용합니다.

### `GET /activity-logs/success-combinations`
성공률이 높은 태그 조합을 추출합니다.

---

## 🧪 Evaluation (프롬프트 모드 비교)

### `GET /evaluation/test-prompts`
테스트용 프롬프트 목록을 조회합니다.

**Response:**
```json
{
  "test_prompts": [
    {
      "id": 1,
      "name": "Simple Portrait",
      "base_prompt": "1girl, long_hair",
      "scene_prompt": "standing, looking_at_viewer"
    },
    {
      "id": 2,
      "name": "Complex Action",
      "base_prompt": "1boy, short_hair",
      "scene_prompt": "running, dynamic_pose, motion_blur"
    }
  ]
}
```

### `POST /evaluation/run`
Mode A/B 비교 평가를 실행합니다.

**Request:**
```json
{
  "test_prompt_ids": [1, 2, 3],
  "mode_a": "standard",
  "mode_b": "lora",
  "samples_per_mode": 3
}
```

**Response:**
```json
{
  "run_id": "eval_20260127_123456",
  "total_tests": 3,
  "status": "running"
}
```

### `GET /evaluation/results/{run_id}`
평가 실행 결과를 조회합니다.

**Response:**
```json
{
  "run_id": "eval_20260127_123456",
  "status": "completed",
  "results": [
    {
      "test_id": 1,
      "mode_a_score": 0.85,
      "mode_b_score": 0.92,
      "winner": "mode_b",
      "samples": [...]
    }
  ]
}
```

### `GET /evaluation/summary`
전체 평가 요약 통계를 조회합니다.

**Response:**
```json
{
  "total_runs": 10,
  "mode_a_wins": 3,
  "mode_b_wins": 7,
  "avg_mode_a_score": 0.82,
  "avg_mode_b_score": 0.88
}
```

---

## 🔧 Admin (관리)

> v3.0: DB 마이그레이션 및 캐시 관리 엔드포인트

### `POST /admin/migrate-tag-rules`
하드코딩된 태그 충돌 규칙을 DB `tag_rules` 테이블로 마이그레이션합니다.

**Response:**
```json
{
  "success": true,
  "added": ["crying <-> laughing", "sitting <-> standing"],
  "skipped": ["sad <-> happy (already exists)"],
  "errors": [],
  "total_added": 2,
  "total_skipped": 1,
  "total_errors": 0
}
```

### `POST /admin/migrate-category-rules`
카테고리 기반 충돌 규칙을 DB로 마이그레이션합니다 (hair_length, camera 등).

**Response:** `/admin/migrate-tag-rules`와 동일 형식

### `POST /admin/refresh-caches`
모든 인메모리 캐시를 DB에서 리프레시합니다.

**Response:**
```json
{
  "success": true,
  "message": "All caches refreshed successfully"
}
```

대상 캐시: `TagCategoryCache`, `TagFilterCache`, `TagAliasCache`, `TagRuleCache`

### `GET /admin/tags/deprecated`
비활성화된 태그 목록을 조회합니다.

**Response:**
```json
{
  "total": 2,
  "tags": [
    {
      "id": 9118,
      "name": "room",
      "category": "scene",
      "deprecated_reason": "Not in Danbooru dataset (0 posts)",
      "replacement": {
        "id": 148,
        "name": "indoors",
        "category": "scene"
      },
      "created_at": "2026-01-30T16:43:30Z",
      "updated_at": "2026-01-30T16:43:44Z"
    }
  ]
}
```

### `PUT /admin/tags/{tag_id}/deprecate`
태그를 비활성화하고 대체 태그를 지정합니다.

**Request Body:**
```json
{
  "deprecated_reason": "Not in Danbooru dataset (0 posts)",
  "replacement_tag_id": 148
}
```

**Response:**
```json
{
  "success": true,
  "tag": {
    "id": 9118,
    "name": "room",
    "is_active": false,
    "deprecated_reason": "Not in Danbooru dataset (0 posts)",
    "replacement_tag_id": 148
  }
}
```

### `PUT /admin/tags/{tag_id}/activate`
비활성화된 태그를 재활성화합니다.

**Response:**
```json
{
  "success": true,
  "tag": {
    "id": 9118,
    "name": "room",
    "is_active": true
  }
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
| 201 | 리소스 생성 성공 |
| 400 | 잘못된 요청 (Invalid input) |
| 404 | 리소스 없음 |
| 500 | 서버 내부 오류 |
| 502 | 외부 서비스 연결 오류 (SD WebUI 등) |

### Danbooru 태그 표준 (중요)

**모든 태그는 언더바(_) 형식을 사용합니다. 공백 형식 절대 금지.**

**올바른 예시:**
```json
["brown_hair", "looking_at_viewer", "cowboy_shot", "school_uniform"]
```

**잘못된 예시:**
```json
["brown hair", "looking at viewer", "cowboy shot", "school uniform"]
```

**적용 범위:**
- DB 저장 (tags 테이블, tag_effectiveness 테이블)
- API 요청/응답 (JSON 포맷)
- 프롬프트 생성 (`/prompt/rewrite`, `/storyboard/create`)
- WD14 검증 결과

**예외:**
- 하이픈 태그는 유지: `close-up`, `full-body`
- 복합어 태그는 언더바로 연결: `light_brown_hair`, `school_uniform`

---

## 📚 참고 문서

- **프롬프트 설계**: `docs/specs/PROMPT_SPEC.md` - 프롬프트 우선순위 및 조합 규칙
- **제품 스펙**: `docs/PRD.md` - 제품 요구사항 및 완료 기준
- **로드맵**: `docs/ROADMAP.md` - 개발 계획 및 완료 이력
- **개발 가이드**: `docs/CONTRIBUTING.md` - 코딩 컨벤션 및 Sub Agents 관리

---

## 🔧 개발 환경 설정

### 필수 사항
1. **Stable Diffusion WebUI** 실행 (`--api` 옵션 필수)
2. **ControlNet Extension** 설치
3. **IP-Adapter Models** 다운로드
4. **PostgreSQL** 데이터베이스 설정
5. **환경 변수** 설정 (`backend/.env`)

### 환경 변수 예시
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/shorts_db
GEMINI_API_KEY=your_gemini_api_key
SD_WEBUI_URL=http://127.0.0.1:7860
```

---

## 🐛 문제 해결

### SD WebUI 연결 오류 (502)
- SD WebUI가 `--api` 옵션으로 실행 중인지 확인
- `SD_WEBUI_URL` 환경 변수 확인
- 방화벽 설정 확인

### 태그 검증 실패
- WD14 Tagger 모델 다운로드 확인
- Danbooru 태그 표준 준수 (언더바 형식)
- `tags` 테이블 데이터 확인

### Activity Log 저장 실패
- PostgreSQL 연결 확인
- `activity_logs` 테이블 마이그레이션 확인

---

**Last Updated:** 2026-01-31
**API Version:** v3.1
**Backend Version:** FastAPI 0.109+
**Database:** PostgreSQL 14+ (v3.1)