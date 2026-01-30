# Database Schema Documentation

This document describes the database schema for the Shorts Producer application.
The database is managed using SQLAlchemy ORM and Alembic for migrations.

## Core Models

### Tags (`tags`)
Stores classification tags for prompts.
- `id`: Integer (PK)
- `name`: String(100) (Unique)
- `category`: String(50) (character, scene, meta)
- `group_name`: String(50) (e.g., hair_color, eye_color)
- `priority`: Integer (Default: 5)
- `exclusive`: Boolean (Default: False)
- `classification_source`: String(20) (pattern, danbooru, llm, manual)
- `classification_confidence`: Float (Default: 1.0)
- `created_at`, `updated_at`: DateTime

### Tag Rules (`tag_rules`)
Defines conflict and dependency rules between tags.
- `id`: Integer (PK)
- `rule_type`: String(20) (conflict, requires)
- `source_tag_id`: Integer (FK -> tags.id)
- `target_tag_id`: Integer (FK -> tags.id)

### Synonyms (`synonyms`)
Maps alternative names to tags.
- `id`: Integer (PK)
- `tag_id`: Integer (FK -> tags.id)
- `synonym`: String(100)

### Classification Rules (`classification_rules`)
Pattern-based rules for auto-classifying tags.
- `id`: Integer (PK)
- `rule_type`: String(20) (suffix, prefix, contains, exact)
- `pattern`: String(100)
- `target_group`: String(50)
- `priority`: Integer
- `active`: Boolean

### Tag Effectiveness (`tag_effectiveness`)
Tracks how well SD models render specific tags (WD14 feedback loop).
- `id`: Integer (PK)
- `tag_id`: Integer (FK -> tags.id)
- `use_count`: Integer
- `match_count`: Integer
- `total_confidence`: Float
- `effectiveness`: Float (match_count / use_count)

---

## Asset Models

### Characters (`characters`)
Character presets with LoRA and prompt configurations.
- `id`: Integer (PK)
- `name`: String(100) (Unique)
- `description`: String(500)
- `gender`: String(10)
- `identity_tags`: Array[Integer] (Tag IDs)
- `clothing_tags`: Array[Integer] (Tag IDs)
- `loras`: JSONB (List of {lora_id, weight})
- `recommended_negative`: Array[Text]
- `custom_base_prompt`: Text
- `custom_negative_prompt`: Text
- `reference_base_prompt`: Text
- `reference_negative_prompt`: Text
- `preview_image_url`: String(500)
- `prompt_mode`: String(20) (auto, standard, lora)
- `ip_adapter_weight`: Float
- `ip_adapter_model`: String(50)

### LoRAs (`loras`)
Stable Diffusion LoRA models.
- `id`: Integer (PK)
- `name`: String(100) (Unique)
- `display_name`: String(100)
- `lora_type`: String(20) (character, style, pose, other)
- `gender_locked`: String(10)
- `civitai_id`: Integer
- `civitai_url`: String(500)
- `trigger_words`: Array[Text]
- `default_weight`: Numeric(3,2)
- `optimal_weight`: Numeric(3,2)
- `calibration_score`: Numeric(5,2)
- `weight_min`: Numeric(3,2)
- `weight_max`: Numeric(3,2)
- `base_models`: Array[Text]
- `character_defaults`: JSONB
- `recommended_negative`: Array[Text]
- `preview_image_url`: String(500)

### SD Models (`sd_models`)
Stable Diffusion checkpoints.
- `id`: Integer (PK)
- `name`: String(200) (Unique)
- `display_name`: String(200)
- `model_type`: String(50)
- `base_model`: String(50)
- `civitai_id`: Integer
- `civitai_url`: String(500)
- `description`: Text
- `preview_image_url`: String(500)
- `is_active`: Boolean

### Embeddings (`embeddings`)
Textual Inversion embeddings.
- `id`: Integer (PK)
- `name`: String(200) (Unique)
- `display_name`: String(200)
- `embedding_type`: String(50)
- `trigger_word`: String(100)
- `description`: Text
- `is_active`: Boolean

### Style Profiles (`style_profiles`)
Bundles of Model + LoRAs + Embeddings.
- `id`: Integer (PK)
- `name`: String(100) (Unique)
- `sd_model_id`: Integer (FK -> sd_models.id)
- `loras`: JSONB
- `negative_embeddings`: Array[Integer]
- `positive_embeddings`: Array[Integer]
- `default_positive`: Text
- `default_negative`: Text
- `is_default`: Boolean
- `is_active`: Boolean

---

## Analytics & History

### Prompt Histories (`prompt_histories`)
Saved prompts with their generation settings.
- `id`: Integer (PK)
- `name`: String(200)
- `positive_prompt`: Text
- `negative_prompt`: Text
- `steps`, `cfg_scale`, `seed`, `clip_skip`: Integer/Float
- `character_id`: Integer
- `lora_settings`: JSONB
- `context_tags`: JSONB
- `last_match_rate`: Float
- `avg_match_rate`: Float
- `validation_count`: Integer
- `is_favorite`: Boolean
- `use_count`: Integer

### Generation Logs (`generation_logs`)
Logs of all generation attempts for analytics.
- `id`: Integer (PK)
- `scene_index`: Integer
- `prompt`: Text
- `tags`: JSONB
- `sd_params`: JSONB
- `match_rate`: Float
- `status`: String(20)
- `image_url`: Text

### Scene Quality Scores (`scene_quality_scores`)
Quality metrics per scene.
- `id`: Integer (PK)
- `scene_id`: Integer
- `match_rate`: Float
- `matched_tags`, `missing_tags`, `extra_tags`: JSONB
- `validated_at`: DateTime

### Gemini Usage Logs (`gemini_usage_logs`)
Cost and usage tracking for Gemini API calls (Image Editing).
- `id`: Integer (PK)
- `scene_index`: Integer
- `edit_type`: String(20)
- `original_prompt`: Text
- `target_change`: Text
- `cost_usd`: Float
- `match_rate_before`: Float
- `match_rate_after`: Float
- `improvement`: Float
- `vision_analysis`: JSONB
- `status`: String(20)

### Evaluation Runs (`evaluation_runs`)
Mode A/B testing results.
- `id`: Integer (PK)
- `test_name`: String(100)
- `mode`: String(20)
- `character_id`: Integer
- `prompt_used`: Text
- `match_rate`: Float
- `matched_tags`, `missing_tags`, `extra_tags`: JSONB
- `image_path`: String(500)
