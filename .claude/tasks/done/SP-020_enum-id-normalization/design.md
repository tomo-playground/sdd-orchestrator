# SP-020 상세 설계 — Enum ID 정규화 (Sprint B)

> 작성: 2026-03-24 | 규모: 풀 설계 (DB 마이그레이션 + 코드 8+ 파일)

## 현황 요약

Sprint A는 2026-03-19에 완료됨 (커밋 `2de15841`):
- `config.py`: `StructureMeta`/`LanguageMeta` SSOT + `coerce_structure_id()`/`coerce_language_id()` 과도기 함수
- 중복 상수 6곳 통합, `normalize_structure()` 삭제
- Agent 노드 14개, Prompt Builders, Schemas 정규화 완료
- `READING_SPEED` dict 키 이미 lowercase

**SP-020은 Sprint B**: DB 마이그레이션 + 잔여 방어 패턴 제거 + 테스트/스냅샷 정규화.

## 현재 DB 상태

```
storyboards.structure: "Monologue"(3), "Dialogue"(2), "monologue"(3), "dialogue"(2),
                       "Narrated Dialogue"(1), "narrated_dialogue"(1)
storyboards.language:  "Korean"(?), "korean"(5), NULL(1)
```

Title Case와 snake_case가 혼재. `coerce_*()` 함수가 경계에서 변환하여 런타임에는 정상 동작.

---

## DoD별 상세 설계

### A. config.py SSOT 정의 — 이미 완료

Sprint A에서 `STRUCTURE_METADATA`, `LANGUAGE_METADATA`, `MULTI_CHAR_STRUCTURES`, `DEFAULT_STRUCTURE="monologue"`, `DEFAULT_LANGUAGE="korean"` 정의 완료. 추가 작업 없음.

### B. Backend 잔여 정규화 패턴 제거

#### B-1. `gemini_generator.py` (3곳)

**현재 코드**:
```python
structure_lower = request.structure.lower()                    # L264
structure_normalized = structure_lower.replace("_", " ")       # L265
has_two_characters = structure_normalized in ("dialogue", "narrated dialogue")  # L266, L289
```

**변경**:
```python
from config import MULTI_CHAR_STRUCTURES, coerce_structure_id
structure = coerce_structure_id(request.structure)
has_two_characters = structure in MULTI_CHAR_STRUCTURES
```
- `structure_lower`, `structure_normalized` 변수 제거
- L289의 `structure_normalized in (...)` 도 `structure in MULTI_CHAR_STRUCTURES`로 전환
- L524의 `auto_pin_raw_scenes(scenes, structure_lower)` → `auto_pin_raw_scenes(scenes, structure)`

**엣지 케이스**: `request.structure`가 None/빈문자열일 수 있음 → `coerce_structure_id()`가 `DEFAULT_STRUCTURE` 반환하므로 안전.

#### B-2. `scene_postprocess.py` (1곳)

**현재 코드**:
```python
def auto_pin_raw_scenes(scenes: list[dict], structure_lower: str) -> None:
    is_dialogue_structure = structure_lower.replace("_", " ") in ("dialogue", "narrated dialogue")
```

**변경**:
```python
from config import MULTI_CHAR_STRUCTURES

def auto_pin_raw_scenes(scenes: list[dict], structure: str) -> None:
    is_dialogue_structure = structure in MULTI_CHAR_STRUCTURES
```
- 파라미터명 `structure_lower` → `structure` (이미 정규화된 값을 받으므로)

#### B-3. `presets.py` (1곳)

**현재 코드**:
```python
def get_preset_by_structure(structure: str) -> StoryboardPreset | None:
    for preset in PRESETS.values():
        if preset.structure.lower() == structure.lower():
            return preset
```

**변경**:
```python
def get_preset_by_structure(structure: str) -> StoryboardPreset | None:
    from config import coerce_structure_id
    sid = coerce_structure_id(structure)
    return PRESETS.get(sid)
```
- `PRESETS` dict 키가 이미 snake_case (`"monologue"`, `"dialogue"`, `"narrated_dialogue"`)이므로 직접 조회 가능
- `coerce_structure_id()`로 입력 정규화 후 dict.get()

#### B-4. `coerce_*()` 함수 — 유지 (제거는 Out of Scope)

DB 마이그레이션 후에도 외부 입력(API 요청, Gemini 응답)의 레거시 포맷 가능성이 있으므로, 과도기 함수를 당장 제거하지 않는다. 제거는 SP-021(Speaker 동적 역할) 완료 후 별도 정리에서 수행.

### C. DB 마이그레이션

#### 구현방법

Alembic 마이그레이션 파일 1개 생성. `op.execute()`로 SQL UPDATE 실행.

```python
def upgrade():
    # Structure: Title Case → snake_case
    op.execute("UPDATE storyboards SET structure = 'monologue' WHERE structure = 'Monologue'")
    op.execute("UPDATE storyboards SET structure = 'dialogue' WHERE structure = 'Dialogue'")
    op.execute(
        "UPDATE storyboards SET structure = 'narrated_dialogue' "
        "WHERE structure IN ('Narrated Dialogue', 'Narrated_Dialogue')"
    )
    op.execute("UPDATE storyboards SET structure = 'monologue' WHERE structure = 'Confession'")

    # Language: Title Case → lowercase
    op.execute("UPDATE storyboards SET language = 'korean' WHERE language = 'Korean'")
    op.execute("UPDATE storyboards SET language = 'english' WHERE language = 'English'")
    op.execute("UPDATE storyboards SET language = 'japanese' WHERE language = 'Japanese'")

    # voice_presets (혹시 Title Case 잔존 시)
    op.execute("UPDATE voice_presets SET language = LOWER(language) WHERE language != LOWER(language)")

def downgrade():
    # Reversible: snake_case → Title Case (복원용)
    op.execute("UPDATE storyboards SET structure = 'Monologue' WHERE structure = 'monologue'")
    op.execute("UPDATE storyboards SET structure = 'Dialogue' WHERE structure = 'dialogue'")
    op.execute(
        "UPDATE storyboards SET structure = 'Narrated Dialogue' "
        "WHERE structure = 'narrated_dialogue'"
    )
    op.execute("UPDATE storyboards SET language = 'Korean' WHERE language = 'korean'")
    op.execute("UPDATE storyboards SET language = 'English' WHERE language = 'english'")
    op.execute("UPDATE storyboards SET language = 'Japanese' WHERE language = 'japanese'")
```

**엣지 케이스**:
- soft-deleted 레코드도 UPDATE 대상 (WHERE 절에 `deleted_at` 필터 없음 — 의도적. 복원 시 정규화 상태여야 함)
- NULL 값은 UPDATE WHERE 절에 매칭되지 않으므로 안전
- `voice_presets.language`가 `LOWER()` 함수로 안전하게 변환

**영향 범위**: `storyboards` 테이블 + `voice_presets` 테이블 (data-only, 스키마 변경 없음)

### D. Frontend 동기화

#### D-1. `structure.ts` — 방어 패턴 단순화

**현재**:
```typescript
export function isMultiCharStructure(structure: string): boolean {
  const s = structure.toLowerCase().replace(/ /g, "_");
  return s === "dialogue" || s === "narrated_dialogue";
}
```

**변경**:
```typescript
export function isMultiCharStructure(structure: string): boolean {
  return structure === "dialogue" || structure === "narrated_dialogue";
}
```
- DB/Backend가 정규화된 ID만 반환하므로 `.toLowerCase().replace()` 불필요

#### D-2. `SpeakerBadge.tsx` — `normalizeStructure()` 제거

**현재**: `normalizeStructure()` 내부 함수가 `.toLowerCase().replace(/ /g, "_")` 수행
**변경**: 함수 제거. `getAvailableSpeakers()`/`shouldShowBadge()` 내에서 structure를 직접 비교.

```typescript
function getAvailableSpeakers(structure?: string): Scene["speaker"][] {
  if (structure === "narrated_dialogue") return ["A", "B", "Narrator"];
  if (structure === "dialogue") return ["A", "B"];
  return ["A"];
}
```

#### D-3. `SceneEssentialFields.tsx` — 직접 비교

**현재**: `const isNarratedDialogue = structure?.toLowerCase().replace(/ /g, "_") === "narrated_dialogue"`
**변경**: `const isNarratedDialogue = structure === "narrated_dialogue"`

#### D-4. `StoryboardGeneratorPanel.tsx` — `.toLowerCase()` 비교 제거

**현재**: `presets.find((p) => p.structure.toLowerCase() === structure.toLowerCase())`
**변경**: `presets.find((p) => p.structure === structure)`
- presets의 structure와 store의 structure가 모두 snake_case이므로 직접 비교

### E. LangFuse 프롬프트 검사

37개 프롬프트 확인 결과:
- `{{structure}}`, `{{language}}` 템플릿 변수 사용 → 코드 쪽 값 변경으로 자동 반영
- `storyboard/dialogue`에 `"Narrative Structure: Dialogue"` 리터럴 존재하나, 이는 프롬프트 자체의 설명이지 데이터가 아님 → 변경 불필요
- 리터럴 `"Monologue"`, `"Korean"` 등이 데이터로 사용되는 프롬프트 없음

**결론: LangFuse 프롬프트 변경 불필요.**

### F. 테스트

#### F-1. Backend 스냅샷 (10파일)

`backend/tests/snapshots/snapshot_*.json`에 `"structure": "Monologue"`, `"language": "Korean"` 등 Title Case 존재.

**변경**: 각 스냅샷의 `"structure"` → snake_case, `"language"` → lowercase로 업데이트.

| 파일 | structure | language |
|------|-----------|----------|
| snapshot_01_monologue_kr | "Monologue" → "monologue" | "Korean" → "korean" |
| snapshot_02_monologue_en | "Monologue" → "monologue" | "English" → "english" |
| snapshot_03_monologue_jp | "Monologue" → "monologue" | "Japanese" → "japanese" |
| snapshot_04_dialogue_kr | "Dialogue" → "dialogue" | "Korean" → "korean" |
| snapshot_05_narrated_dialogue_kr | "Narrated Dialogue" → "narrated_dialogue" | "Korean" → "korean" |
| snapshot_06_monologue_group | "Monologue" → "monologue" | "Korean" → "korean" |
| snapshot_07_monologue_male | "Monologue" → "monologue" | "Korean" → "korean" |
| snapshot_08_short_duration | "Monologue" → "monologue" | "Korean" → "korean" |
| snapshot_09_long_duration | "Monologue" → "monologue" | "Korean" → "korean" |
| snapshot_10_dialogue_en | "Dialogue" → "dialogue" | "English" → "english" |

#### F-2. Backend 테스트 (~6파일)

Title Case 하드코딩이 남아있는 테스트 파일:
- `test_coerce_functions.py` — 입력 테스트이므로 Title Case 유지 (coerce 함수 테스트)
- `test_dialogue_speaker_fix.py` — "Dialogue" 문자열 (에러 메시지 검증 → 실제 출력 확인 후 조정)
- `test_auto_pin_calculation.py` — `"Dialogue"`, `"DIALOGUE"`, `"Narrated Dialogue"` 입력 테스트 → 정규화 후 직접 비교로 변경되면 snake_case 입력으로 전환
- `test_router_presets.py` — `"Monologue"`, `"Dialogue"` name 필드 검증 (label이므로 유지)
- `test_dialogue_storyboard.py` — preset name 검증 (label이므로 유지)
- `test_analyze_topic.py` — 결과의 structure 값 검증 → snake_case로 변경

**전략**:
- coerce 함수 테스트: Title Case 입력 → snake_case 출력 테스트 유지 (과도기 함수 검증)
- structure/language 결과 검증 테스트: 기대값을 snake_case/lowercase로 변경
- preset name/label 검증: Title Case 유지 (label은 디스플레이 이름)

#### F-3. Frontend 테스트 (~8파일)

`frontend/tests/`에 `"Monologue"`, `"Korean"` 등 Title Case fixture 존재:
- `fixtures/studio.ts` — `structure: "Monologue"`, `default_language: "Korean"` → snake_case/lowercase
- `fixtures/voices.ts` — `language: "Korean"` → "korean"
- `actions.test.ts` — `structure: "Monologue"` → "monologue"
- `mappers.test.ts` — `language: "Korean"`, `structure: "Monologue"` → lowercase/snake_case
- `sseProcessor.test.ts` — `structure: "Dialogue"` → "dialogue"
- `StageCastingCompareCard.test.tsx` — `structure: "Monologue"` → "monologue"
- `CastingBanner.test.tsx` — `structure: "Dialogue"` → "dialogue"
- `structure.test.ts` — `isMultiCharStructure("Dialogue")` 등 → 직접 비교 테스트로 전환
- `warning-toast-e2e.spec.ts` — `language: "Korean"`, `structure: "Monologue"` → 정규화

#### F-4. `structure.test.ts` 특수 처리

**현재**: Title Case, 공백 형식 등 다양한 입력 테스트
```typescript
expect(isMultiCharStructure("Dialogue")).toBe(true);
expect(isMultiCharStructure("narrated dialogue")).toBe(true);
```

**변경**: `isMultiCharStructure()`가 정규화 없이 직접 비교하므로:
```typescript
// 정규화된 ID만 테스트
expect(isMultiCharStructure("dialogue")).toBe(true);
expect(isMultiCharStructure("narrated_dialogue")).toBe(true);
expect(isMultiCharStructure("monologue")).toBe(false);
// 비정규화 입력은 false (방어 코드 제거됨)
expect(isMultiCharStructure("Dialogue")).toBe(false);
expect(isMultiCharStructure("Narrated Dialogue")).toBe(false);
```

---

## 영향 범위 요약

| 영역 | 파일 수 | 변경 내용 |
|------|---------|----------|
| Backend 서비스 | 3 | 방어 패턴 제거 (gemini_generator, scene_postprocess, presets) |
| DB 마이그레이션 | 1 | storyboards.structure/language + voice_presets.language UPDATE |
| Frontend 코드 | 4 | 방어 패턴 제거 (structure.ts, SpeakerBadge, SceneEssentialFields, StoryboardGeneratorPanel) |
| Backend 스냅샷 | 10 | Title Case → snake_case/lowercase |
| Backend 테스트 | ~4 | 기대값 정규화 |
| Frontend 테스트 | ~8 | fixture/기대값 정규화 |
| LangFuse | 0 | 변경 불필요 |
| **합계** | **~30** | |

## 테스트 전략

### RED 테스트 (구현 전 작성)

1. **DB 마이그레이션 검증 테스트**: `test_enum_id_migration.py`
   - 마이그레이션 전: Title Case 데이터가 DB에 존재
   - 마이그레이션 후: 모든 structure가 snake_case, 모든 language가 lowercase
   - downgrade 후: Title Case로 복원 확인

2. **방어 패턴 제거 확인**: 기존 `test_auto_pin_calculation.py`의 Title Case 입력 테스트 → snake_case 입력으로 변경. Title Case 입력 시 기존과 다른 결과가 나오는지 확인.

### GREEN (기존 테스트 적응)

- 스냅샷 10개 업데이트
- fixture Title Case → snake_case/lowercase
- 전체 pytest + vitest PASS 확인

### 회귀 방지

- `coerce_structure_id()` 테스트는 유지 (레거시 입력 처리 검증)
- `isMultiCharStructure()` 테스트를 직접 비교 기반으로 전환

## Out of Scope

- `coerce_*()` 함수 완전 제거 — 외부 입력 레거시 호환 유지. SP-021 이후 별도 정리.
- Speaker 정규화 ("A"/"B"/"Narrator" → "speaker_1"/"speaker_2"/"narrator") — SP-021 범위.
- Frontend `SPEAKER_STYLES`/`SPEAKER_COLORS` 키 정규화 — SP-021 범위.
- tag normalization 패턴 (`.lower().replace(" ", "_")`) — 태그 시스템 고유 패턴이므로 SP-020 범위 아님.
- `StoryboardGeneratorPanel`의 `recommendedStructure` `.toLowerCase()` 비교 — 이 값은 topic analysis에서 오는데, 이미 snake_case를 반환. 방어 제거 대상에 포함.

## 실행 순서

1. **Alembic 마이그레이션 생성** (C)
2. **Backend 코드 변경** (B-1, B-2, B-3)
3. **Frontend 코드 변경** (D-1 ~ D-4)
4. **스냅샷 업데이트** (F-1)
5. **Backend 테스트 업데이트** (F-2)
6. **Frontend 테스트 업데이트** (F-3, F-4)
7. **마이그레이션 적용 + 전체 테스트 실행**

## DBA 리뷰 필요 사항

- Alembic 마이그레이션: data-only UPDATE (스키마 변경 없음)
- downgrade 가능 여부 확인
- soft-deleted 레코드 포함 여부 (포함 — 의도적)
- `voice_presets.language` LOWER() 변환 안전성
