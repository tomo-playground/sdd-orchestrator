# API Specification - Analytics & Admin API (v3.1)

Quality, Activity Logs, Evaluation, Admin 관련 API 명세입니다.

> 메인 문서: [REST_API.md](./REST_API.md) | Domain API: [REST_API_DOMAIN.md](./REST_API_DOMAIN.md)

---

## 목차

1. [Quality](#-quality-품질-검증-자동화) - 품질 검증
2. [Activity Logs](#-activity-logs-활동-로그-분석) - 활동 로그 분석
3. [Evaluation](#-evaluation-프롬프트-모드-비교) - 프롬프트 모드 비교
4. [Lab Experiments](#-lab-experiments-실험-및-분석) - 실험 및 분석 (Phase 1)
5. [Admin](#-admin-관리) - 마이그레이션, 캐시, 태그 관리, Media GC

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

## Lab Experiments (실험 및 분석)

> **Phase 1**: Lab 실험이 Studio와 동일한 V3 Prompt Engine + Style Profile 사용
> **통합**: Lab → Studio 워크플로우 (실험 → 검증 → 스토리보드 복사)

### 핵심 개념

**Lab의 역할**:
- **Tag Lab**: 개별 태그 조합의 렌더링 품질 실험
- **Scene Lab**: V3 Prompt Engine을 사용한 씬 구성 실험
- **Creative Lab**: 멀티 에이전트 협업 스토리보드 생성

**V3 Integration (Phase 1)**:
- 모든 Lab 실험은 **Group에 속함** (`group_id` 필수)
- V3 Prompt Builder 사용 (Character LoRA + Scene Tags + Style LoRAs)
- Group Config의 Style Profile 자동 적용 (Quality Tags + Negative Prompt)
- 실험 결과에 V3 메타데이터 저장 (`final_prompt`, `loras_applied`)

---

### `POST /lab/experiments/run`
Tag Lab/Scene Lab 단일 실험을 실행합니다 (V3 Prompt Engine 사용).

**Request:**
```json
{
  "experiment_type": "tag_render",  // "tag_render" or "scene_translate"
  "group_id": 1,  // Required: Lab 실험은 Group에 속함
  "character_id": 1,  // Optional: null이면 narrator 실험
  "target_tags": ["1girl", "smile", "school_uniform"],
  "negative_prompt": "worst quality, low quality",
  "sd_params": {
    "steps": 20,
    "cfg_scale": 7.0,
    "sampler": "DPM++ 2M Karras",
    "width": 512,
    "height": 768,
    "seed": -1
  },
  "scene_description": null,  // scene_translate 타입에서만 사용
  "notes": "Testing uniform rendering"
}
```

**Response:**
```json
{
  "id": 123,
  "batch_id": null,
  "experiment_type": "tag_render",
  "status": "completed",
  "group_id": 1,
  "character_id": 1,

  // Original prompt
  "prompt_used": "1girl, smile, school_uniform",
  "negative_prompt": "worst quality, low quality",
  "target_tags": ["1girl", "smile", "school_uniform"],

  // V3 Metadata (Phase 1)
  "final_prompt": "1girl, smile, school_uniform, <lora:character_lora:1.0>, <lora:anime_style:0.7>, masterpiece, best quality",
  "loras_applied": [
    {"name": "character_lora", "weight": 1.0, "source": "character"},
    {"name": "anime_style", "weight": 0.7, "source": "style"}
  ],

  // Results
  "image_url": "http://localhost:9000/lab/experiments/123.png",
  "seed": 42,
  "match_rate": 0.85,
  "wd14_result": {
    "matched": ["1girl", "smile"],
    "missing": ["school_uniform"],
    "extra": ["indoors", "classroom"],
    "partial_matched": [],
    "skipped": [],
    "raw_tags": [
      {"tag": "1girl", "score": 0.95},
      {"tag": "smile", "score": 0.88}
    ]
  },

  "sd_params": {"steps": 20, "cfg_scale": 7.0, ...},
  "notes": "Testing uniform rendering",
  "created_at": "2026-02-08T12:00:00Z"
}
```

**V3 Prompt Engine 동작**:
1. `target_tags` + `character_id` → V3PromptBuilder로 Character LoRA 삽입
2. Group Config → Style Profile 조회 → Style LoRAs 추가
3. Style Profile의 Quality Tags + Negative Prompt 병합
4. `final_prompt` 생성 → SD API 호출
5. `loras_applied` 메타데이터 추출 및 저장

**Error Handling (Lab Mode)**:
- V3 composition 실패 → fallback to original prompt + warning
- SD API 실패 → status='failed', partial result 반환
- Style Profile 실패 → warning 로그, 실험 계속 진행

---

### `POST /lab/experiments/compose-and-run`
Scene Lab: 씬 설명을 V3로 구성한 후 이미지 생성 및 검증.

**Request:**
```json
{
  "experiment_type": "scene_translate",
  "group_id": 1,
  "character_id": 1,  // Required for Scene Lab
  "scene_description": "A student sitting in the classroom during lunch break",
  "target_tags": [],  // Gemini가 생성한 태그로 자동 채워짐
  "negative_prompt": "blurry, low quality",
  "sd_params": {"steps": 25, "cfg_scale": 7.5},
  "notes": "Testing scene composition"
}
```

**Response:**
```json
{
  "id": 124,
  "experiment_type": "scene_translate",
  "status": "completed",
  "group_id": 1,
  "character_id": 1,

  // Scene description
  "scene_description": "A student sitting in the classroom during lunch break",

  // V3 Composed prompt
  "prompt_used": "1girl, sitting, classroom, lunch_break, school_uniform",
  "final_prompt": "1girl, sitting, classroom, lunch_break, school_uniform, <lora:char:1.0>, <lora:anime:0.7>, masterpiece",
  "loras_applied": [...],

  "match_rate": 0.82,
  "image_url": "...",
  "created_at": "2026-02-08T12:01:00Z"
}
```

---

### `POST /lab/experiments/run-batch`
동일한 태그 조합으로 배치 실험을 실행합니다 (시드만 다름).

**Request:**
```json
{
  "experiment_type": "tag_render",
  "group_id": 1,
  "character_id": 1,
  "target_tags": ["1girl", "smile"],
  "count": 5,  // 배치 크기 (max: LAB_BATCH_MAX_SIZE)
  "seeds": [100, 200, 300, 400, 500],  // Optional: 지정하지 않으면 랜덤
  "sd_params": {"steps": 20},
  "notes": "Testing consistency"
}
```

**Response:**
```json
{
  "batch_id": "abc123def456",
  "total": 5,
  "completed": 5,
  "failed": 0,
  "experiments": [
    {
      "id": 125,
      "batch_id": "abc123def456",
      "status": "completed",
      "seed": 100,
      "match_rate": 0.87,
      "final_prompt": "...",
      "loras_applied": [...]
    },
    // ... 4 more experiments
  ]
}
```

**Use Case**: 동일 프롬프트의 일관성 검증, 최적 시드 탐색.

---

### `GET /lab/experiments`
실험 목록을 조회합니다 (필터링, 페이지네이션).

**Query Parameters:**
- `experiment_type`: `tag_render`, `scene_translate`
- `character_id`: 특정 캐릭터 실험만
- `batch_id`: 특정 배치 실험만
- `limit`: 최대 반환 개수 (default: 50)
- `offset`: 페이지네이션 오프셋 (default: 0)

**Response:**
```json
{
  "items": [
    {
      "id": 123,
      "experiment_type": "tag_render",
      "status": "completed",
      "group_id": 1,
      "character_id": 1,
      "match_rate": 0.85,
      "final_prompt": "...",
      "loras_applied": [...],
      "created_at": "2026-02-08T12:00:00Z"
    }
  ],
  "total": 50
}
```

---

### `GET /lab/experiments/{experiment_id}`
단일 실험의 상세 정보를 조회합니다.

**Response:**
```json
{
  "id": 123,
  "experiment_type": "tag_render",
  "status": "completed",
  "group_id": 1,
  "character_id": 1,

  "prompt_used": "1girl, smile",
  "final_prompt": "1girl, smile, <lora:char:1.0>, <lora:style:0.7>, masterpiece",
  "loras_applied": [
    {"name": "char", "weight": 1.0, "source": "character"},
    {"name": "style", "weight": 0.7, "source": "style"}
  ],

  "target_tags": ["1girl", "smile"],
  "match_rate": 0.85,
  "wd14_result": {...},
  "image_url": "...",
  "seed": 42,
  "created_at": "2026-02-08T12:00:00Z"
}
```

---

### `DELETE /lab/experiments/{experiment_id}`
실험을 삭제합니다.

**Response:**
```json
{
  "ok": true
}
```

---

### `GET /lab/analytics/tag-effectiveness`
Lab 실험 결과 기반 태그 효과성을 집계합니다.

**Response:**
```json
{
  "items": [
    {
      "tag_name": "1girl",
      "tag_id": 1,
      "use_count": 100,
      "match_count": 95,
      "effectiveness": 0.95
    },
    {
      "tag_name": "smile",
      "tag_id": 2,
      "use_count": 80,
      "match_count": 72,
      "effectiveness": 0.90
    },
    {
      "tag_name": "school_uniform",
      "tag_id": 3,
      "use_count": 50,
      "match_count": 30,
      "effectiveness": 0.60
    }
  ],
  "total_experiments": 150,
  "avg_match_rate": 0.82
}
```

**Use Case**:
- Effectiveness < 70%인 태그 → 프롬프트에서 제외 고려
- Effectiveness > 90%인 태그 → 우선적으로 사용

---

### `POST /lab/analytics/sync-effectiveness`
Lab 실험 결과를 Studio의 `tag_effectiveness` 테이블에 동기화합니다.

**Response:**
```json
{
  "synced": 25
}
```

**동작**:
- Lab의 `aggregate_tag_effectiveness()` 결과를 DB `tag_effectiveness` 테이블에 upsert
- Studio에서 프롬프트 생성 시 태그 효과성 데이터 참조 가능

---

### Lab → Studio Workflow

```
1. Tag Lab → 태그 조합 실험 (V3 + Style Profile)
2. Analytics → 효과성 분석 (Match Rate < 70% 태그 제외)
3. Sync → Studio tag_effectiveness 테이블에 동기화
4. Studio → V3 Prompt Engine이 효과성 데이터 참조
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

**Last Updated:** 2026-02-08
**API Version:** v3.2 (Phase 1: Lab-Studio Integration)
