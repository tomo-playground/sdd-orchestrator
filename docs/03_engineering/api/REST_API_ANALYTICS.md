# API Specification - Analytics & Admin API (v3.1)

Quality, Activity Logs, Evaluation, Admin 관련 API 명세입니다.

> 메인 문서: [REST_API.md](./REST_API.md) | Domain API: [REST_API_DOMAIN.md](./REST_API_DOMAIN.md)

---

## 목차

1. [Quality](#-quality-품질-검증-자동화) - 품질 검증
2. [Activity Logs](#-activity-logs-활동-로그-분석) - 활동 로그 분석
3. [Evaluation](#-evaluation-프롬프트-모드-비교) - 프롬프트 모드 비교
4. [Admin](#-admin-관리) - 마이그레이션, 캐시, 태그 관리, Media GC

---

## Quality (품질 검증 자동화)

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

## Activity Logs (활동 로그 분석)

> v3.0: `generation-logs` -> `activity-logs`로 통합 (생성 이력 + 즐겨찾기)

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

## Evaluation (프롬프트 모드 비교)

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

## Admin (관리)

> v3.0+: DB 마이그레이션, 캐시, 태그 관리, 미디어 GC 엔드포인트

### 엔드포인트 분류

| 분류 | 엔드포인트 | Method | Manage UI |
|------|-----------|--------|-----------|
| **마이그레이션** | `/admin/migrate-tag-rules` | POST | ❌ CLI 전용 |
| | `/admin/migrate-category-rules` | POST | ❌ DEPRECATED |
| **캐시** | `/admin/refresh-caches` | POST | ❌ CLI 전용 |
| **태그 관리** | `/admin/tags/deprecated` | GET | ✅ TagsTab |
| | `/admin/tags/{tag_id}/deprecate` | PUT | ❌ CLI 전용 |
| | `/admin/tags/{tag_id}/activate` | PUT | ✅ TagsTab |
| **Media GC** | `/admin/media-assets/orphans` | GET | ❌ CLI 전용 |
| | `/admin/media-assets/cleanup` | POST | ❌ CLI 전용 |
| | `/admin/media-assets/stats` | GET | ❌ CLI 전용 |

---

### 마이그레이션

#### `POST /admin/migrate-tag-rules`
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

#### `POST /admin/migrate-category-rules`
**DEPRECATED** (Phase 6-4.26): 카테고리 레벨 충돌 규칙 삭제됨. 태그 레벨 충돌(`/activity-logs/apply-conflict-rules`)을 사용.

---

### 캐시

#### `POST /admin/refresh-caches`
모든 인메모리 캐시를 DB에서 리프레시합니다.

**Response:**
```json
{
  "success": true,
  "message": "All caches refreshed successfully"
}
```

대상 캐시: `TagCategoryCache`, `TagFilterCache`, `TagAliasCache`, `TagRuleCache`, `LoRATriggerCache`

---

### 태그 관리

#### `GET /admin/tags/deprecated`
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

#### `PUT /admin/tags/{tag_id}/deprecate`
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

#### `PUT /admin/tags/{tag_id}/activate`
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

### Media Asset GC

> Phase 6-7: 고아 media_assets 감지 및 정리. 서비스: `backend/services/media_gc.py`

**감지 카테고리:**
- **Null Owner**: `owner_type IS NULL` + FK 미참조
- **Broken FK**: `owner_type` 존재하지만 owner 레코드 없음
- **Expired Temp**: `is_temp=True` + TTL 초과 (기본 24h, `MEDIA_ASSET_TEMP_TTL_SECONDS`)

#### `GET /admin/media-assets/orphans`
고아 미디어 에셋을 스캔합니다 (감지만, 삭제 없음).

**Response:**
```json
{
  "success": true,
  "null_owner": [
    {"id": 42, "storage_key": "voice-presets/previews/voice_abc.wav",
     "owner_type": null, "owner_id": null, "reason": "No owner reference"}
  ],
  "broken_fk": [],
  "expired_temp": [
    {"id": 55, "storage_key": "voice-presets/previews/voice_xyz.wav",
     "owner_type": "voice_preset_preview", "owner_id": null, "reason": "Temp asset expired (>24h)"}
  ],
  "total": 2
}
```

#### `POST /admin/media-assets/cleanup`
고아 및 만료 임시 에셋을 정리합니다.

**Query Parameters:**
- `dry_run`: bool (default: `true`) — `true`면 삭제 없이 리포트만 반환

**Response:**
```json
{
  "success": true,
  "orphans": {
    "deleted": 2,
    "storage_errors": [],
    "dry_run": false
  },
  "expired_temp": {
    "deleted": 1,
    "storage_errors": [],
    "dry_run": false
  },
  "total_deleted": 3
}
```

#### `GET /admin/media-assets/stats`
미디어 에셋 전체 통계를 조회합니다.

**Response:**
```json
{
  "success": true,
  "total_assets": 150,
  "temp_assets": 5,
  "null_owner_assets": 2,
  "orphan_count": 3,
  "by_owner_type": {
    "scene": 120,
    "voice_preset": 15,
    "voice_preset_preview": 10
  }
}
```

---

## 참고 문서

- **메인 API (Core)**: [REST_API.md](./REST_API.md) - Storyboard, Scene, Video, Presets, Storage, Projects, Groups, Render Presets, Voice Presets
- **Domain API**: [REST_API_DOMAIN.md](./REST_API_DOMAIN.md) - Tags, Keywords, ControlNet, LoRA, Avatar, Assets, Prompt, SD, Characters
- **프롬프트 설계**: `docs/03_engineering/backend/PROMPT_SPEC_V2.md`
- **제품 스펙**: `docs/01_product/PRD.md`
- **로드맵**: `docs/01_product/ROADMAP.md`
- **개발 가이드**: `docs/guides/CONTRIBUTING.md`

---

**Last Updated:** 2026-02-03
**API Version:** v3.1
