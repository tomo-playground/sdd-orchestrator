# DB Schema Cleanup

**Phase**: 6-7 (Infrastructure)
**상태**: 미착수
**우선순위**: P1
**선행**: 없음 (독립 실행 가능)

## 목표

`CLAUDE.md` "DB Schema Design Principles" 및 `dba.md` "스키마 설계 철학"에 정의된 원칙 위반 사항을 정리한다.

## Batch A: 네이밍 수정

`default_` prefix를 실제 값에 사용한 위반 사항.

| 테이블 | 현재 | 변경 | 이유 |
|--------|------|------|------|
| `storyboards` | `default_caption` | `caption` | 스토리보드의 실제 캡션 |
| `characters` | `default_voice_preset_id` | `voice_preset_id` | 캐릭터의 실제 목소리 |
| `projects` | `default_character_id` | `character_id` | 프로젝트의 선택된 캐릭터 |
| `projects` | `default_style_profile_id` | `style_profile_id` | 프로젝트의 선택된 스타일 |

### 마이그레이션

```sql
-- Batch A: Column rename (데이터 보존, 구조만 변경)
ALTER TABLE storyboards RENAME COLUMN default_caption TO caption;
ALTER TABLE characters RENAME COLUMN default_voice_preset_id TO voice_preset_id;
ALTER TABLE projects RENAME COLUMN default_character_id TO character_id;
ALTER TABLE projects RENAME COLUMN default_style_profile_id TO style_profile_id;
```

### 영향 범위

- Backend: 모델, 스키마, 서비스, 라우터에서 필드명 참조 변경
- Frontend: API 응답 필드명 변경에 따른 타입/호출 수정
- Alembic alias 또는 `column_property`로 임시 호환 가능

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
| `storyboards` | `default_character_id` | FK 없음 | Phase 1.7에서 컬럼 제거 |
| `storyboards` | `default_style_profile_id` | FK 없음 | Phase 1.7에서 컬럼 제거 |

## 실행 순서

```
Batch A (네이밍) → Batch B (타입) → Phase 1.7 (group_config 분리)
```

- Batch A/B는 독립적으로 실행 가능 (병렬 가능)
- Phase 1.7은 Batch A 이후 실행 권장 (컬럼명 정리 후 이관)

## 검증

1. Alembic upgrade/downgrade 정상 동작
2. 기존 테스트 전량 통과
3. API 응답 필드명 변경 확인 (프론트엔드 연동)
