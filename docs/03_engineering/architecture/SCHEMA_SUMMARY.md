# Database Schema Documentation

This document describes the database schema for the Shorts Producer application (V3.3 Architecture).
The database is managed using SQLAlchemy ORM and Alembic for migrations.

## Core Models

### Projects (`projects`)
A YouTube Channel project.
- `id`: Integer (PK)
- `name`: String(200)
- `description`: Text
- `avatar_asset_id`: Integer (FK -> media_assets.id)
- `handle`: String(100)
- `render_preset_id`: Integer (FK -> render_presets.id)
- `style_profile_id`: Integer (FK -> style_profiles.id)

### Groups (`groups`)
A series/category within a project.
- `id`: Integer (PK)
- `project_id`: Integer (FK -> projects.id)
- `name`: String(200)
- `description`: Text
- `render_preset_id`: Integer (FK -> render_presets.id)
- `style_profile_id`: Integer (FK -> style_profiles.id)

### Storyboards (`storyboards`)
An individual video episode.
- `id`: Integer (PK)
- `title`: String(200)
- `description`: Text
- `character_id`: Integer
- `style_profile_id`: Integer
- `caption`: Text
- `video_asset_id`: Integer (FK -> media_assets.id)
- `recent_videos`: JSONB
- `created_at`, `updated_at`: DateTime

### Scenes (`scenes`)
A single scene/shot within a storyboard.
- `id`: Integer (PK)
- `storyboard_id`: Integer (FK -> storyboards.id)
- `order`: Integer (Sequence in video)
- `script`: Text
- `description`: Text
- `speaker`: String(20)
- `duration`: Float
- `image_prompt`: Text
- `image_prompt_ko`: Text
- `negative_prompt`: Text
- `width`, `height`: Integer
- `steps`, `cfg_scale`, `sampler_name`, `seed`, `clip_skip`: Overrides
- `context_tags`: JSONB
- `image_asset_id`: Integer (FK -> media_assets.id)
- `created_at`, `updated_at`: DateTime

### Media Assets (`media_assets`)
Polymorphic storage for all files.
- `id`: Integer (PK)
- `owner_type`: String(50)
- `owner_id`: Integer
- `file_name`: String(255)
- `file_type`: String(20)
- `storage_key`: String(500)
- `is_temp`: Boolean
- `checksum`: String(64)

---

## Association Tables

### Character Tags (`character_tags`)
- `character_id`: Integer (FK -> characters.id)
- `tag_id`: Integer (FK -> tags.id)
- `weight`: Float
- `is_permanent`: Boolean

### Scene Tags (`scene_tags`)
- `scene_id`: Integer (FK -> scenes.id)
- `tag_id`: Integer (FK -> tags.id)

### Scene Character Actions (`scene_character_actions`)
- `id`: Integer (PK)
- `scene_id`, `character_id`, `tag_id`: Foreign Keys

---

## Analytics & Tracking

### Activity Logs (`activity_logs`)
- `id`: Integer (PK)
- `storyboard_id`: Integer
- `scene_id`, `character_id`: Identifiers
- `prompt`, `negative_prompt`: Text
- `sd_params`: JSONB
- `image_storage_key`: String(500)
- `match_rate`: Float
- `gemini_edited`: Boolean
- `status`: String(20)

### Scene Quality Scores (`scene_quality_scores`)
- `id`: Integer (PK)
- `storyboard_id`, `scene_id`: Identifiers
- `image_storage_key`: String(500)
- `match_rate`: Float
- `matched_tags`, `missing_tags`, `extra_tags`: JSONB
