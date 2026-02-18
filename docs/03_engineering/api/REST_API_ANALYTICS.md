# API Specification - Analytics & Admin API (v4.0)

Quality, Activity Logs, Gemini Edit Analytics, Lab Experiments, Admin, Settings, YouTube, Scripts, Memory 관련 API 명세입니다.

> 메인 문서: [REST_API.md](./REST_API.md) | Domain API: [REST_API_DOMAIN.md](./REST_API_DOMAIN.md)

---

## 목차

1. [Quality](#quality) - 품질 검증
2. [Activity Logs](#activity-logs) - 활동 로그 분석
3. [Gemini Edit Analytics](#gemini-edit-analytics) - Gemini 자동 편집 분석
4. [Lab Experiments](#lab-experiments) - 실험 및 분석
5. [Admin](#admin) - 마이그레이션, 캐시, 태그 관리, Media GC
6. [Settings](#settings) - Gemini Auto Edit 설정
7. [YouTube](#youtube) - YouTube OAuth & 업로드
8. [Scripts](#scripts) - LangGraph 기반 대본 생성
9. [Memory](#memory) - Memory Store 관리

---

## Quality

> 라우터 prefix: `/quality`

### `POST /quality/batch-validate`
스토리보드의 모든 씬을 배치로 검증하고 품질 점수를 저장합니다.

**Request:** `BatchValidateRequest`
```json
{
  "storyboard_id": 1,
  "scenes": [
    {"scene_id": 1, "image_url": "/outputs/images/scene_1.png", "prompt": "..."},
    {"scene_id": 2, "image_url": "/outputs/images/scene_2.png", "prompt": "..."}
  ]
}
```

### `GET /quality/summary/storyboard/{storyboard_id}`
스토리보드의 품질 요약 통계를 조회합니다.

### `GET /quality/summary/{storyboard_id}`
`/summary/storyboard/{storyboard_id}`와 동일 (호환 유지).

### `GET /quality/alerts/{storyboard_id}`
품질 기준 미달 씬 목록을 조회합니다.

**Query Parameters:**
- `threshold`: 경고 기준 Match Rate (default: 0.7)

---

## Activity Logs

> 라우터 prefix: `/activity-logs`

### `POST /activity-logs`
이미지 생성 메타데이터를 로깅합니다.

**Request:** `CreateActivityLogRequest`
```json
{
  "storyboard_id": 1,
  "scene_id": 0,
  "character_id": 3,
  "prompt": "1girl, smiling, classroom, ...",
  "tags": ["1girl", "smiling", "classroom"],
  "sd_params": {"steps": 20, "cfg_scale": 7, "seed": 12345},
  "match_rate": 0.85,
  "seed": 12345,
  "status": "success",
  "image_url": "/outputs/images/scene_0.png"
}
```

### `GET /activity-logs/storyboard/{storyboard_id}`
특정 스토리보드의 활동 로그를 조회합니다.

**Query Parameters:**
- `status`: `success`, `fail`, `pending`
- `limit`: 최대 반환 개수 (default: 100)

### `PATCH /activity-logs/{id}/status`
로그 상태를 수정합니다.

### `DELETE /activity-logs/{id}`
활동 로그를 삭제합니다.

### `GET /activity-logs/analyze/patterns`
태그 패턴 성공/실패 통계를 제공합니다.

**Query Parameters:** `storyboard_id` (required)

### `GET /activity-logs/suggest-conflict-rules`
패턴 분석 기반 충돌 규칙을 제안합니다.

**Query Parameters:** `storyboard_id` (required)

### `POST /activity-logs/apply-conflict-rules`
제안된 충돌 규칙을 DB에 적용합니다.

### `GET /activity-logs/success-combinations`
성공률이 높은 태그 조합을 추출합니다.

**Query Parameters:** `storyboard_id` (required)

---

## Gemini Edit Analytics

> 라우터: prefix 없음, `/analytics/*`

### `GET /analytics/gemini-edits`
Gemini Auto Edit 분석 데이터. Before/After Match Rate 비교, 편집 타입별 성공률, 비용 등을 조회합니다.

**Query Parameters:**
- `storyboard_id`: int (optional) - 특정 스토리보드만 필터

**Response:**
```json
{
  "total_edits": 15,
  "avg_cost_usd": 0.0404,
  "total_cost_usd": 0.606,
  "avg_improvement": 0.23,
  "edits": [...],
  "by_improvement_range": {"0-10%": 2, "10-20%": 5, "20-30%": 6, "30%+": 2}
}
```

### `GET /analytics/gemini-edits/summary`
Gemini Auto Edit 요약 통계를 간단하게 조회합니다.

**Response:**
```json
{
  "total_edits": 42,
  "total_cost": 1.6968,
  "success_rate": 0.95,
  "avg_improvement": 0.23
}
```

---

## Lab Experiments

> 라우터 prefix: `/lab`

### 핵심 개념

- **Tag Lab**: 개별 태그 조합의 렌더링 품질 실험
- **Scene Lab**: V3 Prompt Engine을 사용한 씬 구성 실험
- **Creative Lab**: 멀티 에이전트 협업 → [REST_API_CREATIVE.md](./REST_API_CREATIVE.md)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/lab/experiments/run` | Tag Lab/Scene Lab 단일 실험 실행 |
| POST | `/lab/experiments/compose-and-run` | Scene Lab: 씬 설명 → 구성 → 이미지 생성 |
| POST | `/lab/experiments/run-batch` | 배치 실험 (동일 태그, 시드만 다름) |
| GET | `/lab/experiments` | 실험 목록 (필터링, 페이지네이션) |
| GET | `/lab/experiments/{id}` | 실험 상세 |
| DELETE | `/lab/experiments/{id}` | 실험 삭제 |
| GET | `/lab/analytics/tag-effectiveness` | 태그 효과성 집계 |
| POST | `/lab/analytics/sync-effectiveness` | tag_effectiveness 테이블 동기화 |

---

## Admin

> 라우터 prefix: `/admin`

### 엔드포인트 분류

| 분류 | 엔드포인트 | Method |
|------|-----------|--------|
| **마이그레이션** | `/admin/migrate-tag-rules` | POST |
| **캐시** | `/admin/refresh-caches` | POST |
| **태그 관리** | `/admin/tags/deprecated` | GET |
| | `/admin/tags/{tag_id}/deprecate` | PUT |
| | `/admin/tags/{tag_id}/activate` | PUT |
| **Media GC** | `/admin/media-assets/orphans` | GET |
| | `/admin/media-assets/cleanup` | POST |
| | `/admin/media-assets/stats` | GET |

### `POST /admin/refresh-caches`
모든 인메모리 캐시를 DB에서 리프레시합니다.
대상: `TagCategoryCache`, `TagFilterCache`, `TagAliasCache`, `TagRuleCache`, `LoRATriggerCache`

### Media Asset GC

**감지 카테고리:**
- **Null Owner**: `owner_type IS NULL` + FK 미참조
- **Broken FK**: `owner_type` 존재하지만 owner 레코드 없음
- **Expired Temp**: `is_temp=True` + TTL 초과 (기본 24h)

#### `GET /admin/media-assets/orphans`
고아 미디어 에셋을 스캔합니다 (감지만, 삭제 없음).

#### `POST /admin/media-assets/cleanup`
고아 및 만료 임시 에셋을 정리합니다. `dry_run` (default: `true`)

#### `GET /admin/media-assets/stats`
미디어 에셋 전체 통계를 조회합니다.

---

## Settings

> 라우터: prefix 없음, `/settings/*`

Gemini Auto Edit 런타임 설정을 관리합니다.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/settings/auto-edit` | 현재 Auto Edit 설정 조회 |
| PUT | `/settings/auto-edit` | Auto Edit 설정 업데이트 (런타임) |
| GET | `/settings/auto-edit/cost-summary` | Auto Edit 비용 요약 (일/주/월/전체) |

> **주의**: PUT 엔드포인트는 런타임 설정을 변경합니다. 서버 재시작 시 `.env` 값으로 초기화됩니다.

---

## YouTube

> 라우터 prefix: `/youtube`

YouTube OAuth 인증 및 비디오 업로드를 관리합니다.

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/youtube/authorize/{project_id}` | Google OAuth URL 생성 | `YouTubeAuthURLResponse` |
| POST | `/youtube/callback` | OAuth 인증 코드 교환 (code, state query) | `YouTubeCredentialResponse` |
| GET | `/youtube/credentials/{project_id}` | YouTube 자격 증명 조회 | `YouTubeCredentialResponse` |
| DELETE | `/youtube/credentials/{project_id}` | YouTube 자격 증명 해제 | `YouTubeRevokeResponse` |
| POST | `/youtube/upload` | YouTube 비디오 업로드 시작 (비동기) | `YouTubeUploadStatusResponse` |
| GET | `/youtube/upload-status/{render_history_id}` | 업로드 상태 폴링 | `YouTubeUploadStatusResponse` |

### `POST /youtube/upload` — 상세

**Request:** `YouTubeUploadRequest`
```json
{
  "project_id": 1,
  "render_history_id": 42,
  "title": "커피숍 일상 #shorts",
  "description": "AI 생성 쇼츠",
  "tags": ["shorts", "AI"],
  "privacy_status": "public"
}
```

---

## Scripts

> 라우터 prefix: `/scripts`

LangGraph 기반 AI 대본 생성 파이프라인. SSE 스트리밍으로 노드별 진행률을 실시간 전송합니다.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/scripts/generate` | 동기 대본 생성 |
| POST | `/scripts/generate-stream` | SSE 스트리밍 대본 생성 |
| POST | `/scripts/resume` | Human Gate/Concept Gate 재개 |
| GET | `/scripts/presets` | LangGraph 프리셋 목록 |
| GET | `/scripts/feedback-presets` | 피드백 프리셋 목록 |
| POST | `/scripts/feedback` | 스크립트 생성 피드백 제출 |

### `POST /scripts/generate-stream` — SSE 이벤트

**Request:** `StoryboardRequest`

**SSE Payload:**
```json
{
  "node": "writer",
  "label": "대본 생성",
  "percent": 40,
  "status": "running",
  "thread_id": "script-abc123def456"
}
```

**노드 순서:** research → critic → concept_gate → writer → review → cinematographer → tts_designer → sound_designer → copyright_reviewer → director → human_gate → finalize → explain → learn

### `POST /scripts/resume`

**Request:** `ScriptResumeRequest`
```json
{
  "thread_id": "script-abc123def456",
  "action": "approve",
  "feedback": null,
  "concept_id": null,
  "trace_id": null
}
```

---

## Memory

> 라우터 prefix: `/memory`

LangGraph Agent의 Memory Store를 관리합니다.

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/memory/stats` | 네임스페이스별 카운트 통계 | `MemoryStatsResponse` |
| GET | `/memory/{ns_type}` | 타입별 항목 목록 | `MemoryListResponse` |
| GET | `/memory/{ns_type}/{ns_id}` | 특정 네임스페이스 조회 | `MemoryListResponse` |
| DELETE | `/memory/{ns_type}/{ns_id}/{key}` | 단일 항목 삭제 | `MemoryDeleteResponse` |
| DELETE | `/memory/{ns_type}/{ns_id}` | 네임스페이스 전체 삭제 | `MemoryDeleteResponse` |

**유효한 ns_type:** `character`, `topic`, `user`, `group`, `feedback`

---

## 참고 문서

| 문서 | 경로 |
|------|------|
| Core API | [REST_API.md](./REST_API.md) |
| Domain API | [REST_API_DOMAIN.md](./REST_API_DOMAIN.md) |
| Creative Engine | [REST_API_CREATIVE.md](./REST_API_CREATIVE.md) |
| Presets | [REST_API_PRESETS.md](./REST_API_PRESETS.md) |

---

**Last Updated:** 2026-02-18
**API Version:** v4.0
