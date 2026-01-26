-- Add conflict rules for new location tags
-- Run this when PostgreSQL is available

-- hospital conflicts
INSERT INTO tag_rules (tag1, tag2, rule_type, reason) VALUES
  ('hospital', 'cafe', 'conflict', '서로 다른 장소'),
  ('hospital', 'library', 'conflict', '서로 다른 장소'),
  ('hospital', 'classroom', 'conflict', '서로 다른 장소'),
  ('hospital', 'street', 'conflict', '실내 vs 실외'),
  ('hospital', 'park', 'conflict', '실내 vs 실외')
ON CONFLICT (tag1, tag2, rule_type) DO NOTHING;

-- clinic conflicts
INSERT INTO tag_rules (tag1, tag2, rule_type, reason) VALUES
  ('clinic', 'cafe', 'conflict', '서로 다른 장소'),
  ('clinic', 'library', 'conflict', '서로 다른 장소'),
  ('clinic', 'classroom', 'conflict', '서로 다른 장소'),
  ('clinic', 'hospital', 'conflict', '중복 의료 시설')
ON CONFLICT (tag1, tag2, rule_type) DO NOTHING;

-- train station conflicts
INSERT INTO tag_rules (tag1, tag2, rule_type, reason) VALUES
  ('train station', 'library', 'conflict', '서로 다른 장소'),
  ('train station', 'cafe', 'conflict', '서로 다른 장소'),
  ('train station', 'classroom', 'conflict', '서로 다른 장소'),
  ('train station', 'hospital', 'conflict', '서로 다른 장소'),
  ('train station', 'park', 'conflict', '서로 다른 장소')
ON CONFLICT (tag1, tag2, rule_type) DO NOTHING;

-- platform conflicts
INSERT INTO tag_rules (tag1, tag2, rule_type, reason) VALUES
  ('platform', 'indoors', 'conflict', '플랫폼은 실외'),
  ('platform', 'room', 'conflict', '플랫폼 vs 실내'),
  ('platform', 'library', 'conflict', '서로 다른 장소'),
  ('platform', 'cafe', 'conflict', '서로 다른 장소'),
  ('platform', 'classroom', 'conflict', '서로 다른 장소')
ON CONFLICT (tag1, tag2, rule_type) DO NOTHING;

-- bus stop conflicts
INSERT INTO tag_rules (tag1, tag2, rule_type, reason) VALUES
  ('bus stop', 'indoors', 'conflict', '정류장은 실외'),
  ('bus stop', 'library', 'conflict', '서로 다른 장소'),
  ('bus stop', 'cafe', 'conflict', '서로 다른 장소'),
  ('bus stop', 'classroom', 'conflict', '서로 다른 장소'),
  ('bus stop', 'hospital', 'conflict', '서로 다른 장소')
ON CONFLICT (tag1, tag2, rule_type) DO NOTHING;

-- platform requires train station
INSERT INTO tag_rules (tag1, tag2, rule_type, reason) VALUES
  ('platform', 'train station', 'requires', '플랫폼은 기차역에 있음')
ON CONFLICT (tag1, tag2, rule_type) DO NOTHING;
