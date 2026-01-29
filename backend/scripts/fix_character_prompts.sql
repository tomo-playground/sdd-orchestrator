-- Fix character base prompts for Blindbox, Doremi, and Flat Color Girl
-- These characters were missing their distinctive features in reference_base_prompt

-- 1. Blindbox: Add 3D toy style features
UPDATE characters 
SET 
    custom_base_prompt = 'blindbox, 3d, toy, plastic, clay, glossy, smooth, vibrant_colors',
    reference_base_prompt = 'masterpiece, best_quality, ultra-detailed, blindbox, 3d, toy, plastic, clay, glossy, smooth, vibrant_colors, solo, upper_body, portrait, facing_viewer, front_view, looking_at_viewer, straight_on, white_background, simple_background',
    updated_at = now()
WHERE name = 'Blindbox';

-- 2. Doremi: Add character-specific features
UPDATE characters 
SET 
    custom_base_prompt = 'harukaze_doremi, casual_outfit, pink_hair',
    reference_base_prompt = 'masterpiece, best_quality, ultra-detailed, harukaze_doremi, pink_hair, casual_outfit, solo, upper_body, portrait, facing_viewer, front_view, looking_at_viewer, straight_on, white_background, simple_background',
    updated_at = now()
WHERE name = 'Doremi';

-- 3. Flat Color Girl: Add flat color style features
UPDATE characters 
SET 
    custom_base_prompt = 'flat_color, simple_shading, vibrant_colors',
    reference_base_prompt = 'masterpiece, best_quality, ultra-detailed, flat_color, simple_shading, vibrant_colors, 1girl, solo, upper_body, portrait, facing_viewer, front_view, looking_at_viewer, straight_on, white_background, simple_background',
    updated_at = now()
WHERE name = 'Flat Color Girl';

-- Verify updates
SELECT name, custom_base_prompt, reference_base_prompt 
FROM characters 
WHERE name IN ('Blindbox', 'Doremi', 'Flat Color Girl')
ORDER BY name;
