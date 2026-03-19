# Enum ID 정규화 — Structure / Language / Style 타입 분리

> 작성: 2026-03-19 | 상태: **미착수**
> 발단: Structure 포맷 이원화 (`"narrated_dialogue"` vs `"Narrated Dialogue"`) → Narrator 씬에 Actor A 표시 버그

---

## 1. 배경

현재 `structure`, `language` 등 enum-like 필드가 **디스플레이 이름을 데이터 ID로 사용**하는 안티패턴이 전체 코드베이스에 만연해 있다.

### 현재 문제

```python
# config.py — Title Case 디스플레이 이름이 DB 저장값
DEFAULT_STRUCTURE = "Monologue"        # ← 디스플레이 이름 = 데이터 ID
STORYBOARD_LANGUAGES = [
    {"value": "Korean", "label": "한국어"},  # ← value가 디스플레이 이름
]

# 코드 전반에서 방어적 정규화 난무
structure.lower().replace("_", " ")   # helpers.py, creative_qc.py, gemini_generator.py
normalize_structure(structure)         # Title Case 변환 함수가 존재하는 것 자체가 문제의 증거
```

### 실제 발생한 버그

| 버그 | 원인 | 파일 |
|------|------|------|
| Narrator 씬에 "Actor A" 배지 표시 | `"narrated_dialogue"` (underscore) vs `"narrated dialogue"` (space) 포맷 불일치 | `SpeakerBadge.tsx` |
| `_DIALOGUE_STRUCTURES`에 3가지 변형 저장 | `{"Dialogue", "Narrated Dialogue", "Narrated_Dialogue"}` — 포맷 불일치 방어 | `helpers.py:34` |
| TTS language 대소문자 불일치 | `TTS_DEFAULT_LANGUAGE="korean"` vs `STORYBOARD_LANGUAGES.value="Korean"` | `config.py` |

---

## 2. 목표

**정석 패턴 `{id, label}` 분리** — DB에는 정규화된 ID만 저장, UI 표시는 매핑 테이블에서 파생.

```python
# Before (안티패턴)
DEFAULT_STRUCTURE = "Monologue"              # 디스플레이 이름 = 데이터 ID

# After (정석)
STRUCTURES = [
    {"id": "monologue",           "label": "Monologue"},
    {"id": "dialogue",            "label": "Dialogue"},
    {"id": "narrated_dialogue",   "label": "Narrated Dialogue"},
    {"id": "confession",          "label": "Confession"},
]
DEFAULT_STRUCTURE = "monologue"              # 정규화된 ID
```

---

## 3. 대상 필드 분석

### 3-1. Structure (HIGH — 47+ 파일)

| 항목 | 현재 | 목표 |
|------|------|------|
| DB 저장값 | `"Monologue"`, `"Narrated Dialogue"` (Title Case) | `"monologue"`, `"narrated_dialogue"` (snake_case) |
| 비교 방식 | `.lower()`, `.lower().replace("_", " ")` 산재 | 직접 `==` 비교 (정규화 불필요) |
| 중복 상수 | `_TWO_CHAR_STRUCTURES` 2곳, `_DIALOGUE_STRUCTURES` 3변형 | `config.py` SSOT 1곳 |
| Frontend | `DEFAULT_STRUCTURE = "Monologue"` 하드코딩 | `/presets` API에서 수신 |

**영향 범위 (코드 감사 결과)**:
- `config.py:296` — `DEFAULT_STRUCTURE`
- `services/presets.py:35,51,67,83` — 프리셋 정의
- `services/storyboard/helpers.py:34,37-45` — `normalize_structure()`, `_DIALOGUE_STRUCTURES`
- `services/storyboard/crud.py:75` — `.lower()` 비교
- `services/creative_qc.py:106-114` — `.lower().replace("_"," ")` 비교
- `services/script/gemini_generator.py:264-266` — `.lower().replace("_"," ")` 비교
- `services/agent/llm_models.py:27` — `_TWO_CHAR_STRUCTURES` (중복)
- `services/agent/nodes/inventory_resolve.py:14` — `_TWO_CHAR_STRUCTURES` (중복)
- `services/agent/nodes/finalize.py:173` — `.lower()`
- `schemas.py` — 다수 스키마 기본값
- `frontend/app/constants/index.ts` — `DEFAULT_STRUCTURE`
- 테스트 다수 — 하드코딩 문자열

### 3-2. Language (MEDIUM — 15+ 파일)

| 항목 | 현재 | 목표 |
|------|------|------|
| DB 저장값 | `"Korean"`, `"English"` (Title Case) | `"korean"`, `"english"` (lowercase) |
| config 불일치 | `TTS_DEFAULT_LANGUAGE="korean"` vs `STORYBOARD_LANGUAGES.value="Korean"` | 통일 |
| Frontend | 하드코딩 없음 (API에서 수신) | 유지 |

**영향 범위**:
- `config.py:718` — `TTS_DEFAULT_LANGUAGE` (이미 lowercase)
- `config.py:776-779` — `STORYBOARD_LANGUAGES[].value` (Title Case → lowercase)
- `services/storyboard/helpers.py:96` — `READING_SPEED` dict 키 (Title Case)
- `services/scripts/topic_analysis.py:40` — fallback `"Korean"`
- `services/video/tts_helpers.py` — language 비교
- `models/voice_preset.py:28` — `language` default `"korean"` (이미 lowercase)

### 3-3. Style (LOW — 6 파일)

| 항목 | 현재 | 목표 |
|------|------|------|
| 참조 방식 | 대부분 `style_profile_id` FK 사용 (정석) | 유지 |
| 문제점 | 셋업 스크립트에서 `name` 문자열 조회 | 셋업 스크립트 정리 |

**영향 범위**:
- `scripts/create_style_profiles.py:27,53` — name 기반 조회
- `scripts/setup_default_style.py:99` — name 기반 조회
- 나머지는 FK 사용 (정상)

---

## 4. 설계

### 4-1. config.py SSOT 정의

```python
# ===== Structure =====
STRUCTURES = [
    {"id": "monologue",           "label": "Monologue"},
    {"id": "dialogue",            "label": "Dialogue"},
    {"id": "narrated_dialogue",   "label": "Narrated Dialogue"},
    {"id": "confession",          "label": "Confession"},
]
DEFAULT_STRUCTURE = "monologue"
MULTI_CHAR_STRUCTURES = frozenset({"dialogue", "narrated_dialogue"})

# ===== Language =====
LANGUAGES = [
    {"id": "korean",   "label": "한국어"},
    {"id": "english",  "label": "English"},
    {"id": "japanese", "label": "日本語"},
]
DEFAULT_LANGUAGE = "korean"
```

### 4-2. `/presets` API 확장

```json
{
  "structures": [
    {"id": "monologue", "label": "Monologue"},
    {"id": "dialogue", "label": "Dialogue"},
    ...
  ],
  "languages": [
    {"id": "korean", "label": "한국어"},
    ...
  ]
}
```

### 4-3. `inventory.py` StructureMeta 통합

> **발견**: `inventory.py`에 이미 `{id, label}` 패턴이 존재함!

```python
# 현재 inventory.py — 이미 올바른 구조
StructureMeta(id="monologue", name="Monologue", ...)
StructureMeta(id="narrated_dialogue", name="Narrated Dialogue", ...)
```

이 정의를 `config.py` SSOT로 승격하고, `inventory.py`는 `config.STRUCTURES`를 참조하도록 변경.

### 4-4. Prompt Builders 정규화 (추가 영향)

**`prompt_builders_writer.py`**, **`prompt_builders_c.py`**에 하드코딩된 비교 + 예시 텍스트:

| 함수 | 하드코딩 | 변경 |
|------|---------|------|
| `build_structure_rules_block()` | `if structure == "Monologue"` | → `if structure == "monologue"` |
| `build_output_format_block()` | `"speaker": "Narrator"` JSON 예시 | → `"speaker": "narrator"` (Speaker 정규화 연계) |
| `build_language_hint()` | `if language == "Korean"` | → `if language == "korean"` |
| `build_korean_hint()` | `if language != "Korean"` | → `if language != "korean"` |
| `build_korean_quality_rules()` | `if language == "Korean"` | → `if language == "korean"` |
| `build_structure_speaker_rule()` | `if structure == "Dialogue"` | → `if structure == "dialogue"` |

### 4-5. LangFuse 템플릿 변수 영향

`compile_prompt()`에 전달되는 template 변수 포맷이 변경됨:

```python
# Before
compile_prompt("writer/...", language="Korean", structure="Monologue")

# After
compile_prompt("writer/...", language="korean", structure="monologue")
```

LangFuse 프롬프트 텍스트에서 `{{structure}}`/`{{language}}` 사용 시:
- **변수만 사용**: 자동 반영 (코드 변경만으로 충분)
- **리터럴 예시 텍스트**: LangFuse 프롬프트 본문에 `"Monologue"` 등이 직접 기술된 경우 수동 업데이트 필요

**액션**: Sprint A 착수 전 LangFuse 프롬프트 28개 전수 검사 추가.

### 4-6. 불필요 코드 제거

| 제거 대상 | 이유 |
|-----------|------|
| `normalize_structure()` | ID가 통일되면 정규화 불필요 |
| `_DIALOGUE_STRUCTURES` 3변형 | `MULTI_CHAR_STRUCTURES` 1곳으로 통합 |
| `_TWO_CHAR_STRUCTURES` 중복 2곳 | config.py SSOT 참조 |
| `.lower().replace("_", " ")` 패턴 | 직접 비교 가능 |

### 4-7. 테스트 영향 (953건)

| 카테고리 | Structure | Language | Speaker | 합계 |
|----------|-----------|----------|---------|------|
| Backend 테스트 (31파일) | 145 | 128 | 648 | 921 |
| Frontend 테스트 (2파일) | 12 | 7 | 12 | 31 |
| 스냅샷 (8파일) | 파일명 포함 | — | — | 8 |

> Speaker 648건은 [SPEAKER_DYNAMIC_ROLE.md](SPEAKER_DYNAMIC_ROLE.md) 범위. 본 피처에서는 Structure(158) + Language(135) = **293건** 업데이트.

### 4-8. 추가 영향 (3차 감사 결과)

#### `READING_SPEED` / `SPEECH_METRICS` dict 키 (CRITICAL)

```python
# config.py:791-795 — 언어 디스플레이 이름이 dict KEY
READING_SPEED = {
    "Korean": {"cps": 4.0, "unit": "chars"},
    "Japanese": {"cps": 5.0, "unit": "chars"},
    "English": {"wps": 2.5, "unit": "words"},
}
```

language ID 전환 시 이 dict 키도 함께 변경 필수. `helpers.py:96`에서 `READING_SPEED.get(language, ...)` 호출.

#### `_DIALOGUE_STRUCTURES` 3곳 중복 정의

| 파일 | 값 |
|------|-----|
| `helpers.py:34` | `{"Dialogue", "Narrated Dialogue", "Narrated_Dialogue"}` |
| `groups/defaults.py:68` | `{"Dialogue", "Narrated Dialogue", "Narrated_Dialogue"}` |
| `finalize.py` | `{"Dialogue", "Narrated Dialogue", "Narrated_Dialogue"}` |

→ `config.py` `MULTI_CHAR_STRUCTURES` 1곳으로 통합.

#### Agent 노드 fallback 기본값 (4파일)

| 파일 | 패턴 |
|------|------|
| `writer.py` | `state.get("language", "Korean")`, `state.get("structure", "Monologue")` |
| `revise.py` | `state.get("language", "Korean")`, `state.get("structure", "Monologue")` |
| `critic.py` | `state.get("language", "Korean")`, `state.get("structure", "Monologue")` |
| `finalize.py` | `speaker == "Narrator"` (8곳) |

→ fallback 값을 `config.DEFAULT_LANGUAGE`, `config.DEFAULT_STRUCTURE` 상수 참조로 전환.

#### `schemas_creative.py` 기본값

```python
# DirectorPlanCreateRequest
structure: str = "Monologue"   # → DEFAULT_STRUCTURE
language: str = "Korean"       # → DEFAULT_LANGUAGE
```

#### Frontend Store/Hooks 기본값 (5파일)

| 파일 | 하드코딩 |
|------|---------|
| `useStoryboardStore.ts:36-37` | `language: "Korean"`, `structure: DEFAULT_STRUCTURE` |
| `useScriptEditor.ts` | `language: "Korean"`, `structure: "Monologue"` |
| `useSceneActions.ts` | `speaker: "Narrator" as const` |
| `useTTSPreview.ts` | `speaker: scene.speaker \|\| "Narrator"` |
| `chatMessageFactory.ts:106` | `structure: editor?.structure ?? "Monologue"` |

#### Frontend speakerResolver.ts (6+ 비교)

```typescript
// 6개 함수 모두 speaker === "Narrator", speaker === "B" 직접 비교
resolveCharacterIdForSpeaker()
resolveIpAdapterForSpeaker()
resolveNegativePromptForSpeaker()
resolveBasePromptForSpeaker()
resolveCharacterLorasForSpeaker()
```

> Speaker 관련은 [SPEAKER_DYNAMIC_ROLE.md](SPEAKER_DYNAMIC_ROLE.md) 범위이나, structure/language 기본값과 동시에 작업 필요.

#### Frontend 컴포넌트 speaker 색상/라벨 (4파일)

| 파일 | 하드코딩 |
|------|---------|
| `SpeakerBadge.tsx` | `"Narrator"`, `"A"`, `"B"` 비교 → 색상/라벨 |
| `SceneEssentialFields.tsx` | `language === "Japanese"` 조건, `<option value="Narrator">` |
| `StageScenePrepSection.tsx` | `Narrator: "bg-zinc-100 text-zinc-500"` |
| `CompletionCard.tsx` | speaker별 색상 분기 |

#### `revise.py` 정규식 패턴 (5차 감사)

```python
# revise.py:27-28 — 정규식에 speaker/structure 하드코딩
_INVALID_SPEAKER_RE = re.compile(r'"speaker"\s*:\s*"(?!A|Narrator|B")')
_DIALOGUE_MISSING_SPEAKER_RE = re.compile(r'"structure"\s*:\s*"Dialogue"')
```

→ 정규식 패턴도 정규화된 ID(`"speaker_1"`, `"narrator"`, `"dialogue"`)로 전환 필요.

#### 헬퍼 함수 파라미터 기본값 (5차 감사)

```python
# 여러 헬퍼 함수에서 파라미터 기본값으로 디스플레이 이름 사용
def build_scene_count_range(structure: str = "Monologue", ...):
def redistribute_durations(structure: str = "Monologue", ...):
```

→ `config.DEFAULT_STRUCTURE` 상수 참조로 전환.

#### 추가 Agent 노드 fallback (5~6차 감사)

```python
# 5차: 기존 4파일 외 추가 발견
state.get("structure", "Monologue")  # _revise_expand.py, location_planner.py

# 6차: 추가 6파일 발견 (총 11파일)
state.get("language", "Korean")      # research.py, review.py, sound_designer.py
state.get("language", "Korean")      # director_plan.py, copyright_reviewer.py
state.get("language", "Korean")      # tts_designer.py
```

→ A-14 작업에 전부 포함 (11파일).

#### `scene_postprocess.py` speaker 비교 (6차 감사)

```python
# scene_postprocess.py:52
if s.get("speaker") != "Narrator":
# scene_postprocess.py:187
if "A" not in speakers or "B" not in speakers:
```

→ A-19 작업에 포함. Speaker 피처와 동시 작업.

#### `cinematographer.py` speaker 하드코딩 (6차 감사)

```python
# cinematographer.py:66
speakers: dict[str, int] = {}
if character_id:
    speakers["A"] = character_id
if character_b_id:
    speakers["B"] = character_b_id
```

→ A-20 작업에 포함. `character_b_id` 리팩토링과 연계 (Speaker 피처 Phase B).

#### Agent 헬퍼 유틸 Narrator 필터 (6차 감사)

```python
# _context_tag_utils.py:273
char_scenes = [s for s in scenes if s.get("speaker") != "Narrator"]
# _diversify_utils.py:164
target = scenes if include_narrator else [s for s in scenes if s.get("speaker") != "Narrator"]
# _finalize_validators.py:120,125,130
if speaker == "Narrator": ...
if speaker == "B": ...
```

→ A-21 작업에 포함.

#### `scene_editor.py`, `topic_analysis.py` fallback (6차 감사)

```python
# scene_editor.py:39-40
context_language = context.get("language") or "Korean"
context_structure = context.get("structure") or "Monologue"

# topic_analysis.py:40-41, 136, 141
language="Korean", structure="Monologue"  # fallback 3곳
```

→ A-22 작업에 포함.

#### `crud.py` 추가 중복 + 역방향 정규화 (7차 감사)

```python
# crud.py:21 — 4번째 DIALOGUE_STRUCTURES 중복
_MULTI_CHAR_STRUCTURES = {"dialogue", "narrated dialogue", "narrated_dialogue"}

# crud.py:397 — .title() 역방향 정규화 (snake_case → Title Case 복원)
storyboard.structure = raw_structure.replace("_", " ").title() if raw_structure else raw_structure
```

→ A-13에 crud.py 추가. A-6에 `.title()` 역방향 패턴 포함.

#### `preview_validate.py` language 하드코딩 (7차 감사)

```python
# preview_validate.py:132
ck = tts_cache_key(cleaned, None, None, "korean", speaker=...)
```

→ A-23 작업에 포함.

#### `scene_postprocess.py` 추가 speaker 비교 (7차 감사)

```python
# scene_postprocess.py:206, 225, 227 — 기존 52, 187 외 추가 3곳
a_count = sum(1 for s in non_narrator if s.get("speaker") == "A")
sum(1 for s in non_narrator if s["speaker"] == "A")
sum(1 for s in non_narrator if s["speaker"] == "B")
```

→ A-19 범위 확대 (2→5곳).

#### 테스트 factory 함수 기본값 (7차 감사)

```python
# test_creative_qc_music.py:66
def _make_scripts(count: int, language: str = "Korean") -> list[dict]:

# test_groups.py:155-164
defaults = {"structure": "Monologue", "language": "Korean", ...}

# test_dialogue_speaker_fix.py:18
def _make_scene(speaker: str = "A", ...) -> dict:
```

→ Sprint C-1 범위. factory 함수 기본값도 상수 참조 전환 필요.

#### Alembic 마이그레이션 server_default

기존 마이그레이션에 `server_default='Narrator'`가 하드코딩. 새 마이그레이션에서 default 변경 포함.

#### 에러 메시지 (creative_qc.py)

```python
"Dialogue requires both A and B, missing: ..."
"Narrated Dialogue requires Narrator, A, and B, missing: ..."
```

사용자 표시 메시지에 구조 디스플레이 이름 포함 — label 매핑 함수 사용으로 전환.

### 4-9. DB 마이그레이션

```sql
-- Structure: Title Case → snake_case
UPDATE storyboards SET structure = 'monologue' WHERE structure = 'Monologue';
UPDATE storyboards SET structure = 'dialogue' WHERE structure = 'Dialogue';
UPDATE storyboards SET structure = 'narrated_dialogue' WHERE LOWER(REPLACE(structure, ' ', '_')) = 'narrated_dialogue';
UPDATE storyboards SET structure = 'confession' WHERE structure = 'Confession';

UPDATE scenes SET structure = LOWER(REPLACE(structure, ' ', '_')) WHERE structure IS NOT NULL;

-- Language: Title Case → lowercase
UPDATE storyboards SET language = LOWER(language) WHERE language IS NOT NULL;
UPDATE voice_presets SET language = LOWER(language) WHERE language IS NOT NULL;
```

### 4-10. Frontend 전수 영향 (28파일, 70+ 참조)

#### 상수/기본값 (5파일)

| 파일 | 현재 | 변경 |
|------|------|------|
| `constants/index.ts:29` | `DEFAULT_STRUCTURE = "Monologue"` | 제거, store/presets 수신 |
| `useScriptEditor.ts:55-56` | `language: "Korean"`, `structure: "Monologue"` | `DEFAULT_LANGUAGE`, `DEFAULT_STRUCTURE` 상수 |
| `useStoryboardStore.ts:138` | `language: "Korean"` | `DEFAULT_LANGUAGE` |
| `useTTSPreview.ts:62,97,153` | `language: "korean"` | 이미 lowercase — ID 전환 후 그대로 유지 |
| `useVoicePresets.ts:21` | `language: "korean"` | 이미 lowercase — 유지 |

#### UI 매핑 테이블 (2파일 — 핵심)

```typescript
// CompletionCard.tsx:9-14 — structure ID → 한국어 라벨
const STRUCTURE_LABELS: Record<string, string> = {
  Monologue: "독백",           // → monologue: "독백"
  Dialogue: "대화형",          // → dialogue: "대화형"
  "Narrated Dialogue": "내레이션 대화",  // → narrated_dialogue: "내레이션 대화"
  Confession: "고백",          // → confession: "고백"
};

// SpeakerBadge.tsx:14-18 — speaker ID → 색상/라벨
const SPEAKER_STYLES = {
  A: { bg: "bg-blue-100", label: "A" },        // Speaker 피처 범위
  B: { bg: "bg-violet-100", label: "B" },       // Speaker 피처 범위
  Narrator: { bg: "bg-amber-100", label: "N" }, // Speaker 피처 범위
};
```

→ `STRUCTURE_LABELS` 키를 snake_case ID로 전환. 또는 `/presets` API에서 `{id, label}` 수신.

#### 비교 로직 (8파일)

| 파일 | 비교 코드 | 영역 |
|------|----------|------|
| `structure.ts:3-4` | `s === "dialogue" \|\| s === "narrated dialogue"` | Structure |
| `SceneEssentialFields.tsx:36` | `structure?.toLowerCase() === "narrated dialogue"` | Structure |
| `SceneEssentialFields.tsx:166` | `language === "Japanese" ? "字" : "자"` | Language |
| `SpeakerBadge.tsx:22-31` | structure→speakers 매핑 + shouldShowBadge | Structure+Speaker |
| `speakerResolver.ts` (6함수) | `speaker === "Narrator"`, `speaker === "B"` | Speaker |
| `sceneActions.ts:47,52` | `speaker === "B" ? promptB : promptA` | Speaker |
| `preflight-settings.ts:36` | `s.speaker === "Narrator"` | Speaker |
| `imageGeneration.ts:62` | `scene.speaker === "Narrator"` | Speaker |
| `SceneToolsContent.tsx:44` | `currentSpeaker === "Narrator"` | Speaker |

#### UI 표시 (SceneEssentialFields dropdown)

```tsx
// SceneEssentialFields.tsx:75-77
{isNarratedDialogue && <option value="Narrator">Narrator</option>}
<option value="A">Actor A</option>
{hasMultipleSpeakers && <option value="B">Actor B</option>}
```

→ Speaker 피처 범위이나, structure 조건(`isNarratedDialogue`)은 본 피처에서 수정.

#### 타입 정의 (1파일)

```typescript
// types/index.ts:60
speaker: "Narrator" | "A" | "B"  // → Speaker 피처에서 string으로 전환
```

---

## 5. 실행 계획

### Sprint A: config.py SSOT + Backend 정규화 (핵심)

| # | 작업 | 파일 | 담당 |
|---|------|------|------|
| A-1 | `STRUCTURES`, `LANGUAGES` 상수 정의 (`inventory.py` StructureMeta 흡수) | `config.py` | Backend Dev |
| A-2 | `DEFAULT_STRUCTURE` → `"monologue"`, 중복 상수 제거 | `config.py` | Backend Dev |
| A-3 | `STORYBOARD_LANGUAGES` → `LANGUAGES` 통합 | `config.py`, `presets.py` | Backend Dev |
| A-4 | `/presets` API에 `structures` 필드 추가 | `presets.py`, `schemas.py` | Backend Dev |
| A-5 | `normalize_structure()` 제거 + 참조 정리 | `helpers.py` + 호출부 | Backend Dev |
| A-6 | `.lower().replace("_"," ")` 및 `.replace("_"," ").title()` 정규화 패턴 → 직접 비교 전환 | `creative_qc.py`, `gemini_generator.py`, `crud.py` | Backend Dev |
| A-7 | `_TWO_CHAR_STRUCTURES` 중복 제거 → `MULTI_CHAR_STRUCTURES` 참조 | `llm_models.py`, `inventory_resolve.py` | Backend Dev |
| A-8 | `_VALID_SPEAKERS` dict 키 → snake_case 전환 | `creative_qc.py` | Backend Dev |
| A-9 | schemas 기본값 → `DEFAULT_STRUCTURE` 참조 확인 | `schemas.py` | Backend Dev |
| A-10 | Prompt Builders 비교문 정규화 (6함수) | `prompt_builders_writer.py`, `prompt_builders_c.py` | Backend Dev |
| A-11 | `inventory.py` → `config.STRUCTURES` 참조 전환 | `inventory.py` | Backend Dev |
| A-12 | `READING_SPEED` dict 키 → lowercase 전환 | `config.py` | Backend Dev |
| A-13 | `_DIALOGUE_STRUCTURES` / `_MULTI_CHAR_STRUCTURES` **4곳** 중복 → `MULTI_CHAR_STRUCTURES` 통합 | `helpers.py`, `defaults.py`, `finalize.py`, `crud.py` | Backend Dev |
| A-14 | Agent 노드 fallback → `config.DEFAULT_*` 상수 참조 | `writer.py`, `revise.py`, `critic.py`, `_revise_expand.py`, `location_planner.py`, `research.py`, `review.py`, `sound_designer.py`, `director_plan.py`, `copyright_reviewer.py`, `tts_designer.py` | Backend Dev |
| A-15 | `schemas_creative.py` 기본값 → 상수 참조 | `schemas_creative.py` | Backend Dev |
| A-16 | 에러 메시지 structure 이름 → label 매핑 함수 사용 | `creative_qc.py` | Backend Dev |
| A-17 | `revise.py` 정규식 패턴 하드코딩 → 상수 참조 전환 | `revise.py` | Backend Dev |
| A-18 | 헬퍼 함수 파라미터 기본값 → `config.DEFAULT_*` 참조 | `build_scene_count_range()`, `redistribute_durations()`, `prompt_builders_c.py` 내 함수 등 | Backend Dev |
| A-19 | `scene_postprocess.py` speaker/structure 비교 정규화 | `scene_postprocess.py` | Backend Dev |
| A-20 | `cinematographer.py` speaker 하드코딩 → 상수 참조 | `cinematographer.py` | Backend Dev |
| A-21 | Agent 헬퍼 유틸 Narrator 필터 → 상수 참조 | `_context_tag_utils.py`, `_diversify_utils.py`, `_finalize_validators.py` | Backend Dev |
| A-22 | `scene_editor.py`, `topic_analysis.py` fallback 기본값 → 상수 참조 | `scene_editor.py`, `topic_analysis.py` | Backend Dev |
| A-23 | `preview_validate.py` language 하드코딩 → 상수 참조 | `preview_validate.py` | Backend Dev |

### Sprint B: DB 마이그레이션 + LangFuse + Frontend

| # | 작업 | 파일 | 담당 |
|---|------|------|------|
| B-1 | Alembic 마이그레이션 (structure + language 데이터 변환) | `alembic/versions/` | DBA |
| B-2 | **LangFuse 프롬프트 28개 전수 검사** — 리터럴 구조/언어명 포함 여부 확인 | LangFuse 서버 | Storyboard Writer |
| B-3 | LangFuse 프롬프트 내 리터럴 업데이트 (해당 시) | LangFuse 서버 | Storyboard Writer |
| B-4 | Frontend `DEFAULT_STRUCTURE` 제거, store/presets 수신 | `constants/index.ts` | Frontend Dev |
| B-5 | `isMultiCharStructure()` 정규화 로직 단순화 | `structure.ts` | Frontend Dev |
| B-6 | `SpeakerBadge.tsx` 포맷 불일치 버그 수정 | `SpeakerBadge.tsx` | Frontend Dev |
| B-7 | `SceneEssentialFields.tsx` 직접 비교 → 헬퍼 전환 | `SceneEssentialFields.tsx` | Frontend Dev |
| B-8 | Frontend Store/Hooks 기본값 → 상수/presets 참조 (5파일) | `useStoryboardStore.ts`, `useScriptEditor.ts`, `useSceneActions.ts`, `useTTSPreview.ts`, `chatMessageFactory.ts` | Frontend Dev |
| B-9 | `SceneEssentialFields` language 분기, speaker dropdown 정규화 | `SceneEssentialFields.tsx` | Frontend Dev |
| B-10 | Speaker 색상/라벨 컴포넌트 정규화 (Speaker 피처 선행 또는 동시) | `StageScenePrepSection.tsx`, `CompletionCard.tsx` | Frontend Dev |
| B-11 | `CompletionCard.tsx` `STRUCTURE_LABELS` 키 → snake_case ID 전환 | `CompletionCard.tsx` | Frontend Dev |
| B-12 | `SceneEssentialFields.tsx` language 분기 (`"Japanese"` → `"japanese"`) | `SceneEssentialFields.tsx` | Frontend Dev |
| B-13 | `sceneActions.ts`, `preflight-settings.ts`, `imageGeneration.ts` speaker 비교 (Speaker 피처 동시) | 3파일 | Frontend Dev |

### Sprint C: 테스트 + Style 정리 + 검증

| # | 작업 | 파일 | 담당 |
|---|------|------|------|
| C-1 | Backend 테스트 문자열 업데이트 (Structure 145건 + Language 128건) | 31개 테스트 파일 | QA |
| C-2 | Frontend 테스트 fixture 업데이트 | `studio.ts`, `voices.ts` | QA |
| C-3 | 스냅샷 파일 8개 갱신 | `tests/snapshots/` | QA |
| C-4 | 셋업/테스트 스크립트 정규화 | `scripts/create_style_profiles.py`, `setup_default_style.py`, `scripts/test_video_render.py` | Backend Dev |
| C-5 | 전체 테스트 통과 확인 | — | QA |
| C-6 | E2E 검증 (파이프라인 실행 → structure/language 정상 저장 확인) | — | QA |

---

## 6. 후방 호환성

| 항목 | 전략 |
|------|------|
| 기존 DB 데이터 | Alembic 마이그레이션으로 일괄 변환 |
| Gemini 응답 | `CastingModel.structure` → 이미 lowercase 반환. 검증 후 저장 |
| LangFuse 프롬프트 | structure/language 예시 확인 및 업데이트 |
| Frontend localStorage | 기존 structure 값 마이그레이션 로직 추가 (1회성) |

---

## 7. DoD (Definition of Done)

### Backend
- [ ] `config.py`에 `STRUCTURES`, `LANGUAGES` SSOT 정의 (inventory.py StructureMeta 흡수)
- [ ] `READING_SPEED` dict 키 lowercase 전환
- [ ] `normalize_structure()` 함수 완전 제거
- [ ] `.lower().replace("_", " ")` 패턴 0건
- [ ] `_DIALOGUE_STRUCTURES` / `_TWO_CHAR_STRUCTURES` / `_MULTI_CHAR_STRUCTURES` 중복 0건 → `MULTI_CHAR_STRUCTURES` 통합 (**4곳**: helpers/defaults/finalize/crud)
- [ ] Agent 노드 fallback → `config.DEFAULT_*` 상수 참조 (**11파일**: writer/revise/critic/finalize/_revise_expand/location_planner/research/review/sound_designer/director_plan/copyright_reviewer/tts_designer)
- [ ] `revise.py` 정규식 패턴 → 정규화 ID 전환
- [ ] 헬퍼 함수 파라미터 기본값 → `config.DEFAULT_*` 상수 참조 (`prompt_builders_c.py` 포함)
- [ ] `scene_postprocess.py` speaker 비교 정규화
- [ ] `cinematographer.py` speaker 하드코딩 → 상수 참조
- [ ] Agent 헬퍼 유틸 Narrator 필터 정규화 (`_context_tag_utils.py`, `_diversify_utils.py`, `_finalize_validators.py`)
- [ ] `scene_editor.py`, `topic_analysis.py` fallback → 상수 참조
- [ ] `preview_validate.py` language 하드코딩 → 상수 참조
- [ ] `scene_postprocess.py` speaker 비교 5곳 정규화 (52, 187, 206, 225, 227)
- [ ] Prompt Builders 비교문 정규화 완료 (6함수)
- [ ] `schemas.py` + `schemas_creative.py` 기본값 상수 참조
- [ ] 에러 메시지 → label 매핑 함수 사용

### DB + LangFuse
- [ ] DB 마이그레이션 적용 (structure snake_case, language lowercase)
- [ ] LangFuse 프롬프트 28개 전수 검사 + 리터럴 업데이트

### Frontend (28파일, 70+ 참조)
- [ ] `/presets` API에 `structures` 필드 포함
- [ ] `DEFAULT_STRUCTURE` 하드코딩 제거 → store/presets 수신
- [ ] Store/Hooks 기본값 상수 참조 (5파일)
- [ ] `STRUCTURE_LABELS` 키 snake_case 전환 (`CompletionCard.tsx`)
- [ ] `SpeakerBadge` 포맷 불일치 버그 해소 + `SPEAKER_STYLES` 키 정규화
- [ ] `SceneEssentialFields` language 분기 (`"Japanese"` → `"japanese"`) + speaker dropdown
- [ ] `sceneActions.ts` / `preflight-settings.ts` / `imageGeneration.ts` speaker 비교 정규화
- [ ] `structure.ts` → snake_case 직접 비교로 단순화

### 테스트
- [ ] Backend 테스트 273건 업데이트 (Structure 145 + Language 128)
- [ ] Frontend 테스트 fixture 19건 업데이트
- [ ] 스냅샷 8개 갱신
- [ ] 전체 테스트 PASS
- [ ] E2E 파이프라인 검증 통과

---

## 8. 참조 문서

| 문서 | 관련 |
|------|------|
| [MULTI_CHARACTER.md](MULTI_CHARACTER.md) | structure-speaker 연동 |
| [SPEAKER_DYNAMIC_ROLE.md](SPEAKER_DYNAMIC_ROLE.md) | speaker 필드 동적 역할 체계 (별도 피처) |
| [AGENTIC_PIPELINE.md](AGENTIC_PIPELINE.md) | CastingModel.structure 반환 포맷 |
| `config.py` | 상수 SSOT |
| `services/presets.py` | `/presets` API |

---

**Last Updated:** 2026-03-19
