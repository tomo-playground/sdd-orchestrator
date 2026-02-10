# API Specification - Domain API (v3.2)

Tags, Keywords, ControlNet, LoRA, Avatar, Assets, Prompt, SD, Characters 관련 API 명세입니다.

> 메인 문서: [REST_API.md](./REST_API.md) | Analytics & Admin: [REST_API_ANALYTICS.md](./REST_API_ANALYTICS.md)

---

## 목차

1. [Tags & Classification](#-tags--classification-태그-분류-시스템) - 태그 분류
2. [Keywords](#-keywords-키워드-관리) - 키워드 관리
3. [ControlNet & IP-Adapter](#-controlnet--ip-adapter) - ControlNet
4. [LoRA Management](#-lora-management) - LoRA 관리
5. [Avatar](#-avatar-아바타-관리) - 아바타 관리
6. [Assets](#-assets-에셋-관리) - 에셋 관리
7. [Prompt](#-prompt-프롬프트-처리) - 프롬프트 처리
8. [Stable Diffusion](#-stable-diffusion-sd-webui-프록시) - SD WebUI 프록시
9. [Characters](#-characters-캐릭터-관리) - 캐릭터 관리

---

## Tags & Classification (태그 분류 시스템)

### `POST /tags/classify`
태그를 DB -> Rule -> Danbooru -> LLM 순으로 자동 분류합니다.

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

## Keywords (키워드 관리)

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

## ControlNet & IP-Adapter

### `GET /controlnet/status`
ControlNet 사용 가능 여부와 모델 목록을 조회합니다.

**Response:**
```json
{
  "available": true,
  "models": ["control_v11p_sd15_openpose", "ip-adapter-plus-face_sd15"],
  "pose_references": ["standing", "sitting"]
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

## LoRA Management

### `GET /loras`
등록된 LoRA 목록을 조회합니다.

**Response:**
```json
[
  {
    "id": 1,
    "name": "detail_slider",
    "optimal_weight": 0.5,
    "calibration_score": 85,
    "is_multi_character_capable": false,
    "multi_char_weight_scale": null,
    "multi_char_trigger_prompt": null
  }
]
```

- `is_multi_character_capable`: 2인 동시 출연 시 사용 가능 여부
- `multi_char_weight_scale`: 멀티캐릭터 씬에서 LoRA weight 축소 비율 (예: `0.70` = 70%)
- `multi_char_trigger_prompt`: 멀티캐릭터 전용 호출 프롬프트 (nullable)

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

## Avatar (아바타 관리)

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

## Assets (에셋 관리)

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

## Prompt (프롬프트 처리)

### `POST /prompt/compose`
V3 12-Layer 프롬프트를 합성합니다.

**Request:**
```json
{
  "character_id": 8,
  "character_b_id": null,
  "scene_id": 42,
  "context_tags": {"expression": ["smile"], "camera": "upper_body"}
}
```

- `character_b_id`: (optional) 2인 동시 출연 시 두 번째 캐릭터 ID
- `scene_id`: (optional) 씬 컨텍스트 태그 자동 로드

**Response:**
```json
{
  "prompt": "masterpiece, best_quality, 1girl, ..., smile, upper_body",
  "layers": [...]
}
```

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

## Stable Diffusion (SD WebUI 프록시)

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

## Characters (캐릭터 관리)

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

## 참고 문서

- **메인 API (Core)**: [REST_API.md](./REST_API.md) - Storyboard, Scene, Video, Presets, Storage, Projects, Groups, Render Presets, Voice Presets
- **Analytics & Admin API**: [REST_API_ANALYTICS.md](./REST_API_ANALYTICS.md) - Quality, Activity Logs, Evaluation, Admin
- **프롬프트 설계**: `docs/03_engineering/backend/PROMPT_SPEC_V2.md`
- **제품 스펙**: `docs/01_product/PRD.md`
- **로드맵**: `docs/01_product/ROADMAP.md`
- **개발 가이드**: `docs/guides/CONTRIBUTING.md`

---

**Last Updated:** 2026-02-11
**API Version:** v3.2
