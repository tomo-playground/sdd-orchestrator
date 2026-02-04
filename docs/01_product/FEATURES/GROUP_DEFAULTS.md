# Group Defaults Cascade

**Phase**: 7-2 Phase 1.7
**상태**: 미착수
**우선순위**: P1

## 문제

### 1. 설정 산재

현재 cascade 설정이 groups/storyboards 테이블에 직접 컬럼으로 붙어 있음:

```
groups: render_preset_id, default_character_id, default_style_profile_id
storyboards: default_character_id, default_style_profile_id, narrator_voice_preset_id, recent_videos_json
```

문제점:
- groups/storyboards 테이블이 콘텐츠와 설정을 혼합
- `default_character_id`, `default_style_profile_id`가 두 테이블에 중복
- 설정 필드가 추가될 때마다 groups 테이블에 컬럼 추가 필요
- `recent_videos_json` 같은 JSON blob이 storyboards에 직접 저장

### 2. 프론트엔드 전용 설정

language, structure, duration 등은 PlanSlice에만 존재:
- 새로고침 시 초기화됨
- 같은 그룹 내 스토리보드마다 반복 설정 필요
- Manage 페이지에 그룹 기본값 편집 UI 없음

## 목표

`group_config` 테이블을 분리하여 설정을 한 곳에서 관리한다.

## 설계: `group_config` 테이블

```sql
CREATE TABLE group_config (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL UNIQUE REFERENCES groups(id) ON DELETE CASCADE,

    -- 기존 (groups/storyboards에서 이관)
    render_preset_id INTEGER REFERENCES render_presets(id),
    default_character_id INTEGER REFERENCES characters(id),
    default_style_profile_id INTEGER REFERENCES style_profiles(id),
    narrator_voice_preset_id INTEGER REFERENCES voice_presets(id),

    -- 신규 (현재 프론트엔드 전용)
    language VARCHAR(20),          -- "Korean" | "English" | "Japanese"
    structure VARCHAR(30),         -- "Monologue" | "Dialogue" | ...
    duration INTEGER,              -- 10-120

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 선택적 확장 (P2)

```sql
    auto_compose_prompt BOOLEAN,
    hi_res_enabled BOOLEAN,
    veo_enabled BOOLEAN,
```

## Storyboard 테이블 정리

storyboards에서 제거할 컬럼:

| 컬럼 | 행선지 | 이유 |
|------|--------|------|
| `default_character_id` | `group_config` | 중복. cascade로 대체 |
| `default_style_profile_id` | `group_config` | 중복. cascade로 대체 |
| `narrator_voice_preset_id` | `group_config` | 시리즈 단위 설정 |

**`recent_videos_json`**: JSON blob → 별도 정규화 검토 (이 명세 스코프 외)

**원칙**: 스토리보드는 "생성된 콘텐츠". 기본값은 Group이 소유하고 스토리보드는 상속만 받는다.

## Groups 테이블 정리

groups에서 `group_config`로 이관할 컬럼:

| 컬럼 | 이유 |
|------|------|
| `render_preset_id` | 설정 관심사 분리 |
| `default_character_id` | 설정 관심사 분리 |
| `default_style_profile_id` | 설정 관심사 분리 |

이관 후 groups는 순수 메타데이터만 보유: `id, project_id, name, description`

## Cascade 규칙

```
System Default < Project Config < Group Config
```

Group이 설정의 최하위 소유자. 스토리보드는 소속 그룹의 설정을 상속받는다.

## 구현 범위

### Backend

1. **`group_config` 모델 생성**: 1:1 관계 (Group ↔ GroupConfig)
2. **Alembic 마이그레이션**: groups/storyboards 기존 값 → group_config 이관, 원본 컬럼 제거
3. **`config_resolver.py` 리팩터**: groups 직접 조회 → group_config 조회로 전환
4. **스키마 업데이트**: GroupConfigCreate/Update, EffectiveConfigResponse 확장
5. **API 엔드포인트**: `PUT /groups/{id}/config` (설정 전용)

### Frontend

1. **Manage 그룹 편집 UI**: 그룹별 기본값 설정 폼
2. **Studio 초기화**: `loadGroupDefaults()` → group_config API 소비
3. **storyboard save/load**: default 컬럼 참조 제거

## 마이그레이션 전략

1. `group_config` 테이블 생성
2. 기존 groups 데이터 이관: `INSERT INTO group_config SELECT ... FROM groups`
3. 기존 storyboards 데이터 이관: narrator_voice → 소속 group_config (null이 아닌 경우)
4. groups에서 `render_preset_id`, `default_character_id`, `default_style_profile_id` 제거
5. storyboards에서 `default_character_id`, `default_style_profile_id`, `narrator_voice_preset_id` 제거

## 관련 파일

- `backend/services/config_resolver.py` — cascade 엔진
- `backend/models/group.py` — Group 모델
- `backend/schemas.py` — API 스키마
- `frontend/app/store/actions/groupActions.ts` — `loadGroupDefaults()`
- `frontend/app/store/slices/contextSlice.ts` — effective 설정 저장
