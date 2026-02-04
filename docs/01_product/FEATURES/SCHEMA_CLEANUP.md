# DB Schema Cleanup

**Phase**: 6-7 (Infrastructure)
**상태**: 부분 완료
**우선순위**: P1
**선행**: 없음 (독립 실행 가능)

## 목표

`CLAUDE.md` "DB Schema Design Principles" 및 `dba.md` "스키마 설계 철학"에 정의된 원칙 위반 사항을 정리한다.

## Batch A: 네이밍 수정 ✅

`default_` prefix를 실제 값에 사용한 위반 사항.

| 테이블 | 현재 | 변경 | 상태 |
|--------|------|------|------|
| `projects` | `default_character_id` | `character_id` | ✅ 완료 (v3.6) |
| `projects` | `default_style_profile_id` | `style_profile_id` | ✅ 완료 (v3.6) |
| `groups` | `default_character_id` | DROP | ✅ 완료 (v3.6, storyboard 레벨에서 관리) |
| `groups` | `default_style_profile_id` | `style_profile_id` | ✅ 완료 (v3.6) |
| `group_config` | `default_character_id` | DROP | ✅ 완료 (v3.6) |
| `group_config` | `default_style_profile_id` | `style_profile_id` | ✅ 완료 (v3.6) |
| `storyboards` | `default_character_id` | `character_id` | ✅ 완료 (v3.6) |
| `storyboards` | `default_style_profile_id` | `style_profile_id` | ✅ 완료 (v3.6) |
| `storyboards` | `default_caption` | `caption` | ✅ 완료 (v3.7) |
| `characters` | `default_voice_preset_id` | `voice_preset_id` | ✅ 완료 (v3.7) |

> Migration 1: `n8o9p0q1r2s3_rename_default_prefix_columns.py`
> 커밋: `62087af refactor: rename default_ prefix columns + drop character_id from groups`
> Migration 2: `o9p0q1r2s3t4_rename_caption_and_voice_preset.py`

## Batch B: 타입 수정

| 테이블 | 컬럼 | 현재 | 변경 | 이유 |
|--------|------|------|------|------|
| `scenes` | `use_reference_only` | `Integer` (1=True) | `Boolean` | Boolean은 Boolean 타입 사용 원칙 |
| `storyboards` | `recent_videos_json` | `Text` (JSON 문자열) | `JSONB` | JSON은 JSONB 원칙 |

### 마이그레이션

```sql
-- scenes: Integer → Boolean 변환
ALTER TABLE scenes ALTER COLUMN use_reference_only TYPE BOOLEAN
  USING CASE WHEN use_reference_only = 1 THEN TRUE ELSE FALSE END;

-- storyboards: Text → JSONB 변환
ALTER TABLE storyboards ALTER COLUMN recent_videos_json TYPE JSONB
  USING recent_videos_json::jsonb;
ALTER TABLE storyboards RENAME COLUMN recent_videos_json TO recent_videos;
```

## Batch C: FK 누락 (Phase 1.7에서 해결)

Phase 1.7 (Group Defaults)에서 해당 컬럼 자체가 제거되므로 FK 추가 불필요.

| 테이블 | 컬럼 | 문제 | 해결 |
|--------|------|------|------|
| `storyboards` | `character_id` | FK 없음 | Phase 1.7에서 컬럼 제거 예정 |
| `storyboards` | `style_profile_id` | FK 없음 | Phase 1.7에서 컬럼 제거 예정 |

## 실행 순서

```
Batch A (네이밍) ✅ → Batch B (타입) → Phase 1.7 (group_config 분리)
```

- Batch A: 완료 (v3.6 + v3.7, 2026-02-04)
- Batch B: 미착수
- Phase 1.7: group_config 테이블 분리 완료 (v3.6)

## 검증

1. Alembic upgrade/downgrade 정상 동작
2. 기존 테스트 전량 통과
3. API 응답 필드명 변경 확인 (프론트엔드 연동)
