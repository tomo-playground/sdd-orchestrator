# SP-056 상세 설계

## DoD-1: config.py STRUCTURE_METADATA에서 confession 제거

### 구현 방법
- `config.py`: `STRUCTURE_METADATA` 튜플에서 confession 항목 제거 (4종 → 3종)
- `StructureMeta.tone` → `default_tone`으로 rename
- `narrated_dialogue`의 `default_tone`: `"narrative"` → `"intimate"` (narrative는 유효 tone이 아님)
- 파생 상수(`STRUCTURE_IDS`, `MULTI_CHAR_STRUCTURES` 등)는 튜플에서 자동 파생되므로 수정 불필요

### 동작 정의
- Before: `STRUCTURE_IDS = {"monologue", "dialogue", "narrated_dialogue", "confession"}`
- After: `STRUCTURE_IDS = {"monologue", "dialogue", "narrated_dialogue"}`
- `StructureMeta(id, label, label_ko, requires_two_characters, default_tone)`

### 엣지 케이스
- 파생 상수(`STRUCTURE_ID_TO_LABEL`, `STRUCTURE_LABEL_TO_ID`)에서 confession 자동 제거 확인

### 영향 범위
- `_STRUCTURE_COERCE_MAP` 자동 재생성 (confession 키 사라짐 → DoD-3에서 fallback 처리)

### 테스트 전략
- `STRUCTURE_IDS`에 confession이 없음을 assert
- `STRUCTURE_METADATA` 길이 == 3 assert
- `StructureMeta` 각 항목에 `default_tone` 필드 존재 assert

### Out of Scope
- structure 추가 (3종 고정)

---

## DoD-2: presets.py confession 프리셋 제거

### 구현 방법
- `PRESETS` dict에서 `"confession"` 키-값 제거
- `get_preset_by_structure("confession")` → None 반환 (자연스러운 fallback)
- `get_all_presets()` 응답에서 confession 자동 제거

### 동작 정의
- Before: `/presets` API가 4개 프리셋 반환
- After: `/presets` API가 3개 프리셋 반환

### 엣지 케이스
- DB에 `structure='confession'`인 스토리보드 로드 시 → `get_preset_by_structure()` None → gemini_generator에서 default template(`"create_storyboard"`) fallback (기존 동작)

### 영향 범위
- Frontend `StoryboardGeneratorPanel.tsx` — 서버에서 presets 소비하므로 자동 반영

### 테스트 전략
- `get_all_presets()` 반환 dict에 `"confession"` 키 없음 assert
- `get_preset_by_structure("confession")` → None assert

### Out of Scope
- LangFuse `storyboard/confession` 프롬프트 삭제 (보존)

---

## DoD-3: coerce_structure_id() "confession" → "monologue" fallback

### 구현 방법
- `config.py`: `_STRUCTURE_COERCE_MAP`은 `STRUCTURE_METADATA`에서 자동 생성되므로, confession 제거 후 "confession" 키가 사라짐
- 추가 매핑: `_STRUCTURE_COERCE_MAP`에 수동 fallback 삽입

```python
# STRUCTURE_METADATA 자동 생성 후 하위 호환 매핑 추가
_STRUCTURE_COERCE_MAP["confession"] = "monologue"
_STRUCTURE_COERCE_MAP["Confession"] = "monologue"
```

### 동작 정의
- Before: `coerce_structure_id("confession")` → `"confession"`
- After: `coerce_structure_id("confession")` → `"monologue"`

### 엣지 케이스
- `"Confession"`, `"CONFESSION"`, `" confession "` 등 다양한 표현 → 정규화 후 "confession" → "monologue"

### 영향 범위
- DB에 `structure='confession'` 레코드가 남아있어도 런타임에서 monologue로 처리됨 (DB 마이그레이션 전에도 안전)

### 테스트 전략
- `coerce_structure_id("confession")` == `"monologue"` assert
- `coerce_structure_id("Confession")` == `"monologue"` assert

### Out of Scope
- DB에서 confession → monologue 일괄 UPDATE (DoD-10에서 처리)

---

## DoD-4: confession 참조 테스트 갱신

### 구현 방법
변경 대상 테스트 파일:
- `test_coerce_functions.py`: confession → monologue 반환으로 기대값 변경
- `test_inventory.py`: 3종 structure assert로 변경
- `test_llm_models_casting.py`: confession 케이스를 monologue로 대체
- `test_router_presets.py`: `"confession" in ids` assert 제거

### 동작 정의
- Before: confession이 유효한 structure로 테스트됨
- After: confession 입력 시 monologue 반환을 테스트

### 테스트 전략
- 모든 기존 테스트가 갱신 후 PASS

### Out of Scope
- 새 테스트 추가 (기존 테스트 갱신만)

---

## DoD-5: ToneMeta + TONE_METADATA 정의

### 구현 방법
- `config.py`에 추가:

```python
@dataclass(frozen=True)
class ToneMeta:
    id: str
    label: str
    label_ko: str

TONE_METADATA: tuple[ToneMeta, ...] = (
    ToneMeta(id="intimate", label="Intimate", label_ko="담담"),
    ToneMeta(id="emotional", label="Emotional", label_ko="감정적"),
    ToneMeta(id="dynamic", label="Dynamic", label_ko="역동적"),
    ToneMeta(id="humorous", label="Humorous", label_ko="유머"),
    ToneMeta(id="suspense", label="Suspense", label_ko="서스펜스"),
)

TONE_IDS: frozenset[str] = frozenset(t.id for t in TONE_METADATA)
DEFAULT_TONE = "intimate"
```

### 동작 정의
- 5종 tone이 config.py SSOT로 정의됨

### 엣지 케이스
- 유효하지 않은 tone 입력 → `DEFAULT_TONE` fallback (coerce 함수 추가)

```python
def coerce_tone_id(value: str | None) -> str:
    if not value:
        return DEFAULT_TONE
    normalized = value.strip().lower()
    return normalized if normalized in TONE_IDS else DEFAULT_TONE
```

### 테스트 전략
- `TONE_IDS` 길이 == 5 assert
- `DEFAULT_TONE == "intimate"` assert
- `coerce_tone_id("emotional")` == `"emotional"` assert
- `coerce_tone_id("invalid")` == `"intimate"` assert
- `coerce_tone_id(None)` == `"intimate"` assert

### Out of Scope
- tone별 LangFuse 프롬프트 분기 (이 태스크에서는 변수 주입만)

---

## DoD-6: storyboards 테이블에 tone 컬럼 추가 (Alembic)

### 구현 방법
- 신규 마이그레이션 파일 (`alembic/versions/xxxx_add_storyboard_tone.py`)
- `down_revision = "z8a9b0c1d2e3"` (현재 head)

```python
def upgrade():
    op.add_column("storyboards", sa.Column("tone", sa.String(30), server_default="intimate", nullable=False))

def downgrade():
    op.drop_column("storyboards", "tone")
```

### 동작 정의
- Before: storyboards 테이블에 tone 컬럼 없음
- After: `tone VARCHAR(30) NOT NULL DEFAULT 'intimate'`

### 영향 범위
- 기존 레코드에 `server_default="intimate"` 자동 적용

### 테스트 전략
- 마이그레이션 up/down 정상 실행 확인 (alembic upgrade/downgrade)

### Out of Scope
- confession 데이터 변환 (DoD-10에서 처리 — 별도 마이그레이션 또는 동일 마이그레이션 내 data migration)

---

## DoD-7: Storyboard ORM 모델에 tone 필드 추가

### 구현 방법
- `backend/models/storyboard.py`:

```python
tone: Mapped[str] = mapped_column(String(30), nullable=False, default=DEFAULT_TONE, server_default=DEFAULT_TONE)
```

### 동작 정의
- ORM으로 Storyboard 생성 시 tone 필드 기본값 "intimate"

### 영향 범위
- `serialize_storyboard()` 등에서 tone이 자동으로 포함됨 (컬럼 기반 직렬화)

### 테스트 전략
- `Storyboard()` 생성 시 `tone == DEFAULT_TONE` assert

### Out of Scope
- Frontend 타입 변경 (별도 DoD)

---

## DoD-8: /presets API에 tones 목록 포함

### 구현 방법
- `backend/services/presets.py`에 `get_all_tones()` 함수 추가:

```python
def get_all_tones() -> list[dict]:
    return [{"id": t.id, "label": t.label, "label_ko": t.label_ko} for t in TONE_METADATA]
```

- `backend/routers/presets.py` 응답에 `tones` 필드 추가
- `backend/schemas.py`에 `PresetsResponse`가 있으면 `tones` 필드 추가

### 동작 정의
- Before: `GET /presets` → `{ presets: [...], languages: [...] }`
- After: `GET /presets` → `{ presets: [...], languages: [...], tones: [...] }`

### 테스트 전략
- `GET /presets` 응답에 `tones` 키 존재 + 길이 == 5 assert
- 각 tone에 `id`, `label`, `label_ko` 필드 존재 assert

### Out of Scope
- Frontend에서 tones를 소비하는 UI (SP-058 Intake 노드에서 활용)

---

## DoD-9: Writer 노드에서 tone 변수 주입

### 구현 방법
- `backend/services/agent/state.py`: `ScriptState`에 `tone: str` 추가
- `backend/services/agent/nodes/writer.py`: `state.get("tone")` → `coerce_tone_id()` → `builder_vars["tone"]`로 전달
- `backend/services/agent/prompt_builders_writer.py`에 `build_tone_hint_block(tone: str) -> str` 함수 추가:

```python
def build_tone_hint_block(tone: str) -> str:
    hints = {
        "intimate": "Write in a calm, introspective tone. Focus on inner thoughts.",
        "emotional": "Write with deep emotion. Include vulnerable moments and heartfelt expressions.",
        "dynamic": "Write with energy and tension. Use short, punchy dialogue.",
        "humorous": "Write with wit and humor. Include comedic timing and light moments.",
        "suspense": "Write with tension and mystery. Build suspense gradually.",
    }
    return f"- Tone: {tone}\n- {hints.get(tone, '')}"
```

- `build_structure_rules_block()` 호출 근처에서 `build_tone_hint_block()` 호출하여 프롬프트에 추가
- `gemini_generator.py`: `StoryboardRequest`에 `tone: str = DEFAULT_TONE` 추가, `builder_vars["tone_hint"]` 전달
- LangFuse 프롬프트 템플릿에 `{tone_hint}` 변수 슬롯 추가

### 동작 정의
- Before: Writer가 structure만 기반으로 프롬프트 생성
- After: Writer가 structure + tone 기반으로 프롬프트 생성

### 엣지 케이스
- tone이 state에 없을 때 → `coerce_tone_id(None)` → `"intimate"` (기본값)

### 영향 범위
- LangFuse 프롬프트 4개 (`storyboard/default`, `storyboard/dialogue`, `storyboard/narrated`, `storyboard/confession`)에 `{tone_hint}` 변수 추가 필요
- `storyboard/confession` 프롬프트는 tone=emotional 시 특화 지시문으로 활용 가능 (별도 태스크)

### 테스트 전략
- `build_tone_hint_block("emotional")` 출력에 "emotion" 키워드 포함 assert
- `build_tone_hint_block("invalid")` → 빈 힌트 (fallback) assert
- Writer 노드에서 state에 tone이 있으면 builder_vars에 전달되는지 단위 테스트

### Out of Scope
- tone별 LangFuse 프롬프트 분기 (단일 템플릿에 tone_hint 변수 주입 방식)
- Cinematographer/TTS Designer에 tone 전달 (이 태스크 범위 아님)

---

## DoD-10: DB 데이터 마이그레이션 (confession → monologue + emotional)

### 구현 방법
- DoD-6과 동일 마이그레이션 파일에 data migration 포함:

```python
def upgrade():
    # 1. tone 컬럼 추가
    op.add_column("storyboards", sa.Column("tone", sa.String(30), server_default="intimate", nullable=False))
    # 2. confession → monologue + emotional
    op.execute("UPDATE storyboards SET structure = 'monologue', tone = 'emotional' WHERE structure = 'confession'")
```

### 동작 정의
- Before: `structure='confession'` 레코드 존재
- After: `structure='monologue', tone='emotional'`로 변환. 나머지는 `tone='intimate'` (server_default)

### 엣지 케이스
- confession 레코드가 0건일 때 → UPDATE 0 rows (정상)

### 테스트 전략
- 마이그레이션 실행 후 `SELECT COUNT(*) FROM storyboards WHERE structure = 'confession'` == 0 확인

### Out of Scope
- Frontend localStorage의 structure='confession' 데이터 (coerce_structure_id로 런타임 처리)

---

## DoD-11/12: 기존 테스트 regression 없음 + 린트 통과

### 구현 방법
- `pytest backend/tests/` 전체 실행
- `ruff check backend/` 실행

### 추가 변경 필요 파일 (confession 참조 정리)

| 파일 | 조치 |
|------|------|
| `creative_qc.py` | `_VALID_SPEAKERS`에서 `"confession"` 키 제거 |
| `_review_validators.py` | `("monologue", "confession")` → `"monologue"` |
| `prompt_builders_inventory.py` | structure 목록에서 confession 제거 (3종) |
| `CompletionCard.tsx` | `STRUCTURE_LABELS`에서 confession 제거 |
| `.claude/agents/storyboard-writer.md` | 4종 → 3종 업데이트 |

---

## 변경 파일 요약

| 파일 | 변경 유형 |
|------|----------|
| `backend/config.py` | STRUCTURE_METADATA 수정 + ToneMeta/TONE_METADATA 추가 + coerce fallback |
| `backend/services/presets.py` | confession 프리셋 제거 + get_all_tones() 추가 |
| `backend/models/storyboard.py` | tone 필드 추가 |
| `backend/alembic/versions/xxxx_*.py` | tone 컬럼 + confession 데이터 마이그레이션 |
| `backend/schemas.py` | StoryboardBase에 tone 추가 + PresetsResponse에 tones 추가 |
| `backend/services/agent/state.py` | ScriptState에 tone 추가 |
| `backend/services/agent/nodes/writer.py` | tone 변수 주입 |
| `backend/services/agent/prompt_builders_writer.py` | build_tone_hint_block() 추가 |
| `backend/services/script/gemini_generator.py` | StoryboardRequest에 tone + builder_vars 전달 |
| `backend/services/creative_qc.py` | confession 제거 |
| `backend/services/agent/nodes/_review_validators.py` | confession 제거 |
| `backend/services/agent/prompt_builders_inventory.py` | 3종 목록 |
| `backend/routers/presets.py` | tones 응답 추가 |
| `frontend/.../CompletionCard.tsx` | STRUCTURE_LABELS confession 제거 |
| `backend/tests/` (4파일) | confession 케이스 갱신 |

**총 15파일** (스키마 변경 포함이므로 DBA 리뷰 필수)
