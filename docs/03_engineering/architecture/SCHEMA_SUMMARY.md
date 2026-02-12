# Database Schema Summary

Shorts Producer 스키마 요약. 상세 명세는 [DB_SCHEMA.md](./DB_SCHEMA.md) (v3.20) 참조.

> **Last Synced:** 2026-02-12 (DB_SCHEMA v3.20 기준)

---

## Core: Channel & Storyboard

### `projects` — YouTube 채널 단위
- `id` (PK), `name`, `description`, `handle`
- `avatar_media_asset_id` (FK → media_assets)
- @property: `avatar_key`, `avatar_url`

### `youtube_credentials` — 프로젝트별 YouTube OAuth (1:1)
- `id` (PK), `project_id` (FK, UNIQUE), `channel_id`, `channel_title`
- `encrypted_token`, `is_valid`

### `groups` — 프로젝트 내 시리즈/카테고리
- `id` (PK), `project_id` (FK → projects), `name`, `description`

### `group_config` — Group별 설정 (1:1 분리 테이블)
- `id` (PK), `group_id` (FK, UNIQUE)
- `render_preset_id` (FK), `style_profile_id` (FK), `narrator_voice_preset_id` (FK)
- `language`, `structure`, `duration`
- `sd_steps`, `sd_cfg_scale` 등 SD 파라미터 오버라이드

### `storyboards` — 개별 에피소드
- `id` (PK), `group_id` (FK → groups), `title`, `description`
- `caption`, `structure` (String, default: `"Monologue"`)
- `duration` (Integer, nullable), `language` (String(20), nullable) — GroupConfig에서 상속 가능
- `version` (Integer, NOT NULL, default 1) — Optimistic Locking. PUT/PATCH 시 검증, 성공 시 +1
- `deleted_at` (Soft Delete)

### `scenes` — 스토리보드 내 개별 씬
- `id` (PK), `client_id` (String(36), UNIQUE, NOT NULL — Frontend UUID 안정 식별자)
- `storyboard_id` (FK), `order`, `script`, `description`, `speaker`, `duration`
- **Prompt**: `image_prompt`, `image_prompt_ko`, `negative_prompt`, `context_tags` (JSONB)
- **Size**: `width`, `height`
- **Background**: `background_id` (FK → backgrounds, SET NULL)
- **IP-Adapter/Ref**: `use_reference_only`, `reference_only_weight`, `environment_reference_id` (FK), `environment_reference_weight`, `use_ip_adapter`, `ip_adapter_reference`, `ip_adapter_weight`
- **ControlNet**: `use_controlnet`, `controlnet_weight`
- **Generation**: `scene_mode` (`single`/`multi`), `multi_gen_enabled`, `image_asset_id` (FK), `candidates` (JSONB)
- `deleted_at` (Soft Delete)

---

## Association Tables (V3 Relational Tags)

### `storyboard_characters` — 화자↔캐릭터 매핑
- `id` (PK), `storyboard_id` (FK), `speaker`, `character_id` (FK)

### `character_tags` — 캐릭터↔태그
- `character_id` (PK, FK), `tag_id` (PK, FK), `weight`, `is_permanent`

### `scene_tags` — 씬↔태그
- `scene_id` (PK, FK), `tag_id` (PK, FK), `weight`

### `scene_character_actions` — 씬 내 캐릭터 액션
- `id` (PK), `scene_id` (FK), `character_id` (FK), `tag_id` (FK), `weight`

---

## Asset System

### `media_assets` — 통합 미디어 저장소 (S3/Local)
- `id` (PK), `owner_type`, `owner_id` (Polymorphic)
- `file_name`, `file_type`, `storage_key`, `file_size`, `mime_type`
- `is_temp`, `checksum`

### `characters` — 캐릭터 프리셋
- `id` (PK), `project_id` (FK → projects, SET NULL), `name` (Unique), `gender`, `description`
- **Prompt**: `loras` (JSONB), `custom_base_prompt`, `custom_negative_prompt`, `recommended_negative` (ARRAY), `reference_base_prompt`, `reference_negative_prompt`, `prompt_mode`
- **IP-Adapter**: `ip_adapter_weight`, `ip_adapter_model`
- **Voice**: `voice_preset_id` (FK → voice_presets)
- `preview_image_asset_id` (FK), `preview_locked`, `deleted_at`

### `loras` — LoRA 모델
- `id` (PK), `name` (Unique), `display_name`, `lora_type`, `trigger_words`
- `default_weight`, `optimal_weight`, `calibration_score`
- `civitai_id`, `civitai_url`, `preview_image_asset_id` (FK)

### `sd_models` — SD 체크포인트
- `id` (PK), `name` (Unique), `display_name`, `model_type`, `base_model`
- `civitai_id`, `preview_image_asset_id` (FK), `is_active`

### `style_profiles` — Model + LoRA 번들
- `id` (PK), `name` (Unique), `display_name`, `description`
- `sd_model_id` (FK), `loras` (JSONB)
- `negative_embeddings` (ARRAY), `positive_embeddings` (ARRAY)
- `default_positive`, `default_negative`
- `is_default`, `is_active`

### `embeddings` — 임베딩 모델
- `id` (PK), `name` (Unique), `display_name`
- `embedding_type` (`negative`/`positive`/`style`), `trigger_word`
- `description`, `is_active`

---

## Presets

### `render_presets` — 렌더링 설정 프리셋
- `id` (PK), `name`, `description`, `is_system`
- **Audio**: `bgm_mode` (`file`/`ai`), `bgm_file`, `music_preset_id` (FK), `bgm_volume`, `audio_ducking`, `speed_multiplier`
- **Visual**: `layout_style`, `frame_style`, `scene_text_font`, `transition_type`, `ken_burns_preset`, `ken_burns_intensity`

### `voice_presets` — 음성 프리셋
- `id` (PK), `name`, `description`
- `source_type` (`generated`/`uploaded`), `tts_engine`
- `audio_asset_id` (FK), `voice_design_prompt`, `language`, `sample_text`, `voice_seed`, `is_system`

### `music_presets` — AI BGM 프리셋
- `id` (PK), `name`, `description`, `prompt`, `duration`, `seed`
- `audio_asset_id` (FK), `is_system`

---

## Tag System

### `tags` — 프롬프트 키워드 마스터 (12-Layer)
- `id` (PK), `name` (Unique, 언더바 형식), `ko_name`, `category`, `group_name`
- `default_layer` (0-11), `usage_scope`, `priority`
- `classification_source`, `classification_confidence`
- `is_active`, `deprecated_reason`, `replacement_tag_id` (FK)

### `tag_rules` — 태그 충돌/의존성 규칙
- `id` (PK), `rule_type` (`conflict`/`requires`), `source_tag_id`, `target_tag_id`
- `message`, `priority`, `active`

### `tag_aliases` — 비표준 태그 자동 치환
- `id` (PK), `source_tag`, `target_tag` (NULL=삭제), `reason`, `active`

### `tag_filters` — 무시/스킵 태그
- `id` (PK), `tag_name` (Unique), `filter_type` (`ignore`/`skip`), `reason`, `active`

### `tag_effectiveness` — WD14 피드백 루프
- `id` (PK), `tag_id` (FK), `use_count`, `match_count`, `effectiveness`

---

## Creative Engine

### `creative_sessions` — 멀티 에이전트 창작 세션
- `id` (PK), `objective`, `evaluation_criteria` (JSONB), `agent_config` (JSONB)
- `character_id` (FK), `context` (JSONB), `final_output` (JSONB), `max_rounds`, `total_token_usage` (JSONB), `status`
- **V2**: `session_type`, `director_mode`, `concept_candidates` (JSONB), `selected_concept_index`
- `deleted_at` (Soft Delete)

### `creative_session_rounds` — 라운드별 요약
- `id` (PK), `session_id` (FK), `round_number`, `leader_summary`, `round_decision`
- `best_agent_role`, `best_score`, `leader_direction`

### `creative_traces` — 에이전트 LLM 호출 추적
- `id` (PK), `session_id` (FK), `round_number`, `sequence`
- `trace_type`, `agent_role`, `agent_preset_id` (FK)
- `input_prompt`, `output_content`, `score`, `feedback`
- `model_id`, `token_usage` (JSONB), `latency_ms`, `temperature`
- `parent_trace_id` (FK, self-ref), `diff_summary`
- **V2**: `phase`, `step_name`, `target_agent`, `decision_context` (JSONB), `retry_count`

### `creative_agent_presets` — 에이전트 페르소나 프리셋
- `id` (PK), `name` (Unique), `role_description`, `system_prompt`
- `agent_role` (String(50)), `category` (String(30)) — V2 Agent Presets
- `model_provider`, `model_name`, `temperature`, `agent_metadata` (JSONB), `is_system`
- `deleted_at` (Soft Delete)

---

## Analytics & History

### `activity_logs` — 이미지 생성 이력
- `id` (PK), `storyboard_id` (FK), `scene_id` (FK), `character_id` (FK)
- `prompt`, `negative_prompt`, `sd_params` (JSONB), `seed`
- `media_asset_id` (FK → media_assets), `match_rate`, `tags_used` (JSONB), `status`
- `gemini_edited`, `gemini_cost_usd`, `original_match_rate`, `final_match_rate`

### `render_history` — 영상 렌더링 이력
- `id` (PK), `storyboard_id` (FK), `media_asset_id` (FK), `label`
- `youtube_video_id`, `youtube_upload_status`, `youtube_uploaded_at`

### `lab_experiments` — 실험실 기능 이력
- `id` (PK), `batch_id`, `experiment_type`, `status`
- `character_id` (FK), `group_id` (FK → groups, CASCADE)
- `prompt_used`, `negative_prompt`, `final_prompt`, `loras_applied` (JSONB)
- `target_tags` (JSONB), `sd_params` (JSONB), `media_asset_id` (FK), `seed`
- `match_rate`, `wd14_result` (JSONB), `scene_description`, `notes`

### `scene_quality_scores` — 씬 품질 점수
- `id` (PK), `storyboard_id` (인덱스, FK 없음), `scene_id` (FK → scenes)
- `prompt`, `match_rate`
- `matched_tags`, `missing_tags`, `extra_tags` (JSONB)

### `prompt_histories` — 프롬프트 히스토리
- `id` (PK), `name`, `positive_prompt`, `negative_prompt`
- SD 파라미터 (`steps`, `cfg_scale`, `sampler_name`, `seed`, `clip_skip`), `character_id` (인덱스, FK 없음), `lora_settings` (JSONB), `context_tags` (JSONB)
- `last_match_rate`, `avg_match_rate`, `is_favorite`, `use_count`
- `deleted_at` (Soft Delete)
