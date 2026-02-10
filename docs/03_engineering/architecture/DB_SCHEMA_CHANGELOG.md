# Database Schema — 변경 이력 (Archive)

> 본 문서는 [DB_SCHEMA.md](DB_SCHEMA.md)에서 분리된 전체 변경 이력입니다.
> 최근 3개 버전은 DB_SCHEMA.md 본문에 유지됩니다.

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
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
