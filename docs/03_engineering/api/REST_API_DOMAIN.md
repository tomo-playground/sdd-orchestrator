# API Specification - Domain API (v4.0)

Tags, Keywords, ControlNet, LoRA, Avatar, Assets, Backgrounds, Prompt, SD, Characters, Style Profiles, SD Models/Embeddings, Prompt Histories 관련 API 명세입니다.

> 메인 문서: [REST_API.md](./REST_API.md) | Analytics & Admin: [REST_API_ANALYTICS.md](./REST_API_ANALYTICS.md)

---

## 목차

1. [Tags & Classification](#tags--classification) - 태그 분류/CRUD
2. [Keywords](#keywords) - 키워드 관리
3. [ControlNet & IP-Adapter](#controlnet--ip-adapter)
4. [LoRA Management](#lora-management)
5. [Avatar](#avatar) - 아바타 관리
6. [Assets](#assets) - 에셋 관리
7. [Backgrounds](#backgrounds) - 배경 관리
8. [Prompt](#prompt) - 프롬프트 처리
9. [Stable Diffusion](#stable-diffusion) - SD WebUI 프록시
10. [Characters](#characters) - 캐릭터 관리
11. [Style Profiles](#style-profiles) - 스타일 프로파일
12. [SD Models & Embeddings](#sd-models--embeddings) - SD 모델/임베딩 CRUD
13. [Prompt Histories](#prompt-histories) - 프롬프트 히스토리

---

## Tags & Classification

> 라우터 prefix: `/tags`

### 태그 CRUD

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/tags` | 태그 목록 (category, search, active_only 필터) | 태그 배열 |
| GET | `/tags/groups` | 태그 그룹 목록 | 그룹 배열 |
| GET | `/tags/search` | 태그 검색 (query, limit) | 태그 배열 |
| GET | `/tags/{id}` | 태그 상세 | 태그 객체 |
| POST | `/tags` | 태그 생성 | 태그 객체 (201) |
| PUT | `/tags/{id}` | 태그 수정 | 태그 객체 |
| DELETE | `/tags/{id}` | 태그 삭제 | `{ok, deleted}` |

### 태그 분류

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tags/classify` | 태그를 DB→Rule→Danbooru→LLM 순으로 자동 분류 |
| GET | `/tags/pending` | 분류 승인 필요한 태그 목록 (source, max_confidence 필터) |
| POST | `/tags/approve-classification` | 태그 분류 승인/수정 |
| POST | `/tags/bulk-approve-classifications` | 다수 태그 분류 일괄 승인 |
| POST | `/tags/migrate-patterns` | CATEGORY_PATTERNS을 DB 규칙으로 마이그레이션 |

---

## Keywords

> 라우터 prefix: `/keywords`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/keywords/suggestions` | 새로운 키워드 제안 (min_count, limit) |
| GET | `/keywords/categories` | 키워드 카테고리 목록 |
| GET | `/keywords/rules` | 태그 충돌/의존성 규칙 요약 |
| GET | `/keywords/priority` | 카테고리별 우선순위 목록 |
| GET | `/keywords/tags` | 등록된 태그 목록 (전체) |
| GET | `/keywords/effectiveness` | 태그 효과성 데이터 |
| GET | `/keywords/effectiveness/summary` | 효과성 요약 통계 |
| POST | `/keywords/validate` | 태그 충돌/의존성 검증 |
| POST | `/keywords/approve` | 제안된 키워드 승인 |
| POST | `/keywords/batch-approve` | 태그 일괄 승인 |
| GET | `/keywords/batch-approve/preview` | 일괄 승인 미리보기 |
| POST | `/keywords/sync-lora-triggers` | LoRA 트리거 워드를 태그 DB와 동기화 |
| POST | `/keywords/sync-category-patterns` | 카테고리 패턴 동기화 |

---

## ControlNet & IP-Adapter

> 라우터 prefix: `/controlnet`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/controlnet/status` | ControlNet 사용 가능 여부와 모델 목록 |
| POST | `/controlnet/detect-pose` | 이미지에서 포즈 추출 |
| POST | `/controlnet/suggest-pose` | 태그 기반 포즈 레퍼런스 제안 |
| GET | `/controlnet/poses` | 사용 가능한 포즈 레퍼런스 목록 |
| GET | `/controlnet/pose/{name}` | 특정 포즈 이미지 조회 |
| GET | `/controlnet/ip-adapter/status` | IP-Adapter 사용 가능 여부 |
| GET | `/controlnet/ip-adapter/references` | 저장된 참조 이미지 목록 |
| POST | `/controlnet/ip-adapter/reference` | 캐릭터 참조 이미지 등록 |
| GET | `/controlnet/ip-adapter/reference/{key}` | 특정 참조 이미지 메타 |
| GET | `/controlnet/ip-adapter/reference/{key}/image` | 참조 이미지 파일 다운로드 |
| DELETE | `/controlnet/ip-adapter/reference/{key}` | 참조 이미지 삭제 |

---

## LoRA Management

> 라우터 prefix: `/loras`

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/loras` | 등록된 LoRA 목록 | LoRA 배열 |
| GET | `/loras/{id}` | LoRA 상세 | LoRA 객체 |
| POST | `/loras` | LoRA 생성 | LoRA 객체 (201) |
| PUT | `/loras/{id}` | LoRA 수정 | LoRA 객체 |
| DELETE | `/loras/{id}` | LoRA 삭제 | `{ok, deleted}` |
| GET | `/loras/search-civitai` | Civitai에서 LoRA 검색 (query) | 검색 결과 |
| POST | `/loras/import-civitai/{civitai_id}` | Civitai 메타데이터로 LoRA 등록 | LoRA 객체 |
| POST | `/loras/{id}/calibrate` | LoRA 최적 가중치 보정 | 보정 결과 |
| POST | `/loras/calibrate-all` | 전체 LoRA 일괄 보정 | 일괄 보정 결과 |

**LoRA 멀티캐릭터 필드:**
- `is_multi_character_capable`: 2인 동시 출연 시 사용 가능 여부
- `multi_char_weight_scale`: 멀티캐릭터 씬에서 LoRA weight 축소 비율
- `multi_char_trigger_prompt`: 멀티캐릭터 전용 호출 프롬프트

---

## Avatar

> 라우터 prefix: `/avatar`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/avatar/regenerate` | 아바타 이미지 재생성 |
| POST | `/avatar/resolve` | 아바타 파일 존재 여부 확인 |

---

## Assets

> 라우터: prefix 없음, `/audio/*`, `/fonts/*`, `/overlay/*`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/audio/list` | 사용 가능한 BGM 파일 목록 |
| GET | `/fonts/list` | 사용 가능한 폰트 파일 목록 |
| GET | `/fonts/file/{filename}` | 폰트 파일 다운로드 |
| GET | `/overlay/list` | 오버레이 템플릿 목록 |
| GET | `/assets/overlay/{filename}` | 오버레이 이미지 파일 |

---

## Backgrounds

> 라우터 prefix: `/backgrounds`

배경 프리셋 CRUD. ControlNet Canny 참조 이미지 + 환경 태그 관리.

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/backgrounds` | 목록 (search, category 필터) | `BackgroundResponse[]` |
| GET | `/backgrounds/categories` | 카테고리 목록 | `string[]` |
| GET | `/backgrounds/{id}` | 상세 | `BackgroundResponse` |
| POST | `/backgrounds` | 생성 | `BackgroundResponse` |
| PUT | `/backgrounds/{id}` | 수정 | `BackgroundResponse` |
| DELETE | `/backgrounds/{id}` | Soft Delete | `{ok, deleted}` |
| POST | `/backgrounds/{id}/restore` | 복구 | `BackgroundResponse` |
| POST | `/backgrounds/{id}/upload-image` | 이미지 업로드 | `BackgroundResponse` |

---

## Prompt

> 라우터 prefix: `/prompt`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/prompt/compose` | 12-Layer 프롬프트 합성 |
| POST | `/prompt/rewrite` | 프롬프트 스타일 재작성 |
| POST | `/prompt/split` | 예시 프롬프트를 base/scene으로 분리 |
| POST | `/prompt/validate` | 프롬프트 문법 검증 |
| POST | `/prompt/validate-tags` | 태그 유효성 검증 |
| POST | `/prompt/auto-replace` | 비활성 태그 자동 대체 |
| POST | `/prompt/check-conflicts` | 태그 충돌 검사 |

### `POST /prompt/compose` — 상세

**Request:**
```json
{
  "character_id": 8,
  "character_b_id": null,
  "scene_id": 42,
  "context_tags": {"expression": ["smile"], "camera": "upper_body"}
}
```

**Response:**
```json
{
  "prompt": "masterpiece, best_quality, 1girl, ..., smile, upper_body",
  "layers": [...]
}
```

---

## Stable Diffusion

> 라우터 prefix: `/sd`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sd/models` | 사용 가능한 SD 모델 목록 (SD WebUI 프록시) |
| GET | `/sd/options` | 현재 SD WebUI 설정 |
| POST | `/sd/options` | SD WebUI 모델 변경 |
| GET | `/sd/loras` | 사용 가능한 LoRA 목록 (SD WebUI 프록시) |

---

## Characters

> 라우터 prefix: `/characters`

### 캐릭터 CRUD

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/characters` | 캐릭터 목록 (group_id, offset, limit) | `PaginatedCharacterList` |
| GET | `/characters/{id}` | 캐릭터 상세 (V3 relational tags + LoRA) | `CharacterResponse` |
| POST | `/characters` | 캐릭터 생성 (201) | `CharacterResponse` |
| PUT | `/characters/{id}` | 캐릭터 수정 (부분 업데이트) | `CharacterResponse` |
| DELETE | `/characters/{id}` | 캐릭터 Soft Delete | `{ok, deleted}` |

### 캐릭터 Soft Delete

| Method | Path | Description |
|--------|------|-------------|
| GET | `/characters/trash` | Soft Delete된 캐릭터 목록 |
| POST | `/characters/{id}/restore` | 캐릭터 복원 |
| DELETE | `/characters/{id}/permanent` | 캐릭터 영구 삭제 |

### 참조 이미지/프리뷰

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| POST | `/characters/preview` | 위저드 임시 프리뷰 생성 (DB 미저장) | `CharacterPreviewResponse` |
| POST | `/characters/{id}/regenerate-reference` | 참조 이미지 재생성 | 생성 결과 |
| POST | `/characters/{id}/enhance-preview` | Gemini로 프리뷰 이미지 향상 | 향상 결과 |
| POST | `/characters/{id}/edit-preview` | 자연어 지시로 프리뷰 편집 | 편집 결과 |
| POST | `/characters/{id}/assign-preview` | 위저드 프리뷰를 캐릭터에 할당 | `AssignPreviewResponse` |
| POST | `/characters/batch-regenerate-references` | 전체 캐릭터 참조 이미지 일괄 재생성 | 일괄 결과 |

---

## Style Profiles

> 라우터 prefix: `/style-profiles`

SD 모델, LoRA, Embedding 조합으로 구성된 스타일 프로파일 관리.

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/style-profiles` | 목록 (active_only 필터) | `list[StyleProfileResponse]` |
| GET | `/style-profiles/default` | 기본 프로파일 (full 정보) | `StyleProfileFullResponse` |
| GET | `/style-profiles/{id}` | 상세 | `StyleProfileResponse` |
| GET | `/style-profiles/{id}/full` | 상세 + SD 모델/LoRA/Embedding resolved | `StyleProfileFullResponse` |
| POST | `/style-profiles` | 생성 (201) | `StyleProfileResponse` |
| PUT | `/style-profiles/{id}` | 수정 | `StyleProfileResponse` |
| DELETE | `/style-profiles/{id}` | 삭제 | `StyleProfileDeleteResponse` |

---

## SD Models & Embeddings

> 라우터: prefix 없음, `/sd-models/*`, `/embeddings/*`

### SD Models

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/sd-models` | SD 모델 목록 (active_only) | `list[SDModelResponse]` |
| GET | `/sd-models/{id}` | SD 모델 상세 | `SDModelResponse` |
| POST | `/sd-models` | SD 모델 생성 (201) | `SDModelResponse` |
| PUT | `/sd-models/{id}` | SD 모델 수정 | `SDModelResponse` |
| DELETE | `/sd-models/{id}` | SD 모델 삭제 | `{ok, deleted}` |

### Embeddings

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/embeddings` | 임베딩 목록 (embedding_type, active_only) | `list[EmbeddingResponse]` |
| GET | `/embeddings/{id}` | 임베딩 상세 | `EmbeddingResponse` |
| POST | `/embeddings` | 임베딩 생성 (201) | `EmbeddingResponse` |
| PUT | `/embeddings/{id}` | 임베딩 수정 | `EmbeddingResponse` |
| DELETE | `/embeddings/{id}` | 임베딩 삭제 | `{ok, deleted}` |

---

## Prompt Histories

> 라우터 prefix: `/prompt-histories`

프롬프트 히스토리 CRUD. 사용 횟수, WD14 검증 점수, 즐겨찾기 관리.

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/prompt-histories` | 목록 (favorite, character_id, search, sort 필터) | `list[PromptHistoryResponse]` |
| GET | `/prompt-histories/{id}` | 상세 | `PromptHistoryResponse` |
| POST | `/prompt-histories` | 생성 (201) | `PromptHistoryResponse` |
| PUT | `/prompt-histories/{id}` | 수정 | `PromptHistoryResponse` |
| DELETE | `/prompt-histories/{id}` | Soft Delete | `{ok, deleted}` |
| GET | `/prompt-histories/trash` | Soft Delete된 목록 | 목록 |
| POST | `/prompt-histories/{id}/restore` | 복원 | `{ok, restored}` |
| DELETE | `/prompt-histories/{id}/permanent` | 영구 삭제 | `{ok, deleted}` |
| POST | `/prompt-histories/{id}/toggle-favorite` | 즐겨찾기 토글 | `PromptHistoryResponse` |
| POST | `/prompt-histories/{id}/apply` | 히스토리 적용 (use_count 증가) | `PromptHistoryApplyResponse` |
| POST | `/prompt-histories/{id}/update-score` | WD14 점수 업데이트 (match_rate query) | `PromptHistoryResponse` |

---

## 참고 문서

| 문서 | 경로 |
|------|------|
| Core API | [REST_API.md](./REST_API.md) |
| Analytics & Admin | [REST_API_ANALYTICS.md](./REST_API_ANALYTICS.md) |
| Creative Engine | [REST_API_CREATIVE.md](./REST_API_CREATIVE.md) |
| Presets | [REST_API_PRESETS.md](./REST_API_PRESETS.md) |

---

**Last Updated:** 2026-02-27
**API Version:** v4.0
