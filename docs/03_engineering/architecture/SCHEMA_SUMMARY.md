# Database Schema Documentation

This document describes the database schema for the Shorts Producer application (V3 Architecture).
The database is managed using SQLAlchemy ORM and Alembic for migrations.

## Core Models

### Storyboards (`storyboards`)
A YouTube Shorts project containing multiple scenes.
- `id`: Integer (PK)
- `title`: String(200)
- `description`: Text
- `default_character_id`: Integer (Optional default)
- `default_style_profile_id`: Integer (Optional default)
- `video_url`: String(500) (URL of the latest rendered video)
- `recent_videos_json`: Text (JSON string of historical video results)
- `created_at`, `updated_at`: DateTime

### Scenes (`scenes`)
A single scene/shot within a storyboard.
- `id`: Integer (PK)
- `storyboard_id`: Integer (FK -> storyboards.id)
- `order`: Integer (Sequence in video)
- `script`: Text (TTS content)
- `description`: Text (Visual context)
- `speaker`: String(20) (Default: Narrator)
- `duration`: Float (Scene timing)
- `image_prompt`: Text (English tags)
- `image_prompt_ko`: Text (Korean draft)
- `negative_prompt`: Text
- `width`, `height`: Integer (Default: 512x768)
- `steps`, `cfg_scale`, `sampler_name`, `seed`, `clip_skip`: Overrides
- `context_tags`: JSONB (Categorized tag groups)
- `image_url`: String(500) (Path to generated asset)
- `created_at`, `updated_at`: DateTime

### Tags (`tags`)
Stores classification tags for prompts.
- `id`: Integer (PK)
- `name`: String(100) (Unique, underscore format)
- `category`: String(50) (character, scene, meta)
- `group_name`: String(50) (e.g., hair_color, clothing)
- `priority`: Integer (Layering order)
- `exclusive`: Boolean (Unique within group)
- `classification_source`: String(20) (danbooru, llm, manual)
- `created_at`, `updated_at`: DateTime

---

## Association Tables (Many-to-Many)

### Character Tags (`character_tags`)
Permanent and transient traits of a character.
- `character_id`: Integer (FK -> characters.id)
- `tag_id`: Integer (FK -> tags.id)
- `weight`: Float (Tag influence)
- `is_permanent`: Boolean (True: Identity, False: Transient/Clothing)

### Scene Tags (`scene_tags`)
Global/Ambient characteristics of a specific scene.
- `scene_id`: Integer (FK -> scenes.id)
- `tag_id`: Integer (FK -> tags.id)
- `weight`: Float

### Scene Character Actions (`scene_character_actions`)
Specific poses/expressions/actions for a character in a scene.
- `id`: Integer (PK)
- `scene_id`: Integer (FK -> scenes.id)
- `character_id`: Integer (FK -> characters.id)
- `tag_id`: Integer (FK -> tags.id)
- `weight`: Float

---

## Assets & Configuration

### Characters (`characters`)
Character presets with LoRA and prompt configurations.
- `id`: Integer (PK)
- `name`: String(100) (Unique)
- `description`: String(500)
- `gender`: String(10)
- `identity_tags`, `clothing_tags`: Handled via associations
- `loras`: JSONB (List of {lora_id, weight})
- `preview_image_url`: String(500)
- `ip_adapter_weight`: Float
- `ip_adapter_model`: String(50)

### LoRAs (`loras`)
Stable Diffusion LoRA models.
- `id`: Integer (PK)
- `name`: String(100)
- `display_name`: String(100)
- `trigger_words`: Array[Text]
- `default_weight`: Numeric(3,2)
- `civitai_id`: Integer

### SD Models (`sd_models`)
Stable Diffusion checkpoints.
- `id`: Integer (PK)
- `name`: String(200)
- `is_active`: Boolean

---

## Analytics & Tracking

### Activity Logs (`activity_logs`)
Unified store for all generation events and successful history.
- `id`: Integer (PK)
- `storyboard_id`: Integer (FK -> storyboards.id)
- `scene_id`: Integer
- `character_id`: Integer
- `prompt`: Text (Final positive prompt)
- `negative_prompt`: Text
- `sd_params`: JSONB
- `image_url`: String(500)
- `match_rate`: Float
- `tags_used`: JSONB
- `status`: String(20) (success, fail)
- `created_at`: DateTime

### Tag Rules & Aliases
- `tag_rules`: Conflict (X prevents Y) and Dependency (X requires Y) logic.
- `tag_aliases`: Maps multiple synonyms (Danbooru/Human) to a single canonical Tag ID.
- `classification_rules`: Pattern matching for automated category/group assignment.
