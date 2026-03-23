# Speaker 동적 역할 체계 — 정적 A/B/Narrator → 캐릭터 기반 동적 역할

> 작성: 2026-03-19 | 갱신: 2026-03-23 | 상태: **미착수** (Phase A 대기 중)
> 선행 조건: [ENUM_ID_NORMALIZATION.md](ENUM_ID_NORMALIZATION.md) 완료 권장
> 흡수: 기존 "캐릭터 복수 표현 리팩토링" 백로그 항목

---

## 1. 배경

현재 speaker 시스템은 **`"A"`, `"B"`, `"Narrator"` 3개 하드코딩**으로 구성되어 있다.

### 현재 구조의 한계

```python
# config.py — 고정 3개
DEFAULT_SPEAKER = "Narrator"
SPEAKER_A = "A"
SPEAKER_B = "B"

# _review_validators.py — 하드코딩 검증
VALID_SPEAKERS = {"Narrator", "A", "B"}

# creative_qc.py — structure별 유효 speaker 맵
_VALID_SPEAKERS = {
    "Monologue": frozenset({"A", "Narrator"}),
    "Dialogue": frozenset({"A", "B", "Narrator"}),
    ...
}

# frontend/types — 고정 리터럴 유니언
speaker: "Narrator" | "A" | "B"
```

**문제**:
- 3인 이상 캐릭터 확장 불가 (`"C"`, `"D"` 추가 시 모든 검증/매핑 코드 수정 필요)
- `character_id` + `character_b_id` 하드코딩이 76파일 432참조에 산재
- speaker 표시 이름이 `"A"`, `"B"`로 무의미 — 캐릭터 이름으로 표시해야 함
- `storyboard_characters` 테이블은 이미 동적 매핑을 지원하지만, 나머지 코드가 활용하지 못함

### 이미 존재하는 동적 인프라

| 컴포넌트 | 상태 | 설명 |
|----------|------|------|
| `storyboard_characters` 테이블 | ✅ 존재 | speaker ↔ character_id 동적 매핑 (유일한 SSOT) |
| `speaker_resolver.py` | ✅ 존재 | `resolve_speaker_to_character()`, `assign_speakers()` |
| `scene_character_actions` 테이블 | ✅ 존재 | 씬별 캐릭터별 액션 태그 |
| `casting_sync.py` | ✅ 존재 | 캐스팅 변경 → 씬 캐스케이드 |

### 2026-03-23 코드 감사 결과

| 항목 | 상태 | 비고 |
|------|------|------|
| ORM `character_id`/`character_b_id` | ✅ 이미 제거 | `storyboard_characters` 관계만 사용 |
| API 스키마 `character_id`/`character_b_id` | ❌ 잔존 | Phase B 제거 대상 |
| `StoryboardDetailResponse.characters` | ✅ 이미 추가 | 동적 리스트 응답 병존 |
| 일부 서비스 신규 형식 사용 | ⚠️ 혼용 | `script_postprocess.py` 등에서 `"speaker_1"` 사용 중 |
| config/validator/QC | ❌ 구 형식 | Phase A 대상 |
| Frontend 타입 | ❌ 고정 유니언 | Phase A 대상 |
| 테스트 fixture | ❌ 구 형식 37+파일 | Phase A 대상 |

---

## 2. 목표

1. **`character_id` + `character_b_id` 하드코딩 제거** → `characters: list` 구조
2. **Speaker를 고정 enum에서 동적 역할로 전환** — 캐릭터 수에 따라 자동 확장
3. **Speaker 표시 이름 = 캐릭터 이름** — `storyboard_characters` JOIN으로 파생
4. **3인 이상 멀티캐릭터 확장 가능 구조** 확보

---

## 3. 설계

### 3-1. Speaker ID 체계

```
현재:  "A", "B", "Narrator"           ← 고정 3개, 의미 불명확
목표:  "speaker_1", "speaker_2", ..., "narrator"  ← N개 확장 가능
```

| Speaker ID | 의미 | 캐릭터 매핑 |
|------------|------|------------|
| `narrator` | 내레이터 (캐릭터 없음, 보이스만) | `narrator_voice_preset_id` |
| `speaker_1` | 첫 번째 등장 캐릭터 | `storyboard_characters` 조회 |
| `speaker_2` | 두 번째 등장 캐릭터 | `storyboard_characters` 조회 |
| `speaker_N` | N번째 등장 캐릭터 | `storyboard_characters` 조회 |

### 3-2. API 변경

```python
# Before — 하드코딩 2개 필드
class StoryboardSave(BaseModel):
    character_id: int | None       # Speaker A
    character_b_id: int | None     # Speaker B

# After — 동적 리스트
class StoryboardSave(BaseModel):
    characters: list[SpeakerAssignment] | None

class SpeakerAssignment(BaseModel):
    speaker: str                   # "speaker_1", "speaker_2", ...
    character_id: int
```

```python
# Before — 고정 응답
class StoryboardDetailResponse(BaseModel):
    character_id: int | None
    character_b_id: int | None
    character_a_name: str | None
    character_b_name: str | None

# After — 동적 리스트 응답
class StoryboardDetailResponse(BaseModel):
    characters: list[CastMember]

class CastMember(BaseModel):
    speaker: str                   # "speaker_1", "narrator", ...
    character_id: int
    character_name: str            # JOIN 파생
    reference_image_url: str | None
```

### 3-3. Scene.speaker 변경

```python
# Before
scene.speaker = "A"          # → storyboard_characters에서 character_id 조회
scene.speaker = "Narrator"   # → narrator_voice_preset_id 사용

# After
scene.speaker = "speaker_1"  # → storyboard_characters에서 character_id 조회
scene.speaker = "narrator"   # → narrator_voice_preset_id 사용
```

### 3-4. Frontend 표시

```typescript
// Before — 무의미한 "A", "B" 표시
<SpeakerBadge speaker="A" />  // → "A"

// After — 캐릭터 이름 표시
<SpeakerBadge speaker="speaker_1" characters={cast} />  // → "하린"
```

### 3-5. `storyboard_characters` 활용 확대

현재 테이블은 존재하지만 `character_id`/`character_b_id` 필드와 이중 관리 상태.

```
Before (명세 작성 시점):
  storyboards.character_id ──→ Character A (하드코딩)
  storyboards.character_b_id ──→ Character B (하드코딩)
  storyboard_characters ──→ speaker→character 매핑 (동적, 동기화 필요)

현재 (2026-03-23):
  storyboard_characters ──→ speaker→character 매핑 (유일한 SSOT) ← ORM 완료
  storyboards.character_id / character_b_id ──→ ORM에서 제거됨
  API 스키마에는 아직 잔존 (Phase B에서 제거)
```

---

## 4. 영향 범위 (코드 감사 결과)

### 4-1. Backend — `character_b_id` 참조 (52파일)

| 카테고리 | 주요 파일 | 변경 내용 |
|----------|----------|----------|
| **스키마** | `schemas.py` (6+ 스키마) | `character_id`/`character_b_id` → `characters: list` |
| **CRUD** | `storyboard/crud.py` | `_sync_speaker_mappings()` → `characters` 리스트 기반 |
| **Agent 노드** | `inventory_resolve.py`, `finalize.py`, `cinematographer.py`, `tts_designer.py`, `revise.py` | CastingModel → `speakers: list`, speaker 매핑 동적화 |
| **Agent 헬퍼** | `_finalize_validators.py`, `_context_tag_utils.py`, `_diversify_utils.py`, `scene_postprocess.py` | Narrator 필터/speaker 비교 → 동적 참조 |
| **이미지 생성** | `image_generation_core.py` | `character_b_id` → speakers 리스트에서 조회 |
| **TTS** | `tts_helpers.py`, `tts_voice_design.py` | speaker→character 매핑 동적 조회 |
| **캐스팅** | `casting_sync.py`, `speaker_resolver.py` | N개 speaker 대응 |
| **액션** | `action_resolver.py` | N개 캐릭터 액션 생성 |
| **검증** | `creative_qc.py`, `_review_validators.py` | `VALID_SPEAKERS` 동적화 |
| **QC** | `creative_qc.py` | `_VALID_SPEAKERS` dict → 동적 |

### 4-2. Frontend — `character_b_id` 참조 (14파일)

| 카테고리 | 주요 파일 | 변경 내용 |
|----------|----------|----------|
| **타입** | `types/index.ts` | `speaker: "Narrator"\|"A"\|"B"` → `string` |
| **Store** | `useStoryboardStore.ts` | `characterBId` → `characters: CastMember[]` |
| **Hooks** | `scriptEditor/actions.ts`, `sseProcessor.ts` | 리스트 기반 |
| **UI** | `PromptSetupPanel.tsx`, `SceneToolsContent.tsx` | N개 캐릭터 셀렉터 |

### 4-3. 테스트 (28파일)

- speaker 하드코딩 (`"A"`, `"B"`, `"Narrator"`) 전수 업데이트
- fixture 데이터 `character_id`/`character_b_id` → `characters` 리스트

---

## 5. 실행 계획

### Phase A: Speaker ID 전환 (핵심 — 후방 호환)

기존 `"A"` → `"speaker_1"`, `"B"` → `"speaker_2"`, `"Narrator"` → `"narrator"` 전환.
이 단계에서는 아직 2인 제한 유지, 포맷만 정규화.

| # | 작업 | 파일 | 담당 |
|---|------|------|------|
| A-1 | `config.py` speaker 상수 변경 | `config.py` | Backend Dev |
| A-2 | `Scene.speaker` DB 마이그레이션 | `alembic/` | DBA |
| A-3 | `_review_validators.py` `VALID_SPEAKERS` 업데이트 | validators | Backend Dev |
| A-4 | `creative_qc.py` `_VALID_SPEAKERS` 업데이트 | creative_qc | Backend Dev |
| A-5 | `tts_helpers.py` speaker 비교 업데이트 | TTS | Backend Dev |
| A-6 | Frontend `speaker` 타입 + 비교 업데이트 | types, components | Frontend Dev |
| A-7 | 테스트 speaker 문자열 업데이트 | 테스트 다수 | QA |

### Phase B: `character_b_id` → `characters` 리스트 전환

API 계약 변경. `character_id`/`character_b_id` 2필드 → `characters: list` 리스트.

| # | 작업 | 파일 | 담당 |
|---|------|------|------|
| B-1 | `SpeakerAssignment`, `CastMember` 스키마 정의 | `schemas.py` | Backend Dev |
| B-2 | `StoryboardSave` → `characters: list` 전환 | `schemas.py` | Backend Dev |
| B-3 | `_sync_speaker_mappings()` 리스트 기반 리팩토링 | `crud.py` | Backend Dev |
| B-4 | `StoryboardDetailResponse` → `characters: list` | `schemas.py`, `crud.py` | Backend Dev |
| B-5 | Agent CastingModel → speakers list | `llm_models.py` | Backend Dev |
| B-6 | `image_generation_core.py` multi-char 로직 리스트 기반 | generation | Backend Dev |
| B-7 | DB에서 `storyboards.character_id`, `character_b_id` 컬럼 DROP | `alembic/` | DBA |
| B-8 | Frontend Store `characterBId` → `characters` | Store, Hooks | Frontend Dev |
| B-9 | Frontend UI N-캐릭터 셀렉터 | `PromptSetupPanel.tsx` | Frontend Dev |
| B-10 | 전체 테스트 업데이트 (28파일) | 테스트 | QA |

### Phase C: 3인+ 캐릭터 확장

2인 제한 해제. `speaker_3`, `speaker_4`, ... 동적 추가.

| # | 작업 | 파일 | 담당 |
|---|------|------|------|
| C-1 | `_VALID_SPEAKERS` → `storyboard_characters` 기반 동적 검증 | validators, QC | Backend Dev |
| C-2 | Gemini CastingModel → N명 캐스팅 | `llm_models.py`, 프롬프트 | Backend Dev |
| C-3 | 이미지 생성 N-캐릭터 대응 | `image_generation_core.py` | Backend Dev |
| C-4 | TTS N-speaker 보이스 매핑 | `tts_helpers.py` | Backend Dev |
| C-5 | Frontend N-캐릭터 UI | 다수 컴포넌트 | Frontend Dev |
| C-6 | E2E 검증 (3인 캐릭터 파이프라인) | — | QA |

---

## 6. 후방 호환성

| 항목 | 전략 |
|------|------|
| Phase A | speaker 값 마이그레이션 (`"A"`→`"speaker_1"` 등). 기존 API는 호환 레이어 제공 |
| Phase B | `character_id`/`character_b_id` → `characters` 리스트. 마이그레이션 기간 동안 양쪽 수용 후 deprecate |
| Phase C | 기존 2인 스토리보드는 그대로 동작. 3인+는 새 구조에서만 |
| Gemini | CastingModel 스키마 변경 → LangFuse 프롬프트 예시 업데이트 |
| Frontend localStorage | 기존 characterId/characterBId 마이그레이션 로직 추가 |

---

## 7. 리스크

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 76파일 432참조 대규모 리팩토링 | 높음 | Phase 분할로 단계적 진행. Phase A는 저리스크 |
| `storyboard_characters` 조회 성능 | 낮음 | 이미 eager load 적용. 행 수 소량 (storyboard당 2~5행) |
| Gemini 캐스팅 정확도 | 중간 | 3인+ 캐스팅 프롬프트 튜닝 필요 |
| SD 3인+ 이미지 생성 품질 | 높음 | Phase C는 ComfyUI 전환 후 착수 권장 |

---

## 8. DoD (Definition of Done)

### Phase A
- [ ] Speaker ID 정규화 완료 (`"speaker_1"`, `"speaker_2"`, `"narrator"`)
- [ ] DB 마이그레이션 적용
- [ ] 하드코딩 `"A"`, `"B"`, `"Narrator"` 비교 0건
- [ ] 전체 테스트 PASS

### Phase B
- [ ] `character_id`/`character_b_id` 컬럼 DROP
- [ ] API 계약 `characters: list` 전환 완료
- [ ] `storyboard_characters` 유일한 SSOT
- [ ] Frontend Store 리스트 기반 전환

### Phase C
- [ ] 3인 이상 캐릭터 파이프라인 E2E 동작
- [ ] Gemini 3인 캐스팅 정확도 > 80%
- [ ] 이미지 생성 3인 씬 품질 검증

---

## 9. 참조 문서

| 문서 | 관련 |
|------|------|
| [MULTI_CHARACTER.md](MULTI_CHARACTER.md) | 기존 멀티캐릭터 인프라 |
| [ENUM_ID_NORMALIZATION.md](ENUM_ID_NORMALIZATION.md) | 선행 — structure/language ID 정규화 |
| [CHARACTER_CONSISTENCY_V2.md](CHARACTER_CONSISTENCY_V2.md) | 캐릭터 이미지 일관성 |
| [CHARACTER_CONSISTENCY_V3.md](CHARACTER_CONSISTENCY_V3.md) | ComfyUI FaceID 멀티캐릭터 |
| `services/characters/speaker_resolver.py` | 핵심 리졸버 |
| `services/characters/casting_sync.py` | 캐스팅 캐스케이드 |

---

**Last Updated:** 2026-03-23
