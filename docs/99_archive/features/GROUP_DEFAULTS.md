# Group Defaults Cascade

**Phase**: 7-2 Phase 1.7
**상태**: 완료
**우선순위**: P1

## 문제

### 1. 설정 산재

기존에 cascade 설정이 groups/storyboards 테이블에 직접 컬럼으로 붙어 있었음:

```
groups: render_preset_id, style_profile_id
storyboards: character_id, style_profile_id, narrator_voice_preset_id, recent_videos_json
```

문제점:
- groups/storyboards 테이블이 콘텐츠와 설정을 혼합
- `character_id`, `style_profile_id`가 두 테이블에 중복
- 설정 필드가 추가될 때마다 groups 테이블에 컬럼 추가 필요
- `recent_videos_json` 같은 JSON blob이 storyboards에 직접 저장

### 2. 프론트엔드 전용 설정

language, structure, duration 등이 PlanSlice에만 존재:
- 새로고침 시 초기화됨
- 같은 그룹 내 스토리보드마다 반복 설정 필요
- Manage 페이지에 그룹 기본값 편집 UI 없음

## 해결

`group_config` 테이블을 분리하여 설정을 한 곳에서 관리.

## 구현 완료 내역

### DB: `group_config` 테이블

```sql
CREATE TABLE group_config (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL UNIQUE REFERENCES groups(id) ON DELETE CASCADE,

    -- 기존 (groups/storyboards에서 이관)
    render_preset_id INTEGER REFERENCES render_presets(id),
    style_profile_id INTEGER REFERENCES style_profiles(id),
    narrator_voice_preset_id INTEGER REFERENCES voice_presets(id),

    -- 신규 (프론트엔드 전용 → DB 영속)
    language VARCHAR(20),          -- "Korean" | "English" | "Japanese"
    structure VARCHAR(30),         -- "Monologue" | "Dialogue" | ...
    duration INTEGER,              -- 10-120

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Backend

| 항목 | 상태 |
|------|------|
| `group_config` 모델 (1:1 Group ↔ GroupConfig) | 완료 |
| Alembic 마이그레이션 (groups/storyboards → group_config 이관) | 완료 |
| `config_resolver.py` CASCADING_FIELDS에 language/structure/duration 포함 | 완료 |
| API: `GET/PUT /groups/{id}/config`, `GET /groups/{id}/effective-config` | 완료 |
| 스키마: GroupConfigCreate/Update, EffectiveConfigResponse | 완료 |

### Frontend

| 항목 | 상태 |
|------|------|
| GroupConfigEditor UI (Manage 그룹 편집에서 기본값 설정) | 완료 |
| `loadGroupDefaults()` → PlanSlice에 language/structure/duration 적용 | 완료 |
| `useProjectGroups` → groupId 변경 시 `loadGroupDefaults()` 호출 | 완료 |

### Cascade 규칙

```
System Default < Project Config < Group Config
```

Group이 설정의 최하위 소유자. 스토리보드는 소속 그룹의 설정을 상속받는다.

## 관련 파일

- `backend/services/config_resolver.py` — cascade 엔진
- `backend/models/group.py` — Group, GroupConfig 모델
- `backend/schemas.py` — API 스키마
- `backend/routers/groups.py` — API 엔드포인트
- `frontend/app/store/actions/groupActions.ts` — `loadGroupDefaults()`
- `frontend/app/hooks/useProjectGroups.ts` — groupId 변경 감지
- `frontend/app/store/slices/contextSlice.ts` — effective 설정 저장
