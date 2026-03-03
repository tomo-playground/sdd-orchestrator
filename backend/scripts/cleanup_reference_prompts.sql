-- 캐릭터 레퍼런스 프롬프트 정리: 공통 태그 제거, 캐릭터 고유만 유지
-- 공통 태그는 config.py/config_prompt.py 상수 + compose_for_reference() 로직이 자동 주입
-- 실행: psql $DATABASE_URL -f backend/scripts/cleanup_reference_prompts.sql

BEGIN;

UPDATE characters SET
  reference_base_prompt = CASE id
    WHEN 3  THEN '(male_focus:1.3), arms_at_sides, expressionless'
    WHEN 8  THEN 'flat_color, arms_at_sides, expressionless'
    WHEN 9  THEN 'hrkzdrm_cs, arms_at_sides, expressionless'
    WHEN 12 THEN 'flat_color, arms_at_sides, expressionless'
    WHEN 13 THEN 'chibi, arms_up, open_mouth, smile'
    WHEN 14 THEN 'chibi, blue_overalls, arms_up, open_mouth, smile'
    WHEN 15 THEN 'smile'
    WHEN 16 THEN '1boy, smile'
    WHEN 17 THEN NULL
    WHEN 18 THEN NULL
    WHEN 19 THEN 'arms_at_sides, white_sweater, blue_jeans, white_sneakers, expressionless'
    WHEN 20 THEN NULL
    WHEN 21 THEN NULL
  END,
  reference_negative_prompt = CASE id
    WHEN 3  THEN 'armor, bodysuit, costume, hero_costume, cape, mask, gloves, belt, frills, dynamic_pose, 1girl, female, skirt, dress, ribbon, (wings:1.3), (debris:1.3)'
    WHEN 8  THEN 'armor, costume, frills, dynamic_pose, floating_hair, close-up, portrait'
    WHEN 9  THEN 'armor, costume, frills, dynamic_pose, (floating_hair:1.5), (very_long_hair:1.3), (absurdly_long_hair:1.5), cape, (wings:1.5), (extra_limbs:1.3), (debris:1.3), (particles:1.3)'
    WHEN 12 THEN 'armor, costume, frills, dynamic_pose, floating_hair, close-up, portrait, faceless, blank_eyes, (wings:1.3), (debris:1.3)'
    WHEN 13 THEN 'realistic, photo, 3d, dark, horror, monochrome, greyscale, from_behind, from_side, profile, looking_away, looking_back, turned_head, (wings:1.3), (extra_limbs:1.3)'
    WHEN 14 THEN 'realistic, photo, 3d, dark, horror, monochrome, greyscale, from_behind, from_side, profile, looking_away, looking_back, turned_head, 1girl, female, (wings:1.3), (extra_limbs:1.3)'
    WHEN 15 THEN '(wings:1.3), (extra_limbs:1.3)'
    WHEN 16 THEN 'faceless, blank_eyes'
    WHEN 17 THEN NULL
    WHEN 18 THEN NULL
    WHEN 19 THEN '(wings:1.3), (debris:1.3)'
    WHEN 20 THEN NULL
    WHEN 21 THEN NULL
  END
WHERE id IN (3, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21)
  AND deleted_at IS NULL;

COMMIT;
