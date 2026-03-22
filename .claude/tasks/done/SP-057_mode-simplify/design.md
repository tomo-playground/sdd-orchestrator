# SP-057 상세 설계

## DoD-1: schemas.py interaction_mode Literal 변경

### 구현 방법
- `backend/schemas.py` L449:
  - Before: `interaction_mode: Literal["auto", "guided", "hands_on"] = "guided"`
  - After: `interaction_mode: Literal["guided", "fast_track"] = "guided"`

### 동작 정의
- API 요청 시 `"auto"` / `"hands_on"` 전달 → Pydantic validation error
- `coerce_interaction_mode()` (DoD-2)에서 라우터 레벨 변환으로 방어

### 엣지 케이스
- 기존 클라이언트가 `"auto"` 전달 → DoD-2 coerce로 `"fast_track"` 변환 (라우터에서 처리)

### 테스트 전략
- `StoryboardRequest(interaction_mode="guided")` 정상 생성 assert
- `StoryboardRequest(interaction_mode="fast_track")` 정상 생성 assert

### Out of Scope
- 새 모드 추가

---

## DoD-2: coerce_interaction_mode() 함수 추가

### 구현 방법
- `backend/config.py`에 추가:

```python
def coerce_interaction_mode(value: str | None) -> str:
    if not value:
        return "guided"
    normalized = value.strip().lower()
    _MODE_MAP = {"auto": "fast_track", "hands_on": "guided"}
    return _MODE_MAP.get(normalized, normalized if normalized in ("guided", "fast_track") else "guided")
```

- `backend/routers/scripts.py` `_request_to_state()`에서 호출:
  - Before: `mode = request.interaction_mode or "guided"`
  - After: `mode = coerce_interaction_mode(request.interaction_mode)`

### 동작 정의
- `"auto"` → `"fast_track"`
- `"hands_on"` → `"guided"`
- `"guided"` → `"guided"`
- `"fast_track"` → `"fast_track"`
- `None` / `""` / 무효값 → `"guided"`

### 테스트 전략
- 각 입력에 대한 매핑 assert (5개 케이스)

### Out of Scope
- DB 마이그레이션 (interaction_mode는 DB에 저장되지 않음 — 요청 파라미터)

---

## DoD-3: Gate 노드 + routing.py 모드 분기 갱신

### 구현 방법

**concept_gate.py** (L24):
- Before: `if mode == "auto" or state.get("auto_approve"):`
- After: `if mode == "fast_track":`

**director_plan_gate.py** (L23):
- Before: `if mode == "auto" or state.get("auto_approve"):`
- After: `if mode == "fast_track":`

**human_gate.py** — 전체 삭제 또는 dead code 처리:
- `route_after_director`에서 `hands_on` 분기 제거 → `human_gate` 도달 경로 없어짐
- human_gate_node 함수 본문을 즉시 approve로 단순화 (안전 fallback)

**routing.py** `route_after_director` (L188-193):
- Before: `if mode == "hands_on": return "human_gate"`
- After: 해당 분기 제거. `"approve"` / `"error"` → 항상 `"finalize"`

**state.py** (L131):
- `auto_approve` 필드 제거
- `interaction_mode` 주석 업데이트: `# "guided" | "fast_track"`

**scripts.py** `_request_to_state()` (L72):
- `auto_approve=(mode == "auto")` 라인 제거
- ScriptState 생성 시 `auto_approve` 키 제거

### 동작 정의
| 모드 | concept_gate | director_plan_gate | Critic 루프 | Director 검수 |
|------|-------------|-------------------|------------|--------------|
| `guided` | interrupt (사용자 선택) | interrupt (사용자 승인) | 최대 3회 | 최대 3회 |
| `fast_track` | pass-through | pass-through | **1회** (DoD-4) | **1회** (DoD-5) |

### 엣지 케이스
- 테스트에서 `auto_approve=True`를 직접 사용하는 4곳 → `interaction_mode="fast_track"`으로 대체

### 영향 범위
- `auto_approve` 제거로 state 직렬화 변경 — 진행 중인 LangGraph 세션에서 호환성 주의 (state에 `auto_approve` 키가 없어도 `.get("auto_approve")` fallback None이므로 안전)

### 테스트 전략
- `concept_gate_node(state={..., "interaction_mode": "fast_track"})` → `{"concept_action": "select"}` assert
- `director_plan_gate_node(state={..., "interaction_mode": "guided"})` → interrupt 발행 assert
- `route_after_director(state={..., "interaction_mode": "guided"})` → `"finalize"` assert (hands_on 분기 없음)

### Out of Scope
- human_gate 노드를 그래프에서 완전히 제거 (안전 fallback으로 유지)

---

## DoD-4: FastTrack Critic 반복 1회 제한

### 구현 방법
- `backend/services/agent/routing.py` `route_after_review()`:
  - fast_track 모드일 때 `LANGGRAPH_MAX_REVISIONS` 대신 **1**을 사용
  - 구현: `max_rev = 1 if state.get("interaction_mode") == "fast_track" else LANGGRAPH_MAX_REVISIONS`

### 동작 정의
- **guided**: Critic이 fail 판정 → Writer revise → Critic 재검토 (최대 3회)
- **fast_track**: Critic이 fail 판정 → Writer revise 1회 → 강제 통과

### 엣지 케이스
- 글로벌 리비전 상한(`LANGGRAPH_MAX_GLOBAL_REVISIONS=6`)은 그대로 적용
- fast_track에서 1회 revise 후에도 Critic fail → 강제 통과 (품질 < 속도 트레이드오프 허용)

### 테스트 전략
- `route_after_review(state={..., "interaction_mode": "fast_track", "revision_count": 1})` → writer가 아닌 다음 단계로 진행 assert
- `route_after_review(state={..., "interaction_mode": "guided", "revision_count": 1})` → `"revise"` assert

### Out of Scope
- Critic 로직 자체 변경

---

## DoD-5: FastTrack Director 검수 1회 제한

### 구현 방법
- `backend/services/agent/routing.py` `route_after_director()`:
  - fast_track 모드일 때 `LANGGRAPH_MAX_DIRECTOR_REVISIONS` 대신 **1** 사용
  - 구현: `max_dir_rev = 1 if state.get("interaction_mode") == "fast_track" else LANGGRAPH_MAX_DIRECTOR_REVISIONS`

### 동작 정의
- **guided**: Director revise 판정 → 타겟 재실행 → Director 재검토 (최대 3회)
- **fast_track**: Director revise 판정 → 타겟 재실행 1회 → 강제 finalize

### 엣지 케이스
- Director 내부 ReAct 루프(`LANGGRAPH_MAX_REACT_STEPS=3`)는 fast_track에서도 유지 (1 Director 호출 내에서의 판단 루프이므로)

### 테스트 전략
- `route_after_director(state={..., "interaction_mode": "fast_track", "director_revision_count": 1})` → `"finalize"` assert
- `route_after_director(state={..., "interaction_mode": "guided", "director_revision_count": 1})` → 재실행 가능 assert

### Out of Scope
- Director ReAct 스텝 수 변경

---

## DoD-6: FastTrack Director Plan Gate 자동 승인

### 구현 방법
- DoD-3에서 이미 처리됨: `director_plan_gate.py`에서 `mode == "fast_track"` → pass-through

### 동작 정의
- **guided**: Director Plan 결과를 사용자에게 보여주고 승인/수정 대기
- **fast_track**: Director Plan 결과를 자동 승인하고 즉시 진행

---

## DoD-7: Frontend 모드 UI 갱신

### 구현 방법

**ChatInput.tsx**:
- `InteractionMode` 타입: `"auto" | "guided"` → `"guided" | "fast_track"`
- `MODE_OPTIONS` 배열:
  - Before: `[{value: "auto", label: "Auto"}, {value: "guided", label: "Guided"}]`
  - After: `[{value: "guided", label: "Guided", tooltip: "컨셉, 플랜 단계에서 직접 선택하고 AI와 협력"}, {value: "fast_track", label: "Fast", tooltip: "AI가 알아서 선택·승인 — 빠른 초안 생성"}]`
- **FastTrack 토글(⚡ Fast) 제거** — 별도 토글이 아닌 모드 선택에 통합

**scriptEditor/types.ts**:
- `interactionMode: "auto" | "guided"` → `"guided" | "fast_track"`

**useScriptEditor.ts** (L81):
- 초기값: `interactionMode: "auto"` → `"guided"` (기본 모드를 guided로 변경)

**scriptEditor/actions.ts** `buildGenerateBody()`:
- `skip_stages` 전달 로직 제거 (`fastTrack` boolean + `fastTrackSkipStages` 제거)
- `interaction_mode` 만 전달

**usePresets.ts**:
- `fastTrackSkipStages` 로딩 로직 제거

### 동작 정의
- Before: Auto/Guided 버튼 + ⚡Fast 토글 (독립)
- After: Guided/Fast 버튼 (2개, 단일 선택)

### 엣지 케이스
- `interactionMode`는 세션 메모리 상태 (localStorage 비영속) → fallback 처리 불필요
- Backend `coerce_interaction_mode()`에서 `"auto"` → `"fast_track"` 변환이 하위 호환 담당

**useChatScriptEditor.ts** (추가 변경):
- `setInteractionMode` 타입: `(mode: "auto" | "guided")` → `(mode: "guided" | "fast_track")`

### 테스트 전략
- `buildGenerateBody()` 결과에 `skip_stages` 키 없음 assert
- `buildGenerateBody()` 결과에 `interaction_mode: "fast_track"` 포함 assert

### Out of Scope
- Intake 노드 연동 (SP-058)

---

## DoD-8: skip_stages / FAST_TRACK_SKIP_STAGES 제거

### 구현 방법

**Backend**:
- `backend/services/agent/config_pipelines.py`: `FAST_TRACK_SKIP_STAGES` 상수 제거
- `backend/routers/scripts.py`: `_resolve_skip_stages()` 함수 제거 / 간소화
  - `skip_stages`를 request에서 받지 않음
  - `_request_to_state()`에서 `skip_stages=[]` 고정
- `backend/services/agent/routing.py`: `"production" in skip` 분기 제거
  - `route_after_review()`: `"production" in skip` 분기 제거 → fast_track 포함 **항상 `"director_checkpoint"` 경유** (모든 노드 실행 원칙)
  - `route_after_cinematographer()`: `"production" in skip` 분기 제거 → fast_track 포함 **항상 fan-out** (tts_designer, sound_designer, copyright_reviewer 모두 실행)
  - `route_after_finalize()`: `"explain" in skip` 분기 제거 → 항상 `"explain"` → `"learn"`
  - `route_after_start()`: `skip_stages` 직접 지정 분기 유지 (Director 자율 skip용)
  - **트레이드오프**: fast_track에서 Production 노드(3개 LLM 호출) 추가 실행 → 속도 감소 vs 품질 향상. "모든 노드 1회 실행"이 설계 원칙이므로 의도적 선택
- `backend/services/agent/nodes/_skip_guard.py`: `should_skip()` 함수 유지 — Director가 런타임에 `_derive_skip_stages()`로 skip_stages를 채울 수 있으므로 제거 불가
- `_derive_skip_stages()`는 Director AI 자율 skip (research/explain)이므로 유지
- `backend/services/agent/script_graph.py`: `route_after_director` conditional edges에서 `"human_gate"` 제거 (도달 불가능 edge)

**Frontend**:
- `frontend/app/hooks/usePresets.ts`: `fastTrackSkipStages` 관련 코드 제거
- `frontend/app/store/useStoryboardStore.ts`: `fastTrackSkipStages` 상태 제거
- `frontend/app/hooks/scriptEditor/types.ts`: `fastTrack: boolean` 제거
- `frontend/app/hooks/scriptEditor/actions.ts`: `skip_stages` 전달 로직 제거

### 동작 정의
- Before: FastTrack 토글 시 `skip_stages=["research","concept","production","explain"]` → 노드 대거 스킵
- After: FastTrack 없음. `fast_track` 모드는 gate 자동 승인 + 반복 1회 제한만

### 엣지 케이스
- Director의 `_derive_skip_stages()` (research/explain AI 자율 skip)는 유지됨 — 이것은 FastTrack과 무관한 AI 판단
- `should_skip()` 호출부가 많으므로, 함수 자체는 유지하되 `skip_stages=[]` 일 때 항상 False 반환 (기존 동작과 동일)

### 영향 범위
- `/presets` API 응답에서 `fastTrackSkipStages` 필드 제거 필요
- `StoryboardRequest`에서 `skip_stages` 필드 제거 (또는 무시)

### 테스트 전략
- `_request_to_state()` 결과의 `skip_stages` == `[]` (Director가 추가하는 것 제외) assert
- `route_after_review()` 에서 skip 분기 없이 항상 `"director_checkpoint"` 경유 assert

### Out of Scope
- Director의 research/explain 자율 skip 로직 변경

---

## DoD-9: CLAUDE.md 폐기 용어 업데이트

### 구현 방법
- CLAUDE.md `### AI 실행 모드` 섹션 업데이트:
  - `auto` → 폐기 용어에 추가
  - `hands_on` → 이미 폐기 상태
  - FastTrack 설명 갱신: "Director/Research/Concept 건너뜀" → "모든 노드 1회 실행, 자동 승인"

### Out of Scope
- 다른 문서 업데이트

---

## DoD-10/11: 테스트 regression + 린트

### 변경 필요 테스트 파일

| 파일 | 조치 |
|------|------|
| `test_pipeline_flow_issues.py` | `"auto"` → `"fast_track"`, `auto_approve` 제거 |
| `test_agent_12b_dataflow_group2.py` | 동일 |
| `test_agent_12b_dataflow_group3.py` | 동일 |
| `test_director_plan_gate.py` | `"auto"` → `"fast_track"`, `auto_approve` → `interaction_mode` 체크로 전환 |
| `test_concept_gate.py` | `auto_approve` 참조 제거, `interaction_mode="fast_track"` 전환 |
| `test_feedback_presets.py` | `auto_approve` 참조 제거 |
| `test_routing.py` | `auto_approve` 참조 제거 |
| `frontend/tests/.../actions.test.ts` | `skip_stages` 관련 테스트 갱신 |

---

## 변경 파일 요약

| 파일 | 변경 유형 |
|------|----------|
| `backend/config.py` | `coerce_interaction_mode()` 추가 |
| `backend/schemas.py` | Literal 타입 변경 |
| `backend/services/agent/state.py` | `auto_approve` 제거, 주석 갱신 |
| `backend/services/agent/routing.py` | hands_on 분기 제거 + fast_track 반복 1회 제한 |
| `backend/services/agent/nodes/concept_gate.py` | mode 체크 변경 |
| `backend/services/agent/nodes/director_plan_gate.py` | mode 체크 변경 |
| `backend/services/agent/nodes/human_gate.py` | 단순화 (dead code) |
| `backend/services/agent/script_graph.py` | route_after_director edges에서 human_gate 제거 |
| `backend/services/agent/config_pipelines.py` | FAST_TRACK_SKIP_STAGES 제거 |
| `backend/routers/scripts.py` | auto_approve 제거 + coerce 호출 + skip 로직 간소화 |
| `backend/services/presets.py` | /presets 응답에서 fast_track_skip_stages 필드 제거 |
| `backend/schemas.py` | ScriptPresetItem.is_auto_approve 필드 제거 |
| `frontend/.../ChatInput.tsx` | 모드 UI 2버튼으로 변경 |
| `frontend/.../useChatScriptEditor.ts` | setInteractionMode 타입 갱신 |
| `frontend/.../types.ts` | InteractionMode 타입 변경 |
| `frontend/.../useScriptEditor.ts` | 초기값 변경 |
| `frontend/.../actions.ts` | skip_stages 전달 제거 |
| `frontend/.../usePresets.ts` | fastTrackSkipStages 제거 |
| `frontend/.../useStoryboardStore.ts` | fastTrackSkipStages 상태 제거 |
| `CLAUDE.md` | 폐기 용어 갱신 |
| `backend/tests/` (3파일) | auto → fast_track 갱신 |
| `frontend/tests/` (1파일) | skip_stages 테스트 갱신 |

**총 21파일 변경**
