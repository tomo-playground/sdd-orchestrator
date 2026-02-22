# API Specification (v4.0)

프론트엔드와 백엔드 간 데이터 통신을 위한 API 명세서입니다.

## 변경 이력

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v4.0 | 2026-02-18 | 문서 전체 소스 기반 최신화: Storyboard GET/DELETE 추가, Video render-history/youtube-statuses 추가, Groups Config CRUD 추가, Storage build cleanup 추가, 신규 API 섹션 참조 추가 |
| v3.8 | 2026-02-13 | Storyboard Optimistic Locking (`version`), Partial Metadata Update (`PATCH`), Material Check (`/materials`), Scene Async Generation (`/scene/generate-async`) |
| v3.7 | 2026-02-11 | Multi-Character LoRA 지원 |
| v3.6 | 2026-02-10 | Storyboard Soft Delete, Scene 편집 엔드포인트, Video 유틸리티 |

---

## 목차

### Core API (이 문서)
1. [Storyboard](#storyboard) - AI 스토리보드 생성
2. [Scene](#scene-이미지-생성검증) - 이미지 생성 및 검증
3. [Video](#video-영상-렌더링) - 영상 렌더링
4. [Presets](#presets-프리셋-템플릿) - 스토리보드 프리셋
5. [Storage](#storage-저장소-관리) - 저장소 관리
6. [Projects & Groups](#projects--groups) - 프로젝트/그룹 관리
7. [공통 사항](#공통-사항) - 에러 처리 및 상태 코드

### 분할 문서
- **Presets API** (Render / Voice / Music) -> [REST_API_PRESETS.md](./REST_API_PRESETS.md)
- **Domain API** -> [REST_API_DOMAIN.md](./REST_API_DOMAIN.md) — Tags, Keywords, ControlNet, LoRA, Avatar, Assets, Backgrounds, Prompt, SD, Characters, Style Profiles, SD Models, Prompt Histories
- **Creative Engine API** -> [REST_API_CREATIVE.md](./REST_API_CREATIVE.md)
- **Analytics & Admin API** -> [REST_API_ANALYTICS.md](./REST_API_ANALYTICS.md) — Quality, Activity Logs, Gemini Edit Analytics, Admin, Settings, YouTube, Scripts, Memory

---

## Storyboard

> Storyboard -> Scene -> CharacterAction 계층 구조. 라우터 prefix: `/storyboards`

### `POST /storyboards/create`
AI (Gemini)를 사용하여 스토리보드를 생성합니다.

**Request:** `StoryboardRequest`
```json
{
  "topic": "string",
  "description": "optional description",
  "duration": 10,
  "style": "Anime",
  "language": "Korean",
  "structure": "Monologue",
  "actor_a_gender": "female",
  "group_id": null,
  "preset": "creator",
  "skip_stages": ["research", "concept", "production", "explain"],
  "references": ["https://example.com/reference"],
  "selected_concept": null
}
```

**Response:** Gemini 생성 결과 (scenes 배열)

### `POST /storyboards`
스토리보드와 씬을 DB에 저장합니다. `response_model=StoryboardSaveResponse`

**Request:** `StoryboardSave`
```json
{
  "title": "커피숍 일상",
  "description": "카페에서의 하루",
  "character_id": 1,
  "style_profile_id": 1,
  "caption": "좋아요 6만개\n15분 전",
  "duration": 10,
  "language": "Korean",
  "version": 1,
  "scenes": [
    {
      "scene_id": 1,
      "script": "나레이션 텍스트",
      "scene_mode": "single",
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

**Response:** `StoryboardSaveResponse`
```json
{"status": "success", "storyboard_id": 1, "version": 1}
```

### `GET /storyboards`
저장된 스토리보드 목록을 조회합니다. `response_model=PaginatedStoryboardList`

**Query Parameters:**
- `group_id`: int (optional) - 특정 그룹의 스토리보드만 필터
- `project_id`: int (optional) - 특정 프로젝트의 스토리보드만 필터
- `offset`: int (default: 0)
- `limit`: int (default: 50)

**Response:** `PaginatedStoryboardList`

### `GET /storyboards/{storyboard_id}`
스토리보드 상세 정보를 조회합니다. `response_model=StoryboardDetailResponse`

### `PUT /storyboards/{storyboard_id}`
기존 스토리보드를 업데이트합니다 (씬 전체 교체). `response_model=StoryboardSaveResponse`

**Request:** `StoryboardSave` (`POST /storyboards`와 동일 형식)

> **동작**: 기존 씬을 모두 삭제 후 새 씬으로 교체 (orphaned media_assets 자동 정리). Title은 200자로 자동 truncate.

### `PATCH /storyboards/{storyboard_id}/metadata`
스토리보드 메타데이터를 부분 업데이트합니다. Optimistic Locking을 위해 `version` 필드 필수. `response_model=StoryboardMetadataUpdateResponse`

**Request:** `StoryboardUpdate`
```json
{ "title": "새로운 제목", "version": 1 }
```

### `DELETE /storyboards/{storyboard_id}`
스토리보드를 Soft Delete합니다. `response_model=StatusResponse`

### `GET /storyboards/{storyboard_id}/materials`
스토리보드의 렌더링 준비 상태를 확인합니다. `response_model=MaterialsCheckResponse`

**Response:**
```json
{
  "storyboard_id": 1,
  "script": {"ready": true, "count": 10},
  "characters": {"ready": true, "count": 2},
  "voice": {"ready": true},
  "music": {"ready": false},
  "background": {"ready": true, "detail": "Optional"}
}
```

### `GET /storyboards/trash`
Soft Delete된 스토리보드 목록. `response_model=list[TrashedStoryboardItem]`

### `POST /storyboards/{storyboard_id}/restore`
Soft Delete된 스토리보드를 복원합니다. `response_model=StoryboardRestoreResponse`

### `DELETE /storyboards/{storyboard_id}/permanent`
스토리보드를 영구 삭제합니다 (복구 불가). `response_model=StatusResponse`

---

## Scene (이미지 생성/검증)

### `POST /scene/generate`
Stable Diffusion을 사용하여 씬 이미지를 생성합니다. `response_model=SceneGenerateResponse`

**Request:** `SceneGenerateRequest`
```json
{
  "prompt": "1girl, coffee shop, anime style",
  "negative_prompt": "bad quality, blurry",
  "steps": 24, "cfg_scale": 7.0,
  "sampler_name": "DPM++ 2M Karras",
  "seed": -1, "width": 512, "height": 768, "clip_skip": 2,
  "enable_hr": false, "hr_scale": 1.5, "hr_upscaler": "Latent",
  "character_id": 8, "character_b_id": null,
  "storyboard_id": 374,
  "prompt_pre_composed": false,
  "style_loras": []
}
```

**Response:** `SceneGenerateResponse`
```json
{
  "image": "base64_encoded_string...",
  "images": ["base64_1...", "base64_2..."],
  "scene_mode": "single",
  "controlnet_pose": "base64_or_null",
  "ip_adapter_reference": "base64_or_null",
  "warnings": ["unpinned tag: xyz"],
  "used_prompt": "flat_color, 1girl, cafe, indoors, <lora:flat_color:0.76>"
}
```

### `POST /scene/generate-batch`
여러 씬의 이미지를 한 번에 생성합니다. `response_model=BatchSceneResponse`

### `POST /image/store`
생성된 이미지를 서버에 저장합니다.

### `POST /scene/generate-async`
씬 이미지를 비동기로 생성합니다. **Response (202):** `{ "task_id": "scene_gen_abc123" }`

### `GET /scene/progress/{task_id}`
씬 생성 작업의 진행 상황을 조회합니다.

### `POST /scene/validate-and-auto-edit`
WD14 검증 + 조건부 Gemini 자동 편집.

### `POST /scene/edit-with-gemini`
Gemini를 사용하여 이미지 프롬프트를 수동 편집합니다.

### `POST /scene/suggest-edit`
Gemini가 프롬프트 개선안을 자동 제안합니다.

### `POST /scene/validate_image`
이미지 품질 및 프롬프트 일치도를 검증합니다. `mode`: `"wd14"` | `"gemini"` | `"both"`

---

## Video (영상 렌더링)

### `POST /video/create`
씬들을 조합하여 최종 비디오를 생성합니다 (동기). `response_model=VideoCreateResponse`

**Request:** `VideoRequest` — scenes, bgm_file, layout_style, ken_burns 등 포함

### `POST /video/create-async`
비동기 영상 생성 (SSE 진행률 스트리밍). `response_model=VideoCreateAccepted` (202)

### `GET /video/progress/{task_id}`
SSE(Server-Sent Events) 스트림으로 렌더링 진행 상황을 실시간 전달합니다.

**Stages:** `queued` -> `setup_avatars` -> `process_scenes` -> `calculate_durations` -> `prepare_bgm` -> `build_filters` -> `encode` -> `upload` -> `completed`

### `POST /video/delete`
비디오 파일을 삭제합니다. `response_model=VideoDeleteResponse`

### `GET /video/exists`
비디오 파일 존재 여부를 확인합니다. `response_model=VideoExistsResponse`

### `POST /video/youtube-statuses`
여러 비디오 URL의 YouTube 업로드 상태를 일괄 조회합니다. `response_model=YouTubeStatusesResponse`

**Request:** `YouTubeStatusesRequest`
```json
{ "video_urls": ["http://...video1.mp4", "http://...video2.mp4"] }
```

**Response:**
```json
{ "statuses": { "http://...video1.mp4": { "video_id": "abc123", "status": "public" } } }
```

### `GET /video/render-history`
렌더링 이력 목록을 조회합니다 (갤러리용, 최신순). `response_model=PaginatedRenderHistoryList`

**Query Parameters:**
- `project_id`: int (optional)
- `offset`: int (default: 0)
- `limit`: int (default: 12, max: 50)

### `GET /video/render-history-lookup`
video URL로 render_history_id를 조회합니다. `response_model=RenderHistoryLookupResponse`

**Query Parameters:** `video_url` (required)

### `GET /video/transitions`
사용 가능한 전환 효과 목록을 조회합니다. `response_model=TransitionsResponse`

### `POST /video/extract-caption`
텍스트에서 캡션을 LLM으로 추출합니다. `response_model=CaptionExtractResponse`

### `POST /video/extract-hashtags`
주제에서 해시태그 3개를 추출합니다. `response_model=HashtagExtractResponse`

---

## Presets (프리셋 템플릿)

### `GET /presets`
사용 가능한 모든 스토리보드 프리셋 목록을 조회합니다. `response_model=PresetListResponse`

### `GET /presets/{preset_id}`
특정 프리셋의 상세 정보를 조회합니다. `response_model=PresetDetailResponse`

### `GET /presets/{preset_id}/topics`
프리셋의 샘플 토픽 목록을 조회합니다. `response_model=PresetTopicsResponse`

---

## Storage (저장소 및 에셋 관리)

### `GET /storage/stats`
저장소 사용량 통계를 조회합니다 (videos, images, cache, build, shared 등).

### `POST /storage/cleanup`
저장소 정리를 실행합니다.

**Request:** `CleanupRequest`
```json
{
  "cleanup_videos": true,
  "video_max_age_days": 7,
  "cleanup_cache": true,
  "cache_max_age_seconds": null,
  "cleanup_build": true,
  "build_max_age_hours": 24,
  "cleanup_test_folders": true,
  "dry_run": false
}
```

### `POST /storage/cleanup/preview`
정리될 파일 목록을 미리 확인합니다 (Query Parameters, 항상 dry_run=true).

### `GET /storage/assets`
등록된 미디어 에셋 목록을 조회합니다.

### `DELETE /storage/assets/{asset_id}`
에셋과 물리적 파일을 삭제합니다.

---

## Projects & Groups

> 프로젝트-그룹 계층 구조. Cascading Config 지원 (Project < Group < Storyboard).

### Projects (`/projects`)

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/projects` | 프로젝트 목록 | `list[ProjectResponse]` |
| POST | `/projects` | 프로젝트 생성 (201) | `ProjectResponse` |
| GET | `/projects/{id}` | 프로젝트 상세 (groups 포함) | `ProjectResponse` |
| PUT | `/projects/{id}` | 프로젝트 수정 (부분 업데이트) | `ProjectResponse` |
| DELETE | `/projects/{id}` | 프로젝트 삭제 (하위 그룹 존재 시 409) | `StatusResponse` |
| GET | `/projects/{id}/effective-config` | Cascading Config 조회 | `EffectiveConfigResponse` |

### Groups (`/groups`)

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/groups` | 그룹 목록 (project_id 필터) | `list[GroupResponse]` |
| POST | `/groups` | 그룹 생성 (201, GroupConfig 자동 생성) | `GroupResponse` |
| GET | `/groups/{id}` | 그룹 상세 | `GroupResponse` |
| PUT | `/groups/{id}` | 그룹 수정 (부분 업데이트) | `GroupResponse` |
| DELETE | `/groups/{id}` | 그룹 삭제 (활성 스토리보드 존재 시 409) | `StatusResponse` |

### Group Config (`/groups/{group_id}/config`)

Group별 1:1 설정 관리. GroupConfig에는 render_preset_id, style_profile_id, narrator_voice_preset_id, SD 생성 설정 등이 포함됩니다.

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/groups/{id}/config` | GroupConfig 조회 (없으면 자동 생성) | `GroupConfigResponse` |
| PUT | `/groups/{id}/config` | GroupConfig 부분 업데이트 | `GroupConfigResponse` |

### `GET /groups/{group_id}/effective-config`
Cascading Config를 조회합니다 (Project < Group 레벨 resolve). `response_model=EffectiveConfigResponse`

**Response:**
```json
{
  "render_preset_id": 2,
  "style_profile_id": 1,
  "narrator_voice_preset_id": 1,
  "language": "Korean",
  "structure": "Monologue",
  "duration": 30,
  "sd_steps": 24,
  "sd_cfg_scale": 7.0,
  "sd_sampler_name": "DPM++ 2M Karras",
  "sd_clip_skip": 2,
  "channel_dna": null,
  "render_preset": { "id": 2, "name": "그룹 프리셋", "..." : "..." },
  "sources": {
    "render_preset_id": "group",
    "style_profile_id": "project",
    "narrator_voice_preset_id": "group"
  }
}
```

---

## Render Presets / Voice Presets / Music Presets -> [REST_API_PRESETS.md](./REST_API_PRESETS.md)

---

## 공통 사항

### Base URL
- Development: `http://localhost:8000`
- Static Files: `/outputs/` (videos, images), `/assets/` (audio, fonts)

### Error Response
```json
{ "detail": "Error message here" }
```

### HTTP Status Codes
| Code | Description |
|------|-------------|
| 200 | 성공 |
| 201 | 리소스 생성 성공 |
| 202 | 비동기 작업 접수 |
| 400 | 잘못된 요청 |
| 404 | 리소스 없음 |
| 409 | 충돌 (하위 리소스 존재 시 삭제 불가 등) |
| 500 | 서버 내부 오류 |
| 502 | 외부 서비스 연결 오류 (SD WebUI 등) |

### Danbooru 태그 표준
모든 태그는 언더바(_) 형식을 사용합니다. 공백 형식 절대 금지.

---

## 참고 문서

| 문서 | 경로 |
|------|------|
| Presets API | [REST_API_PRESETS.md](./REST_API_PRESETS.md) |
| Domain API | [REST_API_DOMAIN.md](./REST_API_DOMAIN.md) |
| Creative Engine API | [REST_API_CREATIVE.md](./REST_API_CREATIVE.md) |
| Analytics & Admin API | [REST_API_ANALYTICS.md](./REST_API_ANALYTICS.md) |

---

**Last Updated:** 2026-02-18
**API Version:** v4.0
**Backend Version:** FastAPI 0.109+
**Database:** PostgreSQL 14+
