# Database Schema — 변경 이력 (Archive)

> 본 문서는 [DB_SCHEMA.md](DB_SCHEMA.md)에서 분리된 전체 변경 이력입니다.
> 최근 3개 버전은 DB_SCHEMA.md 본문에 유지됩니다.

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v3.25 | 2026-02-21 | `style_profiles`에 `default_enable_hr` (Boolean) 추가 — 화풍별 Hi-Res 기본값 자동 적용 |
| v3.24 | 2026-02-21 | `style_profiles`에 생성 파라미터 4컬럼 추가 (default_steps, default_cfg_scale, default_sampler_name, default_clip_skip) |
| v3.23 | 2026-02-21 | `characters`에서 `project_id` FK 제거 (미사용, 글로벌 스코프로 운영) |
| v3.22 | 2026-02-21 | `characters`에 `style_profile_id` FK 추가 (캐릭터별 스타일 프로파일 오버라이드) |
| v3.21 | 2026-02-18 | **Source-Truth Sync**: `active` → `is_active` 문서 반영(tag_rules, tag_aliases, tag_filters, classification_rules). `scenes`에 TTS 필드 3개 추가(voice_design_prompt, head_padding, tail_padding). `group_config`에 `channel_dna`/SD 파라미터 상세화. `creative_sessions.session_type` default 수정(free→shorts). `loras`에 `gender_locked` 누락 복원 |
| v3.20 | 2026-02-12 | `storyboards`에 `version` (Integer, NOT NULL, default 1) 추가 — Optimistic Locking |
| v3.19 | 2026-02-12 | `scenes`에 `client_id` (UUID) 추가 — Frontend 안정 식별자, UNIQUE + NOT NULL |
| v3.18 | 2026-02-12 | `scenes`에 `background_id` FK 추가 (Background 에셋 연동, ControlNet Canny + 태그 자동 주입) |
| v3.17 | 2026-02-11 | `loras`에 멀티캐릭터 필드 3개 추가 (`is_multi_character_capable`, `multi_char_weight_scale`, `multi_char_trigger_prompt`). `scenes`에 `scene_mode` 추가 |
| v3.16 | 2026-02-10 | `storyboards`에 `duration`/`language` 추가 (Creative Lab 연동). `creative_agent_presets`에 `agent_role`/`category`/`agent_metadata` 추가 (V2 Agent Presets) |
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
