# Database Schema (v3.15)

Shorts Producer의 PostgreSQL 데이터베이스 스키마입니다.
SQLAlchemy ORM + Alembic 마이그레이션으로 관리합니다.

## 📝 변경 이력

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v3.15 | 2026-02-10 | **Source-Truth Sync**: 유령 컬럼 18개 제거, 누락 컬럼 45+개 추가, ERD 정합성 수정. `projects`(avatar_key/render_preset_id/style_profile_id 제거), `storyboards`(character_id 등 5개 제거, structure 추가), `scenes`(SD params 5개 제거, ControlNet/IP-Adapter 6개 추가), `characters`(project_id FK 추가), Creative Engine V2 필드 전체, `lab_experiments` 10개 컬럼 추가 |
| v3.14 | 2026-02-08 | **Documentation Catch-up**: `Creative Engine` (Agents), `GroupConfig`, `RenderHistory`, `LabExperiments`, `YouTubeCredential` 추가. `evaluation_runs` 제거. `StoryboardCharacter` 추가. |
| v3.13 | 2026-02-07 | FK 정합성 강화: `scenes.environment_reference_id` → FK media_assets, `activity_logs` 3컬럼 FK 추가, `tags.replacement_tag_id` ondelete 추가. `scenes.deleted_at` SoftDeleteMixin 적용 |
| v3.12 | 2026-02-07 | `music_presets` 테이블 추가 (AI BGM 프리셋). `render_presets`에 `bgm_mode`, `music_preset_id` FK 추가 |
| v3.11 | 2026-02-06 | `scenes.candidates` 형식 변경: `image_url` 제거, `media_asset_id` 필수. Backend에서 GET 시 URL 자동 해석 |
| v3.10 | 2026-02-06 | `render_presets.voice_preset_id` 제거 (GroupConfig.narrator_voice_preset_id로 대체), `group_config.character_id` 제거 (storyboard 레벨에서만 설정) |
| v3.9 | 2026-02-05 | `render_presets.project_id` 컬럼 제거 (글로벌 공통 프리셋으로 단순화) |
| v3.8 | 2026-02-04 | Schema Cleanup Batch B: `scenes.use_reference_only` Integer→Boolean, `storyboards.recent_videos_json` Text→JSONB + rename→`recent_videos` |
| v3.7 | 2026-02-04 | `storyboards.default_caption` → `caption`, `characters.default_voice_preset_id` → `voice_preset_id` 리네이밍. FK/인덱스 리네이밍 포함 |
| v3.6 | 2026-02-04 | `default_` prefix 제거: `projects`/`storyboards`에서 `default_character_id` → `character_id`, `default_style_profile_id` → `style_profile_id` 리네이밍. `groups`/`group_config`에서 `default_character_id` DROP, `default_style_profile_id` → `style_profile_id` 리네이밍. `group_config` 테이블 추가 (1:1 분리 설정). style_profile_id backfill (project → group → group_config) |
| v3.5 | 2026-02-04 | `characters.default_voice_preset_id`, `storyboards.narrator_voice_preset_id` FK 추가. `render_presets`에서 `narrator_voice`, `tts_engine`, `voice_design_prompt` 제거 (voice_preset_id로 대체). Soft Delete (`deleted_at`) 추가 |
| v3.4 | 2026-02-02 | `render_presets`, `voice_presets` 테이블 추가. `projects`에 Cascading Config FK 추가. `groups`에서 `default_bgm_file`/`default_narrator_voice` 제거 |
| v3.3 | 2026-02-02 | `projects`, `groups`, `scene_quality_scores` 테이블 추가, `activity_logs`에 Gemini 트래킹 컬럼 추가, `media_assets`에 `is_temp`/`checksum` 추가, `storyboards`에 `default_caption` 반영 |
| v3.2 | 2026-02-01 | scenes 테이블 누락 컬럼 보완 (prompt, SD params, IP-Adapter, context_tags), characters에 preview_locked 추가, is_permanent/default_layer 상호작용 문서화, 12-Layer 매핑 테이블 추가 |
| v3.1 | 2026-01-31 | **Media Asset 시스템**: 폴리모픽 참조, Legacy URL 컬럼 삭제, S3/Local 통합, Video Asset 생성 활성화 |
| v3.0 | 2026-01-30 | V3 아키텍처: Storyboard-Centric, Relational Tags, Activity Logs, Tag Aliases/Filters |
| v2.0 | 2026-01-27 | Characters, LoRAs, Style Profiles, Tag System |

---

## 🗺️ ER Diagram

```mermaid
erDiagram
    projects ||--o{ groups : "contains"
    projects ||--o| youtube_credentials : "has"
    projects }o--o| media_assets : "avatar"

    groups ||--o| group_config : "has_config"
    groups ||--o{ storyboards : "contains"
    groups ||--o{ lab_experiments : "has"
    
    group_config }o--o| render_presets : "preset"
    group_config }o--o| style_profiles : "style"
    group_config }o--o| voice_presets : "narrator"

    storyboards ||--o{ scenes : "has"
    storyboards ||--o{ storyboard_characters : "maps_speakers"
    storyboards ||--o{ activity_logs : "logged"
    storyboards ||--o{ render_history : "renders"
    
    scenes ||--o{ scene_tags : "has"
    scenes ||--o{ scene_character_actions : "has"
    scenes ||--o{ scene_quality_scores : "evaluated_by"

    voice_presets }o--o| media_assets : "audio"
    music_presets }o--o| media_assets : "audio"
    render_presets }o--o| music_presets : "bgm_ai"

    characters ||--o{ character_tags : "has"
    characters }o--o{ scene_character_actions : "acts_in"
    characters }o--o| projects : "belongs_to"
    storyboard_characters }o--o| characters : "maps_to"

    tags ||--o{ character_tags : "linked"
    tags ||--o{ scene_tags : "linked"
    tags ||--o{ scene_character_actions : "linked"
    tags ||--o{ tag_rules : "source/target"
    tags ||--o{ tag_effectiveness : "tracked"

    sd_models ||--o{ style_profiles : "base_model"
    
    creative_sessions ||--o{ creative_session_rounds : "has"
    creative_sessions ||--o{ creative_traces : "has"
    creative_agent_presets ||--o{ creative_traces : "executed"

    tag_aliases {
        string source_tag
        string target_tag
    }

    tag_filters {
        string tag_name
        string filter_type
    }
```

---

## 📦 Core: Channel & Storyboard System

### `projects`
YouTube 채널 단위. 채널별 설정 및 Cascading Config 최상위 레벨.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(200) | 채널/프로젝트 이름 |
| `description` | Text | 설명 |
| `handle` | String(100) | 채널 핸들 (@...) |
| `avatar_media_asset_id` | Integer (FK → media_assets, SET NULL) | 아바타 이미지 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

**Read-only 속성**:
- `avatar_key` (`@property`): `avatar_media_asset.storage_key` 반환
- `avatar_url` (`@property`): `avatar_media_asset.url` 반환

**Cascading Config 상속 순서**: Project → Group (GroupConfig) → Storyboard (하위가 상위를 오버라이드)

### `youtube_credentials`
프로젝트별 YouTube OAuth 인증 정보 (1:1).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `project_id` | Integer (FK → projects, UNIQUE) | 소속 프로젝트 |
| `channel_id` | String(100) | YouTube Channel ID |
| `channel_title` | String(200) | 채널명 |
| `encrypted_token` | Text | 암호화된 OAuth 토큰 |
| `is_valid` | Boolean | 토큰 유효 여부 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

### `groups`
프로젝트 내의 개별 시리즈 또는 카테고리.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `project_id` | Integer (FK → projects, RESTRICT) | 소속 프로젝트 |
| `name` | String(200) | 시리즈 이름 |
| `description` | Text | 설명 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

### `group_config`
Group별 설정 (1:1, 분리된 설정 테이블). 프로젝트 설정을 상속/오버라이드.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `group_id` | Integer (FK → groups, UNIQUE) | 소속 그룹 |
| `render_preset_id` | Integer (FK → render_presets) | 렌더 프리셋 |
| `style_profile_id` | Integer (FK → style_profiles) | 기본 스타일 프로파일 |
| `narrator_voice_preset_id` | Integer (FK → voice_presets) | 나레이터 음성 |
| `language` | String(20) | 언어 설정 |
| `structure` | String(30) | 구조 설정 |
| `duration` | Integer | 목표 길이 |
| `sd_steps`, `sd_cfg_scale`, ... | | SD 생성 파라미터 오버라이드 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

### `storyboards`
YouTube Shorts 프로젝트 단위. 개별 에피소드를 의미합니다.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `group_id` | Integer (FK → groups, RESTRICT) | 소속 그룹 |
| `title` | String(200) | 스토리보드 제목 |
| `description` | Text | 설명 |
| `caption` | Text | 캡션 텍스트 (Post Layout용) |
| `structure` | String(50) | 구조 설정 (default: `"Monologue"`, config에서 상속) |
| `deleted_at` | DateTime | Soft Delete 타임스탬프 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

**Read-only 속성**:
- `video_url` (`@property`): `render_history[0].media_asset.url` 반환

### `scenes`
스토리보드의 개별 씬/샷.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `storyboard_id` | Integer (FK → storyboards) | 소속 스토리보드 |
| `order` | Integer | 씬 순서 (0-based) |
| `script` | Text | 나레이션/Scene Text |
| `description` | Text | LLM 생성 시각적 설명 |
| `speaker` | String(20) | 화자 (default: `"Narrator"`) |
| `duration` | Float | 씬 길이 초 (default: 3.0) |
| **Prompt** | | |
| `image_prompt` | Text | Gemini 생성 프롬프트 (V3 compose 입력) |
| `image_prompt_ko` | Text | 한국어 프롬프트 |
| `negative_prompt` | Text | 네거티브 프롬프트 |
| `context_tags` | JSONB | 씬 컨텍스트 태그 (expression, gaze, pose, action, camera, environment, mood) |
| **Size** | | |
| `width` | Integer | 이미지 너비 (default: 512) |
| `height` | Integer | 이미지 높이 (default: 768) |
| **IP-Adapter / Reference** | | |
| `use_reference_only` | Boolean | IP-Adapter 사용 여부 (default: true) |
| `reference_only_weight` | Float | IP-Adapter 가중치 (default: 0.5) |
| `environment_reference_id` | Integer (FK → media_assets, SET NULL) | 환경 참조 이미지 ID |
| `environment_reference_weight` | Float | 환경 참조 가중치 (default: 0.3) |
| `use_ip_adapter` | Boolean | IP-Adapter 사용 여부 (씬별 오버라이드) |
| `ip_adapter_reference` | String | IP-Adapter 참조 이미지 경로 |
| `ip_adapter_weight` | Float | IP-Adapter 가중치 (씬별 오버라이드) |
| **ControlNet** | | |
| `use_controlnet` | Boolean | ControlNet 사용 여부 |
| `controlnet_weight` | Float | ControlNet 가중치 |
| **Generation** | | |
| `multi_gen_enabled` | Boolean | 멀티 생성 활성화 여부 |
| `image_asset_id` | Integer (FK → media_assets, SET NULL) | 생성된 이미지 (폴리모픽 참조) |
| `candidates` | JSONB | 후보 이미지 목록 (`media_asset_id`, `match_rate`) |
| `deleted_at` | DateTime | Soft Delete 타임스탬프 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

**Read-only 속성**:
- `image_url` (`@property`): `image_asset.url` 반환

**`context_tags` JSONB 구조**:
```json
{
  "expression": ["expressionless"],
  "gaze": "looking_at_viewer",
  "pose": ["standing"],
  "action": ["adjusting_hair"],
  "camera": "upper_body",
  "environment": ["office", "indoors"],
  "mood": ["melancholic"]
}
```
> list 필드: `expression`, `pose`, `action`, `environment`, `mood`
> string 필드: `gaze`, `camera`

---

## 🤖 Creative Engine (Agents)

Multi-Agent 협업을 통한 창작 프로세스 관리 시스템.

### `creative_agent_presets`
재사용 가능한 에이전트 페르소나 및 모델 설정.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(100) | 에이전트 이름 (Unique) |
| `role_description` | Text | 역할 설명 |
| `system_prompt` | Text | 시스템 프롬프트 |
| `model_provider` | String(20) | `gemini`, `ollama` |
| `model_name` | String(50) | 모델명 (e.g. `gemini-1.5-pro`) |
| `temperature` | Float | 생성 다양성 |
| `is_system` | Boolean | 시스템 프리셋 여부 |
| `deleted_at` | DateTime | Soft Delete 타임스탬프 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

### `creative_sessions`
에이전트 간의 창작 세션 (Leader Agent가 오케스트레이션).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `objective` | Text | 세션 목표 |
| `evaluation_criteria` | JSONB | 평가 기준 |
| `character_id` | Integer (FK) | 대상 캐릭터 (Optional) |
| `context` | JSONB | 추가 컨텍스트 |
| `agent_config` | JSONB | 참여 에이전트 구성 |
| `final_output` | JSONB | 최종 결과물 |
| `max_rounds` | Integer | 최대 라운드 수 |
| `total_token_usage` | JSONB | 총 토큰 사용량 |
| `status` | String(20) | 진행 상태 |
| **V2** | | |
| `session_type` | String(20) | 세션 유형 (default: `"free"`) |
| `director_mode` | String(20) | 디렉터 모드 (default: `"advisor"`) |
| `concept_candidates` | JSONB | 컨셉 후보 목록 |
| `selected_concept_index` | Integer | 선택된 컨셉 인덱스 |
| `deleted_at` | DateTime | Soft Delete 타임스탬프 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

### `creative_session_rounds`
세션 내의 각 토의 라운드 요약.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `session_id` | Integer (FK) | 소속 세션 |
| `round_number` | Integer | 라운드 번호 |
| `leader_summary` | Text | 리더의 라운드 요약 |
| `round_decision` | String(20) | 라운드 결정 (`revise`, `approve` 등) |
| `best_agent_role` | String(50) | 최고 점수 에이전트 역할 |
| `best_score` | Float | 최고 점수 |
| `leader_direction` | Text | 다음 라운드 지시사항 |
| `created_at` | DateTime | 생성 시각 (server_default: now()) |

### `creative_traces`
개별 에이전트의 LLM 호출 및 생각(Thought) 추적.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `session_id` | Integer (FK) | 소속 세션 |
| `round_number` | Integer | 라운드 번호 |
| `sequence` | Integer | 순서 |
| `trace_type` | String(20) | `thought`, `action`, `observation` |
| `agent_role` | String(50) | 에이전트 역할 |
| `agent_preset_id` | Integer (FK) | 사용된 프리셋 |
| `input_prompt` | Text | 입력 프롬프트 |
| `output_content` | Text | LLM 응답 |
| `score` | Float | 평가 점수 |
| `feedback` | Text | 피드백 |
| `model_id` | String(100) | 사용된 모델 ID |
| `token_usage` | JSONB | 토큰 사용량 |
| `latency_ms` | Integer | 응답 시간 (ms) |
| `temperature` | Float | 생성 온도 |
| `parent_trace_id` | Integer (FK → creative_traces, SET NULL) | 부모 트레이스 (self-ref) |
| `diff_summary` | Text | 변경 요약 |
| `created_at` | DateTime | 생성 시각 (server_default: now()) |
| **V2** | | |
| `phase` | String(20) | 단계명 |
| `step_name` | String(50) | 스텝명 |
| `target_agent` | String(50) | 대상 에이전트 |
| `decision_context` | JSONB | 결정 컨텍스트 |
| `retry_count` | Integer | 재시도 횟수 (default: 0) |

---

## 🔗 Association Tables (V3 Relational Tags)

### `storyboard_characters`
스토리보드 내 화자(Speaker)와 캐릭터 매핑 (Dialogue).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `storyboard_id` | Integer (FK) | |
| `speaker` | String(10) | 화자 라벨 (`A`, `B` 등) |
| `character_id` | Integer (FK) | 매핑된 캐릭터 |

### `character_tags`
캐릭터 ↔ 태그 연결.

| Column | Type | Description |
|--------|------|-------------|
| `character_id` | Integer (PK, FK → characters) | |
| `tag_id` | Integer (PK, FK → tags) | |
| `weight` | Float | 태그 가중치 (default: 1.0) |
| `is_permanent` | Boolean | 항상 포함 여부 (아래 참조) |

**`is_permanent`와 레이어 배치 규칙** (V3 Prompt Pipeline):
- `is_permanent=true` → **LAYER_IDENTITY(2)에 강제 배치**, `tag.default_layer` 무시
- `is_permanent=false` → `tag.default_layer` 사용

> **Known Issue**: `is_permanent`가 "항상 포함"과 "캐릭터 identity"를 혼용하고 있음.
> `anime_style`(스타일=L11), `solo`(subject=L1) 같은 비-identity 태그도 permanent로 등록되면
> LAYER_IDENTITY(2)에 강제 배치되어 의미론적 오분류 발생.
> → `PROMPT_PIPELINE_SPEC.md` Known Issue #2 참조

### `scene_tags`
씬 ↔ 태그 연결 (환경/분위기 태그).

| Column | Type | Description |
|--------|------|-------------|
| `scene_id` | Integer (PK, FK → scenes) | |
| `tag_id` | Integer (PK, FK → tags) | |
| `weight` | Float | 태그 가중치 (default: 1.0) |

### `scene_character_actions`
씬 내 캐릭터별 액션/표정 태그.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `scene_id` | Integer (FK → scenes) | |
| `character_id` | Integer (FK → characters) | |
| `tag_id` | Integer (FK → tags) | 액션/표정 태그 |
| `weight` | Float | 태그 가중치 (default: 1.0) |

---

## 🏷️ Tag System

### `tags`
프롬프트 키워드의 마스터 테이블 (12-Layer 시맨틱 데이터).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(100) | Unique, 언더바 형식 (`brown_hair`) |
| `ko_name` | String(100) | 한국어 이름 |
| `category` | String(50) | `character`, `scene`, `meta` |
| `group_name` | String(50) | 의미론적 그룹 (`hair_color`, `expression`, `camera` 등 24종) |
| `description` | String(500) | 태그 설명 |
| `default_layer` | Integer | 12-Layer 위치 (0-11, 아래 매핑 참조) |
| `usage_scope` | String(20) | `PERMANENT`, `TRANSIENT`, `ANY` |
| `priority` | Integer | 정렬 우선순위 (default: 100) |
| `classification_source` | String(20) | `pattern`, `danbooru`, `llm`, `manual` |
| `classification_confidence` | Float | 분류 신뢰도 (0.0-1.0) |
| `wd14_count` | Integer | WD14 출현 횟수 |
| `wd14_category` | Integer | WD14 카테고리 코드 |
| `is_active` | Boolean | 태그 활성화 상태 (default: TRUE) |
| `deprecated_reason` | String(200) | 비활성화 이유 |
| `replacement_tag_id` | Integer (FK → tags, SET NULL) | 대체 태그 ID |

> **Removed**: `subcategory` 컬럼 (deprecated Phase 6-4.25, removed Phase 6-4.26)
> **Added** (Phase 6-4.15.8): `is_active`, `deprecated_reason`, `replacement_tag_id` - DB 기반 태그 비활성화 시스템

**`default_layer` 매핑** (V3 12-Layer System):

| 값 | 상수 | 용도 | 예시 태그 |
|----|------|------|-----------|
| 0 | LAYER_QUALITY | 품질 태그 | `masterpiece`, `best_quality`, `highres` |
| 1 | LAYER_SUBJECT | 주체 | `1boy`, `1girl`, `solo` |
| 2 | LAYER_IDENTITY | 캐릭터 LoRA/트리거 | (주로 character_tags에서 배치) |
| 3 | LAYER_BODY | 체형 | `super_deformed`, `tall`, `slim` |
| 4 | LAYER_MAIN_CLOTH | 주요 의상 | `blue_shirt`, `school_uniform` |
| 5 | LAYER_DETAIL_CLOTH | 의상 디테일 | `striped`, `frills` |
| 6 | LAYER_ACCESSORY | 악세서리 | `glasses`, `hat` |
| 7 | LAYER_EXPRESSION | 표정/시선 | `smile`, `looking_at_viewer` |
| 8 | LAYER_ACTION | 포즈/동작 | `standing`, `walking`, `adjusting_hair` |
| 9 | LAYER_CAMERA | 카메라 앵글 | `upper_body`, `close_up`, `from_above` |
| 10 | LAYER_ENVIRONMENT | 배경/장소 | `office`, `indoors`, `outdoors` |
| 11 | LAYER_ATMOSPHERE | 스타일/분위기/조명 | `anime_style`, `melancholic`, `day` |

> Fallback: DB에 없는 태그는 `LAYER_SUBJECT(1)`로 배치됨.
> 코드 위치: `backend/services/prompt/v3_composition.py` L12-23

### `tag_rules`
태그 간 충돌/의존성 규칙 (개별 태그 레벨).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `rule_type` | String(20) | `conflict` or `requires` |
| `source_tag_id` | Integer | 충돌 소스 태그 |
| `target_tag_id` | Integer | 충돌 대상 태그 |
| `message` | String(200) | 규칙 설명 |
| `priority` | Integer | 우선순위 |
| `active` | Boolean | 활성 여부 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

> **Removed**: `source_category`, `target_category` (Phase 6-4.26)
> 카테고리 간 충돌은 논리적으로 불가능. 모든 충돌은 개별 태그 레벨에서만 발생.

### `tag_aliases`
위험/비표준 태그의 자동 치환 규칙.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `source_tag` | String(100) | 변환 전 (`medium shot`) |
| `target_tag` | String(100) | 변환 후 (`cowboy_shot`), NULL = 삭제 |
| `reason` | String(200) | 치환 사유 |
| `active` | Boolean | 활성 여부 (Known Issue: `is_active`로 변경 예정) |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

### `tag_filters`
무시/스킵할 태그 관리.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `tag_name` | String(100) | Unique, 필터 대상 태그 |
| `filter_type` | String(20) | `ignore` or `skip` |
| `reason` | String(200) | 필터 사유 |
| `active` | Boolean | 활성 여부 (Known Issue: `is_active`로 변경 예정) |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

### `classification_rules`
패턴 기반 태그 자동 분류 규칙.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `rule_type` | String(20) | `suffix`, `prefix`, `contains`, `exact` |
| `pattern` | String(100) | 매칭 패턴 (`_hair`, `eyes`) |
| `target_group` | String(50) | 대상 그룹 |
| `priority` | Integer | 평가 순서 |
| `active` | Boolean | 활성 여부 (Known Issue: `is_active`로 변경 예정) |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

### `tag_effectiveness`
WD14 피드백 루프 데이터.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `tag_id` | Integer (FK → tags) | |
| `use_count` | Integer | 프롬프트 사용 횟수 |
| `match_count` | Integer | WD14 감지 횟수 |
| `effectiveness` | Float | `match_count / use_count` |

---

## 🎨 Asset System

### `media_assets` (V3.1)
통합 미디어 저장소. S3/Local 스토리지 폴리모픽 참조 시스템.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `owner_type` | String(50) | 폴리모픽 타입 (`character`, `scene`, `lora`, `sdmodel`, `storyboard`, `project`) |
| `owner_id` | Integer | 폴리모픽 ID |
| `file_name` | String(255) | 원본 파일명 |
| `file_type` | String(20) | `image`, `video`, `audio`, `cache`, `candidate` |
| `storage_key` | String(500) | 스토리지 경로 |
| `file_size` | BigInteger | 파일 크기 (bytes) |
| `mime_type` | String(100) | `image/png`, `video/mp4` 등 |
| `is_temp` | Boolean | 임시 파일 여부 (GC 대상) |
| `checksum` | String(64) | 파일 SHA-256 해시 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

**특징**:
- **폴리모픽 연관**: `owner_type` + `owner_id`로 모든 엔티티 연결
- **URL 생성**: `url` property가 storage_key 기반 public URL 반환 (`http://minio:9000/shorts-producer/{storage_key}`)
- **S3/Local 통합**: LocalStorage/S3Storage 모두 지원
- **계층 구조**:
  - 영상: `projects/{p_id}/groups/{g_id}/storyboards/{s_id}/videos/{file}`
  - 씬 이미지: `projects/{p_id}/groups/{g_id}/storyboards/{s_id}/images/{file}`
  - 캐릭터: `characters/{id}/preview/{file}`
  - 공유 에셋: `shared/{type}/{file}` (audio, fonts, overlay, references, poses)

**마이그레이션**:
- `ca169902f4a4`: 모든 모델에 `*_asset_id` FK 추가
- `4249c8f1cd5c`: Legacy `*_url` 컬럼 삭제

**중요**: `storage_key`는 버킷명(`shorts-producer`)을 포함하지 않음. `get_storage().get_url(key)`가 버킷명을 자동 추가.

### `characters`
캐릭터 프리셋. V3에서는 `character_tags` 관계형 테이블로 태그 연결.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `project_id` | Integer (FK → projects, SET NULL) | 소속 프로젝트 |
| `name` | String(100) | Unique |
| `gender` | String(10) | `female`, `male` |
| `description` | String(500) | |
| **Prompt** | | |
| `loras` | JSONB | LoRA 설정 (아래 구조 참조) |
| `recommended_negative` | Text[] | 캐릭터별 네거티브 |
| `custom_base_prompt` | Text | V3 compose 입력: LAYER_IDENTITY(2)에 배치 |
| `custom_negative_prompt` | Text | Frontend `buildNegativePrompt()` 입력 |
| `reference_base_prompt` | Text | 레퍼런스 이미지 전용 (V3 compose 미사용) |
| `reference_negative_prompt` | Text | 레퍼런스 이미지 전용 |
| `prompt_mode` | String(20) | `auto`, `standard`, `lora` |
| **IP-Adapter** | | |
| `ip_adapter_weight` | Float | 0.0-1.0 |
| `ip_adapter_model` | String(50) | `clip`, `clip_face`, `faceid` |
| **Voice** | | |
| `voice_preset_id` | Integer (FK → voice_presets, SET NULL) | 캐릭터 고유 음성 프리셋 |
| **Display** | | |
| `preview_image_asset_id` | Integer (FK → media_assets) | 미리보기 이미지 (폴리모픽 참조) |
| `preview_locked` | Boolean | 미리보기 자동 갱신 잠금 (default: false) |
| `deleted_at` | DateTime | Soft Delete 타임스탬프 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

**Read-only 속성**:
- `preview_image_url` (`@property`): `preview_image_asset.url` 반환

> v3.5 변경: `voice_preset_id` FK 추가 (旧 `default_voice_preset_id`, v3.7 리네이밍), `deleted_at` Soft Delete 추가

**V3 Prompt Pipeline에서의 사용** (→ `PROMPT_PIPELINE_SPEC.md` 참조):
| 필드 | V3 compose 사용 | 용도 |
|------|:-:|------|
| `character.tags[]` (via character_tags) | O | `is_permanent` 기반 레이어 배치 |
| `custom_base_prompt` | O | comma split → LAYER_IDENTITY(2), 배경 태그 필터 |
| `loras` | O | trigger words + `<lora:>` → LAYER_IDENTITY(2) |
| `gender` | O | male → gender enhancement → LAYER_SUBJECT(1) |
| `prompt_mode` | O | `"standard"`이면 LoRA 주입 스킵 |
| `custom_negative_prompt` | X | Frontend 로컬 처리 |
| `reference_base_prompt` | X | 레퍼런스 이미지 전용 |
| `reference_negative_prompt` | X | 레퍼런스 이미지 전용 |

> V3 변경: `identity_tags Integer[]`, `clothing_tags Integer[]` 제거 → `character_tags` 테이블로 이관
> V3.1 변경: `preview_image_url` 제거 → `preview_image_asset_id` FK로 전환
> V3.1.1 변경: `preview_locked` 추가 (2026-02-01)

### `loras`
Stable Diffusion LoRA 모델.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(100) | Unique, 파일명/키 |
| `display_name` | String(100) | 표시명 |
| `lora_type` | String(20) | `character`, `style`, `concept`, `pose` |
| `gender_locked` | String(10) | 성별 제한 |
| `civitai_id` | Integer | Civitai ID |
| `civitai_url` | String(500) | |
| `trigger_words` | Text[] | 트리거 키워드 |
| `default_weight` | Decimal(3,2) | 기본 가중치 |
| `optimal_weight` | Decimal(3,2) | 보정된 최적 가중치 |
| `calibration_score` | Integer | 최적 가중치 시 점수 |
| `weight_min`, `weight_max` | Decimal(3,2) | 가중치 범위 |
| `preview_image_asset_id` | Integer (FK → media_assets) | 미리보기 이미지 (폴리모픽 참조) |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

**Read-only 속성**:
- `preview_image_url` (`@property`): `preview_image_asset.url` 반환

### `sd_models`
Stable Diffusion 체크포인트.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(200) | Unique |
| `display_name` | String(200) | |
| `model_type` | String(50) | `checkpoint`, `vae` |
| `base_model` | String(50) | `SD1.5`, `SDXL`, `Pony` |
| `civitai_id` | Integer | |
| `civitai_url` | String(500) | |
| `description` | Text | |
| `preview_image_asset_id` | Integer (FK → media_assets) | 미리보기 이미지 (폴리모픽 참조) |
| `is_active` | Boolean | |

**Read-only 속성**:
- `preview_image_url` (`@property`): `preview_image_asset.url` 반환

### `style_profiles`
Model + LoRAs + Embeddings 번들.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(100) | Unique |
| `display_name` | String(200) | 표시명 |
| `description` | Text | 설명 |
| `sd_model_id` | Integer (FK → sd_models, SET NULL) | 베이스 체크포인트 |
| `loras` | JSONB | LoRA 목록 |
| `positive_embeddings` | Integer[] | Embedding IDs |
| `negative_embeddings` | Integer[] | Embedding IDs |
| `default_positive` | Text | 기본 포지티브 |
| `default_negative` | Text | 기본 네거티브 |
| `is_default` | Boolean | |
| `is_active` | Boolean | |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

### `render_presets`
재사용 가능한 렌더링 설정 프리셋. Project/Group에서 참조.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(200) | 프리셋 이름 |
| `description` | Text | 설명 |
| `is_system` | Boolean | 시스템 프리셋 여부 (default: true) |
| **Audio** | | |
| `bgm_mode` | String(20) | BGM 모드 (`"file"` = 파일, `"ai"` = AI 생성, default: `"file"`) |
| `bgm_file` | String(255) | BGM 파일 경로 (`"random"` = 랜덤, `bgm_mode="file"` 시 사용) |
| `music_preset_id` | Integer (FK → music_presets, SET NULL) | AI BGM 프리셋 (`bgm_mode="ai"` 시 사용) |
| `bgm_volume` | Float | BGM 볼륨 (0.0~1.0) |
| `audio_ducking` | Boolean | 오디오 더킹 여부 |
| `speed_multiplier` | Float | 재생 속도 배율 |
| **Visual** | | |
| `layout_style` | String(50) | 레이아웃 (`full`, `post`) |
| `frame_style` | String(255) | 프레임 스타일 |
| `scene_text_font` | String(255) | Scene Text 폰트 (파일명) |
| `transition_type` | String(50) | 전환 효과 |
| `ken_burns_preset` | String(50) | Ken Burns 프리셋 |
| `ken_burns_intensity` | Float | Ken Burns 강도 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

> v3.5 변경: `narrator_voice`, `tts_engine`, `voice_design_prompt` 제거 → `voice_preset_id` FK로 대체
> v3.10 변경: `voice_preset_id` 제거 → `group_config.narrator_voice_preset_id`로 이관 (음성은 GroupConfig에서만 관리)
> v3.12 변경: `bgm_mode`, `music_preset_id` FK 추가 — AI BGM 생성 지원

### `voice_presets`
재사용 가능한 음성 프리셋. TTS 렌더링 시 사용.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(200) | 프리셋 이름 |
| `description` | Text | 설명 |
| `source_type` | String(20) | `generated` (VoiceDesign) 또는 `uploaded` (파일) |
| `tts_engine` | String(20) | TTS 엔진 (현재 `qwen`) |
| `audio_asset_id` | Integer (FK → media_assets, SET NULL) | 음성 파일 |
| `voice_design_prompt` | Text | VoiceDesign 프롬프트 |
| `language` | String(20) | 언어 (default: `korean`) |
| `sample_text` | Text | 샘플 텍스트 |
| `voice_seed` | Integer | 음성 시드 (VoiceDesign 재현용) |
| `is_system` | Boolean | 시스템 프리셋 여부 (default: false) |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

**Read-only 속성**:
- `audio_url` (`@property`): `audio_asset.url` 반환 (Known Issue: 별도 DB 세션 생성 안티패턴)

### `music_presets`
재사용 가능한 AI BGM 생성 프리셋. `render_presets`에서 참조.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(200) | 프리셋 이름 |
| `description` | Text | 설명 |
| `prompt` | Text | AI 음악 생성 프롬프트 |
| `duration` | Float | 음악 길이 (초) |
| `seed` | Integer | 생성 시드 |
| `audio_asset_id` | Integer (FK → media_assets, SET NULL) | 생성된 오디오 파일 |
| `is_system` | Boolean | 시스템 프리셋 여부 (default: false) |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

> v3.12 추가: AI BGM 생성을 위한 프리셋 테이블. `render_presets.music_preset_id`에서 참조.

### `embeddings`
Textual Inversion 임베딩.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(200) | Unique |
| `display_name` | String(200) | |
| `embedding_type` | String(50) | |
| `trigger_word` | String(100) | |
| `description` | Text | |
| `is_active` | Boolean | |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

---

## 📊 Analytics & History

### `activity_logs`
생성 이력 로그 (Analytics & Tracking).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `storyboard_id` | Integer (FK → storyboards, SET NULL) | 소속 스토리보드 |
| `scene_id` | Integer (FK → scenes, SET NULL) | 소속 씬 |
| `character_id` | Integer (FK → characters, SET NULL) | 캐릭터 ID |
| `prompt` | Text | 사용된 프롬프트 |
| `negative_prompt` | Text | 네거티브 프롬프트 |
| `sd_params` | JSONB | `{steps, cfg_scale, sampler, ...}` |
| `seed` | BigInteger | 생성 시드 |
| `media_asset_id` | Integer (FK → media_assets, SET NULL) | 생성된 이미지 |
| `match_rate` | Float | WD14 매치율 |
| `tags_used` | JSONB | 사용된 태그 배열 |
| `status` | String(20) | `success`, `fail` |
| `gemini_edited` | Boolean | Gemini 자동 편집 여부 |
| `gemini_cost_usd` | Float | Gemini 편집 비용 |
| `original_match_rate` | Float | 편집 전 매치율 |
| `final_match_rate` | Float | 편집 후 매치율 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

**Read-only 속성**:
- `image_url` (`@property`): `media_asset.url` 반환

### `render_history`
영상 렌더링 및 YouTube 업로드 이력.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `storyboard_id` | Integer (FK) | 소속 스토리보드 |
| `media_asset_id` | Integer (FK) | 렌더링된 영상 파일 |
| `label` | String(20) | 버전/라벨 |
| `youtube_video_id` | String(20) | 업로드된 영상 ID |
| `youtube_upload_status` | String(20) | 업로드 상태 |
| `youtube_uploaded_at` | DateTime | 업로드 시각 |

### `lab_experiments`
태그 렌더링, 씬 번역 등 실험실 기능 이력 (旧 evaluation_runs 대체).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `batch_id` | String(50) | 배치 ID (인덱스) |
| `experiment_type` | String(20) | `tag_render`, `scene_translate` |
| `status` | String(20) | `pending`, `completed`, `failed` |
| `character_id` | Integer (FK → characters, SET NULL) | 대상 캐릭터 (nullable) |
| `group_id` | Integer (FK → groups, CASCADE) | 소속 그룹 (필수) |
| `prompt_used` | Text | 사용된 프롬프트 |
| `negative_prompt` | Text | 네거티브 프롬프트 |
| `final_prompt` | Text | V3 Prompt Engine 최종 프롬프트 |
| `loras_applied` | JSONB | 적용된 LoRA 목록 |
| `target_tags` | JSONB | 타겟 태그 |
| `sd_params` | JSONB | SD 생성 파라미터 |
| `media_asset_id` | Integer (FK → media_assets, SET NULL) | 생성된 이미지 |
| `seed` | BigInteger | 생성 시드 |
| `match_rate` | Float | 결과 매치율 |
| `wd14_result` | JSONB | 상세 분석 결과 |
| `scene_description` | Text | 씬 번역 설명 (scene_translate용) |
| `notes` | Text | 사용자 메모 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

### `scene_quality_scores`
장면별 품질 점수 및 WD14 검증 결과 전용 스토어.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `storyboard_id` | Integer | 스토리보드 ID (인덱스, FK 없음) |
| `scene_id` | Integer (FK → scenes, CASCADE) | 씬 ID |
| `prompt` | Text | 사용된 프롬프트 |
| `match_rate` | Float | WD14 매치율 |
| `matched_tags`, `missing_tags`, `extra_tags` | JSONB | 상세 태그 분석 결과 |
| `validated_at` | DateTime | 검증 일시 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

**Read-only 속성**:
- `image_url` (`@property`): `scene.image_asset.url` 반환

### `prompt_histories`
저장된 프롬프트 설정.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | |
| `name` | String(200) | |
| `positive_prompt` | Text | |
| `negative_prompt` | Text | |
| `steps`, `cfg_scale`, `seed`, `clip_skip` | Integer/Float | SD 파라미터 |
| `sampler_name` | String | 샘플러 이름 |
| `character_id` | Integer | (인덱스, FK 없음 — Known Issue) |
| `lora_settings` | JSONB | |
| `context_tags` | JSONB | |
| `last_match_rate`, `avg_match_rate` | Float | |
| `validation_count` | Integer | |
| `is_favorite` | Boolean | |
| `use_count` | Integer | |
| `deleted_at` | DateTime | Soft Delete 타임스탬프 |
| `created_at`, `updated_at` | DateTime | 타임스탬프 |

---

## 📝 JSONB Structures

### `Character.loras`
```json
[
  {
    "lora_id": 5,
    "weight": 1.0,
    "name": "flat_color",
    "trigger_words": ["flat color"],
    "lora_type": "character"
  }
]
```

**V3 Pipeline 처리**: `lora_type`에 관계없이 현재 모두 LAYER_IDENTITY(2)에 배치.
→ Known Issue: `lora_type=style`은 LAYER_ATMOSPHERE(11)에 배치해야 함.

### `Scene.context_tags`
```json
{
  "expression": ["expressionless"],
  "gaze": "looking_at_viewer",
  "pose": ["standing"],
  "action": ["adjusting_hair"],
  "camera": "upper_body",
  "environment": ["office", "indoors"],
  "mood": ["melancholic"]
}
```

**V3 Pipeline 처리**: `_collect_context_tags()`에서 flat list로 변환 후 scene_tags에 병합.

### `ActivityLog.sd_params`
```json
{"steps": 20, "cfg_scale": 7, "sampler": "DPM++ 2M Karras", "width": 512, "height": 768}
```

---

## 🔑 Enums

| Enum | Values |
|------|--------|
| `Tag.usage_scope` | `PERMANENT`, `TRANSIENT`, `ANY` |
| `Tag.classification_source` | `pattern`, `danbooru`, `llm`, `manual` |
| `LoRA.lora_type` | `character`, `style`, `concept`, `pose` |
| `Character.prompt_mode` | `auto`, `standard`, `lora` |
| `TagRule.rule_type` | `conflict`, `requires` |
| `TagAlias.target_tag` | String or `NULL` (= remove tag) |
| `TagFilter.filter_type` | `ignore`, `skip` |
| `RenderPreset.bgm_mode` | `file`, `ai` |
| `ActivityLog.status` | `success`, `fail` |
| `CreativeSession.status` | `pending`, `running`, `completed`, `failed` |
| `CreativeSessionRound.round_decision` | `revise`, `approve`, `reject` |
| `CreativeTrace.trace_type` | `thought`, `action`, `observation` |
| `RenderHistory.youtube_upload_status` | `pending`, `uploaded`, `failed` |
| `LabExperiment.experiment_type` | `tag_render`, `scene_translate` |
| `LabExperiment.status` | `pending`, `completed`, `failed` |

---

## 📐 Column Ordering Convention

모든 테이블의 ORM 모델(`models/*.py`)에서 컬럼 선언 순서를 아래 규칙으로 통일합니다.

```
1. PK          — id
2. Parent FK   — project_id, group_id, storyboard_id 등 (소속 관계)
3. Identity    — name, title 등 (사람이 식별하는 필드)
4. Metadata    — description, gender, is_system 등
5. Domain      — 도메인 고유 필드 (그룹별로 구분)
                 예: Render → Audio 그룹, Visual 그룹
                 예: Character → Prompt, IP-Adapter, Voice
6. Asset FK    — preview_image_asset_id, video_asset_id 등
7. Config FK   — voice_preset_id, render_preset_id 등
8. Flags       — preview_locked, is_active, deleted_at 등
9. Timestamps  — created_at, updated_at (TimestampMixin)
```

**참고**: PostgreSQL은 `ALTER TABLE DROP COLUMN` 후 ordinal_position에 구멍이 생길 수 있음.
물리적 컬럼 순서는 성능에 영향 없으므로, ORM 모델의 선언 순서를 기준으로 합니다.

---

**Last Updated:** 2026-02-10
**Schema Version:** v3.15
**ORM:** SQLAlchemy 2.0 (Mapped Columns)
**Migrations:** Alembic
