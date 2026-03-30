-- E2E Test Seed Data (멱등: ON CONFLICT DO NOTHING)
-- FK 순서: sd_models → style_profiles → render_presets → voice_presets
--           → projects → groups → characters → storyboards → scenes
--           → storyboard_characters → loras

-- SD Model (style_profiles FK)
INSERT INTO sd_models (id, name, display_name, model_type, base_model, is_active)
VALUES (1, 'e2e_checkpoint_v1', 'E2E Test Model', 'checkpoint', 'SDXL', true)
ON CONFLICT (id) DO NOTHING;

-- Style Profiles (groups FK)
INSERT INTO style_profiles (id, name, display_name, description, sd_model_id, is_default, is_active)
VALUES
    (1, 'e2e_anime', 'E2E Anime Style', 'E2E test anime style', 1, true, true),
    (2, 'e2e_realistic', 'E2E Realistic Style', 'E2E test realistic style', 1, false, true)
ON CONFLICT (id) DO NOTHING;

-- Render Preset (groups FK)
INSERT INTO render_presets (id, name, description, is_system, bgm_mode, layout_style, transition_type)
VALUES (1, 'E2E Default', 'E2E test preset', true, 'manual', 'full', 'crossfade')
ON CONFLICT (id) DO NOTHING;

-- Voice Presets (groups FK, characters FK)
INSERT INTO voice_presets (id, name, description, source_type, tts_engine, language, is_system)
VALUES
    (1, 'E2E Narrator', 'E2E narrator voice', 'generated', 'qwen', 'korean', true),
    (2, 'E2E Speaker', 'E2E speaker voice', 'generated', 'qwen', 'korean', false)
ON CONFLICT (id) DO NOTHING;

-- Project
INSERT INTO projects (id, name, description)
VALUES (1, 'E2E 테스트 채널', 'E2E 자동화 테스트용 채널')
ON CONFLICT (id) DO NOTHING;

-- Group
INSERT INTO groups (id, project_id, name, description, render_preset_id, style_profile_id, narrator_voice_preset_id)
VALUES (1, 1, 'E2E 시리즈', 'E2E 테스트용 시리즈', 1, 1, 1)
ON CONFLICT (id) DO NOTHING;

-- Characters
INSERT INTO characters (id, group_id, name, gender, description, positive_prompt, negative_prompt, voice_preset_id)
VALUES
    (1, 1, 'E2E Speaker A', 'female', 'E2E test character A',
     '1girl, long_hair, brown_hair, school_uniform', 'bad_anatomy', 2),
    (2, 1, 'E2E Speaker B', 'male', 'E2E test character B',
     '1boy, short_hair, black_hair, casual_clothes', 'bad_anatomy', NULL)
ON CONFLICT (id) DO NOTHING;

-- Storyboard
INSERT INTO storyboards (id, group_id, title, description, structure, tone, language, duration, version)
VALUES (1, 1, 'E2E 테스트 영상', 'E2E 자동화 테스트용 스토리보드', 'Dialogue', 'intimate', 'korean', 60, 1)
ON CONFLICT (id) DO NOTHING;

-- Scenes (3개)
INSERT INTO scenes (id, client_id, storyboard_id, "order", script, speaker, duration, width, height)
VALUES
    (1, 'e2e-scene-001', 1, 0, '오늘 정말 힘든 하루였어.', 'speaker_1', 3.0, 832, 1216),
    (2, 'e2e-scene-002', 1, 1, '그래? 무슨 일이 있었는데?', 'speaker_2', 2.5, 832, 1216),
    (3, 'e2e-scene-003', 1, 2, '사실은 말이야...', 'speaker_1', 3.5, 832, 1216)
ON CONFLICT (id) DO NOTHING;

-- Storyboard ↔ Character mapping
INSERT INTO storyboard_characters (id, storyboard_id, speaker, character_id)
VALUES
    (1, 1, 'speaker_1', 1),
    (2, 1, 'speaker_2', 2)
ON CONFLICT (id) DO NOTHING;

-- LoRA
INSERT INTO loras (id, name, display_name, lora_type, trigger_words, default_weight, is_active)
VALUES (1, 'e2e_test_lora', 'E2E Test LoRA', 'character', ARRAY['e2e_trigger'], 0.75, true)
ON CONFLICT (id) DO NOTHING;

-- Sequence 동기화 (INSERT 후 auto-increment가 충돌하지 않도록)
SELECT setval('sd_models_id_seq', GREATEST((SELECT MAX(id) FROM sd_models), 1));
SELECT setval('style_profiles_id_seq', GREATEST((SELECT MAX(id) FROM style_profiles), 1));
SELECT setval('render_presets_id_seq', GREATEST((SELECT MAX(id) FROM render_presets), 1));
SELECT setval('voice_presets_id_seq', GREATEST((SELECT MAX(id) FROM voice_presets), 1));
SELECT setval('projects_id_seq', GREATEST((SELECT MAX(id) FROM projects), 1));
SELECT setval('groups_id_seq', GREATEST((SELECT MAX(id) FROM groups), 1));
SELECT setval('characters_id_seq', GREATEST((SELECT MAX(id) FROM characters), 1));
SELECT setval('storyboards_id_seq', GREATEST((SELECT MAX(id) FROM storyboards), 1));
SELECT setval('scenes_id_seq', GREATEST((SELECT MAX(id) FROM scenes), 1));
SELECT setval('storyboard_characters_id_seq', GREATEST((SELECT MAX(id) FROM storyboard_characters), 1));
SELECT setval('loras_id_seq', GREATEST((SELECT MAX(id) FROM loras), 1));
