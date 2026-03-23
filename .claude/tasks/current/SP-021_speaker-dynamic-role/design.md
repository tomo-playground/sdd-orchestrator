---
task: SP-021
phase: A
designed_at: 2026-03-23
---

## 설계 요약

Phase A는 speaker ID 문자열만 정규화하는 기계적 변환.
`"A"` → `"speaker_1"`, `"B"` → `"speaker_2"`, `"Narrator"` → `"narrator"`.
API 계약/DB 스키마(컬럼 정의)/변수명은 변경하지 않음 (Phase B 범위).

**핵심 전략**: 리터럴 문자열을 `config.py` 상수 참조로 교체 → INV-4 준수 + 향후 변경 시 1곳만 수정.

## 변경 파일 요약

### Backend — 코드 변경 필요 (10개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 1 | `config.py` | 상수 값 변경: `SPEAKER_A="speaker_1"`, `SPEAKER_B="speaker_2"`, `DEFAULT_SPEAKER="narrator"` |
| 2 | `services/agent/nodes/_review_validators.py` | `VALID_SPEAKERS` → config 상수 import 사용 |
| 3 | `services/creative_qc.py` | `_VALID_SPEAKERS` → config 상수 import 사용 |
| 4 | `services/agent/nodes/finalize.py` | `== "Narrator"` → `== DEFAULT_SPEAKER`, `== "B"` → `== SPEAKER_B` 등 |
| 5 | `services/agent/nodes/_finalize_validators.py` | 동일 패턴 적용 |
| 6 | `services/script/scene_postprocess.py` | `"A"/"B"` → `SPEAKER_A/SPEAKER_B`, 대화 교대배정 상수화 |
| 7 | `services/agent/nodes/revise.py` | regex 패턴 업데이트 + speaker 할당 상수화 |
| 8 | `services/agent/nodes/cinematographer.py` | speakers dict 키 `"A"/"B"` → 상수 사용 |
| 9 | `services/agent/nodes/tts_designer.py` | speakers dict 키 + Narrator 상수화 |
| 10 | `services/agent/nodes/_cine_compositor.py` | 프롬프트 텍스트 내 speaker 예시 업데이트 |

### Backend — 자동 적용 (코드 변경 불필요)

| 파일 | 이유 |
|------|------|
| `services/storyboard/crud.py` | 이미 `SPEAKER_A`/`SPEAKER_B` 상수 import 사용 |
| `services/video/tts_helpers.py` | 이미 `DEFAULT_SPEAKER` 상수 import 사용 |
| `models/scene.py` | `default=DEFAULT_SPEAKER` — 상수 참조 |

### DB Migration (1개)

| 파일 | 변경 |
|------|------|
| `alembic/versions/sp021_normalize_speaker_ids.py` | `scenes.speaker` + `storyboard_characters.speaker` 데이터 변환 (스키마 변경 없음) |

### Frontend (4개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 1 | `types/index.ts` | `speaker: "Narrator" \| "A" \| "B"` → `speaker: string` |
| 2 | `components/storyboard/SpeakerBadge.tsx` | SPEAKER_STYLES 키 + 비교 로직 + 라벨 |
| 3 | `utils/speakerResolver.ts` | 모든 `"A"/"B"/"Narrator"` → 새 ID |
| 4 | `utils/buildTtsRequest.ts` | 기본값 `"Narrator"` → `"narrator"` |

### 테스트 (36+ 파일)

- Backend 11파일 + Frontend 25파일 — speaker fixture 전수 업데이트
- 기계적 치환: `"A"` → `"speaker_1"`, `"B"` → `"speaker_2"`, `"Narrator"` → `"narrator"`

---

## DoD-1: Speaker ID 정규화

### 구현 방법

**config.py** — 상수 값 변경:
```python
# Before
DEFAULT_SPEAKER = "Narrator"
SPEAKER_A = "A"
SPEAKER_B = "B"

# After
DEFAULT_SPEAKER = "narrator"
SPEAKER_A = "speaker_1"
SPEAKER_B = "speaker_2"
```

**_review_validators.py** — 리터럴 → 상수:
```python
# Before
VALID_SPEAKERS = {"Narrator", "A", "B"}

# After
from config import DEFAULT_SPEAKER, SPEAKER_A, SPEAKER_B
VALID_SPEAKERS = {DEFAULT_SPEAKER, SPEAKER_A, SPEAKER_B}
```

**creative_qc.py** — 리터럴 → 상수:
```python
# Before
_VALID_SPEAKERS = {
    "monologue": frozenset({"A", "Narrator"}),
    "dialogue": frozenset({"A", "B", "Narrator"}),
    "narrated_dialogue": frozenset({"Narrator", "A", "B"}),
}

# After
from config import DEFAULT_SPEAKER, SPEAKER_A, SPEAKER_B
_VALID_SPEAKERS = {
    "monologue": frozenset({SPEAKER_A, DEFAULT_SPEAKER}),
    "dialogue": frozenset({SPEAKER_A, SPEAKER_B, DEFAULT_SPEAKER}),
    "narrated_dialogue": frozenset({DEFAULT_SPEAKER, SPEAKER_A, SPEAKER_B}),
}
```

### 동작 정의
- Before: validator가 `{"Narrator", "A", "B"}`로 검증
- After: validator가 `{"narrator", "speaker_1", "speaker_2"}`로 검증
- config 값 변경 시 validator도 자동 반영

### 엣지 케이스
- 미등록 structure → `_VALID_SPEAKERS.get()` fallback 이미 존재: `frozenset({"A", "Narrator"})` → `frozenset({SPEAKER_A, DEFAULT_SPEAKER})`

### 영향 범위
- `crud.py`, `tts_helpers.py`는 이미 상수 사용으로 자동 적용

### 테스트 전략
- `test_creative_qc` — 각 structure별 유효 speaker 확인
- `test_critic_unit` — validator 검증 (새 ID 포함 확인)

### Out of Scope
- 상수 이름 변경 (`SPEAKER_A` → `SPEAKER_1`) — 별도 리팩토링

---

## DoD-2: 코드 전수 업데이트

### 구현 방법

**공통 패턴**: 리터럴 비교를 config 상수 import로 교체.

```python
# 패턴 A: Narrator 감지
# Before: speaker == "Narrator"
# After:  speaker == DEFAULT_SPEAKER

# 패턴 B: Speaker B 감지
# Before: speaker == "B"
# After:  speaker == SPEAKER_B

# 패턴 C: 비-Narrator 감지
# Before: speaker in ("A", "B")
# After:  speaker in (SPEAKER_A, SPEAKER_B)

# 패턴 D: Speaker 할당
# Before: scene["speaker"] = "A" if i % 2 == 0 else "B"
# After:  scene["speaker"] = SPEAKER_A if i % 2 == 0 else SPEAKER_B
```

**파일별 적용**:

| 파일 | 패턴 | 개소 |
|------|------|------|
| `finalize.py` | A, B | ~10개 (`== "Narrator"` 6+, `== "B"` 2+) |
| `_finalize_validators.py` | A, B | ~4개 |
| `scene_postprocess.py` | A, B, C, D | ~12개 (가장 많음) |
| `revise.py` | A, C, D + regex | ~8개 |
| `cinematographer.py` | dict 키 | ~3개 |
| `tts_designer.py` | dict 키 + A | ~4개 |
| `_cine_compositor.py` | 프롬프트 텍스트 | ~2개 |

**revise.py 특이사항** — regex 패턴:
```python
# Before — QC 에러 메시지 매칭 regex
_INVALID_SPEAKER_RE = re.compile(r"speaker='A' 또는 'Narrator'만 허용")
_DIALOGUE_MISSING_SPEAKER_RE = re.compile(r"Dialogue 구조에서 speaker '([AB])'가 등장하지 않음")

# After — QC가 생성하는 에러 메시지 포맷에 맞춰 업데이트
# (구현 시 creative_qc.py의 실제 에러 메시지 포맷을 확인하여 regex 작성)
```
> regex는 creative_qc 에러 메시지와 동기화되어야 하므로, 구현 시 실제 메시지를 확인 후 작성.

**_cine_compositor.py** — LLM 프롬프트 텍스트:
```python
# Before
"- For Narrator scenes: add no_humans, scenery..."
# JSON 예시: {"speaker": "A", ...}

# After
"- For narrator scenes: add no_humans, scenery..."
# JSON 예시: {"speaker": "speaker_1", ...}
```

### 동작 정의
- 모든 backend 서비스가 새 speaker ID로 비교/할당
- `script_postprocess.py` 등 이미 신규 형식 사용 중인 코드와 통일

### 엣지 케이스
- `revise.py` regex: QC 에러 메시지 포맷 변경에 맞춰 정확히 업데이트
- `_cine_compositor.py` 프롬프트: LLM이 생성하는 speaker 값에 직접 영향 → 반드시 업데이트

### 영향 범위
- 7개 Backend 서비스 파일 수동 변경
- LangFuse 프롬프트는 코드 외 수동 업데이트 필요

### 테스트 전략
- `test_finalize_dialogue_speaker.py` — finalize speaker 라우팅 검증
- `test_dialogue_speaker_fix.py` — scene_postprocess 교대 배정 검증
- `test_revise_expand.py` — revise rule-fix 검증
- `test_casting_sync.py` — speaker→character 매핑 검증

### Out of Scope
- `character_b_id` 변수명 변경 (Phase B)
- LangFuse 프롬프트 수동 업데이트 (구현 완료 후 별도 수행)

---

## DoD-3: Frontend

### 구현 방법

**types/index.ts**:
```typescript
// Before
speaker: "Narrator" | "A" | "B";

// After
speaker: string;
```

**SpeakerBadge.tsx**:
```typescript
// Before
const SPEAKER_STYLES = {
  A: { bg: "bg-blue-100", text: "text-blue-700", label: "A" },
  B: { bg: "bg-violet-100", text: "text-violet-700", label: "B" },
  Narrator: { bg: "bg-amber-100", text: "text-amber-700", label: "N" },
};

// After — 키 + 라벨 변경, fallback 추가
const SPEAKER_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  speaker_1: { bg: "bg-blue-100", text: "text-blue-700", label: "1" },
  speaker_2: { bg: "bg-violet-100", text: "text-violet-700", label: "2" },
  narrator: { bg: "bg-amber-100", text: "text-amber-700", label: "N" },
};

const DEFAULT_STYLE = { bg: "bg-gray-100", text: "text-gray-700", label: "?" };
```

비교 로직도 새 ID로 전환:
```typescript
// Before
if (s === "narrated_dialogue") return ["A", "B", "Narrator"];
if (s === "dialogue") return ["A", "B"];
return ["A"];

// After
if (s === "narrated_dialogue") return ["speaker_1", "speaker_2", "narrator"];
if (s === "dialogue") return ["speaker_1", "speaker_2"];
return ["speaker_1"];
```

**speakerResolver.ts** — 전체 비교 교체:
```typescript
// Before
if (speaker === "Narrator") return null;
if (speaker === "B") return state.selectedCharacterBId;

// After
if (speaker === "narrator") return null;
if (speaker === "speaker_2") return state.selectedCharacterBId;
```
> 5개 resolver 함수 모두 동일 패턴 적용.

**buildTtsRequest.ts**:
```typescript
// Before
speaker: scene.speaker || "Narrator",

// After
speaker: scene.speaker || "narrator",
```

### 동작 정의
- speaker 타입: 고정 유니언 → `string` (Phase C에서 N명 지원 가능)
- SpeakerBadge: `"1 · 하린"`, `"2 · 유나"`, `"N"` 형태로 표시
- 미등록 speaker: DEFAULT_STYLE fallback (회색 배지)

### 엣지 케이스
- `SPEAKER_STYLES[speaker]` 미등록 키 → fallback 스타일 반환 (크래시 방지)
- `Scene["speaker"]`가 `string`으로 넓어지므로 기존 타입 비교 컴파일 에러 없음

### 영향 범위
- 4개 파일 직접 변경
- `creative.ts`의 `character_ids?: Record<string, number>` — `{"A": 1, "B": 2}` 예시 주석 업데이트

### 테스트 전략
- `speakerResolver.test.ts` — 5개 resolver 함수 × 3 speaker ID 검증
- `SpeakerBadge` 관련 테스트 — 새 ID로 렌더 확인

### Out of Scope
- `selectedCharacterBId` → `characters` 리스트 전환 (Phase B)
- N명 캐릭터 동적 UI (Phase C)

---

## DoD-4: DB 마이그레이션

### 구현 방법

```python
# alembic/versions/sp021_normalize_speaker_ids.py
"""SP-021: Normalize speaker IDs (A→speaker_1, B→speaker_2, Narrator→narrator)"""

def upgrade():
    # scenes.speaker 데이터 변환 (soft-deleted rows 포함 — 이력 데이터 일관성 + downgrade 역방향 안전)
    op.execute("UPDATE scenes SET speaker = 'speaker_1' WHERE speaker = 'A'")
    op.execute("UPDATE scenes SET speaker = 'speaker_2' WHERE speaker = 'B'")
    op.execute("UPDATE scenes SET speaker = 'narrator' WHERE speaker = 'Narrator'")

    # scenes.speaker server_default 동기화 (DBA 리뷰 WARNING 반영)
    op.alter_column(
        'scenes', 'speaker',
        server_default='narrator',
        existing_type=sa.String(20),
        existing_nullable=True,
    )

    # storyboard_characters.speaker 데이터 변환
    op.execute("UPDATE storyboard_characters SET speaker = 'speaker_1' WHERE speaker = 'A'")
    op.execute("UPDATE storyboard_characters SET speaker = 'speaker_2' WHERE speaker = 'B'")

def downgrade():
    op.execute("UPDATE scenes SET speaker = 'A' WHERE speaker = 'speaker_1'")
    op.execute("UPDATE scenes SET speaker = 'B' WHERE speaker = 'speaker_2'")
    op.execute("UPDATE scenes SET speaker = 'Narrator' WHERE speaker = 'narrator'")

    # server_default 원복
    op.alter_column(
        'scenes', 'speaker',
        server_default='Narrator',
        existing_type=sa.String(20),
        existing_nullable=True,
    )

    op.execute("UPDATE storyboard_characters SET speaker = 'A' WHERE speaker = 'speaker_1'")
    op.execute("UPDATE storyboard_characters SET speaker = 'B' WHERE speaker = 'speaker_2'")
```

### 동작 정의
- 데이터 변환 + `scenes.speaker` server_default 변경 (DDL 1건)
- `scenes.speaker` 컬럼: String(20) — 충분한 여유
- `storyboard_characters.speaker` 컬럼: String(10) — `"speaker_1"` (9자) 수용 가능
- soft-deleted rows 포함 변환 — 이력 데이터 일관성 + downgrade 역방향 안전

### 엣지 케이스
- NULL speaker → WHERE 조건에 해당 안 함 (무변환)
- 이미 신규 형식 데이터 → 이중 변환 없음 (WHERE가 구 형식만 매칭)
- 롤백 안전: downgrade()로 원복 가능 (server_default 포함)
- server_default: DB INSERT 시 Python ORM 우회 경로(raw SQL 등)에서도 `"narrator"` 적용

### 영향 범위
- DB 데이터 변환 + server_default DDL 1건
- `models/storyboard_character.py` docstring 업데이트 (speaker label 설명)
- `docs/03_engineering/architecture/DB_SCHEMA.md` 업데이트:
  - `scenes.speaker` default: `"Narrator"` → `"narrator"`
  - `storyboard_characters.speaker` 라벨 설명: `"A, B"` → `"speaker_1, speaker_2"`

### 테스트 전략
- `test_sync_speaker_mappings.py` — 새 speaker ID로 매핑 검증
- 마이그레이션 전후 데이터 일관성 확인

### Out of Scope
- `storyboard_characters.speaker` 컬럼 사이즈 변경 (현재 String(10)으로 충분, Phase C에서 필요 시 변경)
- `storyboards.character_id`/`character_b_id` 컬럼 제거 (Phase B)

---

## DoD-5: 품질 (테스트 fixture 전수 업데이트)

### 구현 방법

**일괄 치환 패턴** (speaker 컨텍스트에서만 적용):

| 구 형식 | 신 형식 | 주의 |
|---------|---------|------|
| `"speaker": "A"` | `"speaker": "speaker_1"` | JSON fixture |
| `"speaker": "B"` | `"speaker": "speaker_2"` | JSON fixture |
| `"speaker": "Narrator"` | `"speaker": "narrator"` | JSON fixture |
| `speaker: "A"` | `speaker: "speaker_1"` | TypeScript fixture |
| `speaker: "B"` | `speaker: "speaker_2"` | TypeScript fixture |
| `speaker: "Narrator"` | `speaker: "narrator"` | TypeScript fixture |
| `speaker="A"` | `speaker="speaker_1"` | Python kwarg |
| `speaker="B"` | `speaker="speaker_2"` | Python kwarg |
| `speaker="Narrator"` | `speaker="narrator"` | Python kwarg |

> 주의: `"A"`, `"B"` 단독은 speaker 외 문맥에서도 사용됨 — 반드시 speaker 키 컨텍스트에서만 치환.

### 대상 파일 (36+)

**Backend (11)**:
`test_pipeline_flow_issues`, `test_tts_core`, `test_storyboard`, `test_critic_unit`, `test_finalize_dialogue_speaker`, `test_sync_speaker_mappings`, `test_dialogue_speaker_fix`, `test_revise_expand`, `test_tts_designer_context`, `test_tts_text_filter`, `test_casting_sync`

**Frontend (25)**:
`actions.test.ts`, `SceneEssentialFields.test.tsx`, `DirectorControlPanel.test.tsx`, `autopilotActions.test.ts`, `narratorGeneration.test.ts`, `setGlobalEmotion.test.ts`, `buildScenesPayload.test.ts`, `sseProcessor.test.ts`, `useScriptEditor.test.ts`, `sceneSettingsResolver.test.ts`, `mappers.test.ts`, `autopilotRenderStep.test.ts`, `storyboardActions.test.ts`, `studio.ts` (fixture), `preflight-steps.test.ts`, `updateSceneDirty.test.ts`, `backendCompleteStore.test.ts`, `promptActions.test.ts`, `applyAutoPin.test.ts`, `autoPin.test.ts`, `index.test.ts`, `pinIntegration.test.ts`, `pinnedSceneOrder.test.ts`, `speakerResolver.test.ts`, `warning-toast-e2e.spec.ts`

### 테스트 전략
- RED: 테스트 fixture를 새 ID로 업데이트 → 코드 미변경 상태에서 FAIL 확인
- GREEN: 코드 변경 후 ALL PASS 확인
- 전체 테스트 실행: `pytest` (backend) + `npm test` (frontend)

---

## 실행 순서

1. **DB 마이그레이션 생성** → 코드 변경 전에 준비 (적용은 마지막)
2. **config.py 상수 값 변경** → 기반 변경
3. **Backend 10개 파일** 리터럴 → 상수 교체
4. **Frontend 4개 파일** 변경
5. **테스트 fixture 36개 파일** 업데이트
6. **린트 + 테스트 실행** → ALL PASS 확인
7. **DB 마이그레이션 적용** → 데이터 변환

## LangFuse 프롬프트 (수동 — /sdd-run 범위 밖)

구현 완료 후 수동 업데이트 필요:
- `creative/cinematographer` — speaker 예시
- `creative/tts_designer` — speaker 참조
- Gemini 프롬프트 내 `"A"/"B"/"Narrator"` 예시

이 작업은 코드 외부 시스템이므로 PR에 체크리스트로 기록.
