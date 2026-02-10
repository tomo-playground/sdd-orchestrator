# Database Schema Summary

Shorts Producer 스키마 요약. 상세 명세는 [DB_SCHEMA.md](./DB_SCHEMA.md) (v3.14) 참조.

> **Last Synced:** 2026-02-10 (DB_SCHEMA v3.14 기준)

---

## Core: Channel & Storyboard

### `projects` — YouTube 채널 단위
- `id` (PK), `name`, `description`, `handle`, `avatar_key`
- `avatar_asset_id` (FK → media_assets), `render_preset_id` (FK), `style_profile_id` (FK)

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
- `caption`, `structure` (String, default from config)
- `deleted_at` (Soft Delete)

### `scenes` — 스토리보드 내 개별 씬
- `id` (PK), `storyboard_id` (FK), `order`, `script`, `description`, `speaker`, `duration`
- **Prompt**: `image_prompt`, `image_prompt_ko`, `negative_prompt`, `context_tags` (JSONB)
- **SD Params**: `steps`, `cfg_scale`, `sampler_name`, `seed`, `clip_skip`, `width`, `height`
- **IP-Adapter**: `use_reference_only` (Boolean), `reference_only_weight`
- **Environment**: `environment_reference_id` (FK → media_assets), `environment_reference_weight`
- **Generated**: `image_asset_id` (FK), `candidates` (JSONB)
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
- `id` (PK), `name` (Unique), `gender`, `description`
- **Prompt**: `loras` (JSONB), `custom_base_prompt`, `custom_negative_prompt`, `prompt_mode`
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
- `id` (PK), `name`, `description`, `project_id` (FK, nullable)
- `source_type` (`generated`/`uploaded`), `tts_engine`
- `audio_asset_id` (FK), `voice_design_prompt`, `language`, `sample_text`, `is_system`

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

### `tag_aliases` — 비표준 태그 자동 치환
- `id` (PK), `source_tag`, `target_tag` (NULL=삭제)

### `tag_filters` — 무시/스킵 태그
- `id` (PK), `tag_name` (Unique), `filter_type` (`ignore`/`skip`)

### `tag_effectiveness` — WD14 피드백 루프
- `id` (PK), `tag_id` (FK), `use_count`, `match_count`, `effectiveness`

---

## Creative Engine

### `creative_sessions` — 멀티 에이전트 창작 세션
- `id` (PK), `objective`, `evaluation_criteria` (JSONB), `agent_config` (JSONB)
- `character_id` (FK), `final_output` (JSONB), `max_rounds`, `status`
- **V2**: `session_type`, `director_mode`, `concept_candidates` (JSONB), `selected_concept_index`, `context` (JSONB)

### `creative_session_rounds` — 라운드별 요약
- `id` (PK), `session_id` (FK), `round_number`, `leader_summary`, `round_decision`

### `creative_traces` — 에이전트 LLM 호출 추적
- `id` (PK), `session_id` (FK), `round_number`, `sequence`
- `trace_type`, `agent_role`, `agent_preset_id` (FK)
- `input_prompt`, `output_content`, `score`, `feedback`
- `model_id`, `token_usage` (JSONB), `latency_ms`, `temperature`
- `parent_trace_id` (FK, self-ref), `diff_summary`
- **V2**: `phase`, `step_name`, `target_agent`, `decision_context` (JSONB), `retry_count`

### `creative_agent_presets` — 에이전트 페르소나 프리셋
- `id` (PK), `name` (Unique), `role_description`, `system_prompt`
- `model_provider`, `model_name`, `temperature`, `is_system`

---

## Analytics & History

### `activity_logs` — 이미지 생성 이력
- `id` (PK), `storyboard_id` (FK), `scene_id` (FK), `character_id` (FK)
- `prompt`, `negative_prompt`, `sd_params` (JSONB), `seed`
- `image_storage_key`, `match_rate`, `status`
- `gemini_edited`, `gemini_cost_usd`, `original_match_rate`, `final_match_rate`

### `render_history` — 영상 렌더링 이력
- `id` (PK), `storyboard_id` (FK), `media_asset_id` (FK), `label`
- `youtube_video_id`, `youtube_upload_status`, `youtube_uploaded_at`

### `lab_experiments` — 실험실 기능 이력
- `id` (PK), `experiment_type`, `status`, `prompt_used`
- `target_tags` (JSONB), `match_rate`, `wd14_result` (JSONB)

### `scene_quality_scores` — 씬 품질 점수
- `id` (PK), `storyboard_id`, `scene_id`
- `image_storage_key`, `prompt`, `match_rate`
- `matched_tags`, `missing_tags`, `extra_tags` (JSONB)

### `prompt_histories` — 프롬프트 히스토리
- `id` (PK), `name`, `positive_prompt`, `negative_prompt`
- SD 파라미터, `character_id`, `lora_settings` (JSONB)
- `last_match_rate`, `avg_match_rate`, `is_favorite`, `use_count`
